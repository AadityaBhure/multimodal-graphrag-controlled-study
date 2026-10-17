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
from research.common.reproducibility import seed_everything
from research.repair.schedule import interleaved,prefetch
from research.repair.dispatch import Dispatcher,Paused,write,pre_dispatch_tokens,OVERHEAD_RESERVE,DAILY_TOKEN_BUDGET,MAX_RATE_LIMITED_ATTEMPTS
from scripts.prepare_rq1_repair import save

D=ROOT/'documentation/rq1_repair'
LOCAL=False;S=''          # --local: local model backend; every output uses the '_local' suffix (Groq run archived unchanged)
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
    # Operational plan revisions: each superseded plan is archived byte-for-byte as execution_plan_v<N>.json
    # before re-freezing; the current plan may only be replaced if its bytes equal that archive.
    revision=4;previous=D/f'execution_plan_v{revision-1}.json';current=D/'execution_plan.json'
    if not previous.exists():raise SystemExit(f'Archive the current plan as {previous.name} before re-freezing')
    if current.exists() and current.read_bytes()==previous.read_bytes():current.unlink()
    chain=[{'path':f'execution_plan_v{r}.json','sha256':digest(D/f'execution_plan_v{r}.json')} for r in range(1,revision)]
    save(current,{'version':'rq1-compliance-v1','plan_revision':revision,
        'supersedes':{**chain[-1],'reason':'operational revision only; scientific payloads, configs, cohort and prompts unchanged'},
        'superseded_plans':chain,
        'operational_revision_4':'provider calls made in query-major order (all five methods per query) by the unchanged systems; the unchanged runner then replays stored responses with the dispatcher in replay_only mode',
        'operational_revision_3':'approved maximum counts successful calls only (rate-limited attempts: separate allowance of %d, byte-identical resend); rolling 24 h local token ledger pauses before %d tokens/day'%(MAX_RATE_LIMITED_ATTEMPTS,DAILY_TOKEN_BUDGET),
        'timing_boundary_equivalence_sha256':digest(D/'timing_boundary_equivalence.json'),
        'local_audit_sha256':digest(D/'local_audit.json'),
        'interleaving_offline_check_sha256':digest(D/'interleaving_offline_check.json'),
        'configs':paths,'implementation_sha256':implementation,
        'queries':sorted(data),'maximum_successful_calls':192,'keyword_calls':32,'final_calls':160,
        'model':'openai/gpt-oss-120b','max_completion_tokens_per_stage':1024,'temperature':0,'reasoning_effort':'low',
        'initial_cooldown_seconds':90,'minimum_start_spacing_seconds':90,'test_human_test':False,
        'keyword_prompt':KEYWORD_PROMPT,'final_prompt':PROMPT,'cohort_frozen_before_outcomes':True,
        'operational_revision':4,'admission_policy':'pre-dispatch tokens = local o200k_harmony content tokens + %d overhead reserve <= 8000; completion cap 1024 is sent unchanged and is not charged at admission (groq-admission-probe-v1, HTTP 200)'%OVERHEAD_RESERVE,
        'overhead_reserve_tokens':OVERHEAD_RESERVE,'timing_boundary':'initialise() outside per-query context timer; initialisation_ms recorded separately'})
    print('FROZEN 32 queries; 32 keyword +160 final calls; max192; 196608 completion-token allowance',flush=True)

def freeze_local():
    from research.local_llm import LOCAL_MODEL
    data=inputs();paths=[]
    for method in METHODS:
        config=RunnerConfig(config_id='rq1-local-v1-'+method,system_id=method,system_version=RepairedContextSystem.version,
            query_ids=tuple(sorted(data)),model_ids=(LOCAL_MODEL,),embedding_model='sentence-transformers/all-MiniLM-L6-v2',
            context_method=method,retrieval_parameters={'input_manifest_sha256':digest(D/'input_manifest.json'),
                'generation':'frozen-baseline-prompt','completion_cap':1024,'context_chars':24000,'temperature':0,'reasoning_effort':'low',
                'adaptation_sha256':digest(D/'CM01_Frozen_Provenance_Adaptation.txt'),
                'decisions_sha256':digest(D/'Implementation_Decisions.md'),'keyword_prompt_sha256':content_hash(KEYWORD_PROMPT),'backend':'local'})
        p=D/'configs_local'/(method+'.json');save(p,config.model_dump(mode='json'));paths.append({'path':p.relative_to(D).as_posix(),'sha256':digest(p)})
    implementation={p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'research/repair').rglob('*.py')}
    implementation['scripts/run_rq1_repair.py']=digest(__file__)
    implementation['scripts/prepare_rq1_repair.py']=digest(ROOT/'scripts/prepare_rq1_repair.py')
    implementation['research/local_llm.py']=digest(ROOT/'research/local_llm.py')
    save(D/'execution_plan_local.json',{'version':'rq1-local-v1','backend':'local (Ollama)','model':LOCAL_MODEL,'configs':paths,
        'implementation_sha256':implementation,'queries':sorted(data),'maximum_successful_calls':192,'keyword_calls':32,'final_calls':160,
        'max_completion_tokens_per_stage':1024,'temperature':0,'reasoning_effort':'low','test_human_test':False,
        'keyword_prompt':KEYWORD_PROMPT,'final_prompt':PROMPT,'cohort_frozen_before_outcomes':True,
        'local_audit_sha256':digest(D/'local_audit.json'),'provider_order':'query-major prefetch, then replay-only runner'})
    print('FROZEN rq1-local-v1:',LOCAL_MODEL,len(data),'queries',flush=True)

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
    plan=json.loads((D/f'execution_plan{S}.json').read_text(encoding='utf-8'))
    for p,sha in plan['implementation_sha256'].items():
        if digest(ROOT/p)!=sha:raise ValueError('Frozen repair code changed: '+p)
    data=inputs();assert sorted(data)==plan['queries']
    # Capture provenance once and reject code changes on resume.
    provenance=code_provenance();provpath=D/f'execution_code{S}.json'
    if provpath.exists():
        old=json.loads(provpath.read_text(encoding='utf-8'))
        if old['source_tree_hash']!=provenance['source_tree_hash']:raise ValueError('Research source changed during experiment')
        provenance=old
    else:save(provpath,provenance)
    headers=json.loads((D/'provider_preflight/diagnostic.json').read_text())['completion']['headers']
    dispatcher=Dispatcher(D/f'dispatch{S}',headers,192,local=LOCAL);cache={}
    try:
        for q,obj in sorted(data.items()):
            seed=int(content_hash({'seed':42,'query_id':q})[:8],16);usage_path=D/f'keyword_usage{S}'/(content_hash(q)+'.json')
            def call(system,query):
                raw,usage,_=dispatcher.call('CM-03:keywords:'+q,system,query,seed,1024)
                save(usage_path,usage);return raw
            words=keywords(q,obj['question'],D/f'keywords{S}',call)
            cache[q]={'keywords':words,'usage':json.loads(usage_path.read_text(encoding='utf-8'))}
        encoder=QueryEncoder(ROOT/'data/MMG_STARK_MAG',BaselineOptions())
        reranker=LocalReranker(ROOT/'documentation/phase7/reranker_config.json',ROOT/'artifacts/phase7/reranker')
        # Check the keyword-dependent policy before final-answer dispatch. This
        # executes the same frozen diffusion without looking at gold/outcomes.
        reader=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark')
        validation={q.query_id:q for q in reader.records('validation') if q.query_id in data}
        offline=RepairedContextSystem('CM-03',data,encoder.encode,reranker,cache);offline.initialise()
        for q,obj in sorted(data.items()):
            seed=int(content_hash({'seed':42,'query_id':q})[:8],16)
            out=offline.execute(SystemInput(query_id=q,question=obj['question'],seed=seed,overlay=reader.overlay(validation[q])))
            user='QUESTION\n'+obj['question']+'\n\nEVIDENCE\n'+out.context
            reserved=pre_dispatch_tokens(sum(len(dispatcher.encoder.encode(s,disallowed_special=())) for s in (PROMPT,user)))
            if reserved>8000:raise Paused('CM-03 unchanged context exceeds observed capacity: '+q)
            write(D/f'cm03_local_audit{S}'/(content_hash(q)+'.json'),{'query_id':q,'reserved_tokens':reserved,
                'context_sha256':content_hash(out.context),'diagnostics':json.loads(out.diagnostics)})
            print('CM-03 LOCAL PASS',q,flush=True)
        configs=[]
        for c in plan['configs']:
            path=D/c['path']
            if digest(path)!=c['sha256']:raise ValueError('Frozen config mismatch')
            configs.append(RunnerConfig.model_validate_json(path.read_text(encoding='utf-8')))
        # Operational revision 4, stage A: provider calls in query-major order (all five methods per query)
        # through the unchanged systems, with the runner's own seed and overlay; responses are stored durably.
        ahead={cfg.system_id:RepairedContextSystem(cfg.system_id,data,encoder.encode,reranker,cache,FinalGenerator(dispatcher,cfg.system_id)) for cfg in configs}
        for system in ahead.values():system.initialise()
        seeds={cfg.system_id:cfg.seed for cfg in configs}
        def prefetch_one(q,method):
            query_seed=int(content_hash({'seed':seeds[method],'query_id':q})[:8],16);seed_everything(query_seed)
            ahead[method].execute(SystemInput(query_id=q,question=validation[q].question,seed=query_seed,overlay=reader.overlay(validation[q])))
        prefetch(interleaved(data,[cfg.system_id for cfg in configs]),prefetch_one,D/f'prefetch{S}')
        # Stage B: the unchanged Phase 5 runner per method replays the stored responses. replay_only stops the
        # run (no new call) if any payload differs from the one sent in stage A.
        dispatcher.replay_only=True
        for cfg in configs:
            start=time.perf_counter()
            system=RepairedContextSystem(cfg.system_id,data,encoder.encode,reranker,cache,FinalGenerator(dispatcher,cfg.system_id))
            # Resource/model setup happens before any per-query timer; its cost is recorded separately.
            write(D/f'initialisation{S}'/(cfg.system_id+'.json'),{'method':cfg.system_id,'initialisation_ms':system.initialise()})
            run(cfg,ROOT/'data/MMG_STARK_MAG/benchmark',D/f'runs{S}'/cfg.system_id,system,provenance=provenance)
            print('METHOD COMPLETE',cfg.system_id,'operational_seconds',time.perf_counter()-start,flush=True)
        write(D/f'execution_status{S}.json',{'status':'executed_pending_audit','phase9_started':False})
    except Paused as exc:
        write(D/f'execution_status{S}.json',{'status':'paused','reason':str(exc),'phase9_started':False});raise
    finally:dispatcher.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--execute',action='store_true')
    p.add_argument('--local',action='store_true');args=p.parse_args()
    if args.local:LOCAL,S=True,'_local'
    if args.freeze:freeze_local() if args.local else freeze()
    elif args.execute:execute()
    else:p.error('Choose --freeze or --execute')
