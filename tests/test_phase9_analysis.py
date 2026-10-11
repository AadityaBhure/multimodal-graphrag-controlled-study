"""Hand-computable checks of the frozen Phase 9 metric definitions and the clustered statistics."""
import json
import pytest
from research.agentic import analysis as A


def rec(qid, method, modality, sources, stop='routed_sources_retrieved', f1=1.0, errors=(), status='ok', fallbacks=(), events=(), wait=0., total=1000.):
    calls = [{'step': i + 1, 'source': s, 'query': 'q', 'evidence_ids': [], 'new_evidence': 1, 'latency_ms': 1., 'cache_hit': False, 'status': 'ok', 'reason': 'r', 'detail': {}}
             for i, s in enumerate(sources)]
    diag = {'sources_called': list(dict.fromkeys(sources)), 'tool_calls': calls, 'stop_reason': stop, 'status': status, 'fallbacks': list(fallbacks),
            'events': list(events), 'timings_ms': {'provider_wait': wait}}
    return {'query_id': qid, 'system_id': method, 'stress': ['normal'], 'labels': {'modality': modality}, 'errors': list(errors),
            'metrics': {'f1': f1, 'exact_match': float(f1 == 1.0), 'recall@5': 1.0, 'llm_calls': 2, 'input_tokens': 100, 'output_tokens': 10},
            'total_latency_ms': total, 'output': {'diagnostics': json.dumps(diag)}}


def test_source_metrics_and_stopping_definition():
    m = A.per_record(rec('generated:a:normal', 'X', 'TG', ['text', 'graph']))
    assert (m['source_precision'], m['source_recall'], m['source_f1'], m['source_exact']) == (1., 1., 1., 1.) and m['stopping_accuracy'] == 1. and m['covered_step'] == 2
    over = A.per_record(rec('generated:a:normal', 'X', 'G', ['text', 'graph', 'structured']))
    assert over['source_precision'] == pytest.approx(1 / 3) and over['source_recall'] == 1. and over['unnecessary_retrieval'] == pytest.approx(2 / 3)
    assert over['covered_step'] == 2 and over['stopping_accuracy'] == 0. and over['over_retrieval'] == 1.        # stopped one call after R was covered
    miss = A.per_record(rec('generated:a:normal', 'X', 'TGS', ['text', 'graph'], stop='sufficient'))
    assert miss['required_source_miss'] == pytest.approx(1 / 3) and miss['premature_stop'] == 1. and miss['max_step_exhaustion'] == 0. and miss['stopping_accuracy'] == 0.
    budget = A.per_record(rec('generated:a:normal', 'X', 'TGS', ['text', 'graph'], stop='max_iterations_rejected'))
    assert budget['max_step_exhaustion'] == 1. and budget['premature_stop'] == 0.
    none = A.per_record(rec('generated:a:normal', 'X', 'S', [], stop='route_A_no_retrieval'))
    assert none['source_f1'] == 0. and none['premature_stop'] == 1. and none['unnecessary_retrieval'] == 0.
    assert A.per_record(rec('generated:a:normal', 'X', 'unverified', ['text']))['source_f1'] is None             # NULL, never zero


def test_intrinsic_latency_excludes_provider_waiting():
    m = A.per_record(rec('generated:a:normal', 'X', 'T', ['text'], wait=400., total=1000.))
    assert m['intrinsic_ms'] == 600. and m['provider_wait_ms'] == 400.


def test_family_clustering_and_exact_sign_flip():
    assert A.family('generated:abc:noisy') == 'generated:abc'
    deltas = {'generated:%d:%s' % (f, s): 1.0 for f in range(4) for s in ('normal', 'noisy')}          # every family +1
    assert A.sign_flip_p(deltas) == pytest.approx(2 / 16)                                              # only all-plus / all-minus are as extreme
    ci = A.bootstrap_ci(deltas)
    assert ci == [1.0, 1.0] and A.bootstrap_ci({'generated:1:normal': 1.}) is None                    # one family: no interval claimed
    mixed = {'generated:1:normal': 1., 'generated:2:normal': -1.}
    assert A.sign_flip_p(mixed) == 1.0


def test_holm_is_monotone_and_preserves_none():
    adj = A.holm({'a': .01, 'b': .02, 'c': .04, 'd': None})
    assert adj['a'] == pytest.approx(.03) and adj['b'] == pytest.approx(.04) and adj['c'] == pytest.approx(.04) and adj['d'] is None


def test_paired_uses_only_queries_with_both_values():
    a = [rec('generated:1:normal', 'A', 'T', ['text'], f1=1.0), rec('generated:2:normal', 'A', 'T', ['text'], f1=None)]
    b = [rec('generated:1:normal', 'B', 'T', ['text'], f1=0.5), rec('generated:2:normal', 'B', 'T', ['text'], f1=0.0)]
    a = [A.per_record(r) for r in a]; b = [A.per_record(r) for r in b]
    p = A.paired(a, b, 'answer_f1')
    assert p['n'] == 1 and p['mean_delta'] == .5


def test_pareto_non_dominated_set_and_incomparable_nulls():
    means = {'good': {'answer_f1': .8, 'retrieval_calls': 1.}, 'bad': {'answer_f1': .6, 'retrieval_calls': 3.}, 'cheap': {'answer_f1': .5, 'retrieval_calls': 0.5}}
    assert A.pareto(means, ('answer_f1',), ('retrieval_calls',)) == ['cheap', 'good']
    assert A.pareto({'x': {'answer_f1': None}, 'y': {'answer_f1': .1}}, ('answer_f1',), ()) == ['x', 'y']


def test_failure_taxonomy_separates_routing_from_retriever_weakness():
    ok_route = rec('generated:a:normal', 'X', 'T', ['text'], f1=0.0)
    assert 'retriever_failure_despite_correct_routing' in A.failure_labels(ok_route, [1]) and 'required_source_never_selected' not in A.failure_labels(ok_route, [1])
    bad_route = rec('generated:a:normal', 'X', 'G', ['text'], f1=0.0)
    labels = A.failure_labels(bad_route, [1])
    assert {'wrong_initial_routing', 'required_source_never_selected', 'unnecessary_source_selected'} <= set(labels) and 'retriever_failure_despite_correct_routing' not in labels
    loop = rec('generated:a:normal', 'X', 'S', ['structured'], stop='loop_guard_insufficient_evidence', status='insufficient_evidence')
    assert {'loop_or_repeated_action', 'insufficient_evidence', 'structured_intent_failure'} <= set(A.failure_labels(loop, [1]))
    fa = rec('generated:a:normal', 'AR-03', 'T', ['text'], events=[{'kind': 'candidate', 'iteration': 1, 'answer_ids': [9], 'parse_error': None},
                                                                  {'kind': 'validator', 'iteration': 1, 'verdict': {'accept': True, 'error_type': 'none', 'unsupported_claims': []}}])
    assert 'validator_false_accept' in A.failure_labels(fa, [1])
    ev = rec('generated:a:normal', 'AR-02', 'T', ['text'], events=[{'kind': 'evaluation', 'round': 0, 'state': 'GOOD', 'evaluator_failed': False, 'evidence_ids': ['text:paper:5']}])
    assert {'evaluator_misclassification', 'calibration_or_threshold_failure'} <= set(A.failure_labels(ev, [1]))
