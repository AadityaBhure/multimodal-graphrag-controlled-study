"""Construct Phase 4 only; no evaluation runner or metrics."""
import argparse
from pathlib import Path
import sys
import time
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.benchmark.contracts import load_benchmark_config
from research.benchmark.source import Source
from research.benchmark.build import build,write
from scripts.audit_stark_mag import process_memory,digest

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/phase4.yaml')
    parser.add_argument('--output',default='data/MMG_STARK_MAG/benchmark')
    args=parser.parse_args();start=time.perf_counter()
    output=Path(args.output)
    if (output/'benchmark_manifest.json').exists():
        existing=json.loads((output/'benchmark_manifest.json').read_text(encoding='utf-8'))
        for artifact in existing['files']:
            assert digest(output/artifact['path'])==artifact['sha256'], 'Frozen benchmark changed; refusing overwrite'
        print('Existing frozen benchmark verified. Use a separate --output directory for regeneration; no files changed.')
        raise SystemExit(0)
    source=Source(load_benchmark_config(args.config))
    preserved=source.verify();print('Frozen source and representations verified',flush=True)
    queries,exclusions,records=build(source,Path(args.output))
    assert source.verify()==preserved
    write(Path('documentation/phase4/build_resources.json'),{'elapsed_seconds':time.perf_counter()-start,'resources':process_memory(),
          'preservation':preserved,'queries':len(queries),'generated_base_instances':len(records),'human_exclusions':len(exclusions)})
    source.close();print(f'Constructed {len(queries)} queries; {len(records)} generated base instances',flush=True)
