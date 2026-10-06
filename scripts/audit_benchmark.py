"""Recompute Phase 4 gold and provenance; no evaluation implementation."""
import argparse
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.benchmark.contracts import load_benchmark_config
from research.benchmark.source import Source
from research.benchmark.build import write
from research.benchmark.audit import audit,statistics
from scripts.audit_stark_mag import process_memory
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='data/MMG_STARK_MAG/benchmark');a=p.parse_args()
    start=time.perf_counter();s=Source(load_benchmark_config('configs/phase4.yaml'))
    preserved=s.verify();queries,result=audit(s,Path(a.output));stats=statistics(s,queries,Path(a.output))
    write(Path(a.output)/'benchmark_stats.json',stats)
    assert s.verify()==preserved
    write(Path('documentation/phase4/audit_resources.json'),{'elapsed_seconds':time.perf_counter()-start,'resources':process_memory(),'preservation':preserved})
    print(result);print(stats['split']);s.close()
