"""Deterministic query-weighted excess-flow diffusion, bounded candidate adaptation."""
import numpy as np
from .graph import semantic_order,components

def diffuse(pool,options):
    ids=sorted(n.node_id for n in pool.nodes);ix={n:i for i,n in enumerate(ids)}
    if not ids:return [],[],{'fallback':False,'converged':True,'iterations':0,'reason':'empty'}
    order=semantic_order(pool);fallback=order[:options.top_k] or ids[:1];seeds=order[:options.n_seed]
    info={'fallback':False,'converged':False,'iterations':0,'seed_count':len(seeds),'reason':'ok','weight_scheme':'product_of_shifted_endpoint_cosines','support_normalization':'divide_by_max'}
    if not seeds:return fallback,[],{**info,'fallback':True,'reason':'no_semantic_seed'}
    scores={n.node_id:(n.relevance+1)/2 if n.relevance is not None else .5 for n in pool.nodes}
    adj=[{} for _ in ids]
    for e in pool.edges:
        if e.source==e.target:continue
        a,b=ix[e.source],ix[e.target];w=max(0.,scores[e.source])*max(0.,scores[e.target])
        if w>0:adj[a][b]=adj[a].get(b,0)+w;adj[b][a]=adj[b].get(a,0)+w
    mass=np.zeros(len(ids));support=np.zeros(len(ids))
    for n in seeds:mass[ix[n]]=options.alpha
    # Conservation proves convergence impossible when injected mass exceeds a component's sinks.
    for group in components(pool):
        injected=sum(mass[ix[n]] for n in group)
        if injected>(options.sink_capacity+options.epsilon)*len(group):
            return fallback,[],{**info,'fallback':True,'reason':'component_mass_exceeds_sink_capacity','injected_mass':float(mass.sum())}
    initial=float(mass.sum());iterations=0
    for iterations in range(options.max_iterations):
        excess=mass-options.sink_capacity;i=int(np.argmax(excess))
        if excess[i]<=options.epsilon:info['converged']=True;break
        total=sum(adj[i].values())
        if total<=0:info['reason']='stranded_excess';break
        amount=float(excess[i]);mass[i]-=amount;support[i]+=amount/total
        for j,w in sorted(adj[i].items()):mass[j]+=amount*w/total
    else:iterations=options.max_iterations;info['reason']='iteration_limit'
    info.update(iterations=iterations,remaining_excess=float(np.maximum(0,mass-options.sink_capacity).sum()),mass_error=abs(float(mass.sum())-initial))
    if not np.isfinite(support).all() or not np.isfinite(mass).all():raise ValueError('Nonfinite diffusion state')
    maximum=float(support.max())
    chosen=[ids[i] for i,v in enumerate(support) if maximum>0 and v/maximum>=options.support_threshold]
    if not info['converged'] or not chosen:
        return fallback,[],{**info,'fallback':True,'reason':info['reason'] if not info['converged'] else 'empty_support'}
    chosen.sort(key=lambda n:(-support[ix[n]],n));keys=[e.key for e in pool.edges if e.source in chosen and e.target in chosen]
    info['max_support']=maximum
    return chosen,keys,info
