"""Build common RQ1 candidate pools once, using only graph store access."""
from collections import deque
import json,time
import numpy as np
from research.common.serialization import canonical_json,content_hash
from research.baselines.retrieval import RELATIONS
from .contracts import Pool,Node,Edge
BOUNDARY={'id':'rq1-common-graph-v1','seed_source':'frozen B2 resolver output','depth':2,'base_nodes':256,'base_edges':1024,'per_node_edges':128,'overlay_nodes':320,'overlay_edges':1536,'overlay_graph_paths':5,'ordering':'seed order then CSR order; first discovery','semantic_model':'frozen MiniLM ONNX; labels only','edge_relevance':'mean of available endpoint query cosines; zero if both unavailable','mst_cost':'1 minus endpoint cosine; 1 if unavailable'}

def build_pool(store,query_id,question,seeds,overlay,source_record_hash):
    started=time.perf_counter();nodes={int(n):{'depth':0,'parent_edge':None,'overlay':False} for n in seeds};edges={};queue=deque(nodes);scanned=0;truncated=False
    def add(edge,is_overlay=False):
        key=f"{edge['edge_id']}:{int(edge['derived_inverse'])}:{edge['source']}:{edge['target']}"
        edges.setdefault(key,{**edge,'key':key,'overlay':is_overlay});return key
    while queue:
        n=queue.popleft();depth=nodes[n]['depth']
        if depth>=BOUNDARY['depth']:continue
        a,z=map(int,store.csr['indptr'][n:n+2]);end=min(z,a+BOUNDARY['per_node_edges']);truncated|=end<z
        for pos in range(a,end):
            if len(edges)>=BOUNDARY['base_edges']:truncated=True;break
            scanned+=1;t=int(store.csr['neighbors'][pos])
            if t not in nodes and len(nodes)>=BOUNDARY['base_nodes']:truncated=True;continue
            rid=int(store.csr['relation_ids'][pos]);edge={'source':n,'target':t,'edge_id':int(store.csr['edge_ids'][pos]),'relation':RELATIONS[rid],'derived_inverse':bool(store.csr['derived_inverse'][pos])}
            key=add(edge)
            if t not in nodes:nodes[t]={'depth':depth+1,'parent_edge':key,'overlay':False};queue.append(t)
    injected=0
    if overlay:
        obj=json.loads(overlay)
        if obj['kind']!='noisy':raise ValueError('RQ1 primary comparison permits normal/noisy only')
        for row in obj['distractors']['graph'][:BOUNDARY['overlay_graph_paths']]:
            for depth,e in enumerate(row.get('path',[])):
                fresh={e['source'],e['target']}-set(nodes)
                if len(nodes)+len(fresh)>BOUNDARY['overlay_nodes'] or len(edges)>=BOUNDARY['overlay_edges']:truncated=True;continue
                edge={k:e[k] for k in ('source','target','edge_id','derived_inverse')};edge['relation']=RELATIONS[e['relation_id']]
                key=add(edge,True)
                nodes.setdefault(e['source'],{'depth':depth,'parent_edge':None,'overlay':True})
                nodes.setdefault(e['target'],{'depth':depth+1,'parent_edge':key,'overlay':True});injected+=1
    rows=store.nodes(list(nodes));assert set(rows)==set(nodes)
    semantic=[i for i in nodes if rows[i]['label'] is not None];vectors={};scores={}
    qv=store.encode([question])[0]
    for i in range(0,len(semantic),32):
        batch=semantic[i:i+32];encoded=store.encode([rows[n]['label'] for n in batch])
        for n,v in zip(batch,encoded):vectors[n]=v;scores[n]=float(np.clip(v@qv,-1,1))
    ns=[Node(**rows[n],**nodes[n],relevance=scores.get(n),vector=tuple(map(float,vectors[n])) if n in vectors else None) for n in nodes]
    es=[]
    for e in edges.values():
        a,b=e['source'],e['target'];rs=[scores[n] for n in (a,b) if n in scores]
        sim=float(np.clip(vectors[a]@vectors[b],-1,1)) if a in vectors and b in vectors else 0.
        es.append(Edge(**e,relevance=sum(rs)/len(rs) if rs else 0.,mst_cost=1-sim))
    return Pool(query_id=query_id,question=question,nodes=tuple(ns),edges=tuple(es),seeds=tuple(seeds),boundary=content_hash(BOUNDARY),overlay_hash=content_hash(overlay) if overlay else None,
        provenance=canonical_json({'boundary':BOUNDARY,'representation_sha256':store.manifest_hash,'frozen_B2_record_sha256':source_record_hash,'graph_rows_scanned':scanned,'truncated':truncated,'overlay_path_rows_considered':injected,'common_candidate_build_ms':(time.perf_counter()-started)*1000,'retrieval_calls':1,'text_calls':0,'structured_calls':0}))
