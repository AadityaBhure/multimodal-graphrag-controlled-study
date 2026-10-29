"""Figures for the IEEE paper (serif type, sized for 3.45-inch columns and 7.1-inch double columns).

Every chart reads the frozen study results through the checksummed showcase bundle; diagrams are hand-placed.
Run: python paper_figs.py   (writes 600-dpi PNG files for the Word build and vector PDFs for the LaTeX build to ../figures)
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'project_documentation' / 'build'))
import figlib as FL                                    # noqa: E402  (shared data loading, colours, Flow diagrams)
from figlib import RES, FOUND, mcolor, fnum, fmt, Flow, KINDS, heatmap   # noqa: E402

import numpy as np                                      # noqa: E402
import matplotlib.pyplot as plt                         # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon, FancyArrowPatch   # noqa: E402

OUT = HERE.parent / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
COL, WIDE = 3.45, 7.1
INK, BODY, MUTED, FAINT, GRID = '#111111', '#222222', '#444444', '#6b7280', '#e5e7eb'

plt.rcParams.update({
    'font.family': ['Times New Roman', 'Segoe UI Symbol', 'DejaVu Sans'], 'mathtext.fontset': 'stix', 'font.size': 7.6, 'axes.titlesize': 7.8, 'axes.labelsize': 7.4,
    'xtick.labelsize': 6.8, 'ytick.labelsize': 6.8, 'legend.fontsize': 6.6, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
    'axes.titlecolor': INK, 'axes.labelcolor': BODY, 'xtick.color': BODY, 'ytick.color': BODY, 'axes.edgecolor': '#9ca3af',
    'axes.linewidth': 0.6, 'legend.frameon': False, 'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'pdf.fonttype': 42,                                 # TrueType in PDFs (IEEE PDF eXpress rejects Type 3 fonts)
})
R1, R2, R3, R4 = RES['RQ1'], RES['RQ2'], RES['RQ3'], RES['RQ4']
MOD_ORDER = ['T', 'G', 'S', 'TG', 'TS', 'GS', 'TGS']


def pfmt(v, kind):
    if kind == 'r1':
        return fnum(v, 1)
    if kind == 'r2':
        return fnum(v, 2)
    return fmt(v, kind)


def save(fig, name):
    """PNG (600 dpi) for the Word build and vector PDF with embedded TrueType fonts for the LaTeX build."""
    fig.savefig(OUT / (name + '.png'), dpi=600, bbox_inches='tight', pad_inches=0.03, metadata={'Software': None})
    fig.savefig(OUT / (name + '.pdf'), bbox_inches='tight', pad_inches=0.03,
                metadata={'Creator': None, 'Producer': None, 'CreationDate': None})
    plt.close(fig)


def clean(ax, grid='x'):
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=2, width=0.5)
    if grid:
        getattr(ax, grid + 'axis').grid(True, color=GRID, linewidth=0.5)
        ax.set_axisbelow(True)


def sub(ax, letter, text=None, y=-0.3):
    ax.text(0.5, y, '(%s)%s' % (letter, (' ' + text) if text else ''), transform=ax.transAxes, ha='center', va='top', fontsize=7.6)


class PFlow(Flow):
    """Flow diagrams in the paper's serif type."""

    def __init__(self, w, h, fs=6.8):
        super().__init__(w, h, None, fs)


# ===================================================================================== Fig. framework
def framework():
    F = PFlow(WIDE, 3.25, fs=6.6)
    F.box('dl', 1.0, 1.68, 1.86, 3.2, 'Data layer (Sec. III-B)', 'group', fs=6.8)
    F.box('src', 1.0, 2.86, 1.62, 0.5, 'STaRK-MAG\n700,244 papers · 1.87 M entities · 19.9 M relations', 'io', bold_first=True, fs=6.2)
    F.box('vt', 1.0, 2.15, 1.62, 0.46, 'Text view $V_T$\ntitle + abstract; MiniLM + exact FAISS', 'text', bold_first=True, fs=6.1)
    F.box('vg', 1.0, 1.55, 1.62, 0.46, 'Graph view $V_G$\nwrites, affiliated, cites, has-topic (CSR)', 'graph', bold_first=True, fs=6.1)
    F.box('vs', 1.0, 0.95, 1.62, 0.46, 'Structured view $V_S$\nyear, citations, rank, venue (DuckDB)', 'structured', bold_first=True, fs=6.1)
    F.note(0.24, 0.6, 'views joined only by the global node ID;\neach retriever reads only its own view', fs=5.9, color=FAINT)
    F.edge('src', 'vt')
    F.box('pl', 3.92, 1.68, 3.78, 3.2, 'Retrieval pipeline, studied one component at a time (Sec. III-D to III-G)', 'group', fs=6.8)
    F.box('q', 2.38, 2.86, 0.6, 0.38, 'Question $q$', 'io', fs=6.2)
    F.box('ar', 3.22, 2.86, 0.9, 0.46, 'Retrieval control $\\pi$\nRQ3 · RG3', 'rq', bold_first=True, fs=6.2)
    F.box('b1', 4.2, 3.0, 0.82, 0.24, 'B1 dense text', 'text', fs=5.9)
    F.box('b2', 4.2, 2.72, 0.82, 0.24, 'B2 graph BFS', 'graph', fs=5.9)
    F.box('b3', 4.2, 2.44, 0.82, 0.24, 'B3 typed SQL', 'structured', fs=5.9)
    F.box('ev', 5.25, 2.72, 0.9, 0.5, 'Evidence\n$E_T$, $E_G$, $E_S$', 'data', bold_first=True, fs=6.1)
    F.box('cm', 5.25, 1.95, 0.9, 0.48, 'Context mgmt. $\\kappa$\nRQ1 · RG1', 'rq', bold_first=True, fs=6.1)
    F.box('cf', 4.18, 1.95, 0.9, 0.48, 'Fusion $\\varphi$\nRQ2 · RG2', 'rq', bold_first=True, fs=6.1)
    F.box('c', 3.1, 1.95, 0.92, 0.48, 'Context $c$\n≤ 24,000 characters', 'data', bold_first=True, fs=6.1)
    F.box('g', 3.1, 1.12, 0.98, 0.5, 'Shared LLM $g$\ngpt-oss:20b (T = 0)', 'fixed', bold_first=True, fs=6.1)
    F.box('a', 4.65, 1.12, 1.55, 0.42, 'Answer $A(q)\\subseteq\\mathrm{IDs}(c)$\nJSON set of paper IDs', 'io', bold_first=True, fs=6.1)
    F.box('int', 3.92, 0.43, 3.5, 0.34, 'RQ4 · RG4: INT-1 = the winners of RQ3 → RQ1 → RQ2 combined', 'llm', fs=6.2)
    F.edge('q', 'ar', 'right', 'left')
    for k in ('b1', 'b2', 'b3'):
        F.edge('ar', k, 'right', 'left', via='hvh')
        F.edge(k, 'ev', 'right', 'left', via='hvh')
    F.edge('ev', 'cm')
    F.edge('cm', 'cf', 'left', 'right')
    F.edge('cf', 'c', 'left', 'right')
    F.edge('c', 'g')
    F.edge('g', 'a', 'right', 'left')
    F.box('el', 6.4, 1.68, 1.28, 3.2, 'Evaluation (Sec. III-H)', 'group', fs=6.8)
    F.box('bm', 6.4, 2.86, 1.1, 0.5, 'Benchmark\ngold before wording; strict source necessity', 'data', bold_first=True, fs=5.9)
    F.box('st', 6.4, 2.22, 1.1, 0.46, 'Stress variants\nnormal · noisy · conflict · unanswerable', 'data', bold_first=True, fs=5.9)
    F.box('me', 6.4, 1.6, 1.1, 0.46, 'Metrics\nquality · evidence · control · cost', 'step', bold_first=True, fs=5.9)
    F.box('sx', 6.4, 0.98, 1.1, 0.46, 'Family-clustered tests\nbootstrap · sign-flip · Holm', 'step', bold_first=True, fs=5.9)
    F.box('rk', 6.4, 0.4, 1.1, 0.38, 'Pareto + overall ranking', 'stop', fs=5.9)
    for a, b in (('bm', 'st'), ('st', 'me'), ('me', 'sx'), ('sx', 'rk')):
        F.edge(a, b)
    F.path([F.anchor('a', 'right'), (5.78, 1.12), (5.78, 1.6), F.anchor('me', 'left')], color='#94a3b8', lw=0.8)
    save(F.fig, 'fig_framework')

# ===================================================================================== Fig. worked example
def example():
    ex = FOUND['example']
    c = ex['candidates']
    keys = [('text', 'T'), ('graph', 'G'), ('structured', 'S'), ('text+graph', 'T∩G'), ('text+structured', 'T∩S'), ('graph+structured', 'G∩S'), ('all', 'T∩G∩S')]
    vals = [c[k] for k, _ in keys]
    fig, ax = plt.subplots(figsize=(COL, 1.75))
    cols = [FL.SOURCE_COLOR['text'], FL.SOURCE_COLOR['graph'], FL.SOURCE_COLOR['structured'], '#64748b', '#64748b', '#64748b', '#16a34a']
    ax.bar(range(len(vals)), vals, color=cols, width=0.62)
    ax.set_yscale('log')
    for i, v in enumerate(vals):
        ax.text(i, v * 1.35, fnum(v, 0), ha='center', va='bottom', fontsize=6.6, color=BODY)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels([l for _, l in keys])
    ax.set_ylim(0.6, 1.5e6)
    ax.set_ylabel('papers satisfying (log)')
    ax.minorticks_off()
    clean(ax, 'y')
    save(fig, 'fig_example')


# ===================================================================================== Fig. RQ1 strategies on a toy graph
TOY_POS = {'I': (0.0, 0.0), 'A1': (-1.05, 0.62), 'A2': (0.0, 1.0), 'A3': (1.05, 0.62), 'A4': (1.1, -0.55), 'I2': (1.85, -1.05),
           'P1': (-1.75, 1.3), 'P2': (-1.65, 0.0), 'P3': (-0.45, 1.75), 'P4': (0.45, 1.75), 'P5': (1.7, 1.3), 'P6': (1.95, 0.25),
           'P7': (0.35, -1.25), 'P8': (2.25, -0.35), 'F1': (-1.0, -1.0)}
TOY_TYPE = {k: ('inst' if k.startswith('I') else 'auth' if k.startswith('A') else 'paper' if k.startswith('P') else 'field') for k in TOY_POS}
TOY_E = [('I', 'A1'), ('I', 'A2'), ('I', 'A3'), ('I', 'A4'), ('A4', 'I2'), ('A1', 'P1'), ('A1', 'P2'), ('A2', 'P3'), ('A2', 'P4'), ('A3', 'P5'),
         ('A3', 'P6'), ('A4', 'P7'), ('A4', 'P8'), ('P2', 'F1'), ('P7', 'F1'), ('P3', 'P4')]
TOY_GOLD = {'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8'}
TCOL = {'inst': '#0d9488', 'auth': '#d97706', 'paper': '#2563eb', 'field': '#7c3aed'}


def toy(ax, keep_nodes, keep_edges, title, letter, note, heat=None, prize=(), seeds=(), thick=()):
    ax.set_xlim(-2.25, 2.7)
    ax.set_ylim(-1.55, 2.2)
    ax.set_aspect('equal')
    ax.axis('off')
    for a, b in TOY_E:
        on = (a, b) in keep_edges or (b, a) in keep_edges
        (x0, y0), (x1, y1) = TOY_POS[a], TOY_POS[b]
        lw = 1.6 if ((a, b) in thick or (b, a) in thick) else (0.9 if on else 0.5)
        ax.plot([x0, x1], [y0, y1], color='#1f2937' if on else '#d1d5db', linewidth=lw, zorder=1, solid_capstyle='round')
    for k, (x, y) in TOY_POS.items():
        on = k in keep_nodes
        col = TCOL[TOY_TYPE[k]]
        if heat is not None:
            h = heat.get(k, 0.0)
            ax.add_patch(Circle((x, y), 0.36, facecolor='#f97316', alpha=0.10 + 0.55 * h, edgecolor='none', zorder=0.5))
        ax.add_patch(Circle((x, y), 0.17, facecolor=col if on else 'white', edgecolor=col if on else '#cbd5e1', linewidth=0.8, zorder=2))
        if k in TOY_GOLD:
            ax.add_patch(Circle((x, y), 0.24, facecolor='none', edgecolor='#16a34a', linewidth=0.8, linestyle=(0, (2, 1)), zorder=2))
        if k in prize:
            ax.text(x + 0.2, y + 0.2, '★', fontsize=7, color='#b45309', zorder=3, ha='center', va='center', fontfamily='Segoe UI Symbol')
        if k in seeds:
            ax.add_patch(Circle((x, y), 0.3, facecolor='none', edgecolor='#dc2626', linewidth=0.9, zorder=2))
        ax.text(x, y, k, ha='center', va='center', fontsize=4.6, color='white' if on else '#9ca3af', zorder=3, fontweight='bold')
    ax.text(0.0, 1.0, '(%s) %s' % (letter, title), transform=ax.transAxes, ha='left', va='bottom', fontsize=7.0, fontweight='bold')
    ax.text(0.0, -0.02, note, transform=ax.transAxes, ha='left', va='top', fontsize=5.9, color=MUTED, wrap=True)


def rq1_methods():
    fig, axes = plt.subplots(1, 5, figsize=(WIDE, 1.75))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.27, wspace=0.08)
    allE = set(TOY_E)
    b0_nodes = ['I', 'A1', 'A2', 'A3', 'A4', 'I2', 'P1', 'P2', 'P3']
    toy(axes[0], set(b0_nodes), {e for e in allE if e[0] in b0_nodes and e[1] in b0_nodes}, 'CM-B0 raw order', 'a',
        'records kept in retrieved\norder until the budget is full')
    b1 = {'I', 'A1', 'A2', 'A3', 'P1', 'P2', 'P3', 'P4', 'P5'}
    toy(axes[1], b1, {('I', 'A1'), ('I', 'A2'), ('I', 'A3'), ('A1', 'P1'), ('A1', 'P2'), ('A2', 'P3'), ('A2', 'P4'), ('A3', 'P5')}, 'CM-B1 top-K',
        'a', '5 best-ranked papers and the\npaths to the seed')
    axes[1].texts[-2].set_text('(b) CM-B1 top-K')
    k01 = {'I', 'A2', 'A3', 'P3', 'P4', 'P5', 'P6', 'A1', 'P1'}
    e01 = {('I', 'A2'), ('A2', 'P3'), ('A2', 'P4'), ('I', 'A3'), ('A3', 'P5'), ('A3', 'P6'), ('I', 'A1'), ('A1', 'P1')}
    toy(axes[2], k01, e01, 'CM-01 KG²RAG', 'c', 'seed relations, 1-hop expansion,\nmax. spanning tree, reranked',
        thick={('I', 'A2'), ('A2', 'P3'), ('I', 'A3')})
    k02 = {'I', 'A2', 'P3', 'P4', 'A3', 'P5'}
    toy(axes[3], k02, {('I', 'A2'), ('A2', 'P3'), ('A2', 'P4'), ('I', 'A3'), ('A3', 'P5')}, 'CM-02 PCST', 'd',
        'one connected subgraph: prizes\n(★) minus edge costs', prize={'I', 'P3', 'P4'})
    heat = {'I': 1.0, 'A1': 0.55, 'A2': 0.85, 'A3': 0.75, 'A4': 0.35, 'P3': 0.7, 'P4': 0.62, 'P5': 0.5, 'P1': 0.3, 'P2': 0.22, 'P6': 0.28,
            'I2': 0.05, 'P7': 0.12, 'P8': 0.08, 'F1': 0.04}
    k03 = {k for k, v in heat.items() if v >= 0.28}
    toy(axes[4], k03, {e for e in allE if e[0] in k03 and e[1] in k03}, 'CM-03 flow diffusion', 'e',
        'mass spreads from keyword seeds;\nnodes above τ kept', heat=heat, seeds={'I', 'A2'})
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], marker='o', ls='', markersize=4, markerfacecolor=TCOL[t], markeredgecolor=TCOL[t], label=l)
          for t, l in (('inst', 'institution'), ('auth', 'author'), ('paper', 'paper'), ('field', 'field of study'))]
    hs += [Line2D([], [], marker='o', ls='', markersize=5.5, markerfacecolor='none', markeredgecolor='#16a34a', label='correct answer'),
           Line2D([], [], marker='o', ls='', markersize=4, markerfacecolor='white', markeredgecolor='#cbd5e1', label='not kept'),
           Line2D([], [], color='#1f2937', lw=1.0, label='kept relation')]
    fig.legend(handles=hs, loc='upper center', ncol=7, bbox_to_anchor=(0.5, 0.11), fontsize=6.2, handletextpad=0.3, columnspacing=1.0)
    save(fig, 'fig_rq1_methods')


# ===================================================================================== Fig. RQ2 fusion layouts
SC = {'T': FL.SOURCE_COLOR['text'], 'G': FL.SOURCE_COLOR['graph'], 'S': FL.SOURCE_COLOR['structured']}


def block(ax, x, y, w, h, src, alpha=1.0, label=None, lc='white'):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=SC.get(src, src), edgecolor='white', linewidth=0.6, alpha=alpha))
    if label:
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center', fontsize=5.0, color=lc)


def rq2_methods():
    fig, axes = plt.subplots(1, 5, figsize=(WIDE, 2.05))
    fig.subplots_adjust(wspace=0.12)
    for ax in axes:
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.12)
        ax.axis('off')
    H = 0.055
    # (a) raw concatenation
    ax = axes[0]
    seq = ['T'] * 5 + ['G'] * 5 + ['S'] * 5
    for i, s in enumerate(seq):
        y = 0.95 - (i + 1) * H
        block(ax, 0.2, y, 0.6, H * 0.92, s, alpha=1.0 if i < 12 else 0.25)
    ax.plot([0.12, 0.88], [0.95 - 12 * H - 0.004] * 2, color='#dc2626', lw=0.8, ls=(0, (3, 2)))
    ax.text(0.9, 0.95 - 12 * H, 'budget', fontsize=5.4, color='#dc2626', va='center')
    ax.text(0.0, 1.05, '(a) CF-B0 concatenation', fontsize=7, fontweight='bold')
    ax.text(0.0, 0.0, 'items in source order;\ncut at 24,000 characters', fontsize=5.9, color=MUTED, va='bottom')
    # (b) sections
    ax = axes[1]
    for j, s in enumerate(['T', 'G', 'S']):
        y0 = 0.93 - j * 0.27
        ax.text(0.2, y0, ['[TEXT]', '[GRAPH]', '[STRUCTURED]'][j], fontsize=5.4, color=BODY, va='bottom')
        for i in range(3):
            block(ax, 0.2, y0 - (i + 1) * H - 0.01, 0.6, H * 0.92, s)
        block(ax, 0.2, y0 - 4 * H - 0.01, 0.6, H * 0.92, s, alpha=0.25)
    ax.text(0.0, 1.05, '(b) CF-B1 sections', fontsize=7, fontweight='bold')
    ax.text(0.0, 0.0, 'three labelled sections,\n8,000 characters each', fontsize=5.9, color=MUTED, va='bottom')
    # (c) entity groups
    ax = axes[2]
    groups = [('entity e₁', ['T', 'G', 'S']), ('entity e₂', ['T', 'S']), ('entity e₃', ['G', 'G']), ('UNALIGNED', ['T'])]
    y = 0.93
    for name, items in groups:
        ax.add_patch(FancyBboxPatch((0.14, y - (len(items) + 1) * H - 0.012), 0.72, (len(items) + 1) * H + 0.008,
                                    boxstyle='round,pad=0,rounding_size=0.02', facecolor='#f8fafc', edgecolor='#94a3b8', linewidth=0.5))
        ax.text(0.18, y - H * 0.6, name, fontsize=5.2, va='center', color=BODY)
        for i, s in enumerate(items):
            block(ax, 0.2, y - (i + 2) * H, 0.6, H * 0.92, s)
        y -= (len(items) + 1) * H + 0.03
    ax.text(0.0, 1.05, '(c) CF-01 entity groups', fontsize=7, fontweight='bold')
    ax.text(0.0, 0.0, 'items aligned to entities;\ngroups by relevance, coverage', fontsize=5.9, color=MUTED, va='bottom')
    # (d) dual-path selection
    ax = axes[3]
    ax.text(0.03, 0.93, 'structural', fontsize=5.4, color=BODY)
    for i, s in enumerate(['G', 'S', 'G', 'S', 'G', 'S', 'G']):
        sel = i in (1, 3)
        block(ax, 0.03, 0.88 - (i + 1) * H, 0.34, H * 0.92, s, alpha=1.0 if sel else 0.3, label='✓' if sel else None)
    ax.add_patch(FancyBboxPatch((0.405, 0.59), 0.24, 0.18, boxstyle='round,pad=0,rounding_size=0.02', facecolor='#f5f3ff', edgecolor='#7c3aed', linewidth=0.7))
    ax.text(0.525, 0.68, 'LLM\nselects\n≤ 5', fontsize=4.9, ha='center', va='center')
    ax.annotate('', xy=(0.405, 0.68), xytext=(0.375, 0.68), arrowprops=dict(arrowstyle='-|>', lw=0.6, color='#475569', mutation_scale=6))
    ax.text(0.68, 0.93, 'context (≤ 10)', fontsize=5.4, color=BODY)
    for i, s in enumerate(['S', 'S', 'T', 'T', 'T', 'T', 'T', 'T', 'T', 'T']):
        block(ax, 0.68, 0.88 - (i + 1) * H, 0.3, H * 0.92, s)
    ax.annotate('', xy=(0.68, 0.8), xytext=(0.645, 0.7), arrowprops=dict(arrowstyle='-|>', lw=0.6, color='#475569', mutation_scale=6))
    ax.text(0.0, 1.05, '(d) CF-02 dual path', fontsize=7, fontweight='bold')
    ax.text(0.0, 0.0, 'model picks structural items;\ntext fills remaining slots', fontsize=5.9, color=MUTED, va='bottom')
    # (e) late fusion
    ax = axes[4]
    for j, s in enumerate(['T', 'G', 'S']):
        x = 0.04 + j * 0.32
        block(ax, x, 0.82, 0.26, 0.09, s, label=['text', 'graph', 'struct.'][j])
        ax.add_patch(FancyBboxPatch((x, 0.58), 0.26, 0.15, boxstyle='round,pad=0,rounding_size=0.02', facecolor='#f5f3ff', edgecolor='#7c3aed', linewidth=0.7))
        ax.text(x + 0.13, 0.655, 'LLM\nfinding', fontsize=5.0, ha='center', va='center')
        ax.annotate('', xy=(x + 0.13, 0.73), xytext=(x + 0.13, 0.82), arrowprops=dict(arrowstyle='-|>', lw=0.6, color='#475569', mutation_scale=6))
        ax.annotate('', xy=(0.5, 0.48), xytext=(x + 0.13, 0.58), arrowprops=dict(arrowstyle='-|>', lw=0.6, color='#475569', mutation_scale=6))
    ax.add_patch(FancyBboxPatch((0.27, 0.34), 0.46, 0.14, boxstyle='round,pad=0,rounding_size=0.02', facecolor='#f5f3ff', edgecolor='#7c3aed', linewidth=0.7))
    ax.text(0.5, 0.41, 'LLM fusion call', fontsize=5.2, ha='center', va='center')
    ax.annotate('', xy=(0.5, 0.25), xytext=(0.5, 0.34), arrowprops=dict(arrowstyle='-|>', lw=0.6, color='#475569', mutation_scale=6))
    ax.text(0.5, 0.245, 'answer', fontsize=5.4, ha='center', va='top')
    ax.text(0.0, 1.05, '(e) CF-03 late fusion', fontsize=7, fontweight='bold')
    ax.text(0.0, 0.0, 'per-source reasoning, then\none grounded fusion call', fontsize=5.9, color=MUTED, va='bottom')
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=SC['T'], label='text item'), Patch(color=SC['G'], label='graph item'), Patch(color=SC['S'], label='structured item'),
                        Patch(color='#cbd5e1', label='not in context'), Patch(facecolor='#f5f3ff', edgecolor='#7c3aed', label='LLM call')],
               loc='lower center', ncol=5, bbox_to_anchor=(0.5, -0.1), fontsize=6.2)
    save(fig, 'fig_rq2_methods')


# ===================================================================================== Fig. RQ3 control policies
def mini(ax, nodes, edges, title, note):
    """nodes: key -> (x, y, w, h, text, kind); edges: (a, b, label, pts)"""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.12)
    ax.axis('off')
    for k, (x, y, w, h, t, kind) in nodes.items():
        face, edge, _, _ = KINDS[kind]
        if kind == 'decision':
            ax.add_patch(Polygon([(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)], closed=True, facecolor=face, edgecolor=edge, linewidth=0.6))
        else:
            ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle='round,pad=0,rounding_size=0.02', facecolor=face, edgecolor=edge, linewidth=0.6))
        ax.text(x, y, t, ha='center', va='center', fontsize=4.8, linespacing=1.05)
    for a, b, lab, pts in edges:
        xa, ya = pts[0]
        for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
            ax.plot([x0, x1], [y0, y1], color='#475569', lw=0.55, clip_on=False)
        ax.annotate('', xy=pts[-1], xytext=pts[-2], annotation_clip=False,
                    arrowprops=dict(arrowstyle='-|>', lw=0.55, color='#475569', mutation_scale=5, shrinkA=0, shrinkB=0))
        if lab:
            left = lab.startswith('<')
            lab = lab.lstrip('<')
            mx, my = (pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2
            ax.text(mx - 0.02 if left else mx + 0.02, my + 0.015, lab, fontsize=4.6, color=MUTED, ha='right' if left else 'left')
    ax.text(0.0, 1.06, title, fontsize=7, fontweight='bold')
    ax.text(0.0, 0.0, note, fontsize=5.9, color=MUTED, va='bottom')


def rq3_methods():
    fig, axes = plt.subplots(1, 5, figsize=(WIDE, 2.25))
    fig.subplots_adjust(wspace=0.18)
    mini(axes[0], {'t': (0.5, 0.9, 0.5, 0.1, 'search text', 'text'), 'g': (0.5, 0.72, 0.5, 0.1, 'search graph', 'graph'),
                   's': (0.5, 0.54, 0.5, 0.1, 'search structured', 'structured'), 'a': (0.5, 0.33, 0.56, 0.11, 'answer\n(1 LLM call)', 'llm')},
         [('t', 'g', '', [(0.5, 0.85), (0.5, 0.77)]), ('g', 's', '', [(0.5, 0.67), (0.5, 0.59)]), ('s', 'a', '', [(0.5, 0.49), (0.5, 0.385)])],
         '(a) AR-B0 all', '3 searches for every\nquestion')
    mini(axes[1], {'c': (0.5, 0.9, 0.62, 0.11, 'match cue words\n(frozen table)', 'step'),
                   't': (0.2, 0.68, 0.24, 0.09, 'T?', 'text'), 'g': (0.5, 0.68, 0.24, 0.09, 'G?', 'graph'), 's': (0.8, 0.68, 0.24, 0.09, 'S?', 'structured'),
                   'r': (0.5, 0.49, 0.7, 0.1, 'search routed sources once', 'step'), 'a': (0.5, 0.31, 0.56, 0.1, 'answer', 'llm')},
         [('c', 't', '', [(0.3, 0.845), (0.2, 0.725)]), ('c', 'g', '', [(0.5, 0.845), (0.5, 0.725)]), ('c', 's', '', [(0.7, 0.845), (0.8, 0.725)]),
          ('g', 'r', '', [(0.5, 0.635), (0.5, 0.54)]), ('r', 'a', '', [(0.5, 0.44), (0.5, 0.36)])],
         '(b) AR-B1 rules', 'no learning; default text')
    mini(axes[2], {'k': (0.5, 0.94, 0.7, 0.09, 't5-base classifier', 'model'), 'd': (0.5, 0.79, 0.3, 0.12, 'route', 'decision'),
                   'A': (0.13, 0.62, 0.24, 0.1, 'A: none', 'step'), 'B': (0.48, 0.62, 0.3, 0.1, 'B: 1 source', 'step'),
                   'C': (0.83, 0.62, 0.32, 0.1, 'C: ≤3 steps', 'step'), 'ct': (0.83, 0.43, 0.3, 0.12, 'enough?', 'llm'),
                   'a': (0.48, 0.25, 0.36, 0.09, 'answer', 'llm')},
         [('k', 'd', '', [(0.5, 0.895), (0.5, 0.85)]), ('d', 'A', '', [(0.35, 0.79), (0.13, 0.79), (0.13, 0.67)]),
          ('d', 'B', '', [(0.5, 0.73), (0.5, 0.67)]), ('d', 'C', '', [(0.65, 0.79), (0.83, 0.79), (0.83, 0.67)]),
          ('C', 'ct', '', [(0.83, 0.57), (0.83, 0.49)]), ('ct', 'C', 'no', [(0.99, 0.43), (1.04, 0.43), (1.04, 0.62), (0.99, 0.62)]),
          ('ct', 'a', 'yes', [(0.83, 0.37), (0.83, 0.25), (0.66, 0.25)]), ('A', 'a', '', [(0.13, 0.57), (0.13, 0.25), (0.3, 0.25)]),
          ('B', 'a', '', [(0.5, 0.57), (0.5, 0.295)])],
         '(c) AR-01 adaptive', 'trained router; LLM\nsufficiency controller')
    mini(axes[3], {'f': (0.5, 0.94, 0.62, 0.11, 'search the first\nrouted source', 'step'),
                   'e': (0.5, 0.78, 0.62, 0.11, 'cross-encoder\n+ Platt score', 'model'), 'd': (0.5, 0.6, 0.3, 0.13, 'state', 'decision'),
                   'am': (0.18, 0.42, 0.3, 0.11, 'AMBIG.\n+1 source', 'step'), 'bd': (0.82, 0.42, 0.3, 0.11, 'BAD\n+ all left', 'step'),
                   'a': (0.5, 0.26, 0.36, 0.09, 'answer', 'llm')},
         [('f', 'e', '', [(0.5, 0.885), (0.5, 0.835)]), ('e', 'd', '', [(0.5, 0.725), (0.5, 0.665)]),
          ('d', 'am', '', [(0.35, 0.6), (0.18, 0.6), (0.18, 0.475)]), ('d', 'bd', '', [(0.65, 0.6), (0.82, 0.6), (0.82, 0.475)]),
          ('d', 'a', 'GOOD', [(0.5, 0.535), (0.5, 0.305)]), ('am', 'e', '≤ 2', [(0.06, 0.475), (0.06, 0.78), (0.19, 0.78)]),
          ('bd', 'e', '', [(0.94, 0.475), (0.94, 0.78), (0.81, 0.78)])],
         '(d) AR-02 corrective', 'calibrated evaluator;\n≤ 2 correction rounds')
    mini(axes[4], {'ag': (0.42, 0.94, 0.56, 0.09, 'agent: pick a tool', 'llm'), 'tl': (0.42, 0.8, 0.56, 0.09, 'run one tool', 'step'),
                   'dr': (0.42, 0.66, 0.56, 0.09, 'draft answer', 'llm'), 'va': (0.42, 0.49, 0.3, 0.14, 'valid?', 'decision'),
                   'cm': (0.86, 0.66, 0.24, 0.13, 'commen-\ntor', 'llm'), 'a': (0.42, 0.29, 0.36, 0.09, 'accept', 'stop')},
         [('ag', 'tl', '', [(0.42, 0.895), (0.42, 0.845)]), ('tl', 'dr', '', [(0.42, 0.755), (0.42, 0.705)]),
          ('dr', 'va', '', [(0.42, 0.615), (0.42, 0.56)]), ('va', 'a', 'yes', [(0.42, 0.42), (0.42, 0.335)]),
          ('va', 'cm', 'no', [(0.57, 0.49), (0.86, 0.49), (0.86, 0.595)]), ('cm', 'ag', '≤ 4', [(0.86, 0.725), (0.86, 0.94), (0.7, 0.94)])],
         '(e) AR-03 agent', 'agent, validator and\ncommentor; ≤ 4 iterations')
    save(fig, 'fig_rq3_methods')


# ===================================================================================== Fig. protocol (how it was solved)
def protocol():
    F = PFlow(COL, 3.4, fs=6.2)
    items = [('f', 'Freeze: SHA-256 of code, configs, prompts, inputs, models and cohort', 'step', 0.3),
             ('ck', 'Every hash unchanged?', 'decision', 0.42),
             ('cp', 'Call phase (question-major): all methods per question; each request sent once', 'step', 0.34),
             ('rp', 'Replay phase: unchanged runner, store-only client; stops on any changed request', 'step', 0.34),
             ('rr', 'Per-question run records (448; 0 errors)', 'data', 0.26),
             ('an', 'Frozen analysis plan: metrics, strata, Pareto sets', 'step', 0.28),
             ('sx', 'Family-clustered paired tests: bootstrap CI, exact sign-flip, Holm', 'step', 0.32),
             ('rk', 'Overall ranking → winners → RQ4 integration', 'stop', 0.27)]
    y = 3.32
    for i, (k, t, kind, h) in enumerate(items):
        F.box(k, 1.2, y - h / 2, 2.25 if kind != 'decision' else 1.55, h, t, kind, n=i + 1)
        y -= h + 0.1
    for a, b in zip(items, items[1:]):
        F.edge(a[0], b[0], label='yes' if a[0] == 'ck' else None, ldx=0.06)
    yc, yr = F.n['cp'][1], F.n['rp'][1]
    F.box('ss', 2.92, (yc + yr) / 2, 0.92, (yc - yr) + 0.3, 'Stage store\nhash(request) → response, usage, time', 'data', bold_first=True, fs=5.7)
    F.path([F.anchor('cp', 'right'), (F.n['ss'][0] - 0.46, yc)], color='#475569', lw=0.8)
    F.path([(F.n['ss'][0] - 0.46, yr), F.anchor('rp', 'right')], color='#475569', lw=0.8)
    F.box('rf', 2.95, F.n['ck'][1], 0.78, 0.26, 'refuse to run', 'fail', fs=5.8)
    F.edge('ck', 'rf', 'right', 'left', label='no', lpos=0.25, ldy=0.07)
    save(F.fig, 'fig_protocol')

# ===================================================================================== result charts
def hbar_ci(ax, methods, vals, cis, title, fmtk='rate', xmax=None, star=()):
    ys = np.arange(len(methods))[::-1]
    xmax = xmax or max([v for v in vals] + [c[1] for c in cis if c]) * 1.3
    for y, m, v, c in zip(ys, methods, vals, cis):
        ax.barh(y, v, height=0.56, color=mcolor(m))
        tip = v
        if c:
            ax.plot([c[0], c[1]], [y, y], color=INK, lw=0.7)
            for x in c:
                ax.plot([x, x], [y - 0.12, y + 0.12], color=INK, lw=0.7)
            tip = max(v, c[1])
        ax.text(tip + xmax * 0.02, y, pfmt(v, fmtk), va='center', fontsize=6.3)
    ax.set_yticks(ys)
    ax.set_yticklabels([m + (' ★' if m in star else '') for m in methods])
    ax.set_xlim(0, xmax)
    ax.set_title(title, pad=3)
    clean(ax)


def rq1_results():
    ms, d, ci, P = R1['methods'], R1['descriptive'], R1['ci95'], set(R1['pareto'])
    fig, axes = plt.subplots(2, 2, figsize=(COL, 2.75))
    fig.subplots_adjust(wspace=0.75, hspace=0.75)
    spec = [('answer_f1', 'Answer F1 ↑', 'rate', 0.42), ('mrr', 'MRR ↑', 'rate', None), ('gold_coverage', 'Gold coverage ↑', 'rate', None),
            ('input_tokens', 'Input tokens ↓', 'tokens', None)]
    for ax, (k, t, kind, xm) in zip(axes.flat, spec):
        cis = [tuple(ci[m][k]) if ci.get(m, {}).get(k) else None for m in ms]
        hbar_ci(ax, ms, [d[m][k] for m in ms], cis, t, kind, xm, star=P)
    for ax, l in zip(axes.flat, 'abcd'):
        sub(ax, l, y=-0.28)
    save(fig, 'fig_rq1_bars')


def scatter(R, x, y, xl, yl, name, w=COL, h=2.05, xpad=0.45):
    ms, d, P = R['methods'], R['descriptive'], set(R.get('pareto') or [])
    fig, ax = plt.subplots(figsize=(w, h))
    xs = [d[m][x] / (1000. if x == 'latency' else 1.) for m in ms]
    ys = [d[m][y] / (1000. if y == 'latency' else 1.) for m in ms]
    pts = sorted((xs[i], ys[i]) for i, m in enumerate(ms) if m in P)
    if len(pts) > 1:
        ax.plot(*zip(*pts), color='#cbd5e1', lw=1.0, zorder=1)
    offs = {}
    for i, m in enumerate(ms):
        on = m in P
        ax.scatter(xs[i], ys[i], s=28, marker='o' if on else 'v', facecolor=mcolor(m) if on else 'white', edgecolor=mcolor(m), lw=1.0, zorder=3)
    xr, yr = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
    ax.set_xlim(min(xs) - 0.12 * xr, max(xs) + xpad * xr)
    ax.set_ylim(min(ys) - 0.22 * yr, max(ys) + 0.22 * yr)
    fig.canvas.draw()
    rnd = fig.canvas.get_renderer()
    placed, box = [], ax.get_window_extent(rnd)
    px = [ax.transData.transform((xs[i], ys[i])) for i in range(len(ms))]
    for i, m in enumerate(ms):
        txt = m + (' ★' if m in P else '')
        for dx, dy, ha in ((5, 3, 'left'), (5, -8, 'left'), (-5, 3, 'right'), (-5, -8, 'right'), (5, 10, 'left'), (-5, 10, 'right')):
            t = ax.annotate(txt, (xs[i], ys[i]), xytext=(dx, dy), textcoords='offset points', fontsize=6.4, ha=ha)
            bb = t.get_window_extent(rnd).expanded(1.05, 1.2)
            if (box.x0 <= bb.x0 and bb.x1 <= box.x1 and box.y0 <= bb.y0 and bb.y1 <= box.y1 and not any(bb.overlaps(o) for o in placed)
                    and not any(bb.contains(*p) for j, p in enumerate(px) if j != i)):
                placed.append(bb)
                break
            t.remove()
        else:
            ax.annotate(txt, (xs[i], ys[i]), xytext=(5, 3), textcoords='offset points', fontsize=6.4)
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    clean(ax, None)
    ax.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    save(fig, name)


def rq1_strata():
    ms = R1['methods']
    S = R1['strata']['modality']
    groups = ['G', 'TG', 'GS', 'TGS']
    fig, axes = plt.subplots(2, 1, figsize=(COL, 2.6))
    fig.subplots_adjust(hspace=0.75)
    for ax, k, t in zip(axes, ('answer_f1', 'gold_coverage'), ('Answer F1 by sources needed', 'Gold coverage by sources needed')):
        w = 0.15
        for j, m in enumerate(ms):
            ax.bar(np.arange(4) - 0.3 + j * w, [S[g][m][k] for g in groups], w * 0.9, color=mcolor(m), label=m)
        ax.set_xticks(range(4))
        ax.set_xticklabels(['%s (n=8)' % g for g in groups])
        ax.set_title(t, pad=3)
        clean(ax, 'y')
    axes[0].legend(ncol=5, loc='upper center', bbox_to_anchor=(0.5, 1.42), fontsize=6.0, handlelength=1.0, columnspacing=0.8)
    sub(axes[0], 'a', y=-0.3)
    sub(axes[1], 'b', y=-0.3)
    save(fig, 'fig_rq1_strata')


def rq2_results():
    ms, d = R2['methods'], R2['descriptive']
    fig = plt.figure(figsize=(COL, 2.75))
    gs = fig.add_gridspec(2, 2, hspace=0.85, wspace=0.75)
    ax = fig.add_subplot(gs[0, 0])
    cnt = R2['supportability']['counts']
    ks = [('FULLY_SUPPORTABLE', 'fully', '#16a34a'), ('PARTIALLY_SUPPORTABLE', 'partially', '#d97706'), ('UNSUPPORTABLE', 'none', '#dc2626')]
    ax.bar(range(3), [cnt[k] for k, _, _ in ks], color=[c for _, _, c in ks], width=0.55)
    for i, (k, _, _) in enumerate(ks):
        ax.text(i, cnt[k] + 0.4, str(cnt[k]), ha='center', fontsize=6.6)
    ax.set_xticks(range(3))
    ax.set_xticklabels([l for _, l, _ in ks])
    ax.set_ylim(0, 19)
    ax.set_title('Bundles holding gold papers', pad=3)
    clean(ax, 'y')
    sub(ax, 'a', y=-0.32)
    for pos, (k, t, kind, xm, l) in zip([gs[0, 1], gs[1, 0], gs[1, 1]], [('input_tokens', 'Input tokens ↓', 'tokens', 6200, 'b'),
                                                                         ('latency', 'Latency (s) ↓', 'ms', 26, 'c'),
                                                                         ('llm_calls', 'LLM calls ↓', 'calls', 5.0, 'd')]):
        ax = fig.add_subplot(pos)
        sc = 1000. if k == 'latency' else 1.
        hbar_ci(ax, ms, [d[m][k] / sc for m in ms], [None] * 5, t, 'r1' if k == 'latency' else kind, xm, star=set(R2['pareto']))
        if k == 'latency':
            for txt in ax.texts:
                txt.set_text(txt.get_text())
        sub(ax, l, y=-0.32)
    save(fig, 'fig_rq2')


def forest(ax, rows, title, unit=1.0, fmt_d=lambda v: fnum(v, 3, True)):
    ys = np.arange(len(rows))[::-1]
    lo = min(r['ci95'][0] for r in rows) / unit
    hi = max(r['ci95'][1] for r in rows) / unit
    span = (hi - lo) or 1
    for y, r in zip(ys, rows):
        c = '#15803d' if r['significant'] else '#6b7280'
        ax.plot([r['ci95'][0] / unit, r['ci95'][1] / unit], [y, y], color=c, lw=1.1, solid_capstyle='round')
        ax.scatter([r['delta'] / unit], [y], s=12, color=c, marker='D' if r['significant'] else 'o', zorder=3)
        ax.text(hi + 0.06 * span, y, ('%s*' if r['significant'] else '%s') % fmt('p_holm' and r['p_holm'], 'p'), va='center', fontsize=6.0,
                color=c)
    ax.axvline(0, color='#9ca3af', lw=0.6)
    ax.text(hi + 0.06 * span, len(rows) - 0.45, 'Holm p', fontsize=5.8, color=MUTED, va='bottom')
    ax.set_yticks(ys)
    ax.set_yticklabels(['%s − %s' % (r['a'], r['b']) for r in rows], fontsize=6.4)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlim(lo - 0.06 * span, hi + 0.26 * span)
    ax.set_title(title, pad=3)
    clean(ax)


def rq3_forest():
    T = R3['tests']
    pick = lambda k, pairs: [next(t for t in T[k] if (t['a'], t['b']) == p) for p in pairs]
    fig, axes = plt.subplots(3, 1, figsize=(COL, 3.6), gridspec_kw={'height_ratios': [1, 1.6, 1.6]})
    fig.subplots_adjust(hspace=0.75)
    forest(axes[0], pick('source_f1', [('AR-B1', 'AR-B0'), ('AR-03', 'AR-B1'), ('AR-01', 'AR-B1'), ('AR-02', 'AR-B1')]), 'Source-selection F1 (Δ, 95% CI)')
    forest(axes[1], pick('total_tokens', [('AR-B1', 'AR-B0'), ('AR-01', 'AR-B1'), ('AR-02', 'AR-B1'), ('AR-03', 'AR-B1'), ('AR-01', 'AR-B0'), ('AR-03', 'AR-B0')]),
           'Tokens per question (Δ, 95% CI)')
    forest(axes[2], pick('latency', [('AR-B1', 'AR-B0'), ('AR-01', 'AR-B1'), ('AR-02', 'AR-B1'), ('AR-03', 'AR-B1'), ('AR-01', 'AR-B0'), ('AR-03', 'AR-B0')]),
           'Latency in seconds (Δ, 95% CI)', unit=1000.)
    for ax, l in zip(axes, 'abc'):
        sub(ax, l, y=-0.38 if l == 'a' else -0.25)
    save(fig, 'fig_rq3_forest')


STOP = {'all_sources_retrieved': 'all sources', 'routed_sources_retrieved': 'routed sources', 'max_multi_steps': '3-search limit',
        'sufficient': 'judged sufficient', 'good': 'rated GOOD', 'sources_exhausted': 'no source left', 'max_correction_rounds': '2-round limit',
        'validator_accepted': 'validator accepted', 'max_iterations_rejected': '4 rejected iterations'}
CHOSEN = {'sufficient', 'good', 'validator_accepted'}
LIMIT = {'max_multi_steps', 'max_correction_rounds', 'max_iterations_rejected'}


def rq3_stops():
    ms = R3['methods']
    fig, ax = plt.subplots(figsize=(COL, 1.75))
    ys = np.arange(len(ms))[::-1]
    for y, m in zip(ys, ms):
        left, parts = 0, []
        for r, n in sorted(R3['stop_reasons'][m].items(), key=lambda kv: (kv[0] in LIMIT, kv[0] not in CHOSEN, kv[0])):
            if r in LIMIT:
                ax.barh(y, n, left=left, height=0.56, color='#e5e7eb', hatch='/////', edgecolor='#9ca3af', lw=0)
                tc = BODY
            elif r in CHOSEN:
                ax.barh(y, n, left=left, height=0.56, color=mcolor(m))
                tc = 'white'
            else:
                ax.barh(y, n, left=left, height=0.56, color=mcolor(m), alpha=0.42)
                tc = INK
            ax.text(left + n / 2, y, str(n), ha='center', va='center', fontsize=6.0, color=tc)
            parts.append('%s %d' % (STOP[r], n))
            left += n
            ax.plot([left, left], [y - 0.28, y + 0.28], color='white', lw=1.2)
        ax.text(28.6, y, '; '.join(parts), va='center', fontsize=5.6, color=MUTED)
    ax.set_yticks(ys)
    ax.set_yticklabels(ms)
    ax.set_xlim(0, 28)
    ax.set_xticks([0, 7, 14, 21, 28])
    ax.set_xlabel('questions (28 per policy)')
    clean(ax)
    fig.subplots_adjust(right=0.52)
    save(fig, 'fig_rq3_stops')


def rq4_results():
    ms = ['AR-B0', 'AR-B1', 'INT-1']
    d = R4['descriptive']
    fig, axes = plt.subplots(1, 3, figsize=(COL, 1.35))
    fig.subplots_adjust(wspace=0.95)
    for ax, (k, t, sc, kind) in zip(axes, [('source_f1', 'Source F1 ↑', 1., 'rate'), ('total_tokens', 'Tokens ↓', 1., 'tokens'),
                                          ('latency', 'Latency (s) ↓', 1000., 'r1')]):
        vals = [d[m][k] / sc for m in ms]
        ax.bar(range(3), vals, color=[mcolor(m) for m in ms], width=0.6)
        for i, v in enumerate(vals):
            ax.text(i, v * 1.03, pfmt(v, kind), ha='center', va='bottom', fontsize=5.6)
        ax.set_xticks(range(3))
        ax.set_xticklabels(['B0', 'B1', 'INT-1'], fontsize=6.0)
        ax.set_ylim(0, max(vals) * 1.3)
        ax.set_title(t, pad=3, fontsize=7.0)
        clean(ax, 'y')
    for ax, l in zip(axes, 'abc'):
        sub(ax, l, y=-0.32)
    save(fig, 'fig_rq4')


def ranking():
    fig, axes = plt.subplots(3, 1, figsize=(COL, 4.1), gridspec_kw={'height_ratios': [5, 5, 5]})
    fig.subplots_adjust(hspace=0.62)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list('r', ['#0d366b', '#2a78d6', '#86b6ef', '#cde2fb', '#f3f8fe'])
    short = {'answer_f1': 'F1', 'mrr': 'MRR', 'input_tokens': 'input tok.', 'latency': 'latency', 'source_f1': 'source F1', 'total_tokens': 'tokens'}
    for ax, rq, t in zip(axes, ('RQ1', 'RQ2', 'RQ3'), ('RQ1 context management', 'RQ2 fusion', 'RQ3 retrieval control')):
        o = RES[rq]['overall']
        ms, axn = o['order'], [a['metric'] for a in o['axes']]
        n = len(axn)
        for i, m in enumerate(ms):
            for j, a in enumerate(axn):
                v = o['ranks'][m][a]
                c = cmap((v - 1) / 4)
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=c, edgecolor='white', lw=1.2))
                lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
                ax.text(j + 0.5, i + 0.5, '%g' % v, ha='center', va='center', fontsize=6.4, color='white' if lum < 0.5 else INK)
            win = m == o['winner']
            ax.text(n + 0.55, i + 0.5, '%g' % o['total'][m], ha='center', va='center', fontsize=6.6, fontweight='bold' if win else 'normal')
            ax.text(n + 1.55, i + 0.5, fnum(o['scaled'][m], 3), ha='center', va='center', fontsize=6.6, fontweight='bold' if win else 'normal')
            if win:
                ax.add_patch(Rectangle((0.03, i + 0.05), n + 2.0, 0.9, fill=False, edgecolor='#f59e0b', lw=1.1))
        ax.set_xlim(0, n + 2.1)
        ax.set_ylim(len(ms), 0)
        ax.set_xticks([j + 0.5 for j in range(n)] + [n + 0.55, n + 1.55])
        ax.set_xticklabels([short[a] for a in axn] + ['total', 'scaled'], fontsize=6.2)
        ax.xaxis.set_ticks_position('top')
        ax.set_yticks([i + 0.5 for i in range(len(ms))])
        ax.set_yticklabels(ms, fontsize=6.4)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(t, pad=14, fontsize=7.2)
    save(fig, 'fig_ranking')


def bottleneck():
    import json
    rows = json.loads((FL.ROOT / 'documentation/phase6_closeout/comparison.json').read_text(encoding='utf-8'))
    get = lambda b, c, m: next((r['mean'] for r in rows if r['baseline'] == b and r['cohort'] == c and r['metric'] == m), None)
    fig = plt.figure(figsize=(COL, 2.7))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.05, 1], hspace=0.55)
    ax = fig.add_subplot(gs[0])
    B = ['B1', 'B2', 'B3', 'B4']
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list('b', ['#f8fbff', '#9ec5f4', '#2a78d6', '#0d366b'])
    for i, b in enumerate(B):
        for j, m in enumerate(MOD_ORDER):
            v = get(b, 'modality/' + m, 'gold_coverage') or 0.0
            c = cmap(v)
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=c, edgecolor='white', lw=1.0))
            lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
            ax.text(j + 0.5, i + 0.5, fnum(v, 3) if v else '0', ha='center', va='center', fontsize=5.6, color='white' if lum < 0.5 else INK)
    ax.set_xlim(0, 7)
    ax.set_ylim(4, 0)
    ax.set_xticks([j + 0.5 for j in range(7)])
    ax.set_xticklabels(MOD_ORDER, fontsize=6.4)
    ax.xaxis.set_ticks_position('top')
    ax.set_yticks([i + 0.5 for i in range(4)])
    ax.set_yticklabels(['B1 text', 'B2 graph', 'B3 struct.', 'B4 all'], fontsize=6.4)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    sub(ax, 'a', 'retrieval-only gold coverage by sources needed', y=-0.12)
    ax = fig.add_subplot(gs[1])
    S = R3['strata']['modality']
    vals = [S[g]['AR-B1']['answer_f1'] for g in MOD_ORDER]
    ax.bar(range(7), vals, color='#475569', width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.03, fnum(v, 3), ha='center', fontsize=5.8)
    ax.set_xticks(range(7))
    ax.set_xticklabels(MOD_ORDER)
    ax.set_ylim(0, 1.25)
    ax.set_ylabel('answer F1')
    clean(ax, 'y')
    sub(ax, 'b', 'RQ3 answer F1 by sources needed (all policies)', y=-0.3)
    save(fig, 'fig_bottleneck')


if __name__ == '__main__':
    framework()
    example()
    rq1_methods()
    rq2_methods()
    rq3_methods()
    protocol()
    rq1_results()
    scatter(R1, 'input_tokens', 'answer_f1', 'input tokens per question', 'answer F1', 'fig_rq1_scatter')
    rq1_strata()
    rq2_results()
    scatter(R3, 'total_tokens', 'source_f1', 'tokens per question', 'source-selection F1', 'fig_rq3_scatter', h=1.9)
    rq3_forest()
    rq3_stops()
    rq4_results()
    ranking()
    bottleneck()
    print('paper figures written to', OUT)
