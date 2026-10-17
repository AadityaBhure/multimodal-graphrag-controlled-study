"""Local model backend (Ollama) behind the same request/response contract as the Groq client.

Requests keep the frozen shape {model, temperature, seed, max_completion_tokens, reasoning_effort, response_format,
messages}; this module maps them to Ollama's native /api/chat (format json, think level, temperature, seed, num_predict)
and returns the same fields the studies record (content, finish reason, prompt/completion token usage). No rate limits
apply locally, so the response carries non-binding rate-limit headers.
"""
from types import SimpleNamespace
import subprocess
import time
import httpx

LOCAL_MODEL = 'gpt-oss:20b'
OLLAMA_URL = 'http://127.0.0.1:11434'
NUM_CTX = 16384
NO_LIMIT_HEADERS = {'x-ratelimit-limit-tokens': '8000', 'x-ratelimit-remaining-tokens': '8000', 'x-ratelimit-remaining-requests': '999'}


def _request(payload):
    body = {'model': payload['model'], 'messages': payload['messages'], 'stream': False,
            'options': {'temperature': payload.get('temperature', 0), 'seed': payload.get('seed'), 'num_predict': payload.get('max_completion_tokens'),
                        'num_ctx': NUM_CTX}}
    if payload.get('response_format', {}).get('type') == 'json_object':
        body['format'] = 'json'
    if payload.get('reasoning_effort'):
        body['think'] = payload['reasoning_effort']
    return body


HOT_C, COOL_C, BREAK_S = 80, 70, 600
THERMAL_LOG = []


def gpu_temp():
    try:
        return int(subprocess.check_output(['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'], text=True).strip().splitlines()[0])
    except Exception:
        return None


def thermal_guard(sleep=time.sleep):
    """Before a request: at >= 80 C take a 10-minute break, then wait until < 70 C (GPU protection; never inside latency)."""
    t = gpu_temp()
    if t is not None and t >= HOT_C:
        THERMAL_LOG.append({'t': time.time(), 'temp': t}); sleep(BREAK_S)
        while (gpu_temp() or 0) >= COOL_C:
            sleep(30)


def chat(payload, timeout=900):
    """-> (content, usage{prompt_tokens, completion_tokens, total_tokens, server_ms}, finish_reason, headers).

    server_ms = model compute time reported by Ollama (prompt evaluation + generation, excluding model loading); the
    clients record it as the call latency, so thermal breaks and HTTP overhead never count as latency."""
    thermal_guard()
    r = httpx.post(OLLAMA_URL + '/api/chat', json=_request(payload), timeout=timeout)
    r.raise_for_status()
    j = r.json()
    pin, pout = j.get('prompt_eval_count'), j.get('eval_count')
    server_ms = ((j.get('prompt_eval_duration') or 0) + (j.get('eval_duration') or 0)) / 1e6
    usage = {'prompt_tokens': pin, 'completion_tokens': pout, 'total_tokens': (pin or 0) + (pout or 0), 'server_ms': server_ms} if pin is not None else None
    return (j.get('message') or {}).get('content') or '', usage, j.get('done_reason') or 'stop', dict(NO_LIMIT_HEADERS)


class LocalClient:
    """Drop-in for groq.Groq used by research/repair/dispatch.Dispatcher (chat.completions.with_raw_response.create)."""
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=self._create)))

    def _create(self, **payload):
        content, usage, finish, headers = chat(payload)
        u = SimpleNamespace(prompt_tokens=usage['prompt_tokens'], completion_tokens=usage['completion_tokens'], server_ms=usage['server_ms']) if usage else None
        result = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)], usage=u)
        return SimpleNamespace(parse=lambda: result, status_code=200, headers=headers)

    def close(self):
        pass
