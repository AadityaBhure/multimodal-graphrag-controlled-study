"""Construct tiny deterministic fixtures and sample experiments, never benchmark gold."""
from pathlib import Path
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.benchmark.contracts import BenchmarkQuery
from research.common.contracts import EvidenceItem, Provenance
from research.common.serialization import canonical_json
from research.evaluation.benchmark import digest, BenchmarkReader
from research.evaluation.contracts import SystemOutput, Observation, RunRecord, RunEvent, ReleaseMetadata, AgentFusionAnnotations
from research.experiments.config import RunnerConfig
from research.experiments.runner import write, run, materialize
from research.experiments.synthetic import ScriptedSyntheticSystem, SyntheticSystem
from scripts.audit_stark_mag import process_memory


def create():
    root=ROOT/'tests/fixtures/evaluation/benchmark';root.mkdir(parents=True,exist_ok=True)
    items=[]
    for i,(source,stress) in enumerate([('generated','normal'),('generated','noisy'),('generated','conflict'),('generated','unanswerable'),('official_synthetic','normal'),('official_human','normal')]):
        generated=source=='generated'
        items.append(BenchmarkQuery(query_id=f'fixture:{i}',source_query_id=str(i),split='validation' if i<5 else 'human_test',
            question='Synthetic fixture only: select the indicated paper IDs.',answerable=stress!='unanswerable',
            modalities=('text',) if generated else (),modality_class='T' if generated else 'unverified',
            reasoning={'hop_count':1 if generated else None,'multi_hop':False if generated else None,
                       'complexity':'single-hop' if generated else 'unverified','difficulty':'controlled' if generated else 'unverified'},
            stress={n:n==stress for n in ('noisy','conflict','unanswerable')},gold_answer_ids=() if stress=='unanswerable' else (1,2,3),
            gold_evidence={'evidence_ids':['e1','e3']} if generated else {},
            provenance={'source':source,'annotation_status':'fixture_only_not_human_reviewed'}))
    for split in ('train','validation','test','human_test'):
        (root/(split+'.jsonl')).write_text(''.join(q.model_dump_json()+'\n' for q in items if q.split==split),encoding='utf-8')
    files=[{'path':s+'.jsonl','bytes':(root/(s+'.jsonl')).stat().st_size,'sha256':digest(root/(s+'.jsonl'))} for s in ('train','validation','test','human_test')]
    write(root/'benchmark_manifest.json',{'benchmark_version':'phase5-tiny-fixture-v1','content_frozen':True,'files':files,
        'query_file_sha256':{r['path'].removesuffix('.jsonl'):r['sha256'] for r in files},
        'test_content_freeze_id':'synthetic-fixture-only','representation_manifest_sha256':'synthetic-fixture-only'})
    evidence=tuple(EvidenceItem(evidence_id=f'e{i}',canonical_id=f'stark:{i}',source_type='text',content=f'Paper {i}',score=1.,
        provenance=(Provenance(dataset_version='synthetic-fixture-only',source_id=f'e{i}',locator='fixture'),)) for i in (1,2))
    responses={q.query_id:SystemOutput(answer='[1, 2]',answer_ids=(1,2),ranked_paper_ids=(9,2,2,1),evidence=evidence,
        context='Paper 1',retained_evidence_ids=('e1','e1'),context_tokens=2,tokenizer='fixture-whitespace-v1',
        baseline_context_characters=14,baseline_context_source='fixture-explicit-reference',
        observation=Observation(retrieval_calls=0,tool_calls=0,llm_calls=0)).model_dump(mode='json') for q in items}
    responses['fixture:3']=SystemOutput(answer='[]',answer_ids=(),ranked_paper_ids=(),evidence=(),context='',retained_evidence_ids=(),
        observation=Observation(retrieval_calls=0,tool_calls=0,llm_calls=0)).model_dump(mode='json')
    response_path=root.parent/'responses.json';write(response_path,responses)
    config=RunnerConfig(config_id='phase5-scripted-example-v1',system_id='synthetic-scripted',system_version='1',ks=(1,3,5))
    write(ROOT/'configs/phase5-scripted.json',config.model_dump(mode='json'))
    return root,response_path,config


if __name__=='__main__':
    start=time.perf_counter();root,responses,config=create()
    output=ROOT/'documentation/phase5/sample_experiment_v3'
    run(config,root,output,ScriptedSyntheticSystem(responses))
    before=(output/'records.jsonl').read_bytes()
    run(config,root,output,ScriptedSyntheticSystem(responses))
    assert before==(output/'records.jsonl').read_bytes()
    # Read-only integration across all actual generated validation stress variants plus one official query.
    reader=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark')
    queries=list(reader.records('validation'))
    selected=[q.query_id for q in queries if q.provenance['source']=='generated']
    selected.append(next(q.query_id for q in queries if q.provenance['source']=='official_synthetic'))
    smoke=RunnerConfig(config_id='phase5-real-validation-adapter-smoke-v1',system_id='synthetic-fixture',system_version='1',query_ids=tuple(selected))
    write(ROOT/'configs/phase5-validation-smoke.json',smoke.model_dump(mode='json'))
    run(smoke,reader.root,ROOT/'documentation/phase5/validation_smoke_v3',SyntheticSystem())
    for cls in (RunRecord,RunEvent,ReleaseMetadata,AgentFusionAnnotations):
        write(ROOT/f'documentation/phase5/{cls.__name__}.schema.json',cls.model_json_schema())
    records=materialize(output)
    assert not any(r.errors for r in records)
    smoke_records=materialize(ROOT/'documentation/phase5/validation_smoke_v3')
    assert not any(r.errors for r in smoke_records)
    write(ROOT/'documentation/phase5/sample_resources.json',{'elapsed_seconds':time.perf_counter()-start,
        'resources':process_memory(),'fixture_queries':len(records),'real_validation_smoke_queries':len(smoke_records),
        'llm_calls':0,'retrieval_calls':0,'resume_byte_identical':True,
        'warning':'Synthetic infrastructure outputs; not scientific method results.'})
    print('Fixture and actual validation adapter checks complete; zero LLM calls.')
