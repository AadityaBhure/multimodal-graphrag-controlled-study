"""AR-01 Adaptive-RAG-inspired complexity routing (Phase 1D §6.2 + addendum §2).

A = no retrieval, B = one retrieval from the shared rule router's first source, C = up to three retrievals with a
controller-written subquery between retrievals. Controller failure => STOP retrieval and generate from accumulated
evidence (never another source, never AR-B0). Invalid classifier output => B (fallback='single_step').
"""
from research.agentic.policies import Policy
from research.agentic.rule_router import first_source, next_unqueried
from research.agentic.controllers import structured_call
from research.agentic.prompts import AR01_CONTROLLER_SYSTEM, controller_user, PROMPT_VERSION_HASH
from research.agentic.tools import fixed_context

MAX_MULTI_STEPS = 3


class AdaptiveRAG(Policy):
    def __init__(self, *args, classifier, **kw):
        self.classifier = classifier
        super().__init__(*args, **kw)

    def fingerprint_parts(self):
        return {'classifier': getattr(self.classifier, 'fingerprint', None), 'max_steps': MAX_MULTI_STEPS, 'prompts': PROMPT_VERSION_HASH}

    def run(self, request, memory, trace):
        pred = self.classifier.predict(request.question)
        label = pred.get('label') if pred.get('valid') else None
        trace.extra['classifier'] = {k: pred.get(k) for k in ('label', 'raw', 'probs', 'valid')}
        if label not in ('A', 'B', 'C'):
            label = 'B'
            trace.fallbacks.append({'type': 'invalid_classifier_output', 'fallback': 'single_step'})
        trace.extra['route'] = label
        if label == 'A':
            trace.stop_reason = 'route_A_no_retrieval'
            return {'kind': 'generate'}
        if label == 'B':
            self.retrieve(request, memory, trace, 1, first_source(request.question), request.question, reason='route_B_first_router_source')
            trace.stop_reason = 'single_step'
            return {'kind': 'generate'}
        subquery = request.question
        for step in range(1, MAX_MULTI_STEPS + 1):
            source = next_unqueried(subquery, trace.queried)
            if source is None:
                trace.stop_reason = 'sources_exhausted'
                break
            self.retrieve(request, memory, trace, step, source, subquery, reason='route_C_step_%d' % step, subquery=subquery)
            if step == MAX_MULTI_STEPS:
                trace.stop_reason = 'max_multi_steps'
                break
            context = fixed_context(memory.ordered(), tuple(trace.queried), self.store, request.overlay, self.options)[0]
            obj, events, results = structured_call(self.llm, 'ar01_controller', AR01_CONTROLLER_SYSTEM,
                                                   controller_user(request.question, context, step), request.seed)
            trace.events.extend(events)
            trace.llm(results, step)
            if obj is None:
                trace.fallbacks.append({'type': 'subquery_generation_failed',
                                        'action': 'stop_retrieval_generate_from_accumulated_evidence', 'step': step})
                trace.stop_reason = 'subquery_generation_failed'
                break
            trace.events.append({'kind': 'controller_decision', 'step': step, 'sufficient': obj['sufficient'],
                                 'next_subquery': obj['next_subquery'], 'reason': obj['reason']})
            if obj['sufficient']:
                trace.stop_reason = 'sufficient'
                break
            subquery = obj['next_subquery']
        return {'kind': 'generate'}
