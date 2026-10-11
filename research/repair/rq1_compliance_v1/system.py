"""Gold-free Phase5 adapter: fixed pass-through and graph-only variation."""
import json,time
from research.rq1.contracts import Pool,Options
from research.rq1.manager import Manager,evidence
from research.common.contracts import EvidenceItem,Provenance,MethodError
from research.common.serialization import canonical_json,content_hash
from research.evaluation.contracts import SystemOutput,Observation
from research.baselines.generation import parse_answer,PROMPT
from . import cm01,cm02,cm03
from .context import assemble

class RepairedContextSystem:
    version='rq1-compliance-v1'
    def __init__(self,method,inputs,encode,reranker=None,keyword_cache=None,generator=None):
        self.system_id=method;self.inputs=inputs;self.encode=encode;self.reranker=reranker
        self.keyword_cache=keyword_cache;self.generator=generator
        self._initialised=False;self.initialisation_ms=None
        self.fingerprint=content_hash({'method':method,'inputs':inputs,'version':self.version,'prompt':PROMPT,
            'generation':getattr(generator,'version','offline'),'keyword_cache':keyword_cache if method=='CM-03' else None,
            'reranker':getattr(reranker,'fingerprint',None) if method=='CM-01' else None})

    def initialise(self):
        """Load frozen models/resources BEFORE per-query timing; results of the warm-up calls are discarded.

        Operational timing boundary only: same weights, inputs and ordering. Setup cost is
        recorded separately as initialisation_ms and never inside context_ms.
        """
        if self._initialised:return self.initialisation_ms
        started=time.perf_counter();method=self.system_id
        if method in ('CM-01','CM-03') and self.encode is not None:self.encode(['initialisation warm-up'])
        if method=='CM-01' and self.reranker is not None:
            load=getattr(self.reranker,'load',None)
            if load:load()
            self.reranker('initialisation warm-up query',['initialisation warm-up text'])
        if method=='CM-02':import pcst_fast  # noqa: F401 (solver import outside the query timer)
        self.initialisation_ms=(time.perf_counter()-started)*1000;self._initialised=True
        return self.initialisation_ms

    def execute(self,request):
        lazy=not self._initialised
        if lazy:self.initialise()  # outside the context timer; flagged so a runner that forgot to initialise is visible
        data=self.inputs[request.query_id]
        if request.question!=data['question']:raise ValueError('Question differs from frozen input')
        pool=Pool.model_validate(data['pool']);before=pool.fingerprint();budget=data['source_budget']-len('[GRAPH]\n')
        if pool.overlay_hash!=(content_hash(request.overlay) if request.overlay else None):raise ValueError('Frozen overlay mismatch')
        # The graph conflict overlay stays explicitly tagged and identical between
        # methods; it is never misrepresented as a canonical official relation.
        overlays=[EvidenceItem.model_validate(e) for e in data['graph_conflict_overlays']]
        overlay_text='\n'.join(e.evidence_id+' '+e.payload for e in overlays)
        budget-=len(overlay_text)+(1 if overlay_text else 0)
        if budget<0:raise ValueError('Frozen overlay exceeds graph share')
        started=time.perf_counter();method=self.system_id
        incoming=list(evidence(pool));retained=[];paper_ids=[]
        all_units=cm01.canonical_units(pool)
        for u in all_units:
            incoming.append(EvidenceItem(evidence_id=u.unit_id,source_type='graph',canonical_id=f'stark:{u.source_node_id}',
                content=u.context_line(),score=data['unit_scores'][u.unit_id],provenance=(Provenance(dataset_version='MMG-STaRK-MAG-v1',source_id=str(u.canonical_official_edge_id),locator='graph/edges.parquet'),)))
        if method=='CM-01':
            graph,units,d=cm01.organize(pool,request.question,budget,self.encode,self.reranker)
            retained=[u.unit_id for u in units]
            chosen=list(dict.fromkeys(n for u in units for n in (u.source_node_id,u.target_node_id)))
            selected_nodes=set(chosen)
            d['selected_nodes']=chosen;d['selected_edges']=[u.canonical_official_edge_id for u in units]
        elif method=='CM-02':
            chosen,keys,d=cm02.select(pool,{n.node_id:n.relevance for n in pool.nodes if n.relevance is not None},data['edge_scores'])
            graph,chosen,keys,d=cm02.serialize_pruned(pool,chosen,keys,d,budget)
            selected_nodes=set(chosen);retained=[f'node:{n}' for n in chosen]+['edge:'+k for k in keys]
            d.update(selected_nodes=chosen,selected_edges=keys)
        elif method=='CM-03':
            if self.keyword_cache is None:raise ValueError('Frozen keyword cache required before execution')
            entry=self.keyword_cache[request.query_id]
            words=entry['keywords'] if isinstance(entry,dict) else entry
            scores=cm03.keyword_scores(pool,words,self.encode)
            nodes={n.node_id:n for n in pool.nodes}
            chosen,keys,d=cm03.diffuse(pool,scores,lambda e:cm03.hybrid(nodes[e.source].vector,nodes[e.target].vector,data['query_vector']))
            graph,chosen,keys,d=cm03.serialize_support(pool,chosen,keys,d,budget)
            selected_nodes=set(chosen);retained=[f'node:{n}' for n in chosen]+['edge:'+k for k in keys]
            d.update(selected_nodes=chosen,selected_edges=keys,keywords=words,keyword_scores=scores)
        else:
            manager=Manager(Options(method=method,budget=budget));package=manager.manage(pool,request.question)
            graph=package.serialized_context;retained=list(package.included_evidence_ids);d=manager.diagnostics
            selected_nodes=set(d['selected_nodes'])
        paper_nodes={n.node_id for n in pool.nodes if n.node_type=='paper'}
        paper_ids=[n for n in d['selected_nodes'] if n in paper_nodes]
        graph+='\n'+overlay_text if overlay_text else ''
        incoming+=overlays;retained += [e.evidence_id for e in overlays]
        paper_ids += [int(e.canonical_id.split(':')[1]) for e in overlays]
        for e in data['baseline_evidence']:
            item=EvidenceItem.model_validate(e)
            if item.source_type=='graph':continue
            incoming.append(item)
            if item.evidence_id in data['pass_through'][item.source_type]['retained']:
                retained.append(item.evidence_id);paper_ids.append(int(item.canonical_id.split(':')[1]))
        context=assemble(data['pass_through'],data['sources'],graph)
        context_ms=(time.perf_counter()-started)*1000
        usage={'llm_calls':0,'generation_ms':None};raw=ids=None;errors=()
        if self.generator:
            raw,usage=self.generator.generate(request.question,context,request.seed)
            try:ids=parse_answer(raw,paper_ids)
            except (ValueError,TypeError):
                errors=(MethodError(stage='answer_parse',code='InvalidGroundedAnswer',message='Model output was not a valid context-grounded paper set'),)
                d['parser_failure']=True
        if method=='CM-03' and isinstance(self.keyword_cache[request.query_id],dict):
            kw_usage=self.keyword_cache[request.query_id]['usage'];d['keyword_usage']=kw_usage
            for name in ('llm_calls','input_tokens','output_tokens','generation_ms'):
                a,b=usage.get(name),kw_usage.get(name)
                usage[name]=a+b if a is not None and b is not None else None
            usage['token_measurement_source']='groq.response.usage' if usage.get('input_tokens') is not None else None
        assert pool.fingerprint()==before
        d.update(initialisation_ms=self.initialisation_ms,initialised_lazily_inside_execute=lazy,context_ms=context_ms,pass_through_hashes={s:v['sha256'] for s,v in data['pass_through'].items()},
            candidate_hash=before,selected_paper_ids=paper_ids,graph_budget=budget,
            selected_node_count=len(selected_nodes),selected_edge_count=len(d['selected_edges']),
            graph_conflict_overlay_ids=[e.evidence_id for e in overlays],context_characters=len(context))
        unique={e.evidence_id:e for e in incoming}
        reference=Manager(Options(method='CM-B0',budget=budget)).manage(pool,request.question).serialized_context
        reference+='\n'+overlay_text if overlay_text else ''
        reference=assemble(data['pass_through'],data['sources'],reference)
        import tiktoken
        count=len(tiktoken.get_encoding('o200k_harmony').encode(context,disallowed_special=()))
        return SystemOutput(errors=errors,answer=raw,answer_ids=ids,ranked_paper_ids=tuple(dict.fromkeys(paper_ids)),
            evidence=tuple(unique.values()),context=context,retained_evidence_ids=tuple(dict.fromkeys(retained)),
            context_tokens=count,tokenizer='tiktoken-0.12.0:o200k_harmony',
            baseline_context_characters=len(reference),baseline_context_source='rq1-compliance-v1:CM-B0:'+before,
            diagnostics=canonical_json(d),observation=Observation(retrieval_ms=0.,retrieval_calls=0,tool_calls=0,**usage))
