"""One model-list request and at most one tiny completion; never retry or overwrite."""
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.baselines.config import groq_key
from research.evaluation.benchmark import digest

D = ROOT / 'documentation/groq_diagnostic'
MODEL = 'openai/gpt-oss-120b'

def now():
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()

def main():
    from groq import Groq
    D.mkdir(exist_ok=True)
    # Exclusive guard persists even if interrupted. Never re-probe automatically.
    with (D / 'probe_started.json').open('x', encoding='utf-8') as f:
        json.dump({'timestamp': now(), 'maximum_chat_requests': 1}, f)
    protected = {str(p.relative_to(ROOT)): digest(p) for folder in ('documentation/phase8', 'configs/rq2', 'research/rq2')
        for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    key = groq_key()
    def clean(value):
        if isinstance(value, dict): return {k: clean(v) for k, v in value.items()}
        if isinstance(value, list): return [clean(v) for v in value]
        if not isinstance(value, str): return value
        value = value.replace(key, '[REDACTED]') if key else value
        value = re.sub(r'gsk_[A-Za-z0-9_-]+', '[REDACTED_KEY]', value)
        return re.sub(r'\b(?:org|proj)_[A-Za-z0-9_-]+', '[REDACTED_ACCOUNT_ID]', value)
    def headers(response):
        return {k.lower(): clean(v) for k, v in response.headers.items()
            if 'ratelimit' in k.lower() or 'rate-limit' in k.lower() or k.lower() in ('retry-after', 'date')}
    def call(fn, kind):
        row = {'timestamp': now(), 'model_id': MODEL, 'request': kind}
        try:
            response = fn()
            parsed = response.parse()
            row.update(http_status=response.status_code, exception_class=None, error=None, headers=headers(response))
            if kind == 'models.list':
                row['target_model_listed'] = any(m.id == MODEL for m in parsed.data)
            else:
                row['usage'] = parsed.usage.model_dump(mode='json') if parsed.usage else None
                row['finish_reasons'] = [c.finish_reason for c in parsed.choices]
                row['returned_model_id'] = parsed.model
        except Exception as exc:
            response = getattr(exc, 'response', None)
            body = getattr(exc, 'body', None)
            row.update(http_status=getattr(exc, 'status_code', None), exception_class=type(exc).__name__,
                error=clean(body if body is not None else str(exc)), headers=headers(response) if response is not None else {})
        row['retry_after'] = row['headers'].get('retry-after')
        row['finished_at'] = now()
        (D / (kind.replace('.', '_') + '.json')).write_text(json.dumps(row, indent=2), encoding='utf-8')
        return row
    result = {'timestamp': now(), 'credential_exists': bool(key), 'max_retries': 0, 'chat_requests': 0}
    if key:
        with Groq(api_key=key, base_url='https://api.groq.com', timeout=30, max_retries=0) as client:
            result['models'] = call(client.models.with_raw_response.list, 'models.list')
            if result['models']['http_status'] not in (401, 403):
                result['chat_requests'] = 1
                result['tiny_request_settings'] = {'model': MODEL, 'messages': [{'role': 'user', 'content': 'Hi'}],
                    'max_completion_tokens': 1, 'temperature': 0, 'reasoning_effort': 'low'}
                result['completion'] = call(lambda: client.chat.completions.with_raw_response.create(**result['tiny_request_settings']), 'chat.completions')
    assert all(digest(ROOT / p) == sha for p, sha in protected.items()), 'Protected Phase 8 artifact changed'
    result['protected_phase8_files_verified'] = len(protected)
    (D / 'diagnostic.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
