"""Execute context-only RQ2 through the unchanged Phase 5 experiment runner."""
import argparse
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_phase8 import D, load_inputs, immutable_write
from scripts.audit_stark_mag import process_memory
from research.rq2.contracts import METHODS, Options
from research.rq2.system import FusionSystem
from research.experiments.config import RunnerConfig
from research.experiments.runner import run, write

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--approved-generation-plan', type=Path)
    args = parser.parse_args()
    inputs = load_inputs()
    journal = None
    generators = []
    mode = 'context_only'
    if args.approved_generation_plan:
        from research.baselines.config import BaselineOptions
        from research.baselines.generation import GroqGenerator
        from research.rq2.generation import Journal
        plan = json.loads(args.approved_generation_plan.read_text(encoding='utf-8'))
        if plan['bundle_manifest_sha256'] != __import__('research.evaluation.benchmark', fromlist=['digest']).digest(D / 'bundle_manifest.json'):
            raise ValueError('Generation plan input mismatch')
        inputs = {q: inputs[q] for q in plan['query_ids']}
        if len(inputs) != 2: raise ValueError('Only the prepared two-query generation sample is allowed')
        generators = [GroqGenerator(BaselineOptions()), GroqGenerator(BaselineOptions(max_completion_tokens=220))]
        journal = Journal(D / 'generation_journal', *generators)
        mode = 'generation'
    resource_path = D / (mode + '_resources.json')
    resources = json.loads(resource_path.read_text(encoding='utf-8')) if resource_path.exists() else {}
    try:
        for method in METHODS:
            options = Options(method=method)
            config = RunnerConfig(config_id=method + '-rq2-' + mode + '-v1', system_id=method, system_version='1',
                query_ids=tuple(sorted(inputs)), fusion_method=method,
                model_ids=('openai/gpt-oss-120b',) if journal else (),
                embedding_model='sentence-transformers/all-MiniLM-L6-v2',
                retrieval_parameters={'upstream': 'approved_phase6_B4_cached_once', 'fusion_options': options.model_dump(mode='json'),
                    'generation': mode, 'final_max_completion_tokens': 1024, 'intermediate_max_completion_tokens': 220,
                    'temperature': 0, 'reasoning_effort': 'low'})
            immutable_write(ROOT / 'configs/rq2' / (method + '-' + mode + '.json'), config.model_dump(mode='json'))
            started = time.perf_counter()
            run(config, ROOT / 'data/MMG_STARK_MAG/benchmark', D / mode / method, FusionSystem(options, inputs, journal))
            status = json.loads((D / mode / method / 'status.json').read_text(encoding='utf-8'))
            resources.setdefault(method, {'seconds': time.perf_counter() - started, 'memory': process_memory(), 'status': status})
            write(resource_path, resources)
            print(method, status, flush=True)
    finally:
        for generator in generators: generator.close()

if __name__ == '__main__': main()
