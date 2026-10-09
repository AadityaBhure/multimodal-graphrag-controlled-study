"""Post-run audit for fixed boundaries, metric recomputation and immutable source files."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.rq1.contracts import Pool,METHODS
from research.evaluation.benchmark import BenchmarkReader,digest
from research.evaluation.contracts import RunRecord
from research.experiments.runner import compute_metrics,write
from research.experiments.config import load_runner_config
from scripts.audit_phase5_preservation import audit,git
D=ROOT/'documentation/phase7'
def main():
    reader=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark');queries={q.query_id:q for q in reader.records('validation')}
    manifest=json.loads((D/'pool_manifest.json').read_text(encoding='utf-8'));pools={}
    for row in manifest['files']:
        assert digest(D/row['path'])==row['sha256'];pool=Pool.model_validate_json((D/row['path']).read_text(encoding='utf-8'));assert pool.fingerprint()==row['pool_hash'];pools[pool.query_id]=pool
    count=0
    for method in METHODS:
        cfg=load_runner_config(ROOT/'configs/rq1'/(method+'.json'))
        for line in (D/'runs'/method/'records.jsonl').read_text(encoding='utf-8').splitlines():
            r=RunRecord.model_validate_json(line);p=pools[r.query_id];d=json.loads(r.output.diagnostics)
            assert r.metrics==compute_metrics(queries[r.query_id],r.output,cfg,r.total_latency_ms)
            assert r.source_type=='generated' and r.split=='validation' and r.labels.status=='programmatically_verified'
            assert d['candidate_hash']==p.fingerprint() and len(r.output.context)<=24000
            assert set(d['selected_nodes'])<={n.node_id for n in p.nodes} and set(d['selected_edges'])<={e.key for e in p.edges}
            assert r.observation.retrieval_calls==0 and r.observation.llm_calls==0 and r.answer_ids is None
            assert not r.errors;count+=1
    assert count==80
    assert git('rev-parse','HEAD')=='cd450bbd850fc8066c82b701310420d27e7f0df7'
    assert not git('diff','HEAD','--name-only'),'Previously checkpointed files were changed'
    result=audit();result['phase6_closeout_checkpoint']=result.pop('phase4_checkpoint');result.update(rq1_records_recomputed=count,identical_pool_boundaries_verified=True,all_checkpointed_files_unchanged=True)
    write(D/'preservation.json',result);print('PASS: 80 records, fixed boundaries, all frozen payloads and prior tracked files')
if __name__=='__main__':main()
