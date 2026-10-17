"""Readable step-by-step traces of retrieval-control runs.

`ar_steps` turns one run's stored diagnostics (tool calls, decision events, model calls) into an ordered list of steps.
It is shared by the bundle builder (recorded runs) and the live runner, so recorded and live traces look the same.
Pure Python: no research imports.
"""

SOURCES = ('text', 'graph', 'structured')


def _search(t):
    return {'kind': 'search', 'source': t['source'], 'query': t.get('query'), 'found': len(t.get('evidence_ids') or []),
            'new': t.get('new_evidence'), 'status': t.get('status'), 'reason': t.get('reason'), 'ms': t.get('latency_ms')}


def ar_steps(policy, d):
    """policy: AR-B0..AR-03; d: diagnostics with tool_calls, events, llm_calls, stop_reason, status and (optionally) extra."""
    calls = list(d.get('tool_calls', []))
    events = [e for e in d.get('events', []) if e.get('kind') != 'llm_output']
    extra = d.get('extra') or {}
    steps = []
    if policy == 'AR-B0':
        steps.append({'kind': 'plan', 'sources': extra.get('selected_sources') or list(SOURCES)})
        steps += [_search(t) for t in calls]
    elif policy == 'AR-B1':
        route = extra.get('route') or {}
        steps.append({'kind': 'route', 'sources': route.get('sources'), 'hits': route.get('rule_hits'), 'fallback': route.get('fallback_default_text')})
        steps += [_search(t) for t in calls]
    elif policy == 'AR-01':
        c = extra.get('classifier') or {}
        steps.append({'kind': 'classify', 'label': c.get('label'), 'probs': c.get('probs'), 'valid': c.get('valid')})
        decisions = [e for e in events if e['kind'] == 'controller_decision']
        for i, t in enumerate(calls):                       # each search is followed by the controller's decision on it
            steps.append(_search(t))
            if i < len(decisions):
                steps.append({'kind': 'decide', 'next': decisions[i].get('next_subquery'), 'reason': decisions[i].get('reason')})
        steps += [{'kind': 'decide', 'next': e.get('next_subquery'), 'reason': e.get('reason')} for e in decisions[len(calls):]]
    elif policy == 'AR-02':
        evals = [e for e in events if e['kind'] == 'evaluation']
        queue = list(calls)
        if queue:
            steps.append(_search(queue.pop(0)))
        for e in evals:                                     # BAD adds every remaining source, AMBIGUOUS the next one
            scores = e.get('calibrated') or []
            steps.append({'kind': 'evaluate', 'state': e.get('state'), 'best': max(scores) if scores else None, 'lower': e.get('lower'),
                          'upper': e.get('upper'), 'round': e.get('round'), 'failed': e.get('evaluator_failed')})
            want = {'BAD': 'correction_bad', 'AMBIGUOUS': 'correction_ambiguous'}.get(e.get('state'))
            while queue and want and queue[0].get('reason') == want:
                steps.append(_search(queue.pop(0)))
                if want == 'correction_ambiguous':
                    break
        steps += [_search(t) for t in queue]
    elif policy == 'AR-03':
        queue = list(calls)
        for e in events:
            k = e['kind']
            if k == 'agent_action':
                a = e.get('action') or {}
                steps.append({'kind': 'agent', 'iteration': e.get('iteration'), 'source': a.get('source'), 'query': a.get('retrieval_query'),
                              'reason': a.get('reason_code'), 'stop': a.get('stop_reason')})
                if a.get('source') in SOURCES and queue:
                    steps.append(_search(queue.pop(0)))
            elif k == 'candidate':
                steps.append({'kind': 'draft', 'iteration': e.get('iteration'), 'answer_ids': e.get('answer_ids'), 'parse_error': e.get('parse_error')})
            elif k == 'validator':
                v = e.get('verdict') or {}
                steps.append({'kind': 'validate', 'iteration': e.get('iteration'), 'accept': v.get('accept'), 'error': v.get('error_type')})
            elif k == 'commentor':
                steps.append({'kind': 'comment', 'iteration': e.get('iteration'), 'feedback': (e.get('note') or {}).get('feedback')})
        steps += [_search(t) for t in queue]
    else:
        steps += [_search(t) for t in calls]
    steps.append({'kind': 'stop', 'reason': d.get('stop_reason'), 'status': d.get('status')})
    llm = [{'role': c.get('role'), 'step': c.get('step'), 'input_tokens': (c.get('usage') or {}).get('prompt_tokens'),
            'output_tokens': (c.get('usage') or {}).get('completion_tokens'), 'ms': c.get('latency_ms')} for c in d.get('llm_calls', [])]
    return steps, llm


# plain-language labels used by the trace view
ROUTE_LABEL = {'A': 'answer without searching', 'B': 'one search', 'C': 'several searches (multi-step)'}
STOP_LABEL = {
    'all_sources_retrieved': 'every source was searched',
    'routed_sources_retrieved': 'every routed source was searched',
    'max_multi_steps': 'reached the maximum of 3 searches',
    'sufficient': 'the controller judged the evidence sufficient',
    'good': 'the evidence was rated good',
    'sources_exhausted': 'no sources were left to add',
    'max_correction_rounds': 'reached the maximum of 2 correction rounds',
    'validator_accepted': 'the validator accepted the draft answer',
    'max_iterations_rejected': 'reached 4 iterations without an accepted answer',
    'loop_guard_insufficient_evidence': 'stopped by the guard against repeated actions',
    'no_retrieval': 'answered without searching',
    'single_step_done': 'the single search was done',
}
STATUS_LABEL = {
    'ok': 'searched normally',
    'recognized_structured_clauses_only': 'only some conditions could be turned into a structured query',
    'unsupported_no_structured_filter': 'no structured condition was recognised',
    'rejected_sql_language': 'the query looked like SQL and was rejected (read-only safety rule)',
    'unsupported_structured_disjunction': 'OR-conditions are not supported by the structured search',
}
REASON_LABEL = {
    'always_all': 'fixed: always all sources', 'initial_router_source': 'first source chosen by the rules',
    'correction_bad': 'correction: evidence rated BAD', 'correction_ambiguous': 'correction: evidence rated AMBIGUOUS',
    'textual': 'agent: text cue', 'relational': 'agent: relation cue', 'numeric': 'agent: numeric cue', 'correction': 'agent: correcting itself',
}


def reason_label(reason):
    if not reason:
        return None
    if reason.startswith('route_C_step_'):
        return 'multi-step search %s' % reason.rsplit('_', 1)[1]
    if '+' in reason or reason in SOURCES:
        return 'routed: ' + reason.replace('+', ' + ')
    return REASON_LABEL.get(reason, reason.replace('_', ' '))
