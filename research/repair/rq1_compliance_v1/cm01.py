"""KG²RAG-inspired organization of graph-native relation provenance units.

Dataset adaptation, NOT an exact KG²RAG reproduction. No store/retriever/gold
interface is available. Encoder and reranker consume graph-only strings.
"""
from dataclasses import dataclass, asdict
import math
import numpy as np
from research.common.serialization import canonical_json

OFFICIAL_EDGES = 19_919_698
TYPES = {
    'AUTHOR-WRITES-PAPER': ('author', 'paper'),
    'AUTHOR-AFFILIATED_WITH-INSTITUTION': ('author', 'institution'),
    'PAPER-CITES-PAPER': ('paper', 'paper'),
    'PAPER-HAS_TOPIC-FIELD_OF_STUDY': ('paper', 'field_of_study'),
}


@dataclass(frozen=True)
class GraphProvenanceUnit:
    unit_id: str
    canonical_edge_id: int
    relation_type: str
    source_node_id: int
    target_node_id: int
    source_node_type: str
    target_node_type: str
    source_label: str | None
    target_label: str | None
    serialization: str
    derived_inverse: bool
    canonical_official_edge_id: int
    provenance: tuple[tuple[str, int, bool], ...]

    def triplet(self):
        # Labels remain NULL in the object; the ID is an identifier, not a name.
        return canonical_json({'source': self.source_label if self.source_label is not None else f'stark:{self.source_node_id}',
            'relation': self.relation_type,
            'target': self.target_label if self.target_label is not None else f'stark:{self.target_node_id}'})

    def context_line(self):
        return canonical_json({'evidence_id': self.unit_id, 'content': self.serialization,
            'relation': self.relation_type, 'source_id': self.source_node_id,
            'target_id': self.target_node_id, 'canonical_official_edge_id': self.canonical_official_edge_id,
            'provenance': self.provenance})


def canonical_units(pool, official_edges=OFFICIAL_EDGES):
    """Phase3 inverse edge_id = source_edge_id + official edge count.

    Preserve every observed traversal record; one semantic unit per official
    relation. An inverse-only observation is oriented back to official direction.
    """
    nodes={n.node_id:n for n in pool.nodes}
    grouped={}
    for e in pool.edges:
        eid=e.edge_id-official_edges if e.derived_inverse else e.edge_id
        if not 0 <= eid < official_edges: raise ValueError('Invalid official relation identity')
        s,t=(e.target,e.source) if e.derived_inverse else (e.source,e.target)
        if e.relation not in TYPES: raise ValueError('Nonofficial relation')
        a,b=nodes[s],nodes[t]
        if (a.node_type,b.node_type)!=TYPES[e.relation]: raise ValueError('Relation endpoint type mismatch')
        signature=(e.relation,s,t)
        if eid in grouped and grouped[eid][0]!=signature: raise ValueError('Conflicting canonical edge identity')
        grouped.setdefault(eid,(signature,[]))[1].append((e.key,e.edge_id,e.derived_inverse))
    result=[]
    for eid,((relation,s,t),observed) in sorted(grouped.items()):
        a,b=nodes[s],nodes[t]
        left=a.label if a.label is not None else f'stark:{s}'
        right=b.label if b.label is not None else f'stark:{t}'
        templates={
            'AUTHOR-WRITES-PAPER': f'Author {left} writes Paper {right}.',
            'AUTHOR-AFFILIATED_WITH-INSTITUTION': f'Author {left} is affiliated with Institution {right}.',
            'PAPER-CITES-PAPER': f'Paper {left} cites Paper {right}.',
            'PAPER-HAS_TOPIC-FIELD_OF_STUDY': f'Paper {left} has topic {right}.',
        }
        result.append(GraphProvenanceUnit(f'graph:official:{eid:08d}',eid,relation,s,t,a.node_type,b.node_type,
            a.label,b.label,templates[relation],False,eid,tuple(sorted(set(observed)))))
    return tuple(result)


def cosine_scores(query,units,encode):
    if not units:return {}
    q=np.asarray(encode([query]),dtype=np.float64)[0]
    if not np.isfinite(q).all() or np.linalg.norm(q)==0:raise ValueError('Invalid query vector')
    result={}
    for offset in range(0,len(units),32):
        batch=units[offset:offset+32]
        vectors=np.asarray(encode([u.serialization for u in batch]),dtype=np.float64)
        if len(vectors)!=len(batch):raise ValueError('Embedding count mismatch')
        for u,v in zip(batch,vectors):
            if not np.isfinite(v).all() or np.linalg.norm(v)==0:raise ValueError('Invalid relation vector')
            result[u.unit_id]=float(np.clip(q@v/(np.linalg.norm(q)*np.linalg.norm(v)),-1,1))
    return result


def maximum_forest(units,scores):
    """Literal maximum-weight Kruskal; ties by canonical unit ID."""
    parent={n:n for u in units for n in (u.source_node_id,u.target_node_id)}
    def find(n):
        while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
        return n
    chosen=[]
    for u in sorted(units,key=lambda u:(-scores[u.unit_id],u.unit_id)):
        a,b=find(u.source_node_id),find(u.target_node_id)
        if a!=b:parent[a]=b;chosen.append(u)
    return tuple(chosen)


def tree_sequences(tree,scores):
    adj={}
    for u in tree:
        adj.setdefault(u.source_node_id,[]).append((u.target_node_id,u))
        adj.setdefault(u.target_node_id,[]).append((u.source_node_id,u))
    pending=set(adj);result=[]
    while pending:
        group=set();stack=[min(pending)]
        while stack:
            n=stack.pop()
            if n in group:continue
            group.add(n);stack.extend(v for v,_ in adj[n])
        pending-=group
        edges=[u for u in tree if u.source_node_id in group]
        root_edge=min(edges,key=lambda u:(-scores[u.unit_id],u.unit_id))
        root=min(root_edge.source_node_id,root_edge.target_node_id)
        # Traverse the highest-weight edge first, then stable unit-ID adjacency.
        visited={root};sequence=[];stack=[(root,iter(sorted(adj[root],key=lambda x:(x[1]!=root_edge,x[1].unit_id,x[0]))))]
        while stack:
            _,it=stack[-1]
            try:n,u=next(it)
            except StopIteration:stack.pop();continue
            if n in visited:continue
            visited.add(n);sequence.append(u)
            stack.append((n,iter(sorted(adj[n],key=lambda x:(x[1].unit_id,x[0])))))
        result.append(tuple(sequence))
    return result


def organize(pool,query,budget,encode,rerank):
    if pool.question!=query:raise ValueError('Frozen query mismatch')
    if budget<0:raise ValueError('Negative graph budget')
    units=canonical_units(pool)
    scores=cosine_scores(query,units,encode)
    seeds=sorted(units,key=lambda u:(-scores[u.unit_id],u.unit_id))[:10]
    touched={n for u in seeds for n in (u.source_node_id,u.target_node_id)}
    # Relations incident to seed-touched entities are the one-hop expansion.
    expanded=tuple(u for u in units if u.source_node_id in touched or u.target_node_id in touched)
    forest=maximum_forest(expanded,scores)
    sequences=tree_sequences(forest,scores)
    triplets=['\n'.join(u.triplet() for u in seq) for seq in sequences]
    ranking=list(rerank(query,triplets)) if triplets else []
    if len(ranking)!=len(sequences) or any(not math.isfinite(float(s)) for s in ranking):raise ValueError('Invalid reranker scores')
    order=sorted(range(len(sequences)),key=lambda i:(-ranking[i],min(u.unit_id for u in sequences[i])))
    fallback=None
    if not units:fallback='no_graph_relation_evidence';ordered=[]
    elif not forest:fallback='graph_semantic_units';ordered=seeds
    else:ordered=[u for i in order for u in sequences[i]]
    kept=[];lines=[];seen=set();size=0
    for u in ordered:
        if u.unit_id in seen:continue
        seen.add(u.unit_id);line=u.context_line();extra=len(line)+(1 if lines else 0)
        if size+extra>budget:continue
        lines.append(line);kept.append(u);size+=extra
    diagnostics={'adaptation':'native-graph-provenance-units-v1','candidate_hash':pool.fingerprint(),
        'candidate_unit_count':len(units),'k_seed':10,'m_hops':1,'seed_ids':[u.unit_id for u in seeds],
        'scores':scores,'expanded_unit_ids':[u.unit_id for u in expanded],
        'tree_unit_ids':[u.unit_id for u in forest],'reranker_triplets':triplets,
        'tree_scores':ranking,'reranker_truncated_pairs':getattr(rerank,'truncations',None),
        'dfs_sequences':[[u.unit_id for u in seq] for seq in sequences],
        'selected_unit_ids':[u.unit_id for u in kept],'fallback':fallback,
        'traversal_provenance':{u.unit_id:u.provenance for u in units},'additional_retrieval_calls':0}
    return '\n'.join(lines),tuple(kept),diagnostics
