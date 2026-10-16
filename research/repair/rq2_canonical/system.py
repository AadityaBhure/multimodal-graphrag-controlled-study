"""Phase 5 runner adapter for the canonical RQ2 methods (CF-B0, CF-B1, CF-01, CF-02, CF-03).

`call(stage, system, user, seed, cap) -> (raw, usage, reused)` is the durable dispatcher (research/repair/dispatch.py);
None = offline (contexts and diagnostics only, used for the pre-dispatch audit). Provider pauses are BaseExceptions and
propagate; only deterministic content failures (unparseable output) take the specified fallback paths.
"""
import json
import time
from pathlib import Path
import tiktoken
from research.common.contracts import MethodError
from research.common.serialization import canonical_json, content_hash
from research.evaluation.benchmark import digest
from research.evaluation.contracts import Observation, SystemOutput
from research.baselines.generation import PROMPT, parse_answer
from . import fusion as F
from . import prompts as P

ENC = tiktoken.get_encoding('o200k_harmony')
BUDGET = 24000                       # S1: shared 24,000-character context cap


def count_tokens(text):
    return len(ENC.encode(text, disallowed_special=()))


class CanonicalFusionSystem:
    version = 'rq2-canonical-v1'

    def __init__(self, method, inputs, registry, call=None):
        self.system_id, self.inputs, self.registry, self.call = method, inputs, registry, call
        self.fingerprint = content_hash({'method': method, 'version': self.version, 'prompt_version': P.PROMPT_VERSION, 'final_prompt': PROMPT,
                                         'inputs': {k: v.fingerprint() for k, v in sorted(inputs.items())},
                                         'code': {p.name: digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))}})

    # ------------------------------------------------------------------ helpers
    def _llm(self, stage, system, user, seed, cap, usages, d):
        raw, usage, reused = self.call(stage, system, user, seed, cap)
        usages.append(usage); d['llm_stages'].append({'stage': stage, 'reused': reused, 'usage': usage})
        return raw

    def _final(self, question, context, seed, allowed, usages, d, stage='final'):
        raw = self._llm(self.system_id + ':' + stage + ':' + content_hash(question), PROMPT,
                        'QUESTION\n' + question + '\n\nEVIDENCE\n' + context, seed, P.FINAL_CAP, usages, d)
        return raw, parse_answer(raw, allowed)

    # ------------------------------------------------------------------ main
    def execute(self, request):
        started = time.perf_counter()
        frozen = self.inputs[request.query_id]
        if frozen.question != request.question or frozen.overlay_hash != (content_hash(request.overlay) if request.overlay else None):
            raise ValueError('Frozen query/overlay mismatch')
        before = frozen.bundle.canonical_bytes()
        items = F.evidence(frozen); q = request.question; seed = request.seed
        d = {'method': self.system_id, 'bundle_hash': frozen.bundle.bundle_hash(), 'input_fingerprint': frozen.fingerprint(),
             'incoming_ids': [e.evidence_id for e in items], 'additional_retrieval_calls': 0, 'llm_stages': [], 'requests': []}
        usages, errors, answer, answer_ids = [], (), None, None
        t0 = time.perf_counter()
        m = self.system_id
        if m == 'CF-B0':
            context, kept = F.pack(items, BUDGET)
        elif m in ('CF-B1', 'CF-03'):
            context, kept, parts = F.separated(items, BUDGET); d['source_contexts'] = parts
        elif m == 'CF-01':
            context, kept, info = F.cf01(frozen, BUDGET, self.registry); d.update(info)
        elif m == 'CF-02':
            structural, dropped_s = F.dedup([e for e in items if e.source_type != 'text'])
            semantic, dropped_t = F.dedup([e for e in items if e.source_type == 'text'])
            text_manifest, offered = F.manifest(structural, count_tokens, P.SELECTOR_INPUT_BUDGET)
            d.update(structural_candidates=len(structural), semantic_candidates=len(semantic), dedup_dropped=dropped_s + dropped_t,
                     manifest_candidates=[e.evidence_id for e in offered], selector_fallback=None)
            allowed = {e.evidence_id for e in offered}
            selector_user = 'QUESTION\n' + q + '\n\nCANDIDATES\n' + text_manifest
            d['requests'].append({'stage': 'selector', 'tokens': count_tokens(P.SELECTOR) + count_tokens(selector_user)})
            selected_ids = []
            if offered and self.call:
                raw = self._llm(m + ':selector:' + content_hash(q), P.SELECTOR, selector_user, seed, P.SELECTOR_CAP, usages, d)
                try:
                    selected_ids, invalid = F.parse_selection(raw, allowed)
                except (ValueError, TypeError):
                    repair_user = selector_user + '\n\nPREVIOUS REPLY\n' + raw[:2000] + '\n\n' + P.SELECTOR_REPAIR
                    raw = self._llm(m + ':selector_repair:' + content_hash(q), P.SELECTOR, repair_user, seed, P.REPAIR_CAP, usages, d)
                    try:
                        selected_ids, invalid = F.parse_selection(raw, allowed)
                    except (ValueError, TypeError):
                        selected_ids, invalid = F.relevance_fallback(offered), []
                        d['selector_fallback'] = 'relevance'
                d['selector_invalid_ids'] = invalid
            by_id = {e.evidence_id: e for e in structural}
            chosen_structural = [by_id[i] for i in selected_ids]
            context, kept, trimmed = F.cf02_context(chosen_structural, semantic, BUDGET)
            d.update(selected_structural=selected_ids, semantic_fill=[e.evidence_id for e in kept if e.source_type == 'text'], budget_trimmed=trimmed)
        else:
            raise ValueError('unknown method ' + m)
        d['fusion_ms'] = (time.perf_counter() - t0) * 1000
        kept = tuple(kept)
        ranked = tuple(dict.fromkeys(F.paper_id(e) for e in kept if F.paper_id(e) is not None))
        if m != 'CF-03':
            d['requests'].append({'stage': 'final', 'tokens': count_tokens(PROMPT) + count_tokens('QUESTION\n' + q + '\n\nEVIDENCE\n' + context)})
        if m == 'CF-03':
            findings, papers = [], {}
            for source in F.SOURCES:
                own = [e for e in kept if e.source_type == source]
                user = 'QUESTION\n' + q + '\n\nSOURCE ' + source.upper() + '\n' + parts[source]
                if not own:
                    findings.append({'source': source, 'status': 'NO_EVIDENCE', 'candidate_answer': '', 'supporting_evidence': [], 'confidence': 'low'})
                    continue
                d['requests'].append({'stage': 'reason:' + source, 'tokens': count_tokens(P.REASONING) + count_tokens(user)})
                if not self.call:
                    continue
                raw = self._llm(m + ':reason:' + source + ':' + content_hash(q), P.REASONING, user, seed, P.REASONING_CAP, usages, d)
                try:
                    obj = F.parse_intermediate(raw, {e.evidence_id for e in own})
                    pid = {e.evidence_id: F.paper_id(e) for e in own}
                    sup = [{'evidence_id': i, 'paper_id': pid[i]} for i in obj['supporting_evidence_ids']]
                    papers.update({s['paper_id']: s['evidence_id'] for s in sup if s['paper_id'] is not None})
                    findings.append({'source': source, 'status': 'OK', 'candidate_answer': obj['candidate_answer'], 'supporting_evidence': sup,
                                     'confidence': obj['confidence'], 'invalid_supporting_ids': obj['invalid_ids']})
                except (ValueError, TypeError):
                    findings.append({'source': source, 'status': 'ERROR_NO_EVIDENCE', 'candidate_answer': '', 'supporting_evidence': [], 'confidence': 'low'})
            context = canonical_json({'source_findings': findings})
            d['source_findings'] = findings
            d['requests'].append({'stage': 'fusion', 'tokens': count_tokens(P.FUSION) + count_tokens('QUESTION\n' + q + '\n\nEVIDENCE\n' + context)})
            ranked = tuple(papers)
        if self.call:
            try:
                if m == 'CF-03':
                    stage_prompt = P.FUSION
                    def fuse_call(stage):
                        raw = self._llm(m + ':' + stage + ':' + content_hash(q), stage_prompt, 'QUESTION\n' + q + '\n\nEVIDENCE\n' + context,
                                        seed, P.FINAL_CAP, usages, d)
                        return raw, parse_answer(raw, ranked)
                    try:
                        answer, answer_ids = fuse_call('fusion')
                    except (ValueError, TypeError):
                        d['fusion_retry'] = True
                        answer, answer_ids = fuse_call('fusion_retry')       # one exact retry, same evidence and prompt
                else:
                    answer, answer_ids = self._final(q, context, seed, ranked, usages, d)
                d['generation_status'] = 'complete'
            except (ValueError, TypeError):
                errors = (MethodError(stage='answer_parse', code='InvalidGroundedAnswer', message='Model output was not a valid grounded paper set'),)
                answer, answer_ids = None, None
                d['generation_status'] = 'error'
        else:
            d['generation_status'] = 'offline'
        d['context_characters'] = len(context)
        d['source_counts'] = {s: sum(e.source_type == s for e in kept) for s in F.SOURCES}
        d['source_coverage'] = {s: (sum(e.source_type == s for e in kept) / sum(e.source_type == s for e in items)
                                    if any(e.source_type == s for e in items) else None) for s in F.SOURCES}
        d['execution_ms'] = (time.perf_counter() - started) * 1000
        assert before == frozen.bundle.canonical_bytes() and len(context) <= BUDGET
        def total(key):
            return sum(u[key] for u in usages) if usages and all(u.get(key) is not None for u in usages) else None
        return SystemOutput(answer=answer, answer_ids=answer_ids, errors=errors, ranked_paper_ids=ranked, evidence=items, context=context,
                            retained_evidence_ids=tuple(e.evidence_id for e in kept), diagnostics=canonical_json(d),
                            observation=Observation(retrieval_ms=0., retrieval_calls=0, tool_calls=0, generation_ms=total('generation_ms'),
                                                    llm_calls=len(usages), input_tokens=total('input_tokens'), output_tokens=total('output_tokens'),
                                                    token_measurement_source='groq.response.usage' if total('input_tokens') is not None else None))
