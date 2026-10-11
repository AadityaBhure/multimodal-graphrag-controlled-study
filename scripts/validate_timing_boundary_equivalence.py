"""Prove the initialisation/timing-boundary change alters no scientific output.

Runs the ORIGINAL system.py (git 9e112a9) and the CURRENT one, with the same encoder/reranker,
on all 32 staged queries x 5 methods, and compares every scientific field. CM-03 needs LLM
keywords that do not exist yet; a deterministic, API-free TEST keyword set (content words of the
question) exercises both code paths identically. No API, no generation.
"""
from pathlib import Path
import json, re, statistics, subprocess, sys, time, types
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_rq1_repair import inputs, D
from research.evaluation.benchmark import BenchmarkReader
from research.evaluation.contracts import SystemInput
from research.baselines.stores import QueryEncoder
from research.baselines.config import BaselineOptions
from research.rq1.reranker import LocalReranker
from research.common.serialization import content_hash
import research.repair.rq1_compliance_v1 as pkg
from research.repair.rq1_compliance_v1.system import RepairedContextSystem as New

ORIGINAL_COMMIT = '9e112a9b74c5bbef5fdfee09a6951c4f983f609d'
METHODS = ('CM-B0', 'CM-B1', 'CM-01', 'CM-02', 'CM-03')
TIMING_KEYS = ('context_ms', 'initialisation_ms', 'initialised_lazily_inside_execute')


def original_class():
    src = subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', 'show', f'{ORIGINAL_COMMIT}:research/repair/rq1_compliance_v1/system.py'], cwd=ROOT).decode()
    mod = types.ModuleType('research.repair.rq1_compliance_v1._orig_system'); mod.__package__ = 'research.repair.rq1_compliance_v1'
    exec(compile(src, 'orig_system.py', 'exec'), mod.__dict__)
    return mod.RepairedContextSystem


def test_keywords(question):
    words = [w for w in dict.fromkeys(re.findall(r'[A-Za-z][A-Za-z\-]{4,}', question))][:6]
    return tuple(words or ['paper'])


def main():
    Old = original_class(); data = inputs(); reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
    queries = {q.query_id: q for q in reader.records('validation') if q.query_id in data}
    t = time.perf_counter(); encoder = QueryEncoder(ROOT / 'data/MMG_STARK_MAG', BaselineOptions())
    reranker = LocalReranker(ROOT / 'documentation/phase7/reranker_config.json', ROOT / 'artifacts/phase7/reranker')
    setup_s = time.perf_counter() - t
    cache = {q: test_keywords(data[q]['question']) for q in data}
    reference = {}
    ref_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if ref_path and ref_path.exists():   # context hashes from the pre-change static audit (independent baseline)
        for line in ref_path.read_text(encoding='utf-8').splitlines():
            r = json.loads(line); reference[(r['method'], r['query_id'])] = r['context_sha256']
    rows, init_ms, timings, first_cm01 = [], {}, {m: [] for m in METHODS}, None
    for method in METHODS:
        new = New(method, data, encoder.encode, reranker, cache); old = Old(method, data, encoder.encode, reranker, cache)
        init_ms[method] = new.initialise()          # recorded separately; BGE/MiniLM load happens here for CM-01
        for qid in sorted(data):
            q = queries[qid]; req = SystemInput(query_id=qid, question=q.question, seed=42, overlay=reader.overlay(q))
            a = new.execute(req); b = old.execute(req)
            da, db = json.loads(a.diagnostics), json.loads(b.diagnostics)
            for k in TIMING_KEYS: da.pop(k, None); db.pop(k, None)
            timings[method].append(json.loads(a.diagnostics)['context_ms'])
            if method == 'CM-01' and first_cm01 is None: first_cm01 = json.loads(a.diagnostics)['context_ms']
            ev = lambda o: content_hash([e.model_dump(mode='json') for e in o.evidence])
            row = {'method': method, 'query_id': qid, 'context_sha256': content_hash(a.context),
                   'context_identical': a.context == b.context, 'retained_ids_identical': a.retained_evidence_ids == b.retained_evidence_ids,
                   'evidence_identical': ev(a) == ev(b), 'ranked_paper_ids_identical': a.ranked_paper_ids == b.ranked_paper_ids,
                   'context_tokens_identical': a.context_tokens == b.context_tokens, 'diagnostics_identical_except_timing': da == db,
                   'matches_pre_change_static_audit_hash': (reference[(method, qid)] == content_hash(a.context)) if (method, qid) in reference else None}
            if method == 'CM-01':
                for k in ('seed_ids', 'expanded_unit_ids', 'tree_unit_ids', 'dfs_sequences', 'reranker_triplets', 'tree_scores', 'selected_unit_ids', 'scores', 'candidate_unit_count'):
                    row['cm01_' + k + '_identical'] = da[k] == db[k]
            rows.append(row)
        print(method, 'init_ms', round(init_ms[method], 1), 'median context_ms', round(statistics.median(timings[method]), 2), flush=True)
    flags = [k for k in rows[0] if k.endswith('identical') or k.endswith('_identical_except_timing') or k.startswith('cm01_')]
    flags = sorted({k for r in rows for k in r if (k.endswith('identical') or k.endswith('identical_except_timing')) })
    ok = all(r[k] for r in rows for k in flags if k in r) and all(r['matches_pre_change_static_audit_hash'] in (True, None) for r in rows)
    out = {'check': 'timing-boundary equivalence: original system.py @ ' + ORIGINAL_COMMIT + ' vs current', 'queries': len(data), 'methods': list(METHODS),
           'records_compared': len(rows), 'cm03_note': 'deterministic API-free TEST keywords (content words of the question); real CM-03 keywords do not exist yet',
           'independent_reference_hashes_available': len(reference), 'all_scientific_outputs_identical': ok,
           'initialisation_ms_by_method': init_ms, 'one_time_model_setup_seconds_outside_timers': setup_s,
           'first_cm01_context_ms_after_initialise': first_cm01,
           'context_ms_median_by_method': {m: statistics.median(v) for m, v in timings.items()},
           'context_ms_max_by_method': {m: max(v) for m, v in timings.items()}, 'rows': rows}
    (D / 'timing_boundary_equivalence.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('all_scientific_outputs_identical', ok, 'records', len(rows), 'first CM-01 context_ms', round(first_cm01, 1))


if __name__ == '__main__':
    main()
