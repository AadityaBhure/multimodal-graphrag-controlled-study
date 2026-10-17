"""Deterministic number formatting for every value the app shows.

One rule per kind of quantity, rounding half up (never banker's rounding), a true minus sign, no negative zero.
"""
from decimal import Decimal, ROUND_HALF_UP

KIND = {
    # shares and rates in [0, 1]
    **dict.fromkeys(('answer_f1', 'answer_em', 'answerable_f1', 'precision', 'recall', 'mrr', 'recall_at_5', 'gold_coverage', 'source_f1',
                     'source_precision', 'source_recall', 'source_exact', 'unnecessary_retrieval', 'stopping_accuracy', 'premature_stop',
                     'over_retrieval', 'max_step_exhaustion', 'required_source_miss', 'coverage_text', 'coverage_graph', 'coverage_structured'), 'rate'),
    **dict.fromkeys(('input_tokens', 'output_tokens', 'total_tokens', 'context_tokens'), 'tokens'),
    'context_characters': 'count',
    **dict.fromkeys(('latency', 'cm_ms'), 'ms'),
    **dict.fromkeys(('llm_calls', 'retrieval_calls'), 'calls'),
}
MINUS = '−'


def kind_of(metric):
    return KIND.get(metric, 'number')


def _q(x, places):
    d = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return d.copy_abs() if d.is_zero() else d


def number(x, places=0, sign=False, sep=True):
    d = _q(x, places)
    s = format(d, (',' if sep else '') + '.%df' % places).replace('-', MINUS)
    return ('+' + s) if sign and d > 0 else s


def fmt(value, kind='number', sign=False):
    """value -> display string. kind: rate, pct, tokens, count, ms, seconds, calls, p, ratio, number, text."""
    if value is None:
        return '—'
    if kind == 'text':
        return str(value)
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if kind == 'rate':
        return number(value, 3, sign)
    if kind == 'pct':
        return number(100 * value, 0, sign) + ' %'
    if kind in ('tokens', 'count'):
        return number(value, 0, sign)
    if kind == 'ms':
        return number(value / 1000., 1, sign) + ' s'
    if kind == 'seconds':
        return number(value, 1, sign) + ' s'
    if kind == 'calls':
        return number(value, 2 if abs(value - round(value)) > 1e-9 else 0, sign)
    if kind == 'p':
        return '< 0.001' if value < 0.001 else number(value, 3)
    if kind == 'ratio':
        return number(value, 1)
    return number(value, 3 if abs(value) < 100 else 0, sign)


def metric(value, name, sign=False):
    return fmt(value, kind_of(name), sign)
