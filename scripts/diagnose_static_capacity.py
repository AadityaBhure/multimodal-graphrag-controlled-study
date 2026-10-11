"""Static (no API) capacity audit of every statically constructable RQ1 final request.

Builds each CM-B0/CM-B1/CM-01/CM-02 final-answer payload with the frozen, unchanged
RepairedContextSystem (offline mode), measures it with the pinned tokenizer, and
bounds CM-03 (dynamic: needs LLM keywords) with a sound upper bound. Never
dispatches anything and does not stop at the first oversized request.

usage: diagnose_static_capacity.py WORK_JSONL
"""
from pathlib import Path
import csv, json, sys, time, hashlib
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tiktoken
from research.common.serialization import content_hash, canonical_json
from scripts.run_rq1_repair import inputs, D
from research.evaluation.benchmark import BenchmarkReader
from research.evaluation.contracts import SystemInput
from research.baselines.stores import QueryEncoder
from research.baselines.config import BaselineOptions
from research.baselines.generation import PROMPT
from research.rq1.reranker import LocalReranker
from research.rq1.contracts import Pool
from research.rq1.manager import node_text, edge_text
from research.repair.rq1_compliance_v1.system import RepairedContextSystem
from research.repair.rq1_compliance_v1.cm03 import KEYWORD_PROMPT

ENC = tiktoken.get_encoding('o200k_harmony')
ENVELOPE, CAP, LIMIT, PROVIDER_OVERHEAD = 256, 1024, 8000, 102   # 102 = measured provider-minus-local (Phase 8 v2, 10/10 requests)
METHODS = ('CM-B0', 'CM-B1', 'CM-01', 'CM-02')
T = lambda s: ENC.encode(s, disallowed_special=())


def meta(qid, data):
    cond = qid.rsplit(':', 1)[1]
    mod = ''.join(sorted({'text': 'T', 'graph': 'G', 'structured': 'S'}[s] for s in data['sources']))
    return cond, {'G': 'G', 'GT': 'TG', 'GS': 'GS', 'GST': 'TGS'}.get(mod, mod)


def cm03_upper_bound(data):
    """Sound upper bound on CM-03's final user-message tokens (graph part replaced by a fractional-knapsack bound)."""
    pool = Pool.model_validate(data['pool'])
    budget = data['source_budget'] - len('[GRAPH]\n')
    overlays = data['graph_conflict_overlays']
    overlay_text = '\n'.join(e['evidence_id'] + ' ' + e['payload'] for e in overlays)
    budget -= len(overlay_text) + (1 if overlay_text else 0)
    lines = []
    for n in pool.nodes:
        obj = json.loads(node_text(n)); obj['connector'] = True
        lines.append(canonical_json(obj))
    for e in pool.edges:
        lines.append(edge_text(e))
    items = sorted(((len(T(l)) + 1, len(l) + 1) for l in lines), key=lambda x: -x[0] / x[1])
    bound, left = 0., budget + 1
    for t, c in items:
        if left <= 0: break
        take = min(1., left / c); bound += t * take; left -= c * take
    # fixed parts: pass-through contexts for other sources + overlay text + headers
    fixed = 0
    for s in data['sources']:
        fixed += len(T('[GRAPH]\n' + overlay_text)) if s == 'graph' else len(T(data['pass_through'][s]['context']))
    question = len(T('QUESTION\n' + data['question'] + '\n\nEVIDENCE\n'))
    return int(bound) + 1 + fixed + question + len(T(PROMPT))


def main(work):
    work = Path(work); data = inputs(); reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
    queries = {q.query_id: q for q in reader.records('validation') if q.query_id in data}
    done = {}
    if work.exists():
        for line in work.read_text(encoding='utf-8').splitlines():
            r = json.loads(line); done[(r['method'], r['query_id'])] = r
    encoder = QueryEncoder(ROOT / 'data/MMG_STARK_MAG', BaselineOptions())
    reranker = LocalReranker(ROOT / 'documentation/phase7/reranker_config.json', ROOT / 'artifacts/phase7/reranker')
    started = time.perf_counter()
    for method in METHODS:
        system = RepairedContextSystem(method, data, encoder.encode, reranker)
        for qid in sorted(data):
            if (method, qid) in done: continue
            q = queries[qid]; t0 = time.perf_counter()
            out = system.execute(SystemInput(query_id=qid, question=q.question, seed=42, overlay=reader.overlay(q)))
            assert not out.errors and out.answer is None
            user = 'QUESTION\n' + q.question + '\n\nEVIDENCE\n' + out.context
            ut = T(user)
            row = {'method': method, 'query_id': qid, 'context_sha256': content_hash(out.context), 'context_chars': len(out.context),
                   'message_sha256': content_hash([{'role': 'system', 'content': PROMPT}, {'role': 'user', 'content': user}]),
                   'system_tokens': len(T(PROMPT)), 'user_tokens': len(ut), 'user_token_ids': ut, 'seconds': time.perf_counter() - t0,
                   'fallback': json.loads(out.diagnostics).get('fallback')}
            with work.open('a', encoding='utf-8') as f: f.write(json.dumps(row) + '\n')
            done[(method, qid)] = row
            print(method, qid, row['user_tokens'] + row['system_tokens'] + ENVELOPE + CAP, round(row['seconds'], 1), flush=True)
    # ---- assemble the audit
    rows = []
    prefix_by_query = {}
    for qid in sorted(data):
        lists = [done[(m, qid)]['user_token_ids'] for m in METHODS]
        n = 0
        while all(n < len(l) for l in lists) and len({l[n] for l in lists}) == 1: n += 1
        sys_tokens = done[('CM-B0', qid)]['system_tokens']
        prefix_by_query[qid] = {'system_tokens': sys_tokens, 'user_common_prefix_tokens': n, 'local_common_prefix_tokens': sys_tokens + n,
                                'user_common_prefix_sha256': hashlib.sha256(ENC.decode(lists[0][:n]).encode('utf-8')).hexdigest(),
                                'divergence_text_preview': ENC.decode(lists[0][max(0, n - 6):n + 6])}
    for method in METHODS:
        for qid in sorted(data):
            r = done[(method, qid)]; cond, mod = meta(qid, data[qid]); content = r['system_tokens'] + r['user_tokens']
            reserve = content + ENVELOPE + CAP
            rows.append({'query_id': qid, 'stress': cond, 'modality': mod, 'method': method, 'stage': 'final_answer', 'status': 'STATIC',
                         'message_sha256': r['message_sha256'], 'context_sha256': r['context_sha256'], 'context_chars': r['context_chars'],
                         'system_tokens': r['system_tokens'], 'user_tokens': r['user_tokens'], 'local_content_tokens': content, 'completion_cap': CAP,
                         'envelope_reserve_current': ENVELOPE, 'reservation_current': reserve, 'passes_8000_current': reserve <= LIMIT,
                         'over_under_8000_current': reserve - LIMIT, 'headroom_current': LIMIT - reserve,
                         'common_prefix_tokens_local': prefix_by_query[qid]['local_common_prefix_tokens'],
                         'provider_prompt_estimate_measured_overhead': content + PROVIDER_OVERHEAD,
                         'reservation_measured_overhead': content + PROVIDER_OVERHEAD + CAP,
                         'over_under_8000_measured_overhead': content + PROVIDER_OVERHEAD + CAP - LIMIT})
    for qid in sorted(data):
        cond, mod = meta(qid, data[qid]); ub = cm03_upper_bound(data[qid])
        rows.append({'query_id': qid, 'stress': cond, 'modality': mod, 'method': 'CM-03', 'stage': 'final_answer', 'status': 'DYNAMIC_NOT_YET_CONSTRUCTABLE',
                     'message_sha256': None, 'context_sha256': None, 'context_chars': None, 'system_tokens': len(T(PROMPT)), 'user_tokens': None,
                     'local_content_tokens_upper_bound': ub, 'completion_cap': CAP, 'envelope_reserve_current': ENVELOPE,
                     'reservation_current_upper_bound': ub + ENVELOPE + CAP, 'passes_8000_current': None,
                     'over_under_8000_current': None, 'headroom_current': None,
                     'common_prefix_tokens_local': None, 'depends_on_cm03_keyword_generation': True,
                     'reservation_measured_overhead_upper_bound': ub + PROVIDER_OVERHEAD + CAP})
        kw = len(T(KEYWORD_PROMPT)) + len(T(data[qid]['question']))
        rows.append({'query_id': qid, 'stress': cond, 'modality': mod, 'method': 'CM-03', 'stage': 'keyword_extraction', 'status': 'STATIC',
                     'message_sha256': content_hash([{'role': 'system', 'content': KEYWORD_PROMPT}, {'role': 'user', 'content': data[qid]['question']}]),
                     'system_tokens': len(T(KEYWORD_PROMPT)), 'user_tokens': len(T(data[qid]['question'])), 'local_content_tokens': kw,
                     'completion_cap': CAP, 'envelope_reserve_current': ENVELOPE, 'reservation_current': kw + ENVELOPE + CAP,
                     'passes_8000_current': kw + ENVELOPE + CAP <= LIMIT, 'over_under_8000_current': kw + ENVELOPE + CAP - LIMIT,
                     'headroom_current': LIMIT - (kw + ENVELOPE + CAP), 'reservation_measured_overhead': kw + PROVIDER_OVERHEAD + CAP})
    static = [r for r in rows if r['status'] == 'STATIC']
    fin = [r for r in static if r['stage'] == 'final_answer']
    over = [r for r in fin if not r['passes_8000_current']]
    mid = [r for r in fin if r['passes_8000_current'] and r['reservation_current'] >= 7500]
    low = [r for r in fin if r['reservation_current'] < 7500]
    top = max(fin, key=lambda r: r['reservation_current'])
    cm03 = [r for r in rows if r['method'] == 'CM-03' and r['stage'] == 'final_answer']
    by_method = {m: {'n': sum(r['method'] == m for r in fin), 'max_reservation_current': max(r['reservation_current'] for r in fin if r['method'] == m),
                     'over_8000_current': sum(not r['passes_8000_current'] for r in fin if r['method'] == m),
                     'over_8000_measured_overhead': sum(r['over_under_8000_measured_overhead'] > 0 for r in fin if r['method'] == m),
                     'median_local_content_tokens': sorted(r['local_content_tokens'] for r in fin if r['method'] == m)[sum(r['method'] == m for r in fin) // 2]} for m in METHODS}
    summary = {'limit_tokens': LIMIT, 'static_final_requests': len(fin), 'static_keyword_requests': len(static) - len(fin),
               'dynamic_not_constructable_final_requests_cm03': len(cm03),
               'max_reservation_current': top['reservation_current'], 'max_reservation_request': {k: top[k] for k in ('method', 'query_id', 'stress', 'modality')},
               'count_over_8000_current': len(over), 'count_7500_to_8000_current': len(mid), 'count_below_7500_current': len(low),
               'count_over_8000_measured_overhead_102': sum(r['over_under_8000_measured_overhead'] > 0 for r in fin),
               'count_over_8000_without_any_envelope_reserve': sum(r['local_content_tokens'] + CAP > LIMIT for r in fin),
               'headroom_current_min_max_median': [min(r['headroom_current'] for r in fin), max(r['headroom_current'] for r in fin),
                                                   sorted(r['headroom_current'] for r in fin)[len(fin) // 2]],
               'oversized_requests': [{k: r[k] for k in ('method', 'query_id', 'stress', 'modality', 'local_content_tokens', 'reservation_current', 'over_under_8000_current', 'over_under_8000_measured_overhead')} for r in sorted(over, key=lambda r: -r['reservation_current'])],
               'cm03_upper_bound_reservation_current_max': max(r['reservation_current_upper_bound'] for r in cm03),
               'cm03_upper_bound_over_8000_count_current': sum(r['reservation_current_upper_bound'] > LIMIT for r in cm03),
               'calls_that_depend_on_cm03_keyword_generation': len(cm03), 'by_method': by_method,
               'common_prefix_local_tokens_min_max': [min(p['local_common_prefix_tokens'] for p in prefix_by_query.values()), max(p['local_common_prefix_tokens'] for p in prefix_by_query.values())]}
    out = {'audit_id': 'rq1-static-capacity-audit-v1', 'tokenizer': 'tiktoken-0.12.0:o200k_harmony', 'policy_current': 'content + 256 + 1024 <= 8000',
           'measured_provider_overhead_tokens_used_for_alternative_columns': PROVIDER_OVERHEAD,
           'wall_seconds': time.perf_counter() - started, 'summary': summary, 'common_prefix_by_query': prefix_by_query, 'rows': rows}
    (ROOT / 'documentation/rq1_repair/current_capacity_audit.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    cols = sorted({k for r in rows for k in r})
    with (ROOT / 'documentation/rq1_repair/current_capacity_audit.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
