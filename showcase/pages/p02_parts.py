import streamlit as st
from showcase.lib import state, ui
from showcase.lib.ui import e, html

C = state.content()
D = C['decomposition']
PAGE = {'RQ1': 'pages/p05_rq1.py', 'RQ2': 'pages/p06_rq2.py', 'RQ3': 'pages/p07_rq3.py', 'RQ4': 'pages/p08_rq4.py'}
PART = {'RQ1': 1, 'RQ2': 2, 'RQ3': 3, 'RQ4': 4}

ui.page_header('The problem', 'Four parts, one variable at a time', D['page_intro'])
ui.toc([('pipeline', 'The pipeline'), ('parts', 'The four parts'), ('order', 'How they fit together')])

ui.section('The pipeline', 'pipeline', 'Every question flows through the same stages. Three stages are studied; the others stay fixed.')
boxes = []
for s in D['pipeline']:
    if s['id'].startswith('RQ'):
        boxes.append('<div class="s rq"><span class="tag">Part %d</span><br><b>%s</b><small>%s</small></div>' % (PART[s['id']], e(s['label']), e(s.get('note', ''))))
    else:
        boxes.append('<div class="s"><b>%s</b><small>%s</small></div>' % (e(s['label']), e(s.get('note', ''))))
html('<div class="pipe">%s</div>' % '<div class="a">&#10140;</div>'.join(boxes))
ui.callout(D['principle'], 'note', title='Principle')

ui.section('The four parts', 'parts')
for row in (('RQ1', 'RQ2'), ('RQ3', 'RQ4')):
    for col, rq in zip(st.columns(2, gap='medium'), row):
        p = D['parts'][rq]
        with col:
            html('<div class="card"><div class="kicker">Part %d</div><h4>%s</h4><p><b>%s</b></p><p><b>Changes:</b> %s</p><p><b>Fixed:</b> %s</p>'
                 '<p><b>Judged by:</b> %s</p></div>' % (PART[rq], e(p['name']), e(p['question']), e(p['varies']), e(p['fixed']), e(p['judged_by'])))
            st.page_link(PAGE[rq], label='Open Part %d · %s' % (PART[rq], p['name']), icon=':material/arrow_forward:')

ui.section('How they fit together', 'order')
st.markdown('- **Parts 1–3** each change one component and compare five strategies: two simple controls and three methods adapted from published systems.\n'
            '- **Part 4** combines the best choice from each part, using a selection rule that was written down before any result was known.\n'
            '- Within a part, every strategy sees the same questions, the same evidence and the same answer model, so differences come from the strategy alone.')

ui.nav_footer(*state.neighbours('pages/p02_parts.py'))
