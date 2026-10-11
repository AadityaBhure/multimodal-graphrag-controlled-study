"""Exact edge-rank PCST prizes, BFS ordering and contribution leaf pruning."""
from collections import deque
import numpy as np
from research.rq1.graph import components
from research.rq1.manager import node_text,edge_text

def rank_prizes(scores,k):
    result={key:0. for key in scores}
    for rank,key in enumerate(sorted(scores,key=lambda n:(-scores[n],n))[:k]):result[key]=float(k-rank)
    return result

def select(pool,node_scores,edge_scores,solver=None):
    if solver is None:
        from pcst_fast import pcst_fast
        solver=pcst_fast
    ids=sorted(n.node_id for n in pool.nodes);ix={n:i for i,n in enumerate(ids)}
    if not ids:return [],[],{'fallback':None,'node_prizes':{},'edge_prizes':{}}
    npz=rank_prizes(node_scores,3);epz=rank_prizes(edge_scores,5)
    p=[npz.get(n,0.) for n in ids];se=[];cost=[];mapping=[]
    for e in sorted(pool.edges,key=lambda e:e.key):
        if e.source==e.target:continue
        a,b=ix[e.source],ix[e.target];prize=epz.get(e.key,0.)
        if prize<=.5:se.append((a,b));cost.append(.5-prize);mapping.append(e.key)
        else:
            virtual=len(p);p.append(prize-.5)
            se.extend(((a,virtual),(virtual,b)));cost.extend((0.,0.));mapping.extend((e.key,e.key))
    vertices,edges=solver(np.asarray(se,dtype=np.int64).reshape(-1,2),np.asarray(p,dtype=np.float64),np.asarray(cost,dtype=np.float64),-1,1,'gw',0)
    if any(int(v)<0 or int(v)>=len(p) for v in vertices) or any(int(e)<0 or int(e)>=len(mapping) for e in edges):raise ValueError('Invalid solver indices')
    chosen={ids[int(v)] for v in vertices if int(v)<len(ids)};keys={mapping[int(e)] for e in edges}
    for e in pool.edges:
        if e.key in keys:chosen.update((e.source,e.target))
    info={'fallback':None,'node_prizes':npz,'edge_prizes':epz,'edge_cost':.5}
    if not chosen:
        if not node_scores:raise ValueError('Empty PCST and no semantically represented node for prescribed fallback')
        chosen={min(node_scores,key=lambda n:(-node_scores[n],n))};keys=set();info['fallback']='highest_node'
    if len(components(pool,chosen,keys))!=1:raise ValueError('PCST returned disconnected graph; not an empty-result fallback')
    return sorted(chosen),sorted(keys),info

def bfs(pool,chosen,keys,prizes):
    adj={n:[] for n in chosen}
    for e in pool.edges:
        if e.key in keys:adj[e.source].append((e.target,e.key));adj[e.target].append((e.source,e.key))
    if not chosen:return [],[]
    root=min(chosen,key=lambda n:(-prizes.get(n,0.),n));queue=deque([root]);seen={root};order=[];edge_order=[]
    while queue:
        n=queue.popleft();order.append(n)
        for v,k in sorted(adj[n]):
            if k not in edge_order:edge_order.append(k)
            if v not in seen:seen.add(v);queue.append(v)
    if seen!=set(chosen):raise ValueError('Disconnected serialization')
    return order,edge_order

def serialize_pruned(pool,chosen,keys,info,budget):
    nodes={n.node_id:n for n in pool.nodes};edges={e.key:e for e in pool.edges}
    chosen=set(chosen);keys=set(keys);removed=[]
    def render():
        order,eo=bfs(pool,chosen,keys,info['node_prizes'])
        return '\n'.join([node_text(nodes[n]) for n in order]+[edge_text(edges[k]) for k in eo]),order,eo
    while chosen:
        text,order,eo=render()
        if len(text)<=budget:return text,order,eo,{**info,'pruned_leaves':removed}
        degree={n:[] for n in chosen}
        for k in keys:
            e=edges[k];degree[e.source].append(k);degree[e.target].append(k)
        leaves=[n for n in chosen if len(degree[n])<=1]
        if not leaves:raise ValueError('Budget pruning requires PCST leaf structure')
        def contribution(n):
            return info['node_prizes'].get(n,0.)+sum(info['edge_prizes'].get(k,0.)-.5 for k in degree[n])
        leaf=min(leaves,key=lambda n:(contribution(n),n));removed.append({'node_id':leaf,'net_contribution':contribution(leaf)})
        chosen.remove(leaf);keys-=set(degree[leaf])
    return '',[],[],{**info,'pruned_leaves':removed,'empty_due_to_budget':True}
