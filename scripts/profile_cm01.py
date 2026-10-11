"""Read-only timing profile of the frozen repaired CM-01 on one real staged query.

Wraps (never edits) the frozen functions with timers, runs the unchanged
RepairedContextSystem cold and warm, verifies the output hash is identical, and
writes documentation/rq1_repair/cm01_profile.json. No API/Groq access.
"""
from pathlib import Path
import cProfile, io, json, pstats, sys, time, hashlib
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
QUERY = 'generated:5692e57aa6e252201105:conflict'
T0 = time.perf_counter()
from scripts.run_rq1_repair import inputs, D
from research.evaluation.benchmark import BenchmarkReader
from research.evaluation.contracts import SystemInput
from research.baselines.stores import QueryEncoder
from research.baselines.config import BaselineOptions
from research.rq1.reranker import LocalReranker
from research.repair.rq1_compliance_v1 import cm01, system as syst
from research.rq1 import manager as mgr
from research.common.serialization import content_hash, canonical_json
from scripts.audit_stark_mag import process_memory
IMPORT_S = time.perf_counter() - T0

TIMES, CALLS = {}, {}


def timed(name, fn):
    def wrapper(*a, **k):
        t = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            TIMES[name] = TIMES.get(name, 0.) + time.perf_counter() - t
            CALLS[name] = CALLS.get(name, 0) + 1
    return wrapper


class Proxy:
    def __init__(self, inner, name): object.__setattr__(self, '_i', inner); object.__setattr__(self, '_n', name)
    def __call__(self, *a, **k):
        t = time.perf_counter()
        try:
            return self._i(*a, **k)
        finally:
            TIMES[self._n] = TIMES.get(self._n, 0.) + time.perf_counter() - t
            CALLS[self._n] = CALLS.get(self._n, 0) + 1
    def __getattr__(self, n): return getattr(self._i, n)


def reset():
    TIMES.clear(); CALLS.clear()


def main():
    out = {'query_id': QUERY, 'script': 'scripts/profile_cm01.py', 'import_seconds': IMPORT_S}
    t = time.perf_counter(); data = inputs(); out['load_all_32_staged_inputs_seconds'] = time.perf_counter() - t
    t = time.perf_counter(); reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
    q = next(r for r in reader.records('validation') if r.query_id == QUERY); overlay = reader.overlay(q)
    out['benchmark_reader_and_overlay_seconds'] = time.perf_counter() - t
    t = time.perf_counter(); encoder = QueryEncoder(ROOT / 'data/MMG_STARK_MAG', BaselineOptions()); out['minilm_onnx_session_construct_seconds'] = time.perf_counter() - t
    t = time.perf_counter(); reranker = LocalReranker(ROOT / 'documentation/phase7/reranker_config.json', ROOT / 'artifacts/phase7/reranker')
    out['bge_construct_incl_model_file_sha256_seconds'] = time.perf_counter() - t
    t = time.perf_counter(); reranker.load(); out['bge_model_and_tokenizer_load_seconds'] = time.perf_counter() - t
    out['bge_model_dir_bytes'] = sum(p.stat().st_size for p in reranker.model_dir.iterdir() if p.is_file())
    # Timers around frozen internals (module attributes / proxies only).
    cm01.canonical_units = timed('canonical_units', cm01.canonical_units)
    cm01.cosine_scores = timed('cosine_scores_total', cm01.cosine_scores)
    cm01.maximum_forest = timed('maximum_forest', cm01.maximum_forest)
    cm01.tree_sequences = timed('tree_sequences_dfs', cm01.tree_sequences)
    syst.evidence = timed('evidence_all_pool_items', syst.evidence)
    mgr.Manager.manage = timed('Manager.manage_CM-B0_reference', mgr.Manager.manage)
    enc_inner = encoder.encode
    encoder.encode = timed('minilm_encode_calls', enc_inner)
    reranker.tokenizer = Proxy(reranker.tokenizer, 'bge_tokenization')
    reranker.model = Proxy(reranker.model, 'bge_forward')
    reranker_call = type(reranker).__call__
    type(reranker).__call__ = lambda self, query, texts: timed('bge_rerank_total', reranker_call)(self, query, texts)
    system = syst.RepairedContextSystem('CM-01', data, encoder.encode, reranker)
    request = SystemInput(query_id=QUERY, question=q.question, seed=42, overlay=overlay)
    runs = []
    for label in ('first_execute', 'second_execute', 'third_execute'):
        reset(); mem0 = process_memory(); t = time.perf_counter()
        result = system.execute(request)
        wall = time.perf_counter() - t
        d = json.loads(result.diagnostics)
        runs.append({'label': label, 'wall_seconds': wall, 'reported_context_ms': d['context_ms'], 'stage_seconds': dict(TIMES), 'stage_calls': dict(CALLS),
                     'context_sha256': content_hash(result.context), 'context_chars': len(result.context), 'context_tokens_o200k': result.context_tokens,
                     'diagnostics_sha256': content_hash({k: v for k, v in d.items() if k != 'context_ms'}),
                     'retained_evidence_ids_sha256': content_hash(list(result.retained_evidence_ids)),
                     'retained_evidence_ids': list(result.retained_evidence_ids), 'memory': process_memory(),
                     'candidate_unit_count': d['candidate_unit_count'], 'seed_ids': d['seed_ids'],
                     'expanded_units': len(d['expanded_unit_ids']), 'forest_edges': len(d['tree_unit_ids']), 'dfs_trees': len(d['dfs_sequences']),
                     'tree_sizes': [len(s) for s in d['dfs_sequences']], 'tree_scores': d['tree_scores'],
                     'reranker_truncated_pairs': d['reranker_truncated_pairs'], 'fallback': d['fallback']})
        print(label, round(wall, 2), runs[-1]['context_sha256'], flush=True)
    out['runs'] = runs
    # Detailed function profile of one more warm execution.
    reset(); prof = cProfile.Profile(); prof.enable(); r = system.execute(request); prof.disable()
    s = io.StringIO(); pstats.Stats(prof, stream=s).sort_stats('cumulative').print_stats(30)
    out['cprofile_warm_top30_cumulative'] = s.getvalue()
    out['cprofile_context_sha256'] = content_hash(r.context)
    # Per-tree BGE cost (same scoring call, timed per text, scores compared).
    d = json.loads(r.diagnostics); trip = d['reranker_triplets']
    per = []
    for text in trip:
        tt = time.perf_counter(); sc = reranker(q.question, [text])[0]; per.append({'seconds': time.perf_counter() - tt, 'chars': len(text), 'score': sc})
    out['bge_per_tree_warm'] = per
    out['bge_scores_match_pipeline'] = [p['score'] for p in per] == d['tree_scores']
    out['context_sha256_expected_from_capacity_blocker'] = '9bd8fb8f9752923f3de479b554aadf53e8afc635a8748fe28cb089add486b740'
    out['context_matches_capacity_blocker'] = runs[0]['context_sha256'] == out['context_sha256_expected_from_capacity_blocker']
    out['all_runs_identical_context'] = len({x['context_sha256'] for x in runs}) == 1 and runs[0]['context_sha256'] == out['cprofile_context_sha256']
    out['total_wall_seconds'] = time.perf_counter() - T0
    out['output_hash'] = content_hash({'context_sha256': runs[0]['context_sha256'], 'retained': runs[0]['retained_evidence_ids']})
    path = ROOT / 'documentation/rq1_repair/cm01_profile.json'
    path.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + '\n', encoding='utf-8', newline='\n')
    print('WROTE', path, 'identical', out['all_runs_identical_context'], 'matches_blocker', out['context_matches_capacity_blocker'], flush=True)


if __name__ == '__main__':
    main()
