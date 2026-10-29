"""Build the single-column journal manuscript (layout modelled on a Scientific Reports article) from scirep.md.

Page 8.27 x 10.87 in with a 5.56-in text column and a wide left margin; Corbel headings, title, abstract and
keywords; Palatino body; superscript citation numbers; captions below figures and tables ("Fig. n.", "Table n.");
boxed algorithms; numbered display equations (built into Word equations by ../../ieee/build/finalize_ieee.py);
Nature-style reference list. Wide figures and tables span the page from the left margin edge.

Markup (as in ../../ieee/build/paper.md, plus):
  %title %author %affil %email %running            title block, affiliation footnote, running head
  (i) item                                          list item with its own marker
  @fig label | file | caption | col|wide | width-in   file looked up in ../figures, ../../ieee/figures
  [[sec:x]] -> the title of the section labelled x
Placeholders {{KEY}} bind to the frozen results (build_docx.resolve); P6.<baseline>.<metric> binds the
retrieval-only baseline closeout (documentation/phase6_closeout/comparison.json, overall cohort).
"""
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor

HERE = Path(__file__).resolve().parent
IEEE = HERE.parents[1] / 'ieee' / 'build'
sys.path.insert(0, str(IEEE))
sys.path.insert(0, str(HERE))
import build_ieee as W                                   # noqa: E402  table/cell helpers, parser helpers, number binding
from refs_nature import REFS                             # noqa: E402

BD = W.BD
ROOT = HERE.parents[3]
OUT = HERE.parent / 'Multi-Modal_GraphRAG_SciRep.docx'
FIG_DIRS = [HERE.parent / 'figures', HERE.parents[1] / 'ieee' / 'figures']
SERIF, SANS, SYMBOL = 'Palatino Linotype', 'Corbel', 'Segoe UI Symbol'
BODY = 9.0
PAGE_W, PAGE_H = 8.27, 10.87
LEFT, RIGHT = 2.17, 0.55
COLW = PAGE_W - LEFT - RIGHT                             # 5.55 in text column
WIDE_IN = 1.60                                           # wide items start this far left of the column
WIDEW = COLW + WIDE_IN                                   # 7.15 in
MATH_L, MATH_R = W.MATH_L, W.MATH_R
SUP_L, SUP_R = '', ''                       # superscript citation delimiters
GREY = '595959'

P6 = json.loads((ROOT / 'documentation/phase6_closeout/comparison.json').read_text(encoding='utf-8'))


def bound(key):
    if key.startswith('P6.'):
        _, b, metric = key.split('.', 2)
        row = next(r for r in P6 if r['baseline'] == b and r['cohort'] == 'overall' and r['metric'] == metric)
        return BD.fnum(row['mean'], 3)
    return W.bound(key)


# =============================================================================== runs and paragraphs
def font(run, size=BODY, bold=None, italic=None, face=SERIF, color=None, sup=False, small_caps=False):
    run.font.name = face
    rpr = run._r.get_or_add_rPr()
    rf = rpr.get_or_add_rFonts()
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), face)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    if sup:
        run.font.superscript = True
    if small_caps:
        run.font.small_caps = True


TOKENS = re.compile(r'(⟪[^⟫]*⟫|[^]*|\*\*.+?\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))')
SYMBOLS = set('★✉✓→←↑↓')


def add(p, text, size=BODY, bold=False, italic=False, face=SERIF, color=None):
    for tok in TOKENS.split(text):
        if not tok:
            continue
        b, i, f, sup = bold, italic, face, False
        if tok[0] == MATH_L:
            pass
        elif tok[0] == SUP_L:
            tok, sup = tok[1:-1], True
        elif tok.startswith('**') and tok.endswith('**') and len(tok) > 4:
            add(p, tok[2:-2], size, True, italic, face, color)
            continue
        elif tok.startswith('`') and tok.endswith('`') and len(tok) > 2:
            tok, f, size_ = tok[1:-1], 'Consolas', size - 1
            r = p.add_run(tok)
            font(r, size_, b, False, f, color)
            continue
        elif tok.startswith('*') and tok.endswith('*') and len(tok) > 2:
            add(p, tok[1:-1], size, bold, True, face, color)
            continue
        for part in re.split('([%s])' % ''.join(SYMBOLS), tok):     # glyphs the text fonts lack
            if part:
                r = p.add_run(part)
                font(r, size, b, i, SYMBOL if part in SYMBOLS else f, color, sup)
    return p


def fmt(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=0, first=0.0, left=0.0, right=0.0, keep=False, line=None,
        exact=False):
    f = p.paragraph_format
    p.alignment = align
    f.space_before, f.space_after = Pt(before), Pt(after)
    f.first_line_indent = Inches(first) if first else None
    f.left_indent = Inches(left) if left else None
    f.right_indent = Inches(right) if right else None
    f.keep_with_next = keep
    f.widow_control = True
    if line:
        f.line_spacing_rule = WD_LINE_SPACING.EXACTLY if exact else WD_LINE_SPACING.AT_LEAST
        f.line_spacing = Pt(line)
    return p


def border(p, edge, sz=4, color='000000', space=1):
    W.pborder(p, edge, sz, color, space)


def field(run, instr):
    for kind, text in (('begin', None), (None, instr), ('separate', None), (None, '1'), ('end', None)):
        if kind:
            el = OxmlElement('w:fldChar')
            el.set(qn('w:fldCharType'), kind)
            run._r.append(el)
        elif text == instr:
            el = OxmlElement('w:instrText')
            el.set(qn('xml:space'), 'preserve')
            el.text = ' %s ' % instr
            run._r.append(el)
        else:
            el = OxmlElement('w:t')
            el.text = text
            run._r.append(el)


# =============================================================================== labels, citations, cross references
class Labels:
    def __init__(self):
        self.n = {'fig': 0, 'tab': 0, 'eq': 0, 'alg': 0}
        self.map = {}
        self.sec = {}
        self.cites = []

    def add(self, kind, label):
        self.n[kind] += 1
        self.map['%s:%s' % (kind, label)] = self.n[kind]
        return self.n[kind]

    def ref(self, key):
        kind, _, lab = key.partition(':')
        if kind == 'sec':
            return '“%s”' % self.sec[lab]
        v = self.map[key]
        return {'fig': 'Fig. %d', 'tab': 'Table %d', 'eq': '(%d)', 'alg': 'Algorithm %d'}[kind] % v

    def cite(self, keys):
        nums = []
        for k in (k.strip() for k in keys):
            if k not in REFS:
                raise KeyError('unknown reference ' + k)
            if k not in self.cites:
                self.cites.append(k)
            nums.append(self.cites.index(k) + 1)
        nums = sorted(set(nums))
        parts, i = [], 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            parts.append('%d–%d' % (nums[i], nums[j]) if j - i >= 2 else ','.join(str(n) for n in nums[i:j + 1]))
            i = j + 1
        return SUP_L + ','.join(parts) + SUP_R


def expand(text, L):
    text = re.sub(r'\{\{([^}]+)\}\}', lambda m: bound(m.group(1).strip()), text)
    text = re.sub(r'\[\[((?:fig|tab|eq|alg|sec):[\w\-]+)\]\]', lambda m: L.ref(m.group(1)), text)
    text = re.sub(r'\s*\[@([^\]]+)\]', lambda m: L.cite(m.group(1).split(';')), text)
    return W.smart(W.math_inline(text))


def find_fig(name):
    for d in FIG_DIRS:
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(name)


# =============================================================================== the builder
class Paper:
    def __init__(self):
        self.doc = Document()
        self.L = Labels()
        self.after_block = True                          # next paragraph is the first after a heading or float
        self.subsub = None
        self._page()
        self._styles()

    def _page(self):
        s = self.doc.sections[0]
        s.page_width, s.page_height = Inches(PAGE_W), Inches(PAGE_H)
        s.left_margin, s.right_margin = Inches(LEFT), Inches(RIGHT)
        s.top_margin, s.bottom_margin = Inches(0.78), Inches(0.72)
        s.header_distance = s.footer_distance = Inches(0.32)

    def _styles(self):
        st = self.doc.styles
        n = st['Normal']
        n.font.name = SERIF
        n._element.rPr.rFonts.set(qn('w:eastAsia'), SERIF)
        n.font.size = Pt(BODY)
        n.paragraph_format.space_after = Pt(0)
        n.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
        n.paragraph_format.line_spacing = Pt(11.6)
        eq = st.add_style('IEEE Equation', WD_STYLE_TYPE.PARAGRAPH)   # name expected by finalize_ieee.py
        eq.base_style = n
        eq.paragraph_format.space_before = Pt(4)
        eq.paragraph_format.space_after = Pt(4)
        eq.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for name, size in (('Heading 1', 11), ('Heading 2', 9.5), ('Heading 3', BODY)):
            h = st[name]
            h.font.name = SANS if name != 'Heading 3' else SERIF
            rpr = h._element.get_or_add_rPr()
            rf = rpr.find(qn('w:rFonts'))
            if rf is None:
                rf = OxmlElement('w:rFonts')
                rpr.append(rf)
            for a in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
                rf.set(qn(a), SANS if name != 'Heading 3' else SERIF)
            for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
            h.font.size = Pt(size)
            h.font.bold = name != 'Heading 3'
            h.font.italic = name == 'Heading 3'
            h.font.color.rgb = RGBColor(0, 0, 0)
            h.paragraph_format.keep_with_next = True

    # ------------------------------------------------------------------ title block, header and footer
    def title_block(self, meta):
        p = self.doc.add_paragraph()
        fmt(p, WD_ALIGN_PARAGRAPH.LEFT, before=18, after=12, line=26, exact=True)
        add(p, meta['title'], 22, bold=True, face=SANS)
        p = self.doc.add_paragraph()
        fmt(p, WD_ALIGN_PARAGRAPH.LEFT, after=12)
        add(p, meta['author'], 10, bold=True, face=SANS)
        r = p.add_run('1')
        font(r, 10, True, face=SANS, sup=True)
        r = p.add_run('✉')
        font(r, 7, face=SYMBOL, sup=True)
        foot = self.doc.add_paragraph()               # affiliation footnote at the bottom of page 1 (a frame)
        fmt(foot, WD_ALIGN_PARAGRAPH.LEFT, before=3, line=9.5)
        border(foot, 'top', 4, '808080', 4)
        r = foot.add_run('1')
        font(r, 7, sup=True)
        add(foot, ' '.join(meta.get('affil', [])) + ' ', 7)
        r = foot.add_run('✉')
        font(r, 7, face=SYMBOL)
        add(foot, 'email: ' + meta.get('email', ''), 7)
        f = OxmlElement('w:framePr')
        for k, v in (('w', str(int(COLW * 1440))), ('hSpace', '0'), ('vSpace', '120'), ('wrap', 'notBeside'), ('vAnchor', 'margin'),
                     ('hAnchor', 'margin'), ('x', '0'), ('yAlign', 'bottom')):
            f.set(qn('w:' + k), v)
        pPr = foot._p.get_or_add_pPr()
        pPr.insert(0, f)
        self._header_footer(meta.get('running', ''))

    def _header_footer(self, running):
        s = self.doc.sections[0]
        hp = s.header.paragraphs[0]
        fmt(hp, WD_ALIGN_PARAGRAPH.RIGHT, left=-WIDE_IN)
        add(hp, running, 8, face=SANS, color=GREY)
        border(hp, 'bottom', 4, 'BFBFBF', 3)
        fp = s.footer.paragraphs[0]
        fmt(fp, WD_ALIGN_PARAGRAPH.LEFT, left=-WIDE_IN)
        fp.paragraph_format.tab_stops.add_tab_stop(Inches(WIDEW), 2)    # right tab
        add(fp, 'Manuscript — ' + running, 7.5, face=SANS, color=GREY)
        r = fp.add_run('\t')
        font(r, 8, face=SANS)
        r = fp.add_run()
        font(r, 8, bold=True, face=SANS, color=GREY)
        field(r, 'PAGE')

    def abstract(self, text, keywords):
        p = self.doc.add_paragraph()
        fmt(p, WD_ALIGN_PARAGRAPH.LEFT, after=9, line=11.5)
        add(p, expand(text, self.L), 9, bold=True, face=SANS)
        p = self.doc.add_paragraph()
        fmt(p, WD_ALIGN_PARAGRAPH.LEFT, after=12, line=11.5)
        add(p, 'Keywords', 10, bold=True, face=SANS)
        add(p, ' ' + keywords, 9, face=SANS)
        self.after_block = False                       # the untitled introduction starts indented like the reference

    # ------------------------------------------------------------------ headings and text
    def heading(self, level, text, label=None):
        if label:
            self.L.sec[label] = text.lstrip('*')
        if level == 3:
            p = self.doc.add_paragraph(style='Heading 3')
            fmt(p, WD_ALIGN_PARAGRAPH.LEFT, before=5, after=1, keep=True)
            add(p, expand(text, self.L), BODY, italic=True)
        else:
            p = self.doc.add_paragraph(style='Heading %d' % level)
            fmt(p, WD_ALIGN_PARAGRAPH.LEFT, before=13 if level == 1 else 8, after=3 if level == 1 else 2, keep=True)
            add(p, expand(text.lstrip('*'), self.L), 11 if level == 1 else 9.5, bold=True, face=SANS)
        self.after_block = True

    def paragraph(self, text):
        p = self.doc.add_paragraph()
        cont = text[:1].islower()                       # text continuing after an equation
        fmt(p, first=0 if (self.after_block or cont) else 0.17)
        add(p, expand(text, self.L))
        self.after_block = False
        return p

    def item(self, text, marker, level=0):
        p = self.doc.add_paragraph()
        ind = 0.22 + 0.18 * level
        fmt(p, WD_ALIGN_PARAGRAPH.LEFT if 'http' in text else WD_ALIGN_PARAGRAPH.JUSTIFY, left=ind + 0.08, first=-0.22, after=1.5)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(ind + 0.08))
        r = p.add_run(marker + '\t')
        font(r, BODY)
        add(p, expand(text, self.L))
        self.after_block = False

    # ------------------------------------------------------------------ floats
    def figure(self, label, file, caption, wide, width):
        n = self.L.n['fig'] + 1
        w = min(width or (WIDEW if wide else COLW), WIDEW if wide else COLW)
        p = self.doc.add_paragraph()
        span = WIDEW if wide else COLW
        fmt(p, WD_ALIGN_PARAGRAPH.CENTER, before=8, after=3, keep=True, left=-WIDE_IN if wide else 0)
        p.add_run().add_picture(str(find_fig(file)), width=Inches(w))
        c = self.doc.add_paragraph()
        fmt(c, WD_ALIGN_PARAGRAPH.LEFT, after=10, left=-WIDE_IN if wide else 0, line=10.5)
        r = c.add_run('Fig. %d. ' % n)
        font(r, 8.2, bold=True)
        add(c, expand(caption, self.L), 8.2)
        self.L.add('fig', label)
        self.after_block = True
        del span

    def figpair(self, items, width=3.45):
        """Two figures side by side across the full page width, each with its own number and caption."""
        t = self.doc.add_table(rows=1, cols=2)
        W.table_fixed(t, [WIDEW / 2, WIDEW / 2])
        ind = OxmlElement('w:tblInd')
        ind.set(qn('w:w'), str(int(-WIDE_IN * 1440)))
        ind.set(qn('w:type'), 'dxa')
        t._tbl.tblPr.append(ind)
        W.row_props(t.rows[0])
        for cell, (label, file, caption) in zip(t.rows[0].cells, items):
            W.cell_borders(cell)
            W.cell_margins(cell, t=0, b=0, l=50, r=50)
            p = cell.paragraphs[0]
            fmt(p, WD_ALIGN_PARAGRAPH.CENTER, before=6, after=3, keep=True)
            p.add_run().add_picture(str(find_fig(file)), width=Inches(width))
            c = cell.add_paragraph()
            fmt(c, WD_ALIGN_PARAGRAPH.LEFT, after=6, line=10.5)
            r = c.add_run('Fig. %d. ' % self.L.add('fig', label))
            font(r, 8.2, bold=True)
            add(c, expand(caption, self.L), 8.2)
        sp = self.doc.add_paragraph()
        fmt(sp, after=0, line=4, exact=True)
        self.after_block = True

    def table(self, label, caption, wide, widths, header, rows, align=None, bold_cells=(), size=7.6):
        total = WIDEW if wide else COLW
        widths = widths or [1] * len(header)
        widths = [total * x / sum(widths) for x in widths]
        align = align or ['l'] + ['r'] * (len(header) - 1)
        AL = {'l': WD_ALIGN_PARAGRAPH.LEFT, 'r': WD_ALIGN_PARAGRAPH.RIGHT, 'c': WD_ALIGN_PARAGRAPH.CENTER}
        sp = self.doc.add_paragraph()
        fmt(sp, after=0, line=4, exact=True, keep=True)
        t = self.doc.add_table(rows=1 + len(rows), cols=len(header))
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        W.table_fixed(t, widths)
        if wide:
            ind = OxmlElement('w:tblInd')
            ind.set(qn('w:w'), str(int(-WIDE_IN * 1440)))
            ind.set(qn('w:type'), 'dxa')
            t._tbl.tblPr.append(ind)
        short = len(rows) <= 12
        for ri, row in enumerate([header] + rows):
            tr = t.rows[ri]
            W.row_props(tr, header=ri == 0)
            for ci, val in enumerate(row):
                c = tr.cells[ci]
                W.cell_margins(c, t=25, b=25, l=60, r=60)
                c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                W.cell_borders(c, top=4, bottom=4, left=4, right=4)
                if ri == 0:
                    shd = OxmlElement('w:shd')
                    shd.set(qn('w:val'), 'clear')
                    shd.set(qn('w:color'), 'auto')
                    shd.set(qn('w:fill'), 'F2F2F2')
                    c._tc.get_or_add_tcPr().append(shd)
                p = c.paragraphs[0]
                fmt(p, AL[align[ci]] if ri else WD_ALIGN_PARAGRAPH.LEFT if align[ci] == 'l' else WD_ALIGN_PARAGRAPH.CENTER,
                    keep=short or ri == 0, line=9.2)
                add(p, expand(str(val), self.L), size, bold=(ri == 0) or ((ri - 1, ci) in bold_cells))
        c = self.doc.add_paragraph()
        fmt(c, WD_ALIGN_PARAGRAPH.LEFT, before=3, after=10, left=-WIDE_IN if wide else 0, line=10.5)
        r = c.add_run('Table %d. ' % self.L.add('tab', label))
        font(r, 8.2, bold=True)
        add(c, expand(caption, self.L), 8.2)
        self.after_block = True

    def results(self, label, rq, metrics, caption, wide, methods=None):
        R = BD.RES[rq]
        ms = methods or R['methods']
        P = set(R.get('pareto') or [])
        short = {'answer_f1': 'F1', 'answer_em': 'EM', 'answerable_f1': 'F1 (ans.)', 'mrr': 'MRR', 'gold_coverage': 'GC',
                 'source_f1': 'SF1', 'unnecessary_retrieval': 'WR', 'stopping_accuracy': 'Stop', 'required_source_miss': 'Miss',
                 'input_tokens': 'In tok.', 'output_tokens': 'Out tok.', 'total_tokens': 'Tokens', 'llm_calls': 'Calls',
                 'retrieval_calls': 'Search', 'latency': 'Lat. (s)'}
        header = ['Method'] + ['%s %s' % (short.get(k, k), '↑' if k in BD.HIGHER else '↓') for k in metrics]
        rows, bold = [], set()
        for j, k in enumerate(metrics):
            vals = [R['descriptive'][m].get(k) for m in ms]
            good = [v for v in vals if v is not None]
            if good and max(good) - min(good) > 1e-12:
                best = max(good) if k in BD.HIGHER else min(good)
                bold.update((i, j + 1) for i, v in enumerate(vals) if v is not None and abs(v - best) < 1e-12)
        for m in ms:
            rows.append([m + (' ★' if m in P else '')] +
                        [BD.fmt(R['descriptive'][m][k], BD.KIND.get(k, 'rate')).replace(' s', '') for k in metrics])
        self.table(label, caption, wide, [1.2] + [1.0] * len(metrics), header, rows, bold_cells=bold)

    def equation(self, label, umath):
        n = self.L.add('eq', label)
        p = self.doc.add_paragraph(style='IEEE Equation')
        p.add_run(umath.strip() + '#(%d)' % n)

    def algorithm(self, label, title, lines):
        n = self.L.add('alg', label)
        t = self.doc.add_table(rows=1, cols=1)
        W.table_fixed(t, [COLW])
        cell = t.rows[0].cells[0]
        W.cell_borders(cell, top=6, bottom=6, left=6, right=6)
        W.cell_margins(cell, t=70, b=70, l=110, r=110)
        first = True
        step = 0
        for raw in lines:
            depth = len(raw) - len(raw.lstrip('>'))
            text = raw.lstrip('>').strip()
            p = cell.paragraphs[0] if first else cell.add_paragraph()
            first = False
            head, _, rest = text.partition(':')
            if head.lower() in ('input', 'output'):
                fmt(p, WD_ALIGN_PARAGRAPH.LEFT, left=0.62, first=-0.62, line=10.5, keep=True)
                add(p, head + ':', 8.2, bold=True)
                add(p, ' ' + expand(rest.strip(), self.L), 8.2)
            else:
                step += 1
                ind = 0.42 + 0.2 * depth
                fmt(p, WD_ALIGN_PARAGRAPH.LEFT, left=ind, first=-0.42 if not depth else -0.2, line=10.5, keep=True)
                p.paragraph_format.tab_stops.add_tab_stop(Inches(ind))
                if depth:
                    r = p.add_run('•\t')
                    font(r, 8.2, color=GREY)
                else:
                    r = p.add_run('Step %d.\t' % step)
                    font(r, 8.2, bold=True)
                add(p, expand(text, self.L), 8.2)
        c = self.doc.add_paragraph()
        fmt(c, WD_ALIGN_PARAGRAPH.LEFT, before=3, after=10, line=10.5)
        r = c.add_run('Algorithm %d. ' % n)
        font(r, 8.2, bold=True)
        add(c, expand(title, self.L), 8.2)
        self.after_block = True

    def references(self):
        for i, k in enumerate(self.L.cites, 1):
            p = self.doc.add_paragraph()
            fmt(p, WD_ALIGN_PARAGRAPH.LEFT, left=0.27, first=-0.27, after=1, line=9.6)
            p.paragraph_format.tab_stops.add_tab_stop(Inches(0.27))
            r = p.add_run('%d.\t' % i)
            font(r, 7.5)
            add(p, W.smart(REFS[k]), 7.5)


# =============================================================================== parser
def blocks(lines):
    out, buf = [], []

    def flush():
        if buf:
            out.append(('p', ' '.join(x.strip() for x in buf)))
            buf.clear()
    for line in lines:
        b = re.match(r'^(\s*)- (.*)$', line)
        n = re.match(r'^(\s*)(\d+)\. (.*)$', line)
        r = re.match(r'^(\s*)(\((?:[ivx]+|[a-h])\)) (.*)$', line)
        if not line.strip():
            flush()
        elif b:
            flush()
            out.append(('i', b.group(2), len(b.group(1)) // 2, '•'))
        elif n:
            flush()
            out.append(('i', n.group(3), len(n.group(1)) // 2, n.group(2) + '.'))
        elif r:
            flush()
            out.append(('i', r.group(3), len(r.group(1)) // 2, r.group(2)))
        elif out and out[-1][0] == 'i' and line.startswith('  ') and not buf:
            o = out[-1]
            out[-1] = (o[0], o[1] + ' ' + line.strip(), o[2], o[3])
        else:
            buf.append(line)
    flush()
    return out


def prescan(lines, L):
    counts = {'fig': 0, 'tab': 0, 'eq': 0, 'alg': 0}
    for line in lines:
        s = line.strip()
        fp = re.match(r'^@figpair\s+([\w\-]+)\s*\|[^|]*\|[^|]*\|\s*([\w\-]+)\s*\|', s)
        if fp:
            for lab in fp.groups():
                counts['fig'] += 1
                L.map['fig:' + lab] = counts['fig']
            continue
        m = re.match(r'^@(fig|table|results|eq|alg)\s+([\w\-]+)\s*\|', s)
        if m:
            kind = {'fig': 'fig', 'table': 'tab', 'results': 'tab', 'eq': 'eq', 'alg': 'alg'}[m.group(1)]
            counts[kind] += 1
            L.map['%s:%s' % (kind, m.group(2))] = counts[kind]
        h = re.match(r'^#{1,3}\s+\*?(.*?)\s*\{#sec:([\w\-]+)\}$', s)
        if h:
            L.sec[h.group(2)] = h.group(1)


def build(src):
    lines = src.read_text(encoding='utf-8').splitlines()
    P = Paper()
    prescan(lines, P.L)
    saved = dict(P.L.map)
    P.L.n = {'fig': 0, 'tab': 0, 'eq': 0, 'alg': 0}
    meta, i, para = {'affil': []}, 0, []

    def flush():
        for b in blocks(para):
            if b[0] == 'p':
                P.paragraph(b[1])
            else:
                P.item(b[1], b[3], b[2])
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
            if k == 'running':
                P.title_block(meta)
            i += 1
            continue
        if s.startswith('#'):
            flush()
            m = re.match(r'^(#{1,3})\s+(.*?)\s*(\{#sec:([\w\-]+)\})?$', s)
            P.heading(len(m.group(1)), m.group(2), m.group(4))
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
                P.abstract(' '.join(body), lines[j + 1].strip()[len('@keywords'):].strip())
                i = j + 2
                continue
            if cmd == '@alg':
                j = i + 1
                body = []
                while lines[j].strip() != '@end':
                    body.append(lines[j].rstrip())
                    j += 1
                P.algorithm(args[0], args[1], [b.strip() for b in body if b.strip()])
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
                P.table(args[0], args[1], args[2] == 'wide', widths, header, body, align=align)
                i = j
                continue
            if cmd == '@figpair':
                P.figpair([(args[0], args[1], args[2]), (args[3], args[4], args[5])])
            elif cmd == '@fig':
                P.figure(args[0], args[1], args[2], args[3] == 'wide', float(args[4]) if len(args) > 4 and args[4] else None)
            elif cmd == '@results':
                P.results(args[0], args[1], args[2].split(','), args[3], args[4] == 'wide', args[5].split(',') if len(args) > 5 else None)
            elif cmd == '@eq':
                P.equation(args[0], rest.split('|', 1)[1])
            elif cmd == '@refs':
                P.references()
            else:
                raise ValueError('unknown directive ' + cmd)
            i += 1
            continue
        para.append(line)
        i += 1
    flush()
    for k, v in saved.items():
        assert P.L.map.get(k) == v, ('label numbering mismatch', k, v, P.L.map.get(k))
    unused = [k for k in REFS if k not in P.L.cites]
    P.doc.core_properties.title = meta.get('title', '')
    P.doc.core_properties.author = meta.get('author', '')
    P.doc.save(OUT)
    print('saved %s | figures %d, tables %d, equations %d, algorithms %d, references %d%s'
          % (OUT.name, P.L.n['fig'], P.L.n['tab'], P.L.n['eq'], P.L.n['alg'], len(P.L.cites),
             (' | unused references: ' + ', '.join(unused)) if unused else ''))


if __name__ == '__main__':
    build(HERE / 'scirep.md')
