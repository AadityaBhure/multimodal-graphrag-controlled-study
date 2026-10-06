"""Prepare pending human reviews and freeze benchmark content without approving it."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.benchmark.contracts import load_benchmark_config
from research.benchmark.source import Source
from research.benchmark.review import review_package,freeze_manifest
from research.benchmark.build import write
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='data/MMG_STARK_MAG/benchmark');a=p.parse_args()
    s=Source(load_benchmark_config('configs/phase4.yaml'));out=Path(a.output)
    result=review_package(s,out);manifest=freeze_manifest(s,out)
    write(Path('documentation/phase4/benchmark_manifest.json'),manifest)
    print(result);print('Files:',len(manifest['files']),'bytes:',manifest['total_bytes_excluding_manifest']);s.close()
