"""Verify byte-identical incoming evidence, metrics and all approved artifacts."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_phase8 import D, load_inputs
from scripts.audit_phase5_preservation import audit, git
from research.rq2.contracts import METHODS, SOURCES, evidence
from research.evaluation.benchmark import BenchmarkReader, digest
from research.evaluation.contracts import RunRecord
from research.experiments.config import load_runner_config
from research.experiments.runner import compute_metrics, write

def main():
    inputs = load_inputs()
    queries = {q.query_id: q for q in BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark').records('validation')}
    checked = 0
    for mode in ('context_only', 'generation'):
        for method in METHODS:
            path = D / mode / method / 'records.jsonl'
            if not path.exists(): continue
            config = load_runner_config(ROOT / 'configs/rq2' / (method + '-' + mode + '.json'))
            for line in path.read_text(encoding='utf-8').splitlines():
                r = RunRecord.model_validate_json(line)
                frozen = inputs[r.query_id]
                d = json.loads(r.output.diagnostics)
                assert r.split == 'validation' and r.source_type == 'generated' and r.labels.status == 'programmatically_verified'
                assert r.output.evidence == evidence(frozen)
                original = json.loads(frozen.provenance)
                source = ROOT / original['source_record']
                assert digest(source) == original['source_sha256']
                upstream = RunRecord.model_validate_json(source.read_text(encoding='utf-8'))
                # B4 appends overlays after the cross-source base list. RetrievalBundle
                # partitions by source, retaining exact within-source order and fields.
                assert {e.evidence_id: e for e in upstream.output.evidence} == {e.evidence_id: e for e in evidence(frozen)}
                for source_type in SOURCES:
                    assert tuple(e for e in upstream.output.evidence if e.source_type == source_type) == getattr(frozen.bundle, source_type + '_evidence')
                assert d['bundle_hash'] == frozen.bundle.bundle_hash() and d['input_fingerprint'] == frozen.fingerprint() and d['input_unchanged']
                assert r.observation.retrieval_calls == 0 and r.observation.tool_calls == 0
                assert r.metrics == compute_metrics(queries[r.query_id], r.output, config, r.total_latency_ms)
                assert r.output.context is None or len(r.output.context) <= 24000
                if mode == 'context_only': assert not r.errors and r.observation.llm_calls == 0 and r.answer is None
                checked += 1
    assert checked >= 120
    previous = json.loads((ROOT / 'documentation/phase7/review_manifest.json').read_text(encoding='utf-8'))
    for row in previous['files']:
        path = ROOT / row['path']
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], path
    assert git('rev-parse', 'HEAD') == '2600275b90c1943202004b69452f8f7dcf841aee'
    assert not git('diff', 'HEAD', '--name-only'), 'Previously checkpointed file modified'
    result = audit()
    result['phase7_checkpoint'] = result.pop('phase4_checkpoint')
    result.update(rq2_records_recomputed=checked, byte_identical_evidence_all_variants=True,
        phase7_review_files_verified=len(previous['files']), all_checkpointed_files_unchanged=True,
        no_tuning=True, no_test_or_human_test_execution=True)
    write(D / 'preservation.json', result)
    print('PASS:', checked, 'records; all original source evidence and protected artifacts unchanged')

if __name__ == '__main__': main()
