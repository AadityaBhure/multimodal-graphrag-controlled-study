"""Train the AR-01 t5-base route classifier on the frozen train partition; dev-loss early stopping (addendum §2.2)."""
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.evaluation.benchmark import BenchmarkReader
from research.agentic.ar01_model import train, HYPER

LITE = '--lite' in sys.argv

def main(threads=10):
    labels = json.loads(((ROOT / 'artifacts/phase9/lite/labels.json') if LITE else (ROOT / 'documentation/phase9/ar01/labels.json')).read_text(encoding='utf-8'))
    recs = {q.query_id: q.question for q in BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark').records('train')}
    pairs = {s: [(recs[q], v['label']) for q, v in sorted(labels['labels'].items()) if v['split'] == s] for s in ('train', 'dev')}
    model_dir = ROOT / 'artifacts/phase9/models/t5-base'
    report = train(model_dir, pairs['train'], pairs['dev'], ROOT / ('artifacts/phase9/lite/ar01' if LITE else 'artifacts/phase9/ar01'), threads=threads, log=print, max_epochs=2 if LITE else None)
    report['lite'] = LITE
    report['t5_revision'] = 'a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1'
    report['labels_sha256'] = labels['labels_sha256']; report['partition_sha256'] = labels['partition_sha256']
    import torch, transformers
    report['environment'] = {'torch': torch.__version__, 'transformers': transformers.__version__, 'device': report['device'], 'gpu': report['gpu'], 'dtype': 'float32', 'threads': threads}
    rp = (ROOT / 'artifacts/phase9/lite/ar01_training_report.json') if LITE else (ROOT / 'documentation/phase9/ar01/training_report.json')
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('best epoch', report['best_epoch'], report['stopped'])

if __name__ == '__main__':
    nums = [a for a in sys.argv[1:] if a.isdigit()]
    main(int(nums[0]) if nums else 10)
