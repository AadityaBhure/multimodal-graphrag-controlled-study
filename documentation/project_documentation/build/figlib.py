"""Shared style, data loading and drawing helpers for the documentation figures (charts and flow diagrams)."""
import json
import textwrap
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon, FancyArrowPatch, Circle

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / 'figures'
OUT.mkdir(parents=True, exist_ok=True)

# Colours: the showcase app's own palette, so charts match the screenshots (validated: the three method hues and the three
# source hues each pass the categorical colour checks; controls are deliberately grey).
INK, BODY, MUTED, FAINT = '#0f172a', '#1e293b', '#475569', '#64748b'
GRID, AXIS, SURF = '#e5e7eb', '#cbd5e1', '#ffffff'
METHOD_COLOR = {'B0': '#94a3b8', 'B1': '#334155', '01': '#2563eb', '02': '#16a34a', '03': '#c026d3', 'INT-1': '#7c3aed'}
SOURCE_COLOR = {'text': '#4f46e5', 'graph': '#0d9488', 'structured': '#ea580c'}
STATUS = {'good': '#0ca30c', 'warning': '#fab219', 'critical': '#d03b3b'}
BLUE_RAMP = ['#f8fbff', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']

plt.rcParams.update({
    'font.family': 'Segoe UI', 'font.size': 9.5, 'axes.titlesize': 10.5, 'axes.titleweight': 'semibold', 'axes.titlelocation': 'left',
    'axes.titlecolor': INK, 'axes.labelcolor': MUTED, 'axes.edgecolor': AXIS, 'axes.linewidth': 0.8, 'xtick.color': MUTED,
    'ytick.color': BODY, 'xtick.labelsize': 8.5, 'ytick.labelsize': 9, 'axes.labelsize': 9, 'legend.fontsize': 8.5,
    'legend.frameon': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'grid.color': GRID,
    'grid.linewidth': 0.8, 'axes.grid': False, 'svg.fonttype': 'none', 'pdf.fonttype': 42,
})


def mcolor(m):
    return METHOD_COLOR.get(m if m == 'INT-1' else m.split('-')[-1], '#64748b')


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


RES = load('showcase/bundle/results.json')
FOUND = load('showcase/bundle/foundation.json')
DEMO = load('showcase/bundle/stats_demo.json')


# ------------------------------------------------------------------ number formatting (same rules as the app)
def _round(x, nd):
    q = Decimal(1).scaleb(-nd)
    v = Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)
    return v + 0  # no negative zero


def fnum(x, nd=3, sign=False):
    if x is None:
        return 'n/a'
    v = _round(x, nd)
    s = format(v, ',.%df' % nd).replace('-', '−')
    if s in ('−0', '−0.' + '0' * nd):
        s = s[1:]
    if sign and v > 0:
        s = '+' + s
    return s


def fmt(x, kind='rate', sign=False):
    if x is None:
        return 'n/a'
    if kind == 'rate':
        return fnum(x, 3, sign)
    if kind == 'tokens':
        return fnum(x, 0, sign)
    if kind == 'ms':                      # shown in seconds
        return fnum(x / 1000., 1, sign) + ' s'
    if kind == 'p':
        return fnum(x, 3)
    if kind == 'calls':
        return fnum(x, 2, sign)
    if kind == 'count':
        return fnum(x, 0, sign)
    return str(x)


KIND = {'answer_f1': 'rate', 'answer_em': 'rate', 'answerable_f1': 'rate', 'mrr': 'rate', 'gold_coverage': 'rate', 'recall_at_5': 'rate',
        'source_f1': 'rate', 'unnecessary_retrieval': 'rate', 'stopping_accuracy': 'rate', 'required_source_miss': 'rate',
        'input_tokens': 'tokens', 'output_tokens': 'tokens', 'total_tokens': 'tokens', 'context_tokens': 'tokens',
        'latency': 'ms', 'llm_calls': 'calls', 'retrieval_calls': 'calls'}
LABEL = {'answer_f1': 'Answer F1', 'answer_em': 'Exact match', 'answerable_f1': 'Answer F1 (answerable only)', 'mrr': 'MRR',
         'gold_coverage': 'Gold coverage', 'recall_at_5': 'Recall@5', 'source_f1': 'Source-selection F1', 'unnecessary_retrieval': 'Wasted retrieval',
         'stopping_accuracy': 'Stopping accuracy', 'required_source_miss': 'Required-source miss', 'input_tokens': 'Input tokens',
         'output_tokens': 'Output tokens', 'total_tokens': 'Total tokens', 'context_tokens': 'Context tokens', 'latency': 'Latency (s)',
         'llm_calls': 'Model calls', 'retrieval_calls': 'Retrieval calls'}
HIGHER = {'answer_f1', 'answer_em', 'answerable_f1', 'mrr', 'gold_coverage', 'recall_at_5', 'source_f1', 'stopping_accuracy'}


def scale(metric):
    return 1 / 1000. if KIND.get(metric) == 'ms' else 1.


def save(fig, name):
    path = OUT / (name + '.png')
    fig.savefig(path, dpi=200, bbox_inches='tight', pad_inches=0.12, metadata={'Software': None})
    plt.close(fig)
    return path


def tidy(ax, xgrid=True, ygrid=False):
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.spines['left'].set_color(AXIS)
    ax.spines['bottom'].set_color(AXIS)
    ax.tick_params(length=0)
    if xgrid:
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def hbar(ax, y, value, color, height=0.56, left=0.0):
    """A horizontal bar with a rounded data end and a square baseline."""
    if value == 0:
        ax.add_patch(Rectangle((left, y - height / 2), 0, height, color=color))
        return
    w = value
    ax.add_patch(Rectangle((left, y - height / 2), w, height, facecolor=color, edgecolor='none', linewidth=0))


def bars(ax, methods, values, colors, labels=None, ci=None, xlabel=None, title=None, xmax=None, star=(), fmtk='rate', note=None):
    """Horizontal bars, one per method, value labels at the tip, optional 95 % CI whiskers."""
    ys = list(range(len(methods)))[::-1]
    vmax = max([v for v in values if v is not None] + [hi for lo, hi in (ci or []) if hi is not None] + [1e-9])
    xmax = xmax or vmax * 1.42
    for i, (y, m, v, c) in enumerate(zip(ys, methods, values, colors)):
        if v is None:
            ax.text(0, y, '  not measured', va='center', ha='left', fontsize=8.5, color=FAINT)
            continue
        hbar(ax, y, v, c)
        tip = v
        if ci and ci[i] and ci[i][0] is not None:
            lo, hi = ci[i]
            ax.plot([lo, hi], [y, y], color=INK, linewidth=1.2, solid_capstyle='butt', zorder=3)
            ax.plot([lo, lo], [y - .13, y + .13], color=INK, linewidth=1.2, zorder=3)
            ax.plot([hi, hi], [y - .13, y + .13], color=INK, linewidth=1.2, zorder=3)
            tip = max(v, hi)
        ax.text(tip + xmax * 0.025, y, (labels[i] if labels else fmt(v, fmtk)), va='center', ha='left', fontsize=8.2, color=BODY)
    ax.set_yticks(ys)
    ax.set_yticklabels([m + (' ★' if m in star else '') for m in methods])
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.6, len(methods) - 0.4)
    if xlabel:
        ax.set_xlabel(xlabel)
    if title:
        ax.set_title(title, pad=6)
    tidy(ax)
    if note:
        ax.text(0, -1.25, note, transform=ax.get_yaxis_transform(), fontsize=7.5, color=FAINT, va='top')


def heatmap(ax, rows, cols, values, fmtfn=lambda v: fnum(v, 3), vmin=None, vmax=None, highlight=None, ramp=BLUE_RAMP, xlabels=None,
            ylabels=None, empty='–'):
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list('ramp', ramp)
    arr = np.array([[np.nan if values[i][j] is None else values[i][j] for j in range(len(cols))] for i in range(len(rows))], dtype=float)
    vmin = np.nanmin(arr) if vmin is None else vmin
    vmax = np.nanmax(arr) if vmax is None else vmax
    rng = (vmax - vmin) or 1.
    for i in range(len(rows)):
        for j in range(len(cols)):
            v = arr[i, j]
            if np.isnan(v):
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor='#f8fafc', edgecolor=SURF, linewidth=2))
                ax.text(j + .5, i + .5, empty, ha='center', va='center', fontsize=8.5, color=FAINT)
                continue
            t = (v - vmin) / rng
            fc = cmap(t)
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=fc, edgecolor=SURF, linewidth=2))
            lum = 0.2126 * fc[0] + 0.7152 * fc[1] + 0.0722 * fc[2]
            ax.text(j + .5, i + .5, fmtfn(v), ha='center', va='center', fontsize=8.5, color='white' if lum < 0.5 else INK)
    if highlight:
        for (i, j) in highlight:
            ax.add_patch(Rectangle((j + .04, i + .04), .92, .92, fill=False, edgecolor='#f59e0b', linewidth=2.2))
    ax.set_xlim(0, len(cols))
    ax.set_ylim(len(rows), 0)
    ax.set_xticks([j + .5 for j in range(len(cols))])
    ax.set_xticklabels(xlabels or cols)
    ax.set_yticks([i + .5 for i in range(len(rows))])
    ax.set_yticklabels(ylabels or rows)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.xaxis.set_ticks_position('top')


# ------------------------------------------------------------------ flow diagrams
KINDS = {  # face, edge, text colour, legend label
    'io': ('#f1f5f9', '#64748b', INK, 'Input / output'),
    'step': ('#ffffff', '#334155', INK, 'Deterministic step'),
    'llm': ('#f5f3ff', '#7c3aed', INK, 'Language-model call'),
    'model': ('#eff6ff', '#2563eb', INK, 'Small learned model (no LLM)'),
    'decision': ('#fffbeb', '#d97706', INK, 'Decision'),
    'stop': ('#ecfdf5', '#16a34a', INK, 'Stop / result'),
    'fail': ('#fef2f2', '#dc2626', INK, 'Failure path'),
    'text': ('#eef2ff', SOURCE_COLOR['text'], INK, 'Text source'),
    'graph': ('#f0fdfa', SOURCE_COLOR['graph'], INK, 'Graph source'),
    'structured': ('#fff7ed', SOURCE_COLOR['structured'], INK, 'Structured source'),
    'rq': ('#eff6ff', '#1d4ed8', INK, 'Studied component'),
    'fixed': ('#f8fafc', '#94a3b8', INK, 'Fixed component'),
    'data': ('#f8fafc', '#475569', INK, 'Data / artefact'),
    'group': ('#fbfdff', '#cbd5e1', INK, ''),
}


class Flow:
    """Hand-placed flow diagram in inches: box(key, cx, cy, w, h, text, kind), edge(a, b, ...), path(points)."""

    def __init__(self, w, h, title=None, fs=8.6):
        self.fig = plt.figure(figsize=(w, h))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(0, h)
        self.ax.axis('off')
        self.w, self.h, self.fs = w, h, fs
        self.n = {}
        self.used = []
        if title:
            self.ax.text(0.12, h - 0.18, title, fontsize=10.5, fontweight='semibold', color=INK, va='top', ha='left')

    def _wrap(self, text, w, fs):
        per_inch = 72. / (fs * 0.53)
        width = max(6, int((w - 0.16) * per_inch))
        out = []
        for para in text.split('\n'):
            out.extend(textwrap.wrap(para, width=width, break_long_words=False, break_on_hyphens=False) or [''])
        return '\n'.join(out)

    def box(self, key, cx, cy, w, h, text, kind='step', fs=None, bold_first=False, n=None, align='center'):
        fs = fs or self.fs
        face, edge, tc, _ = KINDS[kind]
        if kind not in self.used and kind != 'group':
            self.used.append(kind)
        x, y = cx - w / 2, cy - h / 2
        if kind == 'decision':
            self.ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)], closed=True, facecolor=face,
                                      edgecolor=edge, linewidth=1.2, zorder=2))
            wrapped = self._wrap(text, w * 0.62, fs)
        else:
            r = 0.06 if kind != 'io' else 0.16
            ls = (0, (4, 2)) if kind == 'group' else 'solid'
            self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=%s' % r, facecolor=face, edgecolor=edge,
                                             linewidth=1.2 if kind != 'group' else 1.0, linestyle=ls, zorder=1 if kind == 'group' else 2))
            wrapped = self._wrap(text, w, fs)
        if kind == 'group':
            self.ax.text(x + 0.1, y + h - 0.08, text, ha='left', va='top', fontsize=fs, color=MUTED, fontweight='semibold', zorder=2)
        else:
            lines = wrapped.split('\n')
            if bold_first and len(text.split('\n')) > 1:
                head = self._wrap(text.split('\n')[0], w, fs)
                rest = self._wrap('\n'.join(text.split('\n')[1:]), w, fs - 0.6)
                nh, nr = head.count('\n') + 1, rest.count('\n') + 1
                lh = fs / 72. * 1.25
                total = nh * lh + nr * (lh * 0.95)
                top = cy + total / 2
                self.ax.text(cx if align == 'center' else x + 0.1, top, head, ha=align if align != 'left' else 'left', va='top', fontsize=fs,
                             color=tc, fontweight='semibold', zorder=3, linespacing=1.15)
                self.ax.text(cx if align == 'center' else x + 0.1, top - nh * lh, rest, ha=align if align != 'left' else 'left', va='top',
                             fontsize=fs - 0.6, color=MUTED, zorder=3, linespacing=1.12)
            else:
                self.ax.text(cx if align == 'center' else x + 0.1, cy, wrapped, ha=align if align != 'left' else 'left', va='center', fontsize=fs,
                             color=tc, zorder=3, linespacing=1.15)
        if n is not None:
            self.ax.add_patch(Circle((x + 0.02, y + h - 0.02), 0.105, facecolor=edge, edgecolor='white', linewidth=1.0, zorder=4))
            self.ax.text(x + 0.02, y + h - 0.02, str(n), ha='center', va='center', fontsize=6.8, color='white', fontweight='bold', zorder=5)
        self.n[key] = (cx, cy, w, h, kind)
        return key

    def anchor(self, key, side):
        cx, cy, w, h, kind = self.n[key]
        return {'top': (cx, cy + h / 2), 'bottom': (cx, cy - h / 2), 'left': (cx - w / 2, cy), 'right': (cx + w / 2, cy)}[side]

    def path(self, pts, label=None, label_at=None, color='#475569', lw=1.1, dashed=False, head=True, lpos=0.5, ldx=0.06, ldy=0.0, lha='left'):
        ls = (0, (3, 2)) if dashed else 'solid'
        for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
            self.ax.plot([x0, x1], [y0, y1], color=color, linewidth=lw, linestyle=ls, solid_capstyle='butt', zorder=1.5)
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        self.ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>' if head else '-', mutation_scale=9, color=color, linewidth=lw,
                                          linestyle=ls, shrinkA=0, shrinkB=0.5, zorder=1.6))
        if label:
            i = label_at if label_at is not None else max(0, len(pts) - 2)
            (a, b), (c, d) = pts[i], pts[i + 1]
            lx, ly = a + (c - a) * lpos + ldx, b + (d - b) * lpos + ldy
            self.ax.text(lx, ly, label, fontsize=self.fs - 1.2, color=MUTED, ha=lha, va='center', zorder=4,
                         bbox=dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor='none'))

    def edge(self, a, b, sa='bottom', sb='top', via=None, **kw):
        p0, p1 = self.anchor(a, sa), self.anchor(b, sb)
        pts = [p0]
        if via == 'hv':
            pts.append((p1[0], p0[1]))
        elif via == 'vh':
            pts.append((p0[0], p1[1]))
        elif via == 'vhv':
            mid = (p0[1] + p1[1]) / 2
            pts += [(p0[0], mid), (p1[0], mid)]
        elif via == 'hvh':
            mid = (p0[0] + p1[0]) / 2
            pts += [(mid, p0[1]), (mid, p1[1])]
        elif isinstance(via, list):
            pts += via
        pts.append(p1)
        self.path(pts, **kw)

    def note(self, x, y, text, fs=None, color=MUTED, ha='left', va='top', w=None, style='normal'):
        fs = fs or self.fs - 0.8
        t = self._wrap(text, w, fs) if w else text
        self.ax.text(x, y, t, fontsize=fs, color=color, ha=ha, va=va, zorder=4, linespacing=1.2, style=style)

    def legend(self, y=0.16, x=0.12, kinds=None):
        kinds = kinds or [k for k in self.used if k != 'group']
        cx = x
        for k in kinds:
            face, edge, _, label = KINDS[k]
            if k == 'decision':
                self.ax.add_patch(Polygon([(cx + .09, y + .07), (cx + .18, y), (cx + .09, y - .07), (cx, y)], closed=True, facecolor=face, edgecolor=edge, linewidth=1))
            else:
                self.ax.add_patch(FancyBboxPatch((cx, y - .06), .18, .12, boxstyle='round,pad=0,rounding_size=0.02', facecolor=face, edgecolor=edge, linewidth=1))
            self.ax.text(cx + .25, y, label, fontsize=7.4, color=MUTED, va='center')
            cx += .25 + len(label) * 0.055 + .22

    def save(self, name):
        return save(self.fig, name)
