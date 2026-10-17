"""INT-1 (documentation/rq4/RQ4_DESIGN.md): selected RQ3 retrieval-control policy -> CM-B1 on Graph evidence ->
selected RQ2 fusion method -> that method's final answer. Every component is the frozen implementation of its study.
"""
import json
import time
from research.common.contracts import RetrievalBundle
from research.common.serialization import canonical_json, content_hash
from research.evaluation.contracts import Observation, SystemOutput
from research.agentic.policies import Trace
from research.agentic.evidence import EvidenceMemory, canonical_paper
from research.baselines.system import apply_overlay
from research.rq2.contracts import FrozenInput
from research.repair.rq2_canonical.system import CanonicalFusionSystem

CM_B1_PAPERS = 5


def cm_b1(graph_items, k=CM_B1_PAPERS):
    """Keep the graph items of the k best-ranked papers (retriever score desc, acquisition order breaks ties) with their paths."""
    ranked = sorted(enumerate(graph_items), key=lambda t: (-(t[1].score or 0.), t[0]))
    papers = []
    for _, e in ranked:
        p = canonical_paper(e)
        if p not in papers:
            papers.append(p)
        if len(papers) == k:
            break
    keep = set(papers)
    return [e for e in graph_items if canonical_paper(e) in keep], papers


class IntegratedSystem:
    version = 'rq4-int1-v1'

    def __init__(self, policy, cf_method, store, options, llm, registry_fn):
        self.policy, self.cf_method, self.store, self.options, self.llm, self.registry_fn = policy, cf_method, store, options, llm, registry_fn
        self.system_id = 'INT-1'
        self.fingerprint = content_hash({'version': self.version, 'ar': policy.fingerprint, 'cf': cf_method, 'cm': 'CM-B1', 'k': CM_B1_PAPERS})

    def call(self, stage, system, user, seed, cap):
        """Adapter: RQ2 methods' call(stage, ...) -> the shared durable client (stage identity = payload hash)."""
        r = self.llm.chat(stage.split(':')[1] if ':' in stage else stage, system, user, cap, seed)
        u = r.usage or {}
        return r.raw, {'llm_calls': 1, 'input_tokens': u.get('prompt_tokens'), 'output_tokens': u.get('completion_tokens'),
                       'generation_ms': r.latency_ms, 'token_measurement_source': 'groq.response.usage' if u else None}, r.reused

    def execute(self, request):
        started = time.perf_counter()
        trace, memory = Trace(), EvidenceMemory()
        self.policy.run(request, memory, trace)                         # retrieval control only; its own final answer is not generated
        ar_done = time.perf_counter()
        # Same frozen overlay injection as the RQ3 fixed downstream (tools.fixed_context), for the sources actually queried.
        items, overlay_info = apply_overlay(self.store, tuple(memory.ordered()), request, tuple(trace.queried), self.options)
        by = {s: [e for e in items if e.source_type == s] for s in ('text', 'graph', 'structured')}
        kept_graph, cm_papers = cm_b1(by['graph'])
        bundle = RetrievalBundle(query_id=request.query_id, text_evidence=tuple(by['text']), graph_evidence=tuple(kept_graph),
                                 structured_evidence=tuple(by['structured']))
        ids = sorted({e.canonical_id for e in (*by['text'], *kept_graph, *by['structured'])})
        registry = self.registry_fn(ids)
        frozen = FrozenInput(question=request.question, bundle=bundle, overlay_hash=content_hash(request.overlay) if request.overlay else None,
                             canonical_ids=tuple(i for i in ids if i in registry), aliases=())
        out = CanonicalFusionSystem(self.cf_method, {request.query_id: frozen}, registry, self.call).execute(request)
        cf = json.loads(out.diagnostics)
        ar_llm = trace.llm_calls
        def tok(key):
            vals = [c['usage'][key] for c in ar_llm if c['usage']]
            return sum(vals) if len(vals) == len(ar_llm) else None
        ar_in, ar_out = tok('prompt_tokens'), tok('completion_tokens')
        o = out.observation
        retrieval_ms = sum(t['latency_ms'] for t in trace.tool_calls)
        ar_llm_ms = sum(c['latency_ms'] or 0 for c in ar_llm)
        d = {'system': 'INT-1', 'ar': {'method': self.policy.system_id, 'sources_called': list(trace.queried), 'tool_calls': trace.tool_calls,
                                       'stop_reason': trace.stop_reason, 'status': trace.status, 'llm_calls': ar_llm, 'fallbacks': trace.fallbacks,
                                       'events': trace.events},
             'cm': {'method': 'CM-B1', 'graph_in': [e.evidence_id for e in by['graph']], 'graph_kept': [e.evidence_id for e in kept_graph], 'papers': cm_papers},
             'cf': cf, 'overlay': overlay_info,
             'timings_ms': {'ar_controller_total': (ar_done - started) * 1000, 'retrieval': retrieval_ms, 'llm_intrinsic': ar_llm_ms + (o.generation_ms or 0.),
                            'provider_wait': sum(c['wait_ms'] or 0 for c in ar_llm), 'total': (time.perf_counter() - started) * 1000},
             # compatibility with research/agentic/analysis.per_record (source metrics use the AR trace)
             'sources_called': list(trace.queried), 'tool_calls': trace.tool_calls, 'stop_reason': trace.stop_reason, 'status': trace.status}
        both = lambda a, b: a + b if a is not None and b is not None else None
        observation = Observation(retrieval_ms=retrieval_ms, retrieval_calls=len(trace.tool_calls), tool_calls=len(trace.tool_calls),
                                  generation_ms=both(ar_llm_ms, o.generation_ms), llm_calls=len(ar_llm) + (o.llm_calls or 0),
                                  input_tokens=both(ar_in, o.input_tokens), output_tokens=both(ar_out, o.output_tokens),
                                  token_measurement_source='groq.response.usage' if both(ar_in, o.input_tokens) is not None else None)
        return SystemOutput(answer=out.answer, answer_ids=out.answer_ids, errors=out.errors, ranked_paper_ids=out.ranked_paper_ids,
                            evidence=tuple(items), context=out.context, retained_evidence_ids=out.retained_evidence_ids,
                            diagnostics=canonical_json(d), observation=observation)
