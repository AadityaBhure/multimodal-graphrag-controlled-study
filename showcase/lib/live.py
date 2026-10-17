"""Live runs for the 'full' profile: the frozen combined-system code (research/integration) with any retrieval policy and
fusion method, CM-B1 fixed, answered by the local model server.

Used only when SHOWCASE_PROFILE=full and the research package, the data and the model server are available. Live answers
are demonstrations, not evaluated results. Requests identical to recorded ones are answered from the recorded responses
(read-only); new responses are kept in artifacts/showcase/live_stages, so repeating a run is instant.
"""
from pathlib import Path
import json, threading, time, urllib.request
from showcase import config
from showcase.lib.metrics import answer_scores, gold_in_context, evidence_text
from showcase.lib.traces import ar_steps

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/MMG_STARK_MAG'
LIVE = ROOT / 'artifacts/showcase'
REUSE = (ROOT / 'artifacts/phase9/llm_stages_local', ROOT / 'documentation/rq4/llm_stages_local')
POLICIES = ('AR-B0', 'AR-B1', 'AR-01', 'AR-02', 'AR-03')
FUSIONS = ('CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03')
MODEL = 'gpt-oss:20b'


def readiness():
    """[(check, ok, detail)] — cheap checks, no model loading."""
    import importlib.util
    out = [('Research code', importlib.util.find_spec('research') is not None, 'research package importable')]
    out.append(('Data', (DATA / 'manifest.json').exists(), 'frozen corpus present'))
    try:
        with urllib.request.urlopen(config.OLLAMA_URL + '/api/tags', timeout=2) as r:
            names = {m.get('name') for m in json.loads(r.read().decode('utf-8')).get('models', [])}
        out.append(('Model server', MODEL in names, '%s %s at %s' % (MODEL, 'available' if MODEL in names else 'not installed', config.OLLAMA_URL)))
    except Exception as exc:          # unreachable server is a normal state for this check
        out.append(('Model server', False, 'not reachable at %s (%s)' % (config.OLLAMA_URL, type(exc).__name__)))
    return out


def gpu_temperature():
    try:
        from research.local_llm import gpu_temp
        return gpu_temp()
    except Exception:
        return None


class _Capture:
    """Transparent proxy around a policy that keeps the trace of its last run (for routing/classifier details)."""

    def __init__(self, policy):
        self._p, self.trace = policy, None

    def __getattr__(self, name):
        return getattr(self._p, name)

    def run(self, request, memory, trace):
        self.trace = trace
        return self._p.run(request, memory, trace)


class LiveEngine:
    def __init__(self):
        from research.baselines.stores import Stores
        from research.baselines.config import BaselineOptions
        from research.agentic.tools import Tools
        from research.integration.llm import ReusingSharedQuotaLLM
        from research.evaluation.benchmark import BenchmarkReader
        self.options = BaselineOptions()
        self.store = Stores(DATA, LIVE / 'work', self.options, modalities=('text', 'graph', 'structured'))
        self.tools = Tools(self.store, self.options, LIVE / 'tool_cache')
        self._clear_incomplete()
        self.llm = ReusingSharedQuotaLLM(LIVE / 'live_stages', reuse_roots=REUSE, external_ledgers=(), local=True)
        self.reader = BenchmarkReader(DATA / 'benchmark')
        self.questions = {q.query_id: q for q in self.reader.records('validation')}
        plan = json.loads((ROOT / 'documentation/phase9/execution_plan_local.json').read_text(encoding='utf-8'))
        self.plan_sha = plan['plan_sha256']
        self.seed = json.loads((ROOT / 'documentation/rq4/configs_local/INT-1.json').read_text(encoding='utf-8'))['seed']
        self.policies = {}
        self.lock = threading.Lock()

    def _clear_incomplete(self):
        """The live store is a demonstration cache: a failed or interrupted request is removed so it can be asked again."""
        stages = LIVE / 'live_stages' / 'stages'
        if stages.exists():
            for p in stages.glob('*.json'):
                try:
                    if json.loads(p.read_text(encoding='utf-8')).get('status') != 'complete':
                        p.unlink()
                except ValueError:
                    p.unlink()

    def policy(self, method):
        if method not in self.policies:
            from research.agentic.factory import build_policy
            from research.common.serialization import content_hash
            self.policies[method] = build_policy(method, self.store, self.options, self.tools, self.llm,
                                                 content_hash({'method': method, 'plan': self.plan_sha}))
        return self.policies[method]

    def run(self, ar, cf, question=None, query_id=None):
        """One live run. query_id: a benchmark question (scored, with its evaluation overlay); else free text (not scored)."""
        from research.common.serialization import content_hash
        from research.common.reproducibility import seed_everything
        from research.evaluation.contracts import SystemInput
        from research.integration.system import IntegratedSystem
        from research.integration.registry import lookup
        from research.agentic.analysis import ORACLE
        assert ar in POLICIES and cf in FUSIONS
        if query_id:
            q = self.questions[query_id]; question, overlay = q.question, self.reader.overlay(q)
            gold, oracle = [int(x) for x in q.gold_answer_ids], sorted(ORACLE[q.modality_class])
        else:
            question = (question or '').strip()[:config.MAX_QUESTION_CHARS]
            query_id, overlay, gold, oracle = 'live:' + content_hash({'question': question})[:16], None, None, None
        seed = int(content_hash({'seed': self.seed, 'query_id': query_id})[:8], 16)
        with self.lock:
            self._clear_incomplete()
            seed_everything(seed)
            policy = _Capture(self.policy(ar))
            t0 = time.perf_counter()
            out = IntegratedSystem(policy, cf, self.store, self.options, self.llm, lookup).execute(
                SystemInput(query_id=query_id, question=question, seed=seed, overlay=overlay))
            wall = (time.perf_counter() - t0) * 1000
        return self._normalize(out, ar, cf, getattr(policy.trace, 'extra', {}) or {}, gold, oracle, wall)

    def _normalize(self, out, ar, cf, extra, gold, oracle, wall):
        d = json.loads(out.diagnostics)
        steps, llm = ar_steps(ar, {**d['ar'], 'extra': extra})
        cfd = d.get('cf') or {}
        stages = [{'stage': s['stage'].split(':')[1] if s['stage'].count(':') >= 2 else s['stage'], 'input_tokens': s['usage'].get('input_tokens'),
                   'output_tokens': s['usage'].get('output_tokens'), 'ms': s['usage'].get('generation_ms'), 'reused': s.get('reused')}
                  for s in cfd.get('llm_stages', [])]
        o = out.observation
        tokens = (o.input_tokens + o.output_tokens) if o.input_tokens is not None and o.output_tokens is not None else None
        metrics = {'retrieval_calls': o.retrieval_calls, 'llm_calls': o.llm_calls, 'input_tokens': o.input_tokens, 'output_tokens': o.output_tokens,
                   'total_tokens': tokens, 'latency': wall, 'model_ms': d['timings_ms'].get('llm_intrinsic')}
        ids = [int(i) for i in (out.answer_ids or [])]
        if gold is not None:
            s = answer_scores(ids, gold)
            metrics.update(answer_f1=s['f1'], answer_em=s['exact_match'])
            called, need = set(d['sources_called']), set(oracle)
            inter = len(called & need)
            metrics['source_f1'] = 2 * inter / (len(called) + len(need)) if (called or need) else None
        names = {k: v['label'] for k, v in self.store.nodes(ids).items()} if ids else {}
        try:
            expl = json.loads(out.answer).get('explanation') if out.answer else None
        except (TypeError, ValueError, AttributeError):
            expl = (out.answer or '')[:800]
        reused = sum(1 for c in d['ar'].get('llm_calls', []) if c.get('reused')) + sum(1 for s in stages if s.get('reused'))
        return {'answer_ids': ids, 'titles': {str(k): v for k, v in names.items()}, 'explanation': expl, 'errors': list(out.errors or []),
                'sources_called': d['sources_called'], 'stop_reason': d['stop_reason'], 'status': d['status'], 'steps': steps, 'llm': llm,
                'cm': {'graph_in': len(d['cm']['graph_in']), 'graph_kept': len(d['cm']['graph_kept']), 'papers': d['cm']['papers']},
                'cf': {'method': cf, 'source_counts': cfd.get('source_counts'), 'stages': stages}, 'context': out.context, 'metrics': metrics,
                'gold_seen': gold_in_context(out.context, gold) if gold is not None else None,
                'gold_retrieved': gold_in_context(evidence_text(list(out.evidence or ())), gold) if gold is not None else None,
                'reused_calls': reused, 'live': True, 'oracle': oracle}
