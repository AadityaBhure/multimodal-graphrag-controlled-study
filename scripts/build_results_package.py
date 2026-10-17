"""Cross-RQ results package: documentation/results/{RESULTS.md, *.csv, fig_*.png} from whichever analyses exist.

Read-only on study outputs; rerun after each study's analysis. Missing studies are listed as pending, never estimated.
"""
from pathlib import Path
import csv, json, sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
OUT = ROOT / 'documentation/results'
SRC = {'RQ1': ROOT / 'documentation/rq1_repair/analysis_local.json', 'RQ2': ROOT / 'documentation/rq2_repair/analysis_local.json',
       'RQ3': ROOT / 'documentation/phase9/analysis_local.json', 'RQ4': ROOT / 'documentation/rq4/analysis_local.json'}
METHODS = {'RQ1': ('CM-B0', 'CM-B1', 'CM-01', 'CM-02', 'CM-03'), 'RQ2': ('CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03'),
           'RQ3': ('AR-B0', 'AR-B1', 'AR-01', 'AR-02', 'AR-03')}
COLS = {'RQ1': [('f1', 'Answer F1'), ('exact_match', 'EM'), ('mrr', 'MRR'), ('gold_coverage', 'Gold coverage'), ('input_tokens', 'Input tokens'),
                ('intrinsic_total_ms', 'Latency ms')],
        'RQ2': [('answer_f1', 'Answer F1'), ('answer_em', 'EM'), ('mrr', 'MRR'), ('llm_calls', 'LLM calls'), ('input_tokens', 'Input tokens'),
                ('intrinsic_ms', 'Latency ms')],
        'RQ3': [('answer_f1', 'Answer F1'), ('answer_em', 'EM'), ('source_f1', 'Source F1'), ('unnecessary_retrieval', 'Wasted retrieval'),
                ('stopping_accuracy', 'Stopping acc.'), ('retrieval_calls', 'Retrieval calls'), ('total_tokens', 'Tokens'), ('intrinsic_ms', 'Latency ms')],
        'RQ4': [('answer_f1', 'Answer F1'), ('answer_em', 'EM'), ('source_f1', 'Source F1'), ('total_tokens', 'Tokens'), ('intrinsic_ms', 'Latency ms')]}


def rq1_view(a):
    """RQ1 analysis.json stores per-(method, cohort, metric) tables; reshape to descriptive means + paired F1 tests."""
    desc = {}
    for t in a['tables']:
        if t['cohort'] == 'all':
            desc.setdefault(t['method'], {})[t['metric']] = t['mean']
    tests = {'%s vs %s' % (c['a'], c['b']): {'mean_delta': c['mean'], 'ci95_family_bootstrap': c['ci95'], 'p_sign_flip': c['p_cluster_sign_permutation'],
                                             'p_holm': c.get('p_holm'), 'significant': (c.get('p_holm') or 1) < .05} for c in a['paired_f1']}
    from research.agentic.analysis import pareto
    front = pareto({m: desc[m] for m in desc}, ('f1', 'mrr'), ('input_tokens', 'intrinsic_total_ms'))
    return {'descriptive': desc, 'paired_tests': {'answer_f1': tests}, 'pareto': front}


def fmt(v):
    if v is None:
        return 'NA'
    if isinstance(v, float):
        return f'{v:,.0f}' if abs(v) >= 100 else f'{v:.3f}'
    return str(v)


def table(rq, view):
    cols = COLS[rq]; methods = METHODS.get(rq) or sorted(view['descriptive'])
    lines = ['| Method | ' + ' | '.join(c[1] for c in cols) + ' |', '|' + '---|' * (len(cols) + 1)]
    rows = []
    for m in methods:
        if m in view['descriptive']:
            d = view['descriptive'][m]; rows.append([m] + [d.get(c[0]) for c in cols])
            lines.append('| %s%s | ' % (m, ' ★' if m in view.get('pareto', []) else '') + ' | '.join(fmt(d.get(c[0])) for c in cols) + ' |')
    with open(OUT / (rq.lower() + '_methods.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['method'] + [c[0] for c in cols]); w.writerows(rows)
    return '\n'.join(lines)


def tests_md(view):
    t = view['paired_tests'].get('answer_f1', {})
    lines = ['| Pair | Δ answer F1 | 95 % CI | p (sign-flip) | p (Holm) |', '|---|---|---|---|---|']
    for k, v in t.items():
        ci = v.get('ci95_family_bootstrap')
        lines.append('| %s | %s | %s | %s | %s%s |' % (k, fmt(v.get('mean_delta')), ('[%.3f, %.3f]' % tuple(ci)) if ci else 'NA',
                                                       fmt(v.get('p_sign_flip')), fmt(v.get('p_holm')), ' *' if v.get('significant') else ''))
    return '\n'.join(lines)


def figure(rq, view):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    d = view['descriptive']; f1 = 'f1' if rq == 'RQ1' else 'answer_f1'
    tok = 'input_tokens' if rq in ('RQ1', 'RQ2') else 'total_tokens'
    ms = [m for m in (METHODS.get(rq) or sorted(d)) if m in d and d[m].get(f1) is not None and d[m].get(tok) is not None]
    if not ms:
        return None
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    for m in ms:
        ax.scatter(d[m][tok], d[m][f1], s=60, marker='o' if m in view.get('pareto', []) else 'x')
        ax.annotate(m, (d[m][tok], d[m][f1]), textcoords='offset points', xytext=(5, 4), fontsize=8)
    ax.set_xlabel('Mean ' + tok.replace('_', ' ')); ax.set_ylabel('Mean answer F1'); ax.set_title(rq + ': quality vs cost (o = Pareto)')
    ax.grid(alpha=.3); fig.tight_layout(); p = OUT / ('fig_%s_quality_cost.png' % rq.lower()); fig.savefig(p, dpi=150); plt.close(fig)
    return p.name


# ------------------------------------------------------------------ overall ranking (PR-15)
# One winner per part ("overall performance"): every method is ranked 1-5 on each of the study's frozen Pareto axes
# (equal weight per axis; tied values share the average rank) and the lowest rank total wins. Ties on the total are
# broken by the frozen RQ4 rule order: higher answer F1, then fewer tokens, then B1, 01, 02, 03, B0. Robustness check:
# the mean of min-max scaled axis scores (1 = best on that axis). Descriptive summary of the frozen means; no new test.
AXES = {'RQ1': (('f1', 'mrr'), ('input_tokens', 'intrinsic_total_ms')), 'RQ2': (('answer_f1',), ('input_tokens', 'intrinsic_ms')),
        'RQ3': (('answer_f1', 'source_f1'), ('total_tokens', 'intrinsic_ms'))}
PRIMARY_F1 = {'RQ1': 'f1', 'RQ2': 'answer_f1', 'RQ3': 'answer_f1'}
TOKENS = {'RQ1': 'input_tokens', 'RQ2': 'total_tokens', 'RQ3': 'total_tokens'}
TIE_ORDER = ('B1', '01', '02', '03', 'B0')
NAME = {'f1': 'answer_f1', 'intrinsic_total_ms': 'latency', 'intrinsic_ms': 'latency'}


def average_ranks(values, higher):
    items = sorted(values.items(), key=lambda kv: -kv[1] if higher else kv[1])
    out, i = {}, 0
    while i < len(items):
        j = i
        while j + 1 < len(items) and abs(items[j + 1][1] - items[i][1]) < 1e-9:
            j += 1
        for k in range(i, j + 1):
            out[items[k][0]] = (i + j) / 2 + 1
        i = j + 1
    return out


def overall(rq, desc, pareto_set):
    hi, lo = AXES[rq]; methods = list(METHODS[rq])
    ranks = {m: {} for m in methods}; scaled = {m: 0. for m in methods}
    for k in hi + lo:
        v = {m: desc[m][k] for m in methods}
        r = average_ranks(v, k in hi); mn, mx = min(v.values()), max(v.values())
        for m in methods:
            ranks[m][NAME.get(k, k)] = r[m]
            scaled[m] += (1. if mx - mn < 1e-12 else ((v[m] - mn) if k in hi else (mx - v[m])) / (mx - mn)) / len(hi + lo)
    total = {m: sum(ranks[m].values()) for m in methods}
    tie = lambda m: (-(desc[m][PRIMARY_F1[rq]] or 0.), desc[m][TOKENS[rq]], TIE_ORDER.index(m.split('-')[1]))
    order = sorted(methods, key=lambda m: (total[m],) + tie(m))
    quality_first = sorted(pareto_set, key=tie)[0]                 # the frozen RQ4 rule, applied to this part
    return {'axes': [{'metric': NAME.get(k, k), 'direction': 'higher' if k in hi else 'lower'} for k in hi + lo], 'ranks': ranks,
            'total': total, 'scaled': scaled, 'order': order, 'winner': order[0],
            'winner_scaled': max(methods, key=lambda m: (round(scaled[m], 12),) + tuple(-x for x in tie(m)[:2]) + (-tie(m)[2],)),
            'winner_quality_first': quality_first}


def overall_ranking(views):
    parts = {rq: overall(rq, views[rq]['descriptive'], views[rq]['pareto']) for rq in AXES if rq in views}
    out = {'rule': 'Rank 1-5 on each frozen Pareto axis of the part (equal weight, average ranks for ties); lowest total wins; '
                   'ties: higher answer F1, fewer tokens, then B1, 01, 02, 03, B0. Check: mean of min-max scaled axis scores.',
           'parts': parts}
    if 'RQ4' in views:
        sel = views['RQ4'].get('selection', {})
        out['combined'] = {'winners': {rq: parts[rq]['winner'] for rq in parts}, 'rq4_pipeline': [sel.get('R-AR'), sel.get('CM'), sel.get('R-CF')],
                           'matches_rq4': [parts['RQ3']['winner'], parts['RQ1']['winner'], parts['RQ2']['winner']] == [sel.get('R-AR'), sel.get('CM'), sel.get('R-CF')]}
    return out


def ranking_md(rk):
    lines = ['## Overall ranking (one winner per part)', '', rk['rule'], '']
    for rq, r in rk['parts'].items():
        axes = [a['metric'] for a in r['axes']]
        lines += ['**%s — winner: %s** (scaled-score check: %s; quality-first rule: %s)' % (rq, r['winner'], r['winner_scaled'], r['winner_quality_first']), '',
                  '| Method | ' + ' | '.join('rank: ' + a for a in axes) + ' | Rank total | Scaled score |', '|' + '---|' * (len(axes) + 3)]
        for m in r['order']:
            lines.append('| %s | %s | %s | %.3f |' % (m, ' | '.join('%g' % r['ranks'][m][a] for a in axes), '%g' % r['total'][m], r['scaled'][m]))
        lines.append('')
    if 'combined' in rk:
        c = rk['combined']
        lines += ['Combined (RQ4): winners %s; INT-1 pipeline %s; identical: %s' % (c['winners'], ' -> '.join(c['rq4_pipeline']), c['matches_rq4']), '']
    return lines


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    md = ['# Results package (validation results; locked test out of scope)', '',
          'Generated by `scripts/build_results_package.py` from the frozen analyses. ★ = Pareto set. Statistics: family-clustered bootstrap CI, '
          'exact sign-flip test over base families, Holm correction; * = Holm p < 0.05.', '']
    views = {}
    for rq, path in SRC.items():
        md.append('## ' + rq)
        if not path.exists():
            md += ['Pending (analysis not yet available).', '']; continue
        a = json.loads(path.read_text(encoding='utf-8'))
        view = rq1_view(a) if rq == 'RQ1' else a
        views[rq] = view
        md += [table(rq, view), '', tests_md(view), '']
        if rq == 'RQ4':
            md += ['Selection: ' + json.dumps(a.get('selection', {})), '']
        fig = figure(rq, view)
        if fig:
            md += ['![%s](%s)' % (rq, fig), '']
    if all(rq in views for rq in AXES):
        rk = overall_ranking(views)
        (OUT / 'overall_ranking.json').write_text(json.dumps(rk, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        md += ranking_md(rk)
    (OUT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8', newline='\n')
    print('WROTE documentation/results/RESULTS.md;', ', '.join(rq for rq, p in SRC.items() if p.exists()), 'included')


if __name__ == '__main__':
    main()
