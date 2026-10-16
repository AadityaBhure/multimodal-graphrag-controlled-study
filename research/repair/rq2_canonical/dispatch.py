"""RQ2 dispatcher: the RQ1 revision-4 Dispatcher (unchanged, frozen for RQ1) plus a shared-quota view.

Groq's 200k tokens/day limit is per organisation, but each study keeps its own local ledger. RQ2 runs right after RQ3,
so its rolling 24 h window also counts the provider tokens recorded by other studies' ledgers (read-only). This only
delays dispatch; it never changes a payload.
"""
import json
import time
from pathlib import Path
from research.repair import dispatch as base

WINDOW = base.WINDOW_SECONDS


def external_entries(paths, now):
    """[(timestamp, tokens)] from other studies' ledgers within the last 24 h. Missing files contribute nothing."""
    out = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        state = json.loads(p.read_text(encoding='utf-8'))
        for e in state.get('ledger', []):
            ts, tok = (e[0], e[1]) if isinstance(e, (list, tuple)) else (e.get('t'), e.get('tokens'))
            if ts is not None and ts > now - WINDOW:
                out.append((ts, tok or 0))
    return out


class SharedQuotaDispatcher(base.Dispatcher):
    def __init__(self, root, initial_headers, max_requests, external_ledgers=()):
        super().__init__(root, initial_headers, max_requests)
        self.external_ledgers = tuple(external_ledgers)

    def call(self, stage, system, user, seed, cap):
        now = time.time()
        used = sum(t for _, t in external_entries(self.external_ledgers, now))
        own = self.daily_budget
        try:
            self.daily_budget = own - used           # the inherited rolling-window check sees the shared usage
            return super().call(stage, system, user, seed, cap)
        finally:
            self.daily_budget = own
