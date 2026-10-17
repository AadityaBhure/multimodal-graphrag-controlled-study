"""'Look inside one question': per-question views of the recorded runs of each study (one shared question picker)."""
import pandas as pd
import streamlit as st
from showcase.lib import state, graph_view, trace_view
from showcase.lib.fmt import fmt, metric as fmt_metric
from showcase.lib.questions import highlighted, label, MODALITY_LABEL
from showcase.lib.ui import e, html, answer_box, gold_box, source_chips, kpi, badge, method_color, SOURCE_LABEL

EXAMPLE = 'generated:69a22c3b4989b07ed6c3:normal'
STRESS_ORDER = ['normal', 'noisy', 'conflict', 'unanswerable']
MODALITY_ORDER = ['T', 'G', 'S', 'TG', 'TS', 'GS', 'TGS']
SUPPORT_LABEL = {'FULLY_SUPPORTABLE': 'all correct papers are in the evidence', 'PARTIALLY_SUPPORTABLE': 'some correct papers are in the evidence',
                 'UNSUPPORTABLE': 'no correct paper is in the evidence'}


def pick_question(rq, qids, key):
    Q = state.bundle().queries
    order = sorted(qids, key=lambda q: (MODALITY_ORDER.index(Q[q]['modality']), Q[q]['family'], STRESS_ORDER.index(Q[q]['stress'])))
    c1, c2 = st.columns([1, 1])
    variants = [s for s in STRESS_ORDER if any(Q[q]['stress'] == s for q in order)]
    mods = [m for m in MODALITY_ORDER if any(Q[q]['modality'] == m for q in order)]
    v = c1.pills('Variant', ['all'] + variants, default='all', key=key + '_v')
    m = c2.pills('Sources the question needs', ['all'] + mods, default='all', key=key + '_m', format_func=lambda x: x if x == 'all' else MODALITY_LABEL[x])
    shown = [q for q in order if (v in (None, 'all') or Q[q]['stress'] == v) and (m in (None, 'all') or Q[q]['modality'] == m)] or order
    current = state.param('q', set(shown), EXAMPLE if EXAMPLE in shown else shown[0])
    q = st.selectbox('Question (%d shown)' % len(shown), shown, index=shown.index(current), key=key + '_q', format_func=lambda x: label(x, Q[x]))
    state.set_param('q', q)
    return q


def question_panel(q, extra_chips=''):
    Q = state.bundle().queries[q]
    html('<div class="q">%s</div>' % highlighted(Q['question']))
    html('<div class="chips" style="margin-top:6px">%s%s needs %s%s</div>' % (
        '<span class="chip">variant: %s</span>' % e(Q['stress']), '<span class="chip">%s</span>' % e(Q['hop'].replace('-', ' ')),
        source_chips(Q['oracle_sources']), extra_chips))
    if Q.get('overlay'):
        o = Q['overlay']
        if o['kind'] == 'noisy':
            st.caption('Noisy variant: misleading evidence is added at evaluation time (%s).' % ', '.join(
                '%d %s' % (n, SOURCE_LABEL.get(s, s).lower()) for s, n in sorted(o['distractors'].items())))
        elif o['kind'] == 'conflict':
            st.caption('Conflict variant: an added %s record claims %s = %s for one paper; the original record stays authoritative.'
                       % (o['source'], (o['field'] or '').replace('_', ' '), o['shown_value']))
    gold_box(Q['gold'], state.title_of)


def pick_methods(methods, names, key, default, short=None):
    m = state.param('m', set(methods), default)
    short = short or names
    c1, c2 = st.columns([3, 1.3], vertical_alignment='bottom')
    sel = c1.segmented_control('Strategy', methods, default=m, key=key + '_meth', format_func=lambda x: '%s · %s' % (x, short.get(x, '')))
    sel = sel or m
    state.set_param('m', sel)
    others = [x for x in methods if x != sel]
    cmp = c2.selectbox('Compare side by side with', ['none'] + others, key=key + '_cmp',
                       format_func=lambda x: 'nothing' if x == 'none' else '%s · %s' % (x, short.get(x, '')))
    return sel, (None if cmp == 'none' else cmp)


def short_names(section):
    return {m: v.get('inspired_by') or v['name'] for m, v in section['methods'].items()}


def metric_row(entry, keys, labels):
    cols = st.columns(len(keys))
    for c, k in zip(cols, keys):
        with c:
            kpi(labels.get(k, k), fmt_metric(entry['metrics'].get(k), k))


def context_expander(entry, name):
    with st.expander('Exact context the model received (%s characters)' % fmt(len(entry.get('context') or ''), 'count')):
        st.code(entry.get('context') or '', language=None, wrap_lines=True)


# ---------------------------------------------------------------------------------------------- RQ1
def rq1_panel(m, entry, q, names):
    n = entry['notes']
    html('<h4 style="margin:.2rem 0"><span class="swatch" style="background:%s"></span>%s · %s</h4>' % (method_color(m), e(m), e(names.get(m, ''))))
    answer_box(entry['answer_ids'], state.bundle().queries[q]['gold'], state.title_of, entry.get('explanation'))
    metric_row(entry, ['answer_f1', 'mrr', 'gold_coverage', 'input_tokens', 'latency'],
               {'answer_f1': 'Answer F1', 'mrr': 'MRR', 'gold_coverage': 'Gold coverage', 'input_tokens': 'Input tokens', 'latency': 'Latency'})
    kept = 'Kept **%s** nodes and **%s** relations out of %s retrieved nodes and %s relations.' % (
        fmt(n['kept_nodes'], 'count'), fmt(n['kept_relations'], 'count'), fmt(n['pool_nodes'], 'count'), fmt(n['pool_relations'], 'count'))
    detail = {
        'CM-B0': 'The budget filled with node descriptions in retrieved order before any relation was reached.' if not n['kept_relations'] else '',
        'CM-B1': 'Kept the graph evidence of the %s best-ranked papers.' % n.get('paper_limit'),
        'CM-01': '%s seed relations, %s-hop expansion, %s evidence tree(s) ranked by the reranker; %s of %s candidate units kept.' % (
            n.get('seed_relations'), n.get('hops'), n.get('trees'), n.get('selected_units'), n.get('candidate_units')),
        'CM-02': '%s nodes and %s relations had a prize; edge cost %s; %s leaves trimmed to fit the budget.' % (
            n.get('prized_nodes'), n.get('prized_relations'), n.get('edge_cost'), n.get('pruned_leaves')),
        'CM-03': 'Keywords: %s. %s seed nodes; diffusion %s; %s connector nodes; %s nodes trimmed.' % (
            ', '.join('“%s”' % k for k in n.get('keywords') or []) or 'none', n.get('seeds'), 'converged' if n.get('converged') else 'stopped at its step limit',
            n.get('connectors'), n.get('pruned'))}.get(m, '')
    st.markdown(kept + (' ' + detail if detail else ''))
    if n.get('overlay_items'):
        st.caption('%d added evaluation item(s) for this variant are listed in the context but not drawn.' % n['overlay_items'])
    graph_view.render(entry['graph'], height=420)
    st.caption(graph_view.caption(entry['graph']) + ' Exactly the graph evidence written into the model’s context.')
    context_expander(entry, m)


def rq1(q_key='rq1'):
    B, C = state.bundle(), state.content()
    X = B.explorer('RQ1'); names = {m: v['name'] for m, v in C['rq1']['methods'].items()}
    q = pick_question('RQ1', X['queries'], q_key)
    question_panel(q)
    m, cmp = pick_methods(X['methods'], names, q_key, 'CM-01', short_names(C['rq1']))
    cols = st.columns(2, gap='large') if cmp else [st.container()]
    for col, mm in zip(cols, [m] + ([cmp] if cmp else [])):
        with col:
            rq1_panel(mm, X['by_query'][q][mm], q, names)


# ---------------------------------------------------------------------------------------------- RQ2
def rq2_panel(m, entry, q, names):
    html('<h4 style="margin:.2rem 0"><span class="swatch" style="background:%s"></span>%s · %s</h4>' % (method_color(m), e(m), e(names.get(m, ''))))
    answer_box(entry['answer_ids'], state.bundle().queries[q]['gold'], state.title_of, entry.get('explanation'))
    metric_row(entry, ['answer_f1', 'input_tokens', 'llm_calls', 'latency'],
               {'answer_f1': 'Answer F1', 'input_tokens': 'Input tokens', 'llm_calls': 'Model calls', 'latency': 'Latency'})
    sc = entry.get('source_counts') or {}
    st.markdown('Evidence items in the context: ' + ', '.join('**%s** %s' % (sc.get(s, 0), SOURCE_LABEL[s].lower()) for s in ('text', 'graph', 'structured'))
                + ' · context size %s characters.' % fmt(entry['metrics'].get('context_characters'), 'count'))
    d = entry.get('detail') or {}
    if m == 'CF-01' and d:
        st.markdown('**Entity groups written:** %s · items attached by: %s' % (d.get('groups'), ', '.join('%s %s' % (n, r.replace('_', ' ')) for r, n in d.get('alignment_rules', {}).items())))
        st.dataframe(pd.DataFrame([{'Entity': g['key'], 'Items': len(g['members']), 'Sources covered': g['sources'], 'Best relevance': fmt(g['score'], 'rate'),
                                    'Members': ', '.join(g['members'])} for g in d.get('group_order', [])]), hide_index=True, width='stretch')
        st.caption('First groups in writing order (best relevance first, then source coverage).')
    if m == 'CF-02' and d:
        sel = d.get('selected') or []
        st.markdown('**Selector:** %s structural candidates shown to the model; it picked **%d**%s. Text filled %d of 10 slots.' % (
            d.get('structural_candidates'), len(sel), (': ' + ', '.join('`%s`' % s for s in sel)) if sel else '', len(d.get('semantic_fill') or [])))
        if d.get('fallback'):
            st.caption('Selector fallback used: %s' % d['fallback'])
    if m == 'CF-03' and d:
        rows = [{'Source': SOURCE_LABEL.get(f['source'], f['source']), 'Status': f['status'], 'Finding': f.get('candidate_answer'), 'Confidence': f.get('confidence'),
                 'Supporting evidence': ', '.join(f.get('supporting_evidence') or []) or '—'} for f in d.get('findings', [])]
        st.markdown('**Per-source findings** (each source read on its own, then fused):')
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    trace_view.llm_table([], extra=[{'role': s['stage'] if not s.get('detail') else '%s (%s)' % (s['stage'], s['detail']), 'step': None,
                                     'input_tokens': s['input_tokens'], 'output_tokens': s['output_tokens'], 'ms': s['ms']} for s in entry.get('stages', [])])
    context_expander(entry, m)


def rq2(q_key='rq2'):
    B, C = state.bundle(), state.content()
    X = B.explorer('RQ2'); names = {m: v['name'] for m, v in C['rq2']['methods'].items()}
    q = pick_question('RQ2', X['queries'], q_key)
    sup = X['support'][q]
    question_panel(q, '<span class="chip">evidence bundle: %s (%d of %d correct papers present)</span>' % (
        e(SUPPORT_LABEL.get(sup['class'], sup['class'])), sup['gold_in_bundle'], sup['gold']))
    m, cmp = pick_methods(X['methods'], names, q_key, 'CF-B1', short_names(C['rq2']))
    cols = st.columns(2, gap='large') if cmp else [st.container()]
    for col, mm in zip(cols, [m] + ([cmp] if cmp else [])):
        with col:
            rq2_panel(mm, X['by_query'][q][mm], q, names)


# ---------------------------------------------------------------------------------------------- RQ3 / RQ4
def sources_line(called, needed):
    called, needed = list(called or []), list(needed or [])
    miss = [s for s in needed if s not in called]; extra = [s for s in called if s not in needed]
    verdict = 'exactly the needed sources' if not miss and not extra else '; '.join(
        x for x in ('missed %s' % ', '.join(SOURCE_LABEL[s] for s in miss) if miss else '', 'extra %s' % ', '.join(SOURCE_LABEL[s] for s in extra) if extra else '') if x)
    html('<div class="small" style="margin:4px 0 8px 0">Searched %s · question needs %s · <b>%s</b></div>' % (source_chips(called), source_chips(needed), e(verdict)))


def rq3_panel(m, entry, q, names):
    Q = state.bundle().queries[q]
    html('<h4 style="margin:.2rem 0"><span class="swatch" style="background:%s"></span>%s · %s</h4>' % (method_color(m), e(m), e(names.get(m, ''))))
    answer_box(entry['answer_ids'], Q['gold'], state.title_of, entry.get('explanation'))
    sources_line(entry['sources_called'], Q['oracle_sources'])
    metric_row(entry, ['source_f1', 'retrieval_calls', 'llm_calls', 'total_tokens', 'latency'],
               {'source_f1': 'Source F1', 'retrieval_calls': 'Searches', 'llm_calls': 'Model calls', 'total_tokens': 'Tokens', 'latency': 'Latency'})
    st.markdown('**What the policy did, step by step**')
    trace_view.timeline(entry['steps'])
    if entry.get('failure_labels'):
        st.caption('Failure labels: ' + ', '.join(x.replace('_', ' ') for x in entry['failure_labels']))
    with st.expander('Model calls (%d)' % len(entry.get('llm') or [])):
        trace_view.llm_table(entry.get('llm') or [])
    context_expander(entry, m)


def rq3(q_key='rq3'):
    B, C = state.bundle(), state.content()
    X = B.explorer('RQ3'); names = {m: v['name'] for m, v in C['rq3']['methods'].items()}
    q = pick_question('RQ3', X['queries'], q_key)
    question_panel(q)
    m, cmp = pick_methods(X['methods'], names, q_key, 'AR-B1', short_names(C['rq3']))
    cols = st.columns(2, gap='large') if cmp else [st.container()]
    for col, mm in zip(cols, [m] + ([cmp] if cmp else [])):
        with col:
            rq3_panel(mm, X['by_query'][q][mm], q, names)


def int1_panel(entry, q):
    Q = state.bundle().queries[q]
    answer_box(entry['answer_ids'], Q['gold'], state.title_of, entry.get('explanation'))
    sources_line(entry['sources_called'], Q['oracle_sources'])
    metric_row(entry, ['source_f1', 'retrieval_calls', 'llm_calls', 'total_tokens', 'latency'],
               {'source_f1': 'Source F1', 'retrieval_calls': 'Searches', 'llm_calls': 'Model calls', 'total_tokens': 'Tokens', 'latency': 'Latency'})
    c1, c2, c3 = st.columns(3, gap='medium')
    with c1:
        st.markdown('**1 · Retrieval control (AR-B1)**')
        trace_view.timeline([s for s in entry['steps'] if s['kind'] != 'stop'])
    with c2:
        cm = entry['cm']
        st.markdown('**2 · Context management (CM-B1)**')
        st.markdown('Graph evidence: %s items retrieved → **%s kept** (the evidence of the 5 best-ranked papers).' % (cm['graph_in'], cm['graph_kept'])
                    if cm['graph_in'] else 'No graph evidence was retrieved for this question, so there was nothing to trim.')
    with c3:
        cf = entry['cf']
        st.markdown('**3 · Fusion (%s) and answer**' % cf.get('method'))
        sc = cf.get('source_counts') or {}
        st.markdown('Context sections: ' + ', '.join('**%s** %s' % (sc.get(s, 0), SOURCE_LABEL[s].lower()) for s in ('text', 'graph', 'structured')) + ' items.')
        trace_view.llm_table([], extra=[{'role': s['stage'], 'step': None, 'input_tokens': s['input_tokens'], 'output_tokens': s['output_tokens'], 'ms': s['ms']}
                                        for s in cf.get('stages', [])])
    context_expander(entry, 'INT-1')


def rq4(q_key='rq4'):
    X = state.bundle().explorer('RQ4')
    q = pick_question('RQ4', X['queries'], q_key)
    question_panel(q)
    int1_panel(X['by_query'][q]['INT-1'], q)
