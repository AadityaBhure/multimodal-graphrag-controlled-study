"""Phase 9 foundations: router, partition, evidence memory, durable LLM, strict controllers, fixed context."""
import json
import pytest
from phase9_fakes import *  # noqa
from research.agentic import rule_router, partition
from research.agentic.llm import DurableLLM, ProviderPause, duration
from research.agentic.controllers import structured_call
from research.agentic.evidence import EvidenceMemory, render, provenance_paper_ids
from research.agentic.tools import fixed_context, PER_SOURCE_CHARS


def test_rule_router_cases_order_and_default():
    r = rule_router.route
    assert r('Which papers mention quantum annealing?')['sources'] == ('text',)
    assert r('Papers written by authors affiliated with MIT')['sources'] == ('graph',)
    assert r('Papers published before 2010 with at least 50 citations')['sources'] == ('structured',)
    assert r('Papers whose abstract mentions graphs by authors from MIT published after 2015')['sources'] == ('text', 'graph', 'structured')
    d = r('hello there')
    assert d['sources'] == ('text',) and d['fallback_default_text'] is True and d['reason_code'] == 'default_text'
    assert r('  CITATION   COUNT  ')['sources'] == ('structured',)
    assert r('Papers with citation count at least 5')['rule_hits']['graph'] == []


def test_router_never_sees_gold_or_labels():
    import ast, inspect
    names = {n.id for n in ast.walk(ast.parse(inspect.getsource(rule_router))) if isinstance(n, ast.Name)} |             {n.attr for n in ast.walk(ast.parse(inspect.getsource(rule_router))) if isinstance(n, ast.Attribute)}
    assert not any('gold' in x.lower() or 'modalit' in x.lower() or 'benchmark' in x.lower() for x in names)
    assert rule_router.next_unqueried('x', ['text']) == 'graph' and rule_router.next_unqueried('x', ['text', 'graph', 'structured']) is None
    assert rule_router.next_unqueried('Papers by authors', ['graph']) == 'text'     # routed set exhausted -> fixed T->G->S order


def test_partition_is_deterministic_and_query_id_hash_based():
    assert partition.bucket('a') == partition.bucket('a')
    ids = ['q%d' % i for i in range(2000)]
    dev = [i for i in ids if partition.is_dev(i)]
    assert 150 < len(dev) < 250 and all(partition.bucket(i) < 10 for i in dev)


def test_evidence_memory_dedup_and_rendering():
    m = EvidenceMemory()
    assert len(m.add([evidence('text', 1), evidence('text', 2)])) == 2
    assert m.add([evidence('text', 1), evidence('graph', 1)]) and len(m.ordered()) == 3
    g = evidence('graph', 5, {'paper_id': 5, 'title': 'T5', 'path': [{'source': 9, 'target': 5, 'relation': 'AUTHOR-WRITES-PAPER'}],
                              'nodes': [{'node_id': 9, 'label': 'Ann', 'node_type': 'author'}, {'node_id': 5, 'label': 'T5', 'node_type': 'paper'}]})
    assert 'Ann AUTHOR-WRITES-PAPER T5' in render(g) and provenance_paper_ids(g) == {5}
    assert render(evidence('structured', 3)).startswith('paper_id: 3')


def test_fixed_context_per_source_budget_order_and_queried_sections_only():
    items = [evidence('graph', 3), evidence('text', 1), evidence('structured', 4)]
    context, retained, truncated, _, _ = fixed_context(items, ('text', 'graph'), FakeStore(), None, options())
    assert context.index('[TEXT]') < context.index('[GRAPH]') and '[STRUCTURED]' not in context
    assert 'structured:paper:4' not in retained and retained == ('text:paper:1', 'graph:paper:3')
    empty = fixed_context([], ('graph',), FakeStore(), None, options())[0]
    assert empty == '[GRAPH]\n'                                   # queried-but-empty source stays visible
    big = [evidence('text', i, {'paper_id': i, 'content': 'x' * 3000}) for i in range(10)]
    ctx = fixed_context(big, ('text',), FakeStore(), None, options())[0]
    assert len(ctx) <= PER_SOURCE_CHARS and fixed_context(big, ('text',), FakeStore(), None, options())[0] == ctx


def test_durable_llm_reuse_resume_and_pause(tmp_path):
    llm, tr = make_llm(tmp_path, {'final': [answer([1])]})
    a = llm.chat('final', 'You answer a research-paper retrieval question x', 'u', 1024, 42)
    b = llm.chat('final', 'You answer a research-paper retrieval question x', 'u', 1024, 42)
    assert not a.reused and b.reused and tr.log == ['final'] and b.usage == a.usage and b.raw == a.raw
    c = llm.chat('final', 'You answer a research-paper retrieval question x', 'u2', 1024, 42)
    assert not c.reused and len(tr.log) == 2
    # a 429 is persisted and pauses; no silent retry, resume re-attempts the rate-limited stage only
    class Boom(Exception):
        status_code = 429
        body = 'quota gsk_secretsecretsecret'
    calls = []
    def bad(payload):
        calls.append(1); raise Boom()
    llm2 = DurableLLM(tmp_path / 'b', transport=bad, clock=lambda: 5., sleep=lambda s: None)
    with pytest.raises(ProviderPause):
        llm2.chat('final', 'You answer a research-paper retrieval question x', 'u', 1024, 42)
    stage = next((tmp_path / 'b' / 'stages').glob('*.json')); row = json.loads(stage.read_text())
    assert row['status'] == 'rate_limited' and 'gsk_secret' not in row['error'] and len(calls) == 1
    llm3 = DurableLLM(tmp_path / 'b', transport=ScriptedTransport({'final': [answer([])]}), clock=lambda: 9999., sleep=lambda s: None)
    assert llm3.chat('final', 'You answer a research-paper retrieval question x', 'u', 1024, 42).raw == answer([])


def test_admission_content_plus_128_and_not_completion_cap(tmp_path):
    llm, tr = make_llm(tmp_path, {'final': ['{}']})
    llm.chat('final', 'You answer a research-paper retrieval question x', 'word ' * 3000, 7000, 42)  # ~3.0k tokens + cap 7000 > 8000 is still admitted
    with pytest.raises(ProviderPause, match='cannot be repaired by waiting'):
        llm.chat('final', 'You answer a research-paper retrieval question x', 'word ' * 8000, 1024, 42)
    assert duration('1m26.4s') == pytest.approx(86.4) and duration('547ms') == pytest.approx(.547)


def test_structured_call_single_repair_and_strict_schema(tmp_path):
    good = json.dumps({'sufficient': False, 'next_subquery': 'more', 'reason': 'r'})
    llm, tr = make_llm(tmp_path, {'ar01_controller': ['not json'], 'repair': [good]})
    obj, events, results = structured_call(llm, 'ar01_controller', 'You are a multi-step retrieval controller x', 'u', 42)
    assert obj['next_subquery'] == 'more' and [e['valid'] for e in events] == [False, True] and tr.log == ['ar01_controller', 'repair']
    llm2, tr2 = make_llm(tmp_path / 'x', {'ar01_controller': ['{"sufficient": "yes"}'], 'repair': ['{"sufficient": false}']})
    obj, events, _ = structured_call(llm2, 'ar01_controller', 'You are a multi-step retrieval controller x', 'u', 42)
    assert obj is None and events[-1]['schema_repair_failed'] and tr2.log == ['ar01_controller', 'repair']      # exactly one repair
    llm3, _ = make_llm(tmp_path / 'y', {'validator': [json.dumps({'accept': True, 'error_type': 'bogus', 'unsupported_claims': []})], 'repair': ['x']})
    assert structured_call(llm3, 'validator', 'You are an evidence-grounding validator x', 'u', 42)[0] is None
