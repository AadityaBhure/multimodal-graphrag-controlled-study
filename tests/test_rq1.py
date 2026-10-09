"""Phase 7 deterministic fixtures, without datasets, remote models or generation."""
import json
import numpy as np
import pytest
from pydantic import ValidationError
from research.rq1.contracts import Pool,Node,Edge,Options,METHODS
from research.rq1.graph import mst,components
from research.rq1.manager import Manager,serialize
from research.rq1.diffusion import diffuse
from research.rq1.pcst import select_pcst

def fixture(count=8):
    nodes=tuple(Node(node_id=i,label=f'paper {i}' if i else None,node_type='paper',relevance=None if i==0 else 1-i/count,vector=None if i==0 else (1.,0.),depth=i,parent_edge=None if i==0 else f'e{i-1}') for i in range(count))
    edges=tuple(Edge(key=f'e{i}',source=i,target=i+1,relation='PAPER-CITES-PAPER',edge_id=i,relevance=.8-i/count,mst_cost=.1+i/count) for i in range(count-1))
    return Pool(query_id='fixture',question='question',nodes=nodes,edges=edges,seeds=(0,),boundary='synthetic')

@pytest.mark.parametrize('method',METHODS)
def test_determinism_budget_serialization_no_retrieval(method):
    pool=fixture();before=pool.model_dump_json();m=Manager(Options(method=method,budget=650),reranker=lambda q,t:[float(len(x)) for x in t])
    a=m.manage(pool,pool.question);d=dict(m.diagnostics);b=m.manage(pool,pool.question)
    assert a==b and len(a.serialized_context)<=650 and pool.model_dump_json()==before
    assert len(a.included_evidence_ids)==len(set(a.included_evidence_ids))
    for line in a.serialized_context.splitlines():json.loads(line)
    assert d['candidate_hash']==pool.fingerprint()
    assert set(d['selected_nodes'])<=set(n.node_id for n in pool.nodes)
    assert not any(x in a.serialized_context for x in ('abstract','publication_year','citation_count'))

@pytest.mark.parametrize('method',METHODS)
def test_empty(method):
    p=Pool(query_id='empty',question='question',nodes=(),edges=(),boundary='fixture')
    assert Manager(Options(method=method)).manage(p,p.question).serialized_context==''

def test_mst_cycle_minimum_and_dfs_connectivity():
    p=fixture(3);p=p.model_copy(update={'edges':p.edges+(Edge(key='cycle',source=0,target=2,relation='PAPER-CITES-PAPER',edge_id=99,mst_cost=9),)})
    assert mst(p,{0,1,2})==['e0','e1']
    m=Manager(Options(method='CM-01'),reranker=lambda q,t:[0.]*len(t));m.manage(p,p.question)
    assert m.diagnostics['mst_edges']==['e0','e1']
    assert len(components(p,m.diagnostics['selected_nodes'],m.diagnostics['selected_edges']))==1

def test_pcst_actual_solver_and_empty_fallback():
    p=fixture();chosen,keys,d=select_pcst(p,Options(method='CM-02'))
    assert chosen and len(components(p,chosen,keys))==1 and not d['fallback']
    chosen,keys,d=select_pcst(p,Options(method='CM-02'),lambda *a:(np.array([],int),np.array([],int)))
    assert chosen==[1] and not keys and d['fallback']

def test_diffusion_convergence_mass_and_hard_stop():
    p=fixture(8);o=Options(method='CM-03',n_seed=1,alpha=2)
    nodes,edges,d=diffuse(p,o)
    assert d['converged'] and not d['fallback'] and d['mass_error']<1e-10
    assert d['iterations']<o.max_iterations and nodes
    _,_,d=diffuse(p,o.model_copy(update={'max_iterations':1,'alpha':7}))
    assert d['fallback'] and not d['converged'] and d['iterations']<=1
    _,_,d=diffuse(p,Options(method='CM-03'))
    assert d['fallback'] and d['reason']=='component_mass_exceeds_sink_capacity'

def test_missing_semantics_not_invented():
    p=fixture(1);m=Manager(Options(method='CM-03'));c=m.manage(p,p.question)
    assert '"label":null' in c.serialized_context and m.diagnostics['fallback']
    with pytest.raises(ValidationError):Node(node_id=0,label=None,node_type='paper',relevance=.1)

@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-float('inf')])
def test_nonfinite_rejected(bad):
    with pytest.raises(ValidationError):Node(node_id=0,label='x',node_type='paper',relevance=bad)
    with pytest.raises(ValidationError):Options(method='CM-03',alpha=bad)
    with pytest.raises(ValidationError):Edge(key='e',source=0,target=1,edge_id=1,relation='x',mst_cost=bad)

def test_duplicates_and_high_degree_bounds():
    p=fixture();raw=p.model_dump();raw['nodes']+=raw['nodes'][:1]
    with pytest.raises(ValidationError):Pool.model_validate(raw)
    with pytest.raises(ValidationError):fixture(321)
    # fixture construction is expected to reject above the common boundary cap.

def test_duplicate_serialization_and_small_budget():
    p=fixture();text,ids,nodes,edges=serialize(p,[1,1,2,2],['e1','e1'],10000)
    assert len(ids)==len(set(ids)) and nodes==[1,2]
    assert serialize(p,[1],[],1)[0]==''

def test_reranker_is_required_and_finite():
    p=fixture()
    with pytest.raises(ValueError):Manager(Options(method='CM-01')).manage(p,p.question)
    with pytest.raises(ValueError):Manager(Options(method='CM-01'),reranker=lambda q,t:[float('nan')]*len(t)).manage(p,p.question)
    with pytest.raises(ValueError):Manager(Options(method='CM-B0')).manage(p,'other question')

def test_runner_resume_and_boundary_mismatch(tmp_path):
    from tests.test_evaluation import fixture_benchmark,query
    from research.rq1.system import ContextSystem
    from research.experiments.config import RunnerConfig
    from research.experiments.runner import run,materialize
    from research.evaluation.contracts import SystemInput
    p=fixture().model_copy(update={'query_id':'q1','question':'Fixture paper set?'})
    root=fixture_benchmark(tmp_path/'benchmark',[query()])
    options=Options(method='CM-B1');system=ContextSystem(options,{'q1':p})
    cfg=RunnerConfig(config_id='rq1-fixture',system_id='CM-B1',system_version='1',context_method='CM-B1')
    dest=run(cfg,root,tmp_path/'run',system,provenance={'git_commit':'fixture'})
    before=(dest/'records.jsonl').read_bytes();records=materialize(dest)
    assert records[0].output and not records[0].errors and records[0].metrics['f1'] is None
    assert records[0].observation.retrieval_calls==0 and records[0].observation.llm_calls==0
    run(cfg,root,dest,system,provenance={'git_commit':'fixture'})
    assert before==(dest/'records.jsonl').read_bytes()
    changed=ContextSystem(options.model_copy(update={'budget':100}),{'q1':p})
    with pytest.raises(ValueError):run(cfg,root,dest,changed,provenance={'git_commit':'fixture'})
    with pytest.raises(ValueError):system.execute(SystemInput(query_id='q1',question=p.question,seed=42,overlay='{}'))

def test_bounded_candidate_builder_without_text_or_sql():
    from research.rq1.candidates import build_pool
    class GraphOnly:
        manifest_hash='fixture'
        csr={'indptr':np.array([0,2,3,4]),'neighbors':np.array([1,2,0,0]),'edge_ids':np.array([0,1,0,1]),'relation_ids':np.array([1,1,1,1]),'derived_inverse':np.array([False,False,True,True])}
        def nodes(self,ids):return {n:{'node_id':n,'label':None if n==2 else str(n),'node_type':'paper'} for n in ids}
        def encode(self,strings):return np.array([[1.,0.] for _ in strings])
    p=build_pool(GraphOnly(),'q','question',[0],None,'fixture')
    assert len(p.nodes)==3 and len(p.edges)==4 and p.nodes[2].label is None
    assert p.nodes[2].relevance is None and p.nodes[2].vector is None
    assert json.loads(p.provenance)['text_calls']==0

def test_connected_budget_prefix_pcst():
    p=fixture();m=Manager(Options(method='CM-02',budget=600));m.manage(p,p.question)
    d=m.diagnostics
    assert len(components(p,d['selected_nodes'],d['selected_edges']))<=1

def test_three_plus_hops_is_explicitly_synthetic():
    p=fixture(5);m=Manager(Options(method='CM-01'),reranker=lambda q,t:[1.]*len(t));m.manage(p,p.question)
    assert len(m.diagnostics['selected_edges'])==4 and p.boundary=='synthetic'

def test_high_degree_materialization_is_capped():
    from research.rq1.candidates import build_pool
    class Star:
        manifest_hash='fixture'
        def __init__(self):
            count=1000
            self.csr={'indptr':np.array([0,count]+list(range(count+1,2*count+1))),
                'neighbors':np.array(list(range(1,count+1))+[0]*count),'edge_ids':np.array(list(range(count))*2),
                'relation_ids':np.ones(2*count,dtype=int),'derived_inverse':np.array([False]*count+[True]*count)}
        def nodes(self,ids):return {n:{'node_id':n,'label':str(n),'node_type':'paper'} for n in ids}
        def encode(self,strings):return np.array([[1.,0.] for _ in strings])
    p=build_pool(Star(),'star','question',[0],None,'fixture')
    assert len(p.nodes)==129 and len(p.edges)==256
    assert json.loads(p.provenance)['truncated'] is True

def test_read_only_context_viewer():
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'context_review_app.py',default_timeout=30).run()
    assert not app.exception and len(app.selectbox)==2
    assert len(app.button)==0
    app.selectbox[0].set_value('CM-02').run()
    assert not app.exception
