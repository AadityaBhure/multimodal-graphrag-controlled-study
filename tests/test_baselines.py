"""Deterministic baseline fixtures test source boundaries, SQL safety and telemetry."""
import json
from types import SimpleNamespace
import numpy as np
import pytest
from pydantic import ValidationError
from research.baselines.config import BaselineOptions
from research.baselines.structured import Predicate,QueryPlan,compile_plan,parse_question
from research.baselines.retrieval import graph_retrieve,text_retrieve,structured_retrieve
from research.baselines.system import BaselineSystem,build_context
from research.baselines.generation import OfflineGenerator,parse_answer
from research.evaluation.contracts import SystemInput
from research.experiments.config import RunnerConfig


class FixtureStore:
    manifest={'dataset_version':'fixture'};manifest_hash='fixture'
    def __init__(self,modalities):
        self.modalities=set(modalities);self.calls=[]
        # Institution 0 -> unnamed author 1 -> paper 2; paper 3 is globally relevant but disconnected.
        self.csr={'indptr':np.array([0,1,3,4,4]),'neighbors':np.array([1,0,2,1]),
                  'edge_ids':np.array([10,0,1,11]),'relation_ids':np.array([0,0,3,3]),'derived_inverse':np.array([True,False,False,True])}
    def seed_nodes(self,q):self.calls.append('seeds');return [{'node_id':0,'label':'Institute','node_type':'institution','score':1.}]
    def nodes(self,ids):
        return {i:{'node_id':i,'node_type':['institution','author','paper','paper'][i],
                   'label':['Institute',None,'Graph title','Disconnected title'][i]} for i in ids}
    def text_search(self,q,k):self.calls.append('text_search');return [(3,.9),(2,.8)][:k]
    def texts(self,ids):
        self.calls.append('texts')
        return {i:{'paper_id':i,'title':f'Title {i}','abstract':'Fixture abstract','content':f'Title {i}\n\nFixture abstract'} for i in ids}
    def structured(self,plan,k):self.calls.append('structured');return [{'paper_id':2,'publication_year':2020,'citation_count':None}]


def cfg(baseline,**kw):
    return RunnerConfig(config_id='fixture-'+baseline,system_id=baseline,system_version='1',embedding_model='sentence-transformers/all-MiniLM-L6-v2',
        retrieval_parameters=BaselineOptions(**kw).model_dump())


def test_graph_candidates_paths_nulls_and_no_text():
    s=FixtureStore(('graph',));items,diag=graph_retrieve(s,'Institute',BaselineOptions())
    assert [e.canonical_id for e in items]==['stark:2'] and 'texts' not in s.calls and 'text_search' not in s.calls
    payload=json.loads(items[0].payload)
    assert len(payload['path'])==2 and payload['path'][0]['derived_inverse'] is True
    assert any(n['label'] is None for n in payload['nodes'])
    assert 'abstract' not in items[0].payload and diag['visited_nodes']<=2000 and diag['scanned_edges']<=20000


@pytest.mark.parametrize('limit',[1,2,3])
def test_graph_budgets(limit):
    items,diag=graph_retrieve(FixtureStore(('graph',)),'Institute',BaselineOptions(max_nodes=limit,max_edges=limit,per_node_edges=1))
    assert diag['visited_nodes']<=limit and diag['scanned_edges']<=limit


def test_graph_no_seed_never_falls_back():
    s=FixtureStore(('graph',));s.seed_nodes=lambda q:[]
    result,diag=graph_retrieve(s,'unknown',BaselineOptions())
    assert not result and diag['status']=='no_graph_seed' and not s.calls


def test_text_topk_and_identity():
    result,_=text_retrieve(FixtureStore(('text',)),'question',BaselineOptions(top_k=1))
    assert len(result)==1 and result[0].canonical_id=='stark:3'
    assert set(json.loads(result[0].payload))=={'paper_id','title','abstract','content'}


def test_sql_safety_and_nulls(tmp_path):
    import duckdb
    con=duckdb.connect(':memory:')
    con.execute('CREATE TABLE papers(paper_id BIGINT,publication_year INTEGER,publication_date DATE,citation_count BIGINT,paper_rank BIGINT,venue_namespace VARCHAR,venue_id VARCHAR,venue_name VARCHAR,document_type VARCHAR)')
    con.execute("INSERT INTO papers VALUES (1,2020,NULL,NULL,3,'journal',NULL,'safe',NULL),(2,2021,NULL,0,4,'journal',NULL,'other',NULL)")
    plan=QueryPlan(predicates=(Predicate(field='citation_count',op='is_null'),))
    sql,args=compile_plan(plan,5);assert con.execute(sql,args).fetchall()[0][0]==1
    sql,args=compile_plan(QueryPlan(predicates=(Predicate(field='citation_count',op='>=',value=0),)),5)
    assert [r[0] for r in con.execute(sql,args).fetchall()]==[2]
    attack="x'; DROP TABLE papers; --"
    sql,args=compile_plan(QueryPlan(predicates=(Predicate(field='venue_name',op='=',value=attack),)),5)
    assert attack not in sql and con.execute(sql,args).fetchall()==[]
    assert con.execute('SELECT count(*) FROM papers').fetchone()[0]==2
    for bad in ({'field':'paper_id;DROP TABLE papers','op':'=','value':1},{'field':'citation_count','op':'=','value':None},{'field':'citation_count','op':'=','value':'0 OR 1=1'}):
        with pytest.raises(ValidationError):Predicate(**bad)
    con.close()


@pytest.mark.parametrize('question,count',[('publication year is between 2010 and 2020',2),('published after 2018 with at least 10 citations',2),('citation count is missing',1),('publication date before 2020-01-01',1),('recorded normalized venue namespace is journal and paper rank is at most 123',2)])
def test_parser(question,count):
    plan,status=parse_question(question);assert plan is not None and len(plan.predicates)==count


def test_unsupported_and_structured_null_preservation():
    assert parse_question('graph retrieval methods')[0] is None
    assert parse_question('SELECT * FROM papers')[0] is None
    assert parse_question('publication year is 2020 or citation count is 1')[0] is None
    result,_=structured_retrieve(FixtureStore(('structured',)),'published in 2020',BaselineOptions())
    assert json.loads(result[0].payload)['citation_count'] is None


def test_b4_independent_sources_context_cache_and_measurements(tmp_path):
    s=FixtureStore(('text','graph','structured'));system=BaselineSystem(cfg('B4'),s,OfflineGenerator(),tmp_path/'cache')
    q=SystemInput(query_id='q',question='Institute published in 2020',seed=42)
    first=system.execute(q)
    assert {e.source_type for e in first.evidence}=={'text','graph','structured'}
    assert all('['+name+']' in first.context for name in ('TEXT','GRAPH','STRUCTURED'))
    assert first.observation.retrieval_calls==3 and first.observation.llm_calls==0 and first.answer_ids is None
    assert first.observation.retrieval_ms>=0 and first.observation.generation_ms is None
    second=system.execute(q)
    assert first.evidence==second.evidence and second.observation.retrieval_calls==0
    assert json.loads(second.diagnostics)['graph']['candidate_ids']==[2]
    assert len(first.context)<=24000


def test_context_safety_cap_and_answer_parsing():
    items,_=text_retrieve(FixtureStore(('text',)),'q',BaselineOptions())
    context,retained,truncated=build_context(items,('text',),60)
    assert len(context)<=60 and retained and truncated
    assert parse_answer('{"answer_ids":[2,2],"explanation":"supported"}',[2])==(2,)
    for raw in ('{"answer_ids":[999]}','{"answer_ids":[true]}','{"answer_ids":["2"]}','bad','{"answer_ids":[],"sql":"drop"}'):
        with pytest.raises((ValueError,TypeError)):parse_answer(raw,[2])


def test_generation_failure_preserves_retrieval_measurements():
    class Failure:
        version='fixture'
        def generate(self,*args):raise RuntimeError('secret')
    system=BaselineSystem(cfg('B1'),FixtureStore(('text',)),Failure())
    out=system.execute(SystemInput(query_id='q',question='question',seed=1))
    assert out.errors and out.evidence and out.answer_ids is None and out.observation.llm_calls==1
    assert 'secret' not in out.model_dump_json()


def test_b4_attempts_all_sources_after_source_failure():
    store=FixtureStore(('text','graph','structured'))
    def fail(*args):raise RuntimeError('failed text')
    store.text_search=fail
    system=BaselineSystem(cfg('B4'),store,OfflineGenerator())
    out=system.execute(SystemInput(query_id='q',question='Institute published in 2020',seed=1))
    assert out.errors and out.errors[0].stage=='text_retrieval'
    assert 'seeds' in store.calls and 'structured' in store.calls and out.observation.retrieval_calls==3
    assert out.observation.llm_calls==0 and out.answer_ids is None


def test_baseline_runner_records_partial_failure_and_resume(tmp_path):
    from tests.test_evaluation import fixture_benchmark
    from research.experiments.runner import run,materialize
    class BadAnswer:
        version='fixture-invalid'
        def generate(self,*args):return '{"answer_ids":[999]}',{'llm_calls':1,'generation_ms':1.0}
    root=fixture_benchmark(tmp_path/'benchmark')
    system=BaselineSystem(cfg('B1'),FixtureStore(('text',)),BadAnswer())
    output=run(cfg('B1'),root,tmp_path/'run',system,provenance={'git_commit':'fixture'})
    records=materialize(output)
    assert all(r.errors and r.output.evidence and r.observation.llm_calls==1 and r.metrics['set_accuracy'] is None for r in records)
    before=(output/'records.jsonl').read_bytes()
    run(cfg('B1'),root,output,system,provenance={'git_commit':'fixture'})
    assert before==(output/'records.jsonl').read_bytes()


def test_stress_overlay_respects_modalities_and_preserves_nulls():
    from research.baselines.system import apply_overlay
    store=FixtureStore(('structured',))
    store.structured_rows=lambda ids:{i:{'paper_id':i,'publication_year':None,'citation_count':None} for i in ids}
    request=SystemInput(query_id='q',question='q',seed=1,overlay=json.dumps({'kind':'noisy','distractors':{'structured':[{'paper_id':3}]}}))
    items,diag=apply_overlay(store,(),request,('structured',),BaselineOptions())
    assert json.loads(items[0].payload)['citation_count'] is None
    assert json.loads(items[0].metadata)['origin']=='phase4_evaluation_overlay'
    request=SystemInput(query_id='q',question='q',seed=1,overlay=json.dumps({'kind':'conflict','injection':{'source':'graph','paper_id':3,'mutated_conflicting_evidence':{'title':'wrong'}}}))
    items,_=apply_overlay(FixtureStore(('graph',)),(),request,('graph',),BaselineOptions())
    assert not items


def test_shared_groq_settings_and_provider_usage(monkeypatch):
    import groq
    from research.baselines.generation import GroqGenerator,PROMPT
    from research.baselines import config as baseline_config
    seen={}
    class FakeClient:
        def __init__(self,**kwargs):
            seen['client']=kwargs
            self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def create(self,**kwargs):
            seen['request']=kwargs
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer_ids":[]}'))],
                                   usage=SimpleNamespace(prompt_tokens=17,completion_tokens=4))
        def close(self):pass
    monkeypatch.setattr(groq,'Groq',FakeClient)
    monkeypatch.setattr(baseline_config,'groq_key',lambda:'fixture-only-not-a-real-key')
    generator=GroqGenerator(BaselineOptions())
    raw,usage=generator.generate('question','context',42)
    assert seen['client']['base_url']=='https://api.groq.com' and seen['client']['max_retries']==0
    assert seen['request']['model']=='openai/gpt-oss-120b' and seen['request']['temperature']==0
    assert seen['request']['seed']==42 and seen['request']['max_completion_tokens']==1024
    assert seen['request']['messages'][0]['content']==PROMPT
    assert usage['input_tokens']==17 and usage['output_tokens']==4 and usage['llm_calls']==1
    assert usage['generation_ms']>=0 and raw=='{"answer_ids":[]}'
