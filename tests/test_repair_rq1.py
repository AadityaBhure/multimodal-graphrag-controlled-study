import numpy as np
import pytest
from research.repair.rq1_compliance_v1 import cm02,cm03
from research.repair.rq1_compliance_v1.context import pass_through,assemble
from research.rq1.contracts import Node,Edge,Pool
from research.common.contracts import EvidenceItem,Provenance

def pool():
    ns=tuple(Node(node_id=i,node_type='paper',label=str(i),relevance=1-i/10,vector=(1.,0.)) for i in range(7))
    es=tuple(Edge(key=str(i),edge_id=i,source=i,target=i+1,relation='PAPER-CITES-PAPER') for i in range(6))
    return Pool(query_id='fixture',question='query',nodes=ns,edges=es,boundary='synthetic')

def test_exact_rank_prizes_ties():
    prizes=cm02.rank_prizes({str(i):.5 for i in range(8)},5)
    assert list(prizes.values())==[5.,4.,3.,2.,1.,0.,0.,0.]

def test_pcst_connected_bfs_and_leaf_pruning():
    p=pool();nodes,keys,d=cm02.select(p,{i:1-i/10 for i in range(7)},{str(i):1-i/10 for i in range(6)})
    full,order,eo,_=cm02.serialize_pruned(p,nodes,keys,d,24000)
    small,remaining,remaining_edges,diag=cm02.serialize_pruned(p,nodes,keys,d,500)
    assert len(small)<=500 and diag['pruned_leaves']
    assert order[0]==0 and order==sorted(order)
    if remaining:
        from research.rq1.graph import components
        assert len(components(p,remaining,remaining_edges))==1

def test_pcst_disconnected_is_error_not_fallback():
    with pytest.raises(ValueError,match='disconnected'):
        cm02.select(pool(),{i:1 for i in range(7)},{str(i):1 for i in range(6)},lambda *args:([0,6],[]))

def test_keyword_cache_identity_and_max_cosine(tmp_path):
    calls=[]
    def call(*args):calls.append(args);return '{"keywords":["first","second"]}'
    a=cm03.keywords('q','question',tmp_path,call)
    assert cm03.keywords('q','question',tmp_path,call)==a and len(calls)==1
    with pytest.raises(ValueError):cm03.keywords('q','changed',tmp_path,call)
    scores=cm03.keyword_scores(pool(),a,lambda texts:np.array([[0.,1.],[1.,0.]]))
    assert all(s==1 for s in scores.values())

def test_hybrid_exact_formula():
    assert cm03.hybrid((1,0),(1,0),(1,0))==1.5
    assert cm03.hybrid(None,(1,0),(1,0))==0

def test_diffusion_current_support_at_limit_and_no_normalization():
    a=cm03.diffuse(pool(),{i:1 for i in range(7)},lambda e:1,max_iterations=3)
    assert a==cm03.diffuse(pool(),{i:1 for i in range(7)},lambda e:1,max_iterations=3)
    nodes,_,d=a
    assert d['fallback'] is None and not d['convergence'] and d['iterations']==3
    assert nodes and all(x>.01 for x in d['x'].values()) and max(d['x'].values())>1
    assert d['mass_error']<1e-10

def test_diffusion_convergence_and_only_missing_seed_fallback():
    _,_,d=cm03.diffuse(pool(),{0:1},lambda e:1,alpha=2,max_iterations=1000)
    assert d['convergence'] and d['fallback'] is None
    _,_,d=cm03.diffuse(pool(),{},lambda e:1)
    assert d['fallback']=='semantic_nodes'

def test_diffusion_weights_only_reachable_edges_and_connector_preservation():
    p=pool();calls=[]
    def weight(e):calls.append(e.key);return 1.
    _,_,d=cm03.diffuse(p,{0:1.},weight,max_iterations=1)
    assert calls==['0'] and d['explored_nodes']==[0,1]
    text,nodes,edges,diag=cm03.serialize_support(p,[0,2],[],
        {'x':{0:2.,2:1.},'explored_nodes':[0,1,2],'fallback':None},24000)
    assert nodes==[0,2,1] and edges==['0','1'] and diag['connector_nodes']==[1]
    assert '"connector":true' in text

def test_mixed_pass_through_byte_identity_and_budget_all_methods():
    items=tuple(EvidenceItem(evidence_id=s,source_type=s,canonical_id='stark:1',score=0.,provenance=(Provenance(dataset_version='fixture',source_id='1',locator='fixture'),),payload='{"paper_id":1,"content":"constant"}') for s in ('text','structured'))
    sources=('text','graph','structured');passed,budget=pass_through(items,sources)
    assert budget==8000
    contexts=[assemble(passed,sources,'graph '+m) for m in ('CM-B0','CM-B1','CM-01','CM-02','CM-03')]
    for context in contexts:
        assert passed['text']['context'] in context and passed['structured']['context'] in context and len(context)<=24000
    again,_=pass_through(items,sources)
    assert again==passed

def test_all_adapters_share_candidates_evidence_and_passthrough():
    from test_repair_cm01 import fixture,encoder
    from research.repair.rq1_compliance_v1.cm01 import canonical_units,cosine_scores
    from research.repair.rq1_compliance_v1.system import RepairedContextSystem
    from research.evaluation.contracts import SystemInput
    from research.common.serialization import content_hash
    p=fixture();units=canonical_units(p);scores=cosine_scores(p.question,units,encoder)
    items=tuple(EvidenceItem(evidence_id=s,source_type=s,canonical_id='stark:1',score=0.,provenance=(Provenance(dataset_version='fixture',source_id='1',locator='fixture'),),payload='{"paper_id":1,"content":"constant"}') for s in ('text','structured'))
    sources=('text','graph','structured');passed,budget=pass_through(items,sources)
    data={'query_id':p.query_id,'question':p.question,'pool':p.model_dump(mode='json'),'sources':sources,
        'pass_through':passed,'source_budget':budget,'graph_conflict_overlays':[],
        'baseline_evidence':[e.model_dump(mode='json') for e in items],'unit_scores':scores,
        'edge_scores':{k:scores[u.unit_id] for u in units for k,_,_ in u.provenance},'query_vector':[1,0]}
    outputs=[]
    for method in ('CM-B0','CM-B1','CM-01','CM-02','CM-03'):
        system=RepairedContextSystem(method,{p.query_id:data},encoder,lambda q,ts:[0]*len(ts),{p.query_id:()})
        outputs.append(system.execute(SystemInput(query_id=p.query_id,question=p.question,seed=42)))
    assert len({content_hash([e.model_dump(mode='json') for e in o.evidence]) for o in outputs})==1
    for o in outputs:
        assert passed['text']['context'] in o.context and passed['structured']['context'] in o.context
        assert o.tokenizer=='tiktoken-0.12.0:o200k_harmony' and o.context_tokens>0
        assert o.answer is None and o.observation.llm_calls==0
    class BrokenAnswer:
        version='fixture'
        def generate(self,*args):
            return '{malformed',{'llm_calls':1,'input_tokens':11,'output_tokens':2,'generation_ms':3.,'token_measurement_source':'fixture'}
    failed=RepairedContextSystem('CM-B0',{p.query_id:data},encoder,generator=BrokenAnswer()).execute(
        SystemInput(query_id=p.query_id,question=p.question,seed=42))
    assert failed.errors and failed.answer_ids is None and failed.answer=='{malformed'
    assert failed.evidence and failed.context and failed.observation.input_tokens==11
