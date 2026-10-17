"""Read-only canonical-entity lookup (entity type, display name) for the INT-1 fusion stage. Not retrieval."""
from pathlib import Path

CANONICAL = Path(__file__).resolve().parents[2] / 'data/MMG_STARK_MAG/canonical/canonical_entities.parquet'


def lookup(ids, path=CANONICAL):
    import duckdb
    con = duckdb.connect(config={'memory_limit': '256MB', 'threads': 2})
    try:
        rows = con.execute('SELECT canonical_id, entity_type, display_name FROM read_parquet(?) WHERE canonical_id IN (SELECT unnest(?))',
                           [str(path), sorted(ids)]).fetchall() if ids else []
    finally:
        con.close()
    return {cid: {'entity_type': t, 'display_name': n} for cid, t, n in rows}
