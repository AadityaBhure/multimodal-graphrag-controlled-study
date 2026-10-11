"""Write the frozen AR-01/AR-02 train/dev partition (train split only; no validation/test access)."""
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.evaluation.benchmark import BenchmarkReader
from research.agentic.partition import build
from research.common.serialization import content_hash, canonical_json

reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
part = build(reader)
part['partition_sha256'] = content_hash({k: part[k] for k in ('version', 'rule', 'train', 'dev')})
part['benchmark_manifest_sha256'] = reader.manifest_hash
out = ROOT / 'documentation/phase9/partition/ar01_partition.json'
if out.exists():
    old = json.loads(out.read_text(encoding='utf-8'))
    assert old['partition_sha256'] == part['partition_sha256'], 'partition changed'
else:
    out.write_text(canonical_json(part) + '\n', encoding='utf-8', newline='\n')
print(len(part['train']), len(part['dev']), part['generated_families'], len(part['generated_families_straddling_train_dev']), part['partition_sha256'][:16])
