"""Frozen RQ1 controls and immutable graph-only candidate contracts."""
from typing import Literal
from pydantic import Field,model_validator
from research.common.contracts import Contract
from research.common.serialization import content_hash

METHODS=('CM-B0','CM-B1','CM-01','CM-02','CM-03')
class Options(Contract):
    method: Literal['CM-B0','CM-B1','CM-01','CM-02','CM-03']
    budget: int=Field(default=24000,ge=1)
    top_k: int=Field(default=5,ge=1)
    fixed_depth: int=Field(default=2,ge=0)
    k_seed: int=Field(default=10,ge=1)
    expansion: int=Field(default=1,ge=0)
    k_node: int=Field(default=3,ge=1)
    k_edge: int=Field(default=5,ge=1)
    edge_cost: float=Field(default=.5,ge=0)
    n_seed: int=Field(default=20,ge=1)
    alpha: float=Field(default=10,gt=0)
    sink_capacity: float=Field(default=1,gt=0)
    support_threshold: float=Field(default=.01,ge=0)
    epsilon: float=Field(default=.05,gt=0)
    max_iterations: int=Field(default=1000000,ge=1)

class Node(Contract):
    node_id:int=Field(ge=0)
    label:str|None
    node_type:Literal['paper','author','institution','field_of_study']
    relevance:float|None=None
    vector:tuple[float,...]|None=None
    depth:int=Field(default=0,ge=0)
    parent_edge:str|None=None
    overlay:bool=False
    @model_validator(mode='after')
    def missing(self):
        if self.label is None and (self.relevance is not None or self.vector is not None):raise ValueError('Missing names have no semantic representation')
        if self.vector is not None and (not self.vector or abs(sum(v*v for v in self.vector)-1)>1e-4):raise ValueError('Vectors must be normalized')
        return self

class Edge(Contract):
    key:str
    source:int=Field(ge=0)
    target:int=Field(ge=0)
    relation:str
    edge_id:int=Field(ge=0)
    derived_inverse:bool=False
    relevance:float=0
    mst_cost:float=Field(default=1,ge=0)
    overlay:bool=False

class Pool(Contract):
    query_id:str
    question:str
    nodes:tuple[Node,...]
    edges:tuple[Edge,...]
    seeds:tuple[int,...]=()
    boundary:str
    overlay_hash:str|None=None
    provenance:str='{}'
    @model_validator(mode='after')
    def valid(self):
        ids={n.node_id for n in self.nodes}
        if len(ids)!=len(self.nodes) or len({e.key for e in self.edges})!=len(self.edges):raise ValueError('Duplicate candidate IDs')
        if len(self.nodes)>320 or len(self.edges)>1536:raise ValueError('Candidate safety cap exceeded')
        if not set(self.seeds)<=ids:raise ValueError('Seed outside boundary')
        if any(e.source not in ids or e.target not in ids for e in self.edges):raise ValueError('Edge outside boundary')
        if any(n.parent_edge is not None and n.parent_edge not in {e.key for e in self.edges} for n in self.nodes):raise ValueError('Unknown parent edge')
        return self
    def fingerprint(self):
        import json
        from research.common.serialization import canonical_json
        data=self.model_dump(mode='json');provenance=json.loads(data['provenance']);provenance.pop('common_candidate_build_ms',None)
        data['provenance']=canonical_json(provenance)
        return content_hash(data)
