"""RQ2 canonical analysis per documentation/rq2_repair/RQ2_ANALYSIS_PLAN.md (replayed Phase 5 records -> analysis.json)."""
from pathlib import Path
import json, sys
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.agentic import analysis as A

D = ROOT / 'documentation/rq2_repair'
METHODS = ('CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03')
PAIRS = [('CF-01', 'CF-B0'), ('CF-02', 'CF-B0'), ('CF-03', 'CF-B0'), ('CF-01', 'CF-B1'), ('CF-02', 'CF-B1'), ('CF-03', 'CF-B1'), ('CF-B1', 'CF-B0')]
PRIMARY = 'answer_f1'
SECONDARY = ('answer_em', 'input_tokens', 'output_tokens', 'llm_calls', 'intrinsic_ms')
DESCRIPTIVE = ('answer_f1', 'answer_em', 'precision', 'recall', 'mrr', 'recall_at_5', 'context_characters', 'coverage_text', 'coverage_graph',
               'coverage_structured', 'llm_calls', 'input_tokens', 'output_tokens', 'total_tokens', 'intrinsic_ms')


def row(rec, strata):
    d = json.loads(rec['output']['diagnostics']) if rec.get('output') and rec['output'].get('diagnostics') else {}
    m, o = rec['metrics'], rec['observation']
    cov = d.get('source_coverage', {})
    r = {'query_id': rec['query_id'], 'family': A.family(rec['query_id']), 'method': rec['system_id'], 'stress': rec['stress'][0],
         'modality': rec['labels']['modality'], 'support': strata[rec['query_id']]['class'], 'error': bool(rec['errors']),
         'answer_f1': m.get('f1'), 'answer_em': m.get('exact_match'), 'precision': m.get('precision'), 'recall': m.get('recall'),
         'mrr': m.get('mrr'), 'recall_at_5': m.get('recall@5'), 'context_characters': d.get('context_characters'),
         'coverage_text': cov.get('text'), 'coverage_graph': cov.get('graph'), 'coverage_structured': cov.get('structured'),
         'llm_calls': o.get('llm_calls'), 'input_tokens': o.get('input_tokens'), 'output_tokens': o.get('output_tokens')}
    r['total_tokens'] = r['input_tokens'] + r['output_tokens'] if r['input_tokens'] is not None and r['output_tokens'] is not None else None
    r['intrinsic_ms'] = (d.get('fusion_ms') or 0.) + o['generation_ms'] if o.get('generation_ms') is not None else None
    r['diag'] = {k: d.get(k) for k in ('fallback', 'group_truncated', 'resolved', 'unresolved', 'global_resolver_uses', 'selector_fallback',
                                        'selector_invalid_ids', 'selected_structural', 'fusion_retry', 'generation_status')}
    r['cf03_statuses'] = [f['status'] for f in d.get('source_findings', [])]
    return r


def main():
    strata = json.loads((D / 'supportability.json').read_text(encoding='utf-8'))['rows']
    rows = {}
    for m in METHODS:
        recs = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((D / 'runs' / m / 'records').glob('*.json'))]
        assert len(recs) == 24, (m, len(recs))
        rows[m] = [row(r, strata) for r in recs]
    mean = lambda rs, ks: {k: A.summarize(rs, k)['mean'] for k in ks}
    desc = {m: mean(r, DESCRIPTIVE) for m, r in rows.items()}
    strat = {}
    for dim in ('support', 'modality', 'stress'):
        for v in sorted({x[dim] for x in rows['CF-B0']}):
            strat['%s:%s' % (dim, v)] = {'n': sum(x[dim] == v for x in rows['CF-B0']),
                                         **{m: mean([x for x in r if x[dim] == v], ('answer_f1', 'answer_em', 'total_tokens')) for m, r in rows.items()}}
    tests = {}
    for metric in (PRIMARY,) + SECONDARY:
        res = {'%s vs %s' % (a, b): A.paired(rows[a], rows[b], metric) for a, b in PAIRS}
        adj = A.holm({k: v['p_sign_flip'] for k, v in res.items()})
        for k in res:
            res[k]['p_holm'] = adj[k]; res[k]['significant'] = adj[k] is not None and adj[k] < 0.05
        tests[metric] = res
    front = A.pareto({m: desc[m] for m in METHODS}, ('answer_f1',), ('input_tokens', 'intrinsic_ms'))
    method_diag = {
        'CF-01': {'fallbacks': Counter(x['diag']['fallback'] for x in rows['CF-01']), 'group_truncated': sum(bool(x['diag']['group_truncated']) for x in rows['CF-01']),
                  'global_resolver_uses': sum(x['diag']['global_resolver_uses'] or 0 for x in rows['CF-01'])},
        'CF-02': {'selector_fallbacks': Counter(x['diag']['selector_fallback'] for x in rows['CF-02']),
                  'invalid_ids': sum(len(x['diag']['selector_invalid_ids'] or []) for x in rows['CF-02']),
                  'mean_selected': sum(len(x['diag']['selected_structural'] or []) for x in rows['CF-02']) / 24},
        'CF-03': {'source_statuses': Counter(s for x in rows['CF-03'] for s in x['cf03_statuses']), 'fusion_retries': sum(bool(x['diag']['fusion_retry']) for x in rows['CF-03'])}}
    out = {'plan': 'documentation/rq2_repair/RQ2_ANALYSIS_PLAN.md', 'bundles': 24, 'families': len({x['family'] for x in rows['CF-B0']}),
           'descriptive': desc, 'strata': strat, 'paired_tests': tests, 'pareto': front,
           'method_diagnostics': {k: {kk: (dict(vv) if isinstance(vv, Counter) else vv) for kk, vv in v.items()} for k, v in method_diag.items()},
           'errors': {m: sum(x['error'] for x in r) for m, r in rows.items()}}
    (D / 'analysis.json').write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + '\n', encoding='utf-8', newline='\n')
    print('WROTE', D / 'analysis.json', '| pareto', front, '| significant primary:', [k for k, v in tests[PRIMARY].items() if v['significant']])


if __name__ == '__main__':
    main()
