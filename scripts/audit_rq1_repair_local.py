"""Read-only real-input audit of deterministic repaired context policies.

CM-03 requires its frozen LLM keyword cache and is covered by fixtures until
that cache exists. No generation, retrieval, or query outcomes are used here.
"""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_rq1_repair import inputs,D
from research.evaluation.benchmark import BenchmarkReader
from research.evaluation.contracts import SystemInput
from research.baselines.stores import QueryEncoder
from research.baselines.config import BaselineOptions
from research.rq1.reranker import LocalReranker
from research.repair.rq1_compliance_v1.system import RepairedContextSystem
from research.repair.dispatch import write,pre_dispatch_tokens
from research.common.serialization import content_hash

def main(methods=('CM-B0','CM-B1','CM-01','CM-02')):
    import tiktoken
    from scripts.audit_stark_mag import process_memory
    data=inputs();reader=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark')
    queries={q.query_id:q for q in reader.records('validation') if q.query_id in data}
    encoder=QueryEncoder(ROOT/'data/MMG_STARK_MAG',BaselineOptions())
    reranker=LocalReranker(ROOT/'documentation/phase7/reranker_config.json',ROOT/'artifacts/phase7/reranker')
    tokenizer=tiktoken.get_encoding('o200k_harmony');rows=[];started=time.perf_counter();hashes={}
    from research.baselines.generation import PROMPT
    for method in methods:
        system=RepairedContextSystem(method,data,encoder.encode,reranker);system.initialise()
        for qid in sorted(data):
            q=queries[qid];start=time.perf_counter()
            out=system.execute(SystemInput(query_id=qid,question=q.question,seed=42,overlay=reader.overlay(q)))
            assert not out.errors and out.answer is None and out.observation.llm_calls==0
            d=json.loads(out.diagnostics);key=content_hash([e.model_dump(mode='json') for e in out.evidence])
            if qid in hashes:assert hashes[qid]==(key,d['pass_through_hashes'])
            else:hashes[qid]=(key,d['pass_through_hashes'])
            user='QUESTION\n'+q.question+'\n\nEVIDENCE\n'+out.context
            reserved=pre_dispatch_tokens(sum(len(tokenizer.encode(s,disallowed_special=())) for s in (PROMPT,user)))
            row={'method':method,'query_id':qid,'context_chars':len(out.context),'reserved_tokens':reserved,
                'seconds':time.perf_counter()-start,'evidence_hash':key,'pass_through_hashes':d['pass_through_hashes'],
                'memory':process_memory(),'fallback':d.get('fallback')}
            if reserved>8000:
                write(D/'capacity_blocker.json',{'status':'BLOCKED_PROVIDER_CAPACITY','row':row,
                    'content_tokens':reserved-128,'completion_cap':1024,'overhead_reserve':128,
                    'observed_tpm':8000,'context_sha256':content_hash(out.context),'query_sha256':content_hash(q.question),
                    'tokenizer':'tiktoken-0.12.0:o200k_harmony','scientific_payload_changed':False,
                    'request_sent':False,'wait_can_resolve':False,'diagnostics':d})
                print('BLOCKED_PROVIDER_CAPACITY',method,qid,reserved,flush=True)
                return
            rows.append(row);write(D/'local_audit_progress.json',{'rows':rows,'complete':False})
            print(method,qid,'PASS',reserved,flush=True)
    write(D/'local_audit.json',{'status':'PASS','records':len(rows),'rows':rows,'elapsed_seconds':time.perf_counter()-started,
        'cm03':'Fixture tested; real keyword cache not yet dispatched','api_calls':0,'new_retrieval_calls':0})

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--methods',nargs='+',choices=('CM-B0','CM-B1','CM-01','CM-02'))
    args=parser.parse_args();main(tuple(args.methods) if args.methods else ('CM-B0','CM-B1','CM-01','CM-02'))
