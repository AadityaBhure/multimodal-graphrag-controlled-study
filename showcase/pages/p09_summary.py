import streamlit as st
from showcase.lib import state, ui
from showcase.lib.content import findings as render_findings
from showcase.lib.ui import e, html

C, B = state.content(), state.bundle()
S = C['summary']
PAGE = {'RQ1': 'pages/p05_rq1.py', 'RQ2': 'pages/p06_rq2.py', 'RQ3': 'pages/p07_rq3.py', 'RQ4': 'pages/p08_rq4.py'}

ui.page_header('Takeaways', 'Conclusions', S['page_intro'])
ui.toc([('key', 'Key findings'), ('parts', 'Each part in one line'), ('limits', 'Limitations'), ('next', 'Next steps')])

ui.section('Key findings', 'key')
ui.findings(S['key_findings'])

ui.section('Each part in one line', 'parts')
for rq in ('RQ1', 'RQ2', 'RQ3', 'RQ4'):
    part = C['decomposition']['parts'][rq]
    lines = render_findings(C[rq.lower()], B.results)
    c1, c2 = st.columns([1, 3], vertical_alignment='center')
    with c1:
        html('<div class="card tight"><div class="kicker">Part %s</div><h4>%s</h4></div>' % (rq[-1], e(part['name'])))
        st.page_link(PAGE[rq], label='Details', icon=':material/arrow_forward:')
    with c2:
        html('<div class="callout">%s</div>' % '<br>'.join(e(t) for t in lines[:2]))

ui.section('Limitations', 'limits')
for t in S['limitations']:
    st.markdown('- ' + t)

ui.section('Next steps', 'next')
for t in S['future_work']:
    st.markdown('- ' + t)

ui.nav_footer(*state.neighbours('pages/p09_summary.py'))
