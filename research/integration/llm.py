"""RQ4 LLM client: the frozen Phase 9 DurableLLM plus (a) read-only reuse of byte-identical completed stages from earlier
studies (the RQ3 run of the same policy) and (b) a shared-quota view of other studies' rolling 24 h ledgers.

Reuse is the frozen client's own rule (stage identity = SHA-256 of the full payload; temperature 0 + fixed seed): an
identical payload already answered costs no new call and keeps its original usage and latency. Nothing is written to
the other studies' stores.
"""
import json
import time
from pathlib import Path
from research.common.serialization import content_hash
from research.agentic.llm import DurableLLM, LLMResult, WINDOW_S


class ReusingSharedQuotaLLM(DurableLLM):
    def __init__(self, root, reuse_roots=(), external_ledgers=(), **kw):
        super().__init__(root, **kw)
        self.reuse_roots = tuple(Path(r) for r in reuse_roots)
        self.external_ledgers = tuple(Path(p) for p in external_ledgers)
        self.reused_external = 0

    def _external_used(self):
        now, used = self.clock(), 0
        for p in self.external_ledgers:
            if p.exists():
                for e in json.loads(p.read_text(encoding='utf-8')).get('ledger', []):
                    if e[0] > now - WINDOW_S:
                        used += e[1]
        return used

    def chat(self, role, system, user, cap, seed, json_mode=True):
        payload = self.payload(role, system, user, cap, seed, json_mode)
        identity = content_hash(payload)
        if not (self.root / 'stages' / (identity + '.json')).exists():
            for root in self.reuse_roots:
                p = root / 'stages' / (identity + '.json')
                if p.exists():
                    old = json.loads(p.read_text(encoding='utf-8'))
                    if old.get('status') == 'complete':
                        self.reused_external += 1
                        return LLMResult(raw=old['raw'], usage=old['usage'], finish_reason=old['finish_reason'], latency_ms=old['latency_ms'],
                                         wait_ms=0., reused=True, stage_id=identity, role=role)
        own = self.daily_budget
        try:
            self.daily_budget = own - self._external_used()
            return super().chat(role, system, user, cap, seed, json_mode)
        finally:
            self.daily_budget = own
