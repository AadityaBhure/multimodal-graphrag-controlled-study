"""Validate closeout tables against raw Phase 5 records, without rerunning retrieval."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.evaluation.contracts import RunRecord
from research.evaluation.aggregate import aggregate
from research.experiments.config import load_runner_config
from research.experiments.runner import compute_metrics,write
from research.evaluation.benchmark import BenchmarkReader
D=ROOT/'documentation/phase6_closeout'
def main():
    queries={q.query_id:q for q in BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark').records('validation') if q.provenance['source']=='generated'}
    expected=[];count=0;null_gold=0
    for b in ('B1','B2','B3','B4'):
        config=load_runner_config(D/(b+'-config.json'))
        original=load_runner_config(ROOT/f'configs/baselines/{b}-validation-offline.json')
        a=config.model_dump();z=original.model_dump()
        for k in ('query_ids','config_id'):a.pop(k);z.pop(k)
        assert a==z
        records=[RunRecord.model_validate_json(line) for line in (D/'runs'/b/'records.jsonl').read_text(encoding='utf-8').splitlines()]
        assert len(records)==56 and {r.query_id for r in records}==set(queries)
        for r in records:
            assert r.metrics==compute_metrics(queries[r.query_id],r.output,config,r.total_latency_ms)
            assert not r.errors and r.observation.llm_calls==0 and r.split=='validation'
            assert r.labels.status=='programmatically_verified' and r.source_type=='generated'
            assert r.metrics['f1'] is None and r.metrics['input_tokens'] is None
            if not r.gold_ids:
                assert r.metrics['recall@5'] is None and r.metrics['mrr'] is None
                null_gold+=1
            count+=1
        expected.extend({'baseline':b,**row} for row in aggregate(records) if row['cohort']=='overall' or row['cohort'].startswith(('modality/','hop/','stress/')))
    assert expected==json.loads((D/'comparison.json').read_text(encoding='utf-8'))
    intersections=json.loads((D/'intersection_comparison.json').read_text(encoding='utf-8'))
    assert sum(r['n_queries'] for r in intersections if r['metric']=='mrr')==224
    write(D/'validation.json',{'status':'pass','raw_records_recomputed':count,'empty_gold_records_with_null_retrieval_metrics':null_gold,'comparison_rows_verified':len(expected),'intersection_rows':len(intersections),'llm_calls':0,'configs_differ_only_in_id_and_query_selection':True})
    print('Closeout audit PASS:',count,'records;',len(expected),'comparison rows')
if __name__=='__main__':main()
