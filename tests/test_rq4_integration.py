"""RQ4 INT-1: CM-B1 graph filter, AR -> CM -> CF composition, external stage reuse and shared quota (offline fakes)."""
import json
import pytest
from research.agentic.llm import DurableLLM, LLMResult, ProviderPause
from research.agentic.tools import ToolCall
from research.baselines.config import BaselineOptions
from research.evaluation.contracts import SystemInput
from research.integration.system import IntegratedSystem, cm_b1
from research.integration.llm import ReusingSharedQuotaLLM
from tests.test_rq2_canonical import item


class FakePolicy:
    system_id, fingerprint = 'AR-B1', 'fp'
    def __init__(self, items_by_source):
        self.items_by_source = items_by_source
    def run(self, request, memory, trace):
        for i, (source, items) in enumerate(self.items_by_source.items(), 1):
            new = memory.add(items)
            trace.tool(i, ToolCall(source, request.question, items, {'status': 'ok'}, 10., False), len(new))
        trace.stop_reason = 'router_exhausted'
        return {'kind': 'generate'}


class FakeLLM:
    def __init__(self, raw):
        self.raw, self.log = raw, []
    def chat(self, role, system, user, cap, seed, json_mode=True):
        self.log.append((role, cap, user))
        return LLMResult(raw=self.raw(role, user) if callable(self.raw) else self.raw, usage={'prompt_tokens': 50, 'completion_tokens': 5},
                         finish_reason='stop', latency_ms=7., wait_ms=0., reused=False, stage_id='s', role=role)


REG = lambda ids: {i: {'entity_type': 'paper', 'display_name': i} for i in ids}


def test_cm_b1_keeps_five_best_papers_in_original_order():
    g = [item('graph', i, s) for i, s in [(1, .1), (2, .9), (3, .8), (4, .7), (5, .6), (6, .5), (7, .95)]]
    kept, papers = cm_b1(g)
    assert papers == [7, 2, 3, 4, 5] and [e.evidence_id for e in kept] == ['graph:paper:%d' % i for i in (2, 3, 4, 5, 7)]


def test_int1_runs_ar_then_cm_b1_then_cf_with_one_final_call_and_no_ar_final():
    pol = FakePolicy({'text': [item('text', 1, .9)], 'graph': [item('graph', i, i / 10) for i in range(2, 9)]})
    llm = FakeLLM(json.dumps({'answer_ids': [1], 'explanation': 'x'}))
    s = IntegratedSystem(pol, 'CF-B1', None, BaselineOptions(), llm, REG)
    out = s.execute(SystemInput(query_id='q1', question='Which papers?', seed=7, overlay=None))
    d = json.loads(out.diagnostics)
    assert [r[0] for r in llm.log] == ['final'] and out.answer_ids == (1,)                 # AR's own final answer is never generated
    assert d['cm']['papers'] == [8, 7, 6, 5, 4] and len(d['cm']['graph_kept']) == 5 and len(d['cm']['graph_in']) == 7
    assert d['sources_called'] == ['text', 'graph'] and out.observation.retrieval_calls == 2
    assert out.observation.input_tokens == 50 and out.observation.llm_calls == 1


def test_int1_with_cf02_makes_selector_then_final_calls():
    pol = FakePolicy({'text': [item('text', 1, .9)], 'graph': [item('graph', 2, .5)], 'structured': [item('structured', 3, .5)]})
    llm = FakeLLM(lambda role, user: json.dumps({'selected_ids': ['graph:paper:2'], 'reason': 'r'}) if role == 'selector'
                  else json.dumps({'answer_ids': [2], 'explanation': 'x'}))
    out = IntegratedSystem(pol, 'CF-02', None, BaselineOptions(), llm, REG).execute(SystemInput(query_id='q1', question='Which papers?', seed=7, overlay=None))
    assert [r[0] for r in llm.log] == ['selector', 'final'] and out.answer_ids == (2,)


def _transport(calls):
    def t(payload):
        calls.append(payload)
        return '{"answer_ids":[]}', {'prompt_tokens': 100, 'completion_tokens': 10, 'total_tokens': 110}, 'stop', \
            {'x-ratelimit-limit-tokens': '8000', 'x-ratelimit-remaining-tokens': '8000', 'x-ratelimit-remaining-requests': '999'}
    return t


def test_reuses_identical_completed_stage_from_earlier_study_read_only(tmp_path):
    calls = []
    rq3 = DurableLLM(tmp_path / 'rq3', transport=_transport(calls), clock=lambda: 5., sleep=lambda s: None)
    first = rq3.chat('agent', 'S', 'U', 256, 1)
    before = sorted(p.name for p in (tmp_path / 'rq3' / 'stages').iterdir())
    rq4 = ReusingSharedQuotaLLM(tmp_path / 'rq4', reuse_roots=[tmp_path / 'rq3'], transport=_transport(calls), clock=lambda: 6., sleep=lambda s: None)
    again = rq4.chat('agent', 'S', 'U', 256, 1)
    assert again.reused and again.raw == first.raw and again.latency_ms == first.latency_ms and len(calls) == 1
    assert sorted(p.name for p in (tmp_path / 'rq3' / 'stages').iterdir()) == before          # nothing written to the earlier study
    rq4.chat('final', 'S', 'NEW', 1024, 1)
    assert len(calls) == 2 and rq4.reused_external == 1


def test_shared_quota_counts_other_ledgers(tmp_path):
    other = tmp_path / 'other.json'; other.write_text(json.dumps({'ledger': [[100., 189_500]]}))
    rq4 = ReusingSharedQuotaLLM(tmp_path / 'rq4', external_ledgers=[other], transport=_transport([]), clock=lambda: 200., sleep=lambda s: None)
    with pytest.raises(ProviderPause, match='Daily token budget'):
        rq4.chat('final', 'S', 'U', 1024, 1)
    assert rq4.daily_budget == 190_000
