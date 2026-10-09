"""Download only the explicitly approved pinned reranker and verify recorded hashes."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from huggingface_hub import snapshot_download
from research.evaluation.benchmark import digest
if __name__=='__main__':
    config=json.loads((ROOT/'documentation/phase7/reranker_config.json').read_text(encoding='utf-8'))
    target=ROOT/'artifacts/phase7/reranker'
    snapshot_download(config['model'],revision=config['revision'],allow_patterns=['*.json','*.safetensors','*.model'],local_dir=target)
    manifest=ROOT/'documentation/phase7/reranker_manifest.json'
    if manifest.exists():
        for name,sha in json.loads(manifest.read_text(encoding='utf-8'))['files'].items():assert digest(target/name)==sha,name
    print('Pinned local reranker ready:',target)
