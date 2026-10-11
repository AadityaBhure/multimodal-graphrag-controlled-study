"""Durable retrieval over the frozen train/dev partition with the UNCHANGED B1/B2/B3 retrievers.

Train queries: only the shared router's first source (all that AR-01 labelling needs).
Dev queries: all three sources (Platt calibration + threshold fitting). Raw question only.
usage: phase9_retrieve_pool.py SOURCE SHARD NSHARDS
"""
from pathlib import Path
import json, sys, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.common.serialization import content_hash, canonical_json
from research.evaluation.benchmark import BenchmarkReader
from research.experiments.config import durable_write
from research.baselines.stores import Stores
from research.baselines.config import BaselineOptions
from research.baselines.retrieval import text_retrieve, graph_retrieve, structured_retrieve
from research.agentic.rule_router import first_source
from research.agentic.evidence import canonical_paper, provenance_paper_ids, render

FN = {'text': text_retrieve, 'graph': graph_retrieve, 'structured': structured_retrieve}
OUT = ROOT / 'artifacts/phase9/pool'


def tasks(source):
    part = json.loads((ROOT / 'documentation/phase9/partition/ar01_partition.json').read_text(encoding='utf-8'))
    dev = set(part['dev']); questions = {q.query_id: q.question for q in BenchmarkReader(ROOT / 'data/MMG_STARK_MAG/benchmark').records('train')}
    result = []
    for qid in part['train'] + part['dev']:
        if qid in dev or first_source(questions[qid]) == source:
            result.append((qid, questions[qid], qid in dev))
    return sorted(result, key=lambda t: content_hash(t[0]))


def main(source, shard, n):
    options = BaselineOptions()
    store = Stores(ROOT / 'data/MMG_STARK_MAG', ROOT / 'artifacts/phase9/work' / f'{source}-{shard}', options, modalities=(source,))
    mine = [t for i, t in enumerate(tasks(source)) if i % n == shard]
    (OUT / source).mkdir(parents=True, exist_ok=True); done = 0
    for qid, question, dev in mine:
        path = OUT / source / (content_hash(qid) + '.json')
        if path.exists():
            continue
        start = time.perf_counter()
        try:
            items, details = FN[source](store, question, options); status = 'ok'; err = None
        except Exception as exc:
            items, details, status, err = (), {}, 'error', type(exc).__name__
        rec = {'query_id': qid, 'source': source, 'status': status, 'error': err, 'retrieval_ms': (time.perf_counter() - start) * 1000,
               'detail_status': details.get('status'), 'evidence': [
                   {'evidence_id': e.evidence_id, 'canonical_paper': canonical_paper(e), 'provenance_papers': sorted(provenance_paper_ids(e)),
                    'score': e.score, **({'text': render(e)} if dev else {})} for e in items]}
        durable_write(path, canonical_json(rec) + '\n'); done += 1
        if done % 25 == 0:
            print(source, shard, done, '/', len(mine), flush=True)
    print('DONE', source, shard, len(mine), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
