"""AR-02 Platt calibration + LOWER/UPPER threshold fitting on the 10 % dev partition only (addendum §3)."""
from pathlib import Path
import json, sys, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.common.serialization import content_hash, canonical_json
from research.evaluation.benchmark import BenchmarkReader, digest
from research.agentic.rule_router import route, SOURCE_ORDER
from research.agentic.crag import CrossEncoderEvaluator, Platt, classify, fit_thresholds, LOWER_GRID, UPPER_GRID

POOL = ROOT / 'artifacts/phase9/pool'
CE_REVISION = '233902d25c440f23af6f7d6e94d2946bac0bee0a'
LITE = '--lite' in sys.argv      # demo-only: calibrate on the dev queries whose three source records already exist


def main():
    part = json.loads((ROOT / 'documentation/phase9/partition/ar01_partition.json').read_text(encoding='utf-8'))
    recs = {q.query_id: q for q in BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark').records('train')}
    ev = CrossEncoderEvaluator(ROOT / 'artifacts/phase9/models/ms-marco-MiniLM-L-6-v2'); ev.load()
    scores_path = ROOT / ('artifacts/phase9/lite/ar02_raw_scores.json' if LITE else 'artifacts/phase9/ar02_raw_scores.json')
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(scores_path.read_text(encoding='utf-8')) if scores_path.exists() else {}
    per_query, raws, labs, fingerprint = {}, [], [], []
    started = time.perf_counter()
    for n, qid in enumerate(part['dev']):
        q = recs[qid]; gold = set(q.gold_answer_ids)
        if not gold:
            continue                                       # empty-gold queries are excluded from fitting
        by_source = {}
        for s in SOURCE_ORDER:
            p = POOL / s / (content_hash(qid) + '.json')
            if not p.exists():
                if LITE:
                    by_source = None; break
                raise SystemExit('dev pool incomplete: %s %s' % (s, qid))
            rec = json.loads(p.read_text(encoding='utf-8')); fingerprint.append(content_hash(rec))
            if rec['status'] != 'ok':
                rec['evidence'] = []
            by_source[s] = rec['evidence']
        if by_source is None:
            continue
        per_query[qid] = by_source
        for s in SOURCE_ORDER:
            for e in by_source[s]:
                key = content_hash([q.question, e['evidence_id'], e['text']])
                if key not in cache:
                    cache[key] = ev.raw_scores(q.question, [e['text']])[0]
                e['raw'] = cache[key]
                raws.append(e['raw']); labs.append(int(bool(gold & set(e['provenance_papers']))))
        if n % 100 == 0:
            print('scored', n, '/', len(part['dev']), round(time.perf_counter() - started), flush=True)
    scores_path.write_text(canonical_json(cache) + '\n', encoding='utf-8', newline='\n')
    platt = Platt.fit(raws, labs)
    samples = []
    for qid, by_source in per_query.items():
        gold = set(recs[qid].gold_answer_ids)
        order = list(route(recs[qid].question)['sources']) + [s for s in SOURCE_ORDER if s not in route(recs[qid].question)['sources']]
        acc, seen = [], set()
        for k in range(1, len(order) + 1):
            for e in by_source[order[k - 1]]:
                if e['evidence_id'] not in seen:
                    seen.add(e['evidence_id']); acc.append(e)
            cov = len(gold & {e['canonical_paper'] for e in acc}) / len(gold)
            truth = 'GOOD' if cov == 1.0 else 'BAD' if cov == 0.0 else 'AMBIGUOUS'
            samples.append((truth, [platt.prob(e['raw']) for e in acc]))
    best, rows = fit_thresholds(samples)
    truths = {s: sum(1 for t, _ in samples if t == s) for s in ('GOOD', 'AMBIGUOUS', 'BAD')}
    out = {'version': 'phase9-ar02-calibration-v1', 'evaluator': 'cross-encoder/ms-marco-MiniLM-L-6-v2', 'evaluator_revision': CE_REVISION,
           'evaluator_files_sha256': ev.fingerprint, 'partition_sha256': part['partition_sha256'],
           'platt': {'coef': platt.coef, 'intercept': platt.intercept, 'solver': 'lbfgs', 'C': 1.0, 'class_weight': 'balanced', 'max_iter': 1000, 'random_state': 42,
                     'n_items': len(raws), 'n_positive': sum(labs), 'n_negative': len(labs) - sum(labs), 'n_queries': len(per_query)},
           'threshold_samples': len(samples), 'threshold_truth_counts': truths, 'thresholds': {'lower': best['lower'], 'upper': best['upper']},
           'selected': best, 'grid': rows, 'grids': {'lower': LOWER_GRID, 'upper': UPPER_GRID},
           'data_fingerprint': content_hash(sorted(fingerprint)), 'used_splits': ['train (dev partition only)'], 'validation_test_human_test_used': False}
    path = (ROOT / 'artifacts/phase9/lite/ar02_calibration.json') if LITE else (ROOT / 'documentation/phase9/calibration/ar02_calibration.json')
    out['lite'] = LITE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: out[k] for k in ('platt', 'thresholds', 'threshold_truth_counts')}, indent=1), flush=True)


if __name__ == '__main__':
    main()
