"""Build the IEEE-format paper (two-column Word document) from paper.md.

Markup (one block per line group):
  %title / %author / %affil / %email      title block
  @abstract ... @end / @keywords ...      abstract and index terms
  # Title {#sec:x}   ## Title {#sec:x}    section (I, II, ...) / subsection (A, B, ...)
  ### Title                                run-in sub-subsection "1) Title:" opening the next paragraph
  - item / 1. item                         bullet / numbered item
  @fig label | file | caption | col|wide | width-in [| top|bottom]
  @table label | caption | col|wide | rel-widths      followed by a pipe table (header, separator, rows)
  @results label | RQx | metric,metric,... | caption | col|wide [| methods]
Wide figures and tables float to the top (or bottom) of the page on which they are anchored and span both columns: a
figure as a Word frame holding the picture and its caption, a table as a floating table whose first rows hold its caption.
  @tests label | RQx | metric | caption
  @eq label | UnicodeMath                  numbered display equation (built into a Word equation by finalize)
  @alg label | title ... @end              algorithm box; '>' prefixes indent a line
  @refs                                     the reference list
  @wide / @narrow                          switch to one / two columns (continuous section break)
Inline: [@key;key] citations, [[fig:x]] [[tab:x]] [[eq:x]] [[alg:x]] [[sec:x]] cross references,
        {{KEY}} numbers from the frozen results, $...$ inline math, *italic*, **bold**, `code`.
"""
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
sys.path.insert(0, str(HERE.parents[2] / 'project_documentation' / 'build'))
import build_docx as BD          # noqa: E402  frozen-result binding (resolve), number formatting
from refs import REFS            # noqa: E402

OUT = HERE.parent / 'Multi-Modal_GraphRAG_IEEE.docx'
FIGS = HERE.parent / 'figures'
FONT = 'Times New Roman'
COLW, WIDEW = 3.5, 7.0
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX']
MATH_L, MATH_R = '\u27ea', '\u27eb'          # inline-math delimiters, replaced by Word equations in finalize


# =============================================================================== low-level helpers
def set_cols(sectPr, n, space_in=0.25):
    for c in sectPr.findall(qn('w:cols')):
        sectPr.remove(c)
    cols = OxmlElement('w:cols')
    cols.set(qn('w:num'), str(n))
    cols.set(qn('w:space'), str(int(space_in * 1440)))
    pgMar = sectPr.find(qn('w:pgMar'))
    (pgMar.addnext if pgMar is not None else sectPr.append)(cols)


def pborder(p, edge, sz=4, color='000000', space=1):
    pPr = p._p.get_or_add_pPr()
    b = pPr.find(qn('w:pBdr'))
    if b is None:
        b = OxmlElement('w:pBdr')
        pPr.append(b)
    el = OxmlElement('w:%s' % edge)
    el.set(qn('w:val'), 'single')
    el.set(qn('w:sz'), str(sz))
    el.set(qn('w:space'), str(space))
    el.set(qn('w:color'), color)
    b.append(el)


def cell_borders(cell, **edges):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement('w:%s' % edge)
        if edge in edges and edges[edge]:
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), str(edges[edge]))
            el.set(qn('w:space'), '0')
            el.set(qn('w:color'), '000000')
        else:
            el.set(qn('w:val'), 'nil')
        b.append(el)
    tcPr.append(b)


def cell_margins(cell, t=20, b=20, l=50, r=50):
    tcPr = cell._tc.get_or_add_tcPr()
    m = OxmlElement('w:tcMar')
    for k, v in (('top', t), ('bottom', b), ('left', l), ('right', r)):
        el = OxmlElement('w:%s' % k)
        el.set(qn('w:w'), str(v))
        el.set(qn('w:type'), 'dxa')
        m.append(el)
    tcPr.append(m)


def table_fixed(table, widths):
    tblPr = table._tbl.tblPr
    lay = OxmlElement('w:tblLayout')
    lay.set(qn('w:type'), 'fixed')
    tblPr.append(lay)
    b = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement('w:%s' % edge)
        el.set(qn('w:val'), 'nil')
        b.append(el)
    tblPr.append(b)
    table.autofit = False
    for row in table.rows:
        for i, c in enumerate(row.cells):
            c.width = Inches(widths[i])
    for i, gc in enumerate(table._tbl.tblGrid.findall(qn('w:gridCol'))):
        gc.set(qn('w:w'), str(int(widths[i] * 1440)))


def frame(p, pos='top', width=None, gap=10):
    """Put a paragraph into a full-width frame at the top or bottom of the page (adjacent paragraphs with equal frame
    properties form one frame). Text never flows beside it."""
    pPr = p._p.get_or_add_pPr()
    f = OxmlElement('w:framePr')
    for k, v in (('w', str(int((width or WIDEW) * 1440))), ('hSpace', '0'), ('vSpace', str(gap * 20)), ('wrap', 'notBeside'),
                 ('vAnchor', 'margin'), ('hAnchor', 'margin'), ('xAlign', 'center'), ('yAlign', pos)):
        f.set(qn('w:' + k), v)
    before = [c for c in pPr if c.tag in (qn('w:pStyle'), qn('w:keepNext'), qn('w:keepLines'), qn('w:pageBreakBefore'))]
    if before:
        before[-1].addnext(f)
    else:
        pPr.insert(0, f)


def float_table(table, width, pos='top', gap=10):
    """Make a table float at the top or bottom of the page, centred across both columns, never overlapping another."""
    tblPr = table._tbl.tblPr
    pp = OxmlElement('w:tblpPr')
    for k, v in (('leftFromText', '0'), ('rightFromText', '0'), ('topFromText', str(gap * 20) if pos == 'bottom' else '0'),
                 ('bottomFromText', '0' if pos == 'bottom' else str(gap * 20)), ('vertAnchor', 'margin'), ('horzAnchor', 'margin'),
                 ('tblpXSpec', 'center'), ('tblpYSpec', pos)):
        pp.set(qn('w:' + k), v)
    style = tblPr.find(qn('w:tblStyle'))
    if style is not None:
        style.addnext(pp)
    else:
        tblPr.insert(0, pp)
    ov = OxmlElement('w:tblOverlap')
    ov.set(qn('w:val'), 'never')
    pp.addnext(ov)
    w = tblPr.find(qn('w:tblW'))
    if w is not None:
        w.set(qn('w:w'), str(int(width * 1440)))
        w.set(qn('w:type'), 'dxa')


def row_props(row, header=False):
    trPr = row._tr.get_or_add_trPr()
    cs = OxmlElement('w:cantSplit')
    cs.set(qn('w:val'), 'true')
    trPr.append(cs)
    if header:
        h = OxmlElement('w:tblHeader')
        h.set(qn('w:val'), 'true')
        trPr.append(h)


def run_font(run, size=None, bold=None, italic=None, small_caps=None, font=FONT, color=None):
    run.font.name = font
    rpr = run._r.get_or_add_rPr()
    rf = rpr.get_or_add_rFonts()
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), font)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if small_caps:
        run.font.small_caps = True
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


INLINE = re.compile(r'(\u27ea[^\u27eb]*\u27eb|\*\*.+?\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))')


def add_text(p, text, size=10, bold=False, italic=False, small_caps=False):
    for tok in INLINE.split(text):
        if not tok:
            continue
        b, i, code, math = bold, italic, False, False
        if tok.startswith(MATH_L):
            math = True
        elif tok.startswith('**') and tok.endswith('**') and len(tok) > 4:
            tok, b = tok[2:-2], True
        elif tok.startswith('`') and tok.endswith('`') and len(tok) > 2:
            tok, code = tok[1:-1], True
        elif tok.startswith('*') and tok.endswith('*') and len(tok) > 2:
            tok, i = tok[1:-1], True
        r = p.add_run(tok)
        if code:
            run_font(r, size=size - 1, bold=b, italic=False, font='Courier New')
        else:
            run_font(r, size=size, bold=b, italic=i, small_caps=small_caps and not math)
    return p


def pfmt(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=0, first=0.0, left=0.0, keep=False, line=None):
    f = p.paragraph_format
    p.alignment = align
    f.space_before, f.space_after = Pt(before), Pt(after)
    f.first_line_indent = Inches(first) if first else None
    f.left_indent = Inches(left) if left else None
    f.keep_with_next = keep
    f.widow_control = True
    if line:
        f.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        f.line_spacing = Pt(line)
    else:
        f.line_spacing = 1.0
    return p


# =============================================================================== content pre-processing
class Labels:
    def __init__(self):
        self.n = {'fig': 0, 'tab': 0, 'eq': 0, 'alg': 0}
        self.map = {}
        self.cites = []

    def add(self, kind, label):
        self.n[kind] += 1
        self.map['%s:%s' % (kind, label)] = self.n[kind]
        return self.n[kind]

    def ref(self, key):
        kind, _, lab = key.partition(':')
        if key not in self.map:
            raise KeyError('undefined reference ' + key)
        v = self.map[key]
        if kind == 'fig':
            return 'Fig. %d' % v
        if kind == 'tab':
            return 'Table %s' % ROMAN[v - 1]
        if kind == 'eq':
            return '(%d)' % v
        if kind == 'alg':
            return 'Algorithm %d' % v
        if kind == 'sec':
            return 'Section %s' % v
        raise KeyError(key)

    def cite(self, keys):
        nums = []
        for k in keys:
            k = k.strip()
            if k not in REFS:
                raise KeyError('unknown reference ' + k)
            if k not in self.cites:
                self.cites.append(k)
            nums.append(self.cites.index(k) + 1)
        nums = sorted(set(nums))
        parts, i = [], 0
        while i < len(nums):            # IEEE: [3]-[5] for runs of three or more
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            if j - i >= 2:
                parts.append('[%d]\u2013[%d]' % (nums[i], nums[j]))
            else:
                parts.extend('[%d]' % n for n in nums[i:j + 1])
            i = j + 1
        return ', '.join(parts)


def smart(text):
    """Typographic quotes outside inline math (whose quotes mark upright text) and code."""
    out, prev, math, code = [], ' ', False, False
    for ch in text:
        if ch == MATH_L:
            math = True
        elif ch == MATH_R:
            math = False
        elif ch == '`' and not math:
            code = not code
        elif not math and not code and ch in '"\'':
            opening = prev.isspace() or prev in '([{\u2014\u2013/'
            ch = ('\u201c' if opening else '\u201d') if ch == '"' else ('\u2018' if opening else '\u2019')
        out.append(ch)
        prev = ch
    return ''.join(out)


def math_inline(text):
    return re.sub(r'\$([^$]+)\$', lambda m: MATH_L + m.group(1) + MATH_R, text)


def bound(key):
    """BD.resolve plus two paper-only flags: |abs drops the sign of a difference, |nounit drops the ' s' of latencies."""
    flags = []
    while key.endswith(('|abs', '|nounit')):
        key, _, f = key.rpartition('|')
        flags.append(f)
    out = BD.resolve(key)
    if 'abs' in flags:
        out = out.lstrip('+−-')
    if 'nounit' in flags:
        out = out.replace(' s', '')
    return out.replace(' %', '%')


def expand(text, L):
    text = re.sub(r'\{\{([^}]+)\}\}', lambda m: bound(m.group(1).strip()), text)
    text = re.sub(r'\[\[((?:fig|tab|eq|alg|sec):[\w\-]+)\]\]', lambda m: L.ref(m.group(1)), text)
    text = re.sub(r'\[@([^\]]+)\]', lambda m: L.cite(m.group(1).split(';')), text)
    return smart(math_inline(text))


# =============================================================================== the builder
class Paper:
    def __init__(self):
        self.doc = Document()
        self.L = Labels()
        self.sec = 0
        self.sub = 0
        self.subsub = 0
        self.runin = None
        self.wide = False
        self._page()
        self._styles()

    def _page(self):
        s = self.doc.sections[0]
        s.page_width, s.page_height = Inches(8.5), Inches(11)
        s.left_margin = s.right_margin = Inches(0.75)
        s.top_margin, s.bottom_margin = Inches(0.75), Inches(1.0)
        s.header_distance = s.footer_distance = Inches(0.4)

    def _styles(self):
        st = self.doc.styles
        n = st['Normal']
        n.font.name = FONT
        n._element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        n.font.size = Pt(10)
        n.paragraph_format.space_after = Pt(0)
        n.paragraph_format.line_spacing = 1.0
        eq = st.add_style('IEEE Equation', WD_STYLE_TYPE.PARAGRAPH)
        eq.base_style = n
        eq.paragraph_format.space_before = Pt(3)
        eq.paragraph_format.space_after = Pt(3)
        eq.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for name in ('Heading 1', 'Heading 2'):
            h = st[name]
            h.font.name = FONT
            rpr = h._element.get_or_add_rPr()
            rf = rpr.find(qn('w:rFonts'))
            if rf is None:
                rf = OxmlElement('w:rFonts')
                rpr.append(rf)
            for a in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
                rf.set(qn(a), FONT)
            for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
            h.font.size = Pt(10)
            h.font.bold = False
            h.font.color.rgb = RGBColor(0, 0, 0)
            h.paragraph_format.keep_with_next = True
            h.paragraph_format.line_spacing = 1.0

    # ------------------------------------------------------------------ layout switches
    def columns(self, n):
        if (n == 1) == self.wide:
            return
        new = self.doc.add_section(WD_SECTION.CONTINUOUS)
        p = self.doc.paragraphs[-1]                    # the paragraph that holds the closed section
        pfmt(p, line=1, after=0)
        set_cols(new._sectPr, n)
        self.wide = n == 1

    # ------------------------------------------------------------------ blocks
    def title_block(self, meta):
        set_cols(self.doc.sections[0]._sectPr, 1)
        self.wide = True
        p = self.doc.add_paragraph()
        pfmt(p, WD_ALIGN_PARAGRAPH.CENTER, after=12)
        add_text(p, meta['title'], size=24)
        p = self.doc.add_paragraph()
        pfmt(p, WD_ALIGN_PARAGRAPH.CENTER, after=1)
        add_text(p, meta['author'], size=11)
        for line in meta.get('affil', []):
            p = self.doc.add_paragraph()
            pfmt(p, WD_ALIGN_PARAGRAPH.CENTER, after=0)
            add_text(p, line, size=10, italic=True)
        if meta.get('email'):
            p = self.doc.add_paragraph()
            pfmt(p, WD_ALIGN_PARAGRAPH.CENTER, after=14)
            add_text(p, meta['email'], size=10)
        self.columns(2)

    def abstract(self, text, keywords):
        p = self.doc.add_paragraph()
        pfmt(p, after=6)
        r = p.add_run('Abstract\u2014')
        run_font(r, size=9, bold=True, italic=True)
        add_text(p, expand(text, self.L), size=9, bold=True)
        p = self.doc.add_paragraph()
        pfmt(p, after=8)
        r = p.add_run('Index Terms\u2014')
        run_font(r, size=9, bold=True, italic=True)
        add_text(p, keywords, size=9, bold=True)

    def heading(self, level, text, label=None):
        if level == 1:
            self.sec += 1
            self.sub = self.subsub = 0
            numbered = not text.startswith('*')
            text = text.lstrip('*')
            p = self.doc.add_paragraph(style='Heading 1')
            pfmt(p, WD_ALIGN_PARAGRAPH.CENTER, before=8, after=4, keep=True)
            add_text(p, ('%s. ' % ROMAN[self.sec - 1] if numbered else '') + text, size=10, small_caps=True)
            if not numbered:
                self.sec -= 1
            if label:
                self.L.map['sec:' + label] = ROMAN[self.sec - 1]
        elif level == 2:
            self.sub += 1
            self.subsub = 0
            letter = chr(ord('A') + self.sub - 1)
            p = self.doc.add_paragraph(style='Heading 2')
            pfmt(p, WD_ALIGN_PARAGRAPH.LEFT, before=6, after=3, keep=True)
            add_text(p, '%s. %s' % (letter, text), size=10, italic=True)
            if label:
                self.L.map['sec:' + label] = '%s-%s' % (ROMAN[self.sec - 1], letter)
        else:
            self.subsub += 1
            self.runin = '%d) %s: ' % (self.subsub, text)

    def paragraph(self, text, first=True):
        p = self.doc.add_paragraph()
        first = first and not text[:1].islower()            # text continuing after an equation is not indented
        pfmt(p, first=0.14 if first else 0)
        if self.runin:
            add_text(p, self.runin, italic=True)
            self.runin = None
        add_text(p, expand(text, self.L))
        return p

    def item(self, text, marker, level=0):
        p = self.doc.add_paragraph()
        ind = 0.14 + 0.16 * level
        pfmt(p, WD_ALIGN_PARAGRAPH.LEFT if 'http' in text else WD_ALIGN_PARAGRAPH.JUSTIFY, left=ind + 0.14, first=-0.14)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(ind + 0.14))
        r = p.add_run(marker + '\t')
        run_font(r, size=10)
        add_text(p, expand(text, self.L))

    def separate_tables(self):
        """Adjacent tables would merge into one; a hairline paragraph keeps a new table apart from a preceding one."""
        body = self.doc.element.body
        last = [e for e in body if e.tag != qn('w:sectPr')][-1:]
        if last and last[0].tag == qn('w:tbl'):
            pfmt(self.doc.add_paragraph(), line=1)

    def figure(self, label, file, caption, wide, width, pos='top'):
        n = self.L.n['fig'] + 1
        if wide:                                     # picture and caption in a borderless floating table
            self.separate_tables()
            t = self.doc.add_table(rows=2, cols=1)
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            table_fixed(t, [WIDEW])
            for row in t.rows:
                row_props(row)
                cell_margins(row.cells[0], t=0, b=0, l=0, r=0)
                cell_borders(row.cells[0])
            p, c = t.rows[0].cells[0].paragraphs[0], t.rows[1].cells[0].paragraphs[0]
            float_table(t, WIDEW, pos)
        else:
            p = self.doc.add_paragraph()
            c = None
        pfmt(p, WD_ALIGN_PARAGRAPH.CENTER, before=0 if wide else 6, after=2, keep=True)
        p.add_run().add_picture(str(FIGS / file), width=Inches(min(width or WIDEW, WIDEW - 0.02) if wide else (width or COLW)))
        if c is None:
            c = self.doc.add_paragraph()
        pfmt(c, WD_ALIGN_PARAGRAPH.JUSTIFY, after=0 if wide else 8)
        r = c.add_run('Fig. %d. ' % n)
        run_font(r, size=8)
        add_text(c, expand(caption, self.L), size=8)
        self.L.add('fig', label)

    def caption_table(self, label, caption):
        n = self.L.add('tab', label)
        p = self.doc.add_paragraph()
        pfmt(p, WD_ALIGN_PARAGRAPH.CENTER, before=8, after=0, keep=True)
        add_text(p, 'TABLE %s' % ROMAN[n - 1], size=8)
        p = self.doc.add_paragraph()
        pfmt(p, WD_ALIGN_PARAGRAPH.CENTER, after=3, keep=True)
        add_text(p, expand(caption, self.L), size=8, small_caps=True)

    def table(self, label, caption, wide, widths, header, rows, align=None, bold_cells=(), notes=None, size=8, pos='top'):
        cap = 2 if wide else 0                          # a floating table carries its caption in its first rows
        if wide:
            self.separate_tables()
            n = self.L.add('tab', label)
        else:
            self.caption_table(label, caption)
        total = WIDEW if wide else COLW
        widths = widths or [1] * len(header)
        widths = [total * w / sum(widths) for w in widths]
        align = align or ['l'] + ['r'] * (len(header) - 1)
        AL = {'l': WD_ALIGN_PARAGRAPH.LEFT, 'r': WD_ALIGN_PARAGRAPH.RIGHT, 'c': WD_ALIGN_PARAGRAPH.CENTER, 'j': WD_ALIGN_PARAGRAPH.LEFT}
        t = self.doc.add_table(rows=cap + 1 + len(rows), cols=len(header))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_fixed(t, widths)
        if wide:
            for k, (txt, sc) in enumerate((('TABLE %s' % ROMAN[n - 1], False), (expand(caption, self.L), True))):
                row = t.rows[k]
                row_props(row)
                c = row.cells[0].merge(row.cells[-1])
                cell_margins(c)
                cell_borders(c)
                p = c.paragraphs[0]
                pfmt(p, WD_ALIGN_PARAGRAPH.CENTER, after=3 if k else 0)
                add_text(p, txt, size=8, small_caps=sc)
            float_table(t, total, pos)
        for ri, row in enumerate([header] + rows):
            tr = t.rows[cap + ri]
            row_props(tr, header=ri == 0 and not wide)
            for ci, val in enumerate(row):
                c = tr.cells[ci]
                cell_margins(c)
                c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                edges = {}
                if ri == 0:
                    edges = {'top': 8, 'bottom': 4}
                if ri == len(rows):
                    edges['bottom'] = 8
                cell_borders(c, **edges)
                p = c.paragraphs[0]
                pfmt(p, AL[align[ci]] if ri else WD_ALIGN_PARAGRAPH.CENTER if align[ci] != 'l' else WD_ALIGN_PARAGRAPH.LEFT,
                     keep=ri < len(rows) and (len(rows) <= 8 or ri <= 1 or ri >= len(rows) - 2))  # short tables stay whole; long ones split without orphan rows
                add_text(p, expand(str(val), self.L), size=size, bold=(ri == 0) or ((ri - 1, ci) in bold_cells))
        if notes:
            p = self.doc.add_paragraph()
            pfmt(p, WD_ALIGN_PARAGRAPH.JUSTIFY, before=2, after=8)
            add_text(p, expand(notes, self.L), size=7)
        elif not wide:
            sp = self.doc.add_paragraph()
            pfmt(sp, after=4, line=6)

    def results(self, label, rq, metrics, caption, wide, methods=None):
        R = BD.RES[rq]
        ms = methods or R['methods']
        P = set(R.get('pareto') or [])
        short = {'answer_f1': 'F1', 'answer_em': 'EM', 'answerable_f1': 'F1 (ans.)', 'mrr': 'MRR', 'gold_coverage': 'GC', 'recall_at_5': 'R@5',
                 'source_f1': 'SF1', 'unnecessary_retrieval': 'WR', 'stopping_accuracy': 'Stop', 'required_source_miss': 'Miss',
                 'input_tokens': 'In tok.', 'output_tokens': 'Out tok.', 'total_tokens': 'Tokens', 'llm_calls': 'Calls', 'retrieval_calls': 'Search',
                 'latency': 'Lat. (s)', 'context_tokens': 'Ctx tok.', 'source_precision': 'SP', 'source_recall': 'SR'}
        header = ['Method'] + ['%s %s' % (short.get(k, k), '\u2191' if k in BD.HIGHER else '\u2193') for k in metrics]
        rows, bold = [], set()
        for j, k in enumerate(metrics):
            vals = [R['descriptive'][m].get(k) for m in ms]
            good = [v for v in vals if v is not None]
            if not good or max(good) - min(good) < 1e-12:
                continue
            best = max(good) if k in BD.HIGHER else min(good)
            for i, v in enumerate(vals):
                if v is not None and abs(v - best) < 1e-12:
                    bold.add((i, j + 1))
        for m in ms:
            row = [m + (' \u2605' if m in P else '')]
            for k in metrics:
                v = R['descriptive'][m].get(k)
                row.append(BD.fmt(v, BD.KIND.get(k, 'rate')).replace(' s', '') if v is not None else 'n/a')
            rows.append(row)
        widths = [1.15] + [1.0] * len(metrics)
        self.table(label, caption, wide, widths, header, rows, bold_cells=bold)

    def tests(self, label, rq, metric, caption, wide=False):
        R = BD.RES[rq]
        mk = BD.KIND.get(metric, 'rate')
        rows = []
        for t in R['tests'][metric]:
            rows.append(['%s \u2212 %s' % (t['a'], t['b']), BD.fmt(t['delta'], mk, sign=True).replace(' s', ''),
                         '[%s, %s]' % (BD.fmt(t['ci95'][0], mk).replace(' s', ''), BD.fmt(t['ci95'][1], mk).replace(' s', '')),
                         BD.fmt(t['p'], 'p'), BD.fmt(t['p_holm'], 'p') + ('*' if t['significant'] else '')])
        self.table(label, caption, wide, [1.5, 0.95, 1.45, 0.75, 0.85], ['Pair (A \u2212 B)', '\u0394', '95% CI', '*p*', '*p* (Holm)'], rows)

    def equation(self, label, umath):
        n = self.L.add('eq', label)
        p = self.doc.add_paragraph(style='IEEE Equation')
        p.add_run(umath.strip() + '#(%d)' % n)

    def algorithm(self, label, title, lines):
        n = self.L.add('alg', label)
        p = self.doc.add_paragraph()
        pfmt(p, WD_ALIGN_PARAGRAPH.LEFT, before=6, after=2, keep=True)
        pborder(p, 'top', 8, space=1)
        pborder(p, 'bottom', 4, space=1)
        r = p.add_run('Algorithm %d: ' % n)
        run_font(r, size=8.5, bold=True)
        add_text(p, expand(title, self.L), size=8.5)
        step = 0
        for i, raw in enumerate(lines):
            depth = len(raw) - len(raw.lstrip('>'))
            text = raw.lstrip('>').strip()
            q = self.doc.add_paragraph()
            ind = 0.24 + 0.15 * depth
            pfmt(q, WD_ALIGN_PARAGRAPH.LEFT, left=ind, first=-0.24 - 0.15 * depth if False else -ind + 0.0, keep=i < len(lines) - 1)
            q.paragraph_format.first_line_indent = Inches(-ind)
            q.paragraph_format.tab_stops.add_tab_stop(Inches(ind))
            if text.lower().startswith(('input:', 'output:', 'require:', 'ensure:')):
                head, _, rest = text.partition(':')
                r = q.add_run('\t')
                run_font(r, size=8)
                rr = q.add_run(head + ':')
                run_font(rr, size=8, bold=True)
                add_text(q, ' ' + expand(rest.strip(), self.L), size=8)
            else:
                step += 1
                r = q.add_run('%d:\t' % step)
                run_font(r, size=7.5)
                add_text(q, expand(text, self.L), size=8)
            if i == len(lines) - 1:
                pborder(q, 'bottom', 8, space=1)
        sp = self.doc.add_paragraph()
        pfmt(sp, after=2, line=6)

    def references(self):
        for i, k in enumerate(self.L.cites, 1):
            p = self.doc.add_paragraph()
            pfmt(p, WD_ALIGN_PARAGRAPH.LEFT, left=0.32, first=-0.32, after=1)
            p.paragraph_format.tab_stops.add_tab_stop(Inches(0.32))
            r = p.add_run('[%d]\t' % i)
            run_font(r, size=8)
            add_text(p, smart(REFS[k]), size=8)


# =============================================================================== parser
def split_row(raw):
    """Split a pipe-table row; '|' inside {{...}} placeholders or $...$ math, or written as '\\|', is kept."""
    cells, buf, depth, math, i = [], '', 0, False, 0
    while i < len(raw):
        if raw.startswith('{{', i):
            depth, buf, i = depth + 1, buf + '{{', i + 2
            continue
        if raw.startswith('}}', i) and depth:
            depth, buf, i = depth - 1, buf + '}}', i + 2
            continue
        ch = raw[i]
        if ch == '\\' and raw[i + 1:i + 2] == '|':
            buf, i = buf + '|', i + 2
            continue
        if ch == '$':
            math = not math
        if ch == '|' and not depth and not math:
            cells.append(buf.strip())
            buf = ''
        else:
            buf += ch
        i += 1
    cells.append(buf.strip())
    return cells


def blocks(lines):
    out, buf = [], []

    def flush():
        if buf:
            out.append(('p', ' '.join(x.strip() for x in buf)))
            buf.clear()
    for line in lines:
        m = re.match(r'^(\s*)- (.*)$', line)
        n = re.match(r'^(\s*)(\d+)\. (.*)$', line)
        if not line.strip():
            flush()
        elif m:
            flush()
            out.append(('b', m.group(2), len(m.group(1)) // 2))
        elif n:
            flush()
            out.append(('n', n.group(3), len(n.group(1)) // 2, n.group(2)))
        elif out and out[-1][0] in ('b', 'n') and line.startswith('  ') and not buf:
            o = out[-1]
            out[-1] = (o[0], o[1] + ' ' + line.strip()) + tuple(o[2:])
        else:
            buf.append(line)
    flush()
    return out


def prescan(lines, L):
    """Assign figure/table/equation/algorithm/section numbers before rendering so forward references resolve."""
    counts = {'fig': 0, 'tab': 0, 'eq': 0, 'alg': 0}
    sec = sub = 0
    for line in lines:
        s = line.strip()
        m = re.match(r'^@(fig|table|results|tests|eq|alg)\s+([\w\-]+)\s*\|', s)
        if m:
            kind = {'fig': 'fig', 'table': 'tab', 'results': 'tab', 'tests': 'tab', 'eq': 'eq', 'alg': 'alg'}[m.group(1)]
            counts[kind] += 1
            L.map['%s:%s' % (kind, m.group(2))] = counts[kind]
        h = re.match(r'^(#{1,2})\s+(\*?)(.*?)\s*(\{#sec:([\w\-]+)\})?$', s)
        if h and not s.startswith('###'):
            if len(h.group(1)) == 1:
                if not h.group(2):
                    sec += 1
                    sub = 0
                if h.group(5):
                    L.map['sec:' + h.group(5)] = ROMAN[sec - 1]
            else:
                sub += 1
                if h.group(5):
                    L.map['sec:' + h.group(5)] = '%s-%s' % (ROMAN[sec - 1], chr(ord('A') + sub - 1))


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
            elif b[0] == 'b':
                P.item(b[1], '\u2022', b[2])
            else:
                P.item(b[1], b[3] + ')', b[2])
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
                kw = lines[j + 1].strip()
                assert kw.startswith('@keywords')
                P.abstract(' '.join(body), kw[len('@keywords'):].strip())
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
                label, caption, kind = args[0], args[1], args[2]
                widths = [float(x) for x in args[3].split(',')] if len(args) > 3 and args[3] else None
                notes = args[4] if len(args) > 4 else None
                j = i + 1
                rows = []
                while j < len(lines) and lines[j].strip().startswith('|'):
                    raw = lines[j].strip()[1:]
                    raw = raw[:-1] if raw.endswith('|') else raw
                    rows.append(split_row(raw))
                    j += 1
                header, sep, body = rows[0], rows[1], rows[2:]
                align = ['r' if c.endswith(':') and not c.startswith(':') else ('c' if c.startswith(':') and c.endswith(':') else 'l') for c in sep]
                P.table(label, caption, kind == 'wide', widths, header, body, align=align, notes=notes)
                i = j
                continue
            if cmd == '@fig':
                P.figure(args[0], args[1], args[2], args[3] == 'wide', float(args[4]) if len(args) > 4 and args[4] else None,
                         args[5] if len(args) > 5 and args[5] else 'top')
            elif cmd == '@results':
                P.results(args[0], args[1], args[2].split(','), args[3], args[4] == 'wide', args[5].split(',') if len(args) > 5 else None)
            elif cmd == '@tests':
                P.tests(args[0], args[1], args[2], args[3])
            elif cmd == '@eq':
                P.equation(args[0], rest.split('|', 1)[1])
            elif cmd == '@refs':
                P.references()
            elif cmd == '@wide':
                P.columns(1)
            elif cmd == '@narrow':
                P.columns(2)
            else:
                raise ValueError('unknown directive ' + cmd)
            i += 1
            continue
        para.append(line)
        i += 1
    flush()
    for k, v in saved.items():                        # numbering must agree between the scan and the render
        if k.split(':')[0] in ('fig', 'tab', 'eq', 'alg'):
            assert P.L.map.get(k) == v, ('label numbering mismatch', k, v, P.L.map.get(k))
    unused = [k for k in REFS if k not in P.L.cites]
    P.doc.core_properties.title = meta.get('title', '')
    P.doc.core_properties.author = meta.get('author', '')
    P.doc.save(OUT)
    print('saved %s | figures %d, tables %d, equations %d, algorithms %d, references %d%s'
          % (OUT.name, P.L.n['fig'], P.L.n['tab'], P.L.n['eq'], P.L.n['alg'], len(P.L.cites),
             (' | unused references: ' + ', '.join(unused)) if unused else ''))


if __name__ == '__main__':
    build(HERE / 'paper.md')
