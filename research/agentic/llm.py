"""Durable, paced, single-in-flight LLM client for Phase 9 controllers and the shared final generator.

* Stage identity = SHA-256 of the full request payload (model, params, messages, seed). A completed
  stage is reused byte-for-byte: temperature 0 + fixed seed make the call a deterministic function of
  its payload, so an identical payload issued by another policy (or after a resume) costs no new call.
  Every *logical* call is still counted with the originally recorded usage and latency.
* Admission (operational, never scientific): local o200k_harmony content tokens + 128 provider-overhead
  reserve must fit the 8,000 TPM bucket; the completion cap is sent unchanged and is not charged at
  admission (groq-admission-probe-v1). Pacing waits on response headers; waiting is recorded separately
  as `wait_ms` and is never part of intrinsic latency.
* A 429/other provider failure is persisted and raises `ProviderPause` (BaseException) so the runner stops
  cleanly and resumes later; nothing is silently retried and no output is fabricated. A rate-limited stage
  produced no model output and is resent later as the byte-identical payload.
* Daily quota (operational): Groq does not expose its 200k tokens/day limit in headers, so a local ROLLING
  24-hour ledger pauses before a request (content + reserve + full cap) could cross the daily budget. Each
  completed call is charged max(provider total_tokens, observed minute-bucket debit) (same rule as RQ1 rev. 3).
* replay_only: after the query-major prefetch, the runner replays stored responses; a payload without a
  completed stored response raises ProviderPause instead of being sent (proves replayed payloads were sent).
"""
from datetime import datetime, timezone
from pathlib import Path
import json, re, time
import tiktoken
from filelock import FileLock
from research.common.serialization import canonical_json, content_hash
from research.experiments.config import durable_write

MODEL = 'openai/gpt-oss-120b'
OVERHEAD_RESERVE = 128
TPM_LIMIT = 8000
TPD_SAFETY = 190_000          # rolling 24 h; stop before the 200,000 tokens/day organisation limit
WINDOW_S = 86_400
ENC = tiktoken.get_encoding('o200k_harmony')


class ProviderPause(BaseException):
    """Operational pause (quota/provider). The durable record is preserved; resume continues."""


def duration(value):
    if value is None:
        return None
    value = str(value)
    if re.fullmatch(r'\d+(?:\.\d+)?', value):
        return float(value)
    parts = re.findall(r'(\d+(?:\.\d+)?)(ms|s|m|h|d)', value)
    if ''.join(a + b for a, b in parts) != value:
        return None
    return sum(float(n) * {'ms': .001, 's': 1, 'm': 60, 'h': 3600, 'd': 86400}[u] for n, u in parts)


def count_tokens(text):
    return len(ENC.encode(text, disallowed_special=()))


class LLMResult:
    __slots__ = ('raw', 'usage', 'finish_reason', 'latency_ms', 'wait_ms', 'reused', 'stage_id', 'role')

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def counters(self):
        u = self.usage or {}
        return {'llm_calls': 1, 'input_tokens': u.get('prompt_tokens'), 'output_tokens': u.get('completion_tokens'),
                'generation_ms': self.latency_ms}


class DurableLLM:
    """transport(payload) -> (raw_text, usage_dict, finish_reason, headers_dict); injectable for offline tests."""

    model = MODEL

    def __init__(self, root, transport=None, clock=time.time, sleep=time.sleep, initial_headers=None, min_spacing_s=2.5, daily_budget=TPD_SAFETY, local=False):
        self.root = Path(root); (self.root / 'stages').mkdir(parents=True, exist_ok=True)
        if local:
            # Local model (research/local_llm.py): same request/response contract; no provider quota or pacing.
            from research.local_llm import chat as local_chat, LOCAL_MODEL
            transport, self.model, min_spacing_s, daily_budget = local_chat, LOCAL_MODEL, 0., 10 ** 12
        self.local = local
        self.clock, self.sleep, self.min_spacing = clock, sleep, min_spacing_s
        self.state_path = self.root / 'state.json'
        self.transport = transport or self._groq_transport()
        self.initial_headers = initial_headers or {}
        self.daily_budget = daily_budget
        self.replay_only = False
        self.key = None

    # ------------------------------------------------------------------ transport
    def _groq_transport(self):
        from research.baselines.config import groq_key
        key = groq_key()
        if not key:
            raise ProviderPause('Groq credential missing')
        self.key = key
        from groq import Groq
        client = Groq(api_key=key, base_url='https://api.groq.com', timeout=90, max_retries=0)

        def call(payload):
            response = client.chat.completions.with_raw_response.create(**payload)
            r = response.parse()
            usage = r.usage.model_dump() if r.usage else None
            return (r.choices[0].message.content or '', usage, r.choices[0].finish_reason,
                    {k.lower(): v for k, v in response.headers.items() if 'ratelimit' in k.lower() or k.lower() in ('retry-after', 'date')})
        return call

    def _sanitize(self, value):
        s = str(value)
        if self.key:
            s = s.replace(self.key, '[REDACTED]')
        s = re.sub(r'gsk_[A-Za-z0-9_-]+', '[REDACTED]', s)
        return re.sub(r'\b(?:org|proj)_[A-Za-z0-9_-]+', '[REDACTED_ACCOUNT]', s)

    # ------------------------------------------------------------------ state
    def _state(self):
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding='utf-8'))
        return {'headers': self.initial_headers, 'observed': 0., 'last_start': 0., 'requests': 0, 'ledger': []}

    def _save(self, state):
        durable_write(self.state_path, canonical_json(state) + '\n')

    @staticmethod
    def payload(role, system, user, cap, seed, json_mode=True, model=MODEL):
        p = {'model': model, 'temperature': 0, 'seed': seed, 'max_completion_tokens': cap, 'reasoning_effort': 'low',
             'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}
        if json_mode:
            p['response_format'] = {'type': 'json_object'}
        return p

    # ------------------------------------------------------------------ call
    def chat(self, role, system, user, cap, seed, json_mode=True):
        if getattr(self, 'local', False):
            from research.local_llm import LOCAL_CAP
            cap = LOCAL_CAP                                  # local backend: one cap for every role
        payload = self.payload(role, system, user, cap, seed, json_mode, self.model)
        identity = content_hash(payload); path = self.root / 'stages' / (identity + '.json')
        with FileLock(str(self.root / 'llm.lock'), timeout=0):
            if path.exists():
                old = json.loads(path.read_text(encoding='utf-8'))
                if old['status'] == 'complete':
                    return LLMResult(raw=old['raw'], usage=old['usage'], finish_reason=old['finish_reason'], latency_ms=old['latency_ms'],
                                     wait_ms=0., reused=True, stage_id=identity, role=role)
                if old['status'] != 'rate_limited':
                    raise ProviderPause('Ambiguous or failed stage requires review (no silent retry): ' + identity)
            if self.replay_only:
                raise ProviderPause('Replay found no completed provider response for this exact payload: ' + identity)
            state = self._state(); headers = state['headers']
            limit = min(TPM_LIMIT, int(headers.get('x-ratelimit-limit-tokens', TPM_LIMIT)))
            tokens = sum(count_tokens(m['content']) for m in payload['messages']); need = tokens + OVERHEAD_RESERVE
            if need > limit:
                raise ProviderPause(f'Unchanged request needs {need} pre-dispatch tokens > {limit}; cannot be repaired by waiting')
            now = self.clock(); window = [e for e in state.get('ledger', []) if e[0] > now - WINDOW_S]
            used = sum(e[1] for e in window)
            if used + need + cap > self.daily_budget:
                resume = datetime.fromtimestamp(min(e[0] for e in window) + WINDOW_S, timezone.utc).isoformat() if window else 'now'
                raise ProviderPause(f'Daily token budget: {used} tokens in the last 24 h + {need + cap} needed > {self.daily_budget}; resume after {resume}')
            target = state['last_start'] + self.min_spacing
            remaining = headers.get('x-ratelimit-remaining-tokens')
            if remaining is not None and int(remaining) < need:
                reset = duration(headers.get('x-ratelimit-reset-tokens'))
                target = max(target, state['observed'] + (reset if reset is not None else 60.) + 1)
            if headers.get('x-ratelimit-remaining-requests') is not None and int(headers['x-ratelimit-remaining-requests']) < 1:
                reset = duration(headers.get('x-ratelimit-reset-requests'))
                target = max(target, state['observed'] + (reset if reset is not None else 3600.) + 1)
            retry = duration(headers.get('retry-after'))
            if retry is not None:
                target = max(target, state['observed'] + retry + 1)
            waited = 0.
            now = self.clock()
            if now < target:
                waited = target - now; self.sleep(waited)
            started = self.clock(); state['requests'] += 1; state['last_start'] = started
            row = {'role': role, 'identity': identity, 'status': 'dispatched', 'payload': payload, 'content_tokens': tokens,
                   'pre_dispatch_tokens': need, 'timestamp': datetime.now(timezone.utc).isoformat(), 'wait_ms': waited * 1000,
                   'daily_window_tokens_before': used}
            durable_write(path, canonical_json(row) + '\n'); self._save(state)
            t0 = time.perf_counter()
            try:
                raw, usage, finish, resp_headers = self.transport(payload)
                latency = (time.perf_counter() - t0) * 1000
                if getattr(self, 'local', False) and usage and usage.get('server_ms') is not None:
                    latency = usage['server_ms']           # local: model compute time (excludes thermal breaks / HTTP)
                row.update(status='complete', raw=raw, usage=usage, finish_reason=finish, latency_ms=latency, headers=resp_headers)
                try: debit = limit - int(resp_headers.get('x-ratelimit-remaining-tokens'))
                except (TypeError, ValueError): debit = 0
                row['daily_ledger_tokens'] = max((usage or {}).get('total_tokens') or need + cap, debit)
            except Exception as exc:
                latency = (time.perf_counter() - t0) * 1000
                code = getattr(exc, 'status_code', None)
                resp_headers = {k.lower(): self._sanitize(v) for k, v in (getattr(getattr(exc, 'response', None), 'headers', None) or {}).items()
                                if 'ratelimit' in k.lower() or k.lower() in ('retry-after', 'date')}
                row.update(status='rate_limited' if code == 429 else 'failed', http_status=code, exception_class=type(exc).__name__,
                           error=self._sanitize(getattr(exc, 'body', None) or str(exc)), latency_ms=latency, headers=resp_headers)
            state.update(headers=row.get('headers') or headers, observed=self.clock())
            state['ledger'] = [e for e in state.get('ledger', []) if e[0] > self.clock() - WINDOW_S] + [[started, row.get('daily_ledger_tokens', 0)]]
            durable_write(path, canonical_json(row) + '\n'); self._save(state)
            (self.root / 'attempts').mkdir(exist_ok=True)
            durable_write(self.root / 'attempts' / f"{state['requests']:06d}.json", canonical_json(row) + '\n')
            if row['status'] != 'complete':
                raise ProviderPause(f"Stage {row['status']} ({row.get('http_status')}); durable record preserved: {identity}")
            return LLMResult(raw=row['raw'], usage=row['usage'], finish_reason=row['finish_reason'], latency_ms=row['latency_ms'],
                             wait_ms=waited * 1000, reused=False, stage_id=identity, role=role)
