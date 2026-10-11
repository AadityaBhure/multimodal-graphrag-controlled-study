"""Freeze approved B4 evidence once, with read-only canonical lookup for resolution."""
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.common.contracts import RetrievalBundle
from research.common.serialization import canonical_json, content_hash
from research.evaluation.benchmark import BenchmarkReader, digest
from research.evaluation.contracts import RunRecord
from research.experiments.runner import write, labels
from research.rq2.contracts import FrozenInput, SOURCES
from research.rq2.fusion import normalize
from scripts.audit_stark_mag import process_memory

D = ROOT / 'documentation/phase8'

def immutable_write(path, value):
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != value:
            raise ValueError('Refusing incompatible artifact: ' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        write(path, value)

def load_inputs():
    manifest = json.loads((D / 'bundle_manifest.json').read_text(encoding='utf-8'))
    inputs = {}
    for row in manifest['files']:
        path = D / row['path']
        if digest(path) != row['sha256']:
            raise ValueError('Frozen input checksum mismatch')
        item = FrozenInput.model_validate_json(path.read_text(encoding='utf-8'))
        if item.fingerprint() != row['fingerprint'] or item.bundle.bundle_hash() != row['bundle_hash']:
            raise ValueError('Frozen input identity mismatch')
        inputs[item.bundle.query_id] = item
    return inputs

def main():
    import duckdb
    started = time.perf_counter()
    reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
    queries = sorted((q for q in reader.records('validation') if q.provenance['source'] == 'generated'
        and q.modality_class in ('TG', 'TS', 'GS', 'TGS') and not q.stress.unanswerable), key=lambda q: q.query_id)
    assert len(queries) == 24 and all(labels(q).status == 'programmatically_verified' for q in queries)
    connection = duckdb.connect(config={'memory_limit': '256MB', 'threads': 2})
    canonical = ROOT / 'data/MMG_STARK_MAG/canonical/canonical_entities.parquet'
    registry = ROOT / 'data/MMG_STARK_MAG/canonical/alias_registry.parquet'
    rows = []
    try:
        for q in queries:
            source = ROOT / 'documentation/phase6_closeout/runs/B4/records' / (content_hash(q.query_id) + '.json')
            record = RunRecord.model_validate_json(source.read_text(encoding='utf-8'))
            assert not record.errors and record.query_id == q.query_id and record.split == 'validation'
            original = record.output.evidence
            bundle = RetrievalBundle(query_id=q.query_id, **{s + '_evidence': tuple(e for e in original if e.source_type == s) for s in SOURCES})
            ids = sorted({e.canonical_id for e in original})
            known = tuple(r[0] for r in connection.execute('SELECT canonical_id FROM read_parquet(?) WHERE canonical_id IN (SELECT unnest(?)) ORDER BY canonical_id', [str(canonical), ids]).fetchall())
            aliases = set()
            for e in original:
                p = json.loads(e.payload) if e.payload else {}
                m = json.loads(e.metadata)
                alias = p.get('title') or p.get('display_name') or m.get('alias')
                if isinstance(alias, str): aliases.add(normalize(alias))
            # Global exact match lookup retains all collisions, not only candidate-local names.
            alias_rows = connection.execute('SELECT alias,canonical_id FROM read_parquet(?) WHERE alias IN (SELECT unnest(?)) ORDER BY alias,canonical_id', [str(registry), sorted(aliases)]).fetchall() if aliases else []
            mapping = {}
            for alias, cid in alias_rows: mapping.setdefault(alias, []).append(cid)
            overlay = reader.overlay(q)
            frozen = FrozenInput(question=q.question, bundle=bundle,
                overlay_hash=content_hash(overlay) if overlay else None, canonical_ids=known,
                aliases=tuple((a, tuple(v)) for a, v in mapping.items()),
                provenance=canonical_json({'source_record': source.relative_to(ROOT).as_posix(),
                    'source_sha256': digest(source), 'original_retrieval_observation': record.observation.model_dump(mode='json'),
                    'benchmark_manifest_sha256': reader.manifest_hash,
                    'representation_manifest_sha256': reader.manifest['representation_manifest_sha256'],
                    'original_retrieval_parameters': record.retrieval_parameters,
                    'canonical_registry_sha256': digest(canonical), 'alias_registry_sha256': digest(registry),
                    'retrieval_bundle_timings': 'default zeros denote replay; measured original observation stored separately'}))
            path = D / 'bundles' / (content_hash(q.query_id) + '.json')
            immutable_write(path, frozen.model_dump(mode='json'))
            rows.append({'query_id': q.query_id, 'path': path.relative_to(D).as_posix(), 'sha256': digest(path),
                'fingerprint': frozen.fingerprint(), 'bundle_hash': bundle.bundle_hash(), 'evidence_count': len(original)})
        immutable_write(D / 'bundle_manifest.json', {'files': rows, 'selection': 'all 24 verified generated validation TG/TS/GS/TGS normal/noisy/conflict', 'no_new_retrieval': True})
        write(D / 'preparation_resources.json', {'seconds': time.perf_counter() - started, 'memory': process_memory(), 'api_calls': 0})
        print('Frozen', len(rows), 'inputs; no retrieval or API calls')
    finally:
        connection.close()

if __name__ == '__main__': main()
