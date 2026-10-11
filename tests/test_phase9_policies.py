"""AR-B0 / AR-B1 / AR-01 / AR-02 / AR-03 behaviour against Phase 1D acceptance tests (offline fakes)."""
import json
import pytest
from phase9_fakes import *  # noqa
from research.agentic.policies import AlwaysAll, RuleRouted
from research.agentic.adaptive_rag import AdaptiveRAG
from research.agentic.crag import CorrectiveRAG, Platt, classify, fit_thresholds, macro_f1
from research.agentic.agent_g import AgentG


def build(cls, tmp_path, script, tools=None, **kw):
    llm, tr = make_llm(tmp_path, script)
    tools = tools or FakeTools()
    return cls(kw.pop('system_id', 'X'), FakeStore(), options(), tools, llm, **kw), tools, tr


def diag(out):
    return json.loads(out.diagnostics)


FINAL = {'final': [answer([1])]}


# ------------------------------------------------------------------ AR-B0 / AR-B1
def test_ar_b0_always_all_in_fixed_order(tmp_path):
    p, tools, tr = build(AlwaysAll, tmp_path, FINAL)
    out = p.execute(request('anything'))
    assert [c['source'] for c in tools.calls] == ['text', 'graph', 'structured'] and tr.log == ['final']
    d = diag(out)
    assert d['sources_called'] == ['text', 'graph', 'structured'] and d['retrieval_steps'] == 3 and out.observation.llm_calls == 1
    assert out.answer_ids == (1,) and '[TEXT]' in out.context and out.context.index('[GRAPH]') < out.context.index('[STRUCTURED]')


def test_ar_b1_routes_by_rules_only_and_stops(tmp_path):
    p, tools, tr = build(RuleRouted, tmp_path, FINAL)
    out = p.execute(request('Papers by authors affiliated with MIT published after 2015'))
    assert [c['source'] for c in tools.calls] == ['graph', 'structured'] and tr.log == ['final']
    assert diag(out)['extra']['route']['rule_hits']['graph'] and diag(out)['stop_reason'] == 'routed_sources_retrieved'
    p2, tools2, _ = build(RuleRouted, tmp_path / 'b', FINAL)
    p2.execute(request('hello'))
    assert [c['source'] for c in tools2.calls] == ['text']


# ------------------------------------------------------------------ AR-01
class FakeClassifier:
    fingerprint = 'fake'
    def __init__(self, label, valid=True):
        self.label, self.valid = label, valid
    def predict(self, q):
        return {'label': self.label if self.valid else None, 'raw': self.label, 'valid': self.valid, 'probs': {'A': .1, 'B': .1, 'C': .8}}


def ar01(tmp_path, label, script, valid=True):
    return build(AdaptiveRAG, tmp_path, script, classifier=FakeClassifier(label, valid))


def test_ar01_a_makes_zero_retrieval_calls(tmp_path):
    p, tools, tr = ar01(tmp_path, 'A', {'final': [answer([])]})
    out = p.execute(request())
    assert tools.calls == [] and out.context == '' and diag(out)['stop_reason'] == 'route_A_no_retrieval' and tr.log == ['final']


def test_ar01_b_exactly_one_retrieval_router_first_source(tmp_path):
    p, tools, _ = ar01(tmp_path, 'B', FINAL)
    p.execute(request('Papers by authors from MIT'))
    assert [c['source'] for c in tools.calls] == ['graph']


def test_ar01_invalid_classifier_falls_back_to_b(tmp_path):
    p, tools, _ = ar01(tmp_path, 'Z', FINAL, valid=False)
    out = p.execute(request('hello'))
    assert len(tools.calls) == 1 and diag(out)['fallbacks'][0]['fallback'] == 'single_step' and diag(out)['extra']['route'] == 'B'


def test_ar01_c_at_most_three_retrievals_distinct_sources(tmp_path):
    more = json.dumps({'sufficient': False, 'next_subquery': 'authors of those papers', 'reason': 'r'})
    p, tools, tr = ar01(tmp_path, 'C', {'final': [answer([1])], 'ar01_controller': [more]})
    out = p.execute(request('Which papers mention graphs?'))
    assert [c['source'] for c in tools.calls] == ['text', 'graph', 'structured'] and tr.log.count('ar01_controller') == 2
    assert diag(out)['stop_reason'] == 'max_multi_steps' and tools.calls[1]['query'] == 'authors of those papers'


def test_ar01_c_sufficient_stops_early(tmp_path):
    done = json.dumps({'sufficient': True, 'next_subquery': '', 'reason': 'enough'})
    p, tools, tr = ar01(tmp_path, 'C', {'final': [answer([1])], 'ar01_controller': [done]})
    out = p.execute(request())
    assert len(tools.calls) == 1 and diag(out)['stop_reason'] == 'sufficient'


def test_ar01_subquery_failure_stops_retrieval_and_generates_from_accumulated_evidence(tmp_path):
    p, tools, tr = ar01(tmp_path, 'C', {'final': [answer([1])], 'ar01_controller': ['garbage'], 'repair': ['still garbage']})
    out = p.execute(request())
    d = diag(out)
    assert len(tools.calls) == 1 and d['stop_reason'] == 'subquery_generation_failed' and d['fallbacks'][0]['type'] == 'subquery_generation_failed'
    assert tr.log == ['ar01_controller', 'repair', 'final'] and d['sources_called'] == ['text'] and out.answer_ids == (1,)


# ------------------------------------------------------------------ AR-02
class FakeEvaluator:
    fingerprint = 'fake'
    def __init__(self, rounds, fail=False):
        self.rounds, self.fail, self.n = rounds, fail, 0
    def raw_scores(self, q, texts):
        if self.fail:
            raise RuntimeError('boom')
        v = self.rounds[min(self.n, len(self.rounds) - 1)]; self.n += 1
        return [v] * len(texts)


def crag(tmp_path, rounds, fail=False, tools=None, script=FINAL):
    return build(CorrectiveRAG, tmp_path, script, tools=tools, evaluator=FakeEvaluator(rounds, fail), platt=Platt(1.0, 0.0), lower=0.3, upper=0.7)


def test_ar02_good_never_triggers_another_retrieval(tmp_path):
    p, tools, _ = crag(tmp_path, [5.0])
    out = p.execute(request())
    assert len(tools.calls) == 1 and diag(out)['stop_reason'] == 'good'


def test_ar02_ambiguous_queries_one_next_source_then_reevaluates(tmp_path):
    p, tools, _ = crag(tmp_path, [0.0, 5.0])        # p=.5 -> AMBIGUOUS, then GOOD
    out = p.execute(request('Which papers mention graphs?'))
    assert [c['source'] for c in tools.calls] == ['text', 'graph'] and diag(out)['stop_reason'] == 'good'
    states = [e['state'] for e in diag(out)['events'] if e['kind'] == 'evaluation']
    assert states == ['AMBIGUOUS', 'GOOD']


def test_ar02_bad_queries_all_remaining_sources_in_fixed_order(tmp_path):
    p, tools, _ = crag(tmp_path, [-9.0, 5.0])
    out = p.execute(request('Papers by authors from MIT'))      # router first source = graph
    assert [c['source'] for c in tools.calls] == ['graph', 'text', 'structured']
    assert diag(out)['stop_reason'] == 'good'


def test_ar02_max_two_correction_rounds_and_insufficient_status(tmp_path):
    p, tools, _ = crag(tmp_path, [-9.0], tools=FakeTools(empty=('text', 'graph', 'structured')))
    out = p.execute(request())
    d = diag(out)
    assert len([e for e in d['events'] if e['kind'] == 'evaluation']) <= 3 and len(tools.calls) == 3
    assert d['status'] == 'insufficient_evidence' and d['stop_reason'] in ('sources_exhausted', 'max_correction_rounds')


def test_ar02_two_ambiguous_rounds_exhaust_and_stop(tmp_path):
    p, tools, _ = crag(tmp_path, [0.0])              # always AMBIGUOUS
    out = p.execute(request('Which papers mention graphs?'))
    assert len(tools.calls) == 3 and diag(out)['stop_reason'] == 'max_correction_rounds'


def test_ar02_evaluator_failure_is_ambiguous_and_corrects_conservatively(tmp_path):
    p, tools, _ = crag(tmp_path, [0.0], fail=True)
    out = p.execute(request())
    ev = [e for e in diag(out)['events'] if e['kind'] == 'evaluation']
    assert all(e['evaluator_failed'] and e['state'] == 'AMBIGUOUS' for e in ev) and len(tools.calls) == 3


def test_ar02_thresholds_grid_constraint_and_tiebreaks():
    samples = [('GOOD', [.9]), ('BAD', [.1]), ('AMBIGUOUS', [.5]), ('GOOD', [.8]), ('BAD', [.15])]
    best, rows = fit_thresholds(samples)
    assert all(r['lower'] < r['upper'] for r in rows) and len(rows) == 25
    assert best['macro_f1'] == pytest.approx(1.0) and best['errors'] == 0
    top = [r for r in rows if r['macro_f1'] == best['macro_f1'] and r['errors'] == 0]
    assert best['margin'] == max(r['margin'] for r in top)            # wider margin wins the tie
    assert classify([], .3, .7) == 'BAD' and classify([.7], .3, .7) == 'GOOD' and classify([.3, .2], .3, .7) == 'BAD' and classify([.3, .4], .3, .7) == 'AMBIGUOUS'
    assert macro_f1(['GOOD'], ['GOOD']) == pytest.approx(1 / 3)


def test_platt_fit_is_deterministic_and_monotone():
    raw = [-5, -4, -3, 2, 3, 4]; lab = [0, 0, 0, 1, 1, 1]
    a, b = Platt.fit(raw, lab), Platt.fit(raw, lab)
    assert (a.coef, a.intercept) == (b.coef, b.intercept) and a.coef > 0 and a.prob(4) > a.prob(-4)


# ------------------------------------------------------------------ AR-03
def ar03(tmp_path, script, tools=None):
    return build(AgentG, tmp_path, script, tools=tools)


def test_ar03_accept_first_iteration_one_tool_and_cited_ids_exist(tmp_path):
    p, tools, tr = ar03(tmp_path, {'agent': [agent('text')], 'final': [answer([1])], 'validator': [verdict(True)]})
    out = p.execute(request())
    d = diag(out)
    assert len(tools.calls) == 1 and d['stop_reason'] == 'validator_accepted' and d['extra']['accepted_iteration'] == 1
    assert out.answer_ids == (1,) and tr.log == ['agent', 'final', 'validator'] and 1 in {int(e.canonical_id[6:]) for e in out.evidence}


def test_ar03_reject_comment_then_accept_with_cumulative_memory(tmp_path):
    script = {'agent': [agent('text'), agent('graph', iteration=2, reason_code='relational')], 'final': [answer([1]), answer([1, 3])],
              'validator': [verdict(False, 'insufficient_evidence'), verdict(True)], 'commentor': [note('graph')]}
    p, tools, tr = ar03(tmp_path, script)
    out = p.execute(request())
    assert [c['source'] for c in tools.calls] == ['text', 'graph'] and tr.log.count('commentor') == 1
    assert out.answer_ids == (1, 3) and diag(out)['sources_called'] == ['text', 'graph']


def test_ar03_exactly_one_tool_per_iteration_and_max_four(tmp_path):
    script = {'agent': [agent('text', 'a'), agent('graph', 'b'), agent('structured', 'c', structured_intent='the recorded publication year is 2000'), agent('text', 'd')], 'final': [answer([1])],
              'validator': [verdict(False, 'wrong_entity')], 'commentor': [note()]}
    p, tools, tr = ar03(tmp_path, script)
    out = p.execute(request())
    d = diag(out)
    assert len(tools.calls) == 4 and d['stop_reason'] == 'max_iterations_rejected' and d['status'] == 'insufficient_evidence'
    assert out.answer_ids == () and out.answer == 'INSUFFICIENT_EVIDENCE' and tr.log.count('commentor') == 3      # none after the terminal iteration
    assert [t['step'] for t in d['tool_calls']] == [1, 2, 3, 4]


def test_ar03_loop_guard_forced_feedback_then_terminate(tmp_path):
    same = agent('structured', 'x', structured_intent='the recorded publication year is 2000')
    tools = FakeTools(empty=('structured',))
    script = {'agent': [same], 'final': [answer([])], 'validator': [verdict(False, 'insufficient_evidence')], 'commentor': [note()]}
    p, tools, tr = ar03(tmp_path, script, tools)
    out = p.execute(request())
    d = diag(out)
    assert d['stop_reason'] == 'loop_guard_insufficient_evidence' and len(tools.calls) == 3
    assert any(e['kind'] == 'forced_feedback' for e in d['events']) and out.answer_ids == ()


def test_ar03_malformed_agent_json_repaired_once(tmp_path):
    script = {'agent': ['oops'], 'repair': [agent('graph', iteration=1)], 'final': [answer([3])], 'validator': [verdict(True)]}
    p, tools, tr = ar03(tmp_path, script)
    out = p.execute(request())
    assert tr.log[:2] == ['agent', 'repair'] and [c['source'] for c in tools.calls] == ['graph'] and not diag(out)['fallbacks']


def test_ar03_repair_failure_counts_iteration_and_router_supplies_source(tmp_path):
    script = {'agent': ['oops'], 'repair': ['still oops'], 'final': [answer([3])], 'validator': [verdict(True)]}
    p, tools, tr = ar03(tmp_path, script)
    out = p.execute(request('Papers by authors from MIT'))
    d = diag(out)
    assert [c['source'] for c in tools.calls] == ['graph'] and d['fallbacks'][0]['type'] == 'agent_schema_repair_failed'
    assert any(e.get('schema_repair_failed') for e in d['events']) and len(tools.calls) == 1


def test_ar03_stop_action_generates_without_validator(tmp_path):
    script = {'agent': [agent('text'), agent('stop', stop_reason='enough')], 'final': [answer([1])], 'validator': [verdict(False, 'insufficient_evidence')], 'commentor': [note()]}
    p, tools, tr = ar03(tmp_path, script)
    out = p.execute(request())
    assert len(tools.calls) == 1 and diag(out)['stop_reason'] == 'agent_stop:enough' and tr.log.count('validator') == 1


def test_ar03_structured_tool_is_read_only_and_validator_has_no_gold(tmp_path):
    import inspect
    import research.agentic.agent_g as mod, research.agentic.prompts as prompts
    code = inspect.getsource(mod) + prompts.VALIDATOR_SYSTEM
    assert 'gold' not in inspect.getsource(mod).lower().replace('gold answers', '') or 'do not have access' in prompts.VALIDATOR_SYSTEM
    assert 'SELECT' not in prompts.AGENT_SYSTEM and 'read-only' in prompts.AGENT_SYSTEM


# ------------------------------------------------------------------ shared downstream stack
def test_downstream_stack_identical_across_policies_for_identical_evidence(tmp_path):
    outs = []
    for i, cls in enumerate((AlwaysAll, RuleRouted)):
        p, tools, tr = build(cls, tmp_path / str(i), FINAL)
        outs.append((p.execute(request('Which papers mention graphs by authors affiliated with MIT published after 2015')), p))
    a, b = outs[0][0], outs[1][0]
    assert a.context == b.context                      # same retrievers, same fixed context, same sections
    assert [json.loads(e.payload) for e in a.evidence] == [json.loads(e.payload) for e in b.evidence]
