"""Serialized, durable Groq stages; 90s pacing and measured-content token bounds.

Exact local content tokens + 256 chat-envelope reserve + unchanged completion
cap replace the old character heuristic. This never changes scientific payloads.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,time,re
import tiktoken
from filelock import FileLock
from research.common.serialization import canonical_json,content_hash
from research.baselines.config import groq_key
from research.experiments.config import durable_write
from scripts.run_phase8_v2 import duration

class Paused(BaseException):pass

def write(path,row):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    durable_write(path,canonical_json(row)+'\n')

class Dispatcher:
    def __init__(self,root,initial_headers,max_requests):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.maximum=max_requests;self.initial=initial_headers
        self.encoder=tiktoken.get_encoding('o200k_harmony')
        self.key=groq_key()
        if not self.key:raise Paused('Groq credential missing')
        from groq import Groq
        self.client=Groq(api_key=self.key,base_url='https://api.groq.com',timeout=60,max_retries=0)
        self.ready=time.time()+90

    def sanitize(self,value):
        s=str(value).replace(self.key,'[REDACTED]')
        s=re.sub(r'gsk_[A-Za-z0-9_-]+','[REDACTED]',s)
        return re.sub(r'\b(?:org|proj)_[A-Za-z0-9_-]+','[REDACTED_ACCOUNT]',s)

    def call(self,stage,system,user,seed,cap):
        payload={'model':'openai/gpt-oss-120b','temperature':0,'seed':seed,'max_completion_tokens':cap,
            'reasoning_effort':'low','response_format':{'type':'json_object'},
            'messages':[{'role':'system','content':system},{'role':'user','content':user}]}
        identity=content_hash({'stage':stage,'payload':payload});path=self.root/'stages'/(identity+'.json')
        with FileLock(str(self.root/'dispatch.lock'),timeout=0):
            if path.exists():
                old=json.loads(path.read_text(encoding='utf-8'))
                if old['status']=='complete':return old['raw'],old['usage'],True
                if old['status']!='rate_limited':raise Paused('Ambiguous or failed dispatch requires review: '+identity)
            state_path=self.root/'state.json'
            state=json.loads(state_path.read_text()) if state_path.exists() else {'headers':self.initial,'observed':0.,'last_start':0.,'requests':0}
            headers=state['headers'];limit=min(8000,int(headers.get('x-ratelimit-limit-tokens','8000')))
            tokens=sum(len(self.encoder.encode(m['content'],disallowed_special=())) for m in payload['messages'])
            reserved=tokens+256+cap
            if reserved>limit:raise Paused(f'Unchanged request requires {reserved} reserved tokens; capacity {limit}; cannot repair by waiting')
            if state['requests']>=self.maximum:raise Paused('Approved request maximum reached')
            target=max(self.ready,state['last_start']+90)
            for kind,need in [('tokens',reserved),('requests',1)]:
                remaining=headers.get('x-ratelimit-remaining-'+kind)
                if remaining is None:raise Paused('Quota state unavailable')
                if int(remaining)<need:
                    reset=duration(headers.get('x-ratelimit-reset-'+kind))
                    if reset is None:raise Paused('Quota reset unavailable')
                    target=max(target,state['observed']+reset+1)
            retry=duration(headers.get('retry-after'))
            if retry is not None:target=max(target,state['observed']+retry+1)
            wait=time.time()
            while time.time()<target:
                print('PACING',stage,round(target-time.time(),1),flush=True);time.sleep(min(30,target-time.time()))
            started=time.time();state['requests']+=1;state['last_start']=started
            row={'stage':stage,'identity':identity,'status':'dispatched','payload':payload,
                'timestamp':datetime.now(timezone.utc).isoformat(),'reserved_tokens':reserved,
                'measured_content_tokens':tokens,'pacing_seconds':started-wait,'sequence':state['requests']}
            write(path,row);write(state_path,state)
            try:
                response=self.client.chat.completions.with_raw_response.create(**payload)
                result=response.parse();elapsed=(time.time()-started)*1000
                row.update(status='complete',http_status=response.status_code,raw=result.choices[0].message.content or '',
                    finish_reason=result.choices[0].finish_reason,usage={'llm_calls':1,'generation_ms':elapsed,
                        'input_tokens':result.usage.prompt_tokens if result.usage else None,
                        'output_tokens':result.usage.completion_tokens if result.usage else None,
                        'token_measurement_source':'groq.response.usage' if result.usage else None})
            except Exception as exc:
                response=getattr(exc,'response',None);status=getattr(exc,'status_code',None)
                row.update(status='rate_limited' if status==429 else 'failed_or_ambiguous',http_status=status,
                    exception_class=type(exc).__name__,error=self.sanitize(getattr(exc,'body',None) or str(exc)))
            observed={k.lower():self.sanitize(v) for k,v in response.headers.items() if 'ratelimit' in k.lower() or k.lower() in ('retry-after','date')} if response is not None else {}
            row['headers']=observed
            state.update(headers=observed or headers,observed=time.time())
            write(self.root/'attempts'/f"{state['requests']:05d}.json",row);write(path,row);write(state_path,state)
            print('GROQ',stage,row['status'],row.get('http_status'),flush=True)
            if row['status']!='complete':raise Paused('Stage paused; durable record preserved: '+identity)
            return row['raw'],row['usage'],False

    def close(self):self.client.close()
