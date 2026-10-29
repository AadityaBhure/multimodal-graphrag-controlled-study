"""Charts for the project documentation, drawn only from frozen result files (same inputs give the same images)."""
import itertools
import math
import random

import textwrap

import numpy as np
from figlib import *

plt.rcParams['font.family'] = ['Segoe UI', 'Segoe UI Symbol', 'DejaVu Sans']
R1, R2, R3, R4 = RES['RQ1'], RES['RQ2'], RES['RQ3'], RES['RQ4']
Q = load('showcase/bundle/queries.json')
MOD_ORDER = ['T', 'G', 'S', 'TG', 'TS', 'GS', 'TGS']
MOD_NAME = {'T': 'Text', 'G': 'Graph', 'S': 'Structured', 'TG': 'Text+Graph', 'TS': 'Text+Struct.', 'GS': 'Graph+Struct.', 'TGS': 'All three'}
ARROW = lambda k: '  ↑' if k in HIGHER else '  ↓'


def panels(n, ncols=3, w=7.3, h=1.95):
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, h * nrows), squeeze=False)
    fig.subplots_adjust(wspace=0.95, hspace=0.78)
    for ax in list(axes.flat)[n:]:
        ax.axis('off')
    return fig, list(axes.flat)


def method_panels(R, metrics, name, ncols=3, ci=False, w=7.3, h=1.95):
    ms, d = R['methods'], R['descriptive']
    fig, axes = panels(len(metrics), ncols, w, h)
    for k, ax in zip(metrics, axes):
        sc = scale(k)
        vals = [None if d[m].get(k) is None else d[m][k] * sc for m in ms]
        c = None
        if ci and R.get('ci95'):
            c = []
            for m in ms:
                lohi = (R['ci95'].get(m) or {}).get(k)
                c.append((lohi[0] * sc, lohi[1] * sc) if lohi else (None, None))
        bars(ax, ms, vals, [mcolor(m) for m in ms], labels=[fmt(d[m].get(k), KIND.get(k, 'rate')) for m in ms], ci=c,
             title=LABEL[k] + ARROW(k), star=R.get('pareto') or ())
    return save(fig, name)


def scatter(R, x, y, name, xlabel, ylabel, w=6.6, h=3.5, note=None):
    ms, d, P = R['methods'], R['descriptive'], set(R.get('pareto') or [])
    fig, ax = plt.subplots(figsize=(w, h))
    xs = [d[m][x] * scale(x) for m in ms]
    ys = [d[m][y] * scale(y) for m in ms]
    pts = sorted((xs[i], ys[i]) for i, m in enumerate(ms) if m in P)
    if len(pts) > 1:
        ax.plot(*zip(*pts), color='#cbd5e1', linewidth=1.6, zorder=1)
    for i, m in enumerate(ms):
        on = m in P
        ax.scatter(xs[i], ys[i], s=95, marker='o' if on else 'v', facecolor=mcolor(m) if on else 'white', edgecolor=mcolor(m), linewidth=1.8, zorder=3)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    xr, yr = max(xs) - min(xs) or 1, max(ys) - min(ys) or 1
    ax.set_xlim(min(xs) - .1 * xr, max(xs) + .45 * xr)
    ax.set_ylim(min(ys) - .2 * yr, max(ys) + .2 * yr)
    tidy(ax, xgrid=True, ygrid=True)
    ax.scatter([], [], s=60, marker='o', facecolor=FAINT, edgecolor=FAINT, label='Pareto-optimal (★)')
    ax.scatter([], [], s=60, marker='v', facecolor='white', edgecolor=FAINT, label='dominated')
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=2, handletextpad=0.3)
    fig.canvas.draw()
    rnd = fig.canvas.get_renderer()
    placed = []
    pts_px = [ax.transData.transform((xs[i], ys[i])) for i in range(len(ms))]
    box = ax.get_window_extent(rnd)
    for i, m in enumerate(ms):
        txt = '%s%s  (%s, %s)' % (m, ' ★' if m in P else '', fmt(d[m][x], KIND[x]), fmt(d[m][y], KIND[y]))
        for dx, dy, ha in ((9, 5, 'left'), (9, -13, 'left'), (-9, 5, 'right'), (-9, -13, 'right'), (9, 17, 'left'), (9, -25, 'left'), (-9, 17, 'right')):
            t = ax.annotate(txt, (xs[i], ys[i]), xytext=(dx, dy), textcoords='offset points', fontsize=8.2, color=BODY, ha=ha)
            bb = t.get_window_extent(rnd).expanded(1.03, 1.15)
            hit_pt = any(bb.contains(px, py) for j, (px, py) in enumerate(pts_px) if j != i)
            inside = box.x0 <= bb.x0 and bb.x1 <= box.x1 and box.y0 <= bb.y0 and bb.y1 <= box.y1
            if not hit_pt and inside and not any(bb.overlaps(o) for o in placed):
                placed.append(bb)
                break
            t.remove()
        else:
            placed.append(ax.annotate(txt, (xs[i], ys[i]), xytext=(9, 5), textcoords='offset points', fontsize=8.2, color=BODY).get_window_extent(rnd))
    if note:
        ax.text(0, -0.24, note, transform=ax.transAxes, fontsize=7.6, color=FAINT, va='top')
    return save(fig, name)


def forest(ax, rows, metric, title, xlabel=None):
    sc = scale(metric)
    ys = list(range(len(rows)))[::-1]
    lo_all = min(t['ci95'][0] * sc for t in rows if t.get('ci95'))
    hi_all = max(t['ci95'][1] * sc for t in rows if t.get('ci95'))
    span = (hi_all - lo_all) or 1.
    for y, t in zip(ys, rows):
        col = '#15803d' if t['significant'] else '#64748b'
        lo, hi = t['ci95']
        ax.plot([lo * sc, hi * sc], [y, y], color=col, linewidth=1.8, solid_capstyle='round', zorder=2)
        ax.scatter([t['delta'] * sc], [y], s=34, color=col, zorder=3, marker='D' if t['significant'] else 'o')
        ax.text(1.02, y, 'p(Holm) %s%s' % (fmt(t['p_holm'], 'p'), '  ✓ significant' if t['significant'] else ''),
                transform=ax.get_yaxis_transform(), va='center', fontsize=7.8, color=col if t['significant'] else FAINT)
    ax.axvline(0, color='#94a3b8', linewidth=1.0, zorder=1)
    ax.set_yticks(ys)
    ax.set_yticklabels(['%s − %s' % (t['a'], t['b']) for t in rows])
    ax.set_xlim(lo_all - .08 * span, hi_all + .08 * span)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_title(title, pad=6)
    if xlabel:
        ax.set_xlabel(xlabel)
    tidy(ax)


def forest_fig(R, metrics, name, w=7.3, h_per=None):
    n = len(metrics)
    heights = [len(R['tests'][k]) for k in metrics]
    fig, axes = plt.subplots(n, 1, figsize=(w, sum(0.3 * x + 0.75 for x in heights)), gridspec_kw={'height_ratios': heights}, squeeze=False)
    fig.subplots_adjust(hspace=0.75, right=0.70)
    for k, ax in zip(metrics, axes.flat):
        forest(ax, R['tests'][k], k, 'Paired difference A − B: %s (95 %% family-bootstrap interval)' % LABEL[k])
    return save(fig, name)


def ranking(R, name, w=7.3):
    o = R['overall']
    ms, ax_ = o['order'], [a['metric'] for a in o['axes']]
    fig, ax = plt.subplots(figsize=(w, 0.42 * len(ms) + 0.9))
    vals = [[o['ranks'][m][a] for a in ax_] for m in ms]
    heatmap(ax, ms, ax_, vals, fmtfn=lambda v: ('%g' % v), vmin=1, vmax=5, ramp=['#0d366b', '#2a78d6', '#86b6ef', '#cde2fb', '#f3f8fe'],
            xlabels=[LABEL[a].replace(' (s)', '') + ('\n(higher better)' if a in HIGHER else '\n(lower better)') for a in ax_])
    n = len(ax_)
    ax.set_xlim(0, n + 2.4)
    ax.text(n + 0.6, -0.12, 'Rank total', ha='center', va='bottom', fontsize=8.6, color=BODY)
    ax.text(n + 1.75, -0.12, 'Scaled score', ha='center', va='bottom', fontsize=8.6, color=BODY)
    for i, m in enumerate(ms):
        win = m == o['winner']
        ax.text(n + 0.6, i + .5, '%g' % o['total'][m], ha='center', va='center', fontsize=9.5, fontweight='bold' if win else 'normal', color=INK)
        ax.text(n + 1.75, i + .5, fnum(o['scaled'][m], 3), ha='center', va='center', fontsize=9.5, fontweight='bold' if win else 'normal', color=INK)
        if win:
            ax.add_patch(Rectangle((0.02, i + 0.04), n + 2.36, 0.92, fill=False, edgecolor='#f59e0b', linewidth=2.0))
    ax.set_yticklabels([m + ('  \U0001F3C6' if m == o['winner'] else '') for m in ms])
    return save(fig, name)


# ======================================================================= foundation
def dataset():
    c = FOUND['corpus']
    fig, axes = plt.subplots(1, 2, figsize=(7.3, 2.2))
    fig.subplots_adjust(wspace=0.75)
    ent = [('Paper', c['entities']['paper']), ('Author', c['entities']['author']), ('Institution', c['entities']['institution']),
           ('Field of study', c['entities']['field_of_study'])]
    rel = [('HAS_TOPIC', c['relations']['HAS_TOPIC']), ('WRITES', c['relations']['WRITES']), ('CITES', c['relations']['CITES']),
           ('AFFILIATED_WITH', c['relations']['AFFILIATED_WITH'])]
    bars(axes[0], [a for a, _ in ent], [b / 1e6 for _, b in ent], ['#475569'] * 4, labels=[fmt(b, 'count') for _, b in ent],
         title='Entities (nodes): %s' % fmt(c['nodes'], 'count'), xlabel='millions', xmax=1.6)
    bars(axes[1], [a for a, _ in rel], [b / 1e6 for _, b in rel], ['#0d9488'] * 4, labels=[fmt(b, 'count') for _, b in rel],
         title='Official directed relations: %s' % fmt(c['official_relations'], 'count'), xlabel='millions', xmax=10.5)
    return save(fig, 'c_dataset')


def benchmark():
    S = load('documentation/phase4/benchmark_stats.json')
    fig, axes = plt.subplots(1, 2, figsize=(7.3, 2.5), gridspec_kw={'width_ratios': [1.1, 1]})
    fig.subplots_adjust(wspace=0.55)
    bins = ['0', '1', '2-5', '6-20', '21-100', '101+']
    ax = axes[0]
    vals = [S['answer_set_size'][b] for b in bins]
    ax.bar(range(len(bins)), vals, width=0.55, color='#475569')
    for i, v in enumerate(vals):
        ax.text(i, v + 120, fmt(v, 'count'), ha='center', va='bottom', fontsize=8.3, color=BODY)
    ax.set_xticks(range(len(bins)))
    ax.set_xticklabels([b.replace('-', '–') for b in bins])
    ax.set_xlabel('Correct papers per question')
    ax.set_title('Answer-set sizes (all 13,571 questions)', pad=6)
    ax.set_ylim(0, max(vals) * 1.15)
    tidy(ax, xgrid=False, ygrid=True)
    ax = axes[1]
    years = [y for y in sorted(S['unique_gold_paper_year_distribution']) if y != 'None' and int(y) >= 2009]
    vals = [S['unique_gold_paper_year_distribution'][y] for y in years]
    ax.bar(range(len(years)), vals, width=0.6, color='#94a3b8')
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(["'" + y[2:] for y in years], fontsize=8)
    ax.set_title('Publication year of the %s distinct correct papers' % fmt(S['unique_gold_papers'], 'count'), pad=6)
    ax.set_xlabel('Year (2009–2019; %s earlier, %s unrecorded)' % (sum(v for y, v in S['unique_gold_paper_year_distribution'].items() if y != 'None' and int(y) < 2009),
                                                                     fmt(S['unique_gold_paper_year_distribution']['None'], 'count')))
    tidy(ax, xgrid=False, ygrid=True)
    save(fig, 'c_benchmark_sizes')

    # generated set composition: modality x stress, modality x reasoning
    J = S['generated_joint_taxonomy']
    stress = ['normal', 'noisy', 'conflict', 'unanswerable']
    hops = ['single-hop', 'multi-hop-2', 'multi-hop-3+']
    fig, axes = plt.subplots(1, 2, figsize=(7.3, 2.6))
    fig.subplots_adjust(wspace=0.45)
    ms = [m for m in MOD_ORDER]
    v1 = [[sum(n for k, n in J.items() if k.split('|')[0] == m and k.split('|')[2] == s) for s in stress] for m in ms]
    v2 = [[sum(n for k, n in J.items() if k.split('|')[0] == m and k.split('|')[1] == h) for h in hops] for m in ms]
    heatmap(axes[0], [MOD_NAME[m] for m in ms], stress, v1, fmtfn=lambda v: '%d' % v, vmin=0, vmax=8)
    axes[0].set_title('Generated questions: sources × variant', pad=26)
    heatmap(axes[1], [MOD_NAME[m] for m in ms], hops, v2, fmtfn=lambda v: '%d' % v, vmin=0, vmax=8)
    axes[1].set_title('Generated questions: sources × reasoning', pad=26)
    return save(fig, 'c_benchmark_generated')


def baselines():
    rows = load('documentation/phase6_closeout/comparison.json')
    get = lambda b, coh, met: next((r['mean'] for r in rows if r['baseline'] == b and r['cohort'] == coh and r['metric'] == met), None)
    B = ['B1', 'B2', 'B3', 'B4']
    col = {'B1': SOURCE_COLOR['text'], 'B2': SOURCE_COLOR['graph'], 'B3': SOURCE_COLOR['structured'], 'B4': '#334155'}
    name = {'B1': 'B1 text', 'B2': 'B2 graph', 'B3': 'B3 structured', 'B4': 'B4 all three'}
    mets = [('recall@5', 'Recall@5'), ('precision@5', 'Precision@5'), ('mrr', 'MRR'), ('ndcg@5', 'nDCG@5'), ('gold_coverage', 'Gold coverage')]
    fig, ax = plt.subplots(figsize=(7.3, 2.7))
    wdt = 0.8 / 4
    for j, b in enumerate(B):
        xs = [i - 0.4 + wdt * (j + .5) for i in range(len(mets))]
        vals = [get(b, 'overall', k) or 0 for k, _ in mets]
        ax.bar(xs, vals, wdt * 0.82, color=col[b], label=name[b])
        for x, v in zip(xs, vals):
            if v >= 0.04:
                ax.text(x, v + 0.006, fnum(v, 2), ha='center', va='bottom', fontsize=6.8, color=BODY)
    ax.set_xticks(range(len(mets)))
    ax.set_xticklabels([l for _, l in mets])
    ax.set_ylim(0, 0.25)
    ax.set_title('Retrieval-only baselines on 56 verified validation questions (42 with a non-empty answer)', pad=6)
    ax.legend(ncol=4, loc='upper center', bbox_to_anchor=(0.5, -0.13))
    tidy(ax, xgrid=False, ygrid=True)
    save(fig, 'c_baselines')
    fig, ax = plt.subplots(figsize=(7.3, 2.1))
    vals = [[get(b, 'modality/%s' % m, 'gold_coverage') for m in MOD_ORDER] for b in B]
    heatmap(ax, [name[b] for b in B], MOD_ORDER, vals, vmin=0, vmax=1, xlabels=[MOD_NAME[m] for m in MOD_ORDER])
    ax.set_title('Gold coverage by the sources a question needs (share of correct papers retrieved)', pad=22)
    return save(fig, 'c_baselines_modality')


# ======================================================================= RQ1
def rq1():
    method_panels(R1, ['answer_f1', 'answerable_f1', 'mrr', 'gold_coverage', 'input_tokens', 'latency'], 'c_rq1_metrics', ci=True)
    scatter(R1, 'input_tokens', 'answer_f1', 'c_rq1_quality_cost', 'Input tokens per question (lower is cheaper)', 'Answer F1 (higher is better)',
            note='Pareto-optimal methods (★) are joined by the grey line; triangles are beaten on every axis by some other method.')
    ms = R1['methods']
    fig, axes = plt.subplots(2, 2, figsize=(7.3, 4.6))
    fig.subplots_adjust(wspace=0.32, hspace=0.75)
    for ax, (dim, k) in zip(axes.flat, [('modality', 'answer_f1'), ('modality', 'gold_coverage'), ('stress', 'answer_f1'), ('stress', 'input_tokens')]):
        groups = [g for g in (['G', 'TG', 'GS', 'TGS'] if dim == 'modality' else ['normal', 'noisy', 'conflict', 'unanswerable']) if g in R1['strata'][dim]]
        grouped(ax, groups, ms, lambda g, m: R1['strata'][dim][g][m].get(k), k,
                [(MOD_NAME.get(g, g) + ' (n=%d)' % R1['strata_n']['%s:%s' % (dim, g)]) for g in groups])
        ax.set_title('%s by %s' % (LABEL[k], 'sources needed' if dim == 'modality' else 'variant'), pad=6)
    axes[0][0].legend(ncol=5, loc='upper left', bbox_to_anchor=(0, 1.42), handlelength=1.0, columnspacing=1.0)
    save(fig, 'c_rq1_strata')
    forest_fig(R1, ['answer_f1'], 'c_rq1_tests')
    ranking(R1, 'c_rq1_ranking')


def grouped(ax, groups, methods, getv, metric, glabels=None):
    n = len(methods)
    wdt = 0.82 / n
    sc = scale(metric)
    for j, m in enumerate(methods):
        xs = [i - 0.41 + wdt * (j + .5) for i in range(len(groups))]
        vals = [(getv(g, m) or 0) * sc for g in groups]
        ax.bar(xs, vals, wdt * 0.84, color=mcolor(m), label=m)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([g.replace(' (', '\n(') for g in (glabels or groups)], fontsize=7.8)
    tidy(ax, xgrid=False, ygrid=True)


# ======================================================================= RQ2
def rq2():
    method_panels(R2, ['mrr', 'input_tokens', 'output_tokens', 'llm_calls', 'latency', 'total_tokens'], 'c_rq2_metrics')
    scatter(R2, 'input_tokens', 'latency', 'c_rq2_quality_cost', 'Input tokens per question (lower is cheaper)', 'Latency in seconds (lower is faster)',
            note='Every method returned the same (empty) answers, so only cost separates them: down and to the left is better.')
    ms = R2['methods']
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.7), gridspec_kw={'width_ratios': [0.8, 1.6]})
    fig.subplots_adjust(wspace=0.32)
    ax = axes[0]
    cnt = R2['supportability']['counts']
    keys = [('FULLY_SUPPORTABLE', 'Fully', STATUS['good']), ('PARTIALLY_SUPPORTABLE', 'Partially', STATUS['warning']), ('UNSUPPORTABLE', 'Not at all', STATUS['critical'])]
    for i, (k, lab, c) in enumerate(keys):
        ax.bar(i, cnt[k], width=0.55, color=c)
        ax.text(i, cnt[k] + 0.3, '%d' % cnt[k], ha='center', va='bottom', fontsize=9, color=BODY)
    ax.set_xticks(range(3))
    ax.set_xticklabels([l for _, l, _ in keys])
    ax.set_title('Bundles holding the correct papers', pad=6)
    ax.set_ylim(0, 19)
    tidy(ax, xgrid=False, ygrid=True)
    groups = ['TG', 'TS', 'GS', 'TGS']
    grouped(axes[1], groups, ms, lambda g, m: R2['strata']['modality'][g][m].get('total_tokens'), 'total_tokens',
            [MOD_NAME[g] + ' (n=6)' for g in groups])
    axes[1].set_title('Total tokens per question, by sources needed', pad=6)
    axes[1].legend(ncol=5, loc='upper left', bbox_to_anchor=(0, -0.2), handlelength=1.0, columnspacing=1.0)
    save(fig, 'c_rq2_support_tokens')
    forest_fig(R2, ['input_tokens', 'latency', 'llm_calls'], 'c_rq2_tests')
    ranking(R2, 'c_rq2_ranking')


# ======================================================================= RQ3
STOP_TEXT = {'all_sources_retrieved': 'searched every source', 'routed_sources_retrieved': 'searched every routed source',
             'max_multi_steps': 'hit 3-search limit', 'sufficient': 'evidence judged sufficient', 'good': 'evidence rated GOOD',
             'sources_exhausted': 'no source left to add', 'max_correction_rounds': 'hit 2-round limit', 'validator_accepted': 'validator accepted',
             'max_iterations_rejected': '4 iterations, no acceptance'}
CHOSEN = {'sufficient', 'good', 'validator_accepted'}
LIMIT = {'max_multi_steps', 'max_correction_rounds', 'max_iterations_rejected'}


def rq3():
    method_panels(R3, ['answer_f1', 'source_f1', 'unnecessary_retrieval', 'stopping_accuracy', 'retrieval_calls', 'llm_calls', 'total_tokens', 'latency'],
                  'c_rq3_metrics', ncols=4, w=7.4, h=1.9)
    scatter(R3, 'total_tokens', 'source_f1', 'c_rq3_quality_cost', 'Tokens per question (lower is cheaper)', 'Source-selection F1 (higher is better)',
            note='All policies gave identical answers (answer F1 0.154), so the chart uses source selection as the quality axis.')
    ms = R3['methods']
    # stop reasons
    fig, ax = plt.subplots(figsize=(7.4, 2.4))
    ys = list(range(len(ms)))[::-1]
    for y, m in zip(ys, ms):
        left, parts = 0, []
        for reason, n in sorted(R3['stop_reasons'][m].items(), key=lambda kv: (kv[0] in LIMIT, kv[0] not in CHOSEN, kv[0])):
            if reason in LIMIT:
                ax.barh(y, n, left=left, height=0.58, color='#e2e8f0', hatch='////', edgecolor='#94a3b8', linewidth=0)
                tc = BODY
            elif reason in CHOSEN:
                ax.barh(y, n, left=left, height=0.58, color=mcolor(m))
                tc = 'white'
            else:
                ax.barh(y, n, left=left, height=0.58, color=mcolor(m), alpha=0.45)
                tc = INK
            ax.text(left + n / 2, y, '%d' % n, ha='center', va='center', fontsize=8, color=tc, fontweight='semibold')
            parts.append('%s %d' % (STOP_TEXT[reason], n))
            left += n
            ax.plot([left, left], [y - .29, y + .29], color='white', linewidth=2)
        ax.text(29.2, y, '  ·  '.join(parts), ha='left', va='center', fontsize=7.7, color=BODY)
    ax.set_yticks(ys)
    ax.set_yticklabels(ms)
    ax.set_xlim(0, 28)
    ax.set_xticks([0, 7, 14, 21, 28])
    ax.set_xlabel('Questions (28 per policy)')
    ax.set_title('Why each run stopped', pad=6)
    tidy(ax)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color='#64748b', label='policy decided to stop'), Patch(color='#64748b', alpha=0.45, label='fixed plan completed'),
                       Patch(facecolor='#e2e8f0', hatch='////', edgecolor='#94a3b8', label='hit a limit')], ncol=3, loc='upper left', bbox_to_anchor=(0, -0.3))
    fig.subplots_adjust(right=0.52)
    save(fig, 'c_rq3_stops')
    # failure taxonomy (rows: labels; columns: policies)
    fx = R3['failure_taxonomy']
    labels = sorted({k for v in fx.values() for k in v}, key=lambda l: -sum(fx[m].get(l, 0) for m in ms))
    fig, ax = plt.subplots(figsize=(6.2, 0.31 * len(labels) + 0.8))
    heatmap(ax, [l.replace('_', ' ') for l in labels], ms, [[fx[m].get(l, 0) or None for m in ms] for l in labels], fmtfn=lambda v: '%d' % v,
            vmin=0, vmax=28, empty='0')
    ax.set_title('Failure labels: questions (of 28) carrying each label', pad=20)
    save(fig, 'c_rq3_failures')
    # strata heatmaps
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.3))
    fig.subplots_adjust(wspace=0.42)
    S = R3['strata']['modality']
    heatmap(axes[0], ms, MOD_ORDER, [[S[g][m]['source_f1'] for g in MOD_ORDER] for m in ms], fmtfn=lambda v: fnum(v, 2), vmin=0, vmax=1)
    axes[0].set_title('Source-selection F1', pad=22)
    heatmap(axes[1], ms, MOD_ORDER, [[S[g][m]['total_tokens'] for g in MOD_ORDER] for m in ms], fmtfn=lambda v: '%.1fk' % (v / 1000.),
            ramp=['#fff7ed', '#fed7aa', '#fb923c', '#ea580c', '#9a3412'])
    axes[1].set_title('Tokens per question', pad=22)
    save(fig, 'c_rq3_strata')
    forest_fig(R3, ['source_f1', 'total_tokens', 'latency', 'unnecessary_retrieval'], 'c_rq3_tests', w=7.3)
    forest_fig(R3, ['retrieval_calls', 'stopping_accuracy'], 'c_rq3_tests_more', w=7.3)
    ranking(R3, 'c_rq3_ranking')


def ar01_ar02():
    T = load('documentation/phase9/ar01/training_report.json')
    C = load('documentation/phase9/calibration/ar02_calibration.json')
    fig, axes = plt.subplots(1, 2, figsize=(7.3, 2.6), gridspec_kw={'width_ratios': [1.35, 1]})
    fig.subplots_adjust(wspace=0.4)
    ax = axes[0]
    ep = [e['epoch'] for e in T['epochs']]
    ax.plot(ep, [e['train_loss'] for e in T['epochs']], color='#94a3b8', linewidth=2, marker='o', markersize=4, label='training loss')
    ax.plot(ep, [e['dev_loss'] for e in T['epochs']], color='#2563eb', linewidth=2, marker='o', markersize=4, label='development loss')
    b = T['best_epoch']
    bd = T['epochs'][b - 1]['dev_loss']
    ax.scatter([b], [bd], s=90, facecolor='none', edgecolor='#f59e0b', linewidth=2, zorder=4)
    ax.annotate('best epoch %d (dev loss %s) is kept;\ntraining stopped after epoch %d\n(no improvement for 2 epochs)' % (b, fnum(bd, 4), ep[-1]), (b, bd),
                xytext=(3.0, 0.58), textcoords='data', fontsize=7.8, color=BODY, arrowprops=dict(arrowstyle='-', color='#94a3b8'))
    ax.set_xticks(ep)
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Cross-entropy loss')
    ax.set_ylim(0.15, 0.85)
    ax.set_title('AR-01 classifier training (t5-base)', pad=6)
    ax.legend(loc='upper right')
    tidy(ax, xgrid=False, ygrid=True)
    ax = axes[1]
    cls = ['A', 'B', 'C']
    tr, dv = T['train_counts'], T['dev_counts']
    xs = np.arange(3)
    ax.bar(xs - 0.18, [tr[c] for c in cls], 0.34, color='#334155', label='train (7,302)')
    ax.bar(xs + 0.18, [dv[c] for c in cls], 0.34, color='#94a3b8', label='dev (747)')
    for x, c in zip(xs, cls):
        ax.text(x - 0.18, tr[c] + 90, fmt(tr[c], 'count'), ha='center', fontsize=7.6, color=BODY)
        ax.text(x + 0.18, dv[c] + 90, fmt(dv[c], 'count'), ha='center', fontsize=7.6, color=BODY)
    ax.set_xticks(xs)
    ax.set_xticklabels(['A\nno retrieval', 'B\none source', 'C\nmulti-step'])
    ax.set_ylim(0, 6600)
    ax.set_title('Oracle route labels', pad=6)
    ax.legend(loc='upper left')
    tidy(ax, xgrid=False, ygrid=True)
    save(fig, 'c_ar01')

    fig, axes = plt.subplots(1, 2, figsize=(7.3, 2.75), gridspec_kw={'width_ratios': [1.25, 1]})
    fig.subplots_adjust(wspace=0.45)
    ax = axes[0]
    a, b0 = C['platt']['coef'], C['platt']['intercept']
    s = np.linspace(-12, 12, 400)
    p = 1 / (1 + np.exp(-(a * s + b0)))
    lo, up = C['thresholds']['lower'], C['thresholds']['upper']
    s_lo = (math.log(lo / (1 - lo)) - b0) / a
    s_up = (math.log(up / (1 - up)) - b0) / a
    ax.axhspan(up, 1, color='#dcfce7', zorder=0)
    ax.axhspan(0, lo, color='#fee2e2', zorder=0)
    ax.plot(s, p, color='#2563eb', linewidth=2)
    ax.axhline(up, color='#16a34a', linewidth=1)
    ax.axhline(lo, color='#dc2626', linewidth=1)
    ax.text(-11.6, (up + 1) / 2, 'GOOD if the best item has p ≥ %s\n(raw score ≥ %s)' % (fnum(up, 2), fnum(s_up, 2)), fontsize=7.6, va='center', color='#166534')
    ax.text(-11.6, lo / 2, 'BAD if every item has p ≤ %s\n(raw score ≤ %s)' % (fnum(lo, 2), fnum(s_lo, 2)), fontsize=7.6, va='center', color='#991b1b')
    ax.text(2.5, (lo + up) / 2, 'otherwise AMBIGUOUS', fontsize=7.6, va='center', color='#92400e')
    ax.set_xlabel('Raw cross-encoder score s')
    ax.set_ylabel('Calibrated relevance p')
    ax.set_title(r'AR-02 Platt calibration: $p = 1/(1+e^{-(%s\,s\,+\,%s)})$' % (fnum(a, 3), fnum(b0, 3)), pad=6, fontsize=9.2)
    ax.set_ylim(0, 1)
    tidy(ax, xgrid=True, ygrid=False)
    ax = axes[1]
    lows, ups = C['grids']['lower'], C['grids']['upper']
    G = {(g['lower'], g['upper']): g['macro_f1'] for g in C['grid']}
    vals = [[G.get((l, u)) for u in ups] for l in lows]
    heatmap(ax, ['%.2f' % l for l in lows], ['%.2f' % u for u in ups], vals, fmtfn=lambda v: fnum(v, 3),
            highlight=[(lows.index(lo), ups.index(up))])
    ax.set_xlabel('UPPER threshold')
    ax.xaxis.set_label_position('top')
    ax.set_ylabel('LOWER threshold')
    ax.set_title('Macro-F1 on the 2,235 development states', pad=30)
    return save(fig, 'c_ar02')


# ======================================================================= RQ4 and overall
def rq4():
    ms = ['AR-B0', 'AR-B1', 'INT-1']
    d = R4['descriptive']
    fig, axes = panels(4, 4, 7.4, 1.75)
    for k, ax in zip(['answer_f1', 'source_f1', 'total_tokens', 'latency'], axes):
        bars(ax, ms, [d[m][k] * scale(k) for m in ms], [mcolor(m) for m in ms], labels=[fmt(d[m][k], KIND[k]) for m in ms], title=LABEL[k] + ARROW(k))
    save(fig, 'c_rq4_metrics')
    forest_fig(R4, ['source_f1', 'total_tokens', 'latency'], 'c_rq4_tests')


def overall():
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.1))
    fig.subplots_adjust(wspace=0.75)
    for ax, rq, t in zip(axes, ('RQ1', 'RQ2', 'RQ3'), ('Part 1 · context', 'Part 2 · fusion', 'Part 3 · retrieval control')):
        o = RES[rq]['overall']
        ms = o['order']
        bars(ax, ms, [o['total'][m] for m in ms], [mcolor(m) for m in ms], labels=['%g' % o['total'][m] for m in ms], title=t, xmax=21,
             xlabel='rank total (lower wins)')
    save(fig, 'c_overall_totals')


def upstream():
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.5), gridspec_kw={'width_ratios': [1.3, 1, 1]})
    fig.subplots_adjust(wspace=0.95)
    ms = R1['methods']
    d = R1['descriptive']
    ax = axes[0]
    ys = list(range(len(ms)))[::-1]
    for y, m in zip(ys, ms):
        un = 8 / 32.
        an = 24 / 32. * d[m]['answerable_f1']
        ax.barh(y, un, height=0.56, color='#cbd5e1')
        ax.barh(y, an, left=un, height=0.56, color=mcolor(m))
        ax.text(un + an + 0.006, y, fmt(d[m]['answer_f1']), va='center', fontsize=8, color=BODY)
    ax.set_yticks(ys)
    ax.set_yticklabels(ms)
    ax.set_xlim(0, 0.36)
    ax.set_title('Part 1: sources of answer F1', pad=6)
    ax.set_xlabel('grey: 8 unanswerable questions\ncolour: 24 answerable questions')
    tidy(ax)
    bars(axes[1], ms, [d[m]['gold_coverage'] for m in ms], [mcolor(m) for m in ms], title='Part 1: gold coverage', xmax=0.5)
    ax = axes[2]
    S = R3['strata']['modality']
    vals = [S[g]['AR-B1']['answer_f1'] for g in MOD_ORDER]
    bars(ax, [MOD_NAME[g] for g in MOD_ORDER], vals, ['#475569'] * 7, title='Part 3: answer F1 by sources', xmax=1.35)
    return save(fig, 'c_upstream')


def signflip_bootstrap():
    d = DEMO[0]
    fams = sorted(d['family_sums'])
    mod = {}
    for q, r in Q.items():
        mod[r['family']] = r['modality']
    order = sorted(fams, key=lambda f: (MOD_ORDER.index(mod[f]), f))
    seen = {}
    lab = []
    for f in order:
        seen[mod[f]] = seen.get(mod[f], 0) + 1
        lab.append('%s-%d' % (mod[f], seen[mod[f]]))
    sums = np.array([d['family_sums'][f] for f in order])
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.5), gridspec_kw={'width_ratios': [1.3, 1, 1]})
    fig.subplots_adjust(wspace=0.45)
    ax = axes[0]
    ax.bar(range(len(sums)), sums, color=['#16a34a' if v > 0 else ('#dc2626' if v < 0 else '#94a3b8') for v in sums], width=0.6)
    ax.axhline(0, color='#94a3b8', linewidth=0.8)
    ax.set_xticks(range(len(sums)))
    ax.set_xticklabels(lab, rotation=90, fontsize=7)
    ax.set_title('1 · Family sums of A − B', pad=6)
    tidy(ax, xgrid=False, ygrid=True)
    ax = axes[1]
    signs = np.array(list(itertools.product((-1., 1.), repeat=len(sums))))
    totals = signs @ sums
    obs = float(sums.sum())
    p = float(np.mean(np.abs(totals) >= abs(obs) - 1e-12))
    vals, counts = np.unique(np.round(totals, 9), return_counts=True)
    ax.bar(vals, counts, width=0.18, color=['#dc2626' if abs(v) >= abs(obs) - 1e-9 else '#94a3b8' for v in vals])
    ax.axvline(obs, color='#dc2626', linewidth=1.2)
    ax.set_title('2 · All %s sign flips' % fmt(len(totals), 'count'), pad=6)
    ax.text(0.02, 0.97, 'observed total %s\np = %s (reported %s)' % (fnum(obs, 3), fnum(p, 4), fnum(d['reported']['p'], 4)),
            transform=ax.transAxes, fontsize=7.4, va='top', color=BODY, bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor='#e2e8f0', alpha=0.95))
    ax.set_xlabel('total of the flipped family sums')
    tidy(ax, xgrid=False, ygrid=True)
    ax = axes[2]
    names = sorted(d['family_sums'])
    s_ = [d['family_sums'][g] for g in names]
    c_ = [d['family_sizes'][g] for g in names]
    rng = random.Random(42)
    samples = []
    for _ in range(10000):
        picks = [rng.randrange(len(names)) for _ in names]
        samples.append(sum(s_[i] for i in picks) / sum(c_[i] for i in picks))
    samples.sort()
    lo, hi = samples[int(.025 * 10000)], samples[int(.975 * 10000) - 1]
    ax.hist(samples, bins=40, color='#94a3b8')
    ax.axvline(lo, color='#2563eb', linewidth=1.2)
    ax.axvline(hi, color='#2563eb', linewidth=1.2)
    ax.axvline(obs / sum(c_), color=INK, linewidth=1.2)
    rep = next(t for t in R3['tests']['source_f1'] if t['a'] == d['a'] and t['b'] == d['b'])
    ax.set_title('3 · 10,000 family bootstraps', pad=6)
    ax.text(0.02, 0.97, 'mean Δ %s\n95%% CI [%s, %s]\nreported [%s, %s]' % (fnum(obs / sum(c_), 3), fnum(lo, 3), fnum(hi, 3), fnum(rep['ci95'][0], 3),
                                                                           fnum(rep['ci95'][1], 3)), transform=ax.transAxes, fontsize=7.2, va='top', color=BODY,
            bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor='#e2e8f0', alpha=0.95))
    ax.set_xlabel('mean per-question difference')
    tidy(ax, xgrid=False, ygrid=True)
    save(fig, 'c_stats_example')
    return {'p': p, 'reported_p': d['reported']['p'], 'ci': [lo, hi], 'reported_ci': rep['ci95']}


if __name__ == '__main__':
    dataset()
    benchmark()
    baselines()
    rq1()
    rq2()
    rq3()
    ar01_ar02()
    rq4()
    overall()
    upstream()
    print('stats example check', signflip_bootstrap())
    print('charts written to', OUT)


def tests_growth():
    pts = [('Phase 0', 18), ('Phase 1', 39), ('Phase 2', 51), ('Phase 3', 68), ('Phase 4', 84), ('Phase 5', 105), ('Phase 6', 125), ('Phase 6.5', 135),
           ('Phase 7', 161), ('Phase 8', 185), ('Repair', 215), ('Exec. checks', 230), ('RQ3 freeze', 273), ('Showcase', 327)]
    fig, ax = plt.subplots(figsize=(7.3, 2.5))
    xs = range(len(pts))
    ax.bar(xs, [v for _, v in pts], width=0.56, color='#2563eb')
    for x, (_, v) in zip(xs, pts):
        ax.text(x, v + 5, str(v), ha='center', va='bottom', fontsize=7.8, color=BODY)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([l for l, _ in pts], rotation=35, ha='right', fontsize=7.8)
    ax.set_ylim(0, 370)
    ax.set_ylabel('tests passing')
    tidy(ax, xgrid=False, ygrid=True)
    return save(fig, 'c_tests')


if __name__ == '__main__':
    tests_growth()
