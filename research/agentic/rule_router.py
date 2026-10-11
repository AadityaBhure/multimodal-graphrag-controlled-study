"""Shared deterministic rule router (Phase 9 addendum §1). No LLM, no learning, no gold.

Used as AR-B1 (every routed source, once, in fixed order) and as the *base source router*
inside AR-01 (B, C), AR-02 (initial source, AMBIGUOUS order) and AR-03 (schema-repair fallback).
The cue table is frozen before any Phase 9 result exists and must not be tuned.
"""
import re
import unicodedata

SOURCE_ORDER = ('text', 'graph', 'structured')
RULE_VERSION = 'phase9-rule-router-v1'

TEXT_CUES = ('abstract', 'title', 'text', 'content', 'phrase', 'wording', 'mention', 'mentions', 'mentioned',
             'contain', 'contains', 'containing')
GRAPH_CUES = ('author', 'authors', 'authored', 'written by', 'writes', 'affiliat', 'institution', 'university',
              'cites', 'cited by', 'references', 'referenced by', 'topic', 'field of study')
STRUCTURED_CUES = ('year', 'publication year', 'date', 'rank', 'paper rank', 'citation count', 'journal', 'conference',
                   'venue', 'document type', 'doctype', 'before', 'after', 'between', 'at least', 'at most',
                   'more than', 'less than', 'greater than', 'fewer than', '>=', '<=', '>', '<')
# "citation count", numeric citation comparisons and "at least N citations" are Structured, not Graph, cues.
NUMERIC_CITATIONS = re.compile(r'\b(?:at least|at most|more than|less than|fewer than|greater than)\s+\d+\s+citations?\b|\b\d+\s+citations?\b|\bcitations?\s*(?:>=|<=|>|<|=)\s*\d+')


def normalize(question):
    return ' '.join(unicodedata.normalize('NFKC', question).lower().split())


def route(question):
    """Return the matched sources (fixed priority Text->Graph->Structured) plus the audit trail."""
    q = normalize(question)
    hits = {'text': [c for c in TEXT_CUES if c in q],
            'graph': [c for c in GRAPH_CUES if c in q],
            'structured': [c for c in STRUCTURED_CUES if c in q]}
    # "citation count", numeric citation comparisons and "at least N citations" are Structured cues.
    # None of the Graph cues is a substring of those phrases, so no Graph hit is produced by them.
    if NUMERIC_CITATIONS.search(q):
        hits['structured'] = sorted(set(hits['structured']) | {'numeric_citations'})
    matched = tuple(s for s in SOURCE_ORDER if hits[s])
    fallback = not matched
    if fallback:
        matched = ('text',)
    return {'version': RULE_VERSION, 'normalized_query': q, 'sources': matched, 'rule_hits': hits,
            'fallback_default_text': fallback, 'reason_code': 'default_text' if fallback else '+'.join(matched)}


def first_source(question):
    return route(question)['sources'][0]


def next_unqueried(question, queried):
    """Highest-priority router source not yet queried; else first unqueried in T->G->S; else None."""
    for s in route(question)['sources']:
        if s not in queried:
            return s
    for s in SOURCE_ORDER:
        if s not in queried:
            return s
    return None
