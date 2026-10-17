"""Serialized, durable Groq stages; 90s pacing and measured-content token bounds.

Operational revision 2 (groq-admission-probe-v1): Groq did not charge a 7,000-token
max_completion_tokens at admission (HTTP 200 for prompt ~1,543 + cap 7,000 > 8,000 TPM).
Pre-dispatch requirement is therefore exact local content tokens + a fixed 128-token
provider-overhead reserve (102 measured in 12/12 research-shaped requests + 26 stated
allowance). The scientific 1,024 completion cap is unchanged and is still sent; its actual
use is debited from the minute bucket by the provider and observed in the response headers.
This never changes scientific payloads.

Operational revision 3: (a) the approved maximum counts SUCCESSFUL calls only, as the frozen plan
states (maximum_successful_calls); a rate-limited attempt produced no model output and is retried
later as the byte-identical payload, within a separate allowance of rate-limited attempts. (b) Groq's
200k tokens/day limit is not exposed in response headers, so a local rolling 24-hour ledger pauses the
run cleanly before a request could cross the daily budget; the run resumes the next day. Neither change
alters any payload; failed or ambiguous dispatches still stop for human review and are never retried.

Operational revision 4: replay_only mode. After the query-major prefetch (research/repair/schedule.py),
the runner replays stored responses; in replay_only mode a payload without a completed stored response
stops the run instead of being sent, which proves the replayed payloads are the ones sent.
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

OVERHEAD_RESERVE=128  # 102 measured provider-minus-local tokens (12/12) + 26 explicit allowance

def pre_dispatch_tokens(content_tokens):
    return content_tokens+OVERHEAD_RESERVE

DAILY_TOKEN_BUDGET=190_000  # of Groq's 200,000 tokens/day; 10k margin for usage this ledger cannot see
MAX_RATE_LIMITED_ATTEMPTS=20
WINDOW_SECONDS=86_400

def write(path,row):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    durable_write(path,canonical_json(row)+'\n')

class Dispatcher:
    daily_budget=DAILY_TOKEN_BUDGET;max_rate_limited=MAX_RATE_LIMITED_ATTEMPTS;replay_only=False
    model='openai/gpt-oss-120b';spacing=90

    def __init__(self,root,initial_headers,max_requests,local=False):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.maximum=max_requests;self.initial=initial_headers
        self.encoder=tiktoken.get_encoding('o200k_harmony')
        if local:
            # Local model (research/local_llm.py): same request/response contract; no provider quota or pacing.
            from research.local_llm import LocalClient,LOCAL_MODEL
            self.key='local-no-key';self.client=LocalClient();self.model=LOCAL_MODEL;self.spacing=0;self.daily_budget=10**12
            self.ready=time.time()
            return
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
        payload={'model':self.model,'temperature':0,'seed':seed,'max_completion_tokens':cap,
            'reasoning_effort':'low','response_format':{'type':'json_object'},
            'messages':[{'role':'system','content':system},{'role':'user','content':user}]}
        identity=content_hash({'stage':stage,'payload':payload});path=self.root/'stages'/(identity+'.json')
        with FileLock(str(self.root/'dispatch.lock'),timeout=0):
            if path.exists():
                old=json.loads(path.read_text(encoding='utf-8'))
                if old['status']=='complete':return old['raw'],old['usage'],True
                if old['status']!='rate_limited':raise Paused('Ambiguous or failed dispatch requires review: '+identity)
            if self.replay_only:raise Paused('Replay found no completed provider response for this exact payload: '+identity)
            state_path=self.root/'state.json'
            state=json.loads(state_path.read_text()) if state_path.exists() else {'headers':self.initial,'observed':0.,'last_start':0.,'requests':0}
            headers=state['headers'];limit=min(8000,int(headers.get('x-ratelimit-limit-tokens','8000')))
            tokens=sum(len(self.encoder.encode(m['content'],disallowed_special=())) for m in payload['messages'])
            reserved=pre_dispatch_tokens(tokens)
            if reserved>limit:raise Paused(f'Unchanged request requires {reserved} pre-dispatch tokens ({tokens} content + {OVERHEAD_RESERVE} overhead reserve); capacity {limit}; cannot repair by waiting')
            successes=state.get('successes',0);limited=state.get('rate_limited',0)
            if successes>=self.maximum:raise Paused('Approved successful-call maximum reached')
            if limited>=self.max_rate_limited:raise Paused('Rate-limited attempt allowance exhausted; review required')
            now=time.time();window=[e for e in state.get('ledger',[]) if e[0]>now-WINDOW_SECONDS]
            used=sum(e[1] for e in window);need=reserved+cap  # conservative: full completion cap
            if used+need>self.daily_budget:
                resume=datetime.fromtimestamp(min(e[0] for e in window)+WINDOW_SECONDS,timezone.utc).isoformat() if window else 'now'
                raise Paused(f'Daily token budget: {used} provider tokens in the last 24 h + {need} needed > {self.daily_budget}; resume after {resume}')
            target=max(self.ready,state['last_start']+self.spacing)
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
                'measured_content_tokens':tokens,'completion_cap':cap,'daily_window_tokens_before':used,'admission_policy':'content+128; completion cap not charged at admission (groq-admission-probe-v1)','pacing_seconds':started-wait,'sequence':state['requests']}
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
            try:row['bucket_debit_observed']=limit-int(observed['x-ratelimit-remaining-tokens'])
            except (KeyError,ValueError):row['bucket_debit_observed']=None
            state.update(headers=observed or headers,observed=time.time())
            if row['status']=='complete':
                state['successes']=successes+1
                usage=row['usage'];total=(usage['input_tokens'] or 0)+(usage['output_tokens'] or 0) if usage['input_tokens'] is not None else reserved+cap
                charged=max(total,row['bucket_debit_observed'] or 0)  # bucket debit includes the provider's unexplained extra
            else:
                charged=0
                if row['status']=='rate_limited':state['rate_limited']=limited+1
            row['daily_ledger_tokens']=charged
            state['ledger']=[e for e in state.get('ledger',[]) if e[0]>time.time()-WINDOW_SECONDS]+[[started,charged]]
            write(self.root/'attempts'/f"{state['requests']:05d}.json",row);write(path,row);write(state_path,state)
            print('GROQ',stage,row['status'],row.get('http_status'),flush=True)
            if row['status']!='complete':raise Paused('Stage paused; durable record preserved: '+identity)
            return row['raw'],row['usage'],False

    def close(self):self.client.close()
