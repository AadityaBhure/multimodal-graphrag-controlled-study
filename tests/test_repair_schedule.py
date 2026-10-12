"""RQ1 operational revision 4: query-major prefetch, then replay-only runner replay."""
import json
import pytest
from research.repair import schedule, dispatch
from tests.test_repair_dispatch import dispatcher


def test_interleaved_is_query_major_and_sorted():
    assert schedule.interleaved({'q2': 0, 'q1': 0}, ['A', 'B']) == [('q1', 'A'), ('q1', 'B'), ('q2', 'A'), ('q2', 'B')]


def test_prefetch_resumes_and_records_deterministic_exceptions(tmp_path):
    seen = []
    def execute(q, m):
        seen.append((q, m))
        if (q, m) == ('q1', 'B'): raise ValueError('parser')
    order = schedule.interleaved(['q1', 'q2'], ['A', 'B'])
    schedule.prefetch(order, execute, tmp_path, log=lambda *a: None)
    assert seen == order
    outcomes = {(r['query_id'], r['method']): r['outcome'] for r in (json.loads(p.read_text()) for p in tmp_path.rglob('*.json'))}
    assert outcomes[('q1', 'B')] == 'exception:ValueError' and outcomes[('q2', 'A')] == 'executed'
    schedule.prefetch(order, lambda q, m: seen.append('again'), tmp_path, log=lambda *a: None)
    assert 'again' not in seen                         # completed pairs are skipped on resume


def test_prefetch_stops_on_provider_pause_and_resumes_at_that_pair(tmp_path):
    calls = []
    def pausing(q, m):
        calls.append((q, m))
        if (q, m) == ('q1', 'B'): raise dispatch.Paused('daily budget')
    order = schedule.interleaved(['q1', 'q2'], ['A', 'B'])
    with pytest.raises(dispatch.Paused):
        schedule.prefetch(order, pausing, tmp_path, log=lambda *a: None)
    resumed = []
    schedule.prefetch(order, lambda q, m: resumed.append((q, m)), tmp_path, log=lambda *a: None)
    assert resumed == [('q1', 'B'), ('q2', 'A'), ('q2', 'B')]


def test_replay_only_returns_stored_response_and_never_sends(tmp_path, monkeypatch):
    d, calls, _ = dispatcher(tmp_path, monkeypatch); d.maximum = 10
    # stage A, query-major: q1/A, q1/B, q2/A, q2/B
    for q, m in schedule.interleaved(['q1', 'q2'], ['A', 'B']):
        d.call(m + ':final:' + q, 'SYS', 'context for ' + q + m, 7, 1024)
    assert [c[1]['messages'][1]['content'] for c in calls] == ['context for q1A', 'context for q1B', 'context for q2A', 'context for q2B']
    sent = len(calls)
    d.replay_only = True
    # stage B, method-major (the unchanged runner): same payloads -> stored responses, no new call
    for m in ('A', 'B'):
        for q in ('q1', 'q2'):
            raw, usage, reused = d.call(m + ':final:' + q, 'SYS', 'context for ' + q + m, 7, 1024)
            assert reused is True
    assert len(calls) == sent
    # any payload difference stops the run instead of being sent
    with pytest.raises(dispatch.Paused, match='Replay found no completed provider response'):
        d.call('A:final:q1', 'SYS', 'context for q1A CHANGED', 7, 1024)
    assert len(calls) == sent
