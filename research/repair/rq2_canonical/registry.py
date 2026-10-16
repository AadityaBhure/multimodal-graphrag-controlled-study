"""Read-only canonical-entity registry lookup for the frozen RQ2 inputs (entity type and display name). Not retrieval."""
from pathlib import Path

CANONICAL = Path(__file__).resolve().parents[3] / 'data/MMG_STARK_MAG/canonical/canonical_entities.parquet'


def load_registry(inputs, path=CANONICAL):
    import duckdb
    ids = sorted({e.canonical_id for f in inputs.values() for s in ('text', 'graph', 'structured') for e in getattr(f.bundle, s + '_evidence')}
                 | {c for f in inputs.values() for _, cands in f.aliases for c in cands})
    con = duckdb.connect(config={'memory_limit': '256MB', 'threads': 2})
    try:
        rows = con.execute('SELECT canonical_id, entity_type, display_name FROM read_parquet(?) WHERE canonical_id IN (SELECT unnest(?))',
                           [str(path), ids]).fetchall()
    finally:
        con.close()
    return {cid: {'entity_type': t, 'display_name': n} for cid, t, n in rows}
