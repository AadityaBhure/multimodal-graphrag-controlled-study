"""Hash the additive Phase 8 review package without touching prior artifacts."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.evaluation.benchmark import digest
from research.experiments.runner import write

def main():
    paths = []
    for root in ('research/rq2', 'configs/rq2', 'documentation/phase8'):
        paths.extend(p for p in (ROOT / root).rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix not in ('.lock', '.log') and p.name != 'review_manifest.json')
    paths.extend((ROOT / 'scripts').glob('*phase8*.py'))
    paths.extend(ROOT / p for p in ('fusion_review_app.py', 'tests/test_rq2.py',
        'documentation/Phase_Reports/Phase_08_RQ2_Cross_Modal_Fusion.md'))
    rows = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(set(paths))]
    manifest = {'phase': '8', 'files': rows, 'file_count': len(rows),
        'total_bytes': sum(r['bytes'] for r in rows), 'generation_status': 'approved_bounded_sample_executed_with_rate_limit_errors',
        'approved_phase7_checkpoint': '2600275b90c1943202004b69452f8f7dcf841aee'}
    write(ROOT / 'documentation/phase8/review_manifest.json', manifest)
    print('Review package:', len(rows), 'files;', manifest['total_bytes'], 'bytes')

if __name__ == '__main__': main()
