"""Common execution frame for all RQ3 policies + AR-B0 / AR-B1.

A policy decides ONLY which tools to call, with what string, in what order, and when to stop. Everything
downstream (tools, evidence memory, fixed context, shared final generator, answer parser) is common code.
"""
import json
import time
import tiktoken
from research.common.contracts import MethodError
from research.common.serialization import canonical_json, content_hash
from research.evaluation.contracts import SystemOutput, Observation
from research.agentic.evidence import EvidenceMemory, canonical_paper
from research.agentic.rule_router import route, SOURCE_ORDER, normalize
from research.agentic.tools import fixed_context, generate_final
from research.agentic.llm import ProviderPause

TOKENIZER = 'tiktoken-0.12.0:o200k_harmony'
ENC = tiktoken.get_encoding('o200k_harmony')
INSUFFICIENT = 'INSUFFICIENT_EVIDENCE'


class Trace:
    def __init__(self):
        self.tool_calls, self.llm_calls, self.events, self.fallbacks = [], [], [], []
        self.queried = []            # sources in order of first call
        self.stop_reason = None
        self.status = 'ok'
        self.extra = {}

    def tool(self, step, call, new_count, reason=None, **meta):
        if call.source not in self.queried:
            self.queried.append(call.source)
        self.tool_calls.append({'step': step, 'source': call.source, 'query': call.query, 'evidence_ids': [e.evidence_id for e in call.evidence],
                                'new_evidence': new_count, 'latency_ms': call.latency_ms, 'cache_hit': call.cache_hit,
                                'status': call.details.get('status'), 'reason': reason, **meta})

    def llm(self, results, step=None):
        for r in results:
            self.llm_calls.append({'role': r.role, 'step': step, 'stage': r.stage_id, 'reused': r.reused, 'latency_ms': r.latency_ms,
                                   'wait_ms': r.wait_ms, 'usage': r.usage, 'finish_reason': r.finish_reason})


class Policy:
    version = 'phase9-v1'
    agentic_method = None

    def __init__(self, system_id, store, options, tools, llm, config_hash='unbound'):
        self.system_id, self.store, self.options, self.tools, self.llm = system_id, store, options, tools, llm
        self.agentic_method = system_id
        self.config_hash = config_hash
        self.fingerprint = content_hash({'system': system_id, 'version': self.version, 'config': config_hash,
                                         'options': options.model_dump(), 'tools': tools.fingerprint, 'extra': self.fingerprint_parts()})

    def fingerprint_parts(self):
        return {}

    # ------------------------------------------------------------------ to override
    def run(self, request, memory, trace):
        raise NotImplementedError

    # ------------------------------------------------------------------ frame
    def retrieve(self, request, memory, trace, step, source, retrieval_query, **kw):
        call = self.tools.call(source, retrieval_query, kw.pop('entities', ()), kw.pop('relations', ()), kw.pop('structured_intent', None))
        new = memory.add(call.evidence)
        trace.tool(step, call, len(new), **kw)
        return call, new

    def build(self, request, memory, trace):
        return fixed_context(memory.ordered(), tuple(trace.queried), self.store, request.overlay, self.options)

    def execute(self, request):
        started = time.perf_counter()
        trace, memory = Trace(), EvidenceMemory()
        final = self.run(request, memory, trace) or {'kind': 'generate'}
        controller_done = time.perf_counter()
        errors = []
        if final['kind'] == 'provided':
            context, retained, truncated, items, overlay = final['context_pack']
            raw, ids, result_error = final['raw'], final['ids'], None
        else:
            context, retained, truncated, items, overlay = self.build(request, memory, trace)
            allowed = [canonical_paper(e) for e in items if e.evidence_id in set(retained)]
            if final['kind'] == 'insufficient':
                raw, ids = None, ()
                trace.status = 'insufficient_evidence'
            else:
                raw, ids, result, perr = generate_final(self.llm, request.question, context, allowed, request.seed)
                trace.llm([result], step='final')
                if perr:
                    errors.append(MethodError(stage='answer_parse', code='InvalidGroundedAnswer', message='Model output was not a valid context-grounded paper set'))
        llm = trace.llm_calls
        usage_in = [c['usage']['prompt_tokens'] for c in llm if c['usage']]
        usage_out = [c['usage']['completion_tokens'] for c in llm if c['usage']]
        complete = bool(llm) and all(c['usage'] for c in llm)
        diagnostics = {'method': self.system_id, 'version': self.version, 'config_hash': self.config_hash,
                       'sources_called': list(trace.queried), 'retrieval_steps': len(trace.tool_calls), 'stop_reason': trace.stop_reason,
                       'status': trace.status, 'fallbacks': trace.fallbacks, 'tool_calls': trace.tool_calls, 'llm_calls': llm,
                       'events': trace.events, 'extra': trace.extra, 'overlay': overlay, 'context_truncated_evidence_ids': truncated,
                       'timings_ms': {'controller_total': (controller_done - started) * 1000,
                                      'retrieval': sum(t['latency_ms'] for t in trace.tool_calls),
                                      'llm_intrinsic': sum(c['latency_ms'] or 0 for c in llm),
                                      'provider_wait': sum(c['wait_ms'] or 0 for c in llm)},
                       'reused_llm_calls': sum(1 for c in llm if c['reused'])}
        observation = Observation(retrieval_ms=diagnostics['timings_ms']['retrieval'], generation_ms=diagnostics['timings_ms']['llm_intrinsic'],
                                  retrieval_calls=len(trace.tool_calls), tool_calls=len(trace.tool_calls), llm_calls=len(llm),
                                  input_tokens=sum(usage_in) if complete else None, output_tokens=sum(usage_out) if complete else None,
                                  token_measurement_source='groq.response.usage' if complete and llm else None)
        ranked = tuple(dict.fromkeys(canonical_paper(e) for e in items))
        answer_text = INSUFFICIENT if final['kind'] == 'insufficient' else raw
        return SystemOutput(answer=answer_text, answer_ids=None if errors else ids, ranked_paper_ids=ranked, evidence=tuple(items), context=context,
                            retained_evidence_ids=tuple(retained), context_tokens=len(ENC.encode(context, disallowed_special=())), tokenizer=TOKENIZER,
                            observation=observation, errors=tuple(errors), diagnostics=canonical_json(diagnostics))


class AlwaysAll(Policy):
    """AR-B0: Text -> Graph -> Structured with the raw query, always, then stop."""
    def run(self, request, memory, trace):
        for step, source in enumerate(SOURCE_ORDER, 1):
            self.retrieve(request, memory, trace, step, source, request.question, reason='always_all')
        trace.stop_reason = 'all_sources_retrieved'
        trace.extra['selected_sources'] = list(SOURCE_ORDER)


class RuleRouted(Policy):
    """AR-B1: deterministic cue router; every routed source once, in fixed order, then stop."""
    def run(self, request, memory, trace):
        decision = route(request.question)
        trace.extra['route'] = {k: decision[k] for k in ('version', 'sources', 'rule_hits', 'fallback_default_text', 'reason_code')}
        for step, source in enumerate(decision['sources'], 1):
            self.retrieve(request, memory, trace, step, source, request.question, reason=decision['reason_code'])
        trace.stop_reason = 'routed_sources_retrieved'
