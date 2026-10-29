"""Build the project documentation (.docx) from the content files in content/.

Content syntax (one directive or block per line):
    #! Part title            part divider (Heading 1, new page)
    #* Title                 unnumbered chapter (Heading 2, new page)
    # Title                  numbered chapter (Heading 2, new page); in appendices "#A Title" gives Appendix A
    ## / ### Title           numbered section / subsection;  #### Title  unnumbered minor heading
    - item / 1. item         bullet (indent 2 spaces per level) / numbered item
    Table: caption {w=1.2,1,1}  followed by a pipe table (second row = alignment)
    @figure path | caption | width      @screen name | caption | width      @screencrop name x0,y0,x1,y1 | caption | width
    @callout kind | title ... @end      @code ... @end      @table kind args | caption      @pagebreak  @toc  @lof  @lot
Placeholders {{KEY}} bind numbers to the frozen results (see resolve()).
"""
import json
import re
import sys
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

from PIL import Image
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, Inches, RGBColor, Emu

BUILD = Path(__file__).resolve().parent
DOCDIR = BUILD.parent
ROOT = BUILD.parents[2]
OUTFILE = DOCDIR / 'Multi-Modal_GraphRAG_Project_Documentation.docx'
IMGTMP = BUILD / '_doc_images'
IMGTMP.mkdir(exist_ok=True)

RES = json.loads((ROOT / 'showcase/bundle/results.json').read_text(encoding='utf-8'))
MAN = json.loads((ROOT / 'showcase/bundle/manifest.json').read_text(encoding='utf-8'))

INK, BODY, MUTED, FAINT, LINE = '0F172A', '1E293B', '475569', '64748B', 'CBD5E1'
BLUE, BLUE_SOFT = '1D4ED8', 'EFF6FF'
TEXT_W = 6.69          # inches between the margins (A4, 2.0 cm side margins)
MAX_H = 8.9            # tallest image (inches) that still leaves room for its caption


# ======================================================================= numbers
def rnd(x, nd):
    v = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)
    return v + 0


def fnum(x, nd=3, sign=False):
    v = rnd(x, nd)
    s = format(v, ',.%df' % nd)
    if v == 0:
        s = s.lstrip('-')
    s = s.replace('-', '−')
    if sign and v > 0:
        s = '+' + s
    return s


KIND = {'answer_f1': 'rate', 'answer_em': 'rate', 'answerable_f1': 'rate', 'mrr': 'rate', 'gold_coverage': 'rate', 'recall_at_5': 'rate',
        'source_f1': 'rate', 'source_precision': 'rate', 'source_recall': 'rate', 'source_exact': 'rate', 'unnecessary_retrieval': 'rate',
        'stopping_accuracy': 'rate', 'required_source_miss': 'rate', 'premature_stop': 'rate', 'over_retrieval': 'rate', 'max_step_exhaustion': 'rate',
        'precision': 'rate', 'recall': 'rate', 'answerability_correctness': 'rate', 'context_reduction': 'rate', 'convergence': 'rate',
        'coverage_text': 'rate', 'coverage_graph': 'rate', 'coverage_structured': 'rate', 'fallback': 'rate',
        'input_tokens': 'tokens', 'output_tokens': 'tokens', 'total_tokens': 'tokens', 'context_tokens': 'tokens', 'context_characters': 'tokens',
        'selected_graph_nodes': 'calls', 'selected_graph_edges': 'calls',
        'latency': 'ms', 'cm_ms': 'ms', 'generation_ms': 'ms', 'llm_calls': 'calls', 'retrieval_calls': 'calls'}
NAME = {'answer_f1': 'Answer F1', 'answer_em': 'Exact match', 'answerable_f1': 'F1 (answerable)', 'mrr': 'MRR', 'gold_coverage': 'Gold coverage',
        'recall_at_5': 'Recall@5', 'source_f1': 'Source F1', 'source_precision': 'Source precision', 'source_recall': 'Source recall',
        'source_exact': 'Exact source set', 'unnecessary_retrieval': 'Wasted retrieval', 'stopping_accuracy': 'Stopping acc.',
        'required_source_miss': 'Source miss', 'premature_stop': 'Premature stop', 'over_retrieval': 'Over-retrieval',
        'max_step_exhaustion': 'Step limit hit', 'precision': 'Precision', 'recall': 'Recall', 'answerability_correctness': 'Answerability',
        'input_tokens': 'Input tokens', 'output_tokens': 'Output tokens', 'total_tokens': 'Tokens', 'context_tokens': 'Context tokens',
        'context_characters': 'Context chars', 'latency': 'Latency', 'cm_ms': 'Context step time', 'generation_ms': 'Model time',
        'llm_calls': 'Model calls', 'retrieval_calls': 'Searches', 'context_reduction': 'Reduction vs B0', 'convergence': 'Converged',
        'selected_graph_nodes': 'Graph nodes kept', 'selected_graph_edges': 'Graph edges kept', 'coverage_text': 'Text kept',
        'coverage_graph': 'Graph kept', 'coverage_structured': 'Structured kept', 'fallback': 'Fallback'}
HIGHER = {'answer_f1', 'answer_em', 'answerable_f1', 'mrr', 'gold_coverage', 'recall_at_5', 'source_f1', 'source_precision', 'source_recall',
          'source_exact', 'stopping_accuracy', 'precision', 'recall', 'answerability_correctness', 'convergence'}


def fmt(v, kind, sign=False):
    if v is None:
        return 'n/a'
    if kind == 'rate':
        return fnum(v, 3, sign)
    if kind == 'tokens':
        return fnum(v, 0, sign)
    if kind == 'ms':
        return fnum(v / 1000., 1, sign) + ' s'
    if kind == 'calls':
        return fnum(v, 2, sign)
    if kind == 'p':
        return '< 0.001' if v < 0.0005 else fnum(v, 3)
    if kind == 'peq':
        return '< 0.001' if v < 0.0005 else '= ' + fnum(v, 3)
    if kind == 'int':
        return fnum(v, 0, sign)
    if kind == 'pct':
        return fnum(100 * v, 0, sign) + ' %'
    if kind == 'pct1':
        return fnum(100 * v, 1, sign) + ' %'
    if kind == 'r1':
        return fnum(v, 1, sign)
    if kind == 'r2':
        return fnum(v, 2, sign)
    if kind == 'r3':
        return fnum(v, 3, sign)
    if kind == 'rank':
        return ('%g' % v)
    return str(v)


def find_test(R, metric, a, b):
    for t in R['tests'][metric]:
        if t['a'] == a and t['b'] == b:
            return t, 1
        if t['a'] == b and t['b'] == a:
            return t, -1
    raise KeyError((metric, a, b))


def resolve(key):
    """Bind a placeholder to the frozen results. Forms (an optional |kind overrides the format):
    RQx.M.metric · RQx.test.metric.A~B.(delta|p|p_holm|ci|sig) · RQx.strata.dim.val.M.metric · RQx.n.dim.val ·
    RQx.overall.(winner|total.M|scaled.M|rank.M.axis|quality_first) · RQx.ratio.metric.A/B · RQx.diff.metric.A-B · RQx.max.metric ·
    RQx.min.metric · RQ2.support.CLASS · RQ3.stop.M.reason · RQ3.fail.M.label · RQ4.sel.KEY · RQx.cohort.(queries|families)"""
    kind = None
    if '|' in key:
        key, kind = key.split('|', 1)
    p = key.split('.')
    R = RES[p[0]]
    d = R.get('descriptive', {})
    if p[1] == 'test':
        metric, (a, b), field = p[2], p[3].split('~'), p[4]
        t, s = find_test(R, metric, a, b)
        mk = kind or KIND.get(metric, 'rate')
        if field == 'delta':
            return fmt(s * t['delta'], mk, sign=True)
        if field in ('p', 'p_holm'):
            return fmt(t[field], kind if kind in ('p', 'peq') else 'p')
        if field == 'ci':
            lo, hi = (t['ci95'] if s == 1 else [-t['ci95'][1], -t['ci95'][0]])
            return '[%s, %s]' % (fmt(lo, mk), fmt(hi, mk))
        if field == 'sig':
            return 'significant' if t['significant'] else 'not significant'
    if p[1] == 'strata':
        dim, val, m, metric = p[2], p[3], p[4], p[5]
        return fmt(R['strata'][dim][val][m][metric], kind or KIND.get(metric, 'rate'))
    if p[1] == 'n':
        return str(R['strata_n']['%s:%s' % (p[2], p[3])])
    if p[1] == 'cohort':
        return str(R['cohort'][p[2]])
    if p[1] == 'overall':
        o = R['overall']
        if p[2] in ('winner', 'winner_scaled', 'winner_quality_first'):
            return o[p[2]]
        if p[2] == 'total':
            return fmt(o['total'][p[3]], 'rank')
        if p[2] == 'scaled':
            return fnum(o['scaled'][p[3]], 3)
        if p[2] == 'rank':
            return fmt(o['ranks'][p[3]][p[4]], 'rank')
        if p[2] == 'order':
            return o['order'][int(p[3])]
    if p[1] == 'ratio':
        a, b = p[3].split('/')
        return fnum(d[a][p[2]] / d[b][p[2]], 1)
    if p[1] == 'diff':
        a, b = p[3].split(':')
        return fmt(d[a][p[2]] - d[b][p[2]], kind or KIND.get(p[2], 'rate'), sign=True)
    if p[1] in ('max', 'min'):
        vals = [d[m][p[2]] for m in R['methods'] if d[m].get(p[2]) is not None]
        return fmt(max(vals) if p[1] == 'max' else min(vals), kind or KIND.get(p[2], 'rate'))
    if p[1] == 'support':
        return str(R['supportability']['counts'][p[2]])
    if p[1] == 'stop':
        return str(R['stop_reasons'][p[2]].get(p[3], 0))
    if p[1] == 'fail':
        return str(R['failure_taxonomy'][p[2]].get(p[3], 0))
    if p[1] == 'sel':
        return R['selection'][p[2]]
    if p[1] == 'diag':
        v = R['method_diagnostics'][p[2]]
        for k in p[3:]:
            v = v[k]
        return fmt(v, kind or 'r2') if isinstance(v, float) else str(v)
    m, metric = p[1], p[2]
    v = d[m][metric]
    return fmt(v, kind or KIND.get(metric, 'rate'))


def bind(text):
    return re.sub(r'\{\{([^}]+)\}\}', lambda mm: resolve(mm.group(1).strip()), text)


# ======================================================================= docx helpers
def set_cell_shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill)
    tcPr.append(shd)


def set_cell_borders(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        spec = kw.get(edge)
        el = OxmlElement('w:%s' % edge)
        if spec is None:
            el.set(qn('w:val'), 'nil')
        else:
            sz, color = spec
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), str(sz))
            el.set(qn('w:space'), '0')
            el.set(qn('w:color'), color)
        b.append(el)
    tcPr.append(b)


def set_cell_margins(cell, top=60, bottom=60, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    m = OxmlElement('w:tcMar')
    for k, v in (('top', top), ('bottom', bottom), ('left', left), ('right', right)):
        el = OxmlElement('w:%s' % k)
        el.set(qn('w:w'), str(v))
        el.set(qn('w:type'), 'dxa')
        m.append(el)
    tcPr.append(m)


def table_borders(table, color=LINE, sz=4, inside=True):
    tblPr = table._tbl.tblPr
    b = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement('w:%s' % edge)
        if edge in ('left', 'right', 'insideV') and not inside:
            el.set(qn('w:val'), 'nil')
        else:
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), str(sz))
            el.set(qn('w:space'), '0')
            el.set(qn('w:color'), color)
        b.append(el)
    tblPr.append(b)


def fixed_layout(table, widths_in):
    tblPr = table._tbl.tblPr
    lay = OxmlElement('w:tblLayout')
    lay.set(qn('w:type'), 'fixed')
    tblPr.append(lay)
    table.autofit = False
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            cell.width = Inches(widths_in[i])
    grid = table._tbl.tblGrid
    for i, gc in enumerate(grid.findall(qn('w:gridCol'))):
        gc.set(qn('w:w'), str(int(widths_in[i] * 1440)))


def row_flags(row, header=False):
    trPr = row._tr.get_or_add_trPr()
    cs = OxmlElement('w:cantSplit')
    cs.set(qn('w:val'), 'true')
    trPr.append(cs)
    if header:
        h = OxmlElement('w:tblHeader')
        h.set(qn('w:val'), 'true')
        trPr.append(h)


def add_field(par, instr, placeholder='', bold=False, size=None, color=None):
    def run():
        r = par.add_run()
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = RGBColor.from_string(color)
        r.bold = bold
        return r
    r = run()
    f = OxmlElement('w:fldChar')
    f.set(qn('w:fldCharType'), 'begin')
    r._r.append(f)
    r = run()
    it = OxmlElement('w:instrText')
    it.set(qn('xml:space'), 'preserve')
    it.text = ' %s ' % instr
    r._r.append(it)
    r = run()
    f = OxmlElement('w:fldChar')
    f.set(qn('w:fldCharType'), 'separate')
    r._r.append(f)
    r = run()
    r.text = placeholder
    r = run()
    f = OxmlElement('w:fldChar')
    f.set(qn('w:fldCharType'), 'end')
    r._r.append(f)


INLINE = re.compile(r'(\*\*.+?\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))')


def add_inline(par, text, size=None, color=None, bold=False, italic=False, font=None):
    for tok in INLINE.split(text):
        if not tok:
            continue
        r_bold, r_italic, r_code = bold, italic, False
        if tok.startswith('**') and tok.endswith('**') and len(tok) > 4:
            tok, r_bold = tok[2:-2], True
        elif tok.startswith('`') and tok.endswith('`') and len(tok) > 2:
            tok, r_code = tok[1:-1], True
        elif tok.startswith('*') and tok.endswith('*') and len(tok) > 2:
            tok, r_italic = tok[1:-1], True
        run = par.add_run(tok)
        if r_bold:
            run.bold = True
        if r_italic:
            run.italic = True
        if r_code:
            run.font.name = 'Consolas'
            run._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), 'Consolas')
            run.font.size = Pt((size or 10.5) - 1)
            run.font.color.rgb = RGBColor.from_string('0F766E')
        else:
            if size:
                run.font.size = Pt(size)
            if font:
                run.font.name = font
        if color and not r_code:
            run.font.color.rgb = RGBColor.from_string(color)
    return par


# ======================================================================= document
class Builder:
    def __init__(self):
        self.doc = Document()
        self.fig = 0
        self.tab = 0
        self.ch = 0
        self.sec = 0
        self.sub = 0
        self.appendix = None
        self.figures, self.tables = [], []
        self._setup()

    # ------------------------------------------------------------------ styles and page
    def _setup(self):
        d = self.doc
        s = d.sections[0]
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)
        s.left_margin = s.right_margin = Cm(2.0)
        s.top_margin, s.bottom_margin = Cm(2.2), Cm(2.1)
        s.header_distance = s.footer_distance = Cm(1.0)
        st = d.styles
        n = st['Normal']
        n.font.name = 'Calibri'
        n._element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
        n.font.size = Pt(10.5)
        n.font.color.rgb = RGBColor.from_string(BODY)
        n.paragraph_format.space_after = Pt(6)
        n.paragraph_format.line_spacing = 1.12
        spec = {'Heading 1': (24, INK, 0, 14), 'Heading 2': (18, '1E3A8A', 0, 10), 'Heading 3': (13.5, INK, 14, 6),
                'Heading 4': (11.5, '1E3A8A', 10, 4), 'Heading 5': (10.5, MUTED, 8, 3), 'Title': (34, INK, 0, 6)}
        for name, (size, color, before, after) in spec.items():
            h = st[name]
            h.font.name = 'Calibri'
            rpr = h._element.get_or_add_rPr()
            rf = rpr.find(qn('w:rFonts'))
            if rf is None:
                rf = OxmlElement('w:rFonts')
                rpr.append(rf)
            for a in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
                rf.set(qn(a), 'Calibri')
            for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
            h.font.size = Pt(size)
            h.font.bold = name != 'Heading 5'
            h.font.italic = False
            h.font.color.rgb = RGBColor.from_string(color)
            pf = h.paragraph_format
            pf.space_before, pf.space_after = Pt(before), Pt(after)
            pf.keep_with_next = True
            pf.line_spacing = 1.0
        cap = st['Caption']
        cap.font.name = 'Calibri'
        cap.font.size = Pt(9)
        cap.font.bold = False
        cap.font.italic = False
        cap.font.color.rgb = RGBColor.from_string(MUTED)
        cap.paragraph_format.space_before = Pt(3)
        cap.paragraph_format.space_after = Pt(10)
        self._header_footer()

    def _header_footer(self):
        s = self.doc.sections[0]
        s.different_first_page_header_footer = True
        hp = s.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run('Multi-Modal GraphRAG · Complete project documentation')
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor.from_string(FAINT)
        fp = s.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run('Page ')
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor.from_string(FAINT)
        add_field(fp, 'PAGE', '1', size=8, color=FAINT)
        r = fp.add_run(' of ')
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor.from_string(FAINT)
        add_field(fp, 'NUMPAGES', '1', size=8, color=FAINT)

    # ------------------------------------------------------------------ blocks
    def para(self, text, style=None, align=None, size=None, color=None, bold=False, italic=False, before=None, after=None, keep=False, indent=None):
        p = self.doc.add_paragraph(style=style)
        add_inline(p, bind(text), size=size, color=color, bold=bold, italic=italic)
        if align:
            p.alignment = align
        pf = p.paragraph_format
        if before is not None:
            pf.space_before = Pt(before)
        if after is not None:
            pf.space_after = Pt(after)
        if keep:
            pf.keep_with_next = True
        if indent is not None:
            pf.left_indent = Inches(indent)
        return p

    def heading(self, level, text):
        if level == 'part':
            self.page_break()
            p = self.doc.add_paragraph(style='Heading 1')
            p.paragraph_format.space_before = Pt(170)
            add_inline(p, text)
            return p
        if level == 'unlisted':
            p = self.doc.add_paragraph()
            p.paragraph_format.page_break_before = True
            p.paragraph_format.space_after = Pt(10)
            add_inline(p, text, size=18, color='1E3A8A', bold=True)
            return p
        if level in ('chapter', 'plain', 'appendix'):
            if level == 'chapter':
                self.ch += 1
                label = '%d' % self.ch
            elif level == 'appendix':
                self.appendix = chr(ord('A') + (0 if self.appendix is None else ord(self.appendix) - ord('A') + 1))
                label = 'Appendix %s' % self.appendix
            else:
                label = None
            self.sec = self.sub = 0
            p = self.doc.add_paragraph(style='Heading 2')
            p.paragraph_format.page_break_before = True
            add_inline(p, ('%s  %s' % (label, text)) if label else text)
            self.cur_chapter = 'plain' if level == 'plain' else (self.appendix if level == 'appendix' else str(self.ch))
            return p
        if level == 'section':
            self.sec += 1
            self.sub = 0
            p = self.doc.add_paragraph(style='Heading 3')
            add_inline(p, '%s.%d  %s' % (self.cur_chapter, self.sec, text) if self.cur_chapter != 'plain' else text)
            return p
        if level == 'sub':
            self.sub += 1
            p = self.doc.add_paragraph(style='Heading 4')
            add_inline(p, '%s.%d.%d  %s' % (self.cur_chapter, self.sec, self.sub, text) if self.cur_chapter != 'plain' else text)
            return p
        p = self.doc.add_paragraph(style='Heading 5')
        add_inline(p, text)
        return p

    def bullet(self, text, level=0, numbered=None):
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        ind = 0.22 + 0.24 * level
        pf.left_indent = Inches(ind + 0.18)
        pf.first_line_indent = Inches(-0.18)
        pf.space_after = Pt(3)
        marker = ('%s.' % numbered) if numbered else ('•' if level == 0 else '–')
        r = p.add_run(marker + '\t')
        r.font.color.rgb = RGBColor.from_string(BLUE if not numbered else BODY)
        if numbered:
            r.bold = True
        tabs = pf.tab_stops
        tabs.add_tab_stop(Inches(ind + 0.18))
        add_inline(p, bind(text))
        return p

    def page_break(self):
        p = self.doc.add_paragraph()
        p.add_run().add_break(WD_BREAK.PAGE)
        p.paragraph_format.space_after = Pt(0)

    def caption(self, kind, text):
        if kind == 'Figure':
            self.fig += 1
            n = self.fig
            self.figures.append(text)
        else:
            self.tab += 1
            n = self.tab
            self.tables.append(text)
        p = self.doc.add_paragraph(style='Caption')
        r = p.add_run(kind + ' ')
        r.bold = True
        r.font.color.rgb = RGBColor.from_string(INK)
        add_field(p, 'SEQ %s \\* ARABIC' % kind, str(n), bold=True, color=INK)
        r = p.add_run('. ')
        r.bold = True
        r.font.color.rgb = RGBColor.from_string(INK)
        add_inline(p, bind(text), size=9, color=MUTED)
        if kind == 'Table':
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.space_before = Pt(8)
        return p

    def image(self, path, caption, width=None, border=False, crop=None):
        path = Path(path)
        img = Image.open(path).convert('RGB')
        if crop:
            img = img.crop(crop)
        if border:
            w, h = img.size
            b = Image.new('RGB', (w + 4, h + 4), (203, 213, 225))
            b.paste(img, (2, 2))
            img = b
        out = IMGTMP / (path.stem + ('_c' if crop else '') + ('_b' if border else '') + '.png')
        if border or crop or path.suffix.lower() != '.png':
            img.save(out, optimize=True)
        else:
            out = path
        w_px, h_px = img.size
        width = width or TEXT_W
        if width * h_px / w_px > MAX_H:
            width = MAX_H * w_px / h_px
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run()
        pic = run.add_picture(str(out), width=Inches(width))
        try:
            pic._inline.docPr.set('descr', re.sub(r'[*`]', '', bind(caption))[:500])
        except Exception:
            pass
        self.caption('Figure', caption)

    def callout(self, kind, title, lines):
        colors = {'note': ('64748B', 'F8FAFC'), 'key': ('1D4ED8', 'EFF6FF'), 'good': ('16A34A', 'F0FDF4'), 'caution': ('D97706', 'FFFBEB'),
                  'warn': ('DC2626', 'FEF2F2')}
        edge, fill = colors.get(kind, colors['note'])
        t = self.doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.rows[0].cells[0]
        set_cell_shade(c, fill)
        set_cell_borders(c, left=(24, edge))
        set_cell_margins(c, 90, 90, 160, 140)
        fixed_layout(t, [TEXT_W - 0.05])
        first = c.paragraphs[0]
        if title:
            add_inline(first, bind(title), bold=True, color=INK, size=10.5)
            first.paragraph_format.space_after = Pt(3)
            target = None
        else:
            target = first
        for kind_, text, level in self._blocks(lines):
            if kind_ == 'p':
                par = target if target is not None else c.add_paragraph()
                target = None
                add_inline(par, bind(text), size=10)
                par.paragraph_format.space_after = Pt(3)
            elif kind_ in ('b', 'n'):
                par = target if target is not None else c.add_paragraph()
                target = None
                ind = 0.18 + 0.22 * level
                par.paragraph_format.left_indent = Inches(ind + 0.16)
                par.paragraph_format.first_line_indent = Inches(-0.16)
                par.paragraph_format.space_after = Pt(2)
                par.paragraph_format.tab_stops.add_tab_stop(Inches(ind + 0.16))
                r = par.add_run(('•' if kind_ == 'b' else '%s.' % text[0]) + '\t')
                r.font.color.rgb = RGBColor.from_string(edge)
                add_inline(par, bind(text if kind_ == 'b' else text[1]), size=10)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def code(self, lines):
        t = self.doc.add_table(rows=1, cols=1)
        c = t.rows[0].cells[0]
        set_cell_shade(c, 'F8FAFC')
        set_cell_borders(c, top=(4, 'E2E8F0'), bottom=(4, 'E2E8F0'), left=(4, 'E2E8F0'), right=(4, 'E2E8F0'))
        set_cell_margins(c, 80, 80, 140, 140)
        fixed_layout(t, [TEXT_W - 0.05])
        par = c.paragraphs[0]
        for i, line in enumerate(lines):
            if i:
                par = c.add_paragraph()
            par.paragraph_format.space_after = Pt(0)
            par.paragraph_format.line_spacing = 1.0
            r = par.add_run(line if line else ' ')
            r.font.name = 'Consolas'
            r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), 'Consolas')
            r.font.size = Pt(8.3)
            r.font.color.rgb = RGBColor.from_string('0F172A')
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def table(self, caption, header, rows, widths=None, align=None, font=8.6, highlight_rows=(), first_bold=True):
        ncol = len(header)
        if widths is None:
            lens = [max([len(str(header[i]))] + [len(re.sub(r'[*`]', '', str(r[i]))) for r in rows]) for i in range(ncol)]
            lens = [min(max(l, 4), 60) for l in lens]
            tot = sum(lens)
            widths = [TEXT_W * l / tot for l in lens]
        else:
            tot = sum(widths)
            widths = [TEXT_W * w / tot for w in widths]
        align = align or (['l'] + ['r' if all(re.fullmatch(r'[−+\-]?[\d,.]+( s| %)?|n/a|–|\[.*\]', str(r[i]).strip() or '0') for r in rows)
                                  else 'l' for i in range(1, ncol)])
        if caption:
            self.caption('Table', caption)
        t = self.doc.add_table(rows=1 + len(rows), cols=ncol)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_borders(t, LINE, 4)
        fixed_layout(t, widths)
        AL = {'l': WD_ALIGN_PARAGRAPH.LEFT, 'r': WD_ALIGN_PARAGRAPH.RIGHT, 'c': WD_ALIGN_PARAGRAPH.CENTER}
        for i, htext in enumerate(header):
            c = t.rows[0].cells[i]
            set_cell_shade(c, '1E3A8A')
            set_cell_margins(c, 50, 50, 70, 70)
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = c.paragraphs[0]
            p.alignment = AL[align[i]]
            p.paragraph_format.space_after = Pt(0)
            add_inline(p, bind(str(htext)), size=font, color='FFFFFF', bold=True)
        row_flags(t.rows[0], header=True)
        for ri, row in enumerate(rows):
            tr = t.rows[ri + 1]
            row_flags(tr)
            for i, val in enumerate(row):
                c = tr.cells[i]
                set_cell_margins(c, 40, 40, 70, 70)
                c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                if ri in highlight_rows:
                    set_cell_shade(c, 'FEF9C3')
                elif ri % 2 == 1:
                    set_cell_shade(c, 'F8FAFC')
                p = c.paragraphs[0]
                p.alignment = AL[align[i]]
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                txt = bind(str(val))
                add_inline(p, txt, size=font, bold=(i == 0 and first_bold and ri not in ()), color=INK if i == 0 else BODY)
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(4)
        return t

    # ------------------------------------------------------------------ parsing helpers
    @staticmethod
    def _blocks(lines):
        """Group raw lines into ('p', text) paragraphs, ('b', text, level) bullets and ('n', (num, text), level) items."""
        out, buf = [], []
        def flush():
            if buf:
                out.append(('p', ' '.join(x.strip() for x in buf), 0))
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
                out.append(('n', (n.group(2), n.group(3)), len(n.group(1)) // 2))
            elif out and out[-1][0] in ('b', 'n') and line.startswith('  ') and not buf:
                k, t, lv = out[-1]
                out[-1] = (k, (t + ' ' + line.strip()) if k == 'b' else (t[0], t[1] + ' ' + line.strip()), lv)
            else:
                buf.append(line)
        flush()
        return out


# ======================================================================= data-driven tables
def methods_rows(rq, metrics, methods=None):
    R = RES[rq]
    ms = methods or R['methods']
    P = set(R.get('pareto') or [])
    rows = []
    for m in ms:
        row = [m + (' ★' if m in P else '')]
        for k in metrics:
            row.append(fmt(R['descriptive'][m].get(k), KIND.get(k, 'rate')))
        rows.append(row)
    return rows


def best_rows(rq, metrics, methods=None):
    """Indices of the best value per column (for bolding) are not marked; returned for completeness."""
    return []


def data_table(B, spec, caption):
    parts = spec.split()
    kind = parts[0]
    if kind == 'methods':
        rq, metrics = parts[1], parts[2].split(',')
        methods = parts[3].split(',') if len(parts) > 3 else None
        header = ['Method'] + ['%s %s' % (NAME.get(k, k), '↑' if k in HIGHER else '↓') for k in metrics]
        B.table(caption, header, methods_rows(rq, metrics, methods), widths=[1.15] + [1] * len(metrics))
    elif kind == 'tests':
        rq, metric = parts[1], parts[2]
        R = RES[rq]
        mk = KIND.get(metric, 'rate')
        rows = [['%s − %s' % (t['a'], t['b']), fmt(t['delta'], mk, sign=True), '[%s, %s]' % (fmt(t['ci95'][0], mk), fmt(t['ci95'][1], mk)),
                 fmt(t['p'], 'p'), fmt(t['p_holm'], 'p'), 'yes' if t['significant'] else 'no'] for t in R['tests'][metric]]
        B.table(caption, ['Pair (A − B)', 'Mean difference', '95 % interval', 'p (sign-flip)', 'p (Holm)', 'Significant'], rows,
                widths=[1.5, 1.1, 1.6, 0.9, 0.9, 0.9], align=['l', 'r', 'r', 'r', 'r', 'c'])
    elif kind == 'ranking':
        rq = parts[1]
        o = RES[rq]['overall']
        d = RES[rq]['descriptive']
        axes = [a['metric'] for a in o['axes']]
        rows = []
        for i, m in enumerate(o['order']):
            rows.append([m + ('  (winner)' if m == o['winner'] else '')] + ['%s (%s)' % (fmt(o['ranks'][m][a], 'rank'), fmt(d[m][a], KIND[a])) for a in axes]
                        + [fmt(o['total'][m], 'rank'), fnum(o['scaled'][m], 3)])
        header = ['Method'] + ['%s rank (value)' % NAME[a] for a in axes] + ['Rank total', 'Scaled score']
        B.table(caption, header, rows, widths=[1.35] + [1.05] * len(axes) + [0.7, 0.75], highlight_rows=[0],
                align=['l'] + ['r'] * (len(axes) + 2))
    elif kind == 'strata':
        rq, dim, metric = parts[1], parts[2], parts[3]
        R = RES[rq]
        order = {'modality': ['T', 'G', 'S', 'TG', 'TS', 'GS', 'TGS'], 'stress': ['normal', 'noisy', 'conflict', 'unanswerable'],
                 'support': ['FULLY_SUPPORTABLE', 'PARTIALLY_SUPPORTABLE', 'UNSUPPORTABLE']}[dim]
        vals = [v for v in order if v in R['strata'][dim]]
        label = {'FULLY_SUPPORTABLE': 'fully supportable', 'PARTIALLY_SUPPORTABLE': 'partially supportable', 'UNSUPPORTABLE': 'unsupportable',
                 'T': 'T (text)', 'G': 'G (graph)', 'S': 'S (structured)', 'TG': 'TG', 'TS': 'TS', 'GS': 'GS', 'TGS': 'TGS'}
        rows = [['%s (n=%s)' % (label.get(v, v), R['strata_n'].get('%s:%s' % (dim, v), '?'))] +
                [fmt(R['strata'][dim][v][m].get(metric), KIND.get(metric, 'rate')) for m in R['methods']] for v in vals]
        B.table(caption, ['Group'] + R['methods'], rows, widths=[1.6] + [1] * len(R['methods']))
    elif kind == 'stops':
        R = RES['RQ3']
        reasons = sorted({k for v in R['stop_reasons'].values() for k in v})
        rows = [[r.replace('_', ' ')] + [str(R['stop_reasons'][m].get(r, 0)) for m in R['methods']] for r in reasons]
        B.table(caption, ['Stop reason'] + R['methods'], rows, widths=[2.2] + [0.9] * 5)
    elif kind == 'failures':
        R = RES['RQ3']
        labels = sorted({k for v in R['failure_taxonomy'].values() for k in v}, key=lambda l: -sum(R['failure_taxonomy'][m].get(l, 0) for m in R['methods']))
        rows = [[l.replace('_', ' ')] + [str(R['failure_taxonomy'][m].get(l, 0)) for m in R['methods']] for l in labels]
        B.table(caption, ['Failure label'] + R['methods'], rows, widths=[2.4] + [0.85] * 5)
    elif kind == 'statuses':
        R = RES['RQ3']
        st = sorted({k for v in R['statuses'].values() for k in v})
        rows = [[s_.replace('_', ' ')] + [str(R['statuses'][m].get(s_, 0)) for m in R['methods']] for s_ in st]
        B.table(caption, ['Final status'] + R['methods'], rows, widths=[2.2] + [0.9] * 5)
    elif kind == 'records':
        rows = [['Part %s' % rq[-1], m, str(n)] for rq, ms in sorted(MAN['records'].items()) for m, n in ms.items()]
        B.table(caption, ['Study', 'Method', 'Run records'], rows, widths=[1, 1, 1])
    elif kind == 'bundle':
        rows = [[k, fnum(v['bytes'], 0), v['sha256'][:32] + '…'] for k, v in sorted(MAN['files'].items())]
        B.table(caption, ['File', 'Bytes', 'SHA-256 (first 32 hex digits)'], rows, widths=[1.6, 0.8, 3.2], font=8.2)
    elif kind == 'sources':
        rows = [[k, v[:32] + '…'] for k, v in sorted(MAN['sources'].items())]
        B.table(caption, ['Frozen source', 'SHA-256 (first 32 hex digits)'], rows, widths=[3.2, 2.6], font=8.2)
    else:
        raise ValueError(spec)


# ======================================================================= content parser
def build(files):
    B = Builder()
    for f in files:
        lines = f.read_text(encoding='utf-8').splitlines()
        i = 0
        para = []

        def flush():
            for kind, text, level in Builder._blocks(para):
                if kind == 'p':
                    B.para(text)
                elif kind == 'b':
                    B.bullet(text, level)
                else:
                    B.bullet(text[1], level, numbered=text[0])
            para.clear()

        while i < len(lines):
            line = lines[i]
            s = line.strip()
            if s.startswith('<!--'):
                while '-->' not in lines[i]:
                    i += 1
                i += 1
                continue
            if s.startswith('#'):
                flush()
                m = re.match(r'^(#!|#\*|#~|#A|####|###|##|#)\s+(.*)$', s)
                tag, text = m.group(1), m.group(2)
                B.heading({'#!': 'part', '#*': 'plain', '#~': 'unlisted', '#A': 'appendix', '#': 'chapter', '##': 'section', '###': 'sub',
                           '####': 'minor'}[tag], bind(text))
                i += 1
                continue
            if s.startswith('Table:'):
                flush()
                cap = s[6:].strip()
                widths = None
                mw = re.search(r'\{w=([\d.,]+)\}\s*$', cap)
                if mw:
                    widths = [float(x) for x in mw.group(1).split(',')]
                    cap = cap[:mw.start()].strip()
                i += 1
                rows = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    raw = lines[i].strip()
                    raw = raw[1:-1] if raw.endswith('|') and not raw.endswith('\\|') else raw[1:]
                    cells = re.split(r'(?<!\\)\|', raw)
                    rows.append([c.strip().replace('\\|', '|') for c in cells])
                    i += 1
                header, sep, body = rows[0], rows[1], rows[2:]
                align = ['r' if c.endswith(':') and not c.startswith(':') else ('c' if c.startswith(':') and c.endswith(':') else 'l') for c in sep]
                B.table(cap, header, body, widths=widths, align=align)
                continue
            if s.startswith('@'):
                flush()
                if s.startswith('@callout') or s.startswith('@code'):
                    block = []
                    j = i + 1
                    while lines[j].strip() != '@end':
                        block.append(lines[j])
                        j += 1
                    if s.startswith('@code'):
                        B.code(block)
                    else:
                        head = s[len('@callout'):].strip()
                        kind, _, title = head.partition('|')
                        B.callout(kind.strip(), title.strip(), block)
                    i = j + 1
                    continue
                cmd, _, rest = s.partition(' ')
                args = [a.strip() for a in rest.split('|')] if rest else []
                if cmd == '@figure':
                    B.image(BUILD.parent / args[0], args[1], float(args[2]) if len(args) > 2 and args[2] else None)
                elif cmd == '@screen':
                    B.image(BUILD.parent / 'screens' / (args[0] + '.png'), args[1], float(args[2]) if len(args) > 2 and args[2] else 6.4, border=True)
                elif cmd == '@screencrop':
                    name, box = args[0].split()
                    B.image(BUILD.parent / 'screens' / (name + '.png'), args[1], float(args[2]) if len(args) > 2 and args[2] else None, border=True,
                            crop=tuple(int(x) for x in box.split(',')))
                elif cmd == '@table':
                    data_table(B, args[0], args[1] if len(args) > 1 else '')
                elif cmd == '@pagebreak':
                    B.page_break()
                elif cmd == '@toc':
                    p = B.doc.add_paragraph()
                    add_field(p, 'TOC \\o "1-3" \\h \\z \\u', 'Right-click and choose Update Field to build the table of contents.')
                elif cmd == '@lof':
                    p = B.doc.add_paragraph()
                    add_field(p, 'TOC \\h \\z \\c "Figure"', 'Right-click and choose Update Field to build the list of figures.')
                elif cmd == '@lot':
                    p = B.doc.add_paragraph()
                    add_field(p, 'TOC \\h \\z \\c "Table"', 'Right-click and choose Update Field to build the list of tables.')
                elif cmd == '@titlepage':
                    titlepage(B)
                elif cmd == '@space':
                    B.doc.add_paragraph().paragraph_format.space_after = Pt(float(args[0]) if args else 6)
                else:
                    raise ValueError('unknown directive %s' % cmd)
                i += 1
                continue
            para.append(line)
            i += 1
        flush()
    return B


def titlepage(B):
    d = B.doc
    p = d.add_paragraph()
    p.paragraph_format.space_before = Pt(120)
    r = p.add_run('PROJECT DOCUMENTATION')
    r.font.size = Pt(11)
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(BLUE)
    p = d.add_paragraph(style='Title')
    p.add_run('Multi-Modal GraphRAG')
    p.paragraph_format.space_after = Pt(8)
    p = d.add_paragraph()
    r = p.add_run('Context management, cross-modal fusion and retrieval control for a language model that answers questions over text, '
                  'graph and structured views of a scientific corpus')
    r.font.size = Pt(15)
    r.font.color.rgb = RGBColor.from_string(MUTED)
    p.paragraph_format.space_after = Pt(36)
    rows = [('Author', 'Aaditya Bhure'), ('Date', '18 October 2026'), ('Version', '1.0 — complete record, from the first commit to the showcase application'),
            ('Repository state', 'commit 7e3cfa5 · showcase data bundle %s' % MAN['bundle_sha256'][:12]),
            ('Results status', 'Validation results on frozen, programmatically verified questions; the locked test set is out of scope')]
    t = d.add_table(rows=len(rows), cols=2)
    fixed_layout(t, [1.6, 5.0])
    for i, (k, v) in enumerate(rows):
        c0, c1 = t.rows[i].cells
        for c in (c0, c1):
            set_cell_borders(c, bottom=(4, 'E2E8F0'))
            set_cell_margins(c, 70, 70, 0, 80)
        add_inline(c0.paragraphs[0], k, size=9.5, color=FAINT, bold=True)
        add_inline(c1.paragraphs[0], v, size=10, color=INK)
        c0.paragraphs[0].paragraph_format.space_after = Pt(0)
        c1.paragraphs[0].paragraph_format.space_after = Pt(0)
    p = d.add_paragraph()
    p.paragraph_format.space_before = Pt(60)
    r = p.add_run('Every number about the studies in this document is read from the frozen analysis files through the checksummed showcase data bundle; '
                  'figures and tables are regenerated by the scripts in documentation/project_documentation/build.')
    r.font.size = Pt(9)
    r.italic = True
    r.font.color.rgb = RGBColor.from_string(FAINT)


if __name__ == '__main__':
    files = sorted((BUILD / 'content').glob('*.md'))
    B = build(files)
    B.doc.core_properties.title = 'Multi-Modal GraphRAG — Complete project documentation'
    B.doc.core_properties.author = 'Aaditya Bhure'
    B.doc.core_properties.subject = 'Controlled study of context management, cross-modal fusion and retrieval control'
    B.doc.save(OUTFILE)
    print('saved', OUTFILE, '| figures', B.fig, '| tables', B.tab, '| chapters', B.ch)
