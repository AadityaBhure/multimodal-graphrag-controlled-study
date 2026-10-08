"""Phase 6 preservation audit; invokes existing read-only hashes without changing prior reports."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_phase5_preservation import audit,git
from research.experiments.runner import write

if __name__=='__main__':
    result=audit()
    result['phase5_checkpoint']=result.pop('phase4_checkpoint')
    assert result['phase5_checkpoint']=='721c27b2bddf0efca2cc62eeeb6e73e2d2c9ca01'
    protected=git('ls-tree','-r','--name-only','HEAD','documentation/phase5','documentation/phase4','tests/fixtures/evaluation').splitlines()
    for p in protected:assert git('hash-object',p)==git('rev-parse','HEAD:'+p),p
    result['prior_phase_review_and_fixture_files_preserved']=len(protected)
    write(ROOT/'documentation/phase6/preservation.json',result)
    print('Phase 6 preservation PASS:',len(protected),'prior review/fixture files; 695 frozen data files; MVP unchanged')
