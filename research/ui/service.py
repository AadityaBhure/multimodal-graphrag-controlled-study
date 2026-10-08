"""Interactive execution of unchanged Phase 6 methods, with explicit generation only."""
from datetime import datetime,timezone
import json
from pathlib import Path
from threading import RLock
import time
from uuid import uuid4
from research.common.config import PROJECT_ROOT
from research.common.serialization import content_hash
from research.common.reproducibility import seed_everything
from research.common.contracts import MethodError
from research.evaluation.contracts import SystemInput,SystemOutput,Observation
from research.evaluation.metrics import context_metrics
from research.experiments.config import load_runner_config
from research.baselines.config import BaselineOptions
from research.baselines.stores import Stores
from research.baselines.system import BaselineSystem,SOURCES
from research.baselines.generation import OfflineGenerator,GroqGenerator,parse_answer


class ResearchService:
    """One active baseline store, serialized across browser sessions to bound memory."""
    def __init__(self,root=PROJECT_ROOT/'data/MMG_STARK_MAG',work=PROJECT_ROOT/'artifacts/research_ui'):
        self.root=Path(root);self.work=Path(work);self.lock=RLock();self.store=None;self.method=None

    def retrieve(self,question,method):
        question=question.strip()
        if not question or len(question)>12000:raise ValueError('Enter a question between 1 and 12,000 characters.')
        if method not in SOURCES:raise ValueError('Select B1, B2, B3 or B4.')
        config=load_runner_config(PROJECT_ROOT/f'configs/baselines/{method}-offline.json')
        options=BaselineOptions.model_validate(config.retrieval_parameters)
        query_id='ui:'+content_hash(question)
        query_seed=int(content_hash({'seed':config.seed,'query_id':query_id})[:8],16)
        with self.lock:
            started=time.perf_counter()
            seed_everything(query_seed)
            if self.method!=method or self.store is None:
                if self.store is not None:self.store.close()
                self.store=None;self.method=None
                self.store=Stores(self.root,self.work/'stores'/method,options,modalities=SOURCES[method]);self.method=method
            system=BaselineSystem(config,self.store,OfflineGenerator(),self.work/'evidence_cache')
            result=system.execute(SystemInput(query_id=query_id,question=question,seed=query_seed))
            return {'run_id':uuid4().hex,'timestamp':datetime.now(timezone.utc).isoformat(),'method':method,'question':question,
                    'query_id':query_id,'query_seed':query_seed,'config_id':config.config_id,
                    'config_hash':content_hash(config.model_dump(mode='json')),'baseline_fingerprint':system.fingerprint,
                    'representation_manifest_sha256':self.store.manifest_hash,'output':result.model_dump(mode='json'),
                    'retrieval_wall_ms':(time.perf_counter()-started)*1000,'generation_attempts':[],
                    'scope':'interactive_inspection_not_benchmark_experiment'}

    def generate(self,run,*,explicit_request=False):
        if not explicit_request:raise ValueError('Generation requires an explicit user action.')
        if run['generation_attempts']:raise ValueError('This snapshot already has a generation attempt; retrieve again to retry explicitly.')
        result=SystemOutput.model_validate(run['output'])
        if result.errors or not result.context or not result.retained_evidence_ids:
            raise ValueError('Retrieve usable evidence before generating an answer.')
        config=load_runner_config(PROJECT_ROOT/f"configs/baselines/{run['method']}.json")
        options=BaselineOptions.model_validate(config.retrieval_parameters)
        allowed=[int(e.canonical_id.removeprefix('stark:')) for e in (result.evidence or ()) if e.evidence_id in result.retained_evidence_ids]
        client=None;called=False;raw=None;ids=None;errors=();usage={'generation_ms':None,'llm_calls':0}
        started=time.perf_counter()
        try:
            client=GroqGenerator(options)
            called=True
            raw,usage=client.generate(run['question'],result.context,run['query_seed'])
            try:ids=parse_answer(raw,allowed)
            except (ValueError,TypeError):
                errors=(MethodError(stage='answer_parse',code='InvalidGroundedAnswer',message='The response was not a valid context-grounded paper set.'),)
        except Exception as exc:
            usage={'generation_ms':(time.perf_counter()-started)*1000 if called else None,'llm_calls':int(called)}
            errors=(MethodError(stage='generation' if called else 'generation_setup',code=type(exc).__name__,
                                message='Generation could not complete. No credentials or provider payload are shown.'),)
        finally:
            if client is not None:client.close()
        observation=Observation(**{**result.observation.model_dump(),**usage})
        updated=result.model_copy(update={'answer':raw,'answer_ids':ids,'observation':observation,'errors':errors})
        attempt={'timestamp':datetime.now(timezone.utc).isoformat(),'model':options.model,'config_id':config.config_id,
                 'config_hash':content_hash(config.model_dump(mode='json')),'observation':observation.model_dump(mode='json'),
                 'errors':[e.model_dump() for e in errors]}
        return {**run,'output':updated.model_dump(mode='json'),'generation_attempts':[attempt]}

    def close(self):
        with self.lock:
            if self.store is not None:self.store.close()
            self.store=None;self.method=None


def performance(run):
    result=SystemOutput.model_validate(run['output']);obs=result.observation
    context=context_metrics(result.context,[e.evidence_id for e in result.evidence] if result.evidence is not None else None,
        result.retained_evidence_ids,tokens=result.context_tokens,tokenizer=result.tokenizer,
        baseline_characters=result.baseline_context_characters)
    return {'method':run['method'],'query':run['question'],'retrieved_papers':len(result.ranked_paper_ids or ()),
        'retrieval_ms':obs.retrieval_ms,'generation_ms':obs.generation_ms,'retrieval_calls':obs.retrieval_calls,
        'tool_calls':obs.tool_calls,'llm_calls':obs.llm_calls,'input_tokens':obs.input_tokens,'output_tokens':obs.output_tokens,
        **context,'answer_f1':None,'recall_at_5':None,'estimated_cost':None,'errors':len(result.errors)}


def comparison(runs):
    if len({r['question'] for r in runs})>1:raise ValueError('Comparison requires the same question.')
    rows=[]
    for run in runs:
        result=SystemOutput.model_validate(run['output'])
        for rank,paper in enumerate(result.ranked_paper_ids or (),1):
            rows.append({'method':run['method'],'rank':rank,'paper_id':paper,
                         'sources':', '.join(sorted({e.source_type for e in (result.evidence or ()) if e.canonical_id==f'stark:{paper}'}))})
    return rows
