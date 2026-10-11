"""Shared retrieval tools (identical for AR-B0/B1/01/02/03) and the fixed downstream context/generation stack.

Tools wrap the UNCHANGED frozen B1/B2/B3 retrieval functions. Nothing here strengthens a retriever:
the only adaptation is the *string* a controller hands to the tool (retrieval query / entities / structured intent).
Downstream stack (fixed for every policy): per-source budget 8,000 chars (B4's build_context rule),
source-separated sections in Text->Graph->Structured order for the sources that were actually queried,
shared final-answer prompt, shared parser, shared generator settings.
"""
from pathlib import Path
import json, time
from research.common.contracts import EvidenceItem
from research.common.serialization import canonical_json, content_hash
from research.evaluation.benchmark import digest
from research.experiments.config import durable_write
from research.baselines.retrieval import text_retrieve, graph_retrieve, structured_retrieve
from research.baselines.system import build_context, apply_overlay
from research.baselines.generation import PROMPT, parse_answer
from research.agentic.rule_router import normalize, SOURCE_ORDER

PER_SOURCE_CHARS = 8000
FINAL_CAP = 1024
RETRIEVERS = {'text': text_retrieve, 'graph': graph_retrieve, 'structured': structured_retrieve}


class ToolCall:
    def __init__(self, source, query, evidence, details, latency_ms, cache_hit):
        self.source, self.query, self.evidence, self.details = source, query, tuple(evidence), details
        self.latency_ms, self.cache_hit = latency_ms, cache_hit


class Tools:
    """retrieve_text / retrieve_graph / query_structured with a durable result cache (original latency is kept)."""

    def __init__(self, store, options, cache_root=None):
        self.store, self.options = store, options
        self.cache_root = Path(cache_root) if cache_root else None
        base = Path(__file__).resolve().parents[1] / 'baselines'
        self.fingerprint = content_hash({n: digest(base / (n + '.py')) for n in ('retrieval', 'stores', 'structured')})
        self.log = []

    def query_for(self, source, retrieval_query, entities=(), structured_intent=None):
        if source == 'graph' and entities:
            return (retrieval_query + ' ' + ' '.join(entities)).strip()
        if source == 'structured':
            return (structured_intent or retrieval_query).strip()
        return retrieval_query.strip()

    def call(self, source, retrieval_query, entities=(), relations=(), structured_intent=None):
        if source not in RETRIEVERS:
            raise ValueError('Unknown retrieval source')
        query = self.query_for(source, retrieval_query, tuple(entities), structured_intent)
        key = content_hash({'source': source, 'query': query, 'options': self.options.model_dump(), 'fp': self.fingerprint,
                            'representation': self.store.manifest_hash})
        path = self.cache_root / (key + '.json') if self.cache_root else None
        if path is not None and path.exists():
            row = json.loads(path.read_text(encoding='utf-8'))
            call = ToolCall(source, query, [EvidenceItem.model_validate(e) for e in row['evidence']], row['details'], row['latency_ms'], True)
        else:
            start = time.perf_counter()
            items, details = RETRIEVERS[source](self.store, query, self.options)
            latency = (time.perf_counter() - start) * 1000
            call = ToolCall(source, query, items, details, latency, False)
            if path is not None:
                self.cache_root.mkdir(parents=True, exist_ok=True)
                durable_write(path, canonical_json({'source': source, 'query': query, 'latency_ms': latency, 'details': details,
                                                    'evidence': [e.model_dump(mode='json') for e in items]}) + '\n')
        call.relations_ignored = tuple(relations)   # B2 takes a query string only; relations are logged, never used to strengthen it
        self.log.append(call)
        return call


def fixed_context(items, queried, store, overlay, options):
    """Fixed per-source budget + source-separated sections for the sources actually queried."""
    class _Req:  # apply_overlay only needs .overlay
        pass
    req = _Req(); req.overlay = overlay
    items, overlay_info = apply_overlay(store, tuple(items), req, tuple(queried), options)
    sections, retained, truncated = [], [], []
    for source in SOURCE_ORDER:
        if source not in queried:
            continue
        text, kept, trunc = build_context(tuple(e for e in items if e.source_type == source), (source,), PER_SOURCE_CHARS)
        sections.append(text); retained.extend(kept); truncated.extend(trunc)
    return ''.join(sections), tuple(retained), truncated, items, overlay_info


def final_user_message(question, context):
    return 'QUESTION\n' + question + '\n\nEVIDENCE\n' + context


def generate_final(llm, question, context, allowed, seed):
    """Shared final generator (frozen prompt, 1,024 cap). Returns (raw, answer_ids|None, LLMResult, parse_error)."""
    result = llm.chat('final', PROMPT, final_user_message(question, context), FINAL_CAP, seed)
    try:
        return result.raw, parse_answer(result.raw, allowed), result, None
    except (ValueError, TypeError) as exc:
        return result.raw, None, result, type(exc).__name__
