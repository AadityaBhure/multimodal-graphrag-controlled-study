"""Adapter to the frozen Phase 5 runner; no retrieval or hidden generation."""
import json,time
from pathlib import Path
from research.common.serialization import content_hash,canonical_json
from research.evaluation.benchmark import digest
from research.evaluation.contracts import SystemOutput,Observation
from research.baselines.generation import parse_answer,PROMPT
from .contracts import Pool
from .manager import Manager,evidence

class ContextSystem:
    version='1'
    def __init__(self,options,pools,reranker=None,generator=None,model_fingerprint=None):
        self.options=options;self.system_id=options.method;self.pools=pools;self.reranker=reranker;self.generator=generator
        self.fingerprint=content_hash({'options':options.model_dump(),'pools':{k:v.fingerprint() for k,v in sorted(pools.items())},'model':model_fingerprint,'generator':generator.version if generator else 'offline','prompt':PROMPT,'code':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}})
    def execute(self,request):
        started=time.perf_counter();pool=self.pools[request.query_id]
        if pool.question!=request.question or pool.overlay_hash!=(content_hash(request.overlay) if request.overlay else None):raise ValueError('Candidate query/overlay mismatch')
        m=Manager(self.options,self.reranker);package=m.manage(pool,request.question);d=m.diagnostics
        answer=None;answer_ids=None;usage={'llm_calls':0,'generation_ms':None}
        if self.generator:
            answer,usage=self.generator.generate(request.question,package.serialized_context,request.seed)
            answer_ids=parse_answer(answer,d['selected_paper_ids'])
        d['common_upstream']=json.loads(pool.provenance);d['upstream_cache_hit']=True
        return SystemOutput(answer=answer,answer_ids=answer_ids,ranked_paper_ids=tuple(d['selected_paper_ids']),evidence=evidence(pool),context=package.serialized_context,retained_evidence_ids=package.included_evidence_ids,
            baseline_context_characters=d['raw_reference_characters'] or None,baseline_context_source='CM-B0:'+pool.fingerprint() if d['raw_reference_characters'] else None,
            observation=Observation(retrieval_ms=0.,retrieval_calls=0,tool_calls=0,**usage),diagnostics=canonical_json(d))
