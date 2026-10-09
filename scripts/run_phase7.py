"""Run fixed five-way RQ1 comparison on identical cached graph candidate pools."""
from pathlib import Path
import argparse,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.rq1.contracts import METHODS,Options,Pool
from research.rq1.system import ContextSystem
from research.rq1.reranker import LocalReranker
from research.experiments.config import RunnerConfig
from research.experiments.runner import run,write
from research.evaluation.benchmark import digest
from scripts.audit_stark_mag import process_memory

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--methods',nargs='+',choices=METHODS,default=list(METHODS));a=parser.parse_args()
    docs=ROOT/'documentation/phase7';manifest=json.loads((docs/'pool_manifest.json').read_text(encoding='utf-8'));pools={}
    for row in manifest['files']:
        p=docs/row['path'];assert digest(p)==row['sha256'];pool=Pool.model_validate_json(p.read_text(encoding='utf-8'));pools[pool.query_id]=pool
    reranker=LocalReranker(docs/'reranker_config.json',ROOT/'artifacts/phase7/reranker') if 'CM-01' in a.methods else None
    if reranker:write(docs/'reranker_manifest.json',{'config':reranker.config,'files':reranker.files,'fingerprint':reranker.fingerprint})
    resources={}
    if (docs/'resources.json').exists():resources=json.loads((docs/'resources.json').read_text(encoding='utf-8'))
    for method in a.methods:
        options=Options(method=method)
        cfg=RunnerConfig(config_id=method+'-rq1-validation-v1',system_id=method,system_version='1',query_ids=tuple(sorted(pools)),seed=42,context_method=method,embedding_model='sentence-transformers/all-MiniLM-L6-v2',retrieval_parameters={'candidate_boundary':next(iter(pools.values())).boundary,'context_options':options.model_dump(mode='json'),'generation':'offline'})
        config_path=ROOT/'configs/rq1'/(method+'.json')
        if config_path.exists() and json.loads(config_path.read_text(encoding='utf-8'))!=cfg.model_dump(mode='json'):raise ValueError('Refusing incompatible existing RQ1 config')
        write(config_path,cfg.model_dump(mode='json'))
        started=time.perf_counter();system=ContextSystem(options,pools,reranker if method=='CM-01' else None,model_fingerprint=reranker.fingerprint if method=='CM-01' else None)
        run(cfg,ROOT/'data/MMG_STARK_MAG/benchmark',docs/'runs'/method,system)
        status=json.loads((docs/'runs'/method/'status.json').read_text(encoding='utf-8'));assert status['complete'] and status['errors']==0,status
        resources.setdefault(method,{'wall_seconds':time.perf_counter()-started,'memory':process_memory(),'queries':len(pools),'llm_calls':0})
        write(docs/'resources.json',resources);print(method,'PASS',resources[method],flush=True)
if __name__=='__main__':main()
