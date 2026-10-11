"""Graph-native adaptation fixtures; no dataset/model/API access."""
import itertools
import json
import numpy as np
import pytest
from research.rq1.contracts import Node,Edge,Pool
from research.repair.rq1_compliance_v1.cm01 import (
    OFFICIAL_EDGES,canonical_units,maximum_forest,organize,tree_sequences,
)

def fixture():
    nodes=tuple(Node(node_id=i,node_type=t,label=l) for i,t,l in [
        (0,'author','A'),(1,'paper','Title One'),(2,'institution','I'),
        (3,'paper','Title Two'),(4,'field_of_study',None)])
    edges=tuple(Edge(key=str(i),edge_id=i,source=s,target=t,relation=r) for i,s,t,r in [
        (0,0,1,'AUTHOR-WRITES-PAPER'),(1,0,2,'AUTHOR-AFFILIATED_WITH-INSTITUTION'),
        (2,1,3,'PAPER-CITES-PAPER'),(3,1,4,'PAPER-HAS_TOPIC-FIELD_OF_STUDY')])
    inverse=Edge(key='inverse',edge_id=OFFICIAL_EDGES,source=1,target=0,
        relation='AUTHOR-WRITES-PAPER',derived_inverse=True)
    return Pool(query_id='synthetic',question='query',nodes=nodes,edges=edges+(inverse,),boundary='fixture')

def encoder(texts):
    return np.array([[1.,(sum(map(ord,t))%17)/17] for t in texts])

def test_templates_and_no_text_structured_provenance():
    units=canonical_units(fixture())
    assert [u.serialization for u in units]==[
        'Author A writes Paper Title One.',
        'Author A is affiliated with Institution I.',
        'Paper Title One cites Paper Title Two.',
        'Paper Title One has topic stark:4.']
    assert units[3].target_label is None
    affiliation=units[1]
    assert (affiliation.source_node_id,affiliation.target_node_id)==(0,2)
    assert 'Title' not in affiliation.serialization
    assert all(not any(x in u.context_line() for x in ('abstract','citation_count','publication_year','venue','document_type','paper_rank')) for u in units)

def test_inverse_deduplicates_with_exact_official_provenance():
    units=canonical_units(fixture())
    assert len(units)==4 and len(units[0].provenance)==2
    assert any(p[2] is True for p in units[0].provenance)
    p=fixture();inverse_only=p.model_copy(update={'edges':(p.edges[-1],)})
    u=canonical_units(inverse_only)[0]
    assert u.unit_id==units[0].unit_id and u.serialization==units[0].serialization
    assert (u.source_node_id,u.target_node_id)==(0,1)

def test_affiliation_is_structural_path_not_paper_chunk():
    units=canonical_units(fixture());a,b=units[:2]
    assert a.source_node_id==b.source_node_id and a.target_node_type=='paper'
    assert b.target_node_type=='institution'
    assert not hasattr(a,'abstract') and not hasattr(b,'paper_id')

def test_boundary_seed_dfs_reranker_and_budget():
    pool=fixture();before=pool.model_dump_json();calls=[]
    def rank(q,texts):
        calls.append((q,texts))
        for text in texts:
            for line in text.splitlines():assert set(json.loads(line))=={'source','relation','target'}
        return [0.]*len(texts)
    first=organize(pool,'query',24000,encoder,rank)
    second=organize(pool,'query',24000,encoder,rank)
    assert first==second and pool.model_dump_json()==before
    text,kept,d=first
    assert len(kept)==len({u.unit_id for u in kept})==4
    assert d['k_seed']==10 and d['m_hops']==1 and d['additional_retrieval_calls']==0
    assert set(d['expanded_unit_ids'])<={u.unit_id for u in canonical_units(pool)}
    short,_,_=organize(pool,'query',80,encoder,rank)
    assert len(short)<=80 and len(text)<=24000
    assert calls and all('abstract' not in text for _,texts in calls for text in texts)

def test_exact_ten_seeds_with_stable_ties_and_one_hop_only():
    ns=tuple(Node(node_id=i,node_type='paper',label=str(i)) for i in range(17))
    es=tuple(Edge(key=str(i),edge_id=i,source=i,target=i+1,relation='PAPER-CITES-PAPER') for i in range(16))
    p=Pool(query_id='chain',question='query',nodes=ns,edges=es,boundary='synthetic')
    _,_,d=organize(p,'query',24000,lambda texts:np.ones((len(texts),2)),lambda q,ts:[0]*len(ts))
    assert d['seed_ids']==[f'graph:official:{i:08d}' for i in range(10)]
    assert d['expanded_unit_ids']==[f'graph:official:{i:08d}' for i in range(11)]

def test_literal_maximum_tree_and_affine_cost_equivalence():
    p=fixture();p=p.model_copy(update={'edges':p.edges+(Edge(key='cycle',edge_id=4,source=3,target=1,relation='PAPER-CITES-PAPER'),)})
    units=canonical_units(p)
    for values in [(1.,.8,.3,.2,.9),(.5,)*5,(-1.,-.8,-.3,-.2,-.9)]:
        scores=dict(zip((u.unit_id for u in units),values));tree=maximum_forest(units,scores)
        # Same stable tie key and affine cost produce exactly identical ordering.
        assert sorted(units,key=lambda u:(-scores[u.unit_id],u.unit_id))==sorted(units,key=lambda u:(1-scores[u.unit_id],u.unit_id))
        # Exhaustively verify connected spanning trees on this small graph.
        sums=[]
        for subset in itertools.combinations(units,4):
            candidate=maximum_forest(subset,scores)
            if len(candidate)==4:sums.append(sum(scores[u.unit_id] for u in candidate))
        assert sum(scores[u.unit_id] for u in tree)==max(sums)
        for seq in tree_sequences(tree,scores):
            assert seq[0]==min(seq,key=lambda u:(-scores[u.unit_id],u.unit_id))

def test_empty_and_no_usable_structure_fallbacks():
    p=fixture().model_copy(update={'edges':()})
    text,kept,d=organize(p,'query',24000,encoder,None)
    assert not text and not kept and d['fallback']=='no_graph_relation_evidence'
    loop=Edge(key='self',edge_id=0,source=1,target=1,relation='PAPER-CITES-PAPER')
    p=p.model_copy(update={'edges':(loop,)})
    text,kept,d=organize(p,'query',24000,encoder,None)
    assert kept and d['fallback']=='graph_semantic_units'

def test_conflicting_edge_identity_rejected():
    p=fixture();wrong=p.edges[1].model_copy(update={'edge_id':0})
    with pytest.raises(ValueError,match='identity'):canonical_units(p.model_copy(update={'edges':p.edges+(wrong,)}))
