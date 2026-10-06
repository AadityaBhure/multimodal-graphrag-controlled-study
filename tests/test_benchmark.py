"""Phase 4 fixtures test answer derivation and mutations, not evaluation metrics."""
from copy import deepcopy
from pathlib import Path
import json
from types import SimpleNamespace
import duckdb
import numpy as np
import pytest
from pydantic import ValidationError
from research.benchmark.source import Source
from research.benchmark.contracts import BenchmarkQuery
from research.benchmark.construction import intersection,necessity,impossible_mutation,template_signature
from research.benchmark.build import human_exclusion,write,load_jsonl
from research.benchmark.audit import leakage_scan,check_path
from research.benchmark.stress import StressBuilder


def query():
    return dict(query_id='fixture',source_query_id='fixture',split='test',question='Which papers report the specified claim?',
                answerable=True,modalities=['text'],modality_class='T',
                reasoning=dict(hop_count=1,multi_hop=False,complexity='single-hop',difficulty='controlled'),
                stress=dict(noisy=False,conflict=False,unanswerable=False),gold_answer_ids=[1172724],gold_evidence={},
                provenance={'source':'generated','template_family':'fixture-test','construction_instance':'one','base_query_id':'fixture'})


@pytest.mark.parametrize('change',[{'gold_answer_ids':[]},{'gold_answer_ids':[1,1]},{'modality_class':'TG'},
                                   {'reasoning':dict(hop_count=2,multi_hop=False,complexity='multi-hop-2',difficulty='controlled')},
                                   {'reasoning':dict(hop_count=1,multi_hop=False,complexity='multi-hop-3+',difficulty='controlled')}])
def test_contract_rejects_invalid_taxonomy_and_gold(change):
    row=query();row.update(change)
    with pytest.raises(ValidationError):BenchmarkQuery.model_validate(row)


def test_official_annotation_can_be_explicitly_unverified():
    row=query();row.update(modalities=[],modality_class='unverified',provenance={'source':'official_synthetic'},
                           reasoning=dict(hop_count=None,multi_hop=None,complexity='unverified',difficulty='unverified'))
    assert BenchmarkQuery.model_validate(row).reasoning.hop_count is None


def test_human_mixed_answer_query_excluded_whole_without_repair():
    original={'id':'50','query':'Example question','answer_ids':'[1172724, 123]'}
    before=deepcopy(original)
    result=human_exclusion(original,{1172724:'paper',123:'author'})
    assert result['original_answer_ids']==[1172724,123]
    assert result['original_answer_entity_types']==['paper','author']
    assert result['answers_repaired'] is False and original==before
    assert human_exclusion({'id':'1','query':'Q','answer_ids':'[1172724]'},{1172724:'paper'}) is None


def test_intersection_requires_every_modality():
    sets={'text':{1,2,3},'graph':{1,2,4},'structured':{1,3,4}}
    assert intersection(sets)=={1} and necessity(sets)
    assert not necessity({'text':{1,2},'graph':{1}})
    assert not necessity({'text':{1},'graph':{2}})


@pytest.fixture
def synthetic_source():
    s=Source.__new__(Source);s.con=duckdb.connect(':memory:')
    s.con.execute('CREATE TABLE texts(paper_id BIGINT,abstract VARCHAR,content VARCHAR)')
    s.con.execute("INSERT INTO texts VALUES (2,'We FIND alpha and beta','We FIND alpha and beta'),(3,'alpha only','alpha only'),(5,'beta only','beta only')")
    s.con.execute('CREATE TABLE papers(paper_id BIGINT,publication_year INTEGER,citation_count BIGINT,paper_rank BIGINT)')
    s.con.execute('INSERT INTO papers VALUES (2,2020,0,10),(3,2021,5,20),(5,NULL,NULL,NULL)')
    # Institution 1 -> author 0 -> paper 2 -> cited paper 3.
    edges=[(0,1,0,False,0),(0,2,3,False,1),(1,0,0,True,4),(2,3,1,False,2),(2,0,3,True,5),(3,2,1,True,6)]
    arrays={key:[] for key in ('neighbors','edge_ids','relation_ids','derived_inverse')};pointer=[0]
    for n in range(6):
        for a,z,r,inv,eid in edges:
            if a==n:
                for key,value in [('neighbors',z),('edge_ids',eid),('relation_ids',r),('derived_inverse',inv)]:arrays[key].append(value)
        pointer.append(len(arrays['neighbors']))
    s.csr={k:np.array(v) for k,v in arrays.items()};s.csr['indptr']=np.array(pointer)
    s.text_cache={};s.structured_cache={};s.graph_cache={};s.labels={0:'Alice Example',1:'Example Institute',2:'Paper A',3:'Paper B'}
    yield s
    s.close()


def test_candidate_predicates_use_abstract_and_preserve_null(synthetic_source):
    s=synthetic_source
    assert s.text({'operator':'all','phrases':['alpha','beta']})=={2}
    assert s.text({'operator':'any','phrases':['alpha','beta']})=={2,3,5}
    assert s.text({'operator':'any','phrases':['alpha','beta'],'required_extra_phrase':'we find'})=={2}
    assert s.structured({'filters':[{'field':'citation_count','operator':'>=','value':0}]})=={2,3}
    with pytest.raises(ValueError):s.text({'operator':'invented','phrases':['alpha']})
    with pytest.raises(ValueError):s.sql_predicate({'filters':[{'field':'abstract; DROP TABLE papers','operator':'=','value':1}]})


def test_real_graph_path_semantics_on_tiny_csr(synthetic_source):
    s=synthetic_source
    assert s.graph({'kind':'author','anchor_id':0})[0]=={2}
    assert s.graph({'kind':'institution','anchor_id':1})[0]=={2}
    values,paths=s.graph({'kind':'institution_citations','anchor_id':1})
    assert values=={3} and [e['relation_id'] for e in paths[3]]==[0,3,1]
    check_path(s,paths[3])


def test_unanswerable_mutation_is_verified_not_retrieval_failure(synthetic_source):
    s=synthetic_source
    record={'conditions':{'structured':{'filters':[dict(field='citation_count',operator='>=',value=0)]}}}
    before=deepcopy(record)
    conditions,rule=impossible_mutation(s,record)
    assert rule['observed_max']==2021
    assert s.candidates(conditions)=={'structured':set()} and record==before


def test_conflict_overlay_is_reversible_and_source_unchanged(synthetic_source):
    s=synthetic_source;before=s.row(2)
    record={'gold':[2],'conditions':{'structured':{'filters':[dict(field='citation_count',operator='>=',value=0)]}}}
    overlay=StressBuilder(s).conflict(record)
    assert overlay['before']==0 and overlay['after']==-1
    assert overlay['inverse_patch']['replace_with']==0
    assert s.row(2)==before


def test_split_leakage_and_paired_stress_handling():
    q=query();paired=deepcopy(q);paired['query_id']='fixture:noise'
    result=leakage_scan([q,paired])
    assert result['intentional_within_split_paired_stress_duplicate_count']==1
    bad=deepcopy(q);bad['query_id']='other';bad['split']='train'
    with pytest.raises(AssertionError):leakage_scan([q,bad])


def test_template_signature_ignores_condition_values_and_split_names():
    a={'text':{'operator':'all','phrases':['one claim']},'graph':{'kind':'author','anchor_id':4}}
    b={'text':{'operator':'all','phrases':['different claim']},'graph':{'kind':'author','anchor_id':99}}
    assert template_signature(a)==template_signature(b)
    b['graph']['kind']='institution'
    assert template_signature(a)!=template_signature(b)


def test_unicode_artifact_roundtrip_and_byte_stable_write(tmp_path):
    path=tmp_path/'record.json';value={'question':'Which paper says “café Δ”?'}
    write(path,value);before=path.read_bytes();write(path,value)
    assert path.read_bytes()==before and json.loads(path.read_text(encoding='utf-8'))==value


def test_bounded_actual_benchmark_compatibility_and_gold():
    root=Path(__file__).resolve().parents[1]/'data/MMG_STARK_MAG/benchmark'
    if not (root/'train.jsonl').exists():pytest.skip('Local full dataset not staged')
    exclusions=json.loads((root/'human_exclusions.json').read_text(encoding='utf-8'))
    assert {r['source_query_id'] for r in exclusions}=={'30','50','72'}
    humans=load_jsonl(root/'human_test.jsonl')
    assert len(humans)==81 and all(all(1172724<=p<=1872967 for p in q['gold_answer_ids']) for q in humans)
    q=next(q for q in load_jsonl(root/'train.jsonl') if q['provenance']['source']=='generated' and not any(q['stress'][k] for k in ('noisy','conflict','unanswerable')))
    record=json.loads((root/q['gold_evidence']['construction_record']).read_text(encoding='utf-8'))
    sets={k:set(json.loads((root/v['path']).read_text(encoding='utf-8'))) for k,v in record['candidate_sets'].items()}
    assert sorted(intersection(sets))==q['gold_answer_ids'] and necessity(sets)
