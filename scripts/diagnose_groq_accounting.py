"""Operational Groq token-accounting / prompt-cache diagnostic (NOT part of any RQ result).

Identity: groq-accounting-diagnostic-v1. Sends at most three tiny synthetic chat
completions (no benchmark, no research context, no retries). Never imported by
the RQ1 runner; output lives under documentation/rq1_repair/provider_diagnostic.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, re, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tiktoken
from research.common.serialization import canonical_json, content_hash
from research.baselines.config import groq_key

ID = 'groq-accounting-diagnostic-v1'
OUT = ROOT / 'documentation/rq1_repair/provider_diagnostic'
MODEL = 'openai/gpt-oss-120b'
ENC = tiktoken.get_encoding('o200k_harmony')
WORDS = ['river', 'stone', 'cloud', 'window', 'garden', 'copper', 'silent', 'bridge', 'lantern', 'meadow', 'harbor', 'violet', 'candle',
         'orchard', 'quiet', 'ribbon', 'summit', 'pebble', 'carpet', 'engine', 'forest', 'marble', 'basket', 'thunder', 'island', 'velvet',
         'compass', 'feather', 'granite', 'hollow', 'jungle', 'kettle', 'ladder', 'mirror', 'nectar', 'oyster', 'pillow', 'quartz', 'rocket',
         'saddle', 'timber', 'umbrella', 'valley', 'walnut', 'yarn', 'zephyr', 'anchor', 'blanket', 'canyon', 'drizzle', 'ember', 'fabric',
         'glacier', 'harvest', 'iron', 'jasmine', 'knot', 'lagoon', 'mosaic', 'needle', 'ocean', 'prairie', 'rainbow', 'shadow']


def filler(sentences):
    # Deterministic, harmless, benchmark-free text.
    out = []
    for i in range(sentences):
        out.append(' '.join(WORDS[(i * 7 + j * 13 + (i * j) % 11) % len(WORDS)] for j in range(12)).capitalize() + '.')
    return '\n'.join(out)


STATIC = ('SYNTHETIC DIAGNOSTIC PREFIX. The following lines are meaningless filler used only to measure provider token accounting.\n'
          + filler(100) + '\nEnd of filler. Reply with a JSON object {"ok": true} and nothing else.')


def payload(kind):
    common = {'model': MODEL, 'temperature': 0, 'seed': 42, 'reasoning_effort': 'low'}
    if kind == 'A':
        return {**common, 'max_completion_tokens': 1, 'messages': [{'role': 'system', 'content': 'Return the token OK only.'}, {'role': 'user', 'content': 'OK'}]}
    suffix = {'B': 'SUFFIX 1', 'C2': 'SUFFIX 2'}[kind]
    return {**common, 'max_completion_tokens': 48, 'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': STATIC}, {'role': 'user', 'content': suffix}]}


def local_tokens(p):
    return [len(ENC.encode(m['content'], disallowed_special=())) for m in p['messages']]


def common_prefix_tokens(a, b):
    ta = [t for m in a['messages'] for t in ENC.encode(m['content'] + '\x00', allowed_special=set())]
    tb = [t for m in b['messages'] for t in ENC.encode(m['content'] + '\x00', allowed_special=set())]
    n = 0
    while n < min(len(ta), len(tb)) and ta[n] == tb[n]: n += 1
    return n


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_head():
    return subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()


def main():
    kinds = ['A', 'B', 'C2']
    OUT.mkdir(parents=True, exist_ok=True)
    if any(OUT.glob('call_*.json')):
        raise SystemExit('Diagnostic already executed; no retries/re-runs are permitted')
    payloads = {k: payload(k) for k in kinds}
    plan = {'diagnostic_id': ID, 'provider': 'groq', 'model': MODEL, 'tokenizer': 'tiktoken-0.12.0:o200k_harmony', 'code_commit': git_head(),
            'script_sha256': sha(__file__), 'planned_at': datetime.now(timezone.utc).isoformat(),
            'purpose': 'operational token-accounting and prompt-cache characterisation; not an RQ1/RQ2 experiment',
            'max_calls': 4, 'planned_calls': 3, 'benchmark_content': False,
            'calls': {k: {'request_sha256': content_hash(payloads[k]), 'local_message_tokens': local_tokens(payloads[k]),
                          'local_content_tokens': sum(local_tokens(payloads[k])), 'max_completion_tokens': payloads[k]['max_completion_tokens'],
                          'message_chars': [len(m['content']) for m in payloads[k]['messages']],
                          'system_message_sha256': hashlib.sha256(payloads[k]['messages'][0]['content'].encode()).hexdigest()} for k in kinds},
            'local_common_prefix_tokens_B_vs_C2': common_prefix_tokens(payloads['B'], payloads['C2'])}
    (OUT / 'plan.json').write_text(canonical_json(plan) + '\n', encoding='utf-8', newline='\n')
    print('PLAN', json.dumps({k: v['local_content_tokens'] for k, v in plan['calls'].items()}), 'prefix', plan['local_common_prefix_tokens_B_vs_C2'], flush=True)
    key = groq_key()
    if not key:
        raise SystemExit('Groq credential missing')
    from groq import Groq
    client = Groq(api_key=key, base_url='https://api.groq.com', timeout=60, max_retries=0)

    def sanitize(v):
        s = str(v).replace(key, '[REDACTED]')
        s = re.sub(r'gsk_[A-Za-z0-9_-]+', '[REDACTED]', s)
        return re.sub(r'\b(?:org|proj)_[A-Za-z0-9_-]+', '[REDACTED_ACCOUNT]', s)

    last = None
    try:
        for n, k in enumerate(kinds, 1):
            if last is not None:
                wait = 90 - (time.time() - last)
                if wait > 0:
                    print('WAIT', round(wait, 1), flush=True); time.sleep(wait)
            p = payloads[k]; started = time.time(); last = started
            row = {'diagnostic_id': ID, 'call': k, 'sequence': n, 'timestamp': datetime.now(timezone.utc).isoformat(),
                   'request_sha256': content_hash(p), 'local_message_tokens': local_tokens(p), 'local_content_tokens': sum(local_tokens(p)),
                   'max_completion_tokens': p['max_completion_tokens']}
            response = None
            try:
                response = client.chat.completions.with_raw_response.create(**p)
                r = response.parse()
                u = r.usage.model_dump() if r.usage else None
                row.update(status='complete', http_status=response.status_code, finish_reason=r.choices[0].finish_reason,
                           content=r.choices[0].message.content, usage=u, elapsed_seconds=time.time() - started,
                           provider_minus_local=(u['prompt_tokens'] - row['local_content_tokens']) if u else None)
            except Exception as exc:
                response = getattr(exc, 'response', None)
                row.update(status='failed', http_status=getattr(exc, 'status_code', None), exception_class=type(exc).__name__,
                           error=sanitize(getattr(exc, 'body', None) or str(exc)), elapsed_seconds=time.time() - started)
            row['headers'] = {a.lower(): sanitize(b) for a, b in response.headers.items() if 'ratelimit' in a.lower() or a.lower() in ('retry-after', 'date')} if response is not None else {}
            (OUT / f'call_{n:02d}_{k}.json').write_text(canonical_json(row) + '\n', encoding='utf-8', newline='\n')
            print('CALL', k, row['status'], row.get('http_status'), row.get('usage'), flush=True)
            if row['status'] != 'complete':
                print('STOP: no retries', flush=True); break
    finally:
        client.close()


if __name__ == '__main__':
    main()
