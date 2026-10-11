"""Prepare exact static API payloads and bounded late-fusion call exposure; no API."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_phase8 import D, load_inputs, immutable_write
from research.rq2.contracts import METHODS, Options, SOURCES
from research.rq2.fusion import fuse
from research.baselines.generation import PROMPT
from research.common.serialization import content_hash
from research.evaluation.benchmark import BenchmarkReader, digest

def main():
    inputs = load_inputs()
    queries = {q.query_id: q for q in BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark').records('validation')}
    base = sorted(k for k in inputs if queries[k].modality_class == 'TGS' and k.endswith(':normal'))[0]
    ids = [base, base.removesuffix(':normal') + ':conflict']
    payloads = []
    for qid in ids:
        frozen = inputs[qid]
        seed = int(content_hash({'seed': 42, 'query_id': qid})[:8], 16)
        for method in METHODS:
            context, _, d = fuse(frozen, Options(method=method))
            contexts = d['source_contexts'] if method == 'CF-03' else {'final': context}
            for stage, value in contexts.items():
                payloads.append({'query_id': qid, 'method': method, 'stage': stage,
                    'model': 'openai/gpt-oss-120b', 'temperature': 0, 'seed': seed, 'reasoning_effort': 'low',
                    'max_completion_tokens': 1024 if stage == 'final' else 220,
                    'response_format': {'type': 'json_object'},
                    'messages': [{'role': 'system', 'content': PROMPT},
                        {'role': 'user', 'content': 'QUESTION\n' + frozen.question + '\n\nEVIDENCE\n' + value}]})
    immutable_write(D / 'generation_payload_previews.json', {'payloads': payloads})
    plan = {'query_ids': ids, 'selection': 'lexicographically first paired TGS normal/conflict; fixed before outcomes',
        'destination': 'https://api.groq.com/openai/v1/chat/completions',
        'model': 'openai/gpt-oss-120b', 'maximum_calls': 16, 'final_calls': 10,
        'intermediate_calls': 6, 'maximum_completion_tokens': 11560,
        'static_payload_count': len(payloads),
        'static_input_characters': sum(len(m['content']) for p in payloads for m in p['messages']),
        'dynamic_final_calls': 2, 'dynamic_final_context_cap_each': 24000,
        'input_tokens': None, 'estimated_cost': None,
        'token_limit_note': 'Completion cap includes provider reasoning tokens. No identified input tokenizer/pricing configured.',
        'dynamic_payload_rule': 'CF-03 final: only three logged intermediate responses, their evidence IDs and provenance; frozen system prompt/question; no gold',
        'bundle_manifest_sha256': digest(D / 'bundle_manifest.json'),
        'payload_previews_sha256': digest(D / 'generation_payload_previews.json'),
        'authorization': 'requires explicit user approval; this file alone is not approval'}
    immutable_write(D / 'generation_plan.json', plan)
    print(plan)

if __name__ == '__main__': main()
