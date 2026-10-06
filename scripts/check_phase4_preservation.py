"""Read-only Phase 4 checks for frozen MVP, environment, data and phase boundary."""
from importlib.metadata import distributions
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.benchmark.source import Source
from research.benchmark.contracts import load_benchmark_config
from research.benchmark.build import write

def git(*args):return subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}',*args],cwd=ROOT)

if __name__=='__main__':
    baseline='4592d102b363c7d55d3c85ee67efe89409ae96b5';checkpoint='3b34d9c234f9861455eea5fc7fd34a939f87518e'
    assert git('rev-parse','baseline-mvp-v1^{commit}').decode().strip()==baseline
    assert git('rev-parse','HEAD').decode().strip()==checkpoint
    protected=[p for p in git('ls-tree','-r','--name-only',baseline).decode().splitlines() if p!='documentation/Research_Decision_Log.md']
    for p in protected:assert git('hash-object',p).strip()==git('rev-parse',baseline+':'+p).strip(),p
    with zipfile.ZipFile(ROOT/'documentation/baseline_phase0/storage_snapshot.zip') as archive:
        for p in archive.namelist():assert (ROOT/p).read_bytes()==archive.read(p),p
        storage=len(archive.namelist())
    pins={line.split('==')[0].lower().replace('_','-'):line.split('==')[1] for line in (ROOT/'documentation/phase3/requirements.freeze.txt').read_text(encoding='utf-8').splitlines() if '==' in line}
    installed={d.metadata['Name'].lower().replace('_','-'):d.version for d in distributions()}
    assert all(installed.get(k)==v for k,v in pins.items())
    result=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True);assert result.returncode==0
    for directory in ('research/evaluation','research/experiments','research/retrieval','research/context','research/fusion','research/agentic'):
        assert not git('diff',checkpoint,'--',directory).strip(),directory
    s=Source(load_benchmark_config(ROOT/'configs/phase4.yaml'));preserved=s.verify();s.close()
    write(ROOT/'documentation/phase4/preservation.json',{'status':'pass','phase3_checkpoint':checkpoint,'clean_immediately_after_checkpoint':True,
          'baseline_commit':baseline,'protected_baseline_files':len(protected),'original_storage_files':storage,'phase3_package_pins_unchanged':len(pins),
          'pip_check':result.stdout.strip(),'new_dependencies':0,'phase5_or_later_modules_changed':False,**preserved,'free_disk_bytes':shutil.disk_usage(ROOT).free})
    print('Frozen baseline, source, representations, packages and phase boundary preserved')
