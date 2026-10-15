"""Run RQ3 policies through the common Phase 5 runner (durable, resumable, one record per query).

  primary : the 28-query cohort frozen in documentation/SCOPE_REVISION_2026-10-15.json (14 families x normal +
            noisy, a subset of the 56 verified generated validation queries; frozen plan required)
  smoke   : N generated TRAIN queries into artifacts/phase9/smoke (plumbing check only, never analysed)

Provider order (operational): provider calls are made first in query-major order (all policies for query 1, then
query 2, ...) so that day-to-day provider drift is not confounded with policy; the unchanged Phase 5 runner then
replays the stored responses per policy with the LLM client in replay_only mode (any payload difference stops).
Provider pauses (quota/429) stop the run cleanly; rerun the same command to resume.
"""
from pathlib import Path
import argparse, json, sys, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.common.serialization import content_hash, canonical_json
from research.evaluation.benchmark import BenchmarkReader, digest
from research.experiments.config import RunnerConfig
from research.experiments.runner import run, code_provenance, labels
from research.baselines.stores import Stores
from research.baselines.config import BaselineOptions
from research.agentic.tools import Tools
from research.agentic.llm import DurableLLM, ProviderPause
from research.agentic.factory import build_policy, METHODS, PHASE9, ARTIFACTS
from research.agentic.policies import Policy
from research.common.reproducibility import seed_everything
from research.evaluation.contracts import SystemInput
from research.repair.schedule import interleaved, prefetch

BENCH = ROOT / 'data/MMG_STARK_MAG/benchmark'
SCOPE = ROOT / 'documentation/SCOPE_REVISION_2026-10-15.json'


def primary_cohort():
    """The frozen two-week RQ3 cohort; must be a subset of the verified generated validation queries."""
    qids = sorted(json.loads(SCOPE.read_text(encoding='utf-8'))['rq3_cohort']['query_ids'])
    if len(qids) != 28 or not set(qids) <= set(cohort('validation')):
        raise SystemExit('Frozen RQ3 cohort must be 28 verified generated validation queries')
    return qids


def cohort(split):
    reader = BenchmarkReader(BENCH)
    qs = [q for q in reader.records(split) if q.provenance['source'] == 'generated' and labels(q).status == 'programmatically_verified']
    return sorted(q.query_id for q in qs)


def check_plan():
    plan = json.loads((PHASE9 / 'execution_plan.json').read_text(encoding='utf-8'))
    for rel, sha in plan['implementation_sha256'].items():
        if digest(ROOT / rel) != sha:
            raise SystemExit('Frozen Phase 9 code changed: ' + rel)
    for rel, sha in plan['artifact_sha256'].items():
        if digest(ROOT / rel) != sha:
            raise SystemExit('Frozen Phase 9 artifact changed: ' + rel)
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=('primary', 'smoke'), required=True)
    ap.add_argument('--methods', nargs='+', choices=METHODS, default=list(METHODS))
    ap.add_argument('--limit', type=int, default=2)
    a = ap.parse_args()
    primary = a.mode == 'primary'
    plan = check_plan() if primary else None
    split = 'validation' if primary else 'train'
    qids = primary_cohort() if primary else cohort(split)[:a.limit]
    if primary and plan['primary_cohort'] != qids:
        raise SystemExit('Frozen plan cohort differs from the scope revision cohort')
    options = BaselineOptions()
    store = Stores(ROOT / 'data/MMG_STARK_MAG', ARTIFACTS / 'work/run', options, modalities=('text', 'graph', 'structured'))
    root = (PHASE9 / 'runs') if primary else (ARTIFACTS / 'smoke')
    tools = Tools(store, options, ARTIFACTS / 'tool_cache')
    llm = DurableLLM(ARTIFACTS / 'llm_stages')
    provenance = code_provenance()
    status = {}
    try:
        policies, configs = {}, {}
        for method in a.methods:
            config_hash = content_hash({'method': method, 'plan': plan['plan_sha256'] if plan else 'smoke'})
            policies[method] = build_policy(method, store, options, tools, llm, config_hash)
            configs[method] = RunnerConfig(config_id='phase9-%s-%s' % (a.mode, method), system_id=method, system_version=Policy.version, splits=(split,),
                               query_ids=tuple(qids), model_ids=('openai/gpt-oss-120b',), embedding_model=options.embedding, agentic_method=method,
                               fusion_method='source-separated-concat', context_method='fixed-8000-chars-per-source',
                               retrieval_parameters={'baseline_options': options.model_dump(), 'per_source_chars': 8000, 'final_cap': 1024,
                                                     'config_hash': config_hash})
        # Stage A: provider calls in query-major order through the same policies, with the runner's own seed and overlay.
        reader = BenchmarkReader(BENCH); queries = {q.query_id: q for q in reader.records(split) if q.query_id in set(qids)}
        def prefetch_one(qid, method):
            q = queries[qid]; seed = int(content_hash({'seed': configs[method].seed, 'query_id': qid})[:8], 16); seed_everything(seed)
            policies[method].execute(SystemInput(query_id=qid, question=q.question, seed=seed, overlay=reader.overlay(q)))
        prefetch(interleaved(qids, list(a.methods)), prefetch_one, root / 'prefetch', log=lambda *x: print(*x, flush=True))
        # Stage B: the unchanged runner per policy replays the stored responses; any payload difference stops the run.
        llm.replay_only = True
        for method in a.methods:
            t = time.perf_counter()
            run(configs[method], BENCH, root / method, policies[method], provenance=provenance)
            status[method] = {'complete': True, 'seconds': time.perf_counter() - t}
            print('METHOD COMPLETE', method, round(time.perf_counter() - t, 1), flush=True)
    except ProviderPause as exc:
        status['paused'] = str(exc)[:300]
        print('PAUSED', exc, flush=True)
        (root).mkdir(parents=True, exist_ok=True)
        (root / 'status.json').write_text(canonical_json({'mode': a.mode, **status}) + '\n', encoding='utf-8', newline='\n')
        sys.exit(75)
    finally:
        store.close()
    root.mkdir(parents=True, exist_ok=True)
    (root / 'status.json').write_text(canonical_json({'mode': a.mode, **status}) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
