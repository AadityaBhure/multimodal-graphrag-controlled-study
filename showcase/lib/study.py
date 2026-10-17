"""One template for the three single-component studies (Parts 1-3): question, strategies, results, tests, findings,
breakdowns and the per-question explorer."""
import io
import pandas as pd
import streamlit as st
from showcase.lib import state, ui, charts, explorer
from showcase.lib.content import findings as render_findings
from showcase.lib.fmt import metric as fmt_metric, fmt
from showcase.lib.ui import e, html

PART = {'RQ1': 1, 'RQ2': 2, 'RQ3': 3, 'RQ4': 4}
PAGE = {'RQ1': 'pages/p05_rq1.py', 'RQ2': 'pages/p06_rq2.py', 'RQ3': 'pages/p07_rq3.py', 'RQ4': 'pages/p08_rq4.py'}
COLUMNS = {
    'RQ1': [('answer_f1', 'Answer F1'), ('answerable_f1', 'F1 answerable'), ('mrr', 'MRR'), ('gold_coverage', 'Gold coverage'),
            ('input_tokens', 'Input tokens'), ('latency', 'Latency'), ('llm_calls', 'Model calls')],
    'RQ2': [('answer_f1', 'Answer F1'), ('mrr', 'MRR'), ('input_tokens', 'Input tokens'), ('output_tokens', 'Output tokens'),
            ('llm_calls', 'Model calls'), ('latency', 'Latency')],
    'RQ3': [('answer_f1', 'Answer F1'), ('source_f1', 'Source F1'), ('unnecessary_retrieval', 'Wasted retrieval'), ('stopping_accuracy', 'Stopping acc.'),
            ('retrieval_calls', 'Searches'), ('llm_calls', 'Model calls'), ('total_tokens', 'Tokens'), ('latency', 'Latency')],
    'RQ4': [('answer_f1', 'Answer F1'), ('source_f1', 'Source F1'), ('retrieval_calls', 'Searches'), ('llm_calls', 'Model calls'),
            ('total_tokens', 'Tokens'), ('latency', 'Latency')],
}
SCATTER = {'RQ1': ('input_tokens', 'answer_f1', 'Input tokens per question (lower is cheaper)', 'Answer F1 (higher is better)'),
           'RQ2': ('input_tokens', 'latency', 'Input tokens per question (lower is cheaper)', 'Latency in seconds (lower is faster)'),
           'RQ3': ('total_tokens', 'source_f1', 'Tokens per question (lower is cheaper)', 'Source-selection F1 (higher is better)')}
SCATTER_NOTE = {'RQ1': 'Up and to the left is better: more correct answers for fewer tokens.',
                'RQ2': 'Every method returned the same (empty) answers, so only cost separates them: down and to the left is better.',
                'RQ3': 'Every policy returned the same answers, so the chart uses source selection: up and to the left is better.'}
BREAKDOWN_METRICS = {'RQ1': ['answer_f1', 'mrr', 'gold_coverage', 'input_tokens'], 'RQ2': ['total_tokens', 'answer_f1'],
                     'RQ3': ['source_f1', 'total_tokens', 'unnecessary_retrieval', 'stopping_accuracy', 'answer_f1']}
DIM_LABEL = {'stress': 'Variant', 'modality': 'Sources the question needs', 'support': 'Evidence supportability'}
SUPPORT_ORDER = ['FULLY_SUPPORTABLE', 'PARTIALLY_SUPPORTABLE', 'UNSUPPORTABLE']
STOP_TEXT = {'all_sources_retrieved': 'searched every source', 'routed_sources_retrieved': 'searched every routed source', 'max_multi_steps': 'hit the 3-search limit',
             'sufficient': 'judged the evidence sufficient', 'good': 'rated the evidence good', 'sources_exhausted': 'ran out of sources to add',
             'max_correction_rounds': 'hit the 2-round correction limit', 'validator_accepted': 'validator accepted an answer',
             'max_iterations_rejected': 'hit 4 iterations without acceptance'}


def csv_bytes(df):
    buf = io.StringIO(); df.to_csv(buf, index=False, lineterminator='\n')
    return buf.getvalue().encode('utf-8')


def scorecard_frame(rq, R, cols):
    return pd.DataFrame([{'method': m, **{k: R['descriptive'][m].get(k) for k, _ in cols}, 'pareto': m in R.get('pareto', [])} for m in R['methods']])


def strategies(rq, S, R):
    ui.section('The five strategies', 'strategies', 'Two simple controls and three methods adapted from published systems. Every strategy receives the same input.')
    ms = R['methods']
    for row in (ms[:3], ms[3:]):
        for col, m in zip(st.columns(3), row):
            with col:
                ui.method_card(m, S['methods'][m], pareto=m in R.get('pareto', []))
    st.markdown('#### Step by step')
    pick = st.segmented_control('Strategy', ms, default=ms[2], key=rq + '_steps', format_func=lambda m: '%s · %s' % (m, S['methods'][m]['name']),
                                label_visibility='collapsed') or ms[2]
    ui.flow(S['methods'][pick]['steps'])
    st.caption('Cost: ' + S['methods'][pick]['cost'])


def results(rq, S, R, C):
    M = C['evaluation']['metrics']; names = {m: S['methods'][m]['name'] for m in R['methods']}
    ui.section('Results', 'results', 'Mean per question over the %d questions. The best value in each column is highlighted; ★ marks the Pareto-optimal methods.'
               % R['cohort']['queries'])
    ui.scorecard(R['methods'], R['descriptive'], COLUMNS[rq], M, pareto=R.get('pareto', []), names=names)
    df = scorecard_frame(rq, R, COLUMNS[rq])
    st.download_button('Download this table (CSV)', csv_bytes(df), file_name='%s_results.csv' % rq.lower(), mime='text/csv', key=rq + '_dl_sc')
    c1, c2 = st.columns([1, 1], gap='large')
    with c1:
        x, y, xt, yt = SCATTER[rq]
        st.markdown('**Quality against cost**')
        charts.quality_cost(R['descriptive'], R['methods'], x, y, xt, yt, pareto=R.get('pareto', []))
        st.caption(SCATTER_NOTE[rq] + ' ' + C['evaluation']['statistics']['pareto'])
    with c2:
        st.markdown('**Compare one metric**')
        opts = [k for k, _ in COLUMNS[rq]]
        k = st.pills('Metric', opts, default=opts[0], key=rq + '_metric', format_func=lambda x: dict(COLUMNS[rq])[x], label_visibility='collapsed') or opts[0]
        charts.method_bars(R['descriptive'], R['methods'], k, dict(COLUMNS[rq])[k], ci=R.get('ci95'), pareto=R.get('pareto', []))
        st.caption((M.get(k) or {}).get('plain', '') + (' Whiskers: family-clustered 95 % bootstrap interval of the mean.' if R.get('ci95') else ''))


def tests(rq, R, C):
    ui.section('Is any difference real?', 'tests', 'Paired comparisons on the same questions, resampling whole families; p-values adjusted with Holm. '
               'Only an adjusted p below 0.05 counts as a real difference.')
    metrics = list(R['tests'])
    names = C['evaluation']['metrics']
    default = 'answer_f1' if 'answer_f1' in metrics else metrics[0]
    k = st.pills('Tested metric', metrics, default=default, key=rq + '_tm', format_func=lambda x: (names.get(x) or {}).get('name', x)) or default
    rows = R['tests'][k]
    ui.tests_table(rows, k)
    sig = [t for t in rows if t['significant']]
    if sig:
        ui.callout('%d of %d pairs differ significantly on %s.' % (len(sig), len(rows), (names.get(k) or {}).get('name', k)), 'good')
    else:
        ui.callout('No pair differs significantly on %s.' % (names.get(k) or {}).get('name', k), 'note')
    st.caption('Mean difference is A minus B. %d independent question families: the smallest possible unadjusted p-value is 2/%s.'
               % (R['cohort']['families'], fmt(2 ** R['cohort']['families'], 'count')))
    df = pd.DataFrame([{'metric': k, **{f: t.get(f) for f in ('a', 'b', 'delta', 'p', 'p_holm', 'significant', 'n', 'families')},
                        'ci_low': (t.get('ci95') or [None, None])[0], 'ci_high': (t.get('ci95') or [None, None])[1]} for k in metrics for t in R['tests'][k]])
    st.download_button('Download all tests (CSV)', csv_bytes(df), file_name='%s_tests.csv' % rq.lower(), mime='text/csv', key=rq + '_dl_t')


def findings(rq, S, R):
    ui.section('What we found', 'findings')
    ui.findings(render_findings(S, state.bundle().results))


def breakdown(rq, R, C):
    ui.section('Breakdown', 'breakdown', 'The same means split by question group (descriptive only; no tests within groups).')
    M = C['evaluation']['metrics']
    dims = [d for d in ('stress', 'modality', 'support') if d in R.get('strata', {})]
    c1, c2 = st.columns(2)
    dim = c1.pills('Split by', dims, default=dims[0], key=rq + '_dim', format_func=lambda d: DIM_LABEL[d]) or dims[0]
    mets = [k for k in BREAKDOWN_METRICS[rq] if any(k in x for v in R['strata'][dim].values() for x in v.values())]
    k = c2.pills('Metric', mets, default=mets[0], key=rq + '_bm', format_func=lambda x: (M.get(x) or {}).get('name', x)) or mets[0]
    values = list(R['strata'][dim])
    if dim == 'support':
        values = [v for v in SUPPORT_ORDER if v in values]
    elif dim == 'stress':
        values = [v for v in explorer.STRESS_ORDER if v in values]
    else:
        values = [v for v in explorer.MODALITY_ORDER if v in values]
    labels = {'FULLY_SUPPORTABLE': 'fully supportable', 'PARTIALLY_SUPPORTABLE': 'partially', 'UNSUPPORTABLE': 'unsupportable'}
    n = R.get('strata_n') or {}
    labels.update({v: '%s (n=%s)' % (labels.get(v, v), n['%s:%s' % (dim, v)]) for v in values if '%s:%s' % (dim, v) in n})
    charts.grouped(R['strata'][dim], values, R['methods'], k, (M.get(k) or {}).get('name', k), value_labels=labels)


def extras(rq, S, R, C):
    if rq == 'RQ2':
        ui.section('Could the evidence support an answer?', 'support', S['supportability_intro'])
        cnt = R['supportability']['counts']
        for col, k in zip(st.columns(3), SUPPORT_ORDER):
            with col:
                ui.kpi({'FULLY_SUPPORTABLE': 'Fully supportable', 'PARTIALLY_SUPPORTABLE': 'Partially supportable', 'UNSUPPORTABLE': 'Unsupportable'}[k],
                       fmt(cnt.get(k, 0), 'count'), explorer.SUPPORT_LABEL[k])
        st.caption('Rule: ' + R['supportability']['rule'].split(':', 1)[-1].strip())
        d = R['method_diagnostics']
        st.markdown('**How the fusion methods behaved**')
        st.markdown('- **CF-01:** every evidence item was attached to its entity by an explicit ID (the registry fallback was used %d times; %d groups truncated).\n'
                    '- **CF-02:** the selector picked %s structural items per question on average, with %d invalid IDs and no fallbacks.\n'
                    '- **CF-03:** %d source findings were grounded and %d sources reported no evidence; the fusion call never needed a retry.'
                    % (d['CF-01']['global_resolver_uses'], d['CF-01']['group_truncated'], fmt(d['CF-02']['mean_selected'], 'calls'), d['CF-02']['invalid_ids'],
                       d['CF-03']['source_statuses'].get('OK', 0), d['CF-03']['source_statuses'].get('NO_EVIDENCE', 0)))
    if rq == 'RQ3':
        ui.section('How each policy stopped', 'stops', 'Why each run ended, over the 28 questions.')
        charts.stacked_counts(R['stop_reasons'], R['methods'], 'Questions', labels=STOP_TEXT)
        with st.expander('Failure labels per policy (a question can carry several)'):
            fx = R['failure_taxonomy']
            labels = sorted({k for v in fx.values() for k in v})
            st.dataframe(pd.DataFrame([{'Failure': l.replace('_', ' '), **{m: fx.get(m, {}).get(l, 0) for m in R['methods']}} for l in labels]),
                         hide_index=True, width='stretch')


def render(rq):
    C, B = state.content(), state.bundle()
    S, R, part = C[rq.lower()], B.results[rq], C['decomposition']['parts'][rq]
    ui.page_header('Part %d of 4' % PART[rq], 'Part %d · %s' % (PART[rq], part['name']), S['page_intro'],
                   chips=[S['cohort'], '%d independent families' % R['cohort']['families'], '5 strategies'])
    ui.toc([('question', 'The question'), ('strategies', 'Strategies'), ('results', 'Results'), ('tests', 'Real differences?'),
            ('findings', 'Findings'), ('breakdown', 'Breakdown')] + ([('support', 'Supportability')] if rq == 'RQ2' else [])
           + ([('stops', 'Stopping')] if rq == 'RQ3' else []) + [('explore', 'Look inside one question')])
    ui.section('The question', 'question')
    ui.callout(part['question'], 'finding')
    for col, (t, k) in zip(st.columns(3), (('What changes', 'varies'), ('What stays fixed', 'fixed'), ('Judged by', 'judged_by'))):
        with col:
            html('<div class="card tight"><h4>%s</h4><p>%s</p></div>' % (e(t), e(part[k])))
    strategies(rq, S, R)
    results(rq, S, R, C)
    tests(rq, R, C)
    findings(rq, S, R)
    breakdown(rq, R, C)
    extras(rq, S, R, C)
    ui.section('Look inside one question', 'explore', 'Pick any question to see what each strategy produced and why. '
               'The link in your address bar reproduces this view.')
    {'RQ1': explorer.rq1, 'RQ2': explorer.rq2, 'RQ3': explorer.rq3}[rq]()
    ui.nav_footer(*state.neighbours(PAGE[rq]))
