"""Hand-calculated metrics and synthetic runner integration; no models or network."""
from datetime import datetime, timezone
import json
from math import log2
import pytest
from pydantic import ValidationError
from research.common.contracts import EvidenceItem, Provenance
from research.evaluation.benchmark import BenchmarkReader, digest, release_gate
from research.evaluation.contracts import SystemInput, SystemOutput, Observation, RunRecord, RunEvent
from research.evaluation.metrics import answer_metrics, retrieval_metrics, context_metrics, coverage
from research.experiments.config import RunnerConfig
from research.experiments.runner import run, write, materialize, compute_metrics, labels
from research.experiments.synthetic import SyntheticSystem
from research.benchmark.contracts import BenchmarkQuery


def query(qid='q1', split='validation', source='generated', gold=(1,2), **kw):
    generated = source == 'generated'
    data = dict(query_id=qid, source_query_id=qid, split=split, question='Fixture paper set?',
        answerable=bool(gold), modalities=('text',) if generated else (), modality_class='T' if generated else 'unverified',
        reasoning=dict(hop_count=1 if generated else None, multi_hop=False if generated else None,
                       complexity='single-hop' if generated else 'unverified', difficulty='controlled' if generated else 'unverified'),
        stress=dict(unanswerable=not bool(gold)), gold_answer_ids=gold, gold_evidence={},
        provenance={'source':source,'annotation_status':'manual_review_pending'})
    data.update(kw)
    return BenchmarkQuery.model_validate(data)


def fixture_benchmark(root, queries=None, overlays=None):
    root.mkdir(parents=True, exist_ok=True)
    queries = queries or [query(), query('q2',source='official_synthetic'), query('test','test'), query('human','human_test','official_human')]
    for split in ('train','validation','test','human_test'):
        (root/(split+'.jsonl')).write_text(''.join(q.model_dump_json()+'\n' for q in queries if q.split==split),encoding='utf-8')
    for name, data in (overlays or {}).items():
        (root/name).parent.mkdir(exist_ok=True,parents=True)
        write(root/name,data)
    files=[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(root.rglob('*')) if p.is_file()]
    manifest={'benchmark_version':'synthetic-fixture-v1','content_frozen':True,'files':files,
              'query_file_sha256':{s:digest(root/(s+'.jsonl')) for s in ('train','validation','test','human_test')},
              'test_content_freeze_id':'fixture-freeze','representation_manifest_sha256':'fixture-only-no-real-representations'}
    write(root/'benchmark_manifest.json',manifest)
    return root


def config(**kw):
    return RunnerConfig(config_id='test',system_id='synthetic-fixture',system_version='1',**kw)


def execute(tmp_path, system=None, cfg=None, root=None, **kw):
    root = root or fixture_benchmark(tmp_path/'benchmark')
    return run(cfg or config(), root, tmp_path/'experiment', system or SyntheticSystem(), provenance={'git_commit':'fixture'}, **kw)


def test_hand_answer_examples():
    m=answer_metrics([1,2,2],[2,3,4])
    assert m=={'set_accuracy':0.,'exact_match':0.,'precision':.5,'recall':1/3,'f1':.4,'answerability_correctness':1.}
    assert all(v==1 for v in answer_metrics([],[]).values())
    assert all(v==0 for v in answer_metrics([],[1]).values())
    assert all(v==0 for v in answer_metrics([1],[]).values())
    assert all(v is None for v in answer_metrics(None,[]).values())
    assert answer_metrics([2,1,1],[1,2])['exact_match']==1


def test_hand_rank_examples():
    m=retrieval_metrics([9,2,2,1],[1,2,3],[1,3,5])
    assert m['mrr']==.5 and m['recall@3']==2/3 and m['precision@3']==2/3
    assert m['ndcg@3']==pytest.approx((1/log2(3)+1/log2(4))/(1+1/log2(3)+1/log2(4)))
    assert m['precision@5']==.4 and m['gold_coverage']==2/3
    assert all(v==0 for v in retrieval_metrics([], [1], [1]).values())
    assert all(v is None for v in retrieval_metrics([], [], [1]).values())
    assert all(v is None for v in retrieval_metrics(None, [1], [1]).values())
    with pytest.raises(ValueError): retrieval_metrics([],[],[0])


def test_context_coverage_and_missing():
    m=context_metrics('abcd',['a','b','b'],['a','a'],tokens=2,tokenizer='fixture-v1',baseline_characters=8)
    assert m==dict(context_characters=4,context_tokens=2,evidence_retained=.5,redundancy=.5,context_reduction=.5)
    assert all(v is None for v in context_metrics(None,None,None).values())
    assert coverage(['a'],None) is None and coverage([],[]) is None
    with pytest.raises(ValueError):context_metrics('a',[],[],tokens=1)
    with pytest.raises(ValueError):context_metrics('a',[],[],baseline_characters=0)


def test_output_and_tokens_validation():
    with pytest.raises(ValidationError): SystemOutput(answer_ids=(True,))
    with pytest.raises(ValidationError): SystemOutput(context_tokens=5)
    with pytest.raises(ValidationError): Observation(input_tokens=1)
    with pytest.raises(ValidationError): SystemOutput(baseline_context_characters=10)
    with pytest.raises(ValidationError): SystemOutput(retained_evidence_ids=('missing',))
    e=EvidenceItem(evidence_id='e',source_type='text',canonical_id='stark:1',content='fixture',score=1,
        provenance=(Provenance(dataset_version='fixture',source_id='fixture',locator='fixture'),))
    assert len(SystemOutput(evidence=(e,e)).evidence)==2
    with pytest.raises(ValidationError): SystemOutput(evidence=(e,e.model_copy(update={'content':'different'})))


def test_cost_only_explicit_and_agent_placeholders():
    q=query()
    output=SystemOutput(answer_ids=(1,),observation=Observation(input_tokens=100,output_tokens=50,token_measurement_source='fixture'))
    assert compute_metrics(q,output,config(),1)['estimated_cost'] is None
    cfg=config(model_ids=('fixture',),pricing={'model_id':'fixture','currency':'USD','source':'fixture-price-v1','input_per_million':2,'output_per_million':4})
    m=compute_metrics(q,output,cfg,1)
    assert m['estimated_cost']==.0004 and m['source_selection_accuracy'] is None and m['evidence_coverage'] is None
    with pytest.raises(ValidationError):config(pricing={'model_id':'x','currency':'USD','source':'x','input_per_million':1,'output_per_million':1})


def test_run_resume_identity_schema_and_cohorts(tmp_path):
    root=fixture_benchmark(tmp_path/'benchmark')
    before={p:digest(p) for p in root.rglob('*') if p.is_file()}
    directory=execute(tmp_path,root=root)
    records=materialize(directory)
    assert len(records)==2
    original=(directory/'records.jsonl').read_bytes()
    execute(tmp_path,root=root)
    assert (directory/'records.jsonl').read_bytes()==original
    assert before=={p:digest(p) for p in root.rglob('*') if p.is_file()}
    assert records[0].metrics['retrieval_ms'] is None and records[0].observation.llm_calls==0
    events=[RunEvent.model_validate_json(line) for line in (directory/'events.jsonl').read_text().splitlines()]
    assert len(events)==4
    table=json.loads((directory/'aggregate.json').read_text())
    assert {r['cohort'] for r in table}>={'official_overall','generated_controlled','modality/T','modality/unverified','hop/unverified'}
    assert next(r for r in table if r['cohort']=='overall' and r['metric']=='generation_ms')['n_null']==2
    with pytest.raises(ValueError,match='Incompatible'):execute(tmp_path,root=root,cfg=config(seed=43))
    assert (directory/'records.jsonl').read_bytes()==original


def test_crash_and_interruption_resume(tmp_path):
    root=fixture_benchmark(tmp_path/'benchmark')
    class Interrupt(SyntheticSystem):
        def execute(self, request): raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):execute(tmp_path,root=root,system=Interrupt())
    directory=execute(tmp_path,root=root)
    assert len(materialize(directory))==2
    assert 'recovered_interruption' in (directory/'events.jsonl').read_text()
    other=tmp_path/'other';other.mkdir()
    class Crash(SyntheticSystem):
        def execute(self, request): raise RuntimeError('secret-value')
    directory=execute(other,system=Crash())
    records=materialize(directory)
    assert all(r.errors and r.metrics['set_accuracy'] is None for r in records)
    assert 'secret-value' not in (directory/'records.jsonl').read_text()
    execute(other,root=other/'benchmark')
    assert all(r.errors for r in materialize(directory))


def release_document(reader):
    return {'benchmark_manifest_sha256':reader.manifest_hash,'test_content_freeze_id':reader.manifest['test_content_freeze_id'],
        'status':'released','leakage_adjudicated':True,'released_by':'Fixture reviewer',
        'decisions':[{'query_id':q.query_id,'decision':'pass','reviewer':'Fixture reviewer','reason':'Synthetic contract test only',
                     'reviewed_at':datetime.now(timezone.utc).isoformat()} for s in ('test','human_test') for q in reader.records(s)]}


def test_release_gate(tmp_path):
    root=fixture_benchmark(tmp_path/'benchmark'); reader=BenchmarkReader(root)
    with pytest.raises(ValueError):release_gate(reader,None)
    release=release_document(reader);path=tmp_path/'release.json';write(path,release)
    assert release_gate(reader,path)['verified']==2
    directory=execute(tmp_path,root=root,cfg=config(mode='paper_test',splits=('test','human_test')),release_path=path)
    assert len(materialize(directory))==2
    for change in ({'status':'pending'}, {'leakage_adjudicated':False}, {'benchmark_manifest_sha256':'wrong'}, {'decisions':release['decisions'][:1]}, {'decisions':release['decisions']*2}):
        write(path,{**release,**change})
        with pytest.raises(ValueError):release_gate(reader,path)
    with pytest.raises(ValueError):execute(tmp_path,root=root,cfg=config(mode='paper_test',splits=('test','human_test')),release_path=path)
    with pytest.raises(ValidationError):config(splits=('test',))


def test_stress_overlay_sanitization(tmp_path):
    q=query(provenance={'source':'generated','stress_record':'stress_cases/conflict.json'},stress={'conflict':True})
    overlay={'source':'structured','paper_id':1,'field':'rank','after':99,'before':1,'authoritative_fact':{'rank':1},
             'mutated_conflicting_evidence':{'rank':99},'expected_behavior':'gold secret','canonical_data_modified':False}
    root=fixture_benchmark(tmp_path/'benchmark',[q],{'stress_cases/conflict.json':overlay})
    reader=BenchmarkReader(root); payload=reader.overlay(q)
    assert 'authoritative_fact' not in payload and 'gold secret' not in payload and 'before' not in payload
    assert json.loads(payload)['injection']['after']==99
    assert set(SystemInput.model_fields)=={'schema_version','query_id','question','seed','overlay'}
    assert labels(query(source='official_synthetic')).hop_count is None
    before=digest(root/'stress_cases/conflict.json');execute(tmp_path,root=root)
    assert digest(root/'stress_cases/conflict.json')==before


def test_checksum_tamper_and_unknown_selection(tmp_path):
    root=fixture_benchmark(tmp_path/'benchmark')
    with pytest.raises(ValueError):execute(tmp_path,root=root,cfg=config(query_ids=('absent',)))
    with pytest.raises(ValueError):BenchmarkReader(root).verified_path('../escape')
    (root/'validation.jsonl').write_text('tamper',encoding='utf-8')
    with pytest.raises(ValueError,match='checksum'):execute(tmp_path,root=root)


def test_record_finite_and_timezone(tmp_path):
    directory=execute(tmp_path);record=materialize(directory)[0].model_dump(mode='json')
    with pytest.raises(ValidationError):RunRecord.model_validate({**record,'timestamp':'2026-01-01T00:00:00'})
    with pytest.raises(ValidationError):RunRecord.model_validate({**record,'metrics':{'bad':float('nan')}})
    with pytest.raises(ValidationError):RunRecord.model_validate({**record,'unknown':1})


def test_aggregate_rejects_mixed_versions_and_duplicates(tmp_path):
    from research.evaluation.aggregate import aggregate
    directory=execute(tmp_path);records=materialize(directory)
    with pytest.raises(ValueError):aggregate([records[0],records[0]])
    with pytest.raises(ValueError):aggregate([records[0],records[1].model_copy(update={'config_hash':'wrong'})])
    with pytest.raises(ValueError):aggregate([records[0],records[1].model_copy(update={'provenance':{}})])


def test_identical_independent_runs_and_partial_marker(tmp_path):
    root=fixture_benchmark(tmp_path/'benchmark')
    first=execute(tmp_path,root=root)
    second=run(config(),root,tmp_path/'second',SyntheticSystem(),provenance={'git_commit':'fixture'})
    a,b=materialize(first),materialize(second)
    assert [r.experiment_id for r in a]==[r.experiment_id for r in b]
    assert [r.config_hash for r in a]==[r.config_hash for r in b]
    assert [r.metrics['mrr'] for r in a]==[r.metrics['mrr'] for r in b]
    class Half(SyntheticSystem):
        def execute(self, request):
            if request.query_id=='q2':raise KeyboardInterrupt()
            return super().execute(request)
    with pytest.raises(KeyboardInterrupt):run(config(),root,tmp_path/'partial',Half(),provenance={'git_commit':'fixture'})
    assert json.loads((tmp_path/'partial/status.json').read_text())['marker']=='INCOMPLETE'
    assert all(not r['run_complete'] for r in json.loads((tmp_path/'partial/aggregate.json').read_text()))
    run(config(),root,tmp_path/'partial',SyntheticSystem(),provenance={'git_commit':'fixture'})
    assert json.loads((tmp_path/'partial/status.json').read_text())['complete']


def test_evidence_cache_immutable_and_versioned(tmp_path):
    from research.experiments.evidence_cache import EvidenceCache
    from research.common.contracts import RetrievalBundle
    cache=EvidenceCache(tmp_path/'cache')
    identity=cache.identity(query_id='q',query_sha256='qhash',representation_sha256='rhash',retriever_id='fixture',retriever_version='1',parameters={'k':3},seed=42)
    assert cache.get(identity) is None
    bundle=RetrievalBundle(query_id='q')
    key=cache.put(identity,bundle)
    assert cache.put(identity,bundle)==key and cache.get(identity)==bundle
    assert cache.get({**identity,'seed':43}) is None
    with pytest.raises(ValueError):cache.put(identity,RetrievalBundle(query_id='wrong'))
    (tmp_path/'cache'/f'{key}.json').write_text('{}')
    with pytest.raises((ValueError,KeyError)):cache.get(identity)


def test_lock_and_committed_pending_recovery(tmp_path):
    from filelock import FileLock, Timeout
    root=fixture_benchmark(tmp_path/'benchmark'); directory=execute(tmp_path,root=root)
    with FileLock(str(directory/'run.lock')):
        with pytest.raises(Timeout):execute(tmp_path,root=root)
    write(directory/'pending.json',{'query_id':'q2','timestamp':'fixture-after-commit-before-cleanup'})
    execute(tmp_path,root=root)
    assert not (directory/'pending.json').exists()
    assert len(materialize(directory))==2


def test_noisy_overlay_and_evidence_coverage(tmp_path):
    q=query(provenance={'source':'generated','stress_record':'noise.json'},stress={'noisy':True})
    root=fixture_benchmark(tmp_path/'benchmark',[q],{'noise.json':{'canonical_data_modified':False,
        'distractors':{'text':[{'paper_id':9,'violates':['secret-gold-filter'],'similar_to_paper_id':1}]}}})
    payload=BenchmarkReader(root).overlay(q)
    assert 'violates' not in payload and 'similar_to_paper_id' not in payload and 'paper_id' in payload
    assert coverage(['e1','e1','e2'],['e1','e3'])==.5


def test_invalid_config_controls():
    for kw in ({'ks':(True,)},{'ks':(0,)},{'ks':(1,1)},{'query_ids':('x','x')},{'splits':()}, {'mode':'paper_test','splits':('validation',)}):
        with pytest.raises(ValidationError):config(**kw)


def test_release_export_binding_and_missing_human_review(tmp_path):
    from scripts.prepare_experiment_release import prepare_release
    root=fixture_benchmark(tmp_path/'data/benchmark');reader=BenchmarkReader(root)
    release=release_document(reader)
    exported=tmp_path/'export.json'
    write(exported,{'benchmark':reader.manifest['benchmark_version'],'decisions':release['decisions']})
    output=tmp_path/'reviews/release.json'
    result=prepare_release(root,[exported],output,released_by='Fixture reviewer',leakage_adjudicated=True)
    assert result['verified']==2 and output.exists()
    with pytest.raises(ValueError):prepare_release(root,[exported],output,released_by='Fixture reviewer',leakage_adjudicated=True)
    write(exported,{'benchmark':reader.manifest['benchmark_version'],'decisions':release['decisions'][:1]})
    with pytest.raises(ValueError):prepare_release(root,[exported],tmp_path/'reviews/incomplete.json',released_by='Fixture reviewer',leakage_adjudicated=True)
    assert not (tmp_path/'reviews/incomplete.json').exists()


def test_system_fingerprint_config_and_event_validation(tmp_path):
    root=fixture_benchmark(tmp_path/'benchmark');execute(tmp_path,root=root)
    class Changed(SyntheticSystem):fingerprint='different-response-contract'
    with pytest.raises(ValueError,match='Incompatible'):execute(tmp_path,root=root,system=Changed())
    with pytest.raises(ValidationError):RunEvent(timestamp='2026-01-01',experiment_id='x',event='started')
    with pytest.raises(ValidationError):RunEvent(timestamp=datetime.now(timezone.utc),experiment_id='x',event='unknown')


def test_dataset_version_mismatch_rejected(tmp_path):
    from research.evaluation.aggregate import aggregate
    records=materialize(execute(tmp_path))
    changed=records[1].model_copy(update={'provenance':{**records[1].provenance,'dataset_version':'other'}})
    with pytest.raises(ValueError):aggregate([records[0],changed])


def test_unobserved_evidence_is_not_measured_empty():
    q=query(gold_evidence={'evidence_ids':['e1']})
    unobserved=compute_metrics(q,SystemOutput(answer_ids=(1,)),config(),1)
    observed_empty=compute_metrics(q,SystemOutput(answer_ids=(1,),evidence=()),config(),1)
    assert unobserved['evidence_coverage'] is None
    assert observed_empty['evidence_coverage']==0
