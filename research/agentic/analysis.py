"""Phase 9 analysis: source/stopping/efficiency metrics (definitions frozen in PHASE9_SPEC_CONSISTENCY_AUDIT.md),
family-clustered paired statistics, Holm correction, Pareto analysis and failure taxonomy.

Operates on plain dict run records (Phase 5 RunRecord JSON). The oracle source set comes from the VERIFIED modality
label and is used here only, never by a policy.
"""
import itertools
import json
import math
import random
from research.agentic.rule_router import SOURCE_ORDER

ORACLE = {'T': {'text'}, 'G': {'graph'}, 'S': {'structured'}, 'TG': {'text', 'graph'}, 'TS': {'text', 'structured'},
          'GS': {'graph', 'structured'}, 'TGS': {'text', 'graph', 'structured'}}
BUDGET_STOPS = ('max_multi_steps', 'max_iterations_rejected', 'loop_guard_insufficient_evidence', 'max_correction_rounds', 'sources_exhausted',
                'all_sources_retrieved')
METRICS_HIGHER = ('answer_f1', 'answer_em', 'source_f1', 'source_recall', 'source_precision', 'source_exact', 'stopping_accuracy', 'recall_at_5')
METRICS_LOWER = ('retrieval_calls', 'llm_calls', 'unnecessary_retrieval', 'intrinsic_ms', 'total_tokens', 'required_source_miss')


def family(query_id):
    return query_id.rsplit(':', 1)[0]


def per_record(rec):
    """Metrics for one run record (dict)."""
    d = json.loads(rec['output']['diagnostics']) if rec.get('output') and rec['output'].get('diagnostics') else {}
    R = ORACLE.get(rec['labels']['modality'])
    S = list(d.get('sources_called', []))
    calls = d.get('tool_calls', [])
    out = {'query_id': rec['query_id'], 'family': family(rec['query_id']), 'method': rec['system_id'], 'stress': rec['stress'][0] if rec['stress'] else 'normal',
           'modality': rec['labels']['modality'], 'status': d.get('status'), 'stop_reason': d.get('stop_reason'), 'error': bool(rec['errors'])}
    m = rec['metrics']
    out.update(answer_f1=m.get('f1'), answer_em=m.get('exact_match'), recall_at_5=m.get('recall@5'), retrieval_calls=len(calls), tool_calls=len(calls),
               llm_calls=m.get('llm_calls'), input_tokens=m.get('input_tokens'), output_tokens=m.get('output_tokens'))
    out['total_tokens'] = (m['input_tokens'] + m['output_tokens']) if m.get('input_tokens') is not None and m.get('output_tokens') is not None else None
    wait = d.get('timings_ms', {}).get('provider_wait', 0.) or 0.
    out['intrinsic_ms'] = rec['total_latency_ms'] - wait
    out['provider_wait_ms'] = wait
    out['sources_called'] = S
    if R is None:
        out.update(source_f1=None, source_recall=None, source_precision=None, source_exact=None, unnecessary_retrieval=None, required_source_miss=None,
                   stopping_accuracy=None, premature_stop=None, over_retrieval=None, max_step_exhaustion=None)
        return out
    Sset = set(S)
    inter = len(Sset & R)
    out['source_precision'] = inter / len(Sset) if Sset else 0.
    out['source_recall'] = inter / len(R)
    out['source_f1'] = 2 * inter / (len(Sset) + len(R)) if (Sset or R) else None
    out['source_exact'] = float(Sset == R)
    out['unnecessary_retrieval'] = len(Sset - R) / len(Sset) if Sset else 0.
    out['required_source_miss'] = len(R - Sset) / len(R)
    covered, acc = None, set()
    for i, c in enumerate(calls, 1):
        acc.add(c['source'])
        if R <= acc:
            covered = i
            break
    out['covered_step'] = covered
    out['stopping_accuracy'] = float(covered is not None and len(calls) == covered)
    never = covered is None
    out['premature_stop'] = float(never and d.get('stop_reason') not in BUDGET_STOPS and d.get('stop_reason') is not None)
    out['max_step_exhaustion'] = float(never and d.get('stop_reason') in BUDGET_STOPS)
    out['over_retrieval'] = float(covered is not None and len(calls) > covered)
    return out


def failure_labels(rec, gold):
    """Multi-label failure taxonomy for one record; separates controller failures from retriever weakness."""
    d = json.loads(rec['output']['diagnostics']) if rec.get('output') and rec['output'].get('diagnostics') else {}
    R = ORACLE.get(rec['labels']['modality'])
    S = d.get('sources_called', [])
    calls = d.get('tool_calls', [])
    labels = []
    f1 = rec['metrics'].get('f1')
    wrong = f1 is not None and f1 < 1.0
    if R is not None:
        if calls and calls[0]['source'] not in R:
            labels.append('wrong_initial_routing')
        if not R <= set(S):
            labels.append('required_source_never_selected')
        if set(S) - R:
            labels.append('unnecessary_source_selected')
        pm = per_record(rec)
        if pm.get('premature_stop'):
            labels.append('premature_stop')
        if pm.get('over_retrieval'):
            labels.append('excessive_retrieval')
        if R <= set(S) and wrong:
            labels.append('retriever_failure_despite_correct_routing')
    for fb in d.get('fallbacks', []):
        if fb['type'] == 'subquery_generation_failed':
            labels.append('subquery_generation_failure')
        if fb['type'] in ('agent_schema_repair_failed',):
            labels.append('agent_schema_failure')
    if d.get('stop_reason') == 'loop_guard_insufficient_evidence':
        labels.append('loop_or_repeated_action')
    if d.get('status') == 'insufficient_evidence':
        labels.append('insufficient_evidence')
    for e in d.get('events', []):
        if e['kind'] == 'structured_error':
            labels.append('structured_intent_failure')
        if e['kind'] == 'evaluation' and gold:
            papers = {int(i.split(':')[2]) for i in e['evidence_ids']}
            cov = len(set(gold) & papers) / len(set(gold))
            truth = 'GOOD' if cov == 1.0 else 'BAD' if cov == 0.0 else 'AMBIGUOUS'
            if e['state'] != truth and not e['evaluator_failed']:
                labels.append('evaluator_misclassification')
                if (e['state'], truth) in (('GOOD', 'BAD'), ('BAD', 'GOOD')):
                    labels.append('calibration_or_threshold_failure')
    for t in calls:
        if t['source'] == 'structured' and not t['detail'].get('plan') and (R is None or 'structured' in R):
            labels.append('structured_intent_failure')
            break
    cand = [e for e in d.get('events', []) if e['kind'] == 'candidate']
    verdicts = [e for e in d.get('events', []) if e['kind'] == 'validator']
    for c, v in zip(cand, verdicts):
        correct = c['answer_ids'] is not None and set(c['answer_ids']) == set(gold)
        if v['verdict']['accept'] and not correct:
            labels.append('validator_false_accept')
        if not v['verdict']['accept'] and correct:
            labels.append('validator_false_reject')
    if rec['errors']:
        labels.append('final_generator_or_parsing_failure')
    return sorted(set(labels))


# ------------------------------------------------------------------ statistics
def cluster_mean(values_by_query):
    groups = {}
    for q, v in values_by_query.items():
        if v is not None:
            groups.setdefault(family(q), []).append(v)
    return groups


def bootstrap_ci(deltas, reps=10000, seed=42):
    groups = cluster_mean(deltas)
    names = sorted(groups)
    if len(names) < 2:
        return None
    rng = random.Random(seed)
    sums = [sum(groups[g]) for g in names]
    counts = [len(groups[g]) for g in names]
    samples = []
    for _ in range(reps):
        picks = [rng.randrange(len(names)) for _ in names]
        n = sum(counts[i] for i in picks)
        samples.append(sum(sums[i] for i in picks) / n)
    samples.sort()
    return [samples[int(.025 * reps)], samples[int(.975 * reps) - 1]]


def sign_flip_p(deltas):
    groups = cluster_mean(deltas)
    names = sorted(groups)
    if len(names) < 2 or len(names) > 20:
        return None
    sums = [sum(groups[g]) for g in names]
    observed = abs(sum(sums))
    extreme = 0
    for signs in itertools.product((-1, 1), repeat=len(names)):
        extreme += abs(sum(s * x for s, x in zip(signs, sums))) >= observed - 1e-12
    return extreme / 2 ** len(names)


def holm(pvalues):
    """pvalues: {key: p or None}. Returns Holm-adjusted p (monotone), None preserved."""
    valid = sorted(((k, p) for k, p in pvalues.items() if p is not None), key=lambda kv: kv[1])
    adjusted, running = {}, 0.
    for i, (k, p) in enumerate(valid):
        running = max(running, min(1., (len(valid) - i) * p))
        adjusted[k] = running
    return {k: adjusted.get(k) for k in pvalues}


def paired(records_a, records_b, metric):
    qa = {r['query_id']: r.get(metric) for r in records_a}
    qb = {r['query_id']: r.get(metric) for r in records_b}
    deltas = {q: qa[q] - qb[q] for q in qa.keys() & qb.keys() if qa[q] is not None and qb[q] is not None}
    if not deltas:
        return {'n': 0, 'mean_delta': None, 'ci95_family_bootstrap': None, 'p_sign_flip': None, 'cohens_dz_families': None}
    groups = cluster_mean(deltas)
    fam_means = [sum(v) / len(v) for v in groups.values()]
    sd = (sum((x - sum(fam_means) / len(fam_means)) ** 2 for x in fam_means) / (len(fam_means) - 1)) ** .5 if len(fam_means) > 1 else None
    return {'n': len(deltas), 'n_families': len(groups), 'mean_delta': sum(deltas.values()) / len(deltas), 'ci95_family_bootstrap': bootstrap_ci(deltas),
            'p_sign_flip': sign_flip_p(deltas), 'cohens_dz_families': (sum(fam_means) / len(fam_means) / sd) if sd else None}


def summarize(rows, metric):
    vals = [r[metric] for r in rows if r.get(metric) is not None]
    return {'n': len(vals), 'n_null': len(rows) - len(vals), 'mean': sum(vals) / len(vals) if vals else None,
            'median': sorted(vals)[len(vals) // 2] if vals else None}


def pareto(method_means, higher, lower):
    """Non-dominated methods. Missing values make a method incomparable on that axis (treated as not dominated by it)."""
    names = sorted(method_means)
    def dominates(a, b):
        better = False
        for k in higher:
            x, y = method_means[a].get(k), method_means[b].get(k)
            if x is None or y is None:
                continue
            if x < y - 1e-12: return False
            better |= x > y + 1e-12
        for k in lower:
            x, y = method_means[a].get(k), method_means[b].get(k)
            if x is None or y is None:
                continue
            if x > y + 1e-12: return False
            better |= x < y - 1e-12
        return better
    return [m for m in names if not any(dominates(o, m) for o in names if o != m)]
