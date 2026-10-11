"""Deterministic fusion fixtures; no model downloads, stores or paid calls."""
import json
import pytest
from research.common.contracts import EvidenceItem, Provenance, RetrievalBundle
from research.common.serialization import canonical_json
from research.rq2.contracts import METHODS, SOURCES, FrozenInput, Options, evidence
from research.rq2.fusion import fuse, resolve, normalize
from research.rq2.system import FusionSystem
from research.rq2.generation import Journal
from research.baselines.config import BaselineOptions
from research.evaluation.contracts import SystemInput, RunRecord
from research.experiments.config import RunnerConfig
from research.experiments.runner import run
from test_evaluation import fixture_benchmark, query

def item(source, i=1, **kw):
    return EvidenceItem(evidence_id=kw.pop('evidence_id', source + ':' + str(i)), source_type=source,
        canonical_id=kw.pop('canonical_id', 'stark:' + str(i)), score=1,
        payload=kw.pop('payload', canonical_json({'paper_id': i, 'title': 'Fixture paper set', 'year': None})),
        provenance=(Provenance(dataset_version='fixture', source_id=str(i), locator='fixture'),), **kw)

def frozen(items=None):
    items = items if items is not None else [item(s) for s in SOURCES]
    return FrozenInput(question='Fixture paper set?', bundle=RetrievalBundle(query_id='q1',
        **{s + '_evidence': tuple(e for e in items if e.source_type == s) for s in SOURCES}),
        canonical_ids=('stark:1', 'stark:2'), aliases=(('fixture paper', ('stark:2',)), ('ambiguous', ('stark:1', 'stark:2'))))

@pytest.mark.parametrize('method', METHODS)
def test_frozen_boundaries_and_determinism(method):
    data = frozen(); before = data.bundle.canonical_bytes()
    a = fuse(data, Options(method=method)); b = fuse(data, Options(method=method))
    assert a[:2] == b[:2] and data.bundle.canonical_bytes() == before
    assert len(a[0]) <= 24000
    assert all(e in evidence(data) for e in a[1])
    assert a[2]['additional_retrieval_calls'] == 0
    assert a[2]['entity_alignment_correctness'] is None

def test_alignment_precedence_ambiguity_and_nfkc():
    data = frozen()
    assert resolve(item('text'), data) == ('stark:1', 'exact_canonical_id')
    assert resolve(item('text', canonical_id='unknown', metadata='{"stark_node_id":2}'), data) == ('stark:2', 'exact_stark_id')
    assert resolve(item('text', canonical_id='unknown', payload='{"title":"  FIXTURE  PAPER "}'), data) == ('stark:2', 'exact_normalized_alias')
    assert resolve(item('text', canonical_id='unknown', payload='{"title":"ambiguous"}'), data) == (None, 'ambiguous_alias')
    assert normalize('ＦＯＯ') == 'foo'
    context, kept, d = fuse(data, Options(method='CF-01'))
    assert len(d['groups']) == 1 and len(kept) == 3 and d['unresolved_count'] == 0

def test_selector_limits_and_all_decisions():
    data = frozen([item(s, i) for s in SOURCES for i in range(1, 9)])
    context, kept, d = fuse(data, Options(method='CF-02'))
    assert len(kept) == 10 and sum(e.source_type != 'text' for e in kept) == 5
    assert len(d['selector']) == 24
    assert [e.source_type for e in kept[:5]] == ['graph'] * 5
    data = frozen([item('graph', payload='{"word":"xyz"}'), item('text')])
    assert [e.source_type for e in fuse(data, Options(method='CF-02'))[1]] == ['text']

@pytest.mark.parametrize('method', METHODS)
def test_empty_oversize_and_nulls(method):
    assert not fuse(frozen([]), Options(method=method))[1]
    large = item('text', content='X' * 30000)
    context, kept, d = fuse(frozen([large, item('graph')]), Options(method=method))
    assert large not in kept and len(context) <= 24000
    assert '"year":null' in context

def test_conflict_provenance_not_repaired():
    overlay = item('structured', evidence_id='overlay', metadata='{"origin":"phase4_evaluation_overlay","overlay_sha256":"sha"}', payload='{"year":1900}')
    data = frozen([item('structured'), overlay])
    context, kept, d = fuse(data, Options(method='CF-01'))
    assert '1900' in context and '"year":null' in context
    assert 'phase4_evaluation_overlay' in context and d['retained_overlay_ids'] == ['overlay']

class FakeGenerator:
    version = 'fixture'
    def __init__(self, cap=1024, bad=False):
        self.options = BaselineOptions(max_completion_tokens=cap)
        self.calls = []; self.bad = bad
    def generate(self, question, context, seed):
        self.calls.append((question, context, seed))
        return ('invalid' if self.bad else '{"answer_ids":[1],"explanation":"fixture"}'), {
            'generation_ms': 2., 'llm_calls': 1, 'input_tokens': 10, 'output_tokens': 5,
            'token_measurement_source': 'fixture'}

def test_late_fusion_four_calls_and_journal_resume(tmp_path):
    final, intermediate = FakeGenerator(), FakeGenerator(220)
    journal = Journal(tmp_path, final, intermediate)
    system = FusionSystem(Options(method='CF-03'), {'q1': frozen()}, journal)
    request = SystemInput(query_id='q1', question='Fixture paper set?', seed=42)
    output = system.execute(request)
    assert not output.errors and output.answer_ids == (1,)
    assert len(final.calls) == 1 and len(intermediate.calls) == 3
    assert output.observation.llm_calls == 4 and output.observation.input_tokens == 40
    assert len(json.loads(output.diagnostics)['stage_results']) == 4
    again = system.execute(request)
    assert len(final.calls) == 1 and len(intermediate.calls) == 3
    assert json.loads(again.diagnostics)['journal_cache_hits'] == 4
    for _, context, _ in intermediate.calls:
        assert sum(heading in context for heading in ('TEXT EVIDENCE', 'GRAPH EVIDENCE', 'STRUCTURED EVIDENCE')) == 1

def test_late_offline_is_null_and_invalid_stage_preserves_usage(tmp_path):
    request = SystemInput(query_id='q1', question='Fixture paper set?', seed=42)
    output = FusionSystem(Options(method='CF-03'), {'q1': frozen()}).execute(request)
    assert output.context is None and output.answer_ids is None and output.ranked_paper_ids is None
    final, intermediate = FakeGenerator(), FakeGenerator(220, bad=True)
    output = FusionSystem(Options(method='CF-03'), {'q1': frozen()}, Journal(tmp_path, final, intermediate)).execute(request)
    assert output.errors and output.answer_ids is None and not final.calls
    assert output.observation.llm_calls == 1 and output.observation.input_tokens == 10

def test_ambiguous_journal_refuses_retry(tmp_path):
    class Crash(FakeGenerator):
        def generate(self, *args):
            self.calls.append(args)
            raise RuntimeError('transport')
    generator = Crash()
    journal = Journal(tmp_path, generator, FakeGenerator(220))
    with pytest.raises(RuntimeError): journal.call('final', 'q', 'c', 42, 'binding')
    with pytest.raises(RuntimeError, match='reconciliation'): journal.call('final', 'q', 'c', 42, 'binding')
    assert len(generator.calls) == 1

@pytest.mark.parametrize('method', METHODS)
def test_runner_resume_schema_and_gold_boundary(tmp_path, method):
    root = fixture_benchmark(tmp_path / 'benchmark', [query()])
    cfg = RunnerConfig(config_id='fixture-' + method, system_id=method, system_version='1')
    system = FusionSystem(Options(method=method), {'q1': frozen()})
    output = tmp_path / 'run'
    run(cfg, root, output, system, provenance={'fixture': True})
    before = (output / 'records.jsonl').read_bytes()
    run(cfg, root, output, system, provenance={'fixture': True})
    assert before == (output / 'records.jsonl').read_bytes()
    r = RunRecord.model_validate_json(before.decode().strip())
    assert r.metrics['f1'] is None and r.metrics['context_tokens'] is None
    assert not r.errors
    assert 'gold_ids' not in frozen().model_dump() and 'gold_ids' not in r.output.context if r.output.context else True
    with pytest.raises(ValueError, match='Incompatible'):
        run(cfg.model_copy(update={'seed': 1}), root, output, system, provenance={'fixture': True})

def test_question_overlay_mismatch():
    system = FusionSystem(Options(method='CF-B0'), {'q1': frozen()})
    with pytest.raises(ValueError, match='mismatch'):
        system.execute(SystemInput(query_id='q1', question='different', seed=42))

def test_read_only_viewer():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'fusion_review_app.py')).run()
    assert not app.exception
    app.selectbox[1].select('CF-03').run()
    assert not app.exception
    app.selectbox[2].select('generation').run()
    assert not app.exception and not app.button

def test_no_retrieval_dependencies():
    import ast
    from pathlib import Path
    forbidden = ('duckdb', 'faiss', 'networkx', 'research.baselines.stores', 'research.baselines.retrieval')
    for path in (Path(__file__).resolve().parents[1] / 'research/rq2').glob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            names = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module or ''] if isinstance(node, ast.ImportFrom) else []
            assert not any(name.startswith(forbidden) for name in names)
