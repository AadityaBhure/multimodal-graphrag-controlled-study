"""Canonical RQ2 methods (Phase 1D §5): acceptance tests with a fake provider (no network, no store)."""
import json
import pytest
from research.common.contracts import EvidenceItem, Provenance, RetrievalBundle
from research.evaluation.contracts import SystemInput
from research.rq2.contracts import FrozenInput
from research.repair.dispatch import Paused
from research.repair.rq2_canonical import fusion as F
from research.repair.rq2_canonical.system import CanonicalFusionSystem


def item(source, pid, score, content='c', alias=None):
    payload = json.dumps({'title': alias}) if alias else None
    return EvidenceItem(evidence_id='%s:paper:%d' % (source, pid), source_type=source, canonical_id='stark:%d' % pid, content=content,
                        payload=payload, score=score, provenance=(Provenance(dataset_version='v1', source_id=str(pid), locator='x'),),
                        metadata=json.dumps({'stark_node_id': pid}))


def frozen(text=(), graph=(), structured=(), known=None, aliases=()):
    b = RetrievalBundle(query_id='q1', text_evidence=tuple(text), graph_evidence=tuple(graph), structured_evidence=tuple(structured))
    ids = known if known is not None else tuple(sorted({e.canonical_id for e in (*text, *graph, *structured)}))
    return FrozenInput(question='Which papers?', bundle=b, canonical_ids=ids, aliases=tuple(aliases))


REG = {'stark:%d' % i: {'entity_type': 'paper', 'display_name': 'Paper %d' % i} for i in range(1, 40)}


class FakeCall:
    def __init__(self, script):
        self.script, self.log = script, []
    def __call__(self, stage, system, user, seed, cap):
        self.log.append((stage, cap, user))
        role = stage.split(':')[1]
        value = self.script[role]
        raw = value(user) if callable(value) else value
        if isinstance(raw, BaseException):
            raise raw
        return raw, {'llm_calls': 1, 'input_tokens': 10, 'output_tokens': 2, 'generation_ms': 5.}, False


def run(method, f, call=None):
    s = CanonicalFusionSystem(method, {'q1': f}, REG, call)
    return s.execute(SystemInput(query_id='q1', question='Which papers?', seed=7, overlay=None))


def ans(ids):
    return json.dumps({'answer_ids': ids, 'explanation': 'x'})


# ------------------------------------------------------------------ CF-01
def test_cf01_every_item_in_exactly_one_group_ordered_by_score_then_coverage_then_id():
    f = frozen(text=[item('text', 2, .9), item('text', 1, .5)], graph=[item('graph', 1, .5)], structured=[item('structured', 3, .9)])
    ctx, kept, d = F.cf01(f, 24000, REG)
    members = [m for g in d['group_order'] for m in g['members']]
    assert sorted(members) == sorted(e.evidence_id for e in F.evidence(f)) and len(members) == len(set(members))
    assert [g['key'] for g in d['group_order']] == ['stark:2', 'stark:3', 'stark:1'] or [g['key'] for g in d['group_order']][:2] == ['stark:2', 'stark:3']
    assert '[ENTITY stark:1 | Paper 1]\n[TEXT]' in ctx and '[GRAPH]' in ctx and '[PROVENANCE]' in ctx and d['group_truncated'] is False


def test_cf01_coverage_breaks_score_ties():
    f = frozen(text=[item('text', 5, .5), item('text', 6, .5)], graph=[item('graph', 6, .1)])
    _, _, d = F.cf01(f, 24000, REG)
    assert [g['key'] for g in d['group_order']] == ['stark:6', 'stark:5']        # same max score, stark:6 has two sources


def test_cf01_truncates_next_group_and_marks_it():
    big = 'x' * 900
    f = frozen(text=[item('text', 1, .9, big), item('text', 2, .8, big)], graph=[item('graph', 2, .1, big)])
    one_group = len(F.render_group('stark:1', [F.evidence(f)[0]], REG, True))
    ctx, kept, d = F.cf01(f, one_group + 1 + 1500, REG)    # full stark:2 group (~2,275) does not fit; its top item (~1,156) does
    assert d['group_truncated'] and d['truncated_group'] == 'stark:2' and [e.evidence_id for e in kept] == ['text:paper:1', 'text:paper:2']


def test_cf01_unaligned_group_and_source_separated_fallback():
    f = frozen(text=[item('text', 1, .9)], known=())                              # nothing resolves
    ctx, kept, d = F.cf01(f, 24000, REG)
    assert d['fallback'] == 'source_separated' and 'TEXT EVIDENCE' in ctx and d['resolved'] == 0


def test_cf01_global_resolver_uses_entity_type_only():
    e = item('text', 1, .9, alias='Same Title')
    f = frozen(text=[e], known=(), aliases=[('same title', ('stark:1', 'stark:900'))])
    reg = {**REG, 'stark:900': {'entity_type': 'author', 'display_name': 'A'}}
    _, _, d = F.cf01(f, 24000, reg)
    assert d['alignments'][0]['rule'] == 'global_type_resolver' and d['global_resolver_uses'] == 1


# ------------------------------------------------------------------ CF-02
def bundle02():
    return frozen(text=[item('text', i, 1 - i / 10) for i in range(1, 7)],
                  graph=[item('graph', i, i / 10) for i in range(10, 14)], structured=[item('structured', i, .5) for i in range(20, 24)])


def test_cf02_one_selector_call_at_most_five_structural_then_semantic_fill_to_ten():
    call = FakeCall({'selector': json.dumps({'selected_ids': ['graph:paper:13', 'structured:paper:20', 'bogus', 'graph:paper:13'], 'reason': 'r'}),
                     'final': ans([13])})
    out = run('CF-02', bundle02(), call)
    d = json.loads(out.diagnostics)
    assert [s[0].split(':')[1] for s in call.log] == ['selector', 'final']
    assert d['selected_structural'] == ['graph:paper:13', 'structured:paper:20'] and 'bogus' in d['selector_invalid_ids']
    assert len(out.retained_evidence_ids) == 8 and d['semantic_fill'] == ['text:paper:%d' % i for i in range(1, 7)]
    assert out.answer_ids == (13,)


def test_cf02_repair_once_then_relevance_fallback():
    call = FakeCall({'selector': 'not json', 'selector_repair': 'still not json', 'final': ans([])})
    d = json.loads(run('CF-02', bundle02(), call).diagnostics)
    assert d['selector_fallback'] == 'relevance' and len(d['selected_structural']) == 5
    assert [s[0].split(':')[1] for s in call.log] == ['selector', 'selector_repair', 'final']


def test_cf02_provider_pause_propagates_not_fallback():
    with pytest.raises(Paused):
        run('CF-02', bundle02(), FakeCall({'selector': Paused('quota'), 'final': ans([])}))


def test_cf02_budget_trim_removes_semantic_tail_first():
    s = [item('structured', 1, .9, 'y' * 300)]
    t = [item('text', i, .5, 'z' * 300) for i in range(2, 5)]
    ctx, kept, trimmed = F.cf02_context(s, t, 1100)
    assert trimmed[0] == 'text:paper:4' and kept[0].evidence_id == 'structured:paper:1'


# ------------------------------------------------------------------ CF-03
def test_cf03_per_source_calls_validated_ids_and_grounded_final():
    def reason(user):
        if 'SOURCE TEXT' in user:
            return json.dumps({'candidate_answer': 'p1', 'supporting_evidence_ids': ['text:paper:1', 'graph:paper:2'], 'confidence': 'high'})
        return json.dumps({'candidate_answer': 'p2', 'supporting_evidence_ids': ['graph:paper:2'], 'confidence': 'medium'})
    call = FakeCall({'reason': reason, 'fusion': ans([1, 2])})
    out = run('CF-03', frozen(text=[item('text', 1, .9)], graph=[item('graph', 2, .9)]), call)
    d = json.loads(out.diagnostics)
    roles = [s[0].split(':')[1] for s in call.log]
    assert roles == ['reason', 'reason', 'fusion'] and all(s[1] == 220 for s in call.log[:2])
    text = next(x for x in d['source_findings'] if x['source'] == 'text')
    assert text['invalid_supporting_ids'] == ['graph:paper:2']                 # an intermediate may cite only its own source
    assert next(x for x in d['source_findings'] if x['source'] == 'structured')['status'] == 'NO_EVIDENCE'
    assert set(out.answer_ids) == {1, 2}


def test_cf03_source_failure_isolated_and_final_cannot_cite_ungrounded_papers():
    call = FakeCall({'reason': lambda u: 'garbage' if 'SOURCE GRAPH' in u else json.dumps(
        {'candidate_answer': 'p1', 'supporting_evidence_ids': ['text:paper:1'], 'confidence': 'low'}), 'fusion': ans([2]), 'fusion_retry': ans([2])})
    out = run('CF-03', frozen(text=[item('text', 1, .9)], graph=[item('graph', 2, .9)]), call)
    d = json.loads(out.diagnostics)
    assert next(x for x in d['source_findings'] if x['source'] == 'graph')['status'] == 'ERROR_NO_EVIDENCE'
    assert d.get('fusion_retry') is True and out.errors and out.answer_ids is None     # paper 2 not grounded -> retry once -> error


def test_no_retrieval_and_input_unchanged_for_all_methods():
    f = bundle02()
    for m in ('CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03'):
        out = run(m, f)                                                           # offline
        d = json.loads(out.diagnostics)
        assert d['additional_retrieval_calls'] == 0 and out.observation.retrieval_calls == 0 and len(out.context) <= 24000


# ------------------------------------------------------------------ shared-quota dispatcher
def test_shared_quota_counts_other_studies_ledgers(tmp_path, monkeypatch):
    from tests.test_repair_dispatch import dispatcher
    from research.repair.rq2_canonical import dispatch as D2
    d, calls, clock = dispatcher(tmp_path, monkeypatch); d.maximum = 10
    shared = object.__new__(D2.SharedQuotaDispatcher); shared.__dict__.update(d.__dict__)
    other = tmp_path / 'other_state.json'
    other.write_text(json.dumps({'ledger': [[clock[0] - 100, 189_000]]}))
    shared.external_ledgers = (other,)
    monkeypatch.setattr(D2.time, 'time', lambda: clock[0])
    with pytest.raises(Paused, match='Daily token budget'):
        shared.call('one', 'system', 'user', 42, 1024)          # 189k used elsewhere + ~1.2k needed > 190k
    assert not calls and shared.daily_budget == 190_000            # budget restored after the check
    other.write_text(json.dumps({'ledger': [[clock[0] - 90_000, 189_000]]}))   # outside the 24 h window
    shared.call('one', 'system', 'user', 42, 1024)
    assert len(calls) == 1
