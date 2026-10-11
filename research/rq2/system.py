"""Phase 5 runner adapter with measured, explicitly requested late generation."""
import json
import time
from pathlib import Path
from research.common.contracts import MethodError
from research.common.serialization import canonical_json, content_hash
from research.evaluation.benchmark import digest
from research.evaluation.contracts import Observation, SystemOutput
from research.baselines.generation import PROMPT, parse_answer
from .contracts import SOURCES, evidence
from .fusion import fuse, paper_id

class FusionSystem:
    version = '1'
    def __init__(self, options, inputs, journal=None):
        self.options, self.inputs, self.journal = options, inputs, journal
        self.system_id = options.method
        self.fingerprint = content_hash({'options': options.model_dump(),
            'inputs': {k: v.fingerprint() for k, v in sorted(inputs.items())},
            'generator': journal.version if journal else 'offline', 'prompt': PROMPT,
            'code': {p.name: digest(p) for p in Path(__file__).parent.glob('*.py')}})

    def execute(self, request):
        started = time.perf_counter()
        frozen = self.inputs[request.query_id]
        if frozen.question != request.question or frozen.overlay_hash != (content_hash(request.overlay) if request.overlay else None):
            raise ValueError('Frozen query/overlay mismatch')
        before = frozen.bundle.canonical_bytes()
        context, kept, d = fuse(frozen, self.options)
        d['upstream_provenance'] = json.loads(frozen.provenance)
        d['stage_results'] = []
        answer, answer_ids, errors = None, None, ()
        late = self.options.method == 'CF-03'
        ranked = tuple(dict.fromkeys(paper_id(e) for e in kept if paper_id(e) is not None))
        usages = []
        attempted = 0
        cache_hits = 0
        if self.journal:
            try:
                if late:
                    intermediate = []
                    for source in SOURCES:
                        source_items = [e for e in kept if e.source_type == source]
                        allowed = [paper_id(e) for e in source_items if paper_id(e) is not None]
                        attempted += 1
                        raw, usage, hit = self.journal.call(source, request.question,
                            d['source_contexts'][source], request.seed, frozen.fingerprint() + self.system_id)
                        usages.append(usage); cache_hits += int(hit)
                        stage = {'source': source, 'raw': raw, 'usage': usage, 'cache_hit': hit,
                                 'allowed_ids': allowed, 'evidence_ids': [e.evidence_id for e in source_items]}
                        d['stage_results'].append(stage)
                        ids = parse_answer(raw, allowed)
                        stage['answer_ids'] = list(ids)
                        intermediate.append({'source': source, 'answer_ids': list(ids), 'raw_answer': raw,
                            'evidence_ids': stage['evidence_ids'],
                            'provenance': [[p.model_dump(mode='json') for p in e.provenance] for e in source_items]})
                    context = canonical_json({'modality_intermediate_answers': intermediate})
                    if len(context) > self.options.budget:
                        raise ValueError('Late-fusion context exceeds safety cap')
                    # Final may combine source claims, but cannot invent another paper.
                    ranked = tuple(dict.fromkeys(i for row in d['stage_results'] for i in row['answer_ids']))
                attempted += 1
                raw, usage, hit = self.journal.call('final', request.question, context,
                    request.seed, frozen.fingerprint() + self.system_id)
                usages.append(usage); cache_hits += int(hit)
                d['stage_results'].append({'source': 'final', 'raw': raw, 'usage': usage, 'cache_hit': hit})
                answer_ids = parse_answer(raw, ranked)
                answer = raw
                d['generation_status'] = 'complete'
            except Exception as exc:
                errors = (MethodError(stage='generation', code=type(exc).__name__,
                    message='Generation or parsing failed; inspect durable stage journal and diagnostics.'),)
                answer, answer_ids = None, None
                d['generation_status'] = 'failed'
        else:
            d['generation_status'] = 'generation_required' if late else 'context_only'
        if late and not self.journal:
            d['prepared_context_characters'] = len(context)
            context, ranked, retained = None, None, None
        else:
            retained = tuple(e.evidence_id for e in kept)
        d['journal_cache_hits'] = cache_hits
        d['attempted_stages'] = attempted
        d['measured_completed_calls'] = sum(u.get('llm_calls', 0) for u in usages)
        # Unknown transport billing/usage remains NULL. Cached calls describe logical experiment usage.
        complete_usage = bool(usages) and len(usages) == attempted
        def total(key):
            return sum(u[key] for u in usages) if complete_usage and all(u.get(key) is not None for u in usages) else None
        d['execution_ms'] = (time.perf_counter() - started) * 1000
        d['input_unchanged'] = before == frozen.bundle.canonical_bytes()
        assert d['input_unchanged']
        measurement_sources = sorted({u.get('token_measurement_source') for u in usages if u.get('token_measurement_source')})
        return SystemOutput(answer=answer, answer_ids=answer_ids, errors=errors,
            ranked_paper_ids=ranked, evidence=evidence(frozen), context=context,
            retained_evidence_ids=retained, diagnostics=canonical_json(d),
            observation=Observation(retrieval_ms=0., retrieval_calls=0, tool_calls=0,
                generation_ms=total('generation_ms'), llm_calls=(len(usages) if complete_usage else None) if self.journal else 0,
                input_tokens=total('input_tokens'), output_tokens=total('output_tokens'),
                token_measurement_source='+'.join(measurement_sources) if total('input_tokens') is not None or total('output_tokens') is not None else None))
