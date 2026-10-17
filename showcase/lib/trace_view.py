"""Timeline rendering of a retrieval-control trace (steps from showcase.lib.traces.ar_steps)."""
import pandas as pd
import streamlit as st
from showcase.lib.fmt import fmt
from showcase.lib.traces import ROUTE_LABEL, STOP_LABEL, STATUS_LABEL, reason_label
from showcase.lib.ui import e, html, source_chips, SOURCE_LABEL

ICON = {'plan': '🧭', 'route': '🧭', 'classify': '🧭', 'search': '🔎', 'decide': '🤔', 'evaluate': '📏', 'agent': '🤖', 'draft': '✍️',
        'validate': '⚖️', 'comment': '💬', 'stop': '🏁'}
ROLE = {'final': 'answer', 'ar01_controller': 'controller', 'agent': 'agent', 'validator': 'validator', 'commentor': 'commentor',
        'repair': 'format repair', 'selector': 'selector', 'reason': 'per-source reasoning', 'fusion': 'fusion', 'keywords': 'keywords'}


def _q(text, n=220):
    t = str(text or '')
    return e(t if len(t) <= n else t[:n - 1] + '…')


def step_html(s):
    k = s['kind']
    if k == 'plan':
        return '<span class="h">Plan:</span> query every source in a fixed order %s' % source_chips(s.get('sources'))
    if k == 'route':
        hits = {src: v for src, v in (s.get('hits') or {}).items() if v}
        cues = '; '.join('%s cues: %s' % (SOURCE_LABEL.get(src, src), ', '.join('“%s”' % e(c) for c in v[:6])) for src, v in sorted(hits.items()))
        return ('<span class="h">Rules choose</span> %s' % source_chips(s.get('sources')) + ('<div class="m">%s</div>' % cues if cues else '')
                + ('<div class="m">no cue found, defaulted to text</div>' if s.get('fallback') else ''))
    if k == 'classify':
        probs = s.get('probs') or {}
        p = ', '.join('%s %s' % (ROUTE_LABEL.get(c, c), fmt(v, 'rate')) for c, v in sorted(probs.items()))
        return '<span class="h">Classifier predicts:</span> %s<div class="m">probabilities — %s</div>' % (e(ROUTE_LABEL.get(s.get('label'), s.get('label'))), e(p))
    if k == 'search':
        status = s.get('status')
        note = '' if status == 'ok' else '<div class="m">⚠ %s</div>' % e(STATUS_LABEL.get(status, status))
        return ('<span class="h">Search</span> %s <span class="m">%s · %s found, %s new · %s</span><div><code>%s</code></div>%s'
                % (source_chips([s['source']]), e(reason_label(s.get('reason')) or ''), s.get('found'), s.get('new'), e(fmt(s.get('ms'), 'ms')), _q(s.get('query')), note))
    if k == 'decide':
        if s.get('next'):
            return '<span class="h">Controller: not enough yet</span> — next search:<div><code>%s</code></div><div class="m">%s</div>' % (_q(s['next']), _q(s.get('reason'), 260))
        return '<span class="h">Controller: enough evidence</span><div class="m">%s</div>' % _q(s.get('reason'), 260)
    if k == 'evaluate':
        st_ = s.get('state')
        col = {'GOOD': '#15803d', 'AMBIGUOUS': '#b45309', 'BAD': '#b91c1c'}.get(st_, '#334155')
        what = {'GOOD': 'stop here', 'AMBIGUOUS': 'add the next source', 'BAD': 'add every remaining source'}.get(st_, '')
        return ('<span class="h">Evidence rated <span style="color:%s">%s</span></span> → %s<div class="m">best calibrated relevance %s (BAD below %s, GOOD from %s)</div>'
                % (col, e(st_), e(what), e(fmt(s.get('best'), 'rate')), e(fmt(s.get('lower'), 'rate')), e(fmt(s.get('upper'), 'rate'))))
    if k == 'agent':
        if s.get('source') in SOURCE_LABEL:
            return '<span class="h">Agent (iteration %s) chooses</span> %s <span class="m">%s</span><div><code>%s</code></div>' % (
                e(s.get('iteration')), source_chips([s['source']]), e(reason_label(s.get('reason')) or ''), _q(s.get('query')))
        return '<span class="h">Agent (iteration %s) decides to stop</span> <span class="m">%s</span>' % (e(s.get('iteration')), e(s.get('stop') or ''))
    if k == 'draft':
        n = len(s.get('answer_ids') or [])
        return '<span class="h">Draft answer:</span> %s' % ('no paper' if not n else '%d paper%s' % (n, '' if n == 1 else 's')) + (
            ' <span class="m">(could not be parsed)</span>' if s.get('parse_error') else '')
    if k == 'validate':
        if s.get('accept'):
            return '<span class="h ok">Validator accepts the draft</span>'
        return '<span class="h no">Validator rejects the draft</span> <span class="m">%s</span>' % e((s.get('error') or '').replace('_', ' '))
    if k == 'comment':
        return '<span class="h">Commentor feedback:</span> <span class="m">%s</span>' % _q(s.get('feedback'), 320)
    if k == 'stop':
        return '<span class="h">Stop:</span> %s' % e(STOP_LABEL.get(s.get('reason'), (s.get('reason') or '').replace('_', ' ')))
    return e(k)


def timeline(steps):
    html('<div class="tl">%s</div>' % ''.join('<div class="e" data-i="%s">%s</div>' % (ICON.get(s['kind'], '•'), step_html(s)) for s in steps))


def llm_table(llm, extra=()):
    rows = [{'Model call': ROLE.get(c['role'], c['role']), 'Step': c.get('step'), 'Input tokens': fmt(c.get('input_tokens'), 'tokens'),
             'Output tokens': fmt(c.get('output_tokens'), 'tokens'), 'Time': fmt(c.get('ms'), 'ms')} for c in list(llm) + list(extra)]
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
