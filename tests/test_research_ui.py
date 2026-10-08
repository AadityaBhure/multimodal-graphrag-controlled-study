"""Research UI tests: no network, API key or full-dataset fixture required."""
import copy
import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from research.evaluation.contracts import SystemOutput,Observation
from research.common.contracts import EvidenceItem,Provenance
from research.ui.service import ResearchService,performance,comparison
from research.ui.views import graph_dot
from research.ui.explorer import DatasetExplorer

ROOT=Path(__file__).resolve().parents[1]


def sample_run(question='fixture question',method='B1',run_id='fixture-run'):
    e=EvidenceItem(evidence_id='text:paper:1172724',source_type='text',canonical_id='stark:1172724',score=.8,
        payload=json.dumps({'paper_id':1172724,'title':'Fixture title','abstract':'Fixture abstract','content':'Fixture title\n\nFixture abstract'}),
        provenance=(Provenance(dataset_version='fixture',source_id='1172724',locator='fixture'),))
    out=SystemOutput(answer=None,answer_ids=None,ranked_paper_ids=(1172724,),evidence=(e,),context='Fixture context',retained_evidence_ids=(e.evidence_id,),
        observation=Observation(retrieval_ms=2,retrieval_calls=1,tool_calls=1,llm_calls=0),diagnostics='{"source_invocations":1}')
    return {'run_id':run_id,'timestamp':'2026-10-08T00:00:00+00:00','method':method,'question':question,'query_id':'ui:fixture',
            'query_seed':42,'config_id':'fixture','config_hash':'fixture','baseline_fingerprint':'fixture','representation_manifest_sha256':'fixture',
            'output':out.model_dump(mode='json'),'retrieval_wall_ms':3.,'generation_attempts':[],'scope':'interactive_inspection_not_benchmark_experiment'}


class FakeService:
    def __init__(self):self.retrieved=[];self.generated=[]
    def retrieve(self,question,method):
        self.retrieved.append((question,method));return sample_run(question,method,'run'+str(len(self.retrieved)))
    def generate(self,run,*,explicit_request=False):
        assert explicit_request;self.generated.append(run['run_id']);updated=copy.deepcopy(run)
        updated['output']['answer']='{"answer_ids":[1172724]}';updated['output']['answer_ids']=[1172724]
        updated['output']['observation'].update(llm_calls=1,input_tokens=11,output_tokens=3,generation_ms=1.,token_measurement_source='fixture')
        updated['generation_attempts']=[{'fixture':True}];return updated
    def close(self):pass


class FakeExplorer:
    def __init__(self):self.calls=[]
    def papers(self,term='',after=-1,limit=20):
        self.calls.append(('papers',term,after,limit));return [{'paper_id':1172724,'title':'Fixture title'}]
    def paper(self,paper_id):
        self.calls.append(('paper',paper_id));return {'text':{'paper_id':paper_id,'title':'Fixture title','abstract':'Fixture abstract'},
            'structured':{'paper_id':paper_id,'citation_count':None},'registry':{'stark_node_id':paper_id,'canonical_id':'stark:'+str(paper_id)}}
    def neighbors(self,node_id,offset=0,limit=25):
        self.calls.append(('neighbors',node_id,offset,limit));return {'node_id':node_id,'degree':1,'offset':offset,'limit':limit,'has_more':False,
            'nodes':[{'node_id':node_id,'node_type':'paper','label':'Title'},{'node_id':1,'node_type':'author','label':None}],
            'rows':[{'source':node_id,'target':1,'relation':'AUTHOR-WRITES-PAPER','edge_id':1,'derived_inverse':True}]}
    def close(self):pass


@pytest.fixture
def app(monkeypatch):
    import research.ui.app as ui
    service=FakeService();explorer=FakeExplorer()
    monkeypatch.setattr(ui,'get_service',lambda:service);monkeypatch.setattr(ui,'get_explorer',lambda:explorer)
    test=AppTest.from_file(str(ROOT/'research_app.py'),default_timeout=20).run()
    assert not test.exception
    return test,service,explorer


def test_initial_ui_does_not_retrieve_or_generate(app):
    at,service,explorer=app
    assert not service.retrieved and not service.generated and not explorer.calls
    assert len(at.tabs)==5
    assert 'Research Lab' in [t.value for t in at.title]


def test_retrieval_generation_is_explicit_and_not_repeated(app):
    at,service,_=app
    at.button(key='retrieve').click().run()
    assert not at.exception and len(service.retrieved)==1 and not service.generated
    at.run();assert not service.generated and len(service.retrieved)==1
    at.button(key='generate').click().run()
    assert not at.exception and len(service.generated)==1
    at.run();assert len(service.generated)==1 and at.button(key='generate').disabled
    assert len(at.session_state['history'])==1


def test_changed_question_disables_stale_generation(app):
    at,service,_=app
    at.button(key='retrieve').click().run()
    at.text_area(key='question').set_value('A different question').run()
    assert at.button(key='generate').disabled and not service.generated


def test_examples_and_comparison_use_same_question_without_generation(app):
    at,service,_=app
    from research.ui.app import EXAMPLES
    at.selectbox(key='example').select(EXAMPLES[1]['label']).run()
    at.button(key='load_example').click().run()
    assert at.selectbox(key='method').value=='B2' and at.text_area(key='question').value==EXAMPLES[1]['question']
    at.button(key='compare').click().run()
    assert not at.exception
    assert len(service.retrieved)==4 and len({q for q,_ in service.retrieved})==1 and not service.generated
    assert len(at.session_state['comparisons'])==4


def test_explorer_is_bounded_and_separate(app):
    at,service,explorer=app
    at.button(key='search_papers').click().run()
    at.button(key='open_paper').click().run()
    at.button(key='open_graph').click().run()
    assert not at.exception and not service.retrieved and not service.generated
    assert explorer.calls[-1][-1]==25 and at.session_state['paper_detail']['structured']['citation_count'] is None


def test_metrics_no_fabricated_gold_or_token_values():
    row=performance(sample_run())
    assert row['answer_f1'] is None and row['recall_at_5'] is None and row['input_tokens'] is None and row['estimated_cost'] is None
    assert row['llm_calls']==0 and row['context_characters']==15
    assert comparison([sample_run()])[0]['paper_id']==1172724
    with pytest.raises(ValueError):comparison([sample_run(),sample_run(question='different')])


def test_generation_uses_snapshot_only_and_preserves_baseline_settings(monkeypatch):
    import research.ui.service as module
    captured={}
    class Generator:
        def __init__(self,options):captured['options']=options
        def generate(self,question,context,seed):
            captured.update(question=question,context=context,seed=seed)
            return '{"answer_ids":[1172724]}',{'generation_ms':1.,'llm_calls':1,'input_tokens':12,'output_tokens':4,'token_measurement_source':'fixture'}
        def close(self):pass
    monkeypatch.setattr(module,'GroqGenerator',Generator)
    service=ResearchService();run=sample_run()
    with pytest.raises(ValueError):service.generate(run)
    assert not captured
    updated=service.generate(run,explicit_request=True)
    assert captured['context']=='Fixture context' and captured['question']==run['question'] and captured['seed']==42
    assert captured['options'].model=='openai/gpt-oss-120b' and captured['options'].temperature==0
    assert run['generation_attempts']==[] and updated['output']['answer_ids']==[1172724]
    assert 'gold' not in captured and updated['output']['evidence']==run['output']['evidence']
    with pytest.raises(ValueError):service.generate(updated,explicit_request=True)


def test_generation_setup_failure_does_not_fake_usage(monkeypatch):
    import research.ui.service as module
    class Missing:
        def __init__(self,options):raise ValueError('secret-do-not-leak')
    monkeypatch.setattr(module,'GroqGenerator',Missing)
    updated=ResearchService().generate(sample_run(),explicit_request=True)
    assert updated['output']['observation']['llm_calls']==0 and updated['output']['observation']['input_tokens'] is None
    assert 'secret-do-not-leak' not in json.dumps(updated)


def test_explorer_limits_and_graph_escaping():
    explorer=DatasetExplorer()
    for args in ((-1,0,25),(0,0,51),(0,-1,25)):
        with pytest.raises(ValueError):explorer.neighbors(*args)
    with pytest.raises(ValueError):explorer.papers(limit=100)
    with pytest.raises(ValueError):explorer.paper(-1)
    dot=graph_dot([{'node_id':1,'node_type':'paper','label':'bad"; node [URL="evil"]'}],[])
    assert '\\"' in dot
    with pytest.raises(ValueError):graph_dot([{}]*102,[])


def test_retrieve_delegates_unchanged_baseline(monkeypatch,tmp_path):
    import research.ui.service as module
    from tests.test_baselines import FixtureStore
    created=[]
    class Store(FixtureStore):
        def __init__(self,root,work,options,*,modalities):super().__init__(modalities);self.closed=False;created.append(self)
        def close(self):self.closed=True
    monkeypatch.setattr(module,'Stores',Store)
    service=ResearchService(work=tmp_path)
    a=service.retrieve('Institute published in 2020','B4');b=service.retrieve('Institute published in 2020','B4')
    assert a['query_seed']==b['query_seed'] and a['output']['evidence']==b['output']['evidence']
    assert a['output']['observation']['llm_calls']==0
    assert a['output']['diagnostics'] and len(created)==1
    service.retrieve('question','B1');assert created[0].closed
    service.close();assert created[-1].closed
