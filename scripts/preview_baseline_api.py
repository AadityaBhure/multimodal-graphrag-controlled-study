"""Prepare auditable Groq requests from read-only offline results; no network access."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.evaluation.benchmark import BenchmarkReader,read_json,digest
from research.evaluation.contracts import RunRecord
from research.experiments.runner import write
from research.baselines.generation import PROMPT

if __name__=='__main__':
    qid='generated:69a22c3b4989b07ed6c3:normal'
    reader=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark')
    q=next(q for q in reader.records('validation') if q.query_id==qid)
    payloads=[]
    for baseline in ('B1','B2','B3','B4'):
        folder=ROOT/f'documentation/phase6/validated/{baseline}'
        records=[RunRecord.model_validate_json(line) for line in (folder/'records.jsonl').read_text(encoding='utf-8').splitlines()]
        r=next(r for r in records if r.query_id==qid)
        assert not r.errors
        payload={'model':'openai/gpt-oss-120b','temperature':0,'seed':r.query_seed,'max_completion_tokens':1024,
            'reasoning_effort':'low','response_format':{'type':'json_object'},'messages':[{'role':'system','content':PROMPT},
                {'role':'user','content':'QUESTION\n'+q.question+'\n\nEVIDENCE\n'+r.output.context}]}
        path=ROOT/f'documentation/phase6/api_payload_preview/{baseline}.json';path.parent.mkdir(exist_ok=True,parents=True);write(path,payload)
        payloads.append({'baseline':baseline,'payload_sha256':digest(path),'question_id':qid,'split':'validation',
            'context_characters':len(r.output.context),'evidence_ids':r.evidence_ids,'source_type':q.provenance['source']})
    source=read_json(ROOT/'data/MMG_STARK_MAG/raw/stark_mag/raw_manifest.json')
    write(ROOT/'documentation/phase6/api_payload_preview/provenance.json',{'destination':'https://api.groq.com/openai/v1/chat/completions',
        'dataset_repository':source['repository'],'dataset_revision':source['dataset_revision'],'representation_manifest_sha256':reader.manifest['representation_manifest_sha256'],
        'payloads':payloads,'credentials_in_payload_files':False,'number_of_requests':4,'max_total_completion_tokens':4096,
        'scope':'Public academic dataset evidence and a generated validation question; no local credentials or private project documents in messages.'})
    print('Prepared four exact public-dataset request previews. No API calls made.')
