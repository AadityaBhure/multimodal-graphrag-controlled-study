"""AR-01 route labels from the frozen train/dev partition (addendum §2.1). Retrieval-only oracle, train split only.

A  : explicitly empty gold set (A is the cheapest successful route); an answerable query can never be labelled A.
B  : the shared rule router's FIRST source retrieves every gold paper (gold_paper_coverage == 1.0).
C  : otherwise (also when nothing would succeed). The C oracle's own success never changes a label, so the
     up-to-three-source oracle retrieval is not needed to assign labels.
"""
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.common.serialization import content_hash, canonical_json
from research.evaluation.benchmark import BenchmarkReader
from research.agentic.rule_router import first_source, route

POOL = ROOT / 'artifacts/phase9/pool'


def load(source, qid):
    p = POOL / source / (content_hash(qid) + '.json')
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def main():
    part = json.loads((ROOT / 'documentation/phase9/partition/ar01_partition.json').read_text(encoding='utf-8'))
    reader = BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark')
    recs = {q.query_id: q for q in reader.records('train')}
    labels, missing, errors = {}, [], 0
    for split in ('train', 'dev'):
        for qid in part[split]:
            q = recs[qid]; gold = set(q.gold_answer_ids); src = first_source(q.question)
            rec = load(src, qid)
            if rec is None:
                missing.append((qid, src)); continue
            if not gold:
                label, cov = 'A', None
            else:
                ok = rec['status'] == 'ok'
                errors += not ok
                cov = len(gold & {e['canonical_paper'] for e in rec['evidence']}) / len(gold) if ok else 0.0
                label = 'B' if cov == 1.0 else 'C'
            labels[qid] = {'split': split, 'label': label, 'first_source': src, 'coverage': cov, 'retrieval_status': rec['status'],
                           'router': route(q.question)['sources']}
    if missing:
        raise SystemExit('pool retrieval incomplete: %d missing (first: %s)' % (len(missing), missing[:3]))
    counts = {s: {c: sum(1 for v in labels.values() if v['split'] == s and v['label'] == c) for c in 'ABC'} for s in ('train', 'dev')}
    out = {'version': 'phase9-ar01-labels-v1', 'partition_sha256': part['partition_sha256'], 'class_counts': counts, 'retrieval_errors': errors,
           'by_first_source': {s: {c: sum(1 for v in labels.values() if v['first_source'] == s and v['label'] == c) for c in 'ABC'} for s in ('text', 'graph', 'structured')},
           'labels': labels}
    out['labels_sha256'] = content_hash(labels)
    path = ROOT / 'documentation/phase9/ar01/labels.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(out) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: out[k] for k in ('class_counts', 'retrieval_errors', 'by_first_source', 'labels_sha256')}, indent=1))


if __name__ == '__main__':
    main()
