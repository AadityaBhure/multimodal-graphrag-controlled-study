import re
import pandas as pd
import streamlit as st
from showcase.lib import state, ui, charts, graph_view
from showcase.lib.fmt import fmt
from showcase.lib.questions import highlighted, MODALITY_LABEL
from showcase.lib.ui import e, html, SOURCE_COLOR, SOURCE_LABEL

C, B = state.content(), state.bundle()
Fd, F = C['foundation'], B.foundation
corpus, bench, ex = F['corpus'], F['benchmark'], F['example']

ui.page_header('Foundation', 'Data and benchmark', Fd['page_intro'])
ui.toc([('views', 'Three views'), ('paper', 'One paper, three views'), ('benchmark', 'The benchmark'), ('variants', 'Variants'), ('cohorts', 'Questions per part')])

ui.section('Three views of one corpus', 'views', Fd['data']['intro'])
ent = corpus['entities']
cards = {
    'text': ('%s documents' % fmt(corpus['text_documents'], 'count'), 'Title and abstract of every paper, searched by meaning with %d-dimensional sentence embeddings.'
             % corpus['embedding_dimension']),
    'graph': ('%s nodes · %s relations' % (fmt(corpus['nodes'], 'count'), fmt(corpus['official_relations'], 'count')),
              '%s papers, %s authors, %s institutions and %s fields of study.' % (fmt(ent['paper'], 'count'), fmt(ent['author'], 'count'),
                                                                                  fmt(ent['institution'], 'count'), fmt(ent['field_of_study'], 'count'))),
    'structured': ('%s rows' % fmt(corpus['structured_rows'], 'count'), 'One row per paper with %s.' % ', '.join(f.replace('_', ' ') for f in corpus['structured_fields']))}
for col, s in zip(st.columns(3), ('text', 'graph', 'structured')):
    with col:
        html('<div class="card"><h4><span class="swatch" style="background:%s"></span>%s</h4><div class="kpi" style="margin:6px 0">'
             '<div class="v" style="font-size:1.15rem">%s</div></div><p>%s</p></div>' % (SOURCE_COLOR[s], SOURCE_LABEL[s], e(cards[s][0]), e(cards[s][1])))
with st.expander('Graph relations by type'):
    charts.relation_bars(corpus['relations'])

ui.section('One paper, three views', 'paper', Fd['data']['paper_example_intro'] + ' This is the correct answer to the example question on the first page.')
v = ex['views']
c1, c2 = st.columns([3, 2], gap='large')
with c1:
    t = v['text']
    abstract = e(t['abstract'] or '')
    if t.get('match'):
        abstract = re.sub(re.escape(e(t['match'])), lambda m: '<span class="t">%s</span>' % m.group(0), abstract, count=1, flags=re.I)
    html('<div class="card"><h4><span class="swatch" style="background:%s"></span>Text view</h4><p><b>%s</b></p><p class="q" style="font-size:.92rem">%s</p>'
         '<div class="meta">The highlighted phrase satisfies the text condition.</div></div>' % (SOURCE_COLOR['text'], e(t['title']), abstract))
with c2:
    row = v['structured']
    filt = {f['field']: f for f in ex['conditions']['structured']['filters']}
    def check(k, val):
        f = filt.get(k)
        if not f:
            return ''
        ok = {'<=': lambda a, b: a <= b, '>=': lambda a, b: a >= b, '=': lambda a, b: a == b}[f['operator']](val, f['value'])
        return ' <span class="%s">%s required %s %s</span>' % ('ok' if ok else 'no', '✔' if ok else '✘', {'<=': '≤', '>=': '≥', '=': '='}[f['operator']], e(f['value']))
    rows = ''.join('<tr><td>%s</td><td>%s%s</td></tr>' % (e(k.replace('_', ' ')), e(row[k]), check(k, row[k]))
                   for k in ('publication_year', 'publication_date', 'citation_count', 'paper_rank', 'venue_namespace', 'venue_name', 'document_type'))
    html('<div class="card"><h4><span class="swatch" style="background:%s"></span>Structured view</h4><table class="sc"><tbody>%s</tbody></table>'
         '<div class="meta">The rank and venue conditions are checked against this row.</div></div>' % (SOURCE_COLOR['structured'], rows))
html('<h4 style="margin:14px 0 4px 0"><span class="swatch" style="background:%s"></span>Graph view</h4>' % SOURCE_COLOR['graph'])
st.caption('The paper with its authors, fields of study and a few citations. Green arrows: the path that satisfies the graph condition (%s ← author → paper).'
           % (v['anchor']['label'] or 'institution'))
graph_view.render(v['graph'], height=460)

ui.section('The benchmark', 'benchmark', Fd['benchmark']['intro'])
c1, c2, c3 = st.columns(3)
with c1:
    ui.kpi('Question families', fmt(bench['families'], 'count'), '%d source combinations × 2 families' % len(bench['families_by_modality']))
with c2:
    ui.kpi('Variants per family', '4', 'normal, noisy, conflict, unanswerable')
with c3:
    ui.kpi('Validation questions', fmt(bench['generated_validation'], 'count'), 'programmatically verified answers')
st.dataframe(pd.DataFrame([{'Sources needed': MODALITY_LABEL[m], 'Families': n} for m, n in bench['families_by_modality'].items()]),
             hide_index=True, width='content')
ui.callout(Fd['benchmark']['families'], 'note', title='Why families matter')

ui.section('Variants of one question', 'variants', Fd['benchmark']['variants_intro'])
names = {'normal': 'Normal', 'noisy': 'Noisy', 'conflict': 'Conflict', 'unanswerable': 'Unanswerable'}
tabs = st.tabs([names[s] for s in ('normal', 'noisy', 'conflict', 'unanswerable')])
for tab, s in zip(tabs, ('normal', 'noisy', 'conflict', 'unanswerable')):
    with tab:
        var = ex['variants'][s]
        st.markdown('**%s**' % Fd['benchmark']['variants'][s])
        html('<div class="q">%s</div>' % highlighted(var['question']))
        o = var.get('overlay') or {}
        if o.get('kind') == 'noisy':
            st.markdown('Added at evaluation time: ' + ', '.join('%d misleading %s item%s' % (n, SOURCE_LABEL[k].lower(), '' if n == 1 else 's')
                                                                  for k, n in sorted(o['distractors'].items())) + '.')
        elif o.get('kind') == 'conflict':
            st.markdown('Added at evaluation time: a %s record claiming **%s = %s** for the correct paper, which breaks the condition. '
                        'The original record stays authoritative, so the correct answer does not change.' % (o['source'], (o['field'] or '').replace('_', ' '), o['shown_value']))
        if var['gold']:
            st.markdown('Correct answer: **%s**' % ', '.join(B.title(g) or 'stark:%s' % g for g in var['gold']))
        else:
            st.markdown('Correct answer: **no paper** — the added condition cannot be met, so the right response is an empty answer.')

ui.section('Which questions each part uses', 'cohorts')
desc = {'RQ1': 'families whose question needs the graph', 'RQ2': 'families whose question needs several sources', 'RQ3': 'every family', 'RQ4': 'every family'}
st.dataframe(pd.DataFrame([{'Part': 'Part %s' % rq[-1], 'Questions': c['queries'], 'Families': c['families'], 'Which families': desc[rq],
                            'Variants': ', '.join(c['variants'])} for rq, c in sorted(bench['cohorts'].items())]), hide_index=True, width='stretch')

ui.nav_footer(*state.neighbours('pages/p03_data.py'))
