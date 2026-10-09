"""Small candidate-graph utilities; never reads a dataset or constructs a full graph."""
from collections import deque

def adjacency(pool,chosen=None,edge_keys=None):
    chosen=set(n.node_id for n in pool.nodes) if chosen is None else set(chosen)
    result={n:[] for n in sorted(chosen)}
    for e in pool.edges:
        if e.source in chosen and e.target in chosen and (edge_keys is None or e.key in edge_keys) and e.source!=e.target:
            result[e.source].append((e.target,e.key));result[e.target].append((e.source,e.key))
    return {n:sorted(v) for n,v in result.items()}

def components(pool,chosen=None,edge_keys=None):
    adj=adjacency(pool,chosen,edge_keys);seen=set();groups=[]
    for root in adj:
        if root in seen:continue
        pending=[root];group=[];seen.add(root)
        while pending:
            n=pending.pop();group.append(n)
            for other,_ in adj[n]:
                if other not in seen:seen.add(other);pending.append(other)
        groups.append(sorted(group))
    return groups

def semantic_order(pool):
    return [n.node_id for n in sorted((n for n in pool.nodes if n.relevance is not None),key=lambda n:(-n.relevance,n.node_id))]

def mst(pool,chosen):
    chosen=set(chosen);parent={n:n for n in chosen}
    def find(n):
        while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
        return n
    result=[]
    for e in sorted(pool.edges,key=lambda e:(e.mst_cost,min(e.source,e.target),max(e.source,e.target),e.key)):
        if e.source not in chosen or e.target not in chosen:continue
        a,b=find(e.source),find(e.target)
        if a!=b:parent[a]=b;result.append(e.key)
    return result

def dfs(pool,chosen,edge_keys=None,roots=None):
    adj=adjacency(pool,chosen,edge_keys);seen=set();order=[];parents={}
    for root in list(roots or [])+sorted(adj):
        if root not in adj or root in seen:continue
        stack=[(root,None)]
        while stack:
            node,parent=stack.pop()
            if node in seen:continue
            seen.add(node);order.append(node)
            if parent:parents[node]=parent
            for other,key in reversed(adj[node]):
                if other not in seen:stack.append((other,key))
    return order,parents

def expand(pool,seeds,depth):
    adj=adjacency(pool);seen=set(seeds);front=set(seeds)
    for _ in range(depth):
        front={n for u in front for n,_ in adj[u]}-seen;seen|=front
    return seen
