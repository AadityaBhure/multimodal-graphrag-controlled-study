"""Reusable presentation components. All data text is HTML-escaped; numbers are formatted by showcase.lib.fmt."""
from html import escape
import streamlit as st
from showcase.lib.fmt import fmt, metric as fmt_metric, kind_of

# One fixed colour per method role, identical in every study and chart.
METHOD_COLOR = {'B0': '#94a3b8', 'B1': '#334155', '01': '#2563eb', '02': '#16a34a', '03': '#c026d3', 'INT-1': '#7c3aed'}
SOURCE_COLOR = {'text': '#4f46e5', 'graph': '#0d9488', 'structured': '#ea580c'}
SOURCE_LABEL = {'text': 'Text', 'graph': 'Graph', 'structured': 'Structured'}


def method_color(m):
    return METHOD_COLOR.get(m if m == 'INT-1' else m.split('-')[-1], '#64748b')


LIGHT = ('--ink:#0f172a;--body:#1e293b;--muted:#475569;--faint:#64748b;--line:#e2e8f0;--line2:#cbd5e1;--soft:#f8fafc;--card:#ffffff;'
         '--blue:#1d4ed8;--blue-soft:#eff6ff;--blue-line:#bfdbfe;--note-bg:#f8fafc;--caution-bg:#fffbeb;--good-bg:#f0fdf4;--ok-line:#bbf7d0;'
         '--warn-line:#fde68a;--best-bg:#ecfdf5;--best-ink:#065f46;--hl-t:#e0e7ff;--hl-g:#ccfbf1;--hl-s:#ffedd5;--hover:#fafcff;--ok:#15803d;--no:#b91c1c;'
         '--b-control-bg:#e2e8f0;--b-control:#334155;--b-method-bg:#dbeafe;--b-method:#1e40af;--b-sig-bg:#dcfce7;--b-sig:#166534;--b-ns-bg:#f1f5f9;'
         '--b-ns:#64748b;--b-par-bg:#fef3c7;--b-par:#92400e;--b-rep-bg:#e0e7ff;--b-rep:#3730a3;--win-bg:#fffbeb;--win-line:#f59e0b')
DARK = ('--ink:#f1f5f9;--body:#e2e8f0;--muted:#cbd5e1;--faint:#94a3b8;--line:#334155;--line2:#475569;--soft:#1e293b;--card:#0f172a;'
        '--blue:#93c5fd;--blue-soft:#172554;--blue-line:#1e40af;--note-bg:#1e293b;--caution-bg:#3b2a07;--good-bg:#052e16;--ok-line:#166534;'
        '--warn-line:#a16207;--best-bg:#064e3b;--best-ink:#a7f3d0;--hl-t:#312e81;--hl-g:#134e4a;--hl-s:#7c2d12;--hover:#172036;--ok:#4ade80;--no:#f87171;'
        '--b-control-bg:#334155;--b-control:#e2e8f0;--b-method-bg:#1e3a8a;--b-method:#dbeafe;--b-sig-bg:#14532d;--b-sig:#bbf7d0;--b-ns-bg:#1e293b;'
        '--b-ns:#94a3b8;--b-par-bg:#78350f;--b-par:#fef3c7;--b-rep-bg:#312e81;--b-rep:#e0e7ff;--win-bg:#2a1f05;--win-line:#d97706')

CSS = """
<style>
:root{__VARS__}
.block-container{padding-top:3.4rem;padding-bottom:3rem;max-width:1240px}
h1,h2,h3{letter-spacing:-.01em}
.kicker{font-size:.8rem;font-weight:700;color:var(--blue);text-transform:uppercase;letter-spacing:.08em;margin-bottom:.1rem}
.intro{font-size:1.08rem;color:var(--muted);margin:.1rem 0 .6rem 0;line-height:1.5}
.chips{margin:.2rem 0 .4rem 0}
.chip{display:inline-block;border:1px solid var(--line2);border-radius:999px;padding:2px 10px;margin:2px 6px 2px 0;font-size:.8rem;background:var(--soft);color:var(--body)}
.chip.src{color:#fff;border:none;font-weight:600}
.toc{display:flex;flex-wrap:wrap;gap:8px;margin:.4rem 0 1rem 0;font-size:.86rem}
.toc a{border:1px solid var(--line);border-radius:8px;padding:4px 10px;text-decoration:none;color:var(--body);background:var(--card)}
.toc a:hover{background:var(--blue-soft);border-color:var(--blue-line)}
.toc span{color:var(--faint);align-self:center}
.card{border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:var(--card);height:100%;box-sizing:border-box}
.card h4{margin:0 0 4px 0;font-size:1.02rem;color:var(--ink)}
.card p{margin:.2rem 0;color:var(--muted);font-size:.92rem;line-height:1.45}
.card .meta{font-size:.78rem;color:var(--faint);margin-top:6px}
.card.tight{padding:10px 12px}
.badge{display:inline-block;border-radius:999px;padding:1px 9px;font-size:.72rem;font-weight:700;letter-spacing:.02em;vertical-align:middle;margin-left:6px}
.badge.control{background:var(--b-control-bg);color:var(--b-control)}.badge.method{background:var(--b-method-bg);color:var(--b-method)}
.badge.sig{background:var(--b-sig-bg);color:var(--b-sig)}.badge.ns{background:var(--b-ns-bg);color:var(--b-ns)}
.badge.pareto{background:var(--b-par-bg);color:var(--b-par)}.badge.live{background:var(--b-sig-bg);color:var(--b-sig)}.badge.replay{background:var(--b-rep-bg);color:var(--b-rep)}
.callout{border-left:4px solid var(--blue);background:var(--blue-soft);padding:10px 14px;border-radius:6px;margin:8px 0;font-size:.97rem;line-height:1.5;color:var(--body)}
.callout.note{border-color:var(--faint);background:var(--note-bg)}.callout.caution{border-color:#d97706;background:var(--caution-bg)}
.callout.good{border-color:#16a34a;background:var(--good-bg)}
.callout b.t{display:block;margin-bottom:2px}
.finding{display:flex;gap:12px;align-items:flex-start;border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:8px 0;background:var(--card)}
.finding .n{flex:0 0 28px;height:28px;border-radius:50%;background:#1d4ed8;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:.9rem}
.finding .x{font-size:1rem;line-height:1.5;color:var(--body)}
.flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:0;margin:6px 0 4px 0}
.flow .s{border:1.5px solid var(--line2);border-radius:10px;padding:8px 10px;background:var(--card);max-width:230px;font-size:.86rem;line-height:1.35;color:var(--body)}
.flow .s b{display:block;font-size:.72rem;color:var(--blue);letter-spacing:.06em;text-transform:uppercase;margin-bottom:2px}
.flow .a{align-self:center;color:var(--faint);padding:0 6px;font-size:1.1rem}
.pipe{display:flex;flex-wrap:nowrap;align-items:stretch;gap:0;margin:10px 0}
.pipe .s{border:1.5px solid var(--line2);border-radius:12px;padding:10px 10px;background:var(--card);flex:1 1 0;min-width:0;text-align:center;font-size:.9rem;line-height:1.3;color:var(--body)}
@media (max-width:760px){.pipe{flex-wrap:wrap}.pipe .s{flex:1 1 40%}}
.pipe .s.rq{border-color:#2563eb;background:var(--blue-soft)}
.pipe .s small{display:block;color:var(--faint);font-size:.75rem;margin-top:3px}
.pipe .s .tag{display:inline-block;background:#1d4ed8;color:#fff;border-radius:6px;font-size:.7rem;font-weight:700;padding:0 6px;margin-bottom:3px}
.pipe .a{align-self:center;color:var(--faint);padding:0 5px;font-size:1.2rem}
table.sc{border-collapse:separate;border-spacing:0;width:100%;font-size:.9rem;margin:4px 0 6px 0}
table.sc th{background:var(--soft);color:var(--body);font-weight:700;text-align:right;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
table.sc th:first-child,table.sc td:first-child{text-align:left}
table.sc td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums;color:var(--body)}
table.sc tr:hover td{background:var(--hover)}
table.sc td.best{font-weight:800;color:var(--best-ink);background:var(--best-bg)}
table.sc .dir{color:var(--faint);font-weight:400;font-size:.75rem}
table.sc .i{cursor:help;color:var(--faint);font-weight:400}
.swatch{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:7px;vertical-align:baseline}
.kpi{border:1px solid var(--line);border-radius:12px;padding:10px 14px;background:var(--soft);height:100%;box-sizing:border-box}
.kpi .v{font-size:1.5rem;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums}
.kpi .l{font-size:.76rem;color:var(--faint);text-transform:uppercase;letter-spacing:.05em}
.kpi .d{font-size:.82rem;color:var(--muted)}
.answer{border:1.5px solid var(--ok-line);background:var(--good-bg);border-radius:12px;padding:10px 14px;margin:6px 0;color:var(--body)}
.answer.empty{border-color:var(--warn-line);background:var(--caution-bg)}
.answer ul{margin:4px 0 2px 18px;padding:0}.answer li{margin:2px 0}
.ok{color:var(--ok);font-weight:700}.no{color:var(--no);font-weight:700}
.q{border-left:4px solid var(--faint);background:var(--note-bg);padding:10px 14px;border-radius:6px;font-size:1.02rem;line-height:1.55;color:var(--body)}
.q .t{background:var(--hl-t);border-radius:4px;padding:0 3px}.q .g{background:var(--hl-g);border-radius:4px;padding:0 3px}.q .st{background:var(--hl-s);border-radius:4px;padding:0 3px}
.tl{border-left:2px solid var(--line2);margin:6px 0 6px 10px;padding-left:16px}
.tl .e{position:relative;margin:0 0 10px 0;font-size:.92rem;line-height:1.45;color:var(--body)}
.tl .e:before{content:attr(data-i);position:absolute;left:-29px;top:0;width:22px;height:22px;border-radius:50%;background:var(--card);border:2px solid var(--line2);font-size:.8rem;display:flex;align-items:center;justify-content:center}
.tl .e .h{font-weight:700}.tl .e .m{color:var(--faint);font-size:.82rem}
.tl .e code{font-size:.8rem;white-space:pre-wrap;word-break:break-word}
.small{font-size:.84rem;color:var(--muted)}
.winner{display:flex;gap:16px;align-items:flex-start;border:2px solid var(--win-line);background:var(--win-bg);border-radius:14px;padding:14px 18px;margin:10px 0}
.winner .cup{font-size:2.2rem;line-height:1}
.winner h3{margin:0 0 4px 0;padding:0;font-size:1.35rem;color:var(--ink)}
.winner p{margin:0;color:var(--body);font-size:1rem;line-height:1.5}
.badge.win{background:var(--win-line);color:#fff}
.sit{border:1px solid var(--line);border-left:4px solid var(--blue);border-radius:10px;padding:10px 14px;background:var(--card);height:100%;box-sizing:border-box}
.sit .w{font-size:.78rem;font-weight:700;color:var(--faint);text-transform:uppercase;letter-spacing:.05em}
.sit h4{margin:2px 0 4px 0;font-size:1.02rem;color:var(--ink)}
.sit p{margin:0;color:var(--body);font-size:.92rem;line-height:1.45}
</style>
"""

PRESENT_CSS = """
<style>
html{font-size:18px}
.block-container{max-width:1380px;padding-top:1.2rem}
header[data-testid="stHeader"]{display:none}
</style>
"""


def dark():
    """Dark styling only when the app really is dark: a configured theme (launch.py, container) decides; without one,
    the browser's theme does (hosts that start the app without the launcher)."""
    try:
        base = st.get_option('theme.base')
        if base in ('light', 'dark'):
            return base == 'dark'
        return getattr(st.context.theme, 'type', None) == 'dark'
    except Exception:          # no browser context (tests, bare mode)
        return False


def ink():
    return '#e2e8f0' if dark() else '#0f172a'


def inject_css(presenting=False):
    st.markdown(CSS.replace('__VARS__', DARK if dark() else LIGHT) + (PRESENT_CSS if presenting else ''), unsafe_allow_html=True)


def e(x):
    return escape('' if x is None else str(x))


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def page_header(kicker, title, intro=None, chips=()):
    html('<div class="kicker">%s</div>' % e(kicker))
    st.title(title, anchor=False)
    if intro:
        html('<div class="intro">%s</div>' % e(intro))
    if chips:
        html('<div class="chips">%s</div>' % ''.join('<span class="chip">%s</span>' % e(c) for c in chips))


def toc(items):
    """items: [(anchor, label)] -> an 'On this page' strip with in-page links."""
    html('<div class="toc"><span>On this page:</span>%s</div>' % ''.join('<a href="#%s" target="_self">%s</a>' % (a, e(t)) for a, t in items))


def section(title, anchor, caption=None):
    st.header(title, anchor=anchor, divider='gray')
    if caption:
        st.caption(caption)


def callout(text, kind='finding', title=None, raw=False):
    body = text if raw else e(text)
    html('<div class="callout %s">%s%s</div>' % ('' if kind == 'finding' else kind, '<b class="t">%s</b>' % e(title) if title else '', body))


def findings(texts):
    html(''.join('<div class="finding"><div class="n">%d</div><div class="x">%s</div></div>' % (i, e(t)) for i, t in enumerate(texts, 1)))


def chips(items, colors=None):
    out = []
    for it in items:
        c = (colors or {}).get(it)
        out.append('<span class="chip src" style="background:%s">%s</span>' % (c, e(SOURCE_LABEL.get(it, it))) if c else '<span class="chip">%s</span>' % e(it))
    return ''.join(out)


def source_chips(sources):
    return chips(list(sources or []), SOURCE_COLOR) if sources else '<span class="chip">none</span>'


def badge(text, kind):
    return '<span class="badge %s">%s</span>' % (kind, e(text))


def kpi(label, value, detail=None):
    html('<div class="kpi"><div class="l">%s</div><div class="v">%s</div>%s</div>' % (e(label), e(value), '<div class="d">%s</div>' % e(detail) if detail else ''))


def flow(steps, label='Step'):
    parts = ['<div class="s"><b>%s %d</b>%s</div>' % (label, i, e(s)) for i, s in enumerate(steps, 1)]
    html('<div class="flow">%s</div>' % '<div class="a">&#10140;</div>'.join(parts))


def method_card(mid, m, pareto=False):
    kind = m.get('kind', 'method')
    head = '<span class="swatch" style="background:%s"></span>%s · %s%s%s' % (method_color(mid), e(mid), e(m['name']),
                                                                            badge('control' if kind == 'control' else 'method', kind),
                                                                            badge('★ Pareto', 'pareto') if pareto else '')
    meta = ('Inspired by %s. ' % e(m['inspired_by']) if m.get('inspired_by') else '') + e(m.get('cost', ''))
    html('<div class="card"><h4>%s</h4><p>%s</p><div class="meta">%s</div></div>' % (head, e(m['one_line']), meta))


def scorecard(methods, desc, columns, metrics_text, pareto=(), names=None):
    """HTML table: rows = methods, columns = [(metric, header)]. The best value per column is highlighted
    (direction from the metric definitions); a header tooltip carries the plain-language definition."""
    best = {}
    for k, _ in columns:
        vals = [desc[m].get(k) for m in methods if desc[m].get(k) is not None]
        d = (metrics_text.get(k) or {}).get('direction')
        if vals and d in ('higher', 'lower') and len(set(round(v, 9) for v in vals)) > 1:
            best[k] = max(vals) if d == 'higher' else min(vals)
    head = ''.join('<th title="%s">%s <span class="i">ⓘ</span><br><span class="dir">%s</span></th>'
                   % (e((metrics_text.get(k) or {}).get('plain', '')), e(h), {'higher': '↑ higher is better', 'lower': '↓ lower is better'}.get((metrics_text.get(k) or {}).get('direction'), ''))
                   for k, h in columns)
    rows = []
    for m in methods:
        cells = []
        for k, _ in columns:
            v = desc[m].get(k)
            cls = ' class="best"' if k in best and v is not None and abs(v - best[k]) < 1e-9 else ''
            cells.append('<td%s>%s</td>' % (cls, e(fmt_metric(v, k))))
        label = '<span class="swatch" style="background:%s"></span><b>%s</b> %s%s' % (method_color(m), e(m), e((names or {}).get(m, '')),
                                                                                    ' ' + badge('★ Pareto', 'pareto') if m in pareto else '')
        rows.append('<tr><td>%s</td>%s</tr>' % (label, ''.join(cells)))
    html('<table class="sc"><thead><tr><th>Method</th>%s</tr></thead><tbody>%s</tbody></table>' % (head, ''.join(rows)))


def tests_table(rows, metric, names=None):
    """Paired tests: one row per pair (A vs B): mean difference A - B, 95 % interval, p, Holm p, verdict."""
    out = []
    for t in rows:
        ci = t.get('ci95')
        ci_s = '[%s, %s]' % (fmt_metric(ci[0], metric, sign=True), fmt_metric(ci[1], metric, sign=True)) if ci else '—'
        verdict = badge('significant', 'sig') if t.get('significant') else badge('not significant', 'ns')
        out.append('<tr><td><b>%s</b> vs <b>%s</b></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                   % (e(t['a']), e(t['b']), e(fmt_metric(t['delta'], metric, sign=True)), e(ci_s), e(fmt(t.get('p'), 'p')), e(fmt(t.get('p_holm'), 'p')), verdict))
    html('<table class="sc"><thead><tr><th>Pair (A vs B)</th><th title="Average of A minus B over the same questions">Mean difference A − B</th>'
         '<th title="Family-clustered bootstrap, 10,000 resamples, seed 42">95 %% interval</th><th title="Exact sign-flip test over families">p</th>'
         '<th title="Holm-adjusted over all pairs tested on this metric">adjusted p (Holm)</th><th>Verdict</th></tr></thead><tbody>%s</tbody></table>' % ''.join(out))


def answer_box(answer_ids, gold, title_of, explanation=None, gold_seen=None, gold_retrieved=None):
    """What the strategy returned against the correct answer. An empty answer says where the correct papers were lost:
    never retrieved, retrieved but left out of the model's context, or seen by the model and rejected."""
    a, g = list(answer_ids or []), set(gold or [])
    plural = lambda n, w: '%d %s%s' % (n, w, '' if n == 1 else 's')
    them = 'it' if len(g) == 1 else 'them'
    if not a:
        if not g:
            html('<div class="answer"><b>Returned: no paper.</b> <span class="ok">✔ Correct</span> — no paper satisfies this question.</div>')
        elif gold_retrieved == 0:
            html('<div class="answer empty"><b>Returned: no paper.</b> The retrievers did not return the correct %s, so the model never saw %s '
                 'and could not answer.</div>' % ('paper' if len(g) == 1 else 'papers', them))
        elif gold_seen == 0:
            html('<div class="answer empty"><b>Returned: no paper.</b> The retrievers found %s, but this strategy left %s out of the '
                 'model’s context.</div>' % ('the correct paper' if len(g) == 1 else '%d of the %s' % (gold_retrieved or 0, plural(len(g), 'correct paper')), them))
        elif gold_seen:
            html('<div class="answer empty"><b>Returned: no paper.</b> %s reached the model, but it judged that no paper met every '
                 'condition.</div>' % ('The correct paper' if len(g) == 1 else '%d of the %s' % (gold_seen, plural(len(g), 'correct paper'))))
        else:
            html('<div class="answer empty"><b>Returned: no paper.</b> The correct answer has %s.</div>' % plural(len(g), 'paper'))
    else:
        hits = sum(i in g for i in a)
        items = ''.join('<li><span class="%s">%s</span> %s <span class="small">stark:%s</span></li>'
                        % ('ok' if i in g else 'no', '✔' if i in g else '✘', e(title_of(i) or 'title unavailable'), i) for i in a)
        wrong = len(a) - hits
        if not g:
            summary = 'but no paper satisfies this question'
        elif set(a) == g:
            summary = 'exactly the correct answer'
        else:
            summary = '%d correct%s%s' % (hits, ', %d wrong' % wrong if wrong else '', '; the full answer has %s' % plural(len(g), 'paper') if hits < len(g) else '')
        html('<div class="answer%s"><b>Returned %s: %s</b> (✔ = correct)<ul>%s</ul></div>' % ('' if hits else ' empty', plural(len(a), 'paper'), summary, items))
    if explanation:
        st.caption('Model’s stated reason: ' + str(explanation))


def gold_box(gold, title_of, limit=12):
    g = list(gold or [])
    if not g:
        html('<div class="answer empty"><b>Correct answer: no paper</b> (an unanswerable variant — the right response is an empty answer).</div>')
        return
    items = ''.join('<li>%s <span class="small">stark:%s</span></li>' % (e(title_of(i) or 'title unavailable'), i) for i in g[:limit])
    more = '<div class="small">… and %d more</div>' % (len(g) - limit) if len(g) > limit else ''
    html('<div class="answer"><b>Correct answer: %d paper%s</b><ul>%s</ul>%s</div>' % (len(g), '' if len(g) == 1 else 's', items, more))


def nav_footer(prev=None, next_=None):
    c1, c2 = st.columns(2)
    if prev:
        c1.page_link(prev[0], label='← ' + prev[1])
    if next_:
        c2.page_link(next_[0], label=next_[1] + ' →')


def winner_card(kicker, title, text):
    html('<div class="winner"><div class="cup">🏆</div><div><div class="kicker">%s</div><h3>%s</h3><p>%s</p></div></div>' % (e(kicker), e(title), e(text)))


def situation_card(when, title, text, color):
    html('<div class="sit" style="border-left-color:%s"><div class="w">%s</div><h4>%s</h4><p>%s</p></div>' % (color, e(when), e(title), e(text)))


def ranking_table(overall, desc, metrics_text, names=None):
    """Overall-performance ranking: rank (and value) on each measure, rank total and scaled score; winner first."""
    axes = overall['axes']
    head = ''.join('<th title="%s">%s <span class="i">ⓘ</span><br><span class="dir">rank (value) · %s</span></th>'
                   % (e((metrics_text.get(a['metric']) or {}).get('plain', '')), e((metrics_text.get(a['metric']) or {}).get('name', a['metric'])),
                      '↑ better' if a['direction'] == 'higher' else '↓ better') for a in axes)
    rows = []
    for pos, m in enumerate(overall['order'], 1):
        cells = ''.join('<td><b>%s</b> <span class="dir">(%s)</span></td>' % (e(fmt(overall['ranks'][m][a['metric']], 'rank')), e(fmt_metric(desc[m].get(a['metric']), a['metric'])))
                        for a in axes)
        win = m == overall['winner']
        label = '<span class="swatch" style="background:%s"></span><b>%s</b> %s%s' % (method_color(m), e(m), e((names or {}).get(m, '')),
                                                                                    ' ' + badge('🏆 overall winner', 'win') if win else '')
        rows.append('<tr><td>%d</td><td>%s</td>%s<td%s><b>%s</b></td><td>%s</td></tr>' % (
            pos, label, cells, ' class="best"' if win else '', e(fmt(overall['total'][m], 'rank')), e(fmt(overall['scaled'][m], 'rate'))))
    html('<table class="sc"><thead><tr><th>#</th><th>Method</th>%s<th title="Sum of the ranks; lower is better">Rank total<br><span class="dir">↓ better</span></th>'
         '<th title="Mean of the measures scaled to 0-1 (1 = best on that measure); a check on the rank total">Scaled score<br><span class="dir">↑ better</span></th>'
         '</tr></thead><tbody>%s</tbody></table>' % (head, ''.join(rows)))
