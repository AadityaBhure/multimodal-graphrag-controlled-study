"""Figures for the B.Tech project report.

1. Re-renders documentation diagrams and charts in the report typeface (Times New Roman) at 600 dpi.
2. Draws report-specific infographics: report roadmap, research framework map, work breakdown structure,
   use-case diagram, data-flow diagrams (levels 0 and 1) and the distribution of the automated tests.
Figures shared with the papers are taken from ../../paper/scirep/figures and ../../paper/ieee/figures.

Run: python report_figs.py   (writes PNG files to ../figures)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOC = HERE.parents[1] / 'project_documentation'
sys.path.insert(0, str(DOC / 'build'))
OUT = HERE.parent / 'figures'
OUT.mkdir(parents=True, exist_ok=True)

import matplotlib                                         # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                          # noqa: E402
from matplotlib.patches import FancyBboxPatch, Ellipse   # noqa: E402
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
Flow = FL.Flow
INK, MUTED = '#0f172a', '#475569'


def roadmap():
    """Infographic: the six chapters of the report and what each delivers."""
    F = Flow(6.4, 3.3, fs=7.6)
    items = [('c1', 'Chapter 1\nIntroduction', 'problem, scope, hypotheses, objectives', 'io'),
             ('c2', 'Chapter 2\nLiterature Review', '25 works compared; research gaps RG1–RG4', 'data'),
             ('c3', 'Chapter 3\nRequirements (SRS)', 'tools, hardware, WBS, FR/NFR, cost', 'fixed'),
             ('c4', 'Chapter 4\nMethodology', 'architecture, modules, algorithms, protocol, testing', 'rq'),
             ('c5', 'Chapter 5\nResults and Discussion', 'four studies, statistics, application, discussion', 'model'),
             ('c6', 'Chapter 6\nConclusion and Future Scope', 'answers to RQ1–RQ4, next steps', 'stop')]
    xs = [0.95, 3.2, 5.45]
    for i, (k, t, sub, kind) in enumerate(items):
        cx, cy = xs[i % 3], 2.45 if i < 3 else 0.95
        F.box(k, cx, cy, 1.95, 0.92, t + '\n' + sub, kind, bold_first=True)
    F.edge('c1', 'c2', 'right', 'left')
    F.edge('c2', 'c3', 'right', 'left')
    F.path([F.anchor('c3', 'bottom'), (5.45, 1.72), (0.95, 1.72), F.anchor('c4', 'top')])
    F.edge('c4', 'c5', 'right', 'left')
    F.edge('c5', 'c6', 'right', 'left')
    F.note(3.2, 0.18, 'front matter (certificate … abbreviations) precedes Chapter 1; references and appendices follow Chapter 6',
           ha='center', va='center', fs=6.8, style='italic')
    F.save('rp_roadmap')


def framework_map():
    """Infographic: problem → gaps → research questions → strategies → findings."""
    F = Flow(7.0, 4.25, fs=7.0)
    cols = [(0.72, 'Research gap'), (2.2, 'Research question'), (3.95, 'Strategies compared'), (5.95, 'Finding')]
    for x, t in cols:
        F.ax.text(x, 4.08, t, ha='center', va='center', fontsize=8, fontweight='bold', color=INK)
    rows = [
        ('RG1', 'Graph context never compared under one budget', 'RQ1 · Context management', 'CM-B0, CM-B1 | CM-01 KG²RAG, CM-02 G-Retriever, CM-03 QAFD', 'Fixed top-K (CM-B1) wins; no significant F1 difference'),
        ('RG2', 'Fusion never compared on identical evidence', 'RQ2 · Cross-modal fusion', 'CF-B0, CF-B1 | CF-01 KAG, CF-02 SAG, CF-03 MegaRAG', 'Source-separated (CF-B1) wins on cost; answers identical'),
        ('RG3', 'Source selection never compared with the same tools', 'RQ3 · Retrieval control', 'AR-B0, AR-B1 | AR-01 Adaptive-RAG, AR-02 CRAG, AR-03 AGENT-G', 'Rule router (AR-B1) best source F1 at lowest cost (significant)'),
        ('RG4', 'Combined effect of chosen components unknown', 'RQ4 · Integration', 'INT-1 = AR-B1 → CM-B1 → CF-B1', 'Same answers, router-level source selection, +772 tokens'),
    ]
    for i, (g, gt, rq, st, fd) in enumerate(rows):
        y = 3.45 - i * 0.92
        F.box('g%d' % i, 0.72, y, 1.3, 0.74, g + '\n' + gt, 'data', bold_first=True, fs=6.8)
        F.box('q%d' % i, 2.2, y, 1.3, 0.74, rq, 'rq', fs=7.0)
        F.box('s%d' % i, 3.95, y, 1.85, 0.74, st.replace(' | ', '\n'), 'fixed', fs=6.4)
        F.box('f%d' % i, 5.95, y, 1.8, 0.74, fd, 'stop', fs=6.6)
        F.edge('g%d' % i, 'q%d' % i, 'right', 'left')
        F.edge('q%d' % i, 's%d' % i, 'right', 'left')
        F.edge('s%d' % i, 'f%d' % i, 'right', 'left')
    F.save('rp_framework_map')


def wbs():
    """Work breakdown structure: the project and its seven work packages."""
    F = Flow(7.1, 4.6, fs=6.6)
    F.box('root', 3.55, 4.25, 3.0, 0.42, 'Multi-Modal GraphRAG: controlled study and platform', 'io', fs=7.6)
    wps = [('WP1', 'Foundation and data', ['Freeze original demo', 'Research scaffold, contracts', 'Acquire and audit STaRK-MAG', 'Build three isolated views']),
           ('WP2', 'Benchmark', ['Gold before wording', 'Strict source necessity', 'Stress overlays', 'Audits, regeneration']),
           ('WP3', 'Harness and baselines', ['Metrics, run records', 'Resumable runner', 'Retrievers B1–B4', 'Retrieval-only closeout']),
           ('WP4', 'Strategies', ['RQ1: CM-B0…CM-03', 'RQ2: CF-B0…CF-03', 'RQ3: AR-B0…AR-03', 'Compliance audit, repair']),
           ('WP5', 'Experiments and analysis', ['Freeze plans', 'Call and replay phases', 'Statistics, Pareto, ranking', 'RQ4 integration']),
           ('WP6', 'Application', ['Checksummed bundle', '11-page Streamlit app', 'Explorers, live runs', 'Application tests']),
           ('WP7', 'Documentation', ['Phase reports, decision log', 'Project documentation', 'Research papers', 'This report'])]
    w, gap = 0.94, 0.07
    x0 = (7.1 - (7 * w + 6 * gap)) / 2 + w / 2
    F.ax.plot([x0, x0 + 6 * (w + gap)], [3.78, 3.78], color='#475569', lw=1.0)
    F.ax.plot([3.55, 3.55], [4.04, 3.78], color='#475569', lw=1.0)
    for i, (k, t, tasks) in enumerate(wps):
        cx = x0 + i * (w + gap)
        F.ax.plot([cx, cx], [3.78, 3.6], color='#475569', lw=1.0)
        F.box(k, cx, 3.3, w, 0.6, k + '\n' + t, 'rq', bold_first=True, fs=6.8)
        for j, task in enumerate(tasks):
            ty = 2.55 - j * 0.6
            F.box('%s_%d' % (k, j), cx, ty, w, 0.48, task, 'step', fs=6.0)
    F.save('rp_wbs')


def use_case():
    """UML-style use-case diagram of the platform."""
    fig = plt.figure(figsize=(6.6, 4.3))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 6.6)
    ax.set_ylim(0, 4.3)
    ax.axis('off')
    ax.add_patch(FancyBboxPatch((1.45, 0.15), 3.7, 4.0, boxstyle='round,pad=0,rounding_size=0.05', facecolor='#fbfdff', edgecolor='#94a3b8', lw=1.0))
    ax.text(3.3, 4.02, 'Multi-Modal GraphRAG platform', ha='center', va='center', fontsize=8.4, fontweight='bold', color=INK)

    def actor(x, y, name):
        ax.add_patch(plt.Circle((x, y + 0.42), 0.09, fill=False, lw=1.1, color=INK))
        ax.plot([x, x], [y + 0.33, y + 0.08], color=INK, lw=1.1)
        ax.plot([x - 0.16, x + 0.16], [y + 0.25, y + 0.25], color=INK, lw=1.1)
        ax.plot([x, x - 0.13], [y + 0.08, y - 0.12], color=INK, lw=1.1)
        ax.plot([x, x + 0.13], [y + 0.08, y - 0.12], color=INK, lw=1.1)
        ax.text(x, y - 0.24, name, ha='center', va='top', fontsize=7.4, color=INK)
    left = [('Build and audit the three data views', 3.55), ('Construct and verify the benchmark', 3.05), ('Freeze and run a study', 2.55),
            ('Replay runs and analyse results', 2.05), ('Export the checksummed bundle', 1.55)]
    right = [('Browse studies, metrics and statistics', 3.55), ('Explore a question step by step', 3.05), ('Replay and compare pipelines', 2.55),
             ('Run a live question (full profile)', 2.05), ('Verify reproducibility', 1.55)]
    for t, y in left:
        ax.add_patch(Ellipse((2.45, y), 1.75, 0.4, facecolor='#eff6ff', edgecolor='#2563eb', lw=1.0))
        ax.text(2.45, y, t, ha='center', va='center', fontsize=6.5, color=INK)
        ax.plot([0.75, 1.58], [2.55, y], color='#64748b', lw=0.7)
    for t, y in right:
        ax.add_patch(Ellipse((4.15, y), 1.75, 0.4, facecolor='#f0fdfa', edgecolor='#0d9488', lw=1.0))
        ax.text(4.15, y, t, ha='center', va='center', fontsize=6.5, color=INK)
        ax.plot([5.85, 5.02], [2.55, y], color='#64748b', lw=0.7)
    ax.add_patch(Ellipse((3.3, 0.75), 2.2, 0.4, facecolor='#f5f3ff', edgecolor='#7c3aed', lw=1.0))
    ax.text(3.3, 0.75, 'Answer a question with the local LLM', ha='center', va='center', fontsize=6.5, color=INK)
    ax.plot([2.45, 2.75], [1.35, 0.92], color='#7c3aed', lw=0.7, ls=(0, (3, 2)))
    ax.plot([4.15, 3.85], [1.35, 0.92], color='#7c3aed', lw=0.7, ls=(0, (3, 2)))
    ax.text(3.3, 1.08, '«include»', fontsize=6.0, color='#7c3aed', ha='center')
    actor(0.62, 2.35, 'Researcher')
    actor(5.98, 2.35, 'Presenter /\nreviewer')
    save(fig, 'rp_use_case')


def dfd():
    """Data-flow diagrams: level 0 (context) and level 1."""
    F = Flow(7.0, 2.3, fs=7.2)
    F.box('u', 0.8, 1.15, 1.25, 0.62, 'Researcher /\nreviewer', 'io')
    F.box('p', 3.4, 1.15, 2.1, 0.95, '0\nMulti-Modal GraphRAG platform', 'rq', bold_first=True)
    F.box('d', 6.05, 1.75, 1.6, 0.55, 'STaRK-MAG release\n(Hugging Face)', 'data')
    F.box('m', 6.05, 0.55, 1.6, 0.55, 'Local LLM server\n(gpt-oss:20b)', 'llm')
    F.path([(1.43, 1.3), (2.35, 1.3)], label='questions, settings', label_at=0, lpos=0.5, ldx=0.0, ldy=0.13, lha='center')
    F.path([(2.35, 1.0), (1.43, 1.0)], label='answers, results, traces', label_at=0, lpos=0.5, ldx=0.0, ldy=-0.13, lha='center')
    F.path([(5.25, 1.75), (4.45, 1.45)], label='raw records', label_at=0, lpos=0.4, ldx=0.05, ldy=0.14, lha='center')
    F.path([(4.45, 0.95), (5.25, 0.65)], label='prompts', label_at=0, lpos=0.4, ldx=0.0, ldy=-0.14, lha='center')
    F.path([(5.25, 0.45), (4.45, 0.75)], label='answers', label_at=0, lpos=0.5, ldx=0.0, ldy=-0.2, lha='center')
    F.save('rp_dfd0')

    F = Flow(7.1, 4.6, fs=6.6)
    procs = [('p1', 1.0, 3.55, '1.0\nBuild views'), ('p2', 1.0, 2.3, '2.0\nBuild benchmark'), ('p3', 3.2, 3.55, '3.0\nRetrieve (B1–B3)'),
             ('p4', 3.2, 2.3, '4.0\nControl · context · fusion'), ('p5', 5.2, 3.55, '5.0\nGenerate answer'), ('p6', 5.2, 2.3, '6.0\nEvaluate and analyse'),
             ('p7', 5.2, 0.85, '7.0\nExport bundle, serve app')]
    for k, x, y, t in procs:
        F.box(k, x, y, 1.45, 0.62, t, 'rq', bold_first=True)
    stores = [('d1', 1.0, 4.35, 'D1 Raw STaRK-MAG', 1.6), ('d2', 1.0, 0.85, 'D2 Three views (FAISS, CSR, DuckDB)', 1.8),
              ('d3', 3.2, 0.85, 'D3 Benchmark (gold, overlays)', 1.6), ('d4', 6.55, 4.35, 'D4 Stage store', 1.0),
              ('d5', 6.55, 1.55, 'D5 Run records, analyses', 1.0)]
    for k, x, y, t, w in stores:
        F.box(k, x, y, w, 0.42, t, 'data', fs=6.1)
    for a, b in (('d1', 'p1'), ('p1', 'p2'), ('p3', 'p4'), ('p5', 'p6'), ('p6', 'p7')):
        F.edge(a, b)
    F.edge('p2', 'd3', 'right', 'top', via=[(2.1, 2.3), (2.1, 1.4), (3.2, 1.4)])
    F.edge('d2', 'p3', 'right', 'left', via=[(2.05, 0.85), (2.05, 3.55)], label='indexes', label_at=1, lpos=0.85, ldx=0.05)
    F.edge('p1', 'd2', 'left', 'left', via=[(0.15, 3.55), (0.15, 0.85)])
    F.edge('d3', 'p4', 'top', 'bottom')
    F.edge('p4', 'p5', 'right', 'left', via='hvh', label='context', label_at=1, lpos=0.5, ldx=0.05)
    F.edge('p5', 'd4', 'right', 'left', via=[(6.05, 3.55), (6.05, 4.35)], label='stored request', label_at=0, lpos=0.0, ldx=0.03, ldy=-0.12)
    F.edge('p6', 'd5', 'right', 'top', via='hv')
    F.edge('d5', 'p7', 'bottom', 'right', via='vh')
    F.save('rp_dfd1')


def tests_distribution():
    cats = [('Original demonstration (frozen)', 18), ('Data source audit and views', 29), ('Benchmark', 16), ('Scaffold and evaluation harness', 42),
            ('Retrieval baselines', 20), ('RQ1 context management', 65), ('RQ2 fusion', 43), ('RQ3 retrieval control', 43),
            ('RQ4 integration', 5), ('Research UIs and application', 46)]
    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    y = range(len(cats))[::-1]
    ax.barh(list(y), [c for _, c in cats], color='#2563eb', height=0.62)
    for yy, (_, c) in zip(y, cats):
        ax.text(c + 0.8, yy, str(c), va='center', fontsize=7.4)
    ax.set_yticks(list(y))
    ax.set_yticklabels([n for n, _ in cats], fontsize=7.6)
    ax.set_xlabel('automated tests (327 in total, all passing)', fontsize=7.8)
    ax.tick_params(axis='x', labelsize=7.2)
    ax.set_xlim(0, 75)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    save(fig, 'rp_tests_by_area')


if __name__ == '__main__' and sys.argv[1:]:
    for name in sys.argv[1:]:
        globals()[name]()
    sys.exit(0)
if __name__ == '__main__':
    for f in (MD.pipeline, MD.statistics_flow, MD.ranking_flow, MD.app_profiles, MD.app_answer_tree, MC.tests_growth, MC.upstream, MC.overall):
        f()
    roadmap()
    framework_map()
    wbs()
    use_case()
    dfd()
    tests_distribution()
    print('figures written to', OUT)
