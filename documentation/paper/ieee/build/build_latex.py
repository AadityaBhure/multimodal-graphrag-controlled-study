"""Build the LaTeX (IEEEtran) version of the paper from paper.md, the same source as the Word build.

Writes ../latex/main.tex and ../latex/figures/*.pdf (vector figures from paper_figs.py) and packs both into
../Multi-Modal_GraphRAG_IEEE_overleaf.zip for Overleaf (New Project > Upload Project). Numbers, citations, labels,
captions and tables come from the same source text and frozen results as the Word version; display equations use the
hand-written LaTeX in EQ, and inline math is translated from the UnicodeMath used for Word. The result is checked
statically (labels, citations, braces, environments, characters, figure files); compile it with pdfLaTeX.

Run: python build_latex.py
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_ieee as W          # noqa: E402  parser helpers (blocks, split_row) and number binding (bound)
from refs import REFS           # noqa: E402

BD = W.BD
SRC = HERE / 'paper.md'
OUT = HERE.parent / 'latex'
FIGS = HERE.parent / 'figures'
ZIP = HERE.parent / 'Multi-Modal_GraphRAG_IEEE_overleaf.zip'
COLW = 3.5

# ===================================================================================== display equations
EQ = {
    'gold': r'G(q)=\bigcap_{m\in M(q)} C_m(q)',
    'necessity': r"\forall m\in M(q):\quad G_{-m}(q)=\bigcap_{m'\in M(q)\setminus\{m\}} C_{m'}(q)\supsetneq G(q)",
    'pipeline': r'A(q)=g\bigl(q,\varphi(E_T,\kappa(E_G),E_S)\bigr),\quad E=\bigcup_{t=1}^{k}\mathcal{R}_{s_t}(q_t)',
    'mst': r'T_k=\operatorname*{arg\,max}_{T\in\mathcal{T}(K_k)}\sum_{e\in T} w(e)',
    'pcst': r'T^*=\operatorname*{arg\,min}_{T}\Bigl(\sum_{e\in E(T)} c_e+\sum_{v\notin V(T)}\pi_v\Bigr)',
    'hsim': r'H(a,b)=\frac{1+\cos(\mathbf{h}_a,\mathbf{h}_b)}{2}',
    'conductance': r'w(u,v)=H(u,v)\Bigl(1+\frac{1}{4}\bigl(H(u,q)+H(v,q)\bigr)\Bigr)',
    'support': r'\mathrm{ex}(v)=\max(0,x_v-1),\quad \mathcal{S}=\{v: x_v>\tau\}',
    'supp': r'\mathrm{class}(b)=\begin{cases}\text{FULLY} & \text{if } G(q)\subseteq P(b)\\'
            r' \text{PARTIALLY} & \text{if } G(q)\cap P(b)\neq\emptyset\\ \text{UNSUPPORTABLE} & \text{otherwise}\end{cases}',
    'label': r'\ell(q)=\min\{\ell\in(A,B,C):\mathrm{succ}_\ell(q)\}',
    'platt': r'p=\frac{1}{1+e^{-(as+b)}},\quad a=0.376,\quad b=0.102',
    'state': r'\mathrm{state}(q)=\begin{cases}\text{GOOD} & \text{if } \max_i p_i\ge U\\'
             r' \text{BAD} & \text{if } \max_i p_i\le L\\ \text{AMBIGUOUS} & \text{otherwise}\end{cases}',
    'select': r'm^*=\operatorname*{arg\,max}_{m\in\mathcal{P}} F_1(m)',
    'prf': r'P=\frac{|A\cap G|}{|A|},\quad R=\frac{|A\cap G|}{|G|},\quad F_1=\frac{2PR}{P+R}',
    'gc': r'\mathrm{GC}(q)=\frac{|G(q)\cap\mathrm{IDs}(c(q))|}{|G(q)|}',
    'source': r'\mathrm{SF}_1=\frac{2|S\cap R|}{|S|+|R|},\quad \mathrm{WR}=\frac{|S\setminus R|}{|S|}',
    'boot': r'\hat{\Delta}_b=\frac{\sum_{f\in\mathcal{B}_b} S_f}{\sum_{f\in\mathcal{B}_b} n_f}',
    'signflip': r'p=\frac{1}{2^F}\sum_{\sigma\in\{\pm1\}^F}\mathbb{I}\bigl[T(\sigma)\ge T(\mathbf{1})\bigr]',
    'tstat': r'T(\sigma)=\Bigl|\sum_{f=1}^{F}\sigma_f S_f\Bigr|',
    'holm': r'\tilde{p}_{(i)}=\min\Bigl\{1,\ \max_{j\le i}\,(k-j+1)\,p_{(j)}\Bigr\}',
    'rank': r'R(m)=\sum_{a\in\mathcal{A}} r_a(m),\quad m^*=\operatorname*{arg\,min}_{m} R(m)',
    'scaled': r's(m)=\frac{1}{|\mathcal{A}|}\sum_{a\in\mathcal{A}}\frac{v_a(m)-v_a^{\min}}{v_a^{\max}-v_a^{\min}}',
}

# ===================================================================================== text and inline math
LATIN = set('áàâäãåçéèêëíìîïñóòôöõúùûüýÁÀÂÄÇÉÈÊËÍÎÏÑÓÔÖÚÙÛÜ')
SPECIAL = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}', '%': r'\%', '&': r'\&', '#': r'\#', '_': r'\_',
           '~': r'\textasciitilde{}', '^': r'\textasciicircum{}', '$': r'\$'}
TEXT_UNI = {'\u2014': '---', '\u2013': '--', '\u2026': r'\ldots{}', '\u00a0': '~', '\u00d7': r'$\times$', '\u2212': '$-$',
            '\u2264': r'$\le$', '\u2265': r'$\ge$', '\u2192': r'$\rightarrow$', '\u2190': r'$\leftarrow$', '\u2191': r'$\uparrow$',
            '\u2193': r'$\downarrow$', '\u2605': r'$\bigstar$', '\u0394': r'$\Delta$', '\u00b2': r'\textsuperscript{2}',
            '\u2229': r'$\cap$', '\u2286': r'$\subseteq$', '\u2208': r'$\in$', '\u00b1': r'$\pm$', '\u2248': r'$\approx$',
            '\u00b7': r'$\cdot$', '\u2019': "'", '\u2018': '`', '\u201c': '``', '\u201d': "''", '\u2713': r'\checkmark{}'}
OPEN_D, CLOSE_D, OPEN_S, CLOSE_S = '\x01', '\x02', '\x03', '\x04'
QUOTES = {OPEN_D: '``', CLOSE_D: "''", OPEN_S: '`', CLOSE_S: "'"}
MATH_SYM = {'π': r'\pi', 'φ': r'\varphi', 'κ': r'\kappa', 'ε': r'\varepsilon', 'τ': r'\tau', 'σ': r'\sigma', 'ℓ': r'\ell',
            'Δ': r'\Delta', '←': r'\leftarrow', '→': r'\rightarrow', '∈': r'\in', '∉': r'\notin', '⊆': r'\subseteq',
            '⊂': r'\subset', '⊄': r'\not\subseteq', '⊋': r'\supsetneq', '∩': r'\cap', '∪': r'\cup', '∖': r'\setminus',
            '≤': r'\le', '≥': r'\ge', '≠': r'\neq', '∅': r'\emptyset', '×': r'\times', '−': '-', '∑': r'\sum',
            '⋂': r'\bigcap', '⋃': r'\bigcup', '∀': r'\forall', '…': r'\ldots', '⋯': r'\cdots', '±': r'\pm', '∕': '/',
            '𝒮': r'\mathcal{S}', '𝒜': r'\mathcal{A}', '𝒩': r'\mathcal{N}', '𝒫': r'\mathcal{P}', '𝒯': r'\mathcal{T}',
            'ℬ': r'\mathcal{B}', 'ℛ': r'\mathcal{R}', 'ℰ': r'\mathcal{E}', '𝒱': r'\mathcal{V}', '𝐡': r'\mathbf{h}',
            '𝟙': r'\mathbb{I}', '𝟏': r'\mathbf{1}', 'Â': r'\hat{A}', '▒': ' ', '\u2061': '', '\u2032': "'"}
TOK = re.compile(r'(\$[^$]+\$|\[@[^\]]+\]|\[\[(?:fig|tab|eq|alg|sec):[\w\-]+\]\]|\*\*.+?\*\*|`[^`]+`'
                 r'|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*])|https?://\S*[^\s.,;:)])')
REF = {'fig': r'Fig.~\ref{%s}', 'tab': r'Table~\ref{%s}', 'eq': r'\eqref{%s}', 'alg': r'Algorithm~\ref{%s}', 'sec': r'Section~\ref{%s}'}


def bind(s):
    return re.sub(r'\{\{([^}]+)\}\}', lambda m: W.bound(m.group(1).strip()), s)


def mark_quotes(s):
    """Straight quotes outside math and code become opening/closing marks (UnicodeMath keeps its own quotes)."""
    out, prev, math, code = [], ' ', False, False
    for ch in s:
        if ch == '$' and not code:
            math = not math
        elif ch == '`' and not math:
            code = not code
        elif not math and not code and ch in '"\'':
            opening = prev.isspace() or prev in '([{\u2014\u2013/'
            ch = (OPEN_D if opening else CLOSE_D) if ch == '"' else (OPEN_S if opening else CLOSE_S)
        out.append(ch)
        prev = ch
    return ''.join(out)


def esc(s):
    out = []
    for ch in s:
        if ch in SPECIAL:
            out.append(SPECIAL[ch])
        elif ch in TEXT_UNI:
            out.append(TEXT_UNI[ch])
        elif ch in QUOTES:
            out.append(QUOTES[ch])
        elif ord(ch) > 127 and ch not in LATIN:
            raise ValueError('no LaTeX mapping for %r in %r' % (ch, s))
        else:
            out.append(ch)
    return ''.join(out)


def um2tex(s):
    """Translate the UnicodeMath subset used in paper.md into LaTeX math."""
    texts = []

    def keep(m):
        texts.append(r'{\text{%s}}' % ''.join(SPECIAL.get(c, c) if c in '_%&#' else c for c in m.group(1)))
        return '\x10%d\x11' % (len(texts) - 1)
    s = re.sub(r'"([^"]*)"', keep, s)
    s = s.replace('{', r'\{').replace('}', r'\}').replace('〖', '{').replace('〗', '}')
    chars, stack = list(s), []
    for i, ch in enumerate(chars):                  # _( ... ) and ^( ... ) are script groups
        if ch == '(':
            stack.append((i, i > 0 and chars[i - 1] in '_^'))
        elif ch == ')':
            j, script = stack.pop()
            if script:
                chars[j], chars[i] = '{', '}'
    out = []
    for ch in chars:
        if ch in '\u0302\u0303':                    # combining hat / tilde on the previous symbol
            out.append(r'\%s{%s}' % ('hat' if ch == '\u0302' else 'tilde', out.pop().strip()))
        elif ch in MATH_SYM:
            r = MATH_SYM[ch]
            out.append(r + (' ' if r[-1:].isalpha() else ''))
        elif ord(ch) > 127 and ch not in '\x10\x11':
            raise ValueError('no math mapping for %r in %r' % (ch, s))
        else:
            out.append(ch)
    s = ''.join(out)
    s = re.sub(r'(?<![\\a-zA-Z])(cos|sin|exp|log|max|min)(?![a-zA-Z])', r'\\\1', s)
    s = re.sub('\x10(\\d+)\x11', lambda m: texts[int(m.group(1))], s)
    return re.sub(r'\s+', ' ', s).strip()


def conv(s, cites):
    """Inline markup to LaTeX: math, citations, cross references, bold, italic, code, URLs, escaped text."""
    parts = []
    for tok in TOK.split(s):
        if not tok:
            continue
        if len(tok) > 1 and tok[0] == '$' and tok[-1] == '$':
            parts.append('$' + um2tex(tok[1:-1]) + '$')
        elif tok.startswith('[@'):
            keys = [k.strip() for k in tok[2:-1].split(';')]
            for k in keys:
                if k not in REFS:
                    raise KeyError('unknown reference ' + k)
                if k not in cites:
                    cites.append(k)
            parts.append(r'\cite{%s}' % ','.join(keys))
        elif tok.startswith('[['):
            kind, _, lab = tok[2:-2].partition(':')
            parts.append(REF[kind] % (kind + ':' + lab))
        elif tok.startswith('**') and tok.endswith('**') and len(tok) > 4:
            parts.append(r'\textbf{%s}' % conv(tok[2:-2], cites))
        elif tok.startswith('`') and tok.endswith('`') and len(tok) > 2:
            parts.append(r'\texttt{%s}' % esc(tok[1:-1]))
        elif tok.startswith('*') and tok.endswith('*') and len(tok) > 2:
            parts.append(r'\emph{%s}' % conv(tok[1:-1], cites))
        elif tok.startswith('http'):
            parts.append(r'\url{%s}' % tok)
        else:
            parts.append(esc(tok))
    return ''.join(parts).replace(r' \cite{', r'~\cite{')


# ===================================================================================== the document
class TeX:
    def __init__(self):
        self.blocks = []                            # (text, glued to the previous block without a blank line)
        self.cites = []
        self.list = None
        self.last_eq = False

    def text(self, s):
        return conv(mark_quotes(bind(s)), self.cites)

    def emit(self, s, glue=False):
        self.blocks.append((s, glue))

    def close_list(self):
        if self.list:
            self.emit(r'\end{%s}' % self.list, glue=True)
            self.list = None

    def render(self):
        out = ''
        for s, glue in self.blocks:
            out += ('\n' if glue else '\n\n') if out else ''
            out += s
        return out + '\n'

    # ------------------------------------------------------------------ blocks
    def title_block(self, meta):
        affil = r'\\'.join(r'\textit{%s}' % self.text(a) for a in meta.get('affil', []))
        self.emit('\n'.join([r'\title{%s}' % self.text(meta['title']),
                             r'\author{\IEEEauthorblockN{%s}' % self.text(meta['author']),
                             r'\IEEEauthorblockA{%s\\' % affil,
                             r'%s}}' % esc(meta.get('email', '')),
                             r'\maketitle']))

    def abstract(self, body, keywords):
        self.emit('\\begin{abstract}\n%s\n\\end{abstract}' % self.text(body))
        self.emit('\\begin{IEEEkeywords}\n%s\n\\end{IEEEkeywords}' % self.text(keywords))

    def heading(self, level, title, label):
        self.close_list()
        self.last_eq = False
        if level == 1 and title.startswith('*'):       # the reference list brings its own heading
            return
        cmd = {1: 'section', 2: 'subsection'}.get(level, 'subsubsection')
        self.emit(r'\%s{%s}' % (cmd, self.text(title)) + (r'\label{sec:%s}' % label if label else ''))

    def paragraph(self, s):
        self.close_list()
        self.emit(self.text(s), glue=self.last_eq and s[:1].islower())    # text continuing an equation
        self.last_eq = False

    def item(self, s, env):
        if self.list != env:
            self.close_list()
            self.emit(r'\begin{%s}' % env)
            self.list = env
        self.emit(r'\item ' + self.text(s), glue=True)
        self.last_eq = False

    def equation(self, label):
        self.close_list()
        if label not in EQ:
            raise KeyError('no LaTeX for equation ' + label)
        self.emit('\\begin{equation}\n%s\n\\label{eq:%s}\n\\end{equation}' % (EQ[label], label), glue=True)
        self.last_eq = True

    def figure(self, label, file, caption, wide, width):
        self.close_list()
        self.last_eq = False
        env = 'figure*' if wide else 'figure'
        size = r'\textwidth' if wide else (r'%.2f\columnwidth' % (min(width, COLW) / COLW) if width else r'\columnwidth')
        self.emit('\n'.join([r'\begin{%s}[!t]' % env, r'\centering',
                             r'\includegraphics[width=%s]{figures/%s.pdf}' % (size, Path(file).stem),
                             r'\caption{%s}' % self.text(caption), r'\label{fig:%s}' % label, r'\end{%s}' % env]))

    def table(self, label, caption, wide, widths, header, rows, align=None, bold=()):
        self.close_list()
        self.last_eq = False
        env = 'table*' if wide else 'table'
        widths = widths or [1] * len(header)
        align = align or ['l'] + ['r'] * (len(header) - 1)
        AL = {'l': r'\raggedright', 'r': r'\raggedleft', 'c': r'\centering'}
        spec = '@{}' + ''.join(r'>{%s\arraybackslash}p{\dimexpr%.3f\linewidth-2\tabcolsep\relax}' % (AL[a], w / sum(widths))
                               for a, w in zip(align, widths)) + '@{}'
        lines = [r'\begin{%s}[!t]' % env, r'\caption{%s}' % self.text(caption), r'\label{tab:%s}' % label, r'\centering',
                 r'\footnotesize', r'\setlength{\tabcolsep}{3pt}', r'\renewcommand{\arraystretch}{1.1}',
                 r'\begin{tabular}{%s}' % spec, r'\toprule',
                 ' & '.join(r'\textbf{%s}' % self.text(h) for h in header) + r' \\', r'\midrule']
        for ri, row in enumerate(rows):
            cells = [self.text(str(v)) for v in row]
            lines.append(' & '.join(r'\textbf{%s}' % c if (ri, ci) in bold else c for ci, c in enumerate(cells)) + r' \\')
        lines += [r'\bottomrule', r'\end{tabular}', r'\end{%s}' % env]
        self.emit('\n'.join(lines))

    def results(self, label, rq, metrics, caption, wide, methods=None):
        R = BD.RES[rq]
        ms = methods or R['methods']
        P = set(R.get('pareto') or [])
        short = {'answer_f1': 'F1', 'answer_em': 'EM', 'answerable_f1': 'F1 (ans.)', 'mrr': 'MRR', 'gold_coverage': 'GC',
                 'recall_at_5': 'R@5', 'source_f1': 'SF1', 'unnecessary_retrieval': 'WR', 'stopping_accuracy': 'Stop',
                 'required_source_miss': 'Miss', 'input_tokens': 'In tok.', 'output_tokens': 'Out tok.', 'total_tokens': 'Tokens',
                 'llm_calls': 'Calls', 'retrieval_calls': 'Search', 'latency': 'Lat. (s)', 'context_tokens': 'Ctx tok.',
                 'source_precision': 'SP', 'source_recall': 'SR'}
        header = ['Method'] + ['%s %s' % (short.get(k, k), '\u2191' if k in BD.HIGHER else '\u2193') for k in metrics]
        rows, bold = [], set()
        for j, k in enumerate(metrics):
            vals = [R['descriptive'][m].get(k) for m in ms]
            good = [v for v in vals if v is not None]
            if not good or max(good) - min(good) < 1e-12:
                continue
            best = max(good) if k in BD.HIGHER else min(good)
            bold.update((i, j + 1) for i, v in enumerate(vals) if v is not None and abs(v - best) < 1e-12)
        for m in ms:
            row = [m + (' \u2605' if m in P else '')]
            for k in metrics:
                v = R['descriptive'][m].get(k)
                row.append(BD.fmt(v, BD.KIND.get(k, 'rate')).replace(' s', '') if v is not None else 'n/a')
            rows.append(row)
        self.table(label, caption, wide, [1.15] + [1.0] * len(metrics), header, rows, bold=bold)

    def tests(self, label, rq, metric, caption):
        R = BD.RES[rq]
        mk = BD.KIND.get(metric, 'rate')
        rows = [['%s \u2212 %s' % (t['a'], t['b']), BD.fmt(t['delta'], mk, sign=True).replace(' s', ''),
                 '[%s, %s]' % (BD.fmt(t['ci95'][0], mk).replace(' s', ''), BD.fmt(t['ci95'][1], mk).replace(' s', '')),
                 BD.fmt(t['p'], 'p'), BD.fmt(t['p_holm'], 'p') + ('*' if t['significant'] else '')] for t in R['tests'][metric]]
        self.table(label, caption, False, [1.5, 0.95, 1.45, 0.75, 0.85], ['Pair (A \u2212 B)', '\u0394', '95% CI', '*p*', '*p* (Holm)'], rows)

    def algorithm(self, label, title, lines):
        self.close_list()
        self.last_eq = False
        out = [r'\begin{algorithm}[!t]', r'\caption{%s}' % self.text(title), r'\label{alg:%s}' % label, r'\begin{algorithmic}[1]']
        for raw in lines:
            depth = len(raw) - len(raw.lstrip('>'))
            body = raw.lstrip('>').strip()
            head, _, rest = body.partition(':')
            if head.lower() in ('input', 'output'):
                out.append((r'\Require ' if head.lower() == 'input' else r'\Ensure ') + self.text(rest.strip()))
            else:
                out.append(r'\State ' + (r'\hspace*{%d\algorithmicindent}' % depth if depth else '') + self.text(body))
        out += [r'\end{algorithmic}', r'\end{algorithm}']
        self.emit('\n'.join(out))

    def references(self):
        self.close_list()
        items = [r'\bibitem{%s} %s' % (k, conv(mark_quotes(REFS[k]), [])) for k in self.cites]
        self.emit('\\begin{thebibliography}{00}\n%s\n\\end{thebibliography}' % '\n'.join(items))


PREAMBLE = r"""%% Multi-Modal GraphRAG: IEEE (IEEEtran) LaTeX source.
%% Generated by documentation/paper/ieee/build/build_latex.py from paper.md, the same source text as the Word
%% version; every number is bound to the frozen study results. Compile with pdfLaTeX (the Overleaf default).
%% Still to complete: the affiliation line under the author and the GitHub URL in Section VI.
\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\interdisplaylinepenalty=2500
\usepackage{algorithm}
\usepackage[noend]{algpseudocode}
\algrenewcommand\algorithmicrequire{\textbf{Input:}}
\algrenewcommand\algorithmicensure{\textbf{Output:}}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{booktabs}
\usepackage{array}
\usepackage[hyphens]{url}

\begin{document}
"""


def build():
    lines = SRC.read_text(encoding='utf-8').splitlines()
    T = TeX()
    meta, i, para = {'affil': []}, 0, []

    def flush():
        for b in W.blocks(para):
            if b[0] == 'p':
                T.paragraph(b[1])
            else:
                T.item(b[1], 'itemize' if b[0] == 'b' else 'enumerate')
        T.close_list()
        para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith('<!--'):
            while '-->' not in lines[i]:
                i += 1
            i += 1
            continue
        if s.startswith('%'):
            k, _, v = s[1:].partition(' ')
            if k == 'affil':
                meta['affil'].append(v.strip())
            else:
                meta[k] = v.strip()
            if k == 'email':
                T.title_block(meta)
            i += 1
            continue
        if s.startswith('#'):
            flush()
            m = re.match(r'^(#{1,3})\s+(.*?)\s*(\{#sec:([\w\-]+)\})?$', s)
            T.heading(len(m.group(1)), m.group(2), m.group(4))
            i += 1
            continue
        if s.startswith('@'):
            flush()
            cmd, _, rest = s.partition(' ')
            args = [a.strip() for a in rest.split('|')]
            if cmd == '@abstract':
                j = i + 1
                body = []
                while lines[j].strip() != '@end':
                    body.append(lines[j].strip())
                    j += 1
                kw = lines[j + 1].strip()
                T.abstract(' '.join(body), kw[len('@keywords'):].strip())
                i = j + 2
                continue
            if cmd == '@alg':
                j = i + 1
                body = []
                while lines[j].strip() != '@end':
                    body.append(lines[j].rstrip())
                    j += 1
                T.algorithm(args[0], args[1], [b.strip() for b in body if b.strip()])
                i = j + 1
                continue
            if cmd == '@table':
                widths = [float(x) for x in args[3].split(',')] if len(args) > 3 and args[3] else None
                j = i + 1
                rows = []
                while j < len(lines) and lines[j].strip().startswith('|'):
                    raw = lines[j].strip()[1:]
                    rows.append(W.split_row(raw[:-1] if raw.endswith('|') else raw))
                    j += 1
                header, sep, body = rows[0], rows[1], rows[2:]
                align = ['r' if c.endswith(':') and not c.startswith(':') else ('c' if c.startswith(':') and c.endswith(':') else 'l') for c in sep]
                T.table(args[0], args[1], args[2] == 'wide', widths, header, body, align=align)
                i = j
                continue
            if cmd == '@fig':
                T.figure(args[0], args[1], args[2], args[3] == 'wide', float(args[4]) if len(args) > 4 and args[4] else None)
            elif cmd == '@results':
                T.results(args[0], args[1], args[2].split(','), args[3], args[4] == 'wide', args[5].split(',') if len(args) > 5 else None)
            elif cmd == '@tests':
                T.tests(args[0], args[1], args[2], args[3])
            elif cmd == '@eq':
                T.equation(args[0])
            elif cmd == '@refs':
                T.references()
            elif cmd not in ('@wide', '@narrow'):
                raise ValueError('unknown directive ' + cmd)
            i += 1
            continue
        para.append(line)
        i += 1
    flush()
    tex = PREAMBLE + T.render() + '\n\\end{document}\n'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'figures').mkdir(exist_ok=True)
    (OUT / 'main.tex').write_text(tex, encoding='utf-8', newline='\n')
    figs = sorted(set(re.findall(r'\\includegraphics\[[^\]]*\]\{figures/([^}]+)\}', tex)))
    for old in (OUT / 'figures').glob('*.pdf'):
        if old.name not in figs:
            old.unlink()
    for f in figs:
        shutil.copyfile(FIGS / f, OUT / 'figures' / f)
    check(tex, figs, T.cites)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(OUT / 'main.tex', 'main.tex')
        for f in figs:
            z.write(OUT / 'figures' / f, 'figures/' + f)
    print('wrote %s (%d lines) | %d figures | %d references | %s'
          % ((OUT / 'main.tex').relative_to(HERE.parents[2]), tex.count('\n'), len(figs), len(T.cites), ZIP.name))


def check(tex, figs, cites):
    """Static checks that catch what would stop pdfLaTeX: references, citations, braces, environments, characters."""
    body = tex.split(r'\begin{document}', 1)[1]
    labels = set(re.findall(r'\\label\{([^}]+)\}', body))
    refs = set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}', body))
    assert refs <= labels, ('references without labels', sorted(refs - labels))
    cited = {k for grp in re.findall(r'\\cite\{([^}]+)\}', body) for k in grp.split(',')}
    items = set(re.findall(r'\\bibitem\{([^}]+)\}', body))
    assert cited == items, ('citations and bibliography differ', sorted(cited ^ items))
    unused = [k for k in REFS if k not in cites]
    assert not unused, ('references never cited', unused)
    depth = 0
    for n, ch in enumerate(re.sub(r'\\[{}]', '', re.sub(r'\\\\', '', tex))):
        depth += {'{': 1, '}': -1}.get(ch, 0)
        assert depth >= 0, ('unbalanced } near', tex[max(0, n - 80):n])
    assert depth == 0, ('unbalanced braces', depth)
    stack = []
    for m in re.finditer(r'\\(begin|end)\{([^}]+)\}', tex):
        if m.group(1) == 'begin':
            stack.append(m.group(2))
        else:
            assert stack and stack.pop() == m.group(2), ('environment mismatch at', m.group(2), tex[max(0, m.start() - 80):m.start()])
    assert not stack, ('unclosed environments', stack)
    bad = sorted({ch for ch in tex if ord(ch) > 127 and ch not in LATIN})
    assert not bad, ('characters pdfLaTeX cannot typeset', bad)
    for blk in tex.split('\n\n'):
        assert len(re.findall(r'(?<!\\)\$', blk)) % 2 == 0, ('odd number of $ in', blk[:160])
    missing = [f for f in figs if not (FIGS / f).exists()]
    assert not missing, ('missing figure files', missing)


if __name__ == '__main__':
    build()
