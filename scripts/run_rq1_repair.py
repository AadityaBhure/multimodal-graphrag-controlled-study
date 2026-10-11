"""Versioned Phase5 runner and durable keyword/final-answer dispatch.

--freeze writes the reviewable plan/configs only. --execute consumes that plan.
The original Phase7/8 experiments are never reopened or overwritten.
"""
from pathlib import Path
import argparse,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.common.serialization import content_hash
from research.evaluation.benchmark import digest,BenchmarkReader
from research.evaluation.contracts import SystemInput
from research.experiments.config import RunnerConfig
from research.experiments.runner import run,code_provenance
from research.baselines.stores import QueryEncoder
from research.baselines.config import BaselineOptions
from research.baselines.generation import PROMPT
from research.rq1.reranker import LocalReranker
from research.repair.rq1_compliance_v1.system import RepairedContextSystem
from research.repair.rq1_compliance_v1.cm03 import keywords,KEYWORD_PROMPT
from research.repair.dispatch import Dispatcher,Paused,write
from scripts.prepare_rq1_repair import save

D=ROOT/'documentation/rq1_repair'
METHODS=('CM-B0','CM-B1','CM-01','CM-02','CM-03')

def inputs():
    manifest=json.loads((D/'input_manifest.json').read_text(encoding='utf-8'));result={}
    for row in manifest['files']:
        p=D/row['path']
        if digest(p)!=row['sha256']:raise ValueError('Input snapshot checksum mismatch')
        obj=json.loads(p.read_text(encoding='utf-8'));result[obj['query_id']]=obj
    assert len(result)==32
    return result

def freeze():
    data=inputs();paths=[]
    for method in METHODS:
        config=RunnerConfig(config_id='rq1-compliance-v1-'+method,system_id=method,system_version=RepairedContextSystem.version,
            query_ids=tuple(sorted(data)),model_ids=('openai/gpt-oss-120b',),embedding_model='sentence-transformers/all-MiniLM-L6-v2',
            context_method=method,retrieval_parameters={'input_manifest_sha256':digest(D/'input_manifest.json'),
                'generation':'frozen-baseline-prompt','completion_cap':1024,'context_chars':24000,'temperature':0,'reasoning_effort':'low',
                'adaptation_sha256':digest(D/'CM01_Frozen_Provenance_Adaptation.txt'),
                'decisions_sha256':digest(D/'Implementation_Decisions.md'),'keyword_prompt_sha256':content_hash(KEYWORD_PROMPT)})
        p=D/'configs'/(method+'.json');save(p,config.model_dump(mode='json'));paths.append({'path':p.relative_to(D).as_posix(),'sha256':digest(p)})
    implementation={p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'research/repair').rglob('*.py')}
    implementation['scripts/run_rq1_repair.py']=digest(__file__)
    implementation['scripts/prepare_rq1_repair.py']=digest(ROOT/'scripts/prepare_rq1_repair.py')
    save(D/'execution_plan.json',{'version':'rq1-compliance-v1','configs':paths,'implementation_sha256':implementation,
        'queries':sorted(data),'maximum_successful_calls':192,'keyword_calls':32,'final_calls':160,
        'model':'openai/gpt-oss-120b','max_completion_tokens_per_stage':1024,'temperature':0,'reasoning_effort':'low',
        'initial_cooldown_seconds':90,'minimum_start_spacing_seconds':90,'test_human_test':False,
        'keyword_prompt':KEYWORD_PROMPT,'final_prompt':PROMPT,'cohort_frozen_before_outcomes':True})
    print('FROZEN 32 queries; 32 keyword +160 final calls; max192; 196608 completion-token allowance',flush=True)

class FinalGenerator:
    version='rq1-compliance-v1-groq-grounded'
    def __init__(self,dispatcher,method):self.dispatcher=dispatcher;self.method=method
    def generate(self,question,context,seed):
        raw,usage,_=self.dispatcher.call(self.method+':final:'+content_hash(question),PROMPT,
            'QUESTION\n'+question+'\n\nEVIDENCE\n'+context,seed,1024)
        return raw,usage

def execute():
    audit_path=D/'local_audit.json'
    if not audit_path.exists():raise Paused('Complete offline context/capacity audit required before any dispatch')
    local=json.loads(audit_path.read_text(encoding='utf-8'))
    if local.get('status')!='PASS' or local.get('records')!=128:
        raise Paused('Offline context/capacity audit has not passed')
    plan=json.loads((D/'execution_plan.json').read_text(encoding='utf-8'))
    for p,sha in plan['implementation_sha256'].items():
        if digest(ROOT/p)!=sha:raise ValueError('Frozen repair code changed: '+p)
    data=inputs();assert sorted(data)==plan['queries']
    # Capture provenance once and reject code changes on resume.
    provenance=code_provenance();provpath=D/'execution_code.json'
    if provpath.exists():
        old=json.loads(provpath.read_text(encoding='utf-8'))
        if old['source_tree_hash']!=provenance['source_tree_hash']:raise ValueError('Research source changed during experiment')
        provenance=old
    else:save(provpath,provenance)
    headers=json.loads((D/'provider_preflight/diagnostic.json').read_text())['completion']['headers']
    dispatcher=Dispatcher(D/'dispatch',headers,192);cache={}
    try:
        for q,obj in sorted(data.items()):
            seed=int(content_hash({'seed':42,'query_id':q})[:8],16);usage_path=D/'keyword_usage'/(content_hash(q)+'.json')
            def call(system,query):
                raw,usage,_=dispatcher.call('CM-03:keywords:'+q,system,query,seed,1024)
                save(usage_path,usage);return raw
            words=keywords(q,obj['question'],D/'keywords',call)
            cache[q]={'keywords':words,'usage':json.loads(usage_path.read_text(encoding='utf-8'))}
        encoder=QueryEncoder(ROOT/'data/MMG_STARK_MAG',BaselineOptions())
        reranker=LocalReranker(ROOT/'documentation/phase7/reranker_config.json',ROOT/'artifacts/phase7/reranker')
        # Check the keyword-dependent policy before final-answer dispatch. This
        # executes the same frozen diffusion without looking at gold/outcomes.
        reader=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark')
        validation={q.query_id:q for q in reader.records('validation') if q.query_id in data}
        offline=RepairedContextSystem('CM-03',data,encoder.encode,reranker,cache)
        for q,obj in sorted(data.items()):
            seed=int(content_hash({'seed':42,'query_id':q})[:8],16)
            out=offline.execute(SystemInput(query_id=q,question=obj['question'],seed=seed,overlay=reader.overlay(validation[q])))
            user='QUESTION\n'+obj['question']+'\n\nEVIDENCE\n'+out.context
            reserved=sum(len(dispatcher.encoder.encode(s,disallowed_special=())) for s in (PROMPT,user))+256+1024
            if reserved>8000:raise Paused('CM-03 unchanged context exceeds observed capacity: '+q)
            write(D/'cm03_local_audit'/(content_hash(q)+'.json'),{'query_id':q,'reserved_tokens':reserved,
                'context_sha256':content_hash(out.context),'diagnostics':json.loads(out.diagnostics)})
            print('CM-03 LOCAL PASS',q,flush=True)
        for c in plan['configs']:
            path=D/c['path']
            if digest(path)!=c['sha256']:raise ValueError('Frozen config mismatch')
            cfg=RunnerConfig.model_validate_json(path.read_text(encoding='utf-8'));start=time.perf_counter()
            system=RepairedContextSystem(cfg.system_id,data,encoder.encode,reranker,cache,FinalGenerator(dispatcher,cfg.system_id))
            run(cfg,ROOT/'data/MMG_STARK_MAG/benchmark',D/'runs'/cfg.system_id,system,provenance=provenance)
            print('METHOD COMPLETE',cfg.system_id,'operational_seconds',time.perf_counter()-start,flush=True)
        write(D/'execution_status.json',{'status':'executed_pending_audit','phase9_started':False})
    except Paused as exc:
        write(D/'execution_status.json',{'status':'paused','reason':str(exc),'phase9_started':False});raise
    finally:dispatcher.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--execute',action='store_true');args=p.parse_args()
    if args.freeze:freeze()
    elif args.execute:execute()
    else:p.error('Choose --freeze or --execute')
