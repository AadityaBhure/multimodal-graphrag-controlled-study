"""On-screen text (content/content.yaml) and the placeholder binding from text to bundle values.

A finding is written once with named placeholders, e.g. "F1 = {F1}", and a `values` map binds each name to a bundle key:

    RQx.methods.<method>.<metric>                 mean of a metric for one method
    RQx.test.<metric>.<A>~<B>.<delta|p|p_holm>    paired test of A against B (B~A is the same test with the sign flipped)
    RQx.test.<metric>.max_p_holm                  largest adjusted p over all pairs tested on that metric
    RQx.ratio.<metric>.<A>/<B>                    ratio of two method means
    RQx.max.<metric>                              largest method mean
    RQ2.support.<CLASS>                           number of RQ2 bundles in a supportability class
    RQ4.selection.<key>                           a component chosen by the frozen RQ4 rule
    RQx.overall.winner | RQx.overall.total.<M>    overall winner of a part / a method's rank total
    RQx.strata.<dim>.<value>.<method>.<metric>    mean within one question group (e.g. modality.G)
    RQx.n.<dim>.<value>                           number of questions in that group

A binding may end in |pct, |ratio, |tokens, |rate, |p or |text to override the default format of its metric.
"""
from pathlib import Path
import re
import yaml
from showcase.lib.fmt import fmt, kind_of

CONTENT = Path(__file__).resolve().parents[1] / 'content/content.yaml'
PLACEHOLDER = re.compile(r'\{([A-Z][A-Z0-9_]*)\}')


def load_content(path=CONTENT):
    return yaml.safe_load(Path(path).read_text(encoding='utf-8'))


class BindingError(KeyError):
    pass


def _test(results, rq, metric, a, b):
    for t in results[rq]['tests'].get(metric, []):
        if (t['a'], t['b']) == (a, b):
            return t, 1.
        if (t['a'], t['b']) == (b, a):
            return t, -1.
    raise BindingError('no paired test %s %s vs %s' % (metric, a, b))


def resolve(key, results):
    """Bundle key -> (value, format kind)."""
    key, _, override = key.partition('|')
    parts = key.split('.')
    rq, what = parts[0], parts[1]
    try:
        r = results[rq]
        if what == 'methods':
            method, metric = parts[2], parts[3]
            value, kind = r['descriptive'][method][metric], kind_of(metric)
        elif what == 'test':
            metric = parts[2]
            if parts[3] == 'max_p_holm':
                value, kind = max(t['p_holm'] for t in r['tests'][metric]), 'p'
            else:
                a, b = parts[3].split('~'); field = parts[4]
                t, s = _test(results, rq, metric, a, b)
                if field == 'delta':
                    value, kind = s * t['delta'] + 0., kind_of(metric)
                elif field in ('p', 'p_holm'):
                    value, kind = t[field], 'p'
                else:
                    raise BindingError(key)
        elif what == 'ratio':
            metric = parts[2]; a, b = '.'.join(parts[3:]).split('/')
            value, kind = r['descriptive'][a][metric] / r['descriptive'][b][metric], 'ratio'
        elif what == 'max':
            metric = parts[2]
            value, kind = max(d[metric] for d in r['descriptive'].values() if d.get(metric) is not None), kind_of(metric)
        elif what == 'support':
            value, kind = r['supportability']['counts'][parts[2]], 'count'
        elif what == 'selection':
            value, kind = r['selection'][parts[2]], 'text'
        elif what == 'overall':
            if parts[2] == 'winner':
                value, kind = r['overall']['winner'], 'text'
            elif parts[2] == 'total':
                value, kind = r['overall']['total'][parts[3]], 'rank'
            else:
                raise BindingError(key)
        elif what == 'strata':
            dim, val, method, metric = parts[2], parts[3], parts[4], parts[5]
            value, kind = r['strata'][dim][val][method][metric], kind_of(metric)
        elif what == 'n':
            value, kind = r['strata_n']['%s:%s' % (parts[2], parts[3])], 'count'
        else:
            raise BindingError(key)
    except (KeyError, IndexError, ValueError) as exc:
        raise BindingError('cannot resolve %r: %s' % (key, exc)) from None
    return value, (override or kind)


def render(text, values, results):
    """Replace every {NAME} in text with the formatted value of its binding. Unbound names raise BindingError."""
    def sub(m):
        name = m.group(1)
        if name not in (values or {}):
            raise BindingError('placeholder {%s} has no binding' % name)
        v, k = resolve(values[name], results)
        return fmt(v, k)
    return PLACEHOLDER.sub(sub, text)


def findings(section, results):
    """Rendered finding texts of one content section (list of {text, values})."""
    return [render(f['text'], f.get('values') or {}, results) for f in section.get('findings', [])]


def all_bindings(content):
    """Every (location, text, values) pair in the content file, for validation."""
    out = []
    def walk(node, where):
        if isinstance(node, dict):
            if 'text' in node and isinstance(node.get('text'), str) and 'values' in node:
                out.append((where, node['text'], node.get('values') or {}))
            for k, v in node.items():
                walk(v, '%s.%s' % (where, k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, '%s[%d]' % (where, i))
    walk(content, 'content')
    return out
