"""Figures for the single-column (Scientific Reports style) paper.

1. Re-renders selected documentation diagrams and charts (project_documentation/build) in the paper typeface at 600 dpi.
2. Draws two new analysis figures from the frozen results: the cost landscape of all strategies and the statistical
   power of the exact sign-flip test with Holm correction.
3. Frames screenshots of the showcase application (captured from the running app) for print.
The 16 figures of the IEEE paper are used directly from ../../ieee/figures.

Run: python scirep_figs.py   (writes PNG files to ../figures)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOC = HERE.parents[2] / 'project_documentation'
sys.path.insert(0, str(DOC / 'build'))
OUT = HERE.parent / 'figures'
OUT.mkdir(parents=True, exist_ok=True)

import matplotlib                                         # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                          # noqa: E402
import figlib as FL                                      # noqa: E402

FONT = ['Times New Roman', 'Segoe UI Symbol', 'DejaVu Sans']


def save(fig, name, dpi=600):
    path = OUT / (name + '.png')
    fig.savefig(path, dpi=dpi, bbox_inches='tight', pad_inches=0.06, metadata={'Software': None})
    plt.close(fig)
    return path


FL.OUT = OUT
FL.save = save
import make_diagrams as MD                               # noqa: E402
import make_charts as MC                                 # noqa: E402
MD.save = MC.save = save
plt.rcParams['font.family'] = FONT
plt.rcParams['mathtext.fontset'] = 'stix'

from PIL import Image, ImageOps                          # noqa: E402

RES = FL.RES
STUDY_COL = {'RQ1': '#2563eb', 'RQ2': '#0d9488', 'RQ3': '#ea580c', 'RQ4': '#7c3aed'}
MARK = {'RQ1': 'o', 'RQ2': 's', 'RQ3': '^', 'RQ4': 'D'}
WIN = {'CM-B1', 'CF-B1', 'AR-B1', 'INT-1'}


def tokens(rq, m):
    d = RES[rq]['descriptive'][m]
    return d['total_tokens'] if d.get('total_tokens') is not None else d['input_tokens'] + d['output_tokens']


def cost_landscape():
    pts = [(rq, m) for rq in ('RQ1', 'RQ2', 'RQ3') for m in RES[rq]['methods']] + [('RQ4', 'INT-1')]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.1, 3.3), gridspec_kw={'width_ratios': [1.45, 1], 'wspace': 0.32})
    off = {'CM-B1': (7, -3, 'left'), 'CM-02': (5, -3, 'left'), 'AR-B1': (0, 6, 'center'), 'AR-02': (0, 5, 'center'),
           'AR-B0': (2, 6, 'left'), 'INT-1': (6, -8, 'left'), 'CF-B1': (6, -7, 'left'), 'CF-02': (-5, 2, 'right'),
           'CF-B0': (-5, 3, 'right'), 'CM-B0': (6, 1, 'left'), 'CF-01': (6, -5, 'left'), 'CM-01': (6, -2, 'left'),
           'CF-03': (-5, 1, 'right'), 'AR-01': (6, 0, 'left'), 'AR-03': (-6, -2, 'right'), 'CM-03': (-6, -2, 'right')}
    for rq, m in pts:
        x, y = tokens(rq, m), RES[rq]['descriptive'][m]['latency'] / 1000
        a.scatter(x, y, s=48 if m in WIN else 26, marker=MARK[rq], color=STUDY_COL[rq], edgecolor='black' if m in WIN else 'white',
                  linewidth=1.0 if m in WIN else 0.4, zorder=3)
        dx, dy, ha = off[m]
        a.annotate(m, (x, y), xytext=(dx, dy), textcoords='offset points', fontsize=6.4, ha=ha, va='center',
                   color='#111111', fontweight='bold' if m in WIN else 'normal')
    a.set_xscale('log')
    a.set_yscale('log')
    a.set_xticks([1500, 2000, 3000, 4000, 6000, 8000])
    a.set_xticklabels(['1.5k', '2k', '3k', '4k', '6k', '8k'])
    a.set_yticks([6, 8, 10, 15, 20, 30, 45])
    a.set_yticklabels(['6', '8', '10', '15', '20', '30', '45'])
    a.minorticks_off()
    a.set_xlabel('tokens per question (input + output, log scale)', fontsize=7.4)
    a.set_ylabel('intrinsic latency per question (s, log scale)', fontsize=7.4)
    a.tick_params(labelsize=6.8)
    a.grid(True, color='#e5e7eb', linewidth=0.5)
    a.set_axisbelow(True)
    for s in ('top', 'right'):
        a.spines[s].set_visible(False)
    for rq, lab in (('RQ1', 'RQ1 context mgmt.'), ('RQ2', 'RQ2 fusion'), ('RQ3', 'RQ3 retrieval control'), ('RQ4', 'RQ4 integrated')):
        a.scatter([], [], marker=MARK[rq], color=STUDY_COL[rq], s=24, label=lab)
    a.legend(fontsize=6.2, loc='upper left', frameon=False)
    a.text(0.5, -0.25, '(a) cost of every strategy (outlined, bold: overall winners)', transform=a.transAxes, ha='center', fontsize=7.6)
    names = [m for _, m in pts]
    calls = [RES[rq]['descriptive'][m]['llm_calls'] for rq, m in pts]
    cols = [STUDY_COL[rq] for rq, _ in pts]
    y = range(len(names))[::-1]
    b.barh(list(y), calls, color=cols, height=0.62)
    for yy, c in zip(y, calls):
        b.text(c + 0.08, yy, '%.2f' % c, va='center', fontsize=6.0)
    b.set_yticks(list(y))
    b.set_yticklabels(names, fontsize=6.2)
    b.set_xlabel('model calls per question', fontsize=7.4)
    b.tick_params(axis='x', labelsize=6.8)
    b.set_xlim(0, 7.6)
    for s in ('top', 'right'):
        b.spines[s].set_visible(False)
    b.text(0.5, -0.25, '(b) model calls', transform=b.transAxes, ha='center', fontsize=7.6)
    save(fig, 'sr_cost_landscape')


def power():
    import numpy as np
    F = np.arange(4, 21)
    fig, ax = plt.subplots(figsize=(3.45, 2.45))
    for k, c in ((1, '#64748b'), (2, '#7c3aed'), (7, '#0d9488'), (10, '#2563eb')):
        p = np.minimum(1.0, k * 2.0 / 2.0 ** F)
        ax.plot(F, p, marker='o', ms=2.6, lw=1.0, color=c, label='%d pair%s' % (k, '' if k == 1 else 's'))
    ax.axhline(0.05, color='#dc2626', lw=0.8, ls='--')
    ax.text(20.2, 0.06, '0.05', color='#dc2626', fontsize=6.4, ha='right', va='bottom')
    for f, lab in ((8, 'RQ1, RQ2\n(8 families)'), (14, 'RQ3, RQ4\n(14 families)')):
        ax.axvline(f, color='#9ca3af', lw=0.6, ls=':')
        ax.text(f + 0.25, 0.22, lab, fontsize=6.0, color='#444444', va='center', ha='left')
    ax.set_yscale('log')
    ax.set_ylim(1e-4, 1.5)
    ax.set_xlim(4, 20.3)
    ax.set_xlabel('number of independent families F', fontsize=7.4)
    ax.set_ylabel('smallest attainable Holm-adjusted p', fontsize=7.4)
    ax.tick_params(labelsize=6.8)
    ax.legend(fontsize=6.2, frameon=False, loc='lower left')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    save(fig, 'sr_power')


SCR = DOC / 'screens'


def framed(name, box=None, out=None, width=None):
    im = Image.open(SCR / (name + '.png')).convert('RGB')
    if box:
        im = im.crop(box)
    if width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im = ImageOps.expand(im, border=2, fill='#9ca3af')
    im.save(OUT / ((out or name) + '.png'), dpi=(300, 300))
    return im


def panels(items, name, ncols=2, w=7.1, dpi=400):
    """Screenshots side by side with (a), (b) ... captions underneath."""
    ims = [Image.open(SCR / (n + '.png')).convert('RGB').crop(box) if box else Image.open(SCR / (n + '.png')).convert('RGB')
           for n, box, _ in items]
    nrows = (len(ims) + ncols - 1) // ncols
    ratios = []
    for r in range(nrows):
        row = ims[r * ncols:(r + 1) * ncols]
        ratios.append(max(im.height / im.width for im in row))
    pw = w / ncols
    fig = plt.figure(figsize=(w, sum(pw * r + 0.28 for r in ratios)))
    gs = fig.add_gridspec(nrows, ncols, height_ratios=[r + 0.28 / pw for r in ratios], hspace=0.06, wspace=0.05)
    for i, (im, (_, _, cap)) in enumerate(zip(ims, items)):
        ax = fig.add_subplot(gs[i // ncols, i % ncols])
        ax.imshow(im, interpolation='lanczos')
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color('#9ca3af')
            s.set_linewidth(0.6)
        ax.set_xlabel('(%s) %s' % ('abcdefgh'[i], cap), fontsize=7.8, labelpad=3)
    save(fig, name, dpi=dpi)


def screenshots():
    panels([('p01_problem__view', None, 'Landing page: the problem and a real benchmark question'),
            ('p02_parts__view', None, 'The four studies, one variable at a time'),
            ('p03_data__view', None, 'Data and benchmark: three views of one corpus'),
            ('p09_summary__view', None, 'Conclusions: the winner of each study')], 'sr_app_pages')
    panels([('p03_data__03', None, 'One paper seen through the text, structured and graph views'),
            ('p04_metrics__06', None, 'The sign-flip test recomputed on real per-question results')], 'sr_app_data_stats')
    panels([('p05_rq1__10', (0, 0, 1425, 1650), 'RQ1 explorer: CM-01 context with the graph evidence drawn'),
            ('p06_rq2__10', None, 'RQ2 explorer: an empty answer explained (correct paper seen, rejected)')], 'sr_app_rq12')
    framed('p07_rq3_compare__12', out='sr_app_rq3_trace')
    panels([('p10_try_compare__02', (0, 0, 1425, 1480), 'Try a question: two recorded pipelines side by side'),
            ('p11_repro__03', None, 'Reproducibility: bundle checksum and verified frozen sources')], 'sr_app_try_repro')


if __name__ == '__main__' and sys.argv[1:] == ['new']:
    cost_landscape()
    power()
    sys.exit(0)
if __name__ == '__main__':
    for f in (MD.timeline, MD.architecture, MD.data_build, MD.benchmark_flow, MD.execution, MD.app_bundle, MD.app_map,
              MC.dataset, MC.benchmark, MC.baselines, MC.ar01_ar02, MC.rq3):
        f()
    print('stats example check', MC.signflip_bootstrap())
    cost_landscape()
    power()
    screenshots()
    print('figures written to', OUT)
