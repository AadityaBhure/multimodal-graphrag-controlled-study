"""ONE synthetic Groq admission-semantics probe (identity groq-admission-probe-v1). Not an RQ result.

Test B's synthetic payload (no benchmark content) with max_completion_tokens=7000, so that
prompt (~1,543 provider tokens) + maximum output (7,000) ~= 8,543 > the 8,000 TPM limit.
No retries; refuses to run twice.
"""
from datetime import datetime, timezone
from pathlib import Path
import importlib.util, json, re, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.common.serialization import canonical_json, content_hash
from research.baselines.config import groq_key

spec = importlib.util.spec_from_file_location('acct', ROOT / 'scripts/diagnose_groq_accounting.py')
acct = importlib.util.module_from_spec(spec); spec.loader.exec_module(acct)
OUT = ROOT / 'documentation/rq1_repair/provider_diagnostic'
RESULT = OUT / 'call_04_admission_probe.json'


def main():
    if RESULT.exists() or (OUT / 'admission_probe_pre_dispatch.json').exists():
        raise SystemExit('Probe already dispatched; exactly one call is authorised')
    p = acct.payload('B'); p['max_completion_tokens'] = 7000
    last = json.loads((OUT / 'call_03_C2.json').read_text(encoding='utf-8'))
    idle = (datetime.now(timezone.utc) - datetime.fromisoformat(last['timestamp'])).total_seconds()
    head = subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    pre = {'diagnostic_id': 'groq-admission-probe-v1', 'timestamp': datetime.now(timezone.utc).isoformat(), 'code_commit': head,
           'request_sha256': content_hash(p), 'model': p['model'], 'max_completion_tokens': 7000, 'local_message_tokens': acct.local_tokens(p),
           'expected_provider_prompt_tokens': sum(acct.local_tokens(p)) + 102, 'expected_requested_total': sum(acct.local_tokens(p)) + 102 + 7000,
           'last_known_headers': last['headers'], 'last_known_call_timestamp': last['timestamp'], 'seconds_since_last_provider_call': idle,
           'bucket_note': 'Token bucket refills 8,000/min; the last response showed reset-tokens 11.76 s; idle time is far above 60 s, so the bucket is full by the documented refill rule. Groq exposes remaining tokens only on responses; no extra call was spent to read it.',
           'script_sha256': acct.sha(__file__)}
    if idle < 120:
        raise SystemExit('Wait: bucket not provably restored')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'admission_probe_pre_dispatch.json').write_text(canonical_json(pre) + '\n', encoding='utf-8', newline='\n')
    key = groq_key()
    from groq import Groq
    client = Groq(api_key=key, base_url='https://api.groq.com', timeout=60, max_retries=0)

    def sanitize(v):
        s = str(v).replace(key, '[REDACTED]')
        s = re.sub(r'gsk_[A-Za-z0-9_-]+', '[REDACTED]', s)
        return re.sub(r'\b(?:org|proj)_[A-Za-z0-9_-]+', '[REDACTED_ACCOUNT]', s)
    row = {'diagnostic_id': 'groq-admission-probe-v1', 'timestamp': datetime.now(timezone.utc).isoformat(), 'request_sha256': pre['request_sha256']}
    response = None; started = time.time()
    try:
        response = client.chat.completions.with_raw_response.create(**p)
        r = response.parse(); u = r.usage.model_dump() if r.usage else None
        row.update(status='complete', http_status=response.status_code, finish_reason=r.choices[0].finish_reason, content=r.choices[0].message.content, usage=u)
    except Exception as exc:
        response = getattr(exc, 'response', None)
        row.update(status='failed', http_status=getattr(exc, 'status_code', None), exception_class=type(exc).__name__,
                   error=sanitize(getattr(exc, 'body', None) or str(exc)), message=sanitize(str(exc)))
    row['elapsed_seconds'] = time.time() - started
    row['headers'] = {a.lower(): sanitize(b) for a, b in response.headers.items() if 'ratelimit' in a.lower() or a.lower() in ('retry-after', 'date')} if response is not None else {}
    RESULT.write_text(canonical_json(row) + '\n', encoding='utf-8', newline='\n')
    client.close()
    print(json.dumps(row, indent=1))


if __name__ == '__main__':
    main()
