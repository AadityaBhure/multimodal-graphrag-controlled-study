import streamlit as st
from showcase.lib import state, ui, charts
from showcase.lib.fmt import fmt
from showcase.lib.questions import highlighted
from showcase.lib.ui import e, html, SOURCE_COLOR, SOURCE_LABEL

C, B = state.content(), state.bundle()
P, F = C['problem'], B.foundation
ex = F['example']

ui.page_header('The problem', C['meta']['title'], C['meta']['subtitle'])
st.caption(C['meta']['scope_note'])
ui.toc([('statement', 'The problem'), ('example', 'A real question'), ('hard', 'Why it is hard'), ('success', 'What counts as better')])

ui.section('The problem', 'statement')
ui.callout(P['statement'], 'note')
views = C['foundation']['data']['views']
for col, s in zip(st.columns(3), ('text', 'graph', 'structured')):
    with col:
        html('<div class="card"><h4><span class="swatch" style="background:%s"></span>%s</h4><p>%s</p></div>'
             % (SOURCE_COLOR[s], e(views[s]['name']), e(views[s]['detail'])))

ui.section('A real question', 'example', P['example_intro'])
html('<div class="q">%s</div>' % highlighted(ex['question']))
html('<div class="small" style="margin:6px 0 10px 0">Colour shows which source can check each condition: '
     '<span class="chip src" style="background:%s">Text</span><span class="chip src" style="background:%s">Graph</span>'
     '<span class="chip src" style="background:%s">Structured</span></div>' % (SOURCE_COLOR['text'], SOURCE_COLOR['graph'], SOURCE_COLOR['structured']))

cond, cand = ex['conditions'], ex['candidates']
checks = {'text': 'The abstract contains one of the phrases ' + ' / '.join('“%s”' % p for p in cond['text']['phrases']) + '.',
          'graph': 'At least one author is affiliated with %s.' % (ex['views']['anchor']['label'] or 'the named institution'),
          'structured': 'Recorded ' + ' and '.join('%s %s %s' % (f['field'].replace('_', ' '), {'<=': '≤', '>=': '≥', '=': '='}.get(f['operator'], f['operator']), f['value'])
                                                 for f in cond['structured']['filters']) + '.'}
for col, s in zip(st.columns(3), ('text', 'graph', 'structured')):
    with col:
        html('<div class="card"><h4><span class="swatch" style="background:%s"></span>%s alone</h4><p>%s</p><div class="kpi" style="margin-top:8px">'
             '<div class="l">papers that pass</div><div class="v">%s</div></div></div>' % (SOURCE_COLOR[s], SOURCE_LABEL[s], e(checks[s]), fmt(cand[s], 'count')))

st.markdown('#### The answer lies in the overlap')
c1, c2 = st.columns([3, 2], gap='large')
with c1:
    charts.source_overlap(cand)
with c2:
    gold_title = B.title(ex['gold'])
    html('<div class="answer"><b>Exactly %s paper satisfies all three:</b><ul><li>%s <span class="small">stark:%s</span></li></ul></div>'
         % (fmt(cand['all'], 'count'), e(gold_title), ex['gold']))
    nec = ex['necessity']
    html('<div class="card tight"><h4>Leave out any one source and the answer goes wrong</h4>%s</div>' % ''.join(
        '<p>Without <b>%s</b>: %s wrong paper%s would also qualify.</p>' % (SOURCE_LABEL[s], fmt(nec[s]['count'], 'count'), '' if nec[s]['count'] == 1 else 's')
        for s in ('text', 'graph', 'structured')))
    st.caption('Counts come from the benchmark’s construction records, which compute each condition on the frozen data before the question is worded.')

ui.section('Why it is hard', 'hard')
for i, t in enumerate(P['why_hard'], 1):
    html('<div class="finding"><div class="n">%d</div><div class="x">%s</div></div>' % (i, e(t)))

ui.section('What counts as better', 'success')
for col, s in zip(st.columns(len(P['success'])), P['success']):
    with col:
        html('<div class="card"><h4>%s</h4><p>%s</p></div>' % (e(s['name']), e(s['detail'])))

ui.nav_footer(*state.neighbours('pages/p01_problem.py'))
