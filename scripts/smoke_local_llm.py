"""Smoke test of the local model backend on TRAIN-split queries only (never a study cohort). Writes artifacts/phase9/smoke_local_report.json.

Checks the frozen prompt roles for JSON validity, latency and determinism: RQ1 keyword extraction and final answer, RQ2
selector / per-source reasoning / fusion (on evidence of a train query), and the five RQ3 policies (run separately via
run_phase9.py --mode smoke --local).
"""
from pathlib import Path
import json, statistics, sys, tempfile, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.local_llm import chat, LOCAL_MODEL
from research.baselines.generation import PROMPT, parse_answer
from research.repair.rq1_compliance_v1.cm03 import KEYWORD_PROMPT
from research.repair.rq2_canonical import prompts as P, fusion as F
from research.evaluation.benchmark import BenchmarkReader


def payload(system, user, cap, seed=42):
    return {'model': LOCAL_MODEL, 'temperature': 0, 'seed': seed, 'max_completion_tokens': cap, 'reasoning_effort': 'low',
            'response_format': {'type': 'json_object'}, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}


def timed(p):
    t = time.perf_counter(); raw, usage, finish, _ = chat(p); return raw, usage, finish, (time.perf_counter() - t) * 1000


def main():
    reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
    train = [q for q in reader.records('train') if q.provenance['source'] == 'generated'][:3]
    rows = []
    def check(role, p, validate):
        raw, usage, finish, ms = timed(p)
        try:
            validate(raw); ok = True; err = None
        except Exception as exc:
            ok, err = False, type(exc).__name__
        rows.append({'role': role, 'ok': ok, 'error': err, 'ms': ms, 'usage': usage, 'finish': finish, 'raw_head': raw[:160]})
        print(role, 'OK' if ok else 'FAIL ' + str(err), round(ms), 'ms', usage, flush=True)
        return raw
    # RQ1 keyword extraction (CM-03)
    for q in train:
        check('rq1_keywords', payload(KEYWORD_PROMPT, q.question, 1024),
              lambda raw: (lambda v: isinstance(v.get('keywords'), list) and all(isinstance(x, str) for x in v['keywords']) or (_ for _ in ()).throw(ValueError()))(json.loads(raw)))
    # evidence of a train query from the frozen tool cache (RQ3 smoke run populates it)
    rec = next((json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT / 'artifacts/phase9/smoke/AR-B0/records').glob('*.json'))), None)
    from research.common.contracts import EvidenceItem
    items = [EvidenceItem.model_validate(e) for e in rec['output']['evidence']] if rec else []
    question = rec and next(q.question for q in reader.records('train') if q.query_id == rec['query_id'])
    if items:
        ctx = '\n'.join(F.LABEL[e.source_type] + ' ' + F.serialize(e) for e in items)[:12000]
        allowed = [F.paper_id(e) for e in items]
        # final answer (shared prompt used by RQ1 / RQ2 / RQ3)
        for seed in (1, 2):
            check('final_answer', payload(PROMPT, 'QUESTION\n' + question + '\n\nEVIDENCE\n' + ctx, 1024, seed), lambda raw: parse_answer(raw, allowed))
        # RQ2 selector
        structural = [e for e in items if e.source_type != 'text']
        man, offered = F.manifest(structural, lambda t: len(t) // 4, P.SELECTOR_INPUT_BUDGET)
        check('rq2_selector', payload(P.SELECTOR, 'QUESTION\n' + question + '\n\nCANDIDATES\n' + man, P.SELECTOR_CAP),
              lambda raw: F.parse_selection(raw, {e.evidence_id for e in offered}))
        # RQ2 per-source reasoning + fusion
        for source in ('text', 'graph', 'structured'):
            own = [e for e in items if e.source_type == source]
            if own:
                sec = '\n'.join(F.serialize(e) for e in own)[:8000]
                check('rq2_reasoning', payload(P.REASONING, 'QUESTION\n' + question + '\n\nSOURCE ' + source.upper() + '\n' + sec, P.REASONING_CAP),
                      lambda raw, own=own: F.parse_intermediate(raw, {e.evidence_id for e in own}))
        findings = json.dumps({'source_findings': [{'source': 'text', 'status': 'OK', 'candidate_answer': 'see ids', 'confidence': 'low',
                                                    'supporting_evidence': [{'evidence_id': items[0].evidence_id, 'paper_id': allowed[0]}]}]})
        check('rq2_fusion', payload(P.FUSION, 'QUESTION\n' + question + '\n\nEVIDENCE\n' + findings, P.FINAL_CAP), lambda raw: parse_answer(raw, allowed[:1]))
        # determinism: identical payload twice
        p = payload(PROMPT, 'QUESTION\n' + question + '\n\nEVIDENCE\n' + ctx, 1024, 7)
        a, b = chat(p)[0], chat(p)[0]
        rows.append({'role': 'determinism', 'ok': a == b, 'error': None if a == b else 'outputs differ', 'ms': None, 'usage': None})
        print('determinism', 'identical' if a == b else 'DIFFERENT', flush=True)
    by = {}
    for r in rows:
        by.setdefault(r['role'], []).append(r)
    summary = {role: {'n': len(v), 'ok': sum(x['ok'] for x in v), 'median_ms': statistics.median([x['ms'] for x in v if x['ms']]) if any(x['ms'] for x in v) else None}
               for role, v in by.items()}
    out = {'model': LOCAL_MODEL, 'summary': summary, 'rows': rows}
    (ROOT / 'artifacts/phase9/smoke_local_report.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
