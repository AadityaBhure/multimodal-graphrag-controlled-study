"""B1--B4 adapters for the common Phase 5 runner."""
import json
import time
from pathlib import Path
from research.common.contracts import RetrievalBundle,Timings,Calls,MethodError
from research.common.serialization import canonical_json,content_hash
from research.evaluation.contracts import SystemOutput,Observation
from research.experiments.evidence_cache import EvidenceCache
from research.evaluation.benchmark import digest
from research.baselines.config import BaselineOptions
from research.baselines.retrieval import text_retrieve,graph_retrieve,structured_retrieve,evidence
from research.baselines.generation import PROMPT,parse_answer

SOURCES={'B1':('text',),'B2':('graph',),'B3':('structured',),'B4':('text','graph','structured')}
RETRIEVERS={'text':text_retrieve,'graph':graph_retrieve,'structured':structured_retrieve}


def build_context(items,sources,limit):
    sections=[];retained=[];truncated=[]
    budget=limit//len(sources)
    for source in sources:
        header='['+source.upper()+']\n';body=header
        for item in items:
            if item.source_type!=source:continue
            payload=json.loads(item.payload)
            if source=='text' and 'content' in payload:
                payload={'paper_id':payload['paper_id'],'content':payload['content']}
            line=item.evidence_id+' '+canonical_json(payload)+'\n'
            remaining=budget-len(body)
            if remaining<40:break
            if len(line)>remaining:
                line=line[:remaining-16]+' [TRUNCATED]\n';truncated.append(item.evidence_id)
            body+=line;retained.append(item.evidence_id)
        sections.append(body)
    return ''.join(sections),tuple(retained),truncated


def apply_overlay(store,items,request,sources,options):
    if not request.overlay:return items,{'applied':False}
    overlay=json.loads(request.overlay);extra=[]
    if overlay['kind']=='conflict':
        injection=overlay['injection'];source=injection['source']
        if source in sources:
            paper=injection['paper_id']
            # Keep B2 restricted to already graph-selected papers.
            if source!='graph' or f'stark:{paper}' in {e.canonical_id for e in items if e.source_type=='graph'}:
                item=evidence(store,source,paper,{'paper_id':paper,'evaluation_overlay':True,
                    'conflicting_fact':injection['mutated_conflicting_evidence']})
                extra.append(item.model_copy(update={'evidence_id':item.evidence_id+':overlay'}))
    elif overlay['kind']=='noisy':
        for source,rows in overlay['distractors'].items():
            if source not in sources:continue
            for row in rows[:options.top_k]:
                paper=row['paper_id']
                if source=='text':
                    payload=store.texts([paper]).get(paper)
                elif source=='graph':
                    if f'stark:{paper}' not in {e.canonical_id for e in items if e.source_type=='graph'}:continue
                    payload={'paper_id':paper,'path':row.get('path',[]),'evaluation_overlay':True}
                else:
                    payload=store.structured_rows([paper]).get(paper)
                    if payload:payload={k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in payload.items()}
                if payload:
                    item=evidence(store,source,paper,{**payload,'evaluation_overlay':True})
                    extra.append(item.model_copy(update={'evidence_id':item.evidence_id+':overlay'}))
    else:raise ValueError('Unknown stress input')
    extra=[e.model_copy(update={'metadata':canonical_json({**json.loads(e.metadata),'origin':'phase4_evaluation_overlay','overlay_sha256':content_hash(request.overlay)})}) for e in extra]
    return items+tuple(extra),{'applied':bool(extra),'kind':overlay['kind'],'injected_evidence_ids':[e.evidence_id for e in extra]}


class BaselineSystem:
    version='1'
    def __init__(self,config,store,generator,cache_root=None):
        self.system_id=config.system_id
        if self.system_id not in SOURCES:raise ValueError('Unknown baseline')
        self.options=BaselineOptions.model_validate(config.retrieval_parameters)
        if config.model_ids not in ((),(self.options.model,)):raise ValueError('Generation model differs from baseline control')
        if config.embedding_model!=self.options.embedding:raise ValueError('Embedding model differs from frozen baseline')
        self.store=store;self.generator=generator;self.sources=SOURCES[self.system_id]
        if set(self.sources)!=store.modalities:raise ValueError('Store modality permissions differ from baseline')
        self.retrieval_fingerprint=content_hash({name:digest(Path(__file__).with_name(name+'.py')) for name in ('retrieval','stores','structured')})
        self.cache=EvidenceCache(cache_root) if cache_root and self.options.cache else None
        self.fingerprint=content_hash({'baseline':self.system_id,'version':self.version,'options':self.options.model_dump(),
            'representation':store.manifest_hash,'generator':generator.version,'prompt':PROMPT,'reasoning_effort':'low'})

    def execute(self,request):
        start=time.perf_counter();items=[];diagnostics={};calls=0;retrieval_errors=[]
        for source in self.sources:
            identity=EvidenceCache.identity(query_id=request.query_id,query_sha256=content_hash(request.question),
                representation_sha256=self.store.manifest_hash,retriever_id=source+'-baseline',retriever_version=self.retrieval_fingerprint,
                parameters=self.options.model_dump(),seed=request.seed)
            try:
                cached=self.cache.get(identity) if self.cache else None
                if cached is not None:
                    found=getattr(cached,source+'_evidence');details={**json.loads(found[0].metadata)['retrieval_diagnostics'],'cache_hit':True}
                else:
                    calls+=1
                    found,details=RETRIEVERS[source](self.store,request.question,self.options)
                    found=tuple(e.model_copy(update={'metadata':canonical_json({**json.loads(e.metadata),'retrieval_diagnostics':details})}) for e in found)
                    if self.cache and found:
                        self.cache.put(identity,RetrievalBundle(query_id=request.query_id,**{source+'_evidence':found}))
                items.extend(found);diagnostics[source]=details
            except Exception as exc:
                retrieval_errors.append(MethodError(stage=source+'_retrieval',code=type(exc).__name__,message='Source retrieval failed; no fallback performed'))
                diagnostics[source]={'status':'error','code':type(exc).__name__}
        items,overlay=apply_overlay(self.store,tuple(items),request,self.sources,self.options)
        diagnostics['overlay']=overlay
        retrieval_ms=(time.perf_counter()-start)*1000
        context,retained,truncated=build_context(items,self.sources,self.options.max_context_chars)
        diagnostics['context_truncated_evidence_ids']=truncated
        diagnostics['context_omitted_evidence_ids']=[e.evidence_id for e in items if e.evidence_id not in retained]
        diagnostics['source_invocations']=len(self.sources)
        allowed=[int(e.canonical_id.removeprefix('stark:')) for e in items if e.evidence_id in retained]
        errors=tuple(retrieval_errors);ids=None;raw=None;usage={'generation_ms':None,'llm_calls':0}
        try:
            if not errors:
                raw,usage=self.generator.generate(request.question,context,request.seed)
            if raw is not None:
                try:ids=parse_answer(raw,allowed)
                except (ValueError,TypeError):errors=(MethodError(stage='answer_parse',code='InvalidGroundedAnswer',message='Model output was not a valid context-grounded paper set'),)
        except Exception as exc:
            usage={'generation_ms':None,'llm_calls':1}
            errors=(MethodError(stage='generation',code=type(exc).__name__,message='Generation failed; provider credentials and payload omitted'),)
        ranked=tuple(dict.fromkeys(int(e.canonical_id.removeprefix('stark:')) for e in items))
        return SystemOutput(answer=raw,answer_ids=ids,ranked_paper_ids=ranked,evidence=items,context=context,
            retained_evidence_ids=retained,observation=Observation(retrieval_ms=retrieval_ms,retrieval_calls=calls,
                tool_calls=calls,**usage),errors=errors,diagnostics=canonical_json(diagnostics))
