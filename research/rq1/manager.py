"""All variants consume an immutable Pool; no retriever or store is accessible here."""
import json,time
from research.common.contracts import ContextPackage,EvidenceItem,Provenance
from research.common.serialization import canonical_json
from .contracts import Options
from .graph import semantic_order,expand,mst,dfs,components
from .pcst import select_pcst
from .diffusion import diffuse

def node_text(n):return canonical_json({'node_id':n.node_id,'node_type':n.node_type,'label':n.label,'evaluation_overlay':n.overlay})
def edge_text(e):return canonical_json({'source':e.source,'target':e.target,'relation':e.relation,'edge_id':e.edge_id,'derived_inverse':e.derived_inverse,'evaluation_overlay':e.overlay})
def evidence(pool):
    result=[]
    for n in pool.nodes:
        result.append(EvidenceItem(evidence_id=f'node:{n.node_id}',source_type='graph',canonical_id=f'stark:{n.node_id}',content=node_text(n),score=n.relevance or 0.,provenance=(Provenance(dataset_version='MMG-STaRK-MAG-v1',source_id=str(n.node_id),locator='graph/nodes.parquet'),)))
    for e in pool.edges:
        result.append(EvidenceItem(evidence_id='edge:'+e.key,source_type='graph',canonical_id=f'stark:{e.source}',content=edge_text(e),score=e.relevance,provenance=(Provenance(dataset_version='MMG-STaRK-MAG-v1',source_id=str(e.edge_id),locator='graph/adjacency'),)))
    return tuple(result)

def serialize(pool,order,keys,budget,parents=None):
    nodes={n.node_id:n for n in pool.nodes};edges={e.key:e for e in pool.edges};parents=parents or {}
    parts=[];included=[];chosen=set();used=set();size=0
    for node in order:
        if node in chosen:continue
        parent=parents.get(node);unit=[(f'node:{node}',node_text(nodes[node]))]
        if parent:
            e=edges[parent];other=e.target if e.source==node else e.source
            if other not in chosen:continue
            unit.append(('edge:'+parent,edge_text(e)))
        block='\n'.join(t for _,t in unit);extra=len(block)+(1 if parts else 0)
        if size+extra>budget:continue
        parts.append(block);size+=extra;chosen.add(node);included.extend(k for k,_ in unit)
        if parent:used.add(parent)
    for key in keys:
        if key in used:continue
        e=edges[key]
        if e.source not in chosen or e.target not in chosen:continue
        text=edge_text(e);extra=len(text)+(1 if parts else 0)
        if size+extra<=budget:parts.append(text);size+=extra;included.append('edge:'+key);used.add(key)
    return '\n'.join(parts),tuple(included),list(dict.fromkeys(n for n in order if n in chosen)),sorted(used)

class Manager:
    def __init__(self,options,reranker=None,solver=None):self.options=options;self.reranker=reranker;self.solver=solver;self.diagnostics={}
    def manage(self,pool,query):
        if query!=pool.question:raise ValueError('Query differs from frozen candidate pool')
        o=self.options;start=time.perf_counter();parents={};extra={'fallback':False};all_ids=[n.node_id for n in pool.nodes];all_keys=[e.key for e in pool.edges]
        if o.method=='CM-B0':order,keys=all_ids,all_keys
        elif o.method=='CM-B1':
            nodes={n.node_id:n for n in pool.nodes};edges={e.key:e for e in pool.edges}
            papers=[n.node_id for n in pool.nodes if n.node_type=='paper' and n.depth<=o.fixed_depth][:o.top_k];chosen=set(papers)
            for n in papers:
                seen=set()
                while nodes[n].parent_edge:
                    if n in seen:raise ValueError('Parent cycle')
                    seen.add(n);e=edges[nodes[n].parent_edge];n=e.source if e.target==n else e.target;chosen.add(n)
            keys=sorted({nodes[n].parent_edge for n in chosen if nodes[n].parent_edge})
            order,parents=dfs(pool,chosen,keys,pool.seeds);extra['fixed_paper_limit']=o.top_k
        elif o.method=='CM-01':
            seeds=semantic_order(pool)[:o.k_seed];chosen=expand(pool,seeds,o.expansion);keys=mst(pool,chosen);groups=components(pool,chosen,keys)
            sequences=[];parent_maps=[];texts=[]
            for group in groups:
                root=next((n for n in semantic_order(pool) if n in group),min(group));seq,par=dfs(pool,group,keys,[root]);sequences.append(seq);parent_maps.append(par)
                texts.append('\n'.join(node_text(next(n for n in pool.nodes if n.node_id==i)) for i in seq))
            if texts and self.reranker is None:raise ValueError('CM-01 requires the explicitly identified cross-encoder')
            scores=list(self.reranker(query,texts)) if texts else []
            import math
            if len(scores)!=len(texts) or not all(math.isfinite(float(s)) for s in scores):raise ValueError('Invalid cross-encoder scores')
            ranks=sorted(range(len(groups)),key=lambda i:(-scores[i],min(groups[i])))
            order=[n for i in ranks for n in sequences[i]];parents={n:p for i in ranks for n,p in parent_maps[i].items()}
            extra['reranker_truncated_components']=getattr(self.reranker,'truncations',None)
            extra.update(seed_count=len(seeds),components=len(groups),mst_edges=keys,component_scores=scores,rerank_unit='DFS-organized component',deduplication=True)
        elif o.method=='CM-02':
            chosen,keys,extra=select_pcst(pool,o,self.solver);order,parents=dfs(pool,chosen,keys,[n for n in semantic_order(pool) if n in chosen])
        else:
            order,keys,extra=diffuse(pool,o)
        text,included,selected,selected_edges=serialize(pool,order,keys,o.budget,parents)
        before=serialize(pool,all_ids,all_keys,o.budget)[0]
        self.diagnostics={**extra,'method':o.method,'candidate_hash':pool.fingerprint(),'candidate_nodes':len(pool.nodes),'candidate_edges':len(pool.edges),'selected_nodes':selected,'selected_edges':selected_edges,'selected_node_count':len(selected),'selected_edge_count':len(selected_edges),'context_ms':(time.perf_counter()-start)*1000,'raw_reference_characters':len(before),'budget':o.budget,'selected_paper_ids':[n for n in selected if next(x for x in pool.nodes if x.node_id==n).node_type=='paper']}
        return ContextPackage(query_id=pool.query_id,serialized_context=text,included_evidence_ids=included,token_count=None,character_count=len(text),byte_count=len(text.encode('utf-8')),method_id=o.method)
