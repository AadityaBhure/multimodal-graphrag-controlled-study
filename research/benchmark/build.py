"""Phase 4 benchmark assembly, source preservation and immutable release files."""
import ast
from collections import Counter
import csv
from copy import deepcopy
import json
from pathlib import Path
import shutil

from research.benchmark.contracts import BenchmarkQuery
from research.benchmark.construction import MODALITIES,generate_bases,intersection,impossible_mutation,wording
from research.benchmark.stress import StressBuilder
from research.common.serialization import canonical_json,content_hash
from scripts.audit_stark_mag import digest

SPLITS=('train','validation','test','human_test')


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    payload=(canonical_json(value)+'\n').encode('utf-8')
    if path.exists() and path.read_bytes()==payload:return
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_bytes(payload);temporary.replace(path)


def jsonl(path,records):
    path.parent.mkdir(parents=True,exist_ok=True)
    payload=''.join(canonical_json(r)+'\n' for r in records).encode('utf-8')
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_bytes(payload);temporary.replace(path)


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def read_official(source):
    raw=source.root/'raw/stark_mag/qa/mag'
    rows={}
    for name,file in [('synthetic','stark_qa.csv'),('human','stark_qa_human_generated_eval.csv')]:
        with (raw/'stark_qa'/file).open(encoding='utf-8',newline='') as stream:
            rows[name]=list(csv.DictReader(stream))
    splits={}
    for name,file in [('train','train.index'),('validation','val.index'),('test','test.index')]:
        for value in (raw/'split'/file).read_text().split():
            assert value not in splits
            splits[value]=name
    assert len(splits)==len(rows['synthetic'])==13323 and len(rows['human'])==84
    return rows,splits


def human_exclusion(row,types):
    answers=ast.literal_eval(row['answer_ids'])
    entity_types=[types.get(int(i),'missing') for i in answers]
    if all(t=='paper' for t in entity_types):return None
    return {'source_query_id':row['id'],'reason':'whole_query_contains_non_paper_answer',
            'original_answer_ids':answers,'original_answer_entity_types':entity_types,'original_record':row,'answers_repaired':False}


def official_queries(source,output):
    originals,assignments=read_official(source)
    raw=source.root/'raw/stark_mag/qa/mag'
    for path in sorted(raw.rglob('*')):
        if path.is_file():
            target=output/'source_preservation'/path.relative_to(raw)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    jsonl(output/'official_human_original.jsonl',originals['human'])
    jsonl(output/'official_synthetic_original.jsonl',originals['synthetic'])
    all_ids=sorted({int(i) for records in originals.values() for r in records for i in ast.literal_eval(r['answer_ids'])})
    types=dict(source.con.execute('SELECT stark_node_id,entity_type FROM registry WHERE stark_node_id IN (SELECT unnest(?))',[all_ids]).fetchall())
    result=[];exclusions=[]
    for kind,records in originals.items():
        for row in records:
            answers=ast.literal_eval(row['answer_ids']); answer_types=[types.get(int(i),'missing') for i in answers]
            assert len(answers)==len(set(answers)), 'Official duplicated answers require explicit preservation handling'
            if any(t!='paper' for t in answer_types):
                assert kind=='human','Unexpected non-paper synthetic query'
                exclusions.append(human_exclusion(row,types))
                continue
            split='human_test' if kind=='human' else assignments[row['id']]
            query={'query_id':f'official:{kind}:{row["id"]}','source_query_id':row['id'],'split':split,
                   'question':row['query'],'answerable':bool(answers),'modalities':[],'modality_class':'unverified',
                   'reasoning':{'hop_count':None,'multi_hop':None,'complexity':'unverified','difficulty':'unverified'},
                   'stress':{'noisy':False,'conflict':False,'unanswerable':not bool(answers)},'gold_answer_ids':answers,
                   'gold_evidence':{'official_original_answer_ids':answers,'source_record_id':row['id']},
                   'provenance':{'source':'official_human' if kind=='human' else 'official_synthetic','construction_source':'stark_original',
                                 'original_row_sha256':content_hash(row),'original_split':split,'annotation_status':'requires_human_review',
                                 'gold_status':'official_supplied_identity_verified_not_semantically_recomputed',
                                 'source_path':('official_human_original.jsonl' if kind=='human' else 'official_synthetic_original.jsonl')}}
            result.append(BenchmarkQuery.model_validate(query).model_dump(mode='json'))
    write(output/'human_exclusions.json',exclusions)
    return result,exclusions


def persist_candidates(source,output,conditions):
    sets=source.candidates(conditions);refs={}
    for modality,values in sets.items():
        values=sorted(values);key=content_hash(values)
        path=Path('construction_records/candidate_sets')/(key+'.json')
        write(output/path,values)
        refs[modality]={'path':path.as_posix(),'sha256':digest(output/path),'count':len(values)}
    return sets,refs


def generated_query(source,output,record,variant='normal',mutation=None):
    sets,refs=persist_candidates(source,output,record['conditions']);gold=sorted(intersection(sets))
    base_id='generated:'+record['instance_id'][:20]
    qid=base_id+':'+variant
    condition_path=Path('construction_records')/(qid.replace(':','_')+'.json')
    witnesses={}
    if 'graph' in sets:
        paths=source.graph(record['conditions']['graph'])[1]
        witnesses={str(p):paths[p] for p in gold}
    necessity_witnesses={m:sorted(intersection({k:v for k,v in sets.items() if k!=m})-set(gold))[:5]
                         for m in sets if len(sets)>1 and gold}
    construction={'instance_id':record['instance_id'],'conditions':record['conditions'],'candidate_sets':refs,
                  'operation':'intersection','gold_answer_ids':gold,'template_family':record['template_family'],
                  'graph_witness_paths':witnesses,'modality_necessity_counterexamples':necessity_witnesses,
                  'mutation':mutation,'base_query_id':base_id+':normal','wording_model':None,
                  'wording_after_gold_computation':True,'text_semantics':'explicit case-insensitive abstract claims; no unbounded synonym-completeness claim'}
    write(output/condition_path,construction)
    hops={'train':1,'validation':2,'test':3}[record['split']] if 'graph' in sets else 1
    query={'query_id':qid,'source_query_id':record['instance_id'],'split':record['split'],'question':record['question'],
           'answerable':bool(gold),'modalities':list(MODALITIES[record['modality_class']]),'modality_class':record['modality_class'],
           'reasoning':{'hop_count':hops,'multi_hop':hops>1,'complexity':'single-hop' if hops==1 else 'multi-hop-2' if hops==2 else 'multi-hop-3+','difficulty':'controlled'},
           'stress':{'noisy':variant=='noisy','conflict':variant=='conflict','unanswerable':variant=='unanswerable'},
           'gold_answer_ids':gold,'gold_evidence':{'construction_record':condition_path.as_posix(),'candidate_sets':refs},
           'provenance':{'source':'generated','construction_source':'phase3_programmatic','base_query_id':base_id+':normal',
                         'construction_instance':record['instance_id'],'template_family':record['template_family'],
                         'paired_stress_variant':variant,'gold_status':'recomputed_from_frozen_views','annotation_status':'manual_review_pending'}}
    return BenchmarkQuery.model_validate(query).model_dump(mode='json')


def build(source,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    queries,exclusions=official_queries(source,output)
    records,diagnostics=generate_bases(source)
    stress=StressBuilder(source);coverage=[]
    for record in records:
        normal=generated_query(source,output,record);queries.append(normal)
        sets=source.candidates(record['conditions'])
        noise=stress.noise(record,sets)
        if noise:
            query=generated_query(source,output,record,'noisy')
            path=Path('stress_cases')/(query['query_id'].replace(':','_')+'.json')
            write(output/path,{'base_query_id':normal['query_id'],'distractors':noise,'canonical_data_modified':False})
            query['provenance']['stress_record']=path.as_posix();queries.append(query)
        else:coverage.append({'query':normal['query_id'],'missing_variant':'noisy','reason':'required distractor type unavailable'})
        query=generated_query(source,output,record,'conflict')
        path=Path('stress_cases')/(query['query_id'].replace(':','_')+'.json')
        write(output/path,{'base_query_id':normal['query_id'],**stress.conflict(record)})
        query['provenance']['stress_record']=path.as_posix();queries.append(query)
        impossible=impossible_mutation(source,record)
        if impossible:
            conditions,rule=impossible
            assert not intersection(source.candidates(conditions))
            changed=deepcopy(record);changed['conditions']=conditions;changed['question']=wording(source,conditions,record['split'])
            query=generated_query(source,output,changed,'unanswerable',mutation={'rule':rule,'original_question':normal['question'],
                        'original_conditions':record['conditions'],'original_gold_answer_ids':record['gold'],'canonical_data_modified':False})
            queries.append(query)
        else:coverage.append({'query':normal['query_id'],'missing_variant':'unanswerable','reason':'no verified disjoint mutation'})
    del stress.index
    for split in SPLITS:
        jsonl(output/(split+'.jsonl'),sorted((q for q in queries if q['split']==split),key=lambda q:q['query_id']))
    write(output/'construction_records/generation_diagnostics.json',{'search':diagnostics,'coverage_limitations':coverage})
    return queries,exclusions,records
