import streamlit as st
from showcase import config
from showcase.lib import state, ui, explorer, trace_view
from showcase.lib.fmt import fmt, metric as fmt_metric
from showcase.lib.ui import e, html, kpi, answer_box, method_color, SOURCE_LABEL

C, B = state.content(), state.bundle()
T = C['try_it']
AR_NAMES = {m: v['name'] for m, v in C['rq3']['methods'].items()}
CF_NAMES = {m: v['name'] for m, v in C['rq2']['methods'].items()}
POLICIES = ('AR-B0', 'AR-B1', 'AR-01', 'AR-02', 'AR-03')
FUSIONS = ('CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03')
RECORDED = [('AR-B1', 'CF-B1')] + [(m, None) for m in POLICIES]      # (policy, fusion or None = the fixed Part 3 answer step)


def recorded_label(p):
    ar, cf = p
    if cf:
        return '%s → CM-B1 → %s · combined system (Part 4)' % (ar, cf)
    return '%s · %s → fixed context → answer (Part 3)' % (ar, AR_NAMES[ar])


def recorded_entry(p, q):
    ar, cf = p
    return B.explorer('RQ4')['by_query'][q]['INT-1'] if cf else B.explorer('RQ3')['by_query'][q][ar]


@st.cache_data(ttl=30, show_spinner=False)
def live_status():
    from showcase.lib.live import readiness
    return readiness()


@st.cache_resource(show_spinner='Opening the text, graph and structured stores…')
def live_engine():
    from showcase.lib.live import LiveEngine
    return LiveEngine()


def pipeline_strip(ar, cf):
    parts = [('Retrieval control', ar, AR_NAMES[ar]), ('Context management', 'CM-B1', 'Fixed top-K')]
    parts.append(('Fusion', cf, CF_NAMES[cf]) if cf else ('Answer step', 'Part 3', 'fixed context (8,000 characters per source)'))
    boxes = ''.join('<div class="a">&#10140;</div><div class="s rq" style="text-align:left;min-width:190px"><span class="tag">%s</span><br>'
                    '<b><span class="swatch" style="background:%s"></span>%s</b><small>%s</small></div>' % (e(t), method_color(m) if m != 'Part 3' else '#94a3b8', e(m), e(n))
                    for t, m, n in parts)
    html('<div class="pipe"><div class="s"><b>Question</b></div>%s<div class="a">&#10140;</div><div class="s"><b>Answer</b></div></div>' % boxes)


def result_panel(r, gold, oracle, title):
    st.markdown('#### ' + title)
    title_of = lambda i: state.title_of(i) or (r.get('titles') or {}).get(str(i))
    if r.get('errors'):
        st.warning('The run recorded an error: ' + '; '.join(map(str, r['errors']))[:400])
    if gold is not None:
        answer_box(r['answer_ids'], gold, title_of, r.get('explanation'), r.get('gold_seen'), r.get('gold_retrieved'))
        explorer.sources_line(r['sources_called'], oracle)
    else:
        ids = r['answer_ids']
        html('<div class="answer%s"><b>%s</b>%s</div>' % ('' if ids else ' empty', 'Returned %d paper%s' % (len(ids), '' if len(ids) == 1 else 's') if ids else 'Returned: no paper',
                                                        '<ul>%s</ul>' % ''.join('<li>%s <span class="small">stark:%s</span></li>' % (e(title_of(i) or 'title unavailable'), i) for i in ids) if ids else ''))
        if r.get('explanation'):
            st.caption('Model’s stated reason: ' + str(r['explanation']))
        html('<div class="small" style="margin:4px 0 8px 0">Searched %s</div>' % ui.source_chips(r['sources_called']))
    keys = ([('answer_f1', 'Answer F1')] if gold is not None else []) + [('retrieval_calls', 'Searches'), ('llm_calls', 'Model calls'),
                                                                         ('total_tokens', 'Tokens'), ('latency', 'Time')]
    for c, (k, lab) in zip(st.columns(len(keys)), keys):
        with c:
            kpi(lab, fmt_metric(r['metrics'].get(k), k))
    if r.get('live'):
        st.caption('Live run: %s of model compute%s.' % (fmt(r['metrics'].get('model_ms'), 'ms'),
                                                         '; %d model call(s) answered from recorded responses' % r['reused_calls'] if r.get('reused_calls') else ''))
    st.markdown('**Step by step**')
    trace_view.timeline([s for s in r['steps'] if s['kind'] != 'stop'] + [s for s in r['steps'] if s['kind'] == 'stop'])
    if r.get('cm'):
        cm = r['cm']
        st.markdown('**Context management (CM-B1):** ' + ('%s graph items retrieved → %s kept.' % (cm['graph_in'], cm['graph_kept']) if cm['graph_in']
                                                          else 'no graph evidence to trim.'))
    if r.get('cf'):
        sc = r['cf'].get('source_counts') or {}
        st.markdown('**Fusion (%s):** context sections with ' % r['cf']['method'] + ', '.join('%s %s' % (sc.get(s, 0), SOURCE_LABEL[s].lower()) for s in ('text', 'graph', 'structured')) + ' items.')
    with st.expander('Model calls'):
        trace_view.llm_table(r.get('llm') or [], extra=[{'role': s['stage'], 'step': None, 'input_tokens': s['input_tokens'], 'output_tokens': s['output_tokens'],
                                                         'ms': s['ms']} for s in ((r.get('cf') or {}).get('stages') or [])])
    with st.expander('Exact context the model received (%s characters)' % fmt(len(r.get('context') or ''), 'count')):
        st.code(r.get('context') or '', language=None, wrap_lines=True)


ui.page_header('Explore', 'Try a question', T['page_intro'])
live_possible = config.PROFILE == 'full'
modes = ['Recorded runs'] + (['Live run'] if live_possible else [])
mode = st.segmented_control('Mode', modes, default=modes[0], key='try_mode') or modes[0]

if mode == 'Recorded runs':
    ui.callout(T['replay_note'] if not live_possible else 'Replays the stored runs of the evaluated pipelines: every step, model call and answer exactly as recorded.', 'note')
    c1, c2 = st.columns(2)
    p1 = c1.selectbox('Pipeline', RECORDED, format_func=recorded_label, key='try_p1')
    p2 = c2.selectbox('Compare with', [None] + [p for p in RECORDED if p != p1], key='try_p2',
                      format_func=lambda p: 'nothing (single view)' if p is None else recorded_label(p))
    st.caption(T['compare_help'])
    q = explorer.pick_question('RQ3', B.explorer('RQ3')['queries'], 'try', explorer.default_question('RQ4', 'INT-1'))
    explorer.question_panel(q)
    Q = B.queries[q]
    cols = st.columns(2, gap='large') if p2 else [st.container()]
    for col, p in zip(cols, [p1] + ([p2] if p2 else [])):
        with col:
            pipeline_strip(*p)
            result_panel(recorded_entry(p, q), Q['gold'], Q['oracle_sources'], recorded_label(p))
else:
    ui.callout(T['live_note'], 'caution')
    checks = live_status()
    ready = all(ok for _, ok, _ in checks)
    with st.expander('Live system status: %s' % ('ready' if ready else 'not ready'), expanded=not ready):
        for name, ok, detail in checks:
            st.markdown('%s **%s** — %s' % ('✅' if ok else '❌', name, detail))
        from showcase.lib.live import gpu_temperature
        t = gpu_temperature() if ready else None
        if t is not None:
            st.markdown('GPU temperature: **%d °C**%s' % (t, ' — runs pause to cool down at 80 °C' if t >= 75 else ''))
    if not ready:
        st.info('Live runs need the research data and the local model server. Recorded runs are still available above.')
        st.stop()
    st.caption(T['builder_help'])
    c1, c2 = st.columns(2)
    ar = c1.pills('Retrieval control', POLICIES, default='AR-B1', key='live_ar', format_func=lambda m: '%s · %s' % (m, AR_NAMES[m])) or 'AR-B1'
    cf = c2.pills('Fusion', FUSIONS, default='CF-B1', key='live_cf', format_func=lambda m: '%s · %s' % (m, CF_NAMES[m])) or 'CF-B1'
    compare = st.toggle('Compare with a second pipeline', key='live_cmp')
    if compare:
        c1, c2 = st.columns(2)
        ar2 = c1.pills('Second: retrieval control', POLICIES, default='AR-03', key='live_ar2', format_func=lambda m: '%s · %s' % (m, AR_NAMES[m])) or 'AR-03'
        cf2 = c2.pills('Second: fusion', FUSIONS, default='CF-03', key='live_cf2', format_func=lambda m: '%s · %s' % (m, CF_NAMES[m])) or 'CF-03'
    source = st.radio('Question', ['A benchmark question (scored against its correct answer)', 'My own question (not scored)'], key='live_src', horizontal=True)
    if source.startswith('A benchmark'):
        q = explorer.pick_question('RQ3', B.explorer('RQ3')['queries'], 'live', explorer.default_question('RQ4', 'INT-1'))
        explorer.question_panel(q)
        Q = B.queries[q]; text, gold, oracle = None, Q['gold'], Q['oracle_sources']
    else:
        q = None; gold = oracle = None
        text = st.text_area('Your question', max_chars=config.MAX_QUESTION_CHARS, key='live_text',
                            placeholder='e.g. Which papers by authors affiliated with University of Insubria mention “we derive analytical expressions” in the abstract?')
    used = st.session_state.get('live_runs', 0)
    left = config.LIVE_RUNS_PER_SESSION - used
    pipes = [(ar, cf)] + ([(ar2, cf2)] if compare else [])
    go = st.button('Run %s' % ('both pipelines' if compare else 'the pipeline'), type='primary', disabled=left < len(pipes) or (q is None and not (text or '').strip()))
    note = st.empty()                    # filled after a run, so the count is current
    key = (q or 'text:' + (text or '').strip(), tuple(pipes))
    if go:
        engine = live_engine()
        results = []
        for a, f in pipes:
            with st.status('Running %s → CM-B1 → %s …' % (a, f), expanded=False) as s:
                if engine.lock.locked():
                    s.update(label='Waiting for another live run to finish…')
                try:
                    results.append(engine.run(a, f, question=text, query_id=q))
                    s.update(label='%s → CM-B1 → %s finished' % (a, f), state='complete')
                except BaseException as exc:          # the research client signals provider problems with BaseException subclasses
                    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                        raise
                    s.update(label='%s → CM-B1 → %s failed' % (a, f), state='error')
                    results.append({'failed': '%s: %s' % (type(exc).__name__, str(exc)[:300])})
        st.session_state['live_runs'] = used + len(pipes)
        st.session_state['live_last'] = (key, results)
    note.caption('%d of %d live runs left in this session. Repeating a run is answered from the stored responses.'
                 % (max(config.LIVE_RUNS_PER_SESSION - st.session_state.get('live_runs', 0), 0), config.LIVE_RUNS_PER_SESSION))
    last = st.session_state.get('live_last')
    if last and last[0] == key:
        cols = st.columns(2, gap='large') if len(last[1]) == 2 else [st.container()]
        for col, (a, f), r in zip(cols, pipes, last[1]):
            with col:
                pipeline_strip(a, f)
                if r.get('failed'):
                    st.error('The run failed: ' + r['failed'])
                else:
                    result_panel(r, gold, oracle, '%s → CM-B1 → %s (live)' % (a, f))

ui.nav_footer(*state.neighbours('pages/p10_try.py'))
