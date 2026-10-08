"""Verify the Phase 6 checkpoint and every frozen data payload without writes."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_phase5_preservation import audit,git
from research.experiments.runner import write

def main():
    checkpoint='a19bdd5e30e33caa7c82a8a0095dcdd1e610693e'
    assert git('rev-parse','HEAD')==checkpoint
    result=audit()
    result['phase6_checkpoint']=result.pop('phase4_checkpoint')
    protected=git('ls-tree','-r','--name-only',checkpoint).splitlines()
    protected=[p for p in protected if p!='documentation/Research_Decision_Log.md']
    for path in protected:
        expected=git('rev-parse',checkpoint+':'+path)
        assert expected in (git('hash-object','--no-filters',path),git('hash-object',path)),path
    result['protected_phase6_checkpoint_files']=len(protected)
    write(ROOT/'documentation/phase6_5/preservation.json',result)
    print('PASS: frozen datasets and',len(protected),'checkpoint files preserved')
if __name__=='__main__':main()
