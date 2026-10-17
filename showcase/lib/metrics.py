"""Answer-set metrics, identical to research.evaluation.metrics.answer_metrics (checked by tests/test_showcase.py)."""


def answer_scores(predicted, gold):
    p, g = set(predicted), set(gold)
    hit = len(p & g)
    precision = hit / len(p) if p else float(not g)
    recall = hit / len(g) if g else float(not p)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.
    return {'hit': hit, 'precision': precision, 'recall': recall, 'f1': f1, 'exact_match': float(p == g)}
