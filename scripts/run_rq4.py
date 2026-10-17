"""RQ4 INT-1 per documentation/rq4/RQ4_DESIGN.md.

  --select   apply the frozen rules R-AR / R-CF to the RQ3 and RQ2 analyses -> documentation/rq4/selection.json
  --freeze   config + execution plan (refuses to overwrite)
  --execute  run INT-1 on the 28-query cohort through the unchanged Phase 5 runner; AR-stage requests identical to the
             RQ3 run are answered from RQ3's stored responses (read-only); pauses at the shared daily budget; rerun to resume.
"""
from pathlib import Path
import argparse, json, sys, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.common.serialization import content_hash
from research.evaluation.benchmark import digest
from research.experiments.config import RunnerConfig
from research.experiments.runner import run, code_provenance
from research.baselines.stores import Stores
from research.baselines.config import BaselineOptions
from research.agentic.tools import Tools
from research.agentic.llm import ProviderPause
from research.agentic.factory import build_policy, PHASE9, ARTIFACTS
from research.integration.system import IntegratedSystem
from research.integration.llm import ReusingSharedQuotaLLM
from research.integration.registry import lookup
from scripts.prepare_rq1_repair import save
from scripts.run_phase9 import primary_cohort
from research.common.reproducibility import seed_everything
from research.evaluation.benchmark import BenchmarkReader
from research.evaluation.contracts import SystemInput
from research.repair.schedule import prefetch

D = ROOT / 'documentation/rq4'
LOCAL = '--local' in sys.argv; S = '_local' if LOCAL else ''      # local backend: '_local' inputs/outputs
BENCH = ROOT / 'data/MMG_STARK_MAG/benchmark'
AR_ORDER = ('AR-B1', 'AR-01', 'AR-02', 'AR-03', 'AR-B0')
CF_ORDER = ('CF-B1', 'CF-01', 'CF-02', 'CF-03', 'CF-B0')
EXTERNAL = (ARTIFACTS / 'llm_stages/state.json', ROOT / 'documentation/rq2_repair/dispatch/state.json', ROOT / 'documentation/rq1_repair/dispatch/state.json')


def rule(analysis, order, tokens_key):
    """Highest mean answer F1 within the Pareto set; ties -> fewer mean tokens -> fixed order."""
    desc, front = analysis['descriptive'], analysis['pareto']
    key = lambda m: (-(desc[m]['answer_f1'] or 0.), desc[m].get(tokens_key) or float('inf'), order.index(m))
    return sorted(front, key=key)[0]


def select():
    rq3 = json.loads((ROOT / ('documentation/phase9/analysis' + S + '.json')).read_text(encoding='utf-8'))
    rq2 = json.loads((ROOT / ('documentation/rq2_repair/analysis' + S + '.json')).read_text(encoding='utf-8'))
    out = {'R-AR': rule(rq3, AR_ORDER, 'total_tokens'), 'R-CF': rule(rq2, CF_ORDER, 'total_tokens'), 'CM': 'CM-B1',
           'rq3_analysis_sha256': digest(ROOT / ('documentation/phase9/analysis' + S + '.json')), 'rq2_analysis_sha256': digest(ROOT / ('documentation/rq2_repair/analysis' + S + '.json')),
           'rules': 'documentation/rq4/RQ4_DESIGN.md (R-AR, R-CF), applied mechanically'}
    save(D / ('selection' + S + '.json'), out)
    print('SELECTED', out['R-AR'], 'CM-B1', out['R-CF'])


def config(sel, qids):
    from research.local_llm import LOCAL_MODEL
    return RunnerConfig(config_id='rq4-int1-local-v1' if LOCAL else 'rq4-int1-v1', system_id='INT-1', system_version=IntegratedSystem.version, splits=('validation',), query_ids=tuple(qids),
                        model_ids=(LOCAL_MODEL if LOCAL else 'openai/gpt-oss-120b',), embedding_model=BaselineOptions().embedding, agentic_method=sel['R-AR'], fusion_method=sel['R-CF'],
                        context_method='CM-B1', retrieval_parameters={'selection_sha256': digest(D / ('selection' + S + '.json')), 'design_sha256': digest(D / 'RQ4_DESIGN.md'),
                                                                      'rq3_plan_sha256': digest(PHASE9 / ('execution_plan' + S + '.json')),
                                                                      'rq2_plan_sha256': digest(ROOT / ('documentation/rq2_repair/execution_plan' + S + '.json'))})


def freeze():
    sel = json.loads((D / ('selection' + S + '.json')).read_text(encoding='utf-8')); qids = primary_cohort()
    p = D / ('configs' + S) / 'INT-1.json'; save(p, config(sel, qids).model_dump(mode='json'))
    impl = {q.relative_to(ROOT).as_posix(): digest(q) for q in sorted((ROOT / 'research/integration').glob('*.py'))}
    impl['scripts/run_rq4.py'] = digest(ROOT / 'scripts/run_rq4.py'); impl['research/local_llm.py'] = digest(ROOT / 'research/local_llm.py')
    save(D / ('execution_plan' + S + '.json'), {'version': 'rq4-int1-local-v1' if LOCAL else 'rq4-int1-v1', 'selection': sel,
                                     'config': {'path': ('configs' + S) + '/INT-1.json', 'sha256': digest(p)},
                                     'implementation_sha256': impl, 'queries': qids, 'reuse_roots': [str((ARTIFACTS / ('llm_stages' + S)).relative_to(ROOT))],
                                     'external_ledgers': [str(e.relative_to(ROOT)) for e in EXTERNAL], 'test_human_test': False})
    print('FROZEN rq4-int1-v1:', sel['R-AR'], '-> CM-B1 ->', sel['R-CF'], '|', len(qids), 'queries')


def execute():
    plan = json.loads((D / ('execution_plan' + S + '.json')).read_text(encoding='utf-8'))
    for f, h in plan['implementation_sha256'].items():
        if digest(ROOT / f) != h:
            raise SystemExit('Frozen RQ4 code changed: ' + f)
    if digest(D / plan['config']['path']) != plan['config']['sha256']:
        raise SystemExit('Frozen RQ4 config changed')
    sel = plan['selection']; cfg = RunnerConfig.model_validate_json((D / plan['config']['path']).read_text(encoding='utf-8'))
    options = BaselineOptions()
    store = Stores(ROOT / 'data/MMG_STARK_MAG', ARTIFACTS / 'work/rq4', options, modalities=('text', 'graph', 'structured'))
    tools = Tools(store, options, ARTIFACTS / 'tool_cache')
    llm = ReusingSharedQuotaLLM(D / ('llm_stages' + S), reuse_roots=[ARTIFACTS / ('llm_stages' + S)], external_ledgers=() if LOCAL else EXTERNAL, local=LOCAL)
    rq3_plan = json.loads((PHASE9 / ('execution_plan' + S + '.json')).read_text(encoding='utf-8'))
    policy = build_policy(sel['R-AR'], store, options, tools, llm, content_hash({'method': sel['R-AR'], 'plan': rq3_plan['plan_sha256']}))
    system = IntegratedSystem(policy, sel['R-CF'], store, options, llm, lookup)
    provenance = code_provenance(); provpath = D / ('execution_code' + S + '.json')          # captured once; resumes reject code changes
    if provpath.exists():
        old = json.loads(provpath.read_text(encoding='utf-8'))
        if old['source_tree_hash'] != provenance['source_tree_hash']:
            raise SystemExit('Research source changed during experiment')
        provenance = old
    else:
        save(provpath, provenance)
    reader = BenchmarkReader(BENCH); qs = {q.query_id: q for q in reader.records('validation') if q.query_id in set(plan['queries'])}
    def one(qid, _m):
        seed = int(content_hash({'seed': cfg.seed, 'query_id': qid})[:8], 16); seed_everything(seed)
        system.execute(SystemInput(query_id=qid, question=qs[qid].question, seed=seed, overlay=reader.overlay(qs[qid])))
    try:
        t = time.perf_counter()
        # Stage A: provider calls (AR stages answered from RQ3's stored responses); stage B: replay-only runner, so latency is
        # measured exactly as in RQ2/RQ3 (recorded provider + retrieval latency + local compute).
        prefetch([(q, 'INT-1') for q in plan['queries']], one, D / ('prefetch' + S), log=lambda *x: print(*x, flush=True))
        llm.replay_only = True
        run(cfg, BENCH, D / ('runs' + S) / 'INT-1', system, provenance=provenance)
        print('METHOD COMPLETE INT-1', round(time.perf_counter() - t, 1), '| AR stages reused from RQ3:', llm.reused_external, flush=True)
    except ProviderPause as exc:
        print('PAUSED', exc, flush=True); sys.exit(75)
    finally:
        store.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--local', action='store_true'); g = ap.add_mutually_exclusive_group(required=True)
    for f in ('select', 'freeze', 'execute'):
        g.add_argument('--' + f, action='store_true')
    a = ap.parse_args()
    (select if a.select else freeze if a.freeze else execute)()
