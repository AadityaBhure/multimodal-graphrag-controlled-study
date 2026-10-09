"""Official PCST solver, with edge-prize virtual-node reduction on bounded candidates."""
import numpy as np
from .graph import semantic_order,components

def select_pcst(pool,options,solver=None):
    if not pool.nodes:return [],[],{'fallback':False,'reason':'empty'}
    order=semantic_order(pool);fallback=order[:1] or [min(n.node_id for n in pool.nodes)]
    if not pool.edges or not order:return fallback,[],{'fallback':True,'reason':'no_edges_or_semantics'}
    if solver is None:
        from pcst_fast import pcst_fast
        solver=pcst_fast
    ids=sorted(n.node_id for n in pool.nodes);mapping={n:i for i,n in enumerate(ids)};prizes=np.zeros(len(ids))
    for rank,node in enumerate(order[:options.k_node]):prizes[mapping[node]]=min(options.k_node,len(order))-rank
    edge_prizes={e.key:0. for e in pool.edges};values=sorted({e.relevance for e in pool.edges},reverse=True)[:options.k_edge]
    ceiling=float(options.k_edge)
    for rank,value in enumerate(values):
        ties=[e for e in pool.edges if e.relevance==value];prize=min((len(values)-rank)/len(ties),ceiling)
        for e in ties:edge_prizes[e.key]=prize
        ceiling=prize*.99
    solver_edges=[];costs=[];orig=[];virtual={};p=list(prizes)
    for e in sorted(pool.edges,key=lambda e:e.key):
        if e.source==e.target:continue
        prize=edge_prizes[e.key];a,b=mapping[e.source],mapping[e.target]
        if prize<=options.edge_cost:
            solver_edges.append((a,b));costs.append(options.edge_cost-prize);orig.append(e.key)
        else:
            v=len(p);p.append(prize-options.edge_cost);virtual[v]=e.key
            solver_edges.extend([(a,v),(v,b)]);costs.extend([0.,0.]);orig.extend([e.key,e.key])
    if not solver_edges:return fallback,[],{'fallback':True,'reason':'no_nonself_edges'}
    # Fail closed on dependency/runtime errors; fallback is for an empty/invalid solution only.
    vertices,edges=solver(np.asarray(solver_edges,dtype=np.int64),np.asarray(p,dtype=np.float64),np.asarray(costs,dtype=np.float64),-1,1,'gw',0)
    if any(int(i)<0 or int(i)>=len(p) for i in vertices) or any(int(i)<0 or int(i)>=len(orig) for i in edges):raise ValueError('Invalid PCST indices')
    chosen={ids[int(i)] for i in vertices if int(i)<len(ids)};keys={orig[int(i)] for i in edges}
    for e in pool.edges:
        if e.key in keys:chosen.update((e.source,e.target))
    valid=bool(chosen) and len(components(pool,chosen,keys))==1
    info={'fallback':not valid,'reason':'ok' if valid else 'empty_or_disconnected_solution','solver':'pcst_fast-1.0.10','virtual_nodes':len(virtual),'node_prize_sum':float(sum(prizes)),'edge_cost':options.edge_cost,'adaptive_cost_reduction':False}
    return (sorted(chosen),sorted(keys),info) if valid else (fallback,[],info)
