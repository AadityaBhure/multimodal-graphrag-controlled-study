"""Run RQ3 policies through the common Phase 5 runner (durable, resumable, one record per query).

  primary : the 56 verified generated validation queries (frozen plan required)
  smoke   : N generated TRAIN queries into artifacts/phase9/smoke (plumbing check only, never analysed)

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

BENCH = ROOT / 'data/MMG_STARK_MAG/benchmark'


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
    qids = cohort(split)
    if not primary:
        qids = qids[:a.limit]
    if primary and len(qids) != 56:
        raise SystemExit('Primary cohort must be 56 verified generated validation queries, found %d' % len(qids))
    options = BaselineOptions()
    store = Stores(ROOT / 'data/MMG_STARK_MAG', ARTIFACTS / 'work/run', options, modalities=('text', 'graph', 'structured'))
    root = (PHASE9 / 'runs') if primary else (ARTIFACTS / 'smoke')
    tools = Tools(store, options, ARTIFACTS / 'tool_cache')
    llm = DurableLLM(ARTIFACTS / 'llm_stages')
    provenance = code_provenance()
    status = {}
    try:
        for method in a.methods:
            config_hash = content_hash({'method': method, 'plan': plan['plan_sha256'] if plan else 'smoke'})
            policy = build_policy(method, store, options, tools, llm, config_hash)
            cfg = RunnerConfig(config_id='phase9-%s-%s' % (a.mode, method), system_id=method, system_version=Policy.version, splits=(split,),
                               query_ids=tuple(qids), model_ids=('openai/gpt-oss-120b',), embedding_model=options.embedding, agentic_method=method,
                               fusion_method='source-separated-concat', context_method='fixed-8000-chars-per-source',
                               retrieval_parameters={'baseline_options': options.model_dump(), 'per_source_chars': 8000, 'final_cap': 1024,
                                                     'config_hash': config_hash})
            t = time.perf_counter()
            run(cfg, BENCH, root / method, policy, provenance=provenance)
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
