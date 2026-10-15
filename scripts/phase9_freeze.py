"""Freeze the Phase 9 execution plan (code, prompts, downstream config, partition, labels, AR-01 model, AR-02 calibration)
BEFORE the primary run on the frozen 28-query cohort (documentation/SCOPE_REVISION_2026-10-15.json). run_phase9.py --mode primary refuses to start if anything below changes."""
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.common.serialization import content_hash, canonical_json
from research.evaluation.benchmark import digest, BenchmarkReader
from research.agentic.prompts import PROMPT_VERSION_HASH
from scripts.run_phase9 import primary_cohort

def main():
    code = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted((ROOT / 'research/agentic').glob('*.py'))}
    for extra in ('scripts/run_phase9.py', 'scripts/phase9_freeze.py', 'research/repair/schedule.py', 'research/baselines/retrieval.py', 'research/baselines/stores.py',
                  'research/baselines/structured.py', 'research/baselines/generation.py', 'research/baselines/system.py'):
        code[extra] = digest(ROOT / extra)
    artifacts = {}
    for rel in ('configs/rq3/fixed_downstream.yaml', 'documentation/phase9/partition/ar01_partition.json', 'documentation/phase9/ar01/labels.json',
                'documentation/phase9/ar01/training_report.json', 'documentation/phase9/calibration/ar02_calibration.json',
                'documentation/phase9/PHASE9_SPEC_CONSISTENCY_AUDIT.md', 'documentation/SCOPE_REVISION_2026-10-15.json'):
        artifacts[rel] = digest(ROOT / rel)
    for p in sorted((ROOT / 'artifacts/phase9/ar01/best').iterdir()):
        artifacts[p.relative_to(ROOT).as_posix()] = digest(p)
    for p in sorted((ROOT / 'artifacts/phase9/models/ms-marco-MiniLM-L-6-v2').iterdir()):
        if p.is_file(): artifacts[p.relative_to(ROOT).as_posix()] = digest(p)
    qids = primary_cohort()
    assert len(qids) == 28
    reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
    plan = {'version': 'phase9-execution-plan-v1', 'implementation_sha256': code, 'artifact_sha256': artifacts, 'prompt_version_hash': PROMPT_VERSION_HASH,
            'primary_cohort': qids, 'scope_revision': 'two-week-scope-v1 (14 families x normal + noisy)',
            'provider_order': 'query-major prefetch, then method-major replay with replay_only', 'primary_cohort_sha256': content_hash(qids), 'benchmark_manifest_sha256': reader.manifest_hash,
            'splits_used_for_training_or_calibration': ['train (frozen partition only)'], 'test_human_test_used': False,
            'stopping_accuracy_definition': 'documentation/phase9/PHASE9_SPEC_CONSISTENCY_AUDIT.md (frozen before any validation outcome)'}
    plan['plan_sha256'] = content_hash({k: v for k, v in plan.items()})
    out = ROOT / 'documentation/phase9/execution_plan.json'
    if out.exists():
        raise SystemExit('execution_plan.json already exists; a changed plan needs an explicit new version')
    out.write_text(canonical_json(plan) + '\n', encoding='utf-8', newline='\n')
    print('FROZEN', plan['plan_sha256'][:16], len(code), 'code files,', len(artifacts), 'artifacts, cohort', len(qids))

if __name__ == '__main__':
    main()
