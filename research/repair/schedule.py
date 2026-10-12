"""Query-major interleaving of provider calls (RQ1 operational revision 4).

The frozen Phase 5 runner executes one method for all queries before the next method, so on a
multi-day run different methods would reach the provider on different days. To keep any provider
drift balanced across methods, the provider calls are made first in query-major order (all five
methods for query 1, then query 2, ...) by executing the unchanged frozen systems; the dispatcher
stores every response durably by payload identity. The unchanged runner then replays them with the
dispatcher in replay-only mode, which refuses (and stops) if any payload differs from the one sent,
so the recorded experiment is byte-for-byte the one that reached the provider.
"""
from datetime import datetime, timezone
from pathlib import Path
from research.common.serialization import canonical_json, content_hash
from research.experiments.config import durable_write


def interleaved(query_ids, methods):
    """Query-major order; queries sorted exactly as the runner sorts them within one split."""
    return [(q, m) for q in sorted(query_ids) for m in methods]


def prefetch(order, execute, done_dir, log=print):
    """Run execute(query_id, method) once per pair in order; skip pairs already done (resumable).

    Provider pauses (BaseException) propagate and stop the run. Any other exception is recorded and the
    run continues: it is deterministic code behaviour that the runner reproduces identically on replay.
    """
    done_dir = Path(done_dir)
    for query_id, method in order:
        marker = done_dir / method / (content_hash(query_id) + '.json')
        if marker.exists():
            continue
        try:
            execute(query_id, method)
            outcome = 'executed'
        except Exception as exc:
            outcome = 'exception:' + type(exc).__name__
        marker.parent.mkdir(parents=True, exist_ok=True)
        durable_write(marker, canonical_json({'query_id': query_id, 'method': method, 'outcome': outcome,
                                              'timestamp': datetime.now(timezone.utc).isoformat()}) + '\n')
        log('PREFETCH', method, query_id, outcome)
