"""Operational pacing wrapper; frozen fusion, payloads and runner are unchanged."""
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.baselines.config import BaselineOptions, groq_key
from research.baselines.generation import GroqGenerator, PROMPT
from research.common.serialization import content_hash
from research.evaluation.benchmark import digest
from research.experiments.config import load_runner_config
from research.experiments.runner import run, write, code_provenance
from research.rq2.contracts import Options
from research.rq2.generation import Journal
from research.rq2.system import FusionSystem
from scripts.prepare_phase8 import load_inputs

D = ROOT / 'documentation/phase8_generation_v2'

class StopBatch(BaseException):
    pass

def duration(value):
    if value is None: return None
    value = str(value)
    if re.fullmatch(r'\d+(?:\.\d+)?', value): return float(value)
    parts = re.findall(r'(\d+(?:\.\d+)?)(ms|s|m|h|d)', value)
    if ''.join(a+b for a,b in parts) != value: return None
    return sum(float(n)*{'ms':.001,'s':1,'m':60,'h':3600,'d':86400}[u] for n,u in parts)

class Gate:
    def __init__(self, root, headers, previews, clock=time.monotonic, sleep=time.sleep):
        self.root, self.headers, self.previews = root, headers, previews
        self.clock, self.sleep = clock, sleep
        self.created = clock(); self.last = None; self.observed = self.created
        self.count = 0; self.active = None
        self.key = None

    def sanitize(self, value):
        value = str(value)
        if self.key: value = value.replace(self.key, '[REDACTED]')
        value = re.sub(r'gsk_[A-Za-z0-9_-]+', '[REDACTED_KEY]', value)
        return re.sub(r'\b(?:org|proj)_[A-Za-z0-9_-]+', '[REDACTED_ACCOUNT_ID]', value)

    def before(self, options, question, context, seed):
        payload = {'model':options.model, 'temperature':0, 'seed':seed,
            'max_completion_tokens':options.max_completion_tokens, 'reasoning_effort':'low',
            'response_format':{'type':'json_object'}, 'messages':[{'role':'system','content':PROMPT},
                {'role':'user','content':'QUESTION\n'+question+'\n\nEVIDENCE\n'+context}]}
        signature = content_hash(payload)
        static = signature in self.previews
        if not static:
            # Only a frozen CF-03 final may be dynamic. Source algorithm constructs it.
            obj = json.loads(context)
            if set(obj) != {'modality_intermediate_answers'} or options.max_completion_tokens != 1024:
                raise StopBatch('Unapproved payload')
        estimate = math.ceil(sum(len(m['content']) for m in payload['messages'])/4)
        needed = math.ceil(estimate*1.25) + options.max_completion_tokens
        limit = min(8000, int(self.headers.get('x-ratelimit-limit-tokens', '8000')))
        if needed > limit: raise StopBatch('Unchanged request exceeds conservatively estimated TPM capacity')
        if self.count >= 16: raise StopBatch('Request cap reached')
        target = max(self.created+90, (self.last+90) if self.last is not None else self.created+90)
        token_reset = duration(self.headers.get('x-ratelimit-reset-tokens'))
        remaining = self.headers.get('x-ratelimit-remaining-tokens')
        if remaining is None: raise StopBatch('Token availability unknown')
        if needed > int(remaining):
            if token_reset is None: raise StopBatch('Token reset unknown')
            target = max(target, self.observed+token_reset+1)
        request_remaining = self.headers.get('x-ratelimit-remaining-requests')
        if request_remaining is None: raise StopBatch('Request quota unknown')
        if int(request_remaining) < 1:
            reset = duration(self.headers.get('x-ratelimit-reset-requests'))
            if reset is None: raise StopBatch('Daily request reset unknown')
            target = max(target, self.observed+reset+1)
        retry = duration(self.headers.get('retry-after'))
        if retry is not None: target = max(target, self.observed+retry+1)
        wait_started = self.clock()
        print('WAIT', self.count+1, 'seconds', round(max(0,target-self.clock()),1), 'reserved_tokens',needed,flush=True)
        while self.clock() < target: self.sleep(min(20,target-self.clock()))
        self.last = self.clock(); self.count += 1
        self.active = {'sequence':self.count,'timestamp':datetime.now(timezone.utc).isoformat(),
            'start_monotonic':self.last,'wait_seconds':self.last-wait_started,'payload_sha256':signature,
            'matches_static_preview':static,'estimated_input_tokens':estimate,'reserved_tokens':needed,
            'completion_cap':options.max_completion_tokens,'prior_headers':dict(self.headers),'status':'dispatching'}
        write(self.root / f'{self.count:02d}.json', self.active)

    def response(self, response):
        response.read()
        headers = {k.lower():self.sanitize(v) for k,v in response.headers.items()
            if 'ratelimit' in k.lower() or 'rate-limit' in k.lower() or k.lower() in ('retry-after','date')}
        self.headers = headers; self.observed = self.clock()
        row = dict(self.active)
        row.update(http_status=response.status_code,headers=headers,status='response_received',
            response_elapsed_seconds=self.observed-self.last)
        try: body = response.json()
        except Exception: body = {'unparsed_body':response.text}
        if response.status_code >= 400:
            row['sanitized_error_body'] = self.sanitize(json.dumps(body))
        else:
            row['usage'] = body.get('usage')
            row['finish_reasons'] = [c.get('finish_reason') for c in body.get('choices',[])]
        write(self.root / f'{self.count:02d}.json',row)
        print('RESPONSE',self.count,response.status_code,headers,flush=True)
        if response.status_code == 429: raise StopBatch('HTTP 429: stopped entire v2 batch; no retry')

class PacedGenerator:
    version = GroqGenerator.version
    def __init__(self, options, gate):
        self.options, self.gate = options, gate
        self.inner = GroqGenerator(options)
        self.inner.client._client.event_hooks['response'] = [gate.response]
    def generate(self, question, context, seed):
        self.gate.before(self.options, question, context, seed)
        try: return self.inner.generate(question, context, seed)
        except Exception as exc:
            # No ambiguous network dispatch can be retried or silently continued.
            write(self.gate.root/'transport_stop.json',{'exception_class':type(exc).__name__,
                'message':self.gate.sanitize(str(exc)),'sequence':self.gate.count})
            raise StopBatch('Provider/transport failure: no retry') from None
    def close(self): self.inner.close()

def main():
    plan_path=ROOT/'documentation/groq_diagnostic/rerun_v2/plan.json'
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    assert plan['experiment_version']=='phase8-generation-v2-paced'
    for p,sha in plan['implementations_sha256'].items(): assert digest(ROOT/p)==sha
    assert digest(ROOT/'documentation/phase8/generation_plan.json')==plan['original_plan_sha256']
    assert digest(ROOT/plan['static_payloads_path'])==plan['static_payloads_sha256']
    assert digest(ROOT/'documentation/phase8/bundle_manifest.json')==plan['bundle_manifest_sha256']
    for row in plan['configs']: assert digest(ROOT/row['config_path'])==row['config_sha256']
    D.mkdir(exist_ok=True)
    with (D/'execution_started.json').open('x',encoding='utf-8') as f:
        json.dump({'plan_sha256':digest(plan_path),'timestamp':datetime.now(timezone.utc).isoformat(),'authorization':'user approved paced v2 only'},f)
    protected={str(p.relative_to(ROOT)):digest(p) for folder in ('documentation/phase8','configs/rq2','research/rq2')
        for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    write(D/'protected_before.json',protected)
    http_dir=D/'http_dispatches';http_dir.mkdir()
    previews=json.loads((ROOT/plan['static_payloads_path']).read_text(encoding='utf-8'))['payloads']
    signatures={content_hash({k:v for k,v in p.items() if k not in ('query_id','method','stage')}) for p in previews}
    initial=json.loads((ROOT/'documentation/groq_diagnostic/diagnostic.json').read_text())['completion']['headers']
    gate=Gate(http_dir,initial,signatures);gate.key=groq_key()
    inputs=load_inputs();inputs={qid:inputs[qid] for qid in plan['query_ids']}
    generators=[PacedGenerator(BaselineOptions(),gate),PacedGenerator(BaselineOptions(max_completion_tokens=220),gate)]
    journal=Journal(ROOT/plan['journal_directory'],*generators)
    provenance=code_provenance();provenance['operational_pacing_script_sha256']=digest(Path(__file__))
    try:
        for row in plan['configs']:
            config=load_runner_config(ROOT/row['config_path'])
            run(config,ROOT/'data/MMG_STARK_MAG/benchmark',ROOT/row['run_directory'],
                FusionSystem(Options(method=row['method']),inputs,journal),provenance=provenance)
            print('METHOD_COMPLETE',row['method'],flush=True)
        write(D/'execution_status.json',{'status':'FINISHED','requests':gate.count})
    except StopBatch as exc:
        write(D/'execution_status.json',{'status':'STOPPED_FOR_REVIEW','reason':str(exc),'requests':gate.count})
        print('STOPPED',str(exc),flush=True)
    finally:
        for g in generators:g.close()
        assert all(digest(ROOT/p)==sha for p,sha in protected.items()),'Protected artifact changed'
        write(D/'protected_after.json',{'verified_files':len(protected),'unchanged':True})

if __name__=='__main__':main()
