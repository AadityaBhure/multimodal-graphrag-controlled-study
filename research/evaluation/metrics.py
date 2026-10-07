"""Pure metrics; unavailable measurements are None."""
from math import log2

AGENT_METRICS = ('source_selection_accuracy', 'unnecessary_retrieval_rate', 'stopping_accuracy',
                 'fusion_coverage', 'entity_alignment_correctness', 'conflict_handling')


def answer_metrics(predicted, gold):
    names = ('set_accuracy', 'exact_match', 'precision', 'recall', 'f1', 'answerability_correctness')
    if predicted is None:
        return dict.fromkeys(names)
    p, g = set(predicted), set(gold)
    hit = len(p & g)
    precision = hit / len(p) if p else float(not g)
    recall = hit / len(g) if g else float(not p)
    return dict(zip(names, (float(p == g), float(p == g), precision, recall,
                           2 * precision * recall / (precision + recall) if precision + recall else 0.,
                           float(bool(p) == bool(g)))))


def coverage(observed, required):
    if observed is None or required is None or not set(required):
        return None
    return len(set(observed) & set(required)) / len(set(required))


def retrieval_metrics(ranking, gold, ks):
    if any(isinstance(k, bool) or not isinstance(k, int) or k < 1 for k in ks):
        raise ValueError('K must be a positive integer')
    keys = ['mrr', 'gold_coverage'] + [f'{name}@{k}' for k in ks for name in ('recall', 'precision', 'ndcg')]
    if ranking is None or not gold:
        return dict.fromkeys(keys)
    ranked = list(dict.fromkeys(ranking))
    relevant = set(gold)
    result = {'mrr': next((1 / i for i, x in enumerate(ranked, 1) if x in relevant), 0.),
              'gold_coverage': coverage(ranked, relevant)}
    for k in ks:
        hits = sum(x in relevant for x in ranked[:k])
        dcg = sum(1 / log2(i + 2) for i, x in enumerate(ranked[:k]) if x in relevant)
        ideal = sum(1 / log2(i + 2) for i in range(min(k, len(relevant))))
        result.update({f'recall@{k}': hits / len(relevant), f'precision@{k}': hits / k,
                       f'ndcg@{k}': dcg / ideal})
    return result


def context_metrics(context, retrieved_ids, retained_ids, *, tokens=None, tokenizer=None, baseline_characters=None):
    if tokens is not None and (not tokenizer or tokens < 0):
        raise ValueError('Nonnegative measured tokens require an identified tokenizer')
    if baseline_characters is not None and baseline_characters <= 0:
        raise ValueError('A context baseline must be positive')
    return {'context_characters': len(context) if context is not None else None,
            'context_tokens': tokens if context is not None else None,
            'evidence_retained': coverage(retained_ids, retrieved_ids),
            'redundancy': (1 - len(set(retained_ids)) / len(retained_ids)) if retained_ids else (0. if retained_ids in ((), []) else None),
            'context_reduction': (1 - len(context) / baseline_characters) if context is not None and baseline_characters is not None else None}
