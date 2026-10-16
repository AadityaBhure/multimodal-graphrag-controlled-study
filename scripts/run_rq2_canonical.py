"""Canonical RQ2 study on the 24 frozen multimodal bundles (Phase 1D §5; settings documentation/rq2_repair/RQ2_CANONICAL_SETTINGS*.md).

  --supportability  evaluator-side strata (S10), computed once before any call and frozen
  --audit           offline contexts + request sizes for every method (no API)
  --freeze          configs + execution plan (refuses to overwrite)
  --execute         query-major provider calls through the unchanged systems, then the unchanged Phase 5 runner replays
                    per method with the dispatcher in replay_only mode. Pauses at the daily budget; rerun to resume.
"""
from pathlib import Path
import argparse, json, sys, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.common.serialization import content_hash, canonical_json
from research.common.reproducibility import seed_everything
from research.evaluation.benchmark import BenchmarkReader, digest
from research.evaluation.contracts import SystemInput
from research.experiments.config import RunnerConfig
from research.experiments.runner import run, code_provenance
from research.rq2.contracts import evidence
from research.repair.dispatch import Paused, write, OVERHEAD_RESERVE
from research.repair.schedule import interleaved, prefetch
from research.repair.rq2_canonical import prompts as P
from research.repair.rq2_canonical.system import CanonicalFusionSystem, count_tokens
from research.repair.rq2_canonical.registry import load_registry
from research.repair.rq2_canonical.dispatch import SharedQuotaDispatcher
from scripts.prepare_phase8 import load_inputs
from scripts.prepare_rq1_repair import save

D = ROOT / 'documentation/rq2_repair'
BENCH = ROOT / 'data/MMG_STARK_MAG/benchmark'
METHODS = ('CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03')
MAX_CALLS = 24 * (1 + 1 + 1 + 3 + 5)          # upper bound incl. CF-02 repair and CF-03 fusion retry
EXTERNAL_LEDGERS = (ROOT / 'artifacts/phase9/llm_stages/state.json', ROOT / 'documentation/rq1_repair/dispatch/state.json')
SETTINGS = D / 'RQ2_CANONICAL_SETTINGS.md'


def requests(qids):
    reader = BenchmarkReader(BENCH); val = {q.query_id: q for q in reader.records('validation')}
    return reader, {q: val[q] for q in qids}


def supportability():
    inputs = load_inputs(); reader, qs = requests(sorted(inputs))
    rows = {}
    for qid, f in inputs.items():
        gold = set(qs[qid].gold_answer_ids)
        present = {int(e.canonical_id.split(':')[1]) for e in evidence(f) if e.canonical_id.startswith('stark:')}
        hit = gold & present
        cls = 'FULLY_SUPPORTABLE' if gold and hit == gold else 'PARTIALLY_SUPPORTABLE' if hit else 'UNSUPPORTABLE'
        rows[qid] = {'class': cls, 'gold': len(gold), 'gold_in_bundle': len(hit), 'modality': qs[qid].modality_class}
    out = {'rule': 'S10: FULLY = every gold paper is the canonical paper of some bundle evidence item; PARTIALLY = at least one; UNSUPPORTABLE = none. '
                   'Evaluator-side stratification only; computed before any RQ2 canonical call.',
           'counts': {c: sum(r['class'] == c for r in rows.values()) for c in ('FULLY_SUPPORTABLE', 'PARTIALLY_SUPPORTABLE', 'UNSUPPORTABLE')}, 'rows': rows}
    save(D / 'supportability.json', out)
    print(json.dumps(out['counts']))


def audit():
    inputs = load_inputs(); registry = load_registry(inputs); reader, qs = requests(sorted(inputs))
    worst, rows = {}, []
    for m in METHODS:
        s = CanonicalFusionSystem(m, inputs, registry)
        for qid in sorted(inputs):
            q = qs[qid]
            out = s.execute(SystemInput(query_id=qid, question=q.question, seed=1, overlay=reader.overlay(q)))
            dg = json.loads(out.diagnostics)
            for rq in dg['requests']:
                need = rq['tokens'] + OVERHEAD_RESERVE
                if rq['stage'] == 'fusion':           # fusion input is known only after the per-source calls: sound upper bound
                    need += 3 * (P.REASONING_CAP + 200)
                worst[m + ' ' + rq['stage'].split(':')[0]] = max(worst.get(m + ' ' + rq['stage'].split(':')[0], 0), need)
                rows.append({'method': m, 'query_id': qid, 'stage': rq['stage'], 'pre_dispatch_tokens': need})
    ok = all(v <= 8000 for v in worst.values())
    write(D / 'local_audit.json', {'status': 'PASS' if ok else 'FAIL', 'records': len(rows), 'max_pre_dispatch_by_stage': worst, 'rows': rows,
                                   'api_calls': 0, 'rule': 'content tokens + 128 <= 8000 (CF-03 fusion: + 3 x (220 + 200) upper bound)'})
    print('PASS' if ok else 'FAIL', worst)


def configs(inputs):
    out = []
    for m in METHODS:
        cfg = RunnerConfig(config_id='rq2-canonical-v1-' + m, system_id=m, system_version=CanonicalFusionSystem.version, query_ids=tuple(sorted(inputs)),
                           model_ids=('openai/gpt-oss-120b',), embedding_model='sentence-transformers/all-MiniLM-L6-v2', fusion_method=m,
                           retrieval_parameters={'bundle_manifest_sha256': digest(ROOT / 'documentation/phase8/bundle_manifest.json'),
                                                 'prompt_version': P.PROMPT_VERSION, 'settings_sha256': digest(SETTINGS), 'context_chars': 24000,
                                                 'final_cap': P.FINAL_CAP, 'temperature': 0, 'reasoning_effort': 'low'})
        p = D / 'configs' / (m + '.json'); save(p, cfg.model_dump(mode='json')); out.append({'path': p.relative_to(D).as_posix(), 'sha256': digest(p)})
    return out


def freeze():
    inputs = load_inputs()
    for need in (SETTINGS, D / 'supportability.json', D / 'local_audit.json'):
        if not need.exists():
            raise SystemExit('missing before freeze: ' + need.name)
    if json.loads((D / 'local_audit.json').read_text(encoding='utf-8'))['status'] != 'PASS':
        raise SystemExit('local audit has not passed')
    impl = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted((ROOT / 'research/repair/rq2_canonical').glob('*.py'))}
    for extra in ('research/repair/dispatch.py', 'research/repair/schedule.py', 'research/rq2/fusion.py', 'research/rq2/contracts.py',
                  'research/baselines/generation.py', 'scripts/run_rq2_canonical.py', 'scripts/prepare_phase8.py'):
        impl[extra] = digest(ROOT / extra)
    plan = {'version': 'rq2-canonical-v1', 'configs': configs(inputs), 'implementation_sha256': impl, 'queries': sorted(inputs),
            'settings_sha256': digest(SETTINGS), 'supportability_sha256': digest(D / 'supportability.json'), 'local_audit_sha256': digest(D / 'local_audit.json'),
            'bundle_manifest_sha256': digest(ROOT / 'documentation/phase8/bundle_manifest.json'), 'prompt_version': P.PROMPT_VERSION,
            'maximum_successful_calls': MAX_CALLS, 'model': 'openai/gpt-oss-120b', 'temperature': 0, 'reasoning_effort': 'low',
            'admission': 'content + 128 <= 8000; successful-call counting; rolling 24 h ledger 190k shared with other studies; query-major provider order; replay_only runner',
            'external_ledgers': [p.relative_to(ROOT).as_posix() for p in EXTERNAL_LEDGERS], 'test_human_test': False, 'cohort_frozen_before_outcomes': True}
    save(D / 'execution_plan.json', plan)
    print('FROZEN rq2-canonical-v1:', len(impl), 'files,', len(plan['queries']), 'bundles, max', MAX_CALLS, 'calls')


def execute():
    plan = json.loads((D / 'execution_plan.json').read_text(encoding='utf-8'))
    for p, sha in plan['implementation_sha256'].items():
        if digest(ROOT / p) != sha:
            raise SystemExit('Frozen RQ2 code changed: ' + p)
    for c in plan['configs']:
        if digest(D / c['path']) != c['sha256']:
            raise SystemExit('Frozen RQ2 config changed: ' + c['path'])
    inputs = load_inputs(); assert sorted(inputs) == plan['queries']
    registry = load_registry(inputs); reader, qs = requests(sorted(inputs))
    provenance = code_provenance(); provpath = D / 'execution_code.json'
    if provpath.exists():
        old = json.loads(provpath.read_text(encoding='utf-8'))
        if old['source_tree_hash'] != provenance['source_tree_hash']:
            raise SystemExit('Research source changed during experiment')
        provenance = old
    else:
        save(provpath, provenance)
    headers = json.loads((ROOT / 'documentation/rq1_repair/provider_preflight/diagnostic.json').read_text())['completion']['headers']
    dispatcher = SharedQuotaDispatcher(D / 'dispatch', headers, plan['maximum_successful_calls'], EXTERNAL_LEDGERS)
    cfgs = {c['path'].split('/')[-1][:-5]: RunnerConfig.model_validate_json((D / c['path']).read_text(encoding='utf-8')) for c in plan['configs']}
    try:
        ahead = {m: CanonicalFusionSystem(m, inputs, registry, dispatcher.call) for m in METHODS}
        def one(qid, m):
            seed = int(content_hash({'seed': cfgs[m].seed, 'query_id': qid})[:8], 16); seed_everything(seed)
            ahead[m].execute(SystemInput(query_id=qid, question=qs[qid].question, seed=seed, overlay=reader.overlay(qs[qid])))
        prefetch(interleaved(inputs, METHODS), one, D / 'prefetch')
        dispatcher.replay_only = True
        for m in METHODS:
            t = time.perf_counter()
            run(cfgs[m], BENCH, D / 'runs' / m, CanonicalFusionSystem(m, inputs, registry, dispatcher.call), provenance=provenance)
            print('METHOD COMPLETE', m, round(time.perf_counter() - t, 1), flush=True)
        write(D / 'execution_status.json', {'status': 'executed_pending_analysis'})
    except Paused as exc:
        write(D / 'execution_status.json', {'status': 'paused', 'reason': str(exc)}); raise
    finally:
        dispatcher.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ('supportability', 'audit', 'freeze', 'execute'):
        g.add_argument('--' + f, action='store_true')
    a = ap.parse_args()
    (supportability if a.supportability else audit if a.audit else freeze if a.freeze else execute)()
