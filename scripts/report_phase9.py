"""RQ3 analysis per documentation/phase9/RQ3_ANALYSIS_PLAN.md. Reads the replayed Phase 5 records; writes analysis.json.

Uses the frozen metric definitions in research/agentic/analysis.py; only the replay-invariant latency is computed here.
"""
from pathlib import Path
import json, sys
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.agentic import analysis as A

LOCAL = '--local' in sys.argv
RUNS = ROOT / ('documentation/phase9/runs' + ('_local' if LOCAL else ''))
OUT = ROOT / ('documentation/phase9/analysis' + ('_local' if LOCAL else '') + '.json')
POLICIES = ('AR-B0', 'AR-B1', 'AR-01', 'AR-02', 'AR-03')
PAIRS = [('AR-01', 'AR-B0'), ('AR-02', 'AR-B0'), ('AR-03', 'AR-B0'), ('AR-01', 'AR-B1'), ('AR-02', 'AR-B1'), ('AR-03', 'AR-B1'), ('AR-B1', 'AR-B0')]
PRIMARY = 'answer_f1'
SECONDARY = ('source_f1', 'unnecessary_retrieval', 'stopping_accuracy', 'retrieval_calls', 'total_tokens', 'intrinsic_ms')
DESCRIPTIVE = ('answer_f1', 'answer_em', 'recall_at_5', 'source_f1', 'source_precision', 'source_recall', 'source_exact', 'unnecessary_retrieval',
               'required_source_miss', 'stopping_accuracy', 'premature_stop', 'over_retrieval', 'max_step_exhaustion', 'retrieval_calls',
               'llm_calls', 'total_tokens', 'intrinsic_ms')


# failure_labels() reads tool_call['detail']['plan'], but policy tool-call records carry only the retriever status
# (research/agentic/policies.py Trace.tool). The structured parser returns no plan exactly for these statuses
# (research/baselines/structured.py, retrieval.py); the adapter supplies that field without changing the taxonomy.
NO_PLAN = ('rejected_sql_language', 'unsupported_no_structured_filter', 'unsupported_structured_disjunction')


def adapt(rec):
    d = json.loads(rec['output']['diagnostics']) if rec.get('output') and rec['output'].get('diagnostics') else None
    if d is None:
        return rec
    for t in d.get('tool_calls', []):
        t.setdefault('detail', {'plan': None if t.get('status') in NO_PLAN else True})
    return {**rec, 'output': {**rec['output'], 'diagnostics': json.dumps(d)}}


def intrinsic(rec):
    d = json.loads(rec['output']['diagnostics']) if rec.get('output') and rec['output'].get('diagnostics') else {}
    t = d.get('timings_ms', {})
    return (t.get('retrieval') or 0.) + (t.get('llm_intrinsic') or 0.) + rec['total_latency_ms'] - (t.get('provider_wait') or 0.)


def load():
    rows, failures = {}, {}
    for m in POLICIES:
        recs = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((RUNS / m / 'records').glob('*.json'))]
        assert len(recs) == 28, (m, len(recs))
        out = []
        for r in recs:
            pm = A.per_record(r); pm['intrinsic_ms'] = intrinsic(r); out.append(pm)
            failures.setdefault(m, Counter()).update(A.failure_labels(adapt(r), r['gold_ids']))
        rows[m] = out
    return rows, failures


def means(rows, keys=DESCRIPTIVE):
    return {k: A.summarize(rows, k)['mean'] for k in keys}


def main():
    rows, failures = load()
    desc = {m: means(r) for m, r in rows.items()}
    strata = {}
    for dim in ('stress', 'modality'):
        for v in sorted({x[dim] for x in rows['AR-B0']}):
            strata['%s:%s' % (dim, v)] = {m: means([x for x in r if x[dim] == v], ('answer_f1', 'source_f1', 'unnecessary_retrieval', 'stopping_accuracy', 'total_tokens'))
                                          for m, r in rows.items()}
    tests = {}
    for metric in (PRIMARY,) + SECONDARY:
        res = {'%s vs %s' % (a, b): A.paired(rows[a], rows[b], metric) for a, b in PAIRS}
        adj = A.holm({k: v['p_sign_flip'] for k, v in res.items()})
        for k in res:
            res[k]['p_holm'] = adj[k]; res[k]['significant'] = adj[k] is not None and adj[k] < 0.05
        tests[metric] = res
    front = A.pareto({m: desc[m] for m in POLICIES}, ('answer_f1', 'source_f1'), ('total_tokens', 'intrinsic_ms'))
    out = {'plan': 'documentation/phase9/RQ3_ANALYSIS_PLAN.md', 'cohort': 28, 'families': len({x['family'] for x in rows['AR-B0']}),
           'descriptive': desc, 'strata': strata, 'paired_tests': tests, 'pareto': front,
           'failure_taxonomy': {m: dict(c) for m, c in failures.items()},
           'errors': {m: sum(x['error'] for x in r) for m, r in rows.items()},
           'statuses': {m: dict(Counter(x['status'] for x in r)) for m, r in rows.items()},
           'stop_reasons': {m: dict(Counter(x['stop_reason'] for x in r)) for m, r in rows.items()}}
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('WROTE', OUT.relative_to(ROOT), '| pareto', front, '| significant primary:',
          [k for k, v in tests[PRIMARY].items() if v['significant']])


if __name__ == '__main__':
    main()
