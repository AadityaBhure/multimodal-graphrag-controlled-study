"""Flow diagrams for the project documentation (hand-placed, deterministic)."""
from datetime import date

from figlib import *

plt.rcParams['font.family'] = ['Segoe UI', 'Segoe UI Symbol', 'DejaVu Sans']


def column(F, cx, top, w, items, gap=0.2, connect=True, fs=None):
    """items: (key, text, kind, h[, n]); placed top-down from `top`; consecutive items joined by arrows."""
    y = top
    for it in items:
        key, text, kind, h = it[:4]
        n = it[4] if len(it) > 4 else None
        F.box(key, cx, y - h / 2, w, h, text, kind, n=n, fs=fs, bold_first='\n' in text)
        y -= h + gap
    if connect:
        for a, b in zip(items, items[1:]):
            F.edge(a[0], b[0])
    return y


# ======================================================================= overview diagrams
def pipeline():
    F = Flow(7.2, 2.95, fs=8.0)
    F.box('q', 0.48, 1.5, 0.78, 0.62, 'Question\n(natural language)', 'io', bold_first=True)
    F.box('ar', 1.58, 1.5, 0.98, 0.95, 'Retrieval control\nwhich sources, in what order, when to stop', 'rq', bold_first=True)
    F.box('grp', 2.78, 1.5, 1.08, 1.86, 'Retrievers', 'group', fs=7.4)
    F.box('t', 2.78, 1.93, 0.92, 0.4, 'Text · B1\ndense search', 'text', bold_first=True, fs=7.6)
    F.box('g', 2.78, 1.45, 0.92, 0.4, 'Graph · B2\ntraversal', 'graph', bold_first=True, fs=7.6)
    F.box('s', 2.78, 0.97, 0.92, 0.4, 'Structured · B3\nread-only SQL', 'structured', bold_first=True, fs=7.6)
    F.box('cm', 3.98, 1.5, 0.98, 0.95, 'Context management\nwhat graph evidence survives the budget', 'rq', bold_first=True)
    F.box('cf', 5.1, 1.5, 0.98, 0.95, 'Fusion\nhow the three sources are combined', 'rq', bold_first=True)
    F.box('llm', 6.24, 1.5, 0.92, 0.95, 'Answer model\nshared and fixed (gpt-oss:20b)', 'fixed', bold_first=True)
    F.box('ans', 6.24, 0.36, 0.92, 0.42, 'Answer = set of paper IDs', 'io', fs=7.6)
    for k, lab in (('ar', 'Part 3 · RQ3'), ('cm', 'Part 1 · RQ1'), ('cf', 'Part 2 · RQ2')):
        cx, cy, w, h, _ = F.n[k]
        F.ax.text(cx, cy + h / 2 + 0.1, lab, ha='center', va='bottom', fontsize=7.6, color='white', fontweight='bold',
                  bbox=dict(boxstyle='round,pad=0.22', facecolor='#1d4ed8', edgecolor='none'))
    F.edge('q', 'ar', 'right', 'left')
    for k in ('t', 'g', 's'):
        F.edge('ar', k, 'right', 'left', via='hvh')
        F.edge(k, 'cm', 'right', 'left', via='hvh')
    F.edge('cm', 'cf', 'right', 'left')
    F.edge('cf', 'llm', 'right', 'left')
    F.edge('llm', 'ans')
    F.ax.add_patch(FancyBboxPatch((1.02, 2.47), 4.64, 0.3, boxstyle='round,pad=0,rounding_size=0.05', facecolor='#f5f3ff', edgecolor='#7c3aed', linewidth=1))
    F.ax.text(3.34, 2.62, 'Part 4 · RQ4: the best choice of each part, combined into one system', ha='center', va='center', fontsize=7.8, color='#5b21b6')
    F.note(0.1, 0.42, 'Blue boxes are studied one at a time (only that component changes); grey and coloured boxes stay fixed.', fs=7.4, w=5.0)
    return F.save('d_pipeline')


def architecture():
    layers = [
        ('1 · Data', [('STaRK-MAG official release (pinned)', 'data'), ('Text view: 700,244 papers, FAISS', 'text'), ('Graph view: 1.87 M nodes, CSR', 'graph'),
                          ('Structured view: DuckDB table', 'structured'), ('Benchmark: 13,571 questions', 'data')]),
        ('2 · Retrieval', [('B1 dense text search', 'text'), ('B2 graph traversal', 'graph'), ('B3 typed read-only SQL', 'structured'), ('B4 all three, fixed', 'fixed')]),
        ('3 · Studied components', [('RQ1 context management\nCM-B0, CM-B1, CM-01, CM-02, CM-03', 'rq'), ('RQ2 fusion\nCF-B0, CF-B1, CF-01, CF-02, CF-03', 'rq'),
                                         ('RQ3 retrieval control\nAR-B0, AR-B1, AR-01, AR-02, AR-03', 'rq'), ('RQ4 integration\nINT-1', 'rq')]),
        ('4 · Generation', [('Shared answer model gpt-oss:20b (temperature 0, JSON, 1,024-token cap)', 'llm'), ('Grounding prompt + strict parser: only paper IDs present in the context', 'step')]),
        ('5 · Execution', [('Frozen execution plans (SHA-256 of every input)', 'step'), ('Durable stage store: every model request and response', 'data'),
                               ('Replay-only runner: per-question records', 'step')]),
        ('6 · Analysis', [('Metrics per question', 'step'), ('Family-clustered paired statistics, Holm', 'step'), ('Pareto sets and overall ranking', 'step'),
                              ('Results package and paper', 'data')]),
        ('7 · Presentation', [('Checksummed showcase bundle', 'data'), ('Showcase app: 11 pages, recorded and live runs', 'io')]),
    ]
    H = 0.86 * len(layers) + 0.3
    F = Flow(7.2, H, fs=7.6)
    y = H - 0.2
    keys = []
    for title, boxes in layers:
        top = y
        F.box('L' + title, 3.6, top - 0.38, 7.0, 0.72, title, 'group', fs=7.8)
        n = len(boxes)
        x0, x1 = 1.45, 7.0
        w = (x1 - x0 - 0.08 * (n - 1)) / n
        for i, (t, k) in enumerate(boxes):
            cx = x0 + w / 2 + i * (w + 0.08)
            F.box('%s%d' % (title, i), cx, top - 0.4, w, 0.5, t, k, fs=7.2, bold_first='\n' in t)
        keys.append('L' + title)
        y -= 0.86
    for a, b in zip(keys, keys[1:]):
        ax_, ay, aw, ah, _ = F.n[a]
        bx_, by, bw, bh, _ = F.n[b]
        F.path([(0.62, ay - ah / 2), (0.62, by + bh / 2)])
    return F.save('d_architecture')


def timeline():
    phases = [  # (label, start, end, group)
        ('Phase 0 · freeze the original MVP', '2026-10-04', '2026-10-04', 'infra'),
        ('Phase 1 · research scaffold and contracts', '2026-10-04', '2026-10-04', 'infra'),
        ('Phase 2 · acquire and audit STaRK-MAG', '2026-10-04', '2026-10-04', 'data'),
        ('Phase 3 · build the three views', '2026-10-04', '2026-10-06', 'data'),
        ('Phase 4 · benchmark construction', '2026-10-06', '2026-10-07', 'data'),
        ('Phase 5 · evaluation harness and runner', '2026-10-07', '2026-10-07', 'infra'),
        ('Phase 6 · baselines B1–B4 and closeout', '2026-10-07', '2026-10-08', 'infra'),
        ('Phase 6.5 · research inspection UIs', '2026-10-08', '2026-10-08', 'app'),
        ('Phases 7–8 · first RQ1/RQ2 diagnostics (kept, superseded)', '2026-10-08', '2026-10-11', 'study'),
        ('Compliance audit (93 requirements) and repair design', '2026-10-11', '2026-10-12', 'study'),
        ('Phase 9 · RQ3 policies implemented', '2026-10-11', '2026-10-12', 'study'),
        ('Completion plan, RQ1 execution checks', '2026-10-12', '2026-10-12', 'study'),
        ('Two-week scope revision', '2026-10-15', '2026-10-15', 'study'),
        ('RQ3 labels, AR-01 training, AR-02 calibration, freeze', '2026-10-16', '2026-10-16', 'study'),
        ('RQ2 settings approved and frozen', '2026-10-16', '2026-10-16', 'study'),
        ('RQ4 design and analysis plans frozen', '2026-10-17', '2026-10-17', 'study'),
        ('All four studies run and analysed (0 errors)', '2026-10-17', '2026-10-17', 'result'),
        ('Results package, paper, overall ranking', '2026-10-17', '2026-10-17', 'result'),
        ('Showcase app', '2026-10-17', '2026-10-18', 'app'),
        ('This documentation', '2026-10-18', '2026-10-18', 'app'),
    ]
    col = {'infra': '#475569', 'data': '#0d9488', 'study': '#2563eb', 'result': '#16a34a', 'app': '#7c3aed'}
    d0 = date(2026, 10, 4)
    day = lambda s: (date.fromisoformat(s) - d0).days
    fig, ax = plt.subplots(figsize=(7.4, 0.27 * len(phases) + 0.9))
    for i, (lab, a, b, g) in enumerate(phases):
        y = len(phases) - i
        ax.barh(y, day(b) - day(a) + 1, left=day(a), height=0.6, color=col[g])
        ax.text(day(b) + 1.15, y, lab, va='center', fontsize=7.8, color=BODY)
    ax.set_yticks([])
    ticks = list(range(0, 15))
    ax.set_xticks([t + 0.5 for t in ticks])
    ax.set_xticklabels(['%d' % (4 + t) for t in ticks], fontsize=7.6)
    ax.set_xlabel('October 2026 (day of month)')
    ax.set_xlim(0, 26)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=col[k], label=l) for k, l in (('infra', 'infrastructure'), ('data', 'data and benchmark'), ('study', 'studies'),
                                                                   ('result', 'results'), ('app', 'presentation'))], ncol=5, loc='upper center',
              bbox_to_anchor=(0.42, -0.12), fontsize=7.6)
    return save(fig, 'd_timeline')


def data_build():
    F = Flow(7.2, 4.75, fs=7.8)
    F.box('src', 3.6, 4.4, 5.6, 0.48, 'STaRK-MAG official release\nHugging Face snap-stanford/stark, pinned revision 88269e23… (CC-BY-4.0 data, MIT code)', 'io', bold_first=True)
    F.box('p2', 3.6, 3.66, 6.2, 0.56, 'Phase 2 · acquire and audit\n15 files with SHA-256; 1,872,968 entities; 19,919,698 directed edges; 13,323 synthetic + 84 human questions; nothing filled or repaired', 'step', bold_first=True, n=1)
    F.box('p3', 3.6, 2.86, 6.2, 0.56, 'Phase 3 · canonical registry\none identity per entity: stark:<global node ID>; 1,714,702 exact aliases (NFKC, casefold), ambiguous ones kept ambiguous', 'step', bold_first=True, n=2)
    F.box('t', 1.22, 1.72, 2.2, 1.12, 'Text view\n700,244 documents = title + two newlines + abstract; MiniLM-L6-v2 (ONNX, 384-d, 256-token input); exact FAISS IndexFlatIP', 'text', bold_first=True)
    F.box('g', 3.6, 1.72, 2.2, 1.12, 'Graph view\n1,872,968 nodes; 19,919,698 official edges + the same number of tagged inverse rows (39,839,396 traversal rows); memory-mapped CSR', 'graph', bold_first=True)
    F.box('s', 5.98, 1.72, 2.2, 1.12, 'Structured view\nDuckDB papers_structured: year, date, citations, rank, venue, document type; missing values stay NULL', 'structured', bold_first=True)
    F.box('man', 3.6, 0.42, 6.2, 0.5, 'Manifest: 358 files, 4.12 GB, SHA-256 each; exhaustive isolation and equality audits pass', 'data', n=3)
    F.edge('src', 'p2')
    F.edge('p2', 'p3')
    for k in ('t', 'g', 's'):
        F.edge('p3', k, via='vhv')
        F.edge(k, 'man', via='vhv')
    return F.save('d_data_build')


def benchmark_flow():
    F = Flow(7.2, 7.1, fs=7.9)
    cx, w = 2.75, 4.6
    F.box('b1', cx, 6.75, w, 0.5, 'Choose conditions for one of 7 source combinations (T, G, S, TG, TS, GS, TGS)\nseed 42; construction instances and graph anchors are exclusive to one split', 'step', bold_first=True, n=1)
    F.box('b2', cx, 5.95, w, 0.62, 'Compute every condition on the frozen data, before any wording\ntext: exact case-insensitive abstract phrases · graph: author / institution / citation paths · structured: parameterised predicates', 'step', bold_first=True, n=2)
    F.box('b3', cx, 5.12, w, 0.44, 'Intersect the candidate sets → gold answer set (sorted paper IDs, hashed)', 'step', n=3)
    F.box('b4', cx, 4.18, 3.3, 0.98, 'Drop any one required source: does the answer set strictly grow?', 'decision', n=4)
    F.box('rej', 6.05, 4.18, 1.9, 0.5, 'Reject the construction (sources not all necessary)', 'fail')
    F.box('b5', cx, 3.2, w, 0.44, 'Word the question from a template (no answer IDs or titles in the text)', 'step', n=5)
    F.box('b6', cx, 2.42, w, 0.62, 'Add stress variants as evaluation-time overlays\nnoisy: hard distractors · conflict: one altered fact (canonical record stays authoritative) · unanswerable: a verified empty answer', 'step', bold_first=True, n=6)
    F.box('b7', cx, 1.52, w, 0.62, 'Audit and regenerate\nrecompute all gold sets and witness paths; leakage scans; full rebuild byte-identical (323 files)', 'step', bold_first=True, n=7)
    F.box('b8', cx, 0.62, w, 0.56, 'Freeze\nbenchmark manifest SHA-256; human-review package of 3,390 items prepared (decisions pending)', 'stop', bold_first=True, n=8)
    for a, b in (('b1', 'b2'), ('b2', 'b3'), ('b3', 'b4'), ('b5', 'b6'), ('b6', 'b7'), ('b7', 'b8')):
        F.edge(a, b)
    F.edge('b4', 'b5', label='yes, for every source')
    F.edge('b4', 'rej', 'right', 'left', label='no', lpos=0.3, ldy=0.1)
    F.note(5.25, 6.95, 'Result: 167 generated questions = 42 base constructions (2 per source combination × 3 splits) × 4 variants, minus 1 infeasible noisy variant.', w=1.85, fs=7.3)
    F.note(5.25, 2.9, 'Variants of one base question form a family. Families, not questions, are the independent units in every statistical test.', w=1.85, fs=7.3)
    return F.save('d_benchmark')


def execution():
    F = Flow(7.2, 6.3, fs=7.9)
    cx, w = 2.6, 4.2
    F.box('e1', cx, 5.95, w, 0.56, 'Freeze the study\nexecution plan = SHA-256 of every code file, config, prompt, input, model artefact and cohort', 'step', bold_first=True, n=1)
    F.box('e2', cx, 5.05, 3.1, 0.86, 'Start or resume: does every hash still match?', 'decision', n=2)
    F.box('ref', 6.05, 5.05, 1.95, 0.5, 'Refuse to run; nothing is sent', 'fail')
    F.box('e3', cx, 4.06, w, 0.62, 'Call phase (question-major)\nfor each question, every method runs through the frozen system; each model request is sent once', 'step', bold_first=True, n=3)
    F.box('st', 6.05, 4.06, 1.95, 0.9, 'Durable stage store\nkey = SHA-256 of the full request; value = response, usage, timing', 'data', bold_first=True)
    F.box('e4', cx, 3.0, w, 0.7, 'Replay phase\nthe unchanged runner re-executes each method; the dispatcher may only answer from the store and stops if any request differs', 'step', bold_first=True, n=4)
    F.box('e5', cx, 2.04, w, 0.5, 'Per-question run records: atomic commits; failures recorded, never retried silently', 'data', n=5)
    F.box('e6', cx, 1.2, w, 0.5, 'Frozen analysis script → analysis file (statistics, Pareto set, strata, failure taxonomy)', 'step', n=6)
    F.box('e7', cx, 0.4, w, 0.46, 'Results package → paper → checksummed showcase bundle → app', 'stop', n=7)
    F.edge('e1', 'e2')
    F.edge('e2', 'e3', label='yes')
    F.edge('e2', 'ref', 'right', 'left', label='no', lpos=0.3, ldy=0.1)
    F.edge('e3', 'st', 'right', 'left', label='store', lpos=0.25, ldy=0.1)
    F.edge('st', 'e4', 'bottom', 'right', via='vh', label='byte-identical responses', lpos=0.5, ldx=-0.95, ldy=-0.12)
    for a, b in (('e3', 'e4'), ('e4', 'e5'), ('e5', 'e6'), ('e6', 'e7')):
        F.edge(a, b)
    return F.save('d_execution')


def statistics_flow():
    F = Flow(7.2, 3.7, fs=7.8)
    F.box('a', 0.85, 2.5, 1.45, 0.78, 'Per question\nmetric of method A and of method B on the same question', 'io', bold_first=True)
    F.box('b', 2.55, 2.5, 1.5, 0.78, 'Paired difference\nd = A − B for every question', 'step', bold_first=True, n=1)
    F.box('c', 4.3, 2.5, 1.55, 0.78, 'Family sums\nS_f = sum of d over the variants of family f', 'step', bold_first=True, n=2)
    F.box('bs', 6.2, 3.18, 1.85, 0.82, 'Bootstrap 95 % CI\nresample families with replacement 10,000× (seed 42); mean Δ = ΣS / Σn', 'step', bold_first=True, n=3)
    F.box('sf', 6.2, 1.86, 1.85, 0.86, 'Exact sign-flip test\nall 2^F sign patterns of the S_f; p = share with |total| ≥ |observed|', 'step', bold_first=True, n=4)
    F.box('h', 4.3, 0.75, 1.75, 0.66, 'Holm correction\nover the pre-specified pairs of that metric', 'step', bold_first=True, n=5)
    F.box('d', 2.2, 0.75, 1.75, 0.82, 'Holm p < 0.05?', 'decision', n=6)
    F.box('y', 0.62, 1.2, 1.0, 0.38, 'significant', 'stop', fs=7.6)
    F.box('nn', 0.62, 0.3, 1.0, 0.38, 'not significant', 'fail', fs=7.6)
    F.edge('a', 'b', 'right', 'left')
    F.edge('b', 'c', 'right', 'left')
    F.edge('c', 'bs', 'right', 'left', via='hvh')
    F.edge('c', 'sf', 'right', 'left', via='hvh')
    F.edge('sf', 'h', 'bottom', 'right', via='vh')
    F.edge('h', 'd', 'left', 'right')
    F.edge('d', 'y', 'left', 'right', via='hvh', label='yes', lpos=0.1, ldy=0.1, label_at=1)
    F.edge('d', 'nn', 'left', 'right', via='hvh', label='no', lpos=0.1, ldy=-0.1, label_at=1)
    return F.save('d_statistics')


def ranking_flow():
    F = Flow(7.2, 2.5, fs=7.7)
    xs = [0.66, 1.98, 3.3, 4.62, 5.94]
    texts = [('Pareto axes\nthe quality and cost measures frozen for the study', 'io'),
             ('Rank 1–5 per axis\nbest = 1; tied methods share the average rank', 'step'),
             ('Rank total\nsum over the axes, each axis weighted equally', 'step'),
             ('Lowest total wins\nties: higher answer F1, then fewer tokens, then B1, 01, 02, 03, B0', 'step'),
             ('Check\nmean of min-max scaled axis scores picks the same winner', 'step')]
    for i, (x, (t, k)) in enumerate(zip(xs, texts)):
        F.box('r%d' % i, x, 1.75, 1.18, 1.0, t, k, bold_first=True, n=i if i else None)
    for i in range(4):
        F.edge('r%d' % i, 'r%d' % (i + 1), 'right', 'left')
    F.box('w', 2.3, 0.45, 3.6, 0.5, 'One winner per study, chained in pipeline order: AR-B1 → CM-B1 → CF-B1', 'stop')
    F.box('c', 5.65, 0.45, 2.5, 0.5, 'Identical to INT-1, chosen earlier by the frozen RQ4 rule', 'rq')
    F.edge('r4', 'w', 'bottom', 'right', via='vh')
    F.edge('w', 'c', 'right', 'left')
    return F.save('d_ranking')


# ======================================================================= method flowcharts
SIDE_X, SIDE_W = 5.85, 2.3


def cm_b0():
    F = Flow(7.2, 4.0)
    F.box('in', 2.4, 3.65, 3.6, 0.48, 'Graph candidate pool of the question (identical for all five methods)', 'io')
    F.box('a', 2.4, 2.9, 3.6, 0.44, 'Take the next node or edge record in retrieved order', 'step', n=1)
    F.box('d', 2.4, 2.0, 2.6, 0.82, 'Does the whole record fit the remaining graph budget?', 'decision', n=2)
    F.box('add', 0.7, 1.15, 1.25, 0.44, 'Append it unchanged', 'step', n=3)
    F.box('out', 2.4, 0.5, 3.0, 0.44, 'Graph context = the records appended so far', 'stop')
    F.edge('in', 'a')
    F.edge('a', 'd')
    F.edge('d', 'add', 'left', 'top', via='hv', label='yes', lpos=0.4, ldy=0.1)
    F.path([F.anchor('add', 'left'), (0.0 + 0.05, 1.15), (0.05, 2.9), F.anchor('a', 'left')], label='next record', label_at=1, ldx=0.04)
    F.edge('d', 'out', label='no (or no records left)')
    F.box('n', SIDE_X, 2.5, SIDE_W, 1.5, 'Notes', 'group', fs=7.4)
    F.note(SIDE_X - SIDE_W / 2 + 0.1, 2.95, 'No reordering and no extra model call. Records are atomic (never cut). Text and structured evidence of mixed questions pass through unchanged, as for every RQ1 method. Total context cap: 24,000 characters.', w=SIDE_W - 0.2, fs=7.4)
    return F.save('m_cm_b0')


def cm_b1():
    F = Flow(7.2, 4.4)
    end = column(F, 2.4, 4.25, 3.6, [
        ('in', 'Graph candidate pool of the question', 'io', 0.42),
        ('a', 'Rank candidate papers in retriever order\npath length, then seed rank, then node ID', 'step', 0.55, 1),
        ('b', 'Keep the first 5 papers (graph depth ≤ 2)', 'step', 0.42, 2),
        ('c', 'Add the parent paths that connect each kept paper to its seed entity', 'step', 0.5, 3),
        ('d', 'Serialise in deterministic depth-first order', 'step', 0.42, 4),
        ('out', 'Graph context: 5 papers and their paths', 'stop', 0.42)])
    F.box('n', SIDE_X, 2.6, SIDE_W, 1.7, 'Why it matters', 'group', fs=7.4)
    F.note(SIDE_X - SIDE_W / 2 + 0.1, 3.3, 'A fixed top-K cut: no model call, no scoring beyond the retriever’s own order. In RQ1 it used about a third of the raw control’s input tokens (1,416 vs 4,499) at equal or better F1 and MRR, and it is the context step of the final system.', w=SIDE_W - 0.2, fs=7.4)
    return F.save('m_cm_b1')


def cm_01():
    F = Flow(7.2, 7.25)
    column(F, 2.45, 7.1, 3.75, [
        ('in', 'Graph candidate pool of the question', 'io', 0.38),
        ('a', 'Build provenance units\none per official relation, written from labels and IDs only: “Author A writes Paper P.”, “Paper A cites Paper B.”, …', 'step', 0.62, 1),
        ('b', 'Embed the question and every unit (MiniLM) and score units by cosine similarity', 'model', 0.48, 2),
        ('c', 'Take the 10 most similar units as seeds', 'step', 0.38, 3),
        ('d', 'Expand one hop around the seeds, inside the candidate pool only', 'step', 0.44, 4),
        ('e', 'Split the expanded graph into connected components', 'step', 0.38, 5),
        ('f', 'Maximum spanning tree per component\nKruskal on edge weight = cosine(question, unit); ties by unit ID', 'step', 0.55, 6),
        ('g', 'Depth-first serialisation rooted at the highest-weight edge', 'step', 0.44, 7),
        ('h', 'Rank the trees with the BGE cross-encoder reranker (bge-reranker-large, pinned revision)', 'model', 0.48, 8),
        ('i', 'Remove duplicate units; pack trees into the graph budget in rank order', 'step', 0.44, 9),
        ('out', 'Graph context: organised evidence trees', 'stop', 0.38)], gap=0.17)
    F.box('n', SIDE_X, 5.0, SIDE_W, 2.0, 'Fallbacks and boundaries', 'group', fs=7.4)
    F.note(SIDE_X - SIDE_W / 2 + 0.1, 5.75, 'Units never contain abstracts, years, venues or citation counts (graph isolation). Derived inverse rows map back to the same official edge. If no usable structure exists the method keeps semantic units only; with no units the graph context is empty. It never falls back to text. Adapted from KG²RAG: seed relations, expansion, spanning-tree organisation and reranking.', w=SIDE_W - 0.2, fs=7.3)
    return F.save('m_cm_01')


def cm_02():
    F = Flow(7.2, 5.9)
    column(F, 2.45, 5.75, 3.75, [
        ('in', 'Graph candidate pool of the question', 'io', 0.38),
        ('a', 'Embed node labels and edge descriptions (the same relation templates) with MiniLM', 'model', 0.5, 1),
        ('b', 'Node prizes: the 3 nodes most similar to the question get 3, 2, 1; all others 0', 'step', 0.5, 2),
        ('c', 'Edge prizes: the 5 most similar edges get 5 … 1; every edge costs Ce = 0.5', 'step', 0.5, 3),
        ('d', 'Prize-collecting Steiner tree with pcst_fast\nunrooted, one tree, GW pruning; edge prizes via virtual nodes', 'step', 0.6, 4),
        ('e', 'One connected subgraph that maximises prizes minus costs', 'step', 0.44, 5),
        ('f', 'Serialise breadth-first; drop lowest-contribution leaves until it fits', 'step', 0.5, 6),
        ('out', 'Graph context: one small connected subgraph', 'stop', 0.38)], gap=0.18)
    F.box('n', SIDE_X, 3.3, SIDE_W, 2.0, 'Notes', 'group', fs=7.4)
    F.note(SIDE_X - SIDE_W / 2 + 0.1, 4.05, 'Adapted from G-Retriever (no graph neural network or soft prompt). A disconnected solver output is reported as an error, not silently replaced. Smallest and fastest context in RQ1 (6.5 s) but the lowest MRR (0.187).', w=SIDE_W - 0.2, fs=7.3)
    return F.save('m_cm_02')


def cm_03():
    F = Flow(7.2, 7.0)
    cx, w = 2.45, 3.75
    F.box('in', cx, 6.8, w, 0.36, 'Question and graph candidate pool', 'io')
    F.box('a', cx, 6.18, w, 0.5, 'Keyword extraction: one model call (strict JSON, cached per question)', 'llm', n=1)
    F.box('b', cx, 5.5, w, 0.55, 'Seed scores = highest cosine(keyword, node label); take 20 seeds, mass 10 each', 'model', n=2)
    F.box('c', cx, 4.78, w, 0.58, 'Edge conductance = H(u,v) · (1 + 0.25 · (H(u,q) + H(v,q))), with H = (cosine + 1) / 2', 'step', n=3)
    F.box('d', cx, 4.02, w, 0.52, 'Push excess mass from the node with the largest excess (each node holds at most 1)', 'step', n=4)
    F.box('e', cx, 3.08, 2.9, 0.9, 'Total excess ≤ ε = 0.05?', 'decision', n=5)
    F.box('f', 5.55, 3.08, 1.9, 0.62, 'Pushes < 1,000,000?', 'decision', fs=7.6)
    F.box('g', cx, 2.1, w, 0.5, 'Support = nodes with x > 0.01, plus the connectors between them', 'step', n=6)
    F.box('h', cx, 1.32, w, 0.5, 'Prune the lowest-x outer nodes until the graph budget fits', 'step', n=7)
    F.box('out', cx, 0.6, w, 0.38, 'Graph context: the high-flow region', 'stop')
    for a, b in (('in', 'a'), ('a', 'b'), ('b', 'c'), ('c', 'd'), ('d', 'e'), ('g', 'h'), ('h', 'out')):
        F.edge(a, b)
    F.edge('e', 'g', label='yes (converged)')
    F.edge('e', 'f', 'right', 'left', label='no', lpos=0.35, ldy=0.1)
    F.path([F.anchor('f', 'top'), (5.55, 4.02), F.anchor('d', 'right')], label='yes: keep pushing', label_at=0, lpos=0.5, ldx=0.06)
    F.path([F.anchor('f', 'bottom'), (5.55, 2.1), F.anchor('g', 'right')], label='no: use current support', label_at=0, lpos=0.45, ldx=0.06)
    F.note(4.62, 1.52, 'Adapted from QAFD-RAG. Converged in 5 of 32 questions; the slowest method (40.7 s) because of the diffusion and its extra model call, but it kept the most correct papers in context (gold coverage 0.338).', w=2.45, fs=7.2)
    return F.save('m_cm_03')


def cf_b0():
    F = Flow(7.2, 3.3)
    column(F, 2.4, 3.15, 3.6, [
        ('in', 'Frozen evidence bundle (text, graph, structured items)', 'io', 0.42),
        ('a', 'Write all items one after another in source order: text, graph, structured', 'step', 0.5, 1),
        ('b', 'Stop when the next whole item would exceed 24,000 characters', 'step', 0.44, 2),
        ('c', 'Answer call with the shared prompt', 'llm', 0.42, 3),
        ('out', 'Answer: paper IDs grounded in the context', 'stop', 0.4)], gap=0.18)
    F.note(4.55, 2.9, 'Control. One model call. Every RQ2 method receives the byte-identical bundle and may not retrieve anything new.', w=2.5, fs=7.4)
    return F.save('m_cf_b0')


def cf_b1():
    F = Flow(7.2, 3.3)
    column(F, 2.4, 3.15, 3.6, [
        ('in', 'Frozen evidence bundle (text, graph, structured items)', 'io', 0.42),
        ('a', 'Split into three labelled sections: [TEXT] [GRAPH] [STRUCTURED]', 'step', 0.5, 1),
        ('b', 'Each section gets a third of the budget: 8,000 characters', 'step', 0.44, 2),
        ('c', 'Answer call with the shared prompt', 'llm', 0.42, 3),
        ('out', 'Answer: paper IDs grounded in the context', 'stop', 0.4)], gap=0.18)
    F.note(4.55, 2.9, 'Control and overall winner of RQ2: the cheapest (3,485 input tokens) and fastest (8.4 s) method, with the same answers as all others. It is the fusion step of the final system.', w=2.5, fs=7.4)
    return F.save('m_cf_b1')


def cf_01():
    F = Flow(7.2, 6.9)
    cx, w = 2.3, 3.4
    F.box('in', cx, 6.7, w, 0.38, 'Frozen evidence bundle', 'io')
    F.box('d1', cx, 5.95, 2.5, 0.72, 'Explicit entity ID on the item?', 'decision', n=1)
    F.box('d2', cx, 5.0, 2.5, 0.78, 'Exactly one exact normalised alias match?', 'decision', n=2)
    F.box('d3', cx, 3.98, 2.5, 0.86, 'Registry lookup: exactly one candidate of the item\u2019s entity type?', 'decision', n=3)
    F.box('un', cx, 3.08, w, 0.4, 'UNALIGNED group (keyed by the evidence ID)', 'step')
    F.box('al', 5.6, 4.98, 1.9, 0.46, 'Attach the item to that entity', 'step')
    F.box('g', cx, 2.32, w, 0.5, 'Group items by entity; keep retriever order inside a group', 'step', n=4)
    F.box('o', cx, 1.62, w, 0.5, 'Order groups: best relevance \u2193, sources covered \u2193, entity ID \u2191', 'step', n=5)
    F.box('wr', cx, 0.95, w, 0.46, 'Write [ENTITY] [TEXT] [GRAPH] [STRUCTURED] [PROVENANCE] per group; whole groups until the budget is full', 'step', n=6)
    F.box('out', cx, 0.3, w, 0.36, 'Answer call (shared prompt) \u2192 answer', 'llm')
    F.edge('in', 'd1')
    F.edge('d1', 'd2', label='no')
    F.edge('d2', 'd3', label='no')
    F.edge('d3', 'un', label='no')
    for k in ('d1', 'd2', 'd3'):
        F.edge(k, 'al', 'right', 'left', via='hvh', label='yes' if k == 'd1' else None, lpos=0.2, ldy=0.1)
    F.edge('un', 'g')
    F.path([F.anchor('al', 'bottom'), (5.6, 2.32), F.anchor('g', 'right')])
    F.edge('g', 'o')
    F.edge('o', 'wr')
    F.edge('wr', 'out')
    F.note(4.3, 1.95, 'Adapted from KAG (mutual indexing; only the alignment principle is used). No model invents entities. In RQ2 every item resolved by explicit ID; the registry step was used 0 times and no group was truncated. If nothing resolves, the CF-B1 layout is used.', w=2.8, fs=7.2)
    return F.save('m_cf_01')


def cf_02():
    F = Flow(7.2, 7.4)
    cx, w = 2.35, 3.5
    F.box('in', cx, 7.2, w, 0.38, 'Frozen evidence bundle', 'io')
    F.box('a', cx, 6.55, w, 0.55, 'Structural candidates = graph + structured items; semantic = text items; remove duplicates', 'step', n=1)
    F.box('b', cx, 5.8, w, 0.6, 'Compact manifest: one line per structural item (ID | source | score | first 200 characters | provenance), ≤ 5,000 tokens', 'step', n=2)
    F.box('c', cx, 5.05, w, 0.5, 'Selector call: choose up to 5 items that answer the question together', 'llm', n=3)
    F.box('d', cx, 4.2, 2.6, 0.78, 'Valid JSON with known IDs?', 'decision', n=4)
    F.box('r', 5.65, 4.2, 1.95, 0.5, 'One schema-repair call', 'llm')
    F.box('d2', 5.65, 3.3, 1.7, 0.68, 'Valid now?', 'decision')
    F.box('fb', 5.65, 2.45, 1.95, 0.5, 'Fallback: top 5 by relevance score (flagged)', 'fail')
    F.box('k', cx, 3.3, w, 0.46, 'Keep ≤ 5 structural items (invalid or duplicate IDs dropped)', 'step', n=5)
    F.box('f', cx, 2.6, w, 0.46, 'Fill with text items in retrieved order up to 10 items', 'step', n=6)
    F.box('t', cx, 1.9, w, 0.5, 'Trim to the budget: lowest text fill first, then lowest-priority structural', 'step', n=7)
    F.box('ans', cx, 1.18, w, 0.4, 'Answer call (shared prompt)', 'llm', n=8)
    F.box('out', cx, 0.5, w, 0.38, 'Answer', 'stop')
    for a, b in (('in', 'a'), ('a', 'b'), ('b', 'c'), ('c', 'd'), ('k', 'f'), ('f', 't'), ('t', 'ans'), ('ans', 'out')):
        F.edge(a, b)
    F.edge('d', 'k', label='yes')
    F.edge('d', 'r', 'right', 'left', label='no', lpos=0.3, ldy=0.1)
    F.edge('r', 'd2')
    F.edge('d2', 'k', 'left', 'right', label='yes', lpos=0.5, ldy=0.1)
    F.edge('d2', 'fb', label='no')
    F.path([F.anchor('fb', 'left'), (4.3, 2.45), (4.3, 2.6), F.anchor('f', 'right')], head=True)
    F.note(4.68, 1.7, 'Adapted from SAG. Two model calls. In RQ2 the selector kept 0.58 structural items per bundle on average, with no fallbacks and no invalid IDs.', w=2.4, fs=7.2)
    return F.save('m_cf_02')


def cf_03():
    F = Flow(7.2, 5.6)
    F.box('in', 3.6, 5.35, 3.6, 0.4, 'Frozen evidence bundle', 'io')
    for i, (k, lab, kind) in enumerate((('t', 'Text', 'text'), ('g', 'Graph', 'graph'), ('s', 'Structured', 'structured'))):
        x = 1.25 + i * 2.35
        F.box('r' + k, x, 4.45, 2.1, 0.72, '%s reasoning call\nsees only %s evidence; skipped if the source is empty (static NO_EVIDENCE)' % (lab, lab.lower()), 'llm', bold_first=True)
        F.box('v' + k, x, 3.28, 2.1, 1.0, 'Finding\n{candidate_answer, supporting_evidence_ids, confidence}; IDs must belong to this source, else ERROR_NO_EVIDENCE', kind, bold_first=True)
        F.edge('in', 'r' + k, via='vhv')
        F.edge('r' + k, 'v' + k)
    F.box('fu', 3.6, 2.15, 4.2, 0.58, 'Fusion call\ncombines the grounded findings; may cite only papers that the findings support', 'llm', bold_first=True)
    for k in ('t', 'g', 's'):
        F.edge('v' + k, 'fu', via='vhv')
    F.box('d', 3.6, 1.18, 2.3, 0.74, 'Fusion call succeeded?', 'decision')
    F.box('re', 6.15, 1.18, 1.6, 0.46, 'Retry once, then error', 'fail')
    F.box('out', 3.6, 0.3, 2.6, 0.38, 'Answer', 'stop')
    F.edge('fu', 'd')
    F.edge('d', 'out', label='yes')
    F.edge('d', 're', 'right', 'left', label='no', lpos=0.3, ldy=0.1)
    F.note(0.12, 1.6, 'Adapted from MegaRAG (late fusion). Up to four model calls: 3.75 per bundle on average in RQ2, 66 grounded findings, 6 no-evidence sources, no fusion retries.', w=2.0, fs=7.2)
    return F.save('m_cf_03')


def ar_b0():
    F = Flow(7.2, 3.1)
    F.box('q', 0.65, 2.3, 1.0, 0.5, 'Question', 'io')
    F.box('t', 2.05, 2.3, 1.15, 0.5, 'Text · B1', 'text', n=1)
    F.box('g', 3.42, 2.3, 1.15, 0.5, 'Graph · B2', 'graph', n=2)
    F.box('s', 4.79, 2.3, 1.15, 0.5, 'Structured · B3', 'structured', n=3)
    F.box('c', 3.42, 1.2, 4.0, 0.5, 'Fixed context: [TEXT] [GRAPH] [STRUCTURED], 8,000 characters per source', 'step', n=4)
    F.box('a', 3.42, 0.38, 2.6, 0.42, 'Answer call (shared prompt) → answer', 'llm', n=5)
    F.edge('q', 't', 'right', 'left')
    F.edge('t', 'g', 'right', 'left')
    F.edge('g', 's', 'right', 'left')
    F.edge('s', 'c', 'bottom', 'top', via='vhv')
    F.edge('c', 'a')
    F.note(5.55, 2.6, 'Control: always all three sources, raw question, fixed order, then stop.', w=1.6, fs=7.3)
    return F.save('m_ar_b0')


def ar_b1():
    F = Flow(7.2, 4.9)
    F.box('q', 3.6, 4.62, 2.4, 0.4, 'Question', 'io')
    F.box('n', 3.6, 3.98, 4.2, 0.42, 'Normalise: Unicode NFKC, lowercase, collapse spaces', 'step', n=1)
    cues = (('t', 'Text cues?', 'abstract, title, text, content, phrase, wording, mention(s/ed), contain(s/ing)', 'text'),
            ('g', 'Graph cues?', 'author(s/ed), written by, writes, affiliat…, institution, university, cites, cited by, references, topic, field of study', 'graph'),
            ('s', 'Structured cues?', 'year, date, rank, citation count, N citations, journal, conference, venue, document type, before/after/between, at least/most, more/less than, >=, <=', 'structured'))
    for i, (k, h, t, kind) in enumerate(cues):
        x = 1.25 + i * 2.35
        F.box(k, x, 2.95, 2.15, 1.15, h + '\n' + t, kind, bold_first=True, fs=7.5)
        F.edge('n', k, via='vhv')
    F.box('r', 3.6, 1.72, 5.6, 0.5, 'Routed sources = every matched source, in the fixed order Text → Graph → Structured; none matched → Text only', 'step', n=2)
    for k in ('t', 'g', 's'):
        F.edge(k, 'r', via='vhv')
    F.box('x', 3.6, 1.02, 4.2, 0.42, 'Query each routed source once, then stop; fixed context', 'step', n=3)
    F.box('a', 3.6, 0.36, 3.0, 0.4, 'Answer call (shared prompt) → answer', 'llm', n=4)
    F.edge('q', 'n')
    F.edge('r', 'x')
    F.edge('x', 'a')
    return F.save('m_ar_b1')


def ar_01():
    F = Flow(7.2, 7.1)
    F.box('q', 2.2, 6.85, 2.2, 0.36, 'Question', 'io')
    F.box('c', 2.2, 6.25, 3.2, 0.5, 't5-base classifier predicts a route: A, B or C', 'model', n=1)
    F.box('d', 2.2, 5.35, 2.4, 0.82, 'Route?', 'decision', n=2)
    F.box('A', 0.75, 4.3, 1.35, 0.62, 'A \u00b7 no retrieval; answer from the question only', 'step')
    F.box('B', 2.2, 4.3, 1.35, 0.62, 'B \u00b7 query the router\u2019s first source once', 'step')
    F.box('C1', 4.9, 4.4, 2.3, 0.56, 'C \u00b7 query the first unqueried routed source (call k \u2264 3)', 'step', n=3)
    F.box('dk', 4.9, 3.45, 1.9, 0.72, 'k = 3?', 'decision', n=4)
    F.box('ctl', 4.9, 2.5, 2.3, 0.62, 'Controller call: {sufficient, next_subquery, reason}', 'llm', n=5)
    F.box('ds', 4.9, 1.55, 1.9, 0.72, 'Sufficient?', 'decision', n=6)
    F.box('nx', 6.62, 3.0, 1.1, 1.25, 'Route the sub-query; take its first unqueried source (else next in T \u2192 G \u2192 S)', 'step', fs=7.0, n=7)
    F.box('ans', 2.2, 0.5, 3.4, 0.46, 'Fixed context \u2192 answer call (shared prompt) \u2192 answer', 'llm')
    F.edge('q', 'c')
    F.edge('c', 'd')
    F.edge('d', 'A', 'left', 'top', via='hv', label='A', lpos=0.5, ldy=0.1)
    F.edge('d', 'B', label='B')
    F.edge('d', 'C1', 'right', 'top', via='hv', label='C', lpos=0.5, ldy=0.1)
    F.edge('C1', 'dk')
    F.edge('dk', 'ctl', label='no')
    F.edge('ctl', 'ds')
    F.path([F.anchor('ds', 'right'), (6.62, 1.55), F.anchor('nx', 'bottom')], label='no', label_at=0, lpos=0.4, ldy=0.1)
    F.path([F.anchor('nx', 'top'), (6.62, 4.4), F.anchor('C1', 'right')])
    F.edge('A', 'ans', 'bottom', 'top', via='vhv')
    F.edge('B', 'ans')
    F.path([F.anchor('ds', 'bottom'), (4.9, 0.5), F.anchor('ans', 'right')], label='yes', label_at=0, lpos=0.5)
    F.path([F.anchor('dk', 'left'), (3.55, 3.45), (3.55, 0.73)], label='yes', label_at=0, lpos=0.4, ldy=0.1)
    F.note(4.1, 7.0, 'Invalid classifier output \u2192 route B. If the controller output is still invalid after one schema repair, retrieval stops and the answer uses the evidence gathered so far. Labels come from a retrieval-only oracle on training questions (train 7,302 / dev 747); best epoch 7 by development loss.', w=3.0, fs=7.1)
    return F.save('m_ar_01')


def ar_02():
    F = Flow(7.2, 6.3)
    cx = 2.3
    F.box('q', cx, 6.05, 2.4, 0.36, 'Question', 'io')
    F.box('a', cx, 5.45, 3.2, 0.46, 'Query the router\u2019s first source', 'step', n=1)
    F.box('s', cx, 4.72, 3.2, 0.62, 'Score every evidence item with the cross-encoder (ms-marco-MiniLM-L-6-v2) \u2192 calibrated p (Platt)', 'model', n=2)
    F.box('d', cx, 3.6, 3.1, 1.08, 'State: GOOD if max p \u2265 0.75; BAD if every p \u2264 0.40 (or no evidence); else AMBIGUOUS', 'decision', n=3)
    F.box('co', 5.65, 3.6, 2.3, 0.86, 'Correction round\nAMBIGUOUS: add the highest-priority unqueried source \u00b7 BAD: add all remaining sources (T \u2192 G \u2192 S)', 'step', n=4)
    F.box('dr', 5.65, 2.3, 2.2, 0.86, 'Fewer than 2 correction rounds done and a source was added?', 'decision', n=5)
    F.box('ans', cx, 0.9, 3.2, 0.5, 'Fixed context \u2192 answer call (shared prompt) \u2192 answer', 'llm', n=6)
    F.edge('q', 'a')
    F.edge('a', 's')
    F.edge('s', 'd')
    F.edge('d', 'co', 'right', 'left', label='AMBIGUOUS or BAD', lpos=0.05, ldy=0.13)
    F.edge('co', 'dr')
    F.edge('d', 'ans', label='GOOD')
    F.path([F.anchor('dr', 'right'), (7.08, 2.3), (7.08, 4.72), F.anchor('s', 'right')], label='yes: re-evaluate', label_at=2, lpos=0.4, ldy=0.12)
    F.path([F.anchor('dr', 'bottom'), (5.65, 0.9), F.anchor('ans', 'right')], label='no', label_at=0, lpos=0.5)
    F.note(0.12, 2.75, 'An evaluator failure counts as AMBIGUOUS. If the state is still BAD with no source left, the answer is generated anyway (status insufficient_evidence). Calibration and thresholds were fitted only on the development partition (745 questions).', w=2.05, fs=7.0)
    return F.save('m_ar_02')


def ar_03():
    F = Flow(7.4, 8.2)
    cx, w = 2.45, 3.2
    F.box('q', cx, 7.95, 2.4, 0.36, 'Question', 'io')
    F.box('it', cx, 7.38, w, 0.42, 'Iteration i (at most 4)', 'step', n=1)
    F.box('ag', cx, 6.68, w, 0.66, 'Agent call: AgentAction {source: text | graph | structured | stop, retrieval_query, entities, relations, structured_intent, reason}', 'llm', n=2)
    F.box('dv', cx, 5.75, 2.2, 0.72, 'Valid JSON?', 'decision', n=3)
    F.box('rp', 5.3, 5.75, 1.8, 0.7, 'One repair call; if still invalid the router picks the source and the iteration counts', 'llm', fs=7.0)
    F.box('ds', cx, 4.8, 2.2, 0.72, 'source = stop?', 'decision', n=4)
    F.box('st', 5.3, 4.8, 1.8, 0.5, 'Generate from memory \u2192 answer', 'llm', fs=7.2)
    F.box('tool', cx, 3.95, w, 0.48, 'Run exactly one tool; add new evidence to memory', 'step', n=5)
    F.box('gen', cx, 3.28, w, 0.46, 'Generator call: candidate answer from the memory', 'llm', n=6)
    F.box('val', cx, 2.6, w, 0.5, 'Validator call: {accept, error_type, unsupported_claims}; never sees gold', 'llm', n=7)
    F.box('da', cx, 1.72, 2.1, 0.72, 'Accepted?', 'decision', n=8)
    F.box('di', 4.85, 1.72, 1.45, 0.7, 'i = 4?', 'decision', n=9)
    F.box('cm', 6.45, 1.72, 1.45, 0.92, 'Commentor call: feedback for the next action (sees query, action, verdict only)', 'llm', fs=6.8, n=10)
    F.box('ok', cx, 0.62, 2.6, 0.46, 'Answer = the accepted candidate', 'stop')
    F.box('ins', 4.85, 0.62, 1.75, 0.5, 'INSUFFICIENT_EVIDENCE (empty answer)', 'fail', fs=7.0)
    F.edge('q', 'it')
    F.edge('it', 'ag')
    F.edge('ag', 'dv')
    F.edge('dv', 'ds', label='yes')
    F.edge('dv', 'rp', 'right', 'left', label='no', lpos=0.3, ldy=0.1)
    F.path([F.anchor('rp', 'bottom'), (5.3, 5.28), (cx + 0.08, 5.28)])
    F.edge('ds', 'st', 'right', 'left', label='yes', lpos=0.3, ldy=0.1)
    F.edge('ds', 'tool', label='no')
    F.edge('tool', 'gen')
    F.edge('gen', 'val')
    F.edge('val', 'da')
    F.edge('da', 'ok', label='yes')
    F.edge('da', 'di', 'right', 'left', label='no', lpos=0.3, ldy=0.1)
    F.edge('di', 'ins', label='yes')
    F.edge('di', 'cm', 'right', 'left', label='no', lpos=0.3, ldy=0.1)
    F.path([F.anchor('cm', 'top'), (6.45, 7.38), F.anchor('it', 'right')], label='next iteration', label_at=1, lpos=0.4, ldy=0.12)
    F.note(4.32, 4.25, 'Loop guard: the same normalised action twice without new evidence forces fixed feedback; a third time ends with INSUFFICIENT_EVIDENCE. Adapted from AGENT-G (agent, validator and commentor roles). In RQ3: 6.54 model calls per question and the lowest wasted retrieval (0.012).', w=1.95, fs=6.9)
    return F.save('m_ar_03')


def int_1():
    F = Flow(7.2, 3.4)
    xs = [0.55, 1.75, 3.05, 4.35, 5.6, 6.65]
    boxes = [('q', 'Question', 'io', None), ('ar', 'AR-B1 rule router\nqueries the routed sources once', 'rq', 'Part 3 winner'),
             ('mem', 'Evidence memory\ntext, graph and structured items', 'data', None), ('cm', 'CM-B1 on graph items\n5 best papers and their paths', 'rq', 'Part 1 winner'),
             ('cf', 'CF-B1 fusion\nthree labelled sections', 'rq', 'Part 2 winner'), ('a', 'Answer call\nshared prompt → paper IDs', 'llm', None)]
    for x, (k, t, kind, tag) in zip(xs, boxes):
        F.box(k, x, 1.95, 1.08 if k != 'q' else 0.85, 1.0, t, kind, bold_first='\n' in t)
        if tag:
            F.ax.text(x, 2.6, tag, ha='center', va='bottom', fontsize=7.4, color='white', fontweight='bold',
                      bbox=dict(boxstyle='round,pad=0.2', facecolor='#1d4ed8', edgecolor='none'))
    for a, b in zip(boxes, boxes[1:]):
        F.edge(a[0], b[0], 'right', 'left')
    F.note(0.1, 0.95, 'Text and structured items pass through CM-B1 unchanged. The final answer comes from the fusion step and replaces the policy’s own answer. Under the frozen top-5 graph retriever, CM-B1 removed no graph evidence for this single-graph-call policy.', w=6.9, fs=7.4)
    return F.save('m_int_1')


# ======================================================================= showcase app diagrams
def app_map():
    F = Flow(7.2, 3.7, fs=7.6)
    secs = [('The problem', ['The problem', 'Four parts', 'Data and benchmark', 'Metrics and statistics'], 'io'),
            ('The studies', ['Part 1 · Context management', 'Part 2 · Fusion', 'Part 3 · Retrieval control', 'Part 4 · Combined system'], 'rq'),
            ('Takeaways', ['Conclusions'], 'stop'), ('Explore', ['Try a question', 'Reproducibility'], 'data')]
    xs = [0.95, 2.75, 4.55, 6.3]
    prev = None
    for x, (title, pages, kind) in zip(xs, secs):
        F.box('S' + title, x, 1.95, 1.7, 3.3, title, 'group', fs=7.8)
        for i, p in enumerate(pages):
            k = '%s%d' % (title, i)
            F.box(k, x, 3.15 - i * 0.72, 1.5, 0.5, p, kind, n=None)
            if i:
                F.edge('%s%d' % (title, i - 1), k)
        if prev:
            F.edge(prev, '%s0' % title, 'right', 'left', via='hvh')
        prev = '%s%d' % (title, len(pages) - 1)
    F.note(0.12, 0.16, 'Reading order: the problem → its four parts → the evidence for each part → the verdict → hands-on exploration and proof of reproducibility.', fs=7.2)
    return F.save('a_map')


def app_bundle():
    F = Flow(7.2, 5.5, fs=7.6)
    F.box('src', 1.35, 4.7, 2.5, 1.35, 'Frozen study outputs\nanalysis files of the 4 studies; run records; stored model requests; benchmark records; paper titles; overall ranking', 'data', bold_first=True)
    F.box('b', 1.35, 3.25, 2.5, 0.72, 'build_showcase_bundle.py\ndeterministic export (gzip mtime 0, sorted keys)', 'step', bold_first=True, n=1)
    F.box('files', 4.35, 3.25, 2.8, 1.25, 'Bundle files\nresults.json, queries.json, papers.json, foundation.json, stats_demo.json, explorer_rq1–4.json.gz', 'data', bold_first=True)
    F.box('man', 4.35, 4.75, 2.8, 0.85, 'manifest.json\nSHA-256 of every file + bundle_sha256 over the name:hash lines', 'data', bold_first=True)
    F.box('chk', 1.35, 1.95, 2.5, 0.72, '--check\nrebuild and compare byte for byte → IDENTICAL', 'step', bold_first=True, n=2)
    F.box('v', 4.35, 1.85, 2.2, 0.86, 'App start: do all checksums match?', 'decision', n=3)
    F.box('x', 6.55, 2.6, 1.15, 0.7, 'Withhold content and show an error', 'fail', fs=7.0)
    F.box('pg', 4.35, 0.55, 2.8, 0.66, 'Pages read only the bundle; text from content.yaml with {placeholders} bound to bundle keys', 'stop', n=4)
    F.box('ct', 1.35, 0.55, 2.5, 0.66, 'content.yaml → content.py (resolve keys) → fmt.py (formats)', 'step', n=5)
    F.edge('src', 'b')
    F.edge('b', 'files', 'right', 'left')
    F.edge('files', 'man', 'top', 'bottom', label='described by', lpos=0.5)
    F.edge('b', 'chk')
    F.edge('files', 'v')
    F.edge('v', 'pg', label='yes')
    F.edge('v', 'x', 'right', 'bottom', via='hv', label='no', lpos=0.4, ldy=0.1)
    F.edge('ct', 'pg', 'right', 'left')
    return F.save('a_bundle')


def app_profiles():
    F = Flow(7.2, 4.1, fs=7.6)
    F.box('L', 1.8, 2.15, 3.4, 3.7, 'Profile “showcase” (default; Docker)', 'group', fs=8)
    F.box('R', 5.4, 2.15, 3.4, 3.7, 'Profile “full” (adds live runs)', 'group', fs=8)
    column(F, 1.8, 3.55, 3.0, [
        ('l1', 'All 11 pages from the checksummed bundle', 'stop', 0.42),
        ('l2', 'Try a question: replay any of 6 recorded pipelines on any benchmark question of Parts 3–4', 'step', 0.62),
        ('l3', 'No research data, no model server, no network needed', 'io', 0.5),
        ('l4', 'python showcase/launch.py', 'data', 0.38)], gap=0.18)
    column(F, 5.4, 3.55, 3.0, [
        ('r1', 'Everything in “showcase”, plus a live run builder', 'stop', 0.42),
        ('r2', 'LiveEngine → research IntegratedSystem: any AR policy × any CF method, CM-B1 fixed', 'step', 0.62),
        ('r3', 'Retrievers over the MMG-STaRK-MAG data; local model server (gpt-oss:20b)', 'llm', 0.6),
        ('r4', 'Stored responses reused; readiness checks; limit of 8 live runs per session', 'data', 0.55)], gap=0.18)
    return F.save('a_profiles')


def app_answer_tree():
    F = Flow(7.2, 4.6, fs=7.6)
    F.box('d0', 2.0, 4.15, 2.4, 0.72, 'Did the strategy return any paper?', 'decision', n=1)
    F.box('y0', 5.55, 4.15, 2.9, 0.62, 'List each paper with ✔ / ✘; e.g. “exactly the correct answer” or “14 correct; the full answer has 78”', 'stop', fs=7.2)
    F.box('d1', 2.0, 3.1, 2.4, 0.72, 'Is the correct answer empty?', 'decision', n=2)
    F.box('y1', 5.55, 3.1, 2.9, 0.46, '✔ Correct: no paper satisfies this question', 'stop')
    F.box('d2', 2.0, 2.05, 2.4, 0.78, 'Did the retrievers return a correct paper? (gold_retrieved)', 'decision', n=3)
    F.box('y2', 5.55, 2.05, 2.9, 0.5, 'The retrievers did not return the correct paper, so the model never saw it', 'fail', fs=7.2)
    F.box('d3', 2.0, 0.95, 2.4, 0.78, 'Did it reach the model’s context? (gold_seen)', 'decision', n=4)
    F.box('y3', 5.55, 1.15, 2.9, 0.42, 'Found, but this strategy left it out of the context', 'fail', fs=7.2)
    F.box('y4', 5.55, 0.42, 2.9, 0.48, 'Reached the model, but it judged that no paper met every condition', 'fail', fs=7.2)
    F.edge('d0', 'y0', 'right', 'left', label='yes', lpos=0.3, ldy=0.1)
    F.edge('d0', 'd1', label='no')
    F.edge('d1', 'y1', 'right', 'left', label='yes', lpos=0.3, ldy=0.1)
    F.edge('d1', 'd2', label='no')
    F.edge('d2', 'y2', 'right', 'left', label='no', lpos=0.3, ldy=0.1)
    F.edge('d2', 'd3', label='yes')
    F.edge('d3', 'y3', 'right', 'left', via='hvh', label='no', lpos=0.2, ldy=0.1)
    F.edge('d3', 'y4', 'right', 'left', via='hvh', label='yes', lpos=0.2, ldy=-0.1)
    return F.save('a_answer_tree')


if __name__ == '__main__':
    for f in (pipeline, architecture, timeline, data_build, benchmark_flow, execution, statistics_flow, ranking_flow,
              cm_b0, cm_b1, cm_01, cm_02, cm_03, cf_b0, cf_b1, cf_01, cf_02, cf_03, ar_b0, ar_b1, ar_01, ar_02, ar_03, int_1,
              app_map, app_bundle, app_profiles, app_answer_tree):
        f()
    print('diagrams written to', OUT)
