"""Build a separate complete copy and compare every benchmark byte."""
from pathlib import Path
import sys
import time
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.benchmark.contracts import load_benchmark_config
from research.benchmark.source import Source
from research.benchmark.build import build,write
from research.benchmark.audit import audit,statistics
from research.benchmark.review import review_package,freeze_manifest
from scripts.audit_stark_mag import process_memory,digest

if __name__=='__main__':
    start=time.perf_counter();source=Source(load_benchmark_config('configs/phase4.yaml'))
    original=source.root/'benchmark';replica=source.root/'_build/phase4/regenerated'
    preserved=source.verify();build(source,replica)
    queries,result=audit(source,replica);write(replica/'benchmark_stats.json',statistics(source,queries,replica))
    review_package(source,replica);freeze_manifest(source,replica)
    original_files={p.relative_to(original).as_posix():digest(p) for p in original.rglob('*') if p.is_file()}
    replica_files={p.relative_to(replica).as_posix():digest(p) for p in replica.rglob('*') if p.is_file()}
    assert original_files==replica_files, 'Regeneration differs: '+str([p for p in original_files if original_files[p]!=replica_files.get(p)])
    assert source.verify()==preserved
    write(Path('documentation/phase4/regeneration.json'),{'status':'pass','files_byte_identical':len(original_files),
          'elapsed_seconds':time.perf_counter()-start,'resources':process_memory(),'preservation':preserved,
          'separate_output':replica.relative_to(source.root).as_posix(),'queries':len(queries)})
    print(f'Regeneration passed: {len(original_files)} files byte-identical');source.close()
