"""Showcase app: bundle integrity, content bindings, deterministic formatting, metric parity and page smoke tests."""
from pathlib import Path
import hashlib, json, re, subprocess, sys
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from showcase.lib.bundle import Bundle
from showcase.lib.content import load_content, all_bindings, render, resolve, PLACEHOLDER
from showcase.lib.fmt import fmt, number
from showcase.lib.metrics import answer_scores
from showcase.lib.traces import ar_steps
from showcase.lib.state import PAGES

APP = ROOT / 'showcase/app.py'


@pytest.fixture(scope='module')
def bundle():
    return Bundle()


def test_bundle_checksums_verify(bundle):
    assert bundle.verified, {k: ok for k, ok in bundle.checks.items() if not ok}
    m = json.loads((ROOT / 'showcase/bundle/manifest.json').read_text(encoding='utf-8'))
    for name, meta in m['files'].items():
        assert hashlib.sha256((ROOT / 'showcase/bundle' / name).read_bytes()).hexdigest() == meta['sha256']


def test_bundle_matches_frozen_analyses(bundle):
    """Study-level numbers are copied, not recomputed: spot-check against the analysis files."""
    rq3 = json.loads((ROOT / 'documentation/phase9/analysis_local.json').read_text(encoding='utf-8'))
    assert bundle.results['RQ3']['descriptive']['AR-B1']['source_f1'] == rq3['descriptive']['AR-B1']['source_f1']
    assert bundle.results['RQ3']['pareto'] == rq3['pareto']
    rq4 = json.loads((ROOT / 'documentation/rq4/analysis_local.json').read_text(encoding='utf-8'))
    t = next(x for x in bundle.results['RQ4']['tests']['total_tokens'] if (x['a'], x['b']) == ('INT-1', 'AR-B1'))
    assert t['p_holm'] == rq4['paired_tests']['total_tokens']['INT-1 vs AR-B1']['p_holm']
    for d in bundle.stats_demo:                     # the builder re-derived each demo p and asserted equality; keep it pinned
        assert d['reported']['p'] is not None


@pytest.mark.skipif(not (ROOT / 'data/MMG_STARK_MAG/manifest.json').exists(), reason='needs the frozen data and run records')
def test_bundle_rebuild_is_byte_identical():
    r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_showcase_bundle.py'), '--check'], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0 and 'IDENTICAL' in r.stdout, r.stdout + r.stderr


def test_content_has_no_stray_yaml_keys():
    """An unquoted comma inside a YAML flow mapping silently creates extra keys with empty values."""
    bad = []
    def walk(n, w):
        if isinstance(n, dict):
            for k, v in n.items():
                if v is None:
                    bad.append('%s.%s' % (w, k))
                walk(v, '%s.%s' % (w, k))
        elif isinstance(n, list):
            for i, v in enumerate(n):
                walk(v, '%s[%d]' % (w, i))
    walk(load_content(), 'content')
    assert not bad, bad
    for k, m in load_content()['evaluation']['metrics'].items():
        assert set(m) == {'name', 'direction', 'plain', 'formula', 'why'}, k


def test_every_placeholder_resolves_and_signs_read_correctly(bundle):
    bindings = all_bindings(load_content())
    assert len(bindings) >= 15
    for where, text, values in bindings:
        names = set(PLACEHOLDER.findall(text))
        assert names == set(values), (where, names, set(values))
        out = render(text, values, bundle.results)
        assert '{' not in out, (where, out)
        for name in re.findall(r'\+\{([A-Z0-9_]+)\}', text):     # "+{D}" must not show a negative number
            v, _ = resolve(values[name], bundle.results)
            assert v >= 0, (where, name, v)


@pytest.mark.parametrize('value,kind,expected', [
    (0.2834, 'rate', '0.283'), (0.0005, 'rate', '0.001'), (-0.0, 'rate', '0.000'), (-0.0004, 'rate', '0.000'), (-0.0136, 'rate', '−0.014'),
    (4982.0, 'tokens', '4,982'), (1415.78125, 'tokens', '1,416'), (2.5, 'tokens', '3'), (7644.84, 'ms', '7.6 s'), (40709.47, 'ms', '40.7 s'),
    (0.013671875, 'p', '0.014'), (0.000244140625, 'p', '< 0.001'), (1.0, 'p', '1.000'), (3.5185, 'ratio', '3.5'), (0.3377, 'pct', '34 %'),
    (6.535714, 'calls', '6.54'), (1.0, 'calls', '1'), (None, 'rate', '—')])
def test_formatting_is_deterministic(value, kind, expected):
    assert fmt(value, kind) == expected


def test_signed_numbers():
    assert number(2168.4, 0, sign=True) == '+2,168'
    assert number(-629.2, 0, sign=True) == '−629'
    assert number(0.0, 3, sign=True) == '0.000'


@pytest.mark.parametrize('pred,gold', [([], []), ([1], []), ([], [1]), ([1, 2], [2, 3]), ([1, 2, 3], [1, 2, 3]), ([4], [1, 2])])
def test_answer_scores_match_research_metrics(pred, gold):
    from research.evaluation.metrics import answer_metrics
    ours, theirs = answer_scores(pred, gold), answer_metrics(pred, gold)
    for k in ('precision', 'recall', 'f1', 'exact_match'):
        assert ours[k] == theirs[k], k


def test_traces_are_ordered_and_complete(bundle):
    X = bundle.explorer('RQ3')
    for q, by in X['by_query'].items():
        for m, entry in by.items():
            kinds = [s['kind'] for s in entry['steps']]
            assert kinds[-1] == 'stop'
            assert sum(k == 'search' for k in kinds) == entry['metrics']['retrieval_calls'], (q, m)
    ar03 = {'tool_calls': [{'step': 1, 'source': 'text', 'query': 'x', 'evidence_ids': ['a'], 'new_evidence': 1, 'reason': 'textual', 'status': 'ok'}],
            'events': [{'kind': 'agent_action', 'iteration': 1, 'action': {'source': 'text', 'retrieval_query': 'x', 'reason_code': 'textual'}},
                       {'kind': 'candidate', 'iteration': 1, 'answer_ids': [1]}, {'kind': 'validator', 'iteration': 1, 'verdict': {'accept': True}}],
            'stop_reason': 'validator_accepted', 'status': 'ok'}
    assert [s['kind'] for s in ar_steps('AR-03', ar03)[0]] == ['agent', 'search', 'draft', 'validate', 'stop']


def _app(profile):
    from streamlit.testing.v1 import AppTest
    import showcase.config as config
    config.PROFILE = profile
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@pytest.mark.parametrize('profile', ['showcase', 'full'])
def test_every_page_renders(profile):
    at = _app(profile)
    for path, *_ in PAGES:
        at.switch_page(path); at.run()
        assert not at.exception, (profile, path, [e.value for e in at.exception])
        assert not at.error, (profile, path, [e.value for e in at.error])


def test_explorers_respond_to_choices(bundle):
    at = _app('showcase')
    for path, rq, other in (('pages/p05_rq1.py', 'RQ1', 'CM-B0'), ('pages/p06_rq2.py', 'RQ2', 'CF-B0'), ('pages/p07_rq3.py', 'RQ3', 'AR-B0')):
        at.switch_page(path); at.run()
        box = next(s for s in at.selectbox if s.label.startswith('Question'))
        box.set_value(bundle.explorer(rq)['queries'][-1]).run()     # widgets take raw values (labels are formatted)
        assert not at.exception, (path, [e.value for e in at.exception])
        cmp = next(s for s in at.selectbox if s.label.startswith('Compare'))
        cmp.set_value(other).run()
        assert not at.exception, (path, [e.value for e in at.exception])


def test_overall_winners_are_reproducible_and_consistent(bundle):
    """The ranking in the bundle is recomputed here from the method means; the content names the same winners; the
    combined system is the chain of the three winners."""
    from scripts.build_results_package import average_ranks
    content = load_content()
    for rq in ('RQ1', 'RQ2', 'RQ3'):
        o, d = bundle.results[rq]['overall'], bundle.results[rq]['descriptive']
        total = {m: 0. for m in bundle.results[rq]['methods']}
        for a in o['axes']:
            r = average_ranks({m: d[m][a['metric']] for m in total}, a['direction'] == 'higher')
            for m in total:
                total[m] += r[m]
        assert total == o['total'], rq
        assert min(total, key=lambda m: (total[m], o['order'].index(m))) == o['winner'] == content[rq.lower()]['overall']['winner'], rq
        for s in content[rq.lower()]['overall']['situations']:
            assert s['pick'] in bundle.results[rq]['methods'] and s['pick'] != o['winner'], (rq, s['pick'])
    c = bundle.results['RQ4']['combined']
    assert c['matches_rq4'] and c['rq4_pipeline'] == [bundle.results[rq]['overall']['winner'] for rq in ('RQ3', 'RQ1', 'RQ2')]
