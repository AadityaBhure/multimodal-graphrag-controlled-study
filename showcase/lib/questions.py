"""Question helpers: readable labels and per-source highlighting of the generated benchmark wording."""
import re
from showcase.lib.ui import e

STRESS_LABEL = {'normal': 'normal', 'noisy': 'noisy', 'conflict': 'conflict', 'unanswerable': 'unanswerable'}
MODALITY_LABEL = {'T': 'Text', 'G': 'Graph', 'S': 'Structured', 'TG': 'Text + Graph', 'TS': 'Text + Structured', 'GS': 'Graph + Structured',
                  'TGS': 'Text + Graph + Structured'}
_CLASS = {'text': 't', 'graph': 'g', 'structured': 'st'}


def clause_source(clause):
    c = clause.lower()
    if 'abstract' in c or 'title' in c:
        return 'text'
    if 'recorded' in c:
        return 'structured'
    if any(w in c for w in ('author', 'affiliat', 'cite', 'field of study', 'topic', 'written')):
        return 'graph'
    return None


def clauses(question):
    """[(text, source or None)] for 'Which papers satisfy these requirements: A; and B, and C?' style questions."""
    head, sep, body = question.partition(': ')
    if not sep:
        return [(question, None)]
    end = '?' if body.endswith('?') else ''
    parts = re.split(r'(; and |, and )', body[:-1] if end else body)
    out = [(head + sep, None)]
    for p in parts:
        out.append((p, None) if p in ('; and ', ', and ') else (p, clause_source(p)))
    if end:
        out.append((end, None))
    return out


def highlighted(question):
    """HTML with each condition coloured by the source that can check it."""
    return ''.join('<span class="%s">%s</span>' % (_CLASS[s], e(t)) if s else e(t) for t, s in clauses(question))


def short_family(family_id):
    return family_id.split(':')[-1][:6]


def label(qid, q, width=88):
    text = q['question'].split(': ', 1)[-1]
    text = text if len(text) <= width else text[:width - 1] + '…'
    return '%s · %s · %s' % (q['modality'], STRESS_LABEL.get(q['stress'], q['stress']), text)
