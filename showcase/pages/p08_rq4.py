import pandas as pd
import streamlit as st
from showcase.lib import state, ui, explorer
from showcase.lib.content import findings as render_findings
from showcase.lib.fmt import fmt, metric as fmt_metric
from showcase.lib.study import COLUMNS, csv_bytes
from showcase.lib.ui import e, html, method_color

C, B = state.content(), state.bundle()
S, R, RES = C['rq4'], B.results['RQ4'], B.results
M = C['evaluation']['metrics']
sel = R['selection']
name_of = {**{m: v['name'] for m, v in C['rq3']['methods'].items()}, **{m: v['name'] for m, v in C['rq2']['methods'].items()},
           **{m: v['name'] for m, v in C['rq1']['methods'].items()}, 'INT-1': 'Combined system'}

ui.page_header('Part 4 of 4', 'Part 4 · Combined system', S['page_intro'], chips=[S['cohort'], '%d independent families' % R['cohort']['families']])
ui.toc([('choice', 'The three winners combined'), ('results', 'Results'), ('tests', 'Real differences?'), ('findings', 'Findings'),
        ('explore', 'Look inside one question'), ('scoreboard', 'Final scoreboard')])

ui.section('The three winners combined', 'choice', 'The combined system chains the overall winner of each part, in pipeline order.')
comb = R['combined']
boxes = []
for rq, part in (('RQ3', 'Retrieval control'), ('RQ1', 'Context management'), ('RQ2', 'Fusion')):
    o = RES[rq]['overall']; m = o['winner']; runner = o['order'][1]
    boxes.append('<div class="s rq" style="text-align:left"><span class="tag">Winner of Part %s</span><br><b><span class="swatch" style="background:%s"></span>%s · %s</b>'
                 '<small>%s · rank total %s (runner-up %s: %s)</small></div>' % (rq[-1], method_color(m), e(m), e(name_of.get(m, '')), e(part),
                                                                                e(fmt(o['total'][m], 'rank')), e(runner), e(fmt(o['total'][runner], 'rank'))))
html('<div class="pipe"><div class="s" style="flex:0 0 90px"><b>Question</b></div><div class="a">&#10140;</div>%s<div class="a">&#10140;</div>'
     '<div class="s" style="flex:0 0 90px"><b>Answer</b></div></div>' % '<div class="a">&#10140;</div>'.join(boxes))
if comb['matches_rq4']:
    ui.callout('The selection rule written down before any result was known (best answer F1 among the Pareto-optimal methods, with context management fixed '
               'to CM-B1 for cost) picked the same three components, so the system evaluated here is exactly the combination of the three winners.', 'good')
else:
    ui.callout('The pre-registered selection rule picked %s; the overall winners are %s.' % (' -> '.join(comb['rq4_pipeline']), comb['winners']), 'caution')
with st.expander('The pre-registered selection rule'):
    st.markdown(S['selection_rule'])

ui.section('Results', 'results', 'The combined system against searching everything (AR-B0) and the chosen policy on its own (AR-B1, recorded in Part 3) '
           'on the same %d questions.' % R['cohort']['queries'])
ui.scorecard(R['methods'], R['descriptive'], COLUMNS['RQ4'], M, names={m: name_of.get(m, '') for m in R['methods']})
df = pd.DataFrame([{'method': m, **{k: R['descriptive'][m].get(k) for k, _ in COLUMNS['RQ4']}} for m in R['methods']])
st.download_button('Download this table (CSV)', csv_bytes(df), file_name='rq4_results.csv', mime='text/csv', key='rq4_dl')

ui.section('Is any difference real?', 'tests', 'Same paired family test as in Parts 1–3, Holm-adjusted over the two comparisons.')
metrics = list(R['tests'])
k = st.pills('Tested metric', metrics, default='answer_f1', key='rq4_tm', format_func=lambda x: (M.get(x) or {}).get('name', x)) or 'answer_f1'
ui.tests_table(R['tests'][k], k)

ui.section('What we found', 'findings')
ui.findings(render_findings(S, RES))

ui.section('Look inside one question', 'explore', 'The combined system’s three stages for one question.')
explorer.rq4()

ui.section('Final scoreboard', 'scoreboard', 'One row per part: the overall winner, the reasonable trade-offs, the strongest and cheapest strategy, and what the tests support.')
rows = []
for rq, tok in (('RQ1', 'input_tokens'), ('RQ2', 'input_tokens'), ('RQ3', 'total_tokens')):
    r = RES[rq]; d = r['descriptive']
    f1 = max(d[m]['answer_f1'] for m in r['methods'])
    top = [m for m in r['methods'] if abs(d[m]['answer_f1'] - f1) < 1e-12]
    cheap = min(r['methods'], key=lambda m: (d[m][tok], r['methods'].index(m)))
    sig_q = sum(t['significant'] for t in r['tests'].get('answer_f1', []))
    sig_other = {mk: sum(t['significant'] for t in ts) for mk, ts in r['tests'].items() if mk != 'answer_f1'}
    rows.append({'Part': 'Part %s · %s' % (rq[-1], C['decomposition']['parts'][rq]['name']), 'Overall winner': '🏆 %s · %s' % (r['overall']['winner'], name_of.get(r['overall']['winner'], '')),
                 'Pareto set': ', '.join(r['pareto']),
                 'Highest answer F1': ('all tied (%s)' % fmt(f1, 'rate')) if len(top) == len(r['methods']) else '%s (%s)' % (', '.join(top), fmt(f1, 'rate')),
                 'Cheapest': '%s (%s tokens)' % (cheap, fmt(d[cheap][tok], 'tokens')),
                 'Significant answer-F1 differences': '%d of %d pairs' % (sig_q, len(r['tests'].get('answer_f1', []))),
                 'Other significant differences': ', '.join('%s: %d pairs' % ((M.get(mk) or {}).get('name', mk), n) for mk, n in sorted(sig_other.items()) if n)
                                                  or ('none' if sig_other else 'not tested')})
d4 = R['descriptive']
rows.append({'Part': 'Part 4 · Combined system', 'Overall winner': ' → '.join(R['combined']['rq4_pipeline']), 'Pareto set': '—', 'Highest answer F1': 'all tied (%s)' % fmt(d4['INT-1']['answer_f1'], 'rate'),
             'Cheapest': '%s (%s tokens)' % (min(R['methods'], key=lambda m: d4[m]['total_tokens']), fmt(min(d4[m]['total_tokens'] for m in R['methods']), 'tokens')),
             'Significant answer-F1 differences': '%d of %d pairs' % (sum(t['significant'] for t in R['tests']['answer_f1']), len(R['tests']['answer_f1'])),
             'Other significant differences': ', '.join('%s: %d pairs' % ((M.get(mk) or {}).get('name', mk), sum(t['significant'] for t in ts))
                                                        for mk, ts in sorted(R['tests'].items()) if mk != 'answer_f1' and any(t['significant'] for t in ts)) or 'none'})
st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
st.caption('Counts of significant pairs use Holm-adjusted p < 0.05 within each metric. Part 1 tested answer F1 only.')

ui.nav_footer(*state.neighbours('pages/p08_rq4.py'))
