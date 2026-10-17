import itertools
import numpy as np
import streamlit as st
from showcase.lib import state, ui, charts
from showcase.lib.fmt import fmt, metric as fmt_metric
from showcase.lib.metrics import answer_scores
from showcase.lib.questions import short_family
from showcase.lib.ui import e, html

C, B = state.content(), state.bundle()
E = C['evaluation']; M = E['metrics']
GROUPS = [('Answer quality', ['answer_f1', 'answer_em', 'precision', 'recall']),
          ('Evidence', ['mrr', 'recall_at_5', 'gold_coverage', 'supportability']),
          ('Retrieval control', ['source_f1', 'unnecessary_retrieval', 'stopping_accuracy']),
          ('Cost', ['input_tokens', 'total_tokens', 'context_tokens', 'llm_calls', 'retrieval_calls', 'latency'])]
ARROW = {'higher': '↑ higher is better', 'lower': '↓ lower is better', 'none': 'a classification, not a score'}

ui.page_header('Foundation', 'Metrics and statistics', E['page_intro'])
ui.toc([('metrics', 'Metrics'), ('playground', 'Try the answer metrics'), ('stats', 'When is a difference real?'), ('signflip', 'Sign-flip test on real results'),
        ('pareto', 'Trade-offs'), ('protocol', 'Protocol')])

ui.section('Metrics', 'metrics', 'Every metric is computed per question and then averaged over the questions of a study.')
for title, keys in GROUPS:
    st.markdown('#### ' + title)
    cols = st.columns(3)
    for i, k in enumerate(keys):
        m = M[k]
        with cols[i % 3]:
            html('<div class="card" style="margin-bottom:10px"><h4>%s <span class="small">%s</span></h4><p>%s</p><p><code>%s</code></p><div class="meta">%s</div></div>'
                 % (e(m['name']), e(ARROW.get(m['direction'], '')), e(m['plain']), e(m['formula']), e(m['why'])))

ui.section('Try the answer metrics', 'playground', 'Pick which papers are correct and which the system returned; the scores update immediately.')
papers = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
c1, c2 = st.columns(2)
gold = c1.multiselect('Correct papers', papers, default=['P1', 'P2', 'P3'], key='pg_gold')
pred = c2.multiselect('Returned papers', papers, default=['P2', 'P3', 'P5'], key='pg_pred')
s = answer_scores(pred, gold)
k1, k2, k3, k4 = st.columns(4)
with k1:
    ui.kpi('Precision', fmt(s['precision'], 'rate'), '%d correct of %d returned' % (s['hit'], len(pred)) if pred else 'nothing returned')
with k2:
    ui.kpi('Recall', fmt(s['recall'], 'rate'), '%d found of %d correct' % (s['hit'], len(gold)) if gold else 'no correct paper exists')
with k3:
    ui.kpi('Answer F1', fmt(s['f1'], 'rate'), 'balance of precision and recall')
with k4:
    ui.kpi('Exact match', fmt(s['exact_match'], 'rate'), 'returned set = correct set?')
st.caption('Special case used by the unanswerable variants: when no paper is correct, returning nothing scores 1 and returning anything scores 0.')

ui.section('When is a difference real?', 'stats')
st_ = E['statistics']
for i, (t, k) in enumerate((('Compare on the same questions.', 'paired'), ('Respect question families.', 'families'), ('How sure is the average?', 'bootstrap'),
                            ('Could it be chance?', 'sign_flip'), ('Many pairs at once.', 'holm')), 1):
    html('<div class="finding"><div class="n">%d</div><div class="x"><b>%s</b> %s</div></div>' % (i, e(t), e(st_[k])))

ui.section('Sign-flip test on real results', 'signflip', 'The exact test used in every study, run here live on recorded per-question differences. '
           'It reproduces the reported p-value.')
D = B.stats_demo
names = {d['rq']: C['decomposition']['parts'][d['rq']]['name'] for d in D}
opts = list(range(len(D)))
pick = st.selectbox('Comparison', opts, format_func=lambda i: 'Part %s · %s: %s vs %s' % (D[i]['rq'][-1], M[D[i]['metric']]['name'], D[i]['a'], D[i]['b']), key='sf_pick')
d = D[pick]
sums = np.array([d['family_sums'][f] for f in sorted(d['family_sums'])], dtype=float)
signs = np.array(list(itertools.product((-1., 1.), repeat=len(sums))))
totals = signs @ sums
observed = float(sums.sum())
p = float(np.mean(np.abs(totals) >= abs(observed) - 1e-12))
k1, k2, k3, k4 = st.columns(4)
with k1:
    ui.kpi('Families', str(len(sums)), '%s sign patterns' % fmt(2 ** len(sums), 'count'))
with k2:
    ui.kpi('Observed total A − B', fmt_metric(observed, d['metric'], sign=True), 'summed over %d questions' % len(d['per_query']))
with k3:
    ui.kpi('p (computed here)', fmt(p, 'p'), 'reported: %s' % fmt(d['reported']['p'], 'p'))
with k4:
    ui.kpi('Adjusted p (Holm)', fmt(d['reported']['p_holm'], 'p'), 'significant' if d['reported']['significant'] else 'not significant')
c1, c2 = st.columns(2, gap='large')
with c1:
    st.markdown('**1 · Difference per family** (A − B, summed within each family)')
    charts.family_bars(dict(sorted(d['family_sums'].items())), d['metric'], short_family)
with c2:
    st.markdown('**2 · Every way of flipping the family signs**')
    charts.signflip_hist(totals.tolist(), observed, d['metric'])
st.caption('If A and B were truly equal, each family’s difference would be as likely positive as negative. The p-value is the share of the %s sign patterns '
           'whose total is at least as far from zero as the observed one (red).' % fmt(2 ** len(sums), 'count'))

ui.section('Reasonable trade-offs: the Pareto set', 'pareto')
ui.callout(st_['pareto'], 'note')
st.markdown('Each study marks its Pareto-optimal methods with ★. A method outside the set is beaten by another method on every axis at once. '
            'A method inside the set is a defensible choice for some budget.')

ui.section('Protocol', 'protocol')
for t in E['protocol']:
    st.markdown('- ' + t)

ui.nav_footer(*state.neighbours('pages/p04_metrics.py'))
