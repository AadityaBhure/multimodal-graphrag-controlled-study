"""Answer-set metrics, identical to research.evaluation.metrics.answer_metrics (checked by tests/test_showcase.py)."""
import re


def answer_scores(predicted, gold):
    p, g = set(predicted), set(gold)
    hit = len(p & g)
    precision = hit / len(p) if p else float(not g)
    recall = hit / len(g) if g else float(not p)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.
    return {'hit': hit, 'precision': precision, 'recall': recall, 'f1': f1, 'exact_match': float(p == g)}


_ID_MARK = r'(?:paper:|stark:|"paper_id":|"node_id":|"source_id":|"target_id":)'


def gold_in_context(context, gold):
    """How many correct papers appear in the evidence the model received (as an evidence ID or graph node ID)."""
    ctx = context or ''
    return sum(1 for g in gold if re.search(_ID_MARK + '%d(?!\\d)' % int(g), ctx))


def evidence_text(items):
    """Searchable text of evidence items (dicts or objects with canonical_id, evidence_id, payload, content)."""
    get = (lambda x, k: x.get(k)) if items and isinstance(items[0], dict) else (lambda x, k: getattr(x, k, None))
    return '\n'.join('%s %s %s %s' % (get(x, 'canonical_id') or '', get(x, 'evidence_id') or '', get(x, 'payload') or '', get(x, 'content') or '')
                     for x in items or ())
