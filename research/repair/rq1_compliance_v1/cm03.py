"""Phase1D keyword-scored flow diffusion; current support survives nonconvergence.

Hybrid Eq.(2c), supplied QAFD paper p4; a=1,b=1/4 from p9.
No semantic substitution on infeasibility, iteration limit or empty support.
"""
import json
from pathlib import Path
import numpy as np
from research.common.serialization import content_hash,canonical_json

KEYWORD_PROMPT = ('Extract the query keywords and concepts needed to identify relevant graph entities. '
    'Use only concepts explicitly expressed in the query. Do not answer the query or add facts. '
    'Return strict JSON with exactly one key, keywords, containing a list of strings.')

def keywords(query_id,query,root,call):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    binding=content_hash({'query_id':query_id,'query':query,'prompt':KEYWORD_PROMPT})
    path=root/(content_hash(query_id)+'.json')
    if path.exists():
        row=json.loads(path.read_text(encoding='utf-8'))
        if row['binding']!=binding:raise ValueError('Keyword cache identity mismatch')
        return tuple(row['keywords'])
    raw=call(KEYWORD_PROMPT,query)
    obj=json.loads(raw)
    if not isinstance(obj,dict) or set(obj)!={'keywords'} or not isinstance(obj['keywords'],list) or any(not isinstance(s,str) or not s.strip() for s in obj['keywords']):raise ValueError('Invalid keyword JSON')
    words=tuple(dict.fromkeys(s.strip() for s in obj['keywords']))
    with path.open('x',encoding='utf-8') as f:f.write(canonical_json({'binding':binding,'keywords':words,'raw':raw}))
    return words

def keyword_scores(pool,words,encode):
    if not words:return {}
    vectors=np.asarray(encode(list(words)),dtype=float)
    norms=np.linalg.norm(vectors,axis=1)
    if not np.isfinite(vectors).all() or np.any(norms==0):raise ValueError('Invalid keyword embedding')
    vectors=vectors/norms[:,None]
    return {n.node_id:float(np.max(vectors@np.asarray(n.vector))) for n in pool.nodes if n.vector is not None}

def hybrid(a,b,query):
    if a is None or b is None:return 0. # Missing semantics supply no semantic conductance.
    a,b,q=map(lambda v:np.asarray(v,dtype=float),(a,b,query))
    # Pinned official implementation defines Hsim=(cos+1)/2 for edge
    # conductance. Keyword seed ranking still uses raw cosine, per Phase1D.
    def hsim(u,v):
        denominator=np.linalg.norm(u)*np.linalg.norm(v)
        if denominator==0:return 0.
        return max(0.,(float(np.clip(u@v/denominator,-1,1))+1.)/2.)
    value=hsim(a,b)*(1.+.25*(hsim(a,q)+hsim(b,q)))
    if not np.isfinite(value):raise ValueError('Nonfinite hybrid conductance')
    return value

def diffuse(pool,seed_scores,weight,*,max_iterations=1_000_000,alpha=10.,epsilon=.05):
    ids=sorted(n.node_id for n in pool.nodes);ix={n:i for i,n in enumerate(ids)}
    if not seed_scores:
        fallback=sorted((n for n in pool.nodes if n.relevance is not None),key=lambda n:(-n.relevance,n.node_id))[:20]
        return [n.node_id for n in fallback],[],{'fallback':'semantic_nodes','convergence':None,'iterations':0,'x':{}}
    seeds=sorted(seed_scores,key=lambda n:(-seed_scores[n],n))[:20]
    adj={n:[] for n in ids}
    for e in pool.edges:
        if e.source!=e.target:adj[e.source].append((e.target,e));adj[e.target].append((e.source,e))
    mass=np.zeros(len(ids));x=np.zeros(len(ids))
    for n in seeds:mass[ix[n]]=alpha
    initial=float(mass.sum());weights={};explored=set(seeds);iterations=0;converged=False
    for step in range(max_iterations):
        excess=np.maximum(0.,mass-1.)
        if float(excess.sum())<=epsilon:converged=True;break
        i=int(np.argmax(excess));node=ids[i];out=[]
        for other,e in sorted(adj[node],key=lambda pair:(pair[0],pair[1].key)):
            if e.key not in weights:weights[e.key]=float(weight(e))
            w=weights[e.key]
            if not np.isfinite(w) or w<0:raise ValueError('Invalid conductance')
            if w>0:out.append((other,w));explored.add(other)
        total=sum(w for _,w in out)
        if total>0:
            amount=float(excess[i]);x[i]+=amount/total;mass[i]=1.
            for other,w in out:mass[ix[other]]+=amount*w/total
        iterations=step+1
    remaining=float(np.maximum(0.,mass-1.).sum());converged=remaining<=epsilon
    chosen=sorted((n for n in ids if x[ix[n]]>.01),key=lambda n:(-x[ix[n]],n))
    keys=[e.key for e in pool.edges if e.source in chosen and e.target in chosen]
    return chosen,keys,{'fallback':None,'convergence':converged,'iterations':iterations,
        'reason':'converged' if converged else 'N_max','seed_ids':seeds,'injected_mass':initial,
        'remaining_excess':remaining,'mass_error':abs(float(mass.sum())-initial),
        'x':{n:float(x[ix[n]]) for n in chosen},'explored_nodes':sorted(explored),
        'edge_weights':weights,'support_threshold':.01,'support_normalization':None,'timeout':False}

def serialize_support(pool,chosen,keys,diagnostics,budget):
    """Keep induced support; connect reachable support through explored nodes.

    Budget pruning removes lowest-x peripheral evidence while preserving each
    connected component; x=0 connectors are explicitly distinguished from support.
    """
    from collections import deque
    from research.rq1.graph import components
    from research.rq1.manager import node_text,edge_text
    nodes={n.node_id:n for n in pool.nodes};edges={e.key:e for e in pool.edges}
    if diagnostics.get('fallback')=='semantic_nodes':
        kept=[];lines=[]
        for n in chosen:
            line=node_text(nodes[n])
            if len('\n'.join(lines+[line]))<=budget:lines.append(line);kept.append(n)
        return '\n'.join(lines),kept,[],{**diagnostics,'connector_nodes':[],'pruned_nodes':[n for n in chosen if n not in kept]}
    support=set(chosen);selected=set(chosen);keys=set(keys)
    explored=set(diagnostics.get('explored_nodes',chosen));connectors=set()
    adj={n:[] for n in explored}
    for e in pool.edges:
        if e.source in explored and e.target in explored and e.source!=e.target:
            adj[e.source].append((e.target,e.key));adj[e.target].append((e.source,e.key))
    groups=components(pool,selected,keys)
    while len(groups)>1:
        connected=set(groups[0]);targets=selected-connected;queue=deque((n,[]) for n in sorted(connected));seen=set(connected);path=None
        while queue and path is None:
            n,p=queue.popleft()
            for v,k in sorted(adj.get(n,())):
                if v in seen:continue
                seen.add(v);next_path=p+[(v,k)]
                if v in targets:path=next_path;break
                queue.append((v,next_path))
        if path is None:break
        for n,k in path:
            selected.add(n);keys.add(k)
            if n not in support:connectors.add(n)
        # The retained graph is induced over support plus necessary connectors.
        keys|={e.key for e in pool.edges if e.source in selected and e.target in selected}
        groups=components(pool,selected,keys)
    x=diagnostics.get('x',{});removed=[]
    while selected:
        order=sorted(selected,key=lambda n:(-x.get(n,0.),n))
        lines=[]
        for n in order:
            obj=json.loads(node_text(nodes[n]));obj['connector']=n in connectors;lines.append(canonical_json(obj))
        lines += [edge_text(edges[k]) for k in sorted(keys)]
        text='\n'.join(lines)
        if len(text)<=budget:return text,order,sorted(keys),{**diagnostics,'connector_nodes':sorted(connectors & selected),'pruned_nodes':removed}
        before=len(components(pool,selected,keys));eligible=[]
        for n in selected:
            new=selected-{n};newkeys={k for k in keys if n not in (edges[k].source,edges[k].target)}
            if not new or len(components(pool,new,newkeys))<=before:eligible.append(n)
        n=min(eligible,key=lambda n:(x.get(n,0.),n))
        selected.remove(n);keys={k for k in keys if n not in (edges[k].source,edges[k].target)};removed.append(n)
    return '',[],[],{**diagnostics,'connector_nodes':[],'pruned_nodes':removed}
