"""Prove the initialisation/timing-boundary change alters no scientific output.

Runs the ORIGINAL system.py (git 9e112a9) and the CURRENT one, with the same encoder/reranker,
on all 32 staged queries x 5 methods, and compares every scientific field. CM-03 needs LLM
keywords that do not exist yet; a deterministic, API-free TEST keyword set (content words of the
question) exercises both code paths identically. No API, no generation.

Durable and resumable: every (method, query) comparison is written as its own record, so the
slow CM-03 diffusion can be split across processes and survive restarts.

  validate_timing_boundary_equivalence.py --shard I --nshards N   # worker (skips finished records)
  validate_timing_boundary_equivalence.py --summarize             # writes timing_boundary_equivalence.json

Independent reference: context hashes of the static methods from the pre-change revised capacity
audit (original code on master), when present.
"""
from pathlib import Path
import argparse, json, re, statistics, subprocess, sys, time, types
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_rq1_repair import inputs, D
from research.repair.dispatch import write
from research.common.serialization import content_hash

ORIGINAL_COMMIT = '9e112a9b74c5bbef5fdfee09a6951c4f983f609d'
METHODS = ('CM-B0', 'CM-B1', 'CM-01', 'CM-02', 'CM-03')
TIMING_KEYS = ('context_ms', 'initialisation_ms', 'initialised_lazily_inside_execute')
OUT = D / 'timing_equivalence'
CM01_KEYS = ('seed_ids', 'expanded_unit_ids', 'tree_unit_ids', 'dfs_sequences', 'reranker_triplets', 'tree_scores', 'selected_unit_ids', 'scores', 'candidate_unit_count')


def original_class():
    src = subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', 'show', f'{ORIGINAL_COMMIT}:research/repair/rq1_compliance_v1/system.py'], cwd=ROOT).decode()
    mod = types.ModuleType('research.repair.rq1_compliance_v1._orig_system'); mod.__package__ = 'research.repair.rq1_compliance_v1'
    exec(compile(src, 'orig_system.py', 'exec'), mod.__dict__)
    return mod.RepairedContextSystem


def test_keywords(question):
    words = [w for w in dict.fromkeys(re.findall(r'[A-Za-z][A-Za-z\-]{4,}', question))][:6]
    return tuple(words or ['paper'])


def reference_hashes():
    """Context hashes from the pre-change static capacity audit (original code)."""
    path = D / 'revised_capacity_audit.json'
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding='utf-8'))['rows']
    return {(r['method'], r['query_id']): r['context_sha256'] for r in rows if r.get('stage') == 'final_answer' and r.get('context_sha256')}


def record_path(method, qid):
    return OUT / 'rows' / method / (content_hash(qid) + '.json')


def pairs(data):
    return [(m, q) for m in METHODS for q in sorted(data)]


def worker(shard, nshards):
    from research.evaluation.benchmark import BenchmarkReader
    from research.evaluation.contracts import SystemInput
    from research.baselines.stores import QueryEncoder
    from research.baselines.config import BaselineOptions
    from research.rq1.reranker import LocalReranker
    from research.repair.rq1_compliance_v1.system import RepairedContextSystem as New
    data = inputs()
    mine = [p for i, p in enumerate(pairs(data)) if i % nshards == shard and not record_path(*p).exists()]
    print('shard', shard, 'todo', len(mine), flush=True)
    if not mine:
        return
    Old = original_class(); reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
    queries = {q.query_id: q for q in reader.records('validation') if q.query_id in data}
    t = time.perf_counter(); encoder = QueryEncoder(ROOT / 'data/MMG_STARK_MAG', BaselineOptions())
    reranker = LocalReranker(ROOT / 'documentation/phase7/reranker_config.json', ROOT / 'artifacts/phase7/reranker')
    setup_s = time.perf_counter() - t
    cache = {q: test_keywords(data[q]['question']) for q in data}
    reference = reference_hashes(); systems = {}
    for method, qid in mine:
        if method not in systems:
            new = New(method, data, encoder.encode, reranker, cache); old = Old(method, data, encoder.encode, reranker, cache)
            systems[method] = (new, old, new.initialise())   # recorded separately; model load happens here
        new, old, init_ms = systems[method]
        q = queries[qid]; req = SystemInput(query_id=qid, question=q.question, seed=42, overlay=reader.overlay(q))
        started = time.perf_counter()
        a = new.execute(req); b = old.execute(req)
        da, db = json.loads(a.diagnostics), json.loads(b.diagnostics)
        context_ms = da.get('context_ms')
        for k in TIMING_KEYS: da.pop(k, None); db.pop(k, None)
        ev = lambda o: content_hash([e.model_dump(mode='json') for e in o.evidence])
        row = {'method': method, 'query_id': qid, 'context_sha256': content_hash(a.context),
               'context_identical': a.context == b.context, 'retained_ids_identical': a.retained_evidence_ids == b.retained_evidence_ids,
               'evidence_identical': ev(a) == ev(b), 'ranked_paper_ids_identical': a.ranked_paper_ids == b.ranked_paper_ids,
               'context_tokens_identical': a.context_tokens == b.context_tokens, 'diagnostics_identical_except_timing': da == db,
               'matches_pre_change_static_audit_hash': (reference[(method, qid)] == content_hash(a.context)) if (method, qid) in reference else None,
               'context_ms_new': context_ms, 'initialisation_ms_new': init_ms, 'worker_setup_seconds': setup_s,
               'pair_wall_seconds': time.perf_counter() - started, 'shard': shard}
        if method == 'CM-01':
            for k in CM01_KEYS:
                row['cm01_' + k + '_identical'] = da.get(k) == db.get(k)
        write(record_path(method, qid), row)
        print(method, qid, 'ok' if all(v for k, v in row.items() if k.endswith('identical') or k.endswith('_identical_except_timing')) else 'DIFF',
              round(row['pair_wall_seconds'], 1), 's', flush=True)


def summarize():
    data = inputs(); rows, missing = [], []
    for m, q in pairs(data):
        p = record_path(m, q)
        (rows.append(json.loads(p.read_text(encoding='utf-8'))) if p.exists() else missing.append((m, q)))
    flags = sorted({k for r in rows for k in r if k.endswith('identical') or k.endswith('identical_except_timing')})
    ok = (not missing and all(r[k] for r in rows for k in flags if k in r)
          and all(r['matches_pre_change_static_audit_hash'] in (True, None) for r in rows))
    diffs = [{'method': r['method'], 'query_id': r['query_id'], 'failed': [k for k in flags if k in r and not r[k]]} for r in rows if any(k in r and not r[k] for k in flags)]
    ref_checked = sum(1 for r in rows if r['matches_pre_change_static_audit_hash'] is not None)
    by = lambda m, k: [r[k] for r in rows if r['method'] == m and r.get(k) is not None]
    out = {'check': 'timing-boundary equivalence: original system.py @ ' + ORIGINAL_COMMIT + ' vs current', 'queries': len(data), 'methods': list(METHODS),
           'records_expected': len(pairs(data)), 'records_compared': len(rows), 'records_missing': [list(x) for x in missing],
           'cm03_note': 'deterministic API-free TEST keywords (content words of the question); real CM-03 keywords do not exist yet',
           'independent_reference': 'context_sha256 from revised_capacity_audit.json (pre-change code), static methods only',
           'independent_reference_checks': ref_checked, 'all_scientific_outputs_identical': ok, 'differences': diffs,
           'initialisation_ms_by_method': {m: statistics.median(by(m, 'initialisation_ms_new')) for m in METHODS if by(m, 'initialisation_ms_new')},
           'context_ms_median_by_method': {m: statistics.median(by(m, 'context_ms_new')) for m in METHODS if by(m, 'context_ms_new')},
           'context_ms_max_by_method': {m: max(by(m, 'context_ms_new')) for m in METHODS if by(m, 'context_ms_new')},
           'rows': sorted(rows, key=lambda r: (METHODS.index(r['method']), r['query_id']))}
    (D / 'timing_boundary_equivalence.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('all_scientific_outputs_identical', ok, 'records', len(rows), '/', len(pairs(data)), 'missing', len(missing), 'reference checks', ref_checked, 'differences', len(diffs))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--shard', type=int, default=0); ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('--summarize', action='store_true'); a = ap.parse_args()
    summarize() if a.summarize else worker(a.shard, a.nshards)
