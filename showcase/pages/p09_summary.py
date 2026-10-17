import streamlit as st
from showcase.lib import state, ui
from showcase.lib.content import render
from showcase.lib.fmt import fmt
from showcase.lib.ui import e, html, method_color

C, B = state.content(), state.bundle()
S, RES = C['summary'], B.results
PAGE = {'RQ1': 'pages/p05_rq1.py', 'RQ2': 'pages/p06_rq2.py', 'RQ3': 'pages/p07_rq3.py', 'RQ4': 'pages/p08_rq4.py'}
ORDER = ('RQ1', 'RQ2', 'RQ3')

ui.page_header('Takeaways', 'Conclusions', S['page_intro'])
ui.toc([('winners', 'The winners'), ('combined', 'Combined system'), ('situations', 'When to pick something else'), ('key', 'Key findings'),
        ('limits', 'Limitations'), ('next', 'Next steps')])
ui.callout(S['verdict'], 'good', title='Verdict')

ui.section('The winners', 'winners', C['evaluation']['overall']['rule'])
for col, rq in zip(st.columns(3, gap='medium'), ORDER):
    sec, o = C[rq.lower()], RES[rq]['overall']
    w = o['winner']
    with col:
        html('<div class="winner" style="height:100%%;box-sizing:border-box"><div class="cup">🏆</div><div><div class="kicker">Part %s · %s</div>'
             '<h3><span class="swatch" style="background:%s"></span>%s · %s</h3><p>%s</p><div class="small" style="margin-top:6px">Rank total %s; runner-up %s (%s).</div>'
             '</div></div>' % (rq[-1], e(C['decomposition']['parts'][rq]['name']), method_color(w), e(w), e(sec['methods'][w]['name']),
                               e(render(sec['overall']['summary']['text'], sec['overall']['summary']['values'], RES)), e(fmt(o['total'][w], 'rank')),
                               e(o['order'][1]), e(fmt(o['total'][o['order'][1]], 'rank'))))
        st.page_link(PAGE[rq], label='Ranking and details', icon=':material/arrow_forward:')

ui.section('The combined system', 'combined', 'The three winners chained in pipeline order (Part 4).')
comb, d4 = RES['RQ4']['combined'], RES['RQ4']['descriptive']['INT-1']
html('<div class="pipe">%s</div>' % '<div class="a">&#10140;</div>'.join(
    ['<div class="s" style="flex:0 0 90px"><b>Question</b></div>'] +
    ['<div class="s rq"><span class="tag">Winner of Part %s</span><br><b><span class="swatch" style="background:%s"></span>%s</b><small>%s</small></div>'
     % (rq[-1], method_color(RES[rq]['overall']['winner']), e(RES[rq]['overall']['winner']), e(C[rq.lower()]['methods'][RES[rq]['overall']['winner']]['name']))
     for rq in ('RQ3', 'RQ1', 'RQ2')] + ['<div class="s" style="flex:0 0 90px"><b>Answer</b></div>']))
k = st.columns(4)
for col, (label, metric) in zip(k, (('Answer F1', 'answer_f1'), ('Source-selection F1', 'source_f1'), ('Tokens per question', 'total_tokens'), ('Time per question', 'latency'))):
    with col:
        ui.kpi(label, fmt(d4[metric], {'answer_f1': 'rate', 'source_f1': 'rate', 'total_tokens': 'tokens', 'latency': 'ms'}[metric]))
f = S['key_findings'][0]
ui.callout(render(f['text'], f['values'], RES), 'note')
st.page_link(PAGE['RQ4'], label='Part 4 in detail', icon=':material/arrow_forward:')

ui.section('When to pick something else', 'situations', 'The winners are the best overall choice. In these situations another strategy measured better.')
for rq in ORDER:
    sec = C[rq.lower()]
    st.markdown('**Part %s · %s** — overall winner %s' % (rq[-1], C['decomposition']['parts'][rq]['name'], RES[rq]['overall']['winner']))
    sits = sec['overall']['situations']
    for col, s_ in zip(st.columns(len(sits)), sits):
        with col:
            ui.situation_card(s_['when'], '%s · %s' % (s_['pick'], sec['methods'][s_['pick']]['name']), render(s_['text'], s_['values'], RES), method_color(s_['pick']))
    st.write('')

ui.section('Key findings', 'key')
ui.findings([render(f['text'], f['values'], RES) for f in S['key_findings'][1:]])
st.caption(C['evaluation']['overall']['note'])

ui.section('Limitations', 'limits')
for t in S['limitations']:
    st.markdown('- ' + t)

ui.section('Next steps', 'next')
for t in S['future_work']:
    st.markdown('- ' + t)

ui.nav_footer(*state.neighbours('pages/p09_summary.py'))
