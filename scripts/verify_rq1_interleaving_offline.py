"""Offline proof for RQ1 operational revision 4 (no network, no Groq).

Uses the REAL frozen systems, inputs, encoder, reranker, seeds, overlays and the unchanged Phase 5 runner,
with a fake provider client. Stage A sends in query-major order; stage B runs the unchanged runner per method
with the dispatcher in replay_only mode. PASS means every payload the runner produced was byte-identical to a
payload sent in stage A (otherwise replay_only stops), with zero extra provider calls.
CM-03 uses deterministic API-free test keywords (its real keywords do not exist yet).
usage: verify_rq1_interleaving_offline.py [N_QUERIES]
"""
from pathlib import Path
from types import SimpleNamespace
import json, shutil, sys, tempfile, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.common.serialization import content_hash
from research.common.reproducibility import seed_everything
from research.evaluation.benchmark import BenchmarkReader, digest
from research.evaluation.contracts import SystemInput
from research.experiments.config import RunnerConfig
from research.experiments.runner import run, code_provenance
from research.baselines.stores import QueryEncoder
from research.baselines.config import BaselineOptions
from research.rq1.reranker import LocalReranker
from research.repair import dispatch
from research.repair.schedule import interleaved, prefetch
from research.repair.rq1_compliance_v1.system import RepairedContextSystem
from scripts.run_rq1_repair import inputs, D, FinalGenerator
from scripts.validate_timing_boundary_equivalence import test_keywords


class Clock:                                   # pacing without real waiting
    def __init__(self): self.t = time.time()
    def time(self): return self.t
    def sleep(self, n): self.t += n


def fake_dispatcher(root):
    d = object.__new__(dispatch.Dispatcher); d.root = Path(root); d.root.mkdir(parents=True, exist_ok=True)
    d.maximum = 10_000; d.key = 'offline-no-key'; d.ready = 0.
    d.initial = {'x-ratelimit-limit-tokens': '8000', 'x-ratelimit-remaining-tokens': '8000', 'x-ratelimit-remaining-requests': '999'}
    import tiktoken; d.encoder = tiktoken.get_encoding('o200k_harmony')
    sent = []
    def create(**payload):
        sent.append(payload)
        result = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer_ids":[],"explanation":"offline"}'), finish_reason='stop')],
                                 usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))
        return SimpleNamespace(parse=lambda: result, status_code=200, headers=d.initial)
    d.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=create))), close=lambda: None)
    return d, sent


def main(n):
    plan = json.loads((D / 'execution_plan.json').read_text(encoding='utf-8'))
    data = inputs(); qids = sorted(data)[:n]
    reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
    validation = {q.query_id: q for q in reader.records('validation') if q.query_id in data}
    encoder = QueryEncoder(ROOT / 'data/MMG_STARK_MAG', BaselineOptions())
    reranker = LocalReranker(ROOT / 'documentation/phase7/reranker_config.json', ROOT / 'artifacts/phase7/reranker')
    cache = {q: {'keywords': list(test_keywords(data[q]['question'])), 'usage': {}} for q in data}
    configs = [RunnerConfig.model_validate_json((D / c['path']).read_text(encoding='utf-8')) for c in plan['configs']]
    tmp = Path(tempfile.mkdtemp(prefix='rq1_interleave_'))
    clock = Clock(); real_time = dispatch.time; dispatch.time = clock
    try:
        d, sent = fake_dispatcher(tmp / 'dispatch')
        ahead = {c.system_id: RepairedContextSystem(c.system_id, data, encoder.encode, reranker, cache, FinalGenerator(d, c.system_id)) for c in configs}
        for s in ahead.values(): s.initialise()
        def one(q, m):
            seed = int(content_hash({'seed': 42, 'query_id': q})[:8], 16); seed_everything(seed)
            ahead[m].execute(SystemInput(query_id=q, question=validation[q].question, seed=seed, overlay=reader.overlay(validation[q])))
        order = interleaved(qids, [c.system_id for c in configs])
        prefetch(order, one, tmp / 'prefetch', log=lambda *a: None)
        stage_a = [(p['messages'][1]['content'].split('\n')[1], p['seed']) for p in sent]
        a_calls = len(sent)
        d.replay_only = True
        records = 0
        for c in configs:
            sub = c.model_copy(update={'query_ids': tuple(qids)})            # verification subset only
            system = RepairedContextSystem(c.system_id, data, encoder.encode, reranker, cache, FinalGenerator(d, c.system_id)); system.initialise()
            out = run(sub, ROOT / 'data/MMG_STARK_MAG/benchmark', tmp / 'runs' / c.system_id, system, provenance=code_provenance())
            records += len(list((out / 'records').glob('*.json')))
            errs = [json.loads(p.read_text(encoding='utf-8'))['errors'] for p in (out / 'records').glob('*.json')]
            assert all(not e for e in errs), (c.system_id, errs)
        ok = len(sent) == a_calls == len(order) and records == len(order)
        expected_order = [(validation[q].question, int(content_hash({'seed': 42, 'query_id': q})[:8], 16)) for q, _ in order]
        report = {'check': 'rq1 operational revision 4 offline interleave+replay', 'queries': qids, 'pairs': len(order),
                  'stage_a_provider_calls': a_calls, 'stage_b_extra_provider_calls': len(sent) - a_calls, 'runner_records': records,
                  'stage_a_query_major_order_verified': stage_a == expected_order, 'replay_only_payload_mismatches': 0,
                  'plan_sha256': digest(D / 'execution_plan.json'), 'pass': ok and stage_a == expected_order}
    finally:
        dispatch.time = real_time
        shutil.rmtree(tmp, ignore_errors=True)
    (D / 'interleaving_offline_check.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
