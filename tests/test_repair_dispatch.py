from types import SimpleNamespace
import json
import pytest
from research.repair import dispatch

def dispatcher(tmp_path,monkeypatch):
    clock=[1000.]
    monkeypatch.setattr(dispatch.time,'time',lambda:clock[0])
    monkeypatch.setattr(dispatch.time,'sleep',lambda n:clock.__setitem__(0,clock[0]+n))
    d=object.__new__(dispatch.Dispatcher);d.root=tmp_path;d.maximum=4;d.ready=1090.;d.key='fixture-secret'
    d.initial={'x-ratelimit-limit-tokens':'8000','x-ratelimit-remaining-tokens':'8000','x-ratelimit-remaining-requests':'999'}
    d.encoder=SimpleNamespace(encode=lambda text,**kw:list(text));calls=[]
    result=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"keywords":["x"]}'),finish_reason='stop')],usage=SimpleNamespace(prompt_tokens=10,completion_tokens=2))
    def create(**kw):
        calls.append((clock[0],kw));return SimpleNamespace(parse=lambda:result,status_code=200,headers=d.initial)
    d.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=create))))
    return d,calls,clock

def test_pacing_and_completed_resume(tmp_path,monkeypatch):
    d,calls,clock=dispatcher(tmp_path,monkeypatch)
    first=d.call('one','system','user',42,1024)
    assert d.call('one','system','user',42,1024)[2] is True
    d.call('two','system','user',42,1024)
    assert len(calls)==2 and calls[0][0]==1090 and calls[1][0]-calls[0][0]>=90

def test_oversized_unchanged_payload_never_sent(tmp_path,monkeypatch):
    d,calls,_=dispatcher(tmp_path,monkeypatch)
    with pytest.raises(dispatch.Paused,match='cannot repair by waiting'):d.call('large','s','x'*8000,42,1024)
    assert not calls

def test_ambiguous_dispatch_not_retried(tmp_path,monkeypatch):
    d,calls,_=dispatcher(tmp_path,monkeypatch)
    d.call('one','s','u',42,1024)
    p=next((tmp_path/'stages').glob('*.json'));row=json.loads(p.read_text());row['status']='dispatched';p.write_text(json.dumps(row))
    with pytest.raises(dispatch.Paused,match='Ambiguous'):d.call('one','s','u',42,1024)
    assert len(calls)==1

def test_429_preserves_headers_and_stops(tmp_path,monkeypatch):
    d,calls,_=dispatcher(tmp_path,monkeypatch)
    class Failure(Exception):
        status_code=429
        body='fixture-secret quota'
        response=SimpleNamespace(headers={**d.initial,'retry-after':'90'})
    def fail(**kwargs):raise Failure()
    d.client.chat.completions.with_raw_response.create=fail
    with pytest.raises(dispatch.Paused):d.call('one','s','u',42,1024)
    row=json.loads(next((tmp_path/'stages').glob('*.json')).read_text())
    assert row['status']=='rate_limited' and row['headers']['retry-after']=='90'
    assert 'fixture-secret' not in row['error']


def test_completion_cap_not_charged_at_admission_but_overhead_reserve_is(tmp_path,monkeypatch):
    # groq-admission-probe-v1: pre-dispatch = content tokens + 128 <= 8000; the 1024 cap is still sent.
    d,calls,_=dispatcher(tmp_path,monkeypatch)
    d.call('fits','s','x'*7871,42,1024)           # 7872 content + 128 == 8000 -> admitted although +1024 would not fit
    assert len(calls)==1 and calls[0][1]['max_completion_tokens']==1024
    row=json.loads(next((tmp_path/'stages').glob('*.json')).read_text())
    assert row['reserved_tokens']==8000 and row['completion_cap']==1024 and 'bucket_debit_observed' in row
    with pytest.raises(dispatch.Paused,match='cannot repair by waiting'):d.call('too-large','s','x'*7872,42,1024)  # 8001
    assert len(calls)==1

def test_pre_dispatch_rule_constants():
    assert dispatch.OVERHEAD_RESERVE==128 and dispatch.pre_dispatch_tokens(7028)==7156


# ---------------------------------------------------------------- operational revision 3
def _fail_429(d,headers=None):
    class Failure(Exception):
        status_code=429
        body='daily limit'
        response=SimpleNamespace(headers=headers or d.initial)
    def fail(**kwargs):raise Failure()
    return fail

def test_payload_and_stage_identity_unchanged_byte_for_byte(tmp_path,monkeypatch):
    # Revision 3 changes only counting/pausing: the request sent and its stage identity are exactly the v2 ones.
    from research.common.serialization import content_hash
    d,calls,_=dispatcher(tmp_path,monkeypatch)
    d.call('CM-01:final:q','SYS','USER',7,1024)
    expected={'model':'openai/gpt-oss-120b','temperature':0,'seed':7,'max_completion_tokens':1024,'reasoning_effort':'low',
              'response_format':{'type':'json_object'},'messages':[{'role':'system','content':'SYS'},{'role':'user','content':'USER'}]}
    assert calls[0][1]==expected
    assert (tmp_path/'stages'/(content_hash({'stage':'CM-01:final:q','payload':expected})+'.json')).exists()

def test_rate_limited_attempt_does_not_consume_a_successful_call_and_retries_identical_payload(tmp_path,monkeypatch):
    d,calls,_=dispatcher(tmp_path,monkeypatch);d.maximum=1
    ok=d.client.chat.completions.with_raw_response.create
    sent=[]
    def fail(**kw):sent.append(kw);return _fail_429(d)()
    d.client.chat.completions.with_raw_response.create=fail
    with pytest.raises(dispatch.Paused):d.call('one','s','u',42,1024)
    d.client.chat.completions.with_raw_response.create=ok
    raw,_,reused=d.call('one','s','u',42,1024)          # v2 would stop here: 'Approved request maximum reached'
    assert not reused and calls[-1][1]==sent[0]          # byte-identical resend of the refused request
    state=json.loads((tmp_path/'state.json').read_text())
    assert state['successes']==1 and state['rate_limited']==1 and state['requests']==2
    with pytest.raises(dispatch.Paused,match='successful-call maximum'):d.call('two','s','u',42,1024)
    assert len(calls)==1 and len(list((tmp_path/'attempts').glob('*.json')))==2   # every attempt kept

def test_rate_limited_allowance_is_bounded(tmp_path,monkeypatch):
    d,calls,_=dispatcher(tmp_path,monkeypatch);d.max_rate_limited=2
    d.client.chat.completions.with_raw_response.create=_fail_429(d)
    for _ in range(2):
        with pytest.raises(dispatch.Paused,match='Stage paused'):d.call('one','s','u',42,1024)
    with pytest.raises(dispatch.Paused,match='allowance exhausted'):d.call('one','s','u',42,1024)
    assert json.loads((tmp_path/'state.json').read_text())['requests']==2   # third attempt never sent

def test_daily_budget_pauses_before_sending_and_resumes_after_window(tmp_path,monkeypatch):
    d,calls,clock=dispatcher(tmp_path,monkeypatch);d.maximum=10
    d.daily_budget=1170          # need per call = (10 content + 128) + 1024 cap = 1162; each completed call charges 12
    d.call('one','system','user',42,1024)
    with pytest.raises(dispatch.Paused,match='Daily token budget: 12 provider tokens'):d.call('two','system','user',42,1024)
    assert len(calls)==1
    clock[0]+=86_401
    d.call('two','system','user',42,1024)
    assert len(calls)==2
    rows=[json.loads(p.read_text()) for p in sorted((tmp_path/'attempts').glob('*.json'))]
    assert [r['daily_ledger_tokens'] for r in rows]==[12,12] and rows[1]['daily_window_tokens_before']==0

def test_daily_ledger_charges_observed_bucket_debit_when_larger(tmp_path,monkeypatch):
    d,calls,_=dispatcher(tmp_path,monkeypatch)
    d.initial={**d.initial,'x-ratelimit-remaining-tokens':'7500'}   # provider debited 500 > usage total 12
    d.call('one','s','u',42,1024)
    row=json.loads(next((tmp_path/'attempts').glob('*.json')).read_text())
    assert row['bucket_debit_observed']==500 and row['daily_ledger_tokens']==500

def test_revision3_constants():
    assert dispatch.DAILY_TOKEN_BUDGET==190_000 and dispatch.MAX_RATE_LIMITED_ATTEMPTS==20
