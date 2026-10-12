"""Read-only preservation audit for RQ1 operational revision 2 (before its re-freeze).

1. Frozen data / benchmark / MVP / storage / release gate (the Phase 5 audit: 695 payloads).
2. Git: since the preserved diagnostics checkpoint 159a48f, only the files listed in ALLOWED may differ;
   historical Phase 7/8 results, historical RQ1/RQ2 code, baselines and earlier repair records are byte-identical.
3. No tracked file is modified in the working tree; no RQ1 run directory or Groq repair request exists.
"""
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_phase5_preservation import audit, git
from research.experiments.runner import write

CHECKPOINT = '159a48f'
ALLOWED = {
    # operational revision 2 (admission rule + timing boundary), code and tests
    'research/repair/dispatch.py', 'research/repair/rq1_compliance_v1/system.py', 'scripts/audit_rq1_repair_local.py',
    'scripts/report_rq1_repair.py', 'scripts/run_rq1_repair.py', 'scripts/validate_timing_boundary_equivalence.py',
    'tests/test_repair_dispatch.py', 'tests/test_repair_timing_boundary.py', 'scripts/audit_rq1_rev2_preservation.py',
    # plan / decision log (decision log is append-only and excluded from the baseline audit)
    'documentation/PROJECT_COMPLETION_PLAN.md', 'documentation/Research_Decision_Log.md', '.gitattributes',
    'research/repair/schedule.py', 'tests/test_repair_schedule.py', 'scripts/verify_rq1_interleaving_offline.py',
}
ALLOWED_PREFIXES = ('documentation/rq1_repair/timing_equivalence/',)
ALLOWED_NEW_OUTPUTS = {'documentation/rq1_repair/timing_boundary_equivalence.json', 'documentation/rq1_repair/rev2_preservation.json',
                       'documentation/rq1_repair/rev2_full_tests.xml', 'documentation/rq1_repair/execution_plan_v1.json',
                       'documentation/rq1_repair/execution_plan.json', 'documentation/rq1_repair/RQ1_OPERATIONAL_REVISION_2_VALIDATION.md',
                       'documentation/rq1_repair/execution_plan_v2.json', 'documentation/rq1_repair/local_audit.json',
                       'documentation/rq1_repair/local_audit_progress_rev2.json', 'documentation/rq1_repair/RQ1_OPERATIONAL_REVISION_3.md',
                       'documentation/rq1_repair/rev3_full_tests.xml',
                       'documentation/rq1_repair/execution_plan_v3.json', 'documentation/rq1_repair/interleaving_offline_check.json',
                       'documentation/rq1_repair/RQ1_OPERATIONAL_REVISION_4.md', 'documentation/rq1_repair/rev4_full_tests.xml'}
PROTECTED_TREES = ('documentation/phase7', 'documentation/phase8', 'documentation/phase8_generation_v2', 'documentation/compliance_repair',
                   'research/rq1', 'research/rq2', 'research/baselines', 'research/evaluation', 'research/experiments', 'src', 'configs')


def main():
    result = audit()
    changed = [p for p in git('diff', '--name-only', CHECKPOINT, 'HEAD').splitlines() if p]
    unexpected = [p for p in changed if p not in ALLOWED and p not in ALLOWED_NEW_OUTPUTS and not p.startswith(ALLOWED_PREFIXES)]
    protected_changed = [p for p in git('diff', '--name-only', CHECKPOINT, 'HEAD', '--', *PROTECTED_TREES).splitlines() if p]
    dirty = [l.split(maxsplit=1)[1] for l in git('status', '--porcelain', '--untracked-files=no').splitlines() if l.strip()]   # git() strips the first line's status padding
    dirty = [p for p in dirty if p not in ALLOWED and p not in ALLOWED_NEW_OUTPUTS and not p.startswith(ALLOWED_PREFIXES)]
    runs = ROOT / 'documentation/rq1_repair/runs'
    dispatch = ROOT / 'documentation/rq1_repair/dispatch'   # Dispatcher root of run_rq1_repair.py
    result.update(audit_name='rq1-operational-revision-2-preservation', checkpoint=CHECKPOINT, head=git('rev-parse', 'HEAD'),
                  files_changed_since_checkpoint=changed, unexpected_changes=unexpected, protected_trees=list(PROTECTED_TREES),
                  protected_tree_changes=protected_changed, tracked_dirty_outside_allowed=dirty,
                  rq1_run_dirs_present=runs.exists(), repair_dispatch_records_present=dispatch.exists(),
                  test_human_test_run=False)
    ok = not unexpected and not protected_changed and not dirty and not runs.exists() and not dispatch.exists()
    result['status'] = 'pass' if ok and result['status'] == 'pass' else 'FAIL'
    write(ROOT / 'documentation/rq1_repair/rev2_preservation.json', result)
    print(result['status'], '| changed since', CHECKPOINT, len(changed), '| unexpected', unexpected, '| protected changes', protected_changed,
          '| dirty', dirty, '| payloads', {k: v['files'] for k, v in result['groups'].items()})


if __name__ == '__main__':
    main()
