"""Fixed modality-local retrievers with deterministic traversal budgets."""
from collections import deque
from research.common.contracts import EvidenceItem,Provenance
from research.common.serialization import canonical_json
from research.baselines.structured import parse_question

RELATIONS={0:'AUTHOR-AFFILIATED_WITH-INSTITUTION',1:'PAPER-CITES-PAPER',2:'PAPER-HAS_TOPIC-FIELD_OF_STUDY',3:'AUTHOR-WRITES-PAPER'}


def evidence(store,source,paper,payload,score=0.):
    return EvidenceItem(evidence_id=f'{source}:paper:{paper}',source_type=source,canonical_id=f'stark:{paper}',
        payload=canonical_json(payload),score=score,provenance=(Provenance(dataset_version=store.manifest['dataset_version'],
            source_id=str(paper),locator={'text':'text/text_documents.parquet','graph':'graph/adjacency + graph/nodes.parquet','structured':'structured/stark_mag.duckdb:papers_structured'}[source]),),
        metadata=canonical_json({'stark_node_id':paper,'representation_manifest_sha256':store.manifest_hash}))


def text_retrieve(store,question,options):
    ranked=store.text_search(question,options.top_k)
    rows=store.texts([paper for paper,_ in ranked])
    return tuple(evidence(store,'text',paper,rows[paper],score) for paper,score in ranked),{'status':'ok','ranking':'frozen normalized MiniLM inner product'}


def graph_retrieve(store,question,options):
    seeds=store.seed_nodes(question)
    queue=deque((seed['node_id'],[],i) for i,seed in enumerate(seeds))
    visited=set();paths={};scanned=0;truncated=False;csr=store.csr
    while queue and scanned<options.max_edges and len(visited)<options.max_nodes:
        node,path,seed_order=queue.popleft()
        if node in visited:continue
        visited.add(node);paths[node]=(path,seed_order)
        if len(path)>=options.graph_depth:continue
        a,z=map(int,csr['indptr'][node:node+2]);end=min(z,a+options.per_node_edges)
        truncated |= end<z
        for pos in range(a,end):
            if scanned>=options.max_edges or len(queue)+len(visited)>=options.max_nodes:
                truncated=True;break
            scanned+=1
            target=int(csr['neighbors'][pos]);relation=int(csr['relation_ids'][pos])
            if relation not in RELATIONS:raise ValueError('Unexpected source relation')
            if target in visited:continue
            edge={'source':node,'target':target,'edge_id':int(csr['edge_ids'][pos]),'relation':RELATIONS[relation],
                  'derived_inverse':bool(csr['derived_inverse'][pos])}
            queue.append((target,path+[edge],seed_order))
    truncated |= bool(queue)
    nodes=store.nodes(sorted(paths))
    candidates=sorted((node for node in paths if nodes[node]['node_type']=='paper'),key=lambda n:(len(paths[n][0]),paths[n][1],n))[:options.top_k]
    results=[]
    for paper in candidates:
        path,seed_order=paths[paper]
        involved={paper}|{e['source'] for e in path}|{e['target'] for e in path}
        payload={'paper_id':paper,'title':nodes[paper]['label'],'path':path,'nodes':[nodes[n] for n in sorted(involved)],
                 'seed_node_id':seeds[seed_order]['node_id']}
        results.append(evidence(store,'graph',paper,payload,1/(1+len(path))))
    return tuple(results),{'status':'ok' if seeds else 'no_graph_seed','seeds':seeds,'visited_nodes':len(visited),
                           'scanned_edges':scanned,'truncated':truncated,'candidate_ids':candidates,
                           'ranking':'path length, seed rank, global node ID','global_text_fallback':False}


def structured_retrieve(store,question,options):
    plan,status=parse_question(question)
    if plan is None:return (),{'status':status,'plan':None}
    rows=store.structured(plan,options.top_k)
    # DATE values preserve source ISO dates; NULL remains None.
    rows=[{k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in row.items()} for row in rows]
    return tuple(evidence(store,'structured',r['paper_id'],r) for r in rows),{'status':status,'plan':plan.model_dump(),
            'ranking':'global node ID ascending','result_limit':options.top_k,'returned_rows':len(rows)}
