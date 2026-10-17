"""RQ4 analysis per documentation/rq4/RQ4_DESIGN.md: INT-1 vs AR-B0 and vs the selected AR policy alone (RQ3 records, same 28 queries)."""
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.agentic import analysis as A
from scripts.report_phase9 import intrinsic

D = ROOT / 'documentation/rq4'
RQ3 = ROOT / 'documentation/phase9/runs'
METRICS = ('answer_f1', 'answer_em', 'recall_at_5', 'source_f1', 'retrieval_calls', 'llm_calls', 'total_tokens', 'intrinsic_ms')


def load(directory, n=28):
    recs = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((directory / 'records').glob('*.json'))]
    assert len(recs) == n, (directory, len(recs))
    return [{**A.per_record(r), 'intrinsic_ms': intrinsic(r)} for r in recs]


def main():
    sel = json.loads((D / 'selection.json').read_text(encoding='utf-8'))
    rows = {'INT-1': load(D / 'runs/INT-1'), 'AR-B0': load(RQ3 / 'AR-B0')}
    if sel['R-AR'] != 'AR-B0':
        rows[sel['R-AR']] = load(RQ3 / sel['R-AR'])
    desc = {m: {k: A.summarize(r, k)['mean'] for k in METRICS} for m, r in rows.items()}
    pairs = [('INT-1', 'AR-B0')] + ([('INT-1', sel['R-AR'])] if sel['R-AR'] != 'AR-B0' else [])
    tests = {}
    for metric in ('answer_f1', 'total_tokens', 'intrinsic_ms', 'source_f1'):
        res = {'%s vs %s' % (a, b): A.paired(rows[a], rows[b], metric) for a, b in pairs}
        adj = A.holm({k: v['p_sign_flip'] for k, v in res.items()})
        for k in res:
            res[k]['p_holm'] = adj[k]; res[k]['significant'] = adj[k] is not None and adj[k] < 0.05
        tests[metric] = res
    strata = {'stress:%s' % s: {m: A.summarize([x for x in r if x['stress'] == s], 'answer_f1')['mean'] for m, r in rows.items()}
              for s in ('normal', 'noisy')}
    out = {'design': 'documentation/rq4/RQ4_DESIGN.md', 'selection': sel, 'descriptive': desc, 'paired_tests': tests, 'strata': strata,
           'errors': {m: sum(x['error'] for x in r) for m, r in rows.items()}}
    (D / 'analysis.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('WROTE', D / 'analysis.json', '| significant answer F1:', [k for k, v in tests['answer_f1'].items() if v['significant']])


if __name__ == '__main__':
    main()
