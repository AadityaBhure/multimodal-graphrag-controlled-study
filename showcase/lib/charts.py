"""Altair charts with fixed method colours, fixed ordering and formatted labels (deterministic rendering)."""
import altair as alt
import pandas as pd
import streamlit as st
from showcase.lib.fmt import metric as fmt_metric, fmt, kind_of
from showcase.lib.ui import method_color, SOURCE_COLOR, ink


def _show(chart):
    st.altair_chart(chart.configure_view(strokeWidth=0).configure_axis(labelFontSize=12, titleFontSize=12.5, grid=True, gridColor='#eef2f7'),
                    width='stretch')


def _height(rows):
    return 130 + 34 * rows


def _unit(metric):
    """Charts show times in seconds (the data stores milliseconds)."""
    return (1 / 1000., ' (s)') if kind_of(metric) == 'ms' else (1., '')


def method_bars(desc, methods, metric, title, ci=None, pareto=()):
    f, unit = _unit(metric)
    title = title + unit
    rows = []
    for m in methods:
        v = desc[m].get(metric)
        if v is None:
            continue
        lo, hi = (ci or {}).get(m, {}).get(metric) or (None, None)
        lo, hi = (lo * f if lo is not None else None), (hi * f if hi is not None else None)
        rows.append({'method': m, 'value': v * f, 'label': fmt_metric(v, metric), 'lo': lo, 'hi': hi, 'at': max(v * f, hi) if hi is not None else v * f,
                     'pareto': '★' if m in pareto else ''})
    df = pd.DataFrame(rows)
    if df.empty:
        st.info('No values for this metric.')
        return
    y = alt.Y('method:N', sort=methods, title=None, axis=alt.Axis(labelLimit=220))
    base = alt.Chart(df)
    bars = base.mark_bar(cornerRadiusEnd=3, size=22).encode(
        y=y, x=alt.X('value:Q', title=title), color=alt.Color('method:N', scale=alt.Scale(domain=methods, range=[method_color(m) for m in methods]), legend=None),
        tooltip=[alt.Tooltip('method:N', title='Method'), alt.Tooltip('label:N', title=title)])
    text = base.mark_text(align='left', dx=6, fontSize=12, color=ink()).encode(y=y, x='at:Q', text='label:N')
    layers = [bars, text]
    if df['lo'].notna().any():
        layers.append(base.mark_rule(color=ink(), strokeWidth=1.4).encode(y=y, x='lo:Q', x2='hi:Q'))
    _show(alt.layer(*layers).properties(height=_height(len(df))))


def quality_cost(desc, methods, x, y, x_title, y_title, pareto=()):
    (fx, _), (fy, _) = _unit(x), _unit(y)
    df = pd.DataFrame([{'method': m, 'x': desc[m][x] * fx, 'y': desc[m][y] * fy, 'status': 'Pareto-optimal' if m in pareto else 'dominated',
                        'xs': fmt_metric(desc[m][x], x), 'ys': fmt_metric(desc[m][y], y)} for m in methods if desc[m].get(x) is not None and desc[m].get(y) is not None])
    enc = dict(x=alt.X('x:Q', title=x_title, scale=alt.Scale(zero=False, padding=30)), y=alt.Y('y:Q', title=y_title, scale=alt.Scale(zero=False, padding=24)))
    color = alt.Color('method:N', scale=alt.Scale(domain=methods, range=[method_color(m) for m in methods]), legend=None)
    pts = alt.Chart(df).mark_point(size=230, filled=True, opacity=.95).encode(
        **enc, color=color, shape=alt.Shape('status:N', scale=alt.Scale(domain=['Pareto-optimal', 'dominated'], range=['circle', 'triangle-down']),
                                            legend=alt.Legend(title=None, orient='bottom')),
        tooltip=[alt.Tooltip('method:N', title='Method'), alt.Tooltip('xs:N', title=x_title), alt.Tooltip('ys:N', title=y_title), alt.Tooltip('status:N', title='')])
    ring = alt.Chart(df[df.status == 'Pareto-optimal']).mark_point(size=520, filled=False, strokeWidth=2, color='#b45309').encode(**enc)
    lab = alt.Chart(df).mark_text(align='left', dx=13, dy=-11, fontSize=12.5, fontWeight='bold').encode(**enc, text='method:N', color=color)
    _show(alt.layer(ring, pts, lab).properties(height=340))


def grouped(strata, dim_values, methods, metric, title, value_labels=None):
    rows = []
    for v in dim_values:
        for m in methods:
            x = (strata.get(v) or {}).get(m, {}).get(metric)
            if x is not None:
                rows.append({'group': (value_labels or {}).get(v, v), 'method': m, 'value': x, 'label': fmt_metric(x, metric)})
    df = pd.DataFrame(rows)
    if df.empty:
        st.info('No values for this breakdown.')
        return
    order = [(value_labels or {}).get(v, v) for v in dim_values]
    ch = alt.Chart(df).mark_bar(cornerRadiusEnd=2).encode(
        x=alt.X('group:N', sort=order, title=None, axis=alt.Axis(labelAngle=0)), xOffset=alt.XOffset('method:N', sort=methods),
        y=alt.Y('value:Q', title=title), color=alt.Color('method:N', scale=alt.Scale(domain=methods, range=[method_color(m) for m in methods]),
                                                       legend=alt.Legend(title=None, orient='bottom')),
        tooltip=[alt.Tooltip('group:N', title='Group'), alt.Tooltip('method:N', title='Method'), alt.Tooltip('label:N', title=title)])
    _show(ch.properties(height=300))


def stacked_counts(counts, methods, title, labels=None):
    rows = [{'method': m, 'what': (labels or {}).get(k, k), 'n': n} for m in methods for k, n in sorted((counts.get(m) or {}).items())]
    df = pd.DataFrame(rows)
    if df.empty:
        return
    ch = alt.Chart(df).mark_bar().encode(
        y=alt.Y('method:N', sort=methods, title=None), x=alt.X('n:Q', title=title, stack='zero'),
        color=alt.Color('what:N', legend=alt.Legend(title=None, orient='bottom', columns=2, labelLimit=360)),
        tooltip=[alt.Tooltip('method:N', title='Method'), alt.Tooltip('what:N', title=''), alt.Tooltip('n:Q', title='Questions')])
    _show(ch.properties(height=_height(len(methods)) + 40))


def family_bars(sums, metric, short):
    df = pd.DataFrame([{'family': short(f), 'value': v, 'sign': 'A better' if v > 0 else ('B better' if v < 0 else 'no difference'),
                        'label': fmt_metric(v, metric, sign=True)} for f, v in sums.items()])
    ch = alt.Chart(df).mark_bar(cornerRadiusEnd=2).encode(
        x=alt.X('family:N', sort=None, title='Question family', axis=alt.Axis(labelAngle=-35)), y=alt.Y('value:Q', title='Summed difference A − B'),
        color=alt.Color('sign:N', scale=alt.Scale(domain=['A better', 'B better', 'no difference'], range=['#2563eb', '#dc2626', '#94a3b8']),
                        legend=alt.Legend(title=None, orient='bottom')),
        tooltip=[alt.Tooltip('family:N', title='Family'), alt.Tooltip('label:N', title='Difference')])
    _show(ch.properties(height=280))


def signflip_hist(totals, observed, metric):
    df = pd.DataFrame({'total': totals})
    df['extreme'] = (df['total'].abs() >= abs(observed) - 1e-12).map({True: 'at least as extreme as observed', False: 'less extreme'})
    bars = alt.Chart(df).mark_bar(binSpacing=0).encode(
        x=alt.X('total:Q', bin=alt.Bin(maxbins=60), title='Total difference under a random sign flip of each family',
                axis=alt.Axis(tickCount=9, labelOverlap='greedy', format='~r')),
        y=alt.Y('count():Q', title='Number of sign patterns'),
        color=alt.Color('extreme:N', scale=alt.Scale(domain=['at least as extreme as observed', 'less extreme'], range=['#dc2626', '#cbd5e1']),
                        legend=alt.Legend(title=None, orient='bottom')))
    rule = alt.Chart(pd.DataFrame({'x': [observed]})).mark_rule(color=ink(), strokeWidth=2, strokeDash=[5, 3]).encode(x='x:Q')
    _show(alt.layer(bars, rule).properties(height=280))


def source_overlap(counts):
    """Single, pairwise and triple condition counts for the example question (log scale)."""
    order = [('text', 'Text condition'), ('graph', 'Graph condition'), ('structured', 'Structured condition'), ('text+graph', 'Text + Graph'),
             ('text+structured', 'Text + Structured'), ('graph+structured', 'Graph + Structured'), ('all', 'All three = the answer')]
    df = pd.DataFrame([{'set': label, 'n': counts[k], 'label': fmt(counts[k], 'count'), 'kind': 'answer' if k == 'all' else ('pair' if '+' in k else 'single')}
                       for k, label in order])
    y = alt.Y('set:N', sort=[l for _, l in order], title=None, axis=alt.Axis(labelLimit=260))
    base = alt.Chart(df)
    bars = base.mark_bar(cornerRadiusEnd=3, size=20).encode(
        y=y, x=alt.X('n:Q', scale=alt.Scale(type='symlog'), axis=alt.Axis(values=[0, 1, 10, 100, 1000, 10000, 100000], format=',d', grid=False),
                     title='Papers satisfying the condition(s) — logarithmic scale'),
        color=alt.Color('kind:N', scale=alt.Scale(domain=['single', 'pair', 'answer'], range=['#94a3b8', '#475569', '#16a34a']), legend=None),
        tooltip=[alt.Tooltip('set:N', title=''), alt.Tooltip('label:N', title='Papers')])
    text = base.mark_text(align='left', dx=6, fontSize=12.5, fontWeight='bold', color=ink()).encode(y=y, x='n:Q', text='label:N')
    _show(alt.layer(bars, text).properties(height=_height(len(df))))


def relation_bars(relations):
    labels = {'WRITES': 'author writes paper', 'HAS_TOPIC': 'paper has field of study', 'CITES': 'paper cites paper', 'AFFILIATED_WITH': 'author affiliated with institution'}
    df = pd.DataFrame([{'rel': labels[k], 'n': v, 'label': fmt(v, 'count')} for k, v in sorted(relations.items(), key=lambda kv: -kv[1])])
    y = alt.Y('rel:N', sort=None, title=None)
    base = alt.Chart(df)
    ch = alt.layer(base.mark_bar(color=SOURCE_COLOR['graph'], size=20, cornerRadiusEnd=3).encode(y=y, x=alt.X('n:Q', title='Relations')),
                   base.mark_text(align='left', dx=6, fontSize=12, color=ink()).encode(y=y, x='n:Q', text='label:N'))
    _show(ch.properties(height=_height(len(df))))
