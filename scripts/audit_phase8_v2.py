"""Read-only scientific/pacing checks plus protected dataset hashes."""
import json
import sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_phase8 import load_inputs
from scripts.audit_phase5_preservation import audit
from research.rq2.contracts import evidence
from research.evaluation.benchmark import digest,BenchmarkReader
from research.evaluation.contracts import RunRecord
from research.experiments.config import load_runner_config
from research.experiments.runner import compute_metrics,write
D=ROOT/'documentation/phase8_generation_v2'

def main():
    plan=json.loads((ROOT/'documentation/groq_diagnostic/rerun_v2/plan.json').read_text())
    protected=json.loads((D/'protected_before.json').read_text())
    for p,sha in protected.items():assert digest(ROOT/p)==sha,p
    inputs=load_inputs()
    queries={q.query_id:q for q in BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark').records('validation')}
    count=0
    for c in plan['configs']:
        assert digest(ROOT/c['config_path'])==c['config_sha256']
        cfg=load_runner_config(ROOT/c['config_path'])
        path=ROOT/c['run_directory']/'records.jsonl'
        if not path.exists():continue
        for line in path.read_text(encoding='utf-8').splitlines():
            r=RunRecord.model_validate_json(line);count+=1
            assert r.query_id in plan['query_ids'] and r.split=='validation'
            assert r.metrics==compute_metrics(queries[r.query_id],r.output,cfg,r.total_latency_ms)
            if r.output:
                assert r.output.evidence==evidence(inputs[r.query_id])
                assert r.observation.retrieval_calls==0 and r.observation.tool_calls==0
                d=json.loads(r.output.diagnostics)
                assert d['input_unchanged'] and d['bundle_hash']==inputs[r.query_id].bundle.bundle_hash()
    for p,sha in plan['implementations_sha256'].items():assert digest(ROOT/p)==sha
    http=[json.loads(p.read_text()) for p in sorted((D/'http_dispatches').glob('[0-9][0-9].json'))]
    assert len(http)<=16
    if http:
        started=json.loads((D/'execution_started.json').read_text())
        assert (datetime.fromisoformat(http[0]['timestamp'])-datetime.fromisoformat(started['timestamp'])).total_seconds()>=90
    for previous,current in zip(http,http[1:]):
        assert current['start_monotonic']-previous['start_monotonic']>=90
        assert previous.get('http_status')!=429,'Request issued after 429'
    assert all(r['reserved_tokens']<=8000 for r in http)
    assert len({r['payload_sha256'] for r in http})==len(http),'Duplicate dispatch payload'
    result=audit();result['phase7_checkpoint']=result.pop('phase4_checkpoint')
    result.update(v2_records_recomputed=count,v2_http_requests=len(http),original_phase8_files_unchanged=len(protected),
        scientific_implementations_unchanged=True,request_spacing_verified=True,no_retries=True,
        requests_after_first_429=0,phase9_started=False)
    write(D/'preservation.json',result)
    print('PASS:',count,'v2 records;',len(http),'requests; spacing, immutable evidence, original run and 695 protected data payloads')

if __name__=='__main__':main()
