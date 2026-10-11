"""Operational scheduling only; no credentials, real sleeping or API requests."""
import json
import httpx
import pytest
from scripts.run_phase8_v2 import Gate, StopBatch, duration
from research.baselines.config import BaselineOptions

class Clock:
    value = 0.
    def now(self): return self.value
    def sleep(self, seconds): self.value += seconds

def fixture(tmp_path, **headers):
    clock=Clock()
    values={'x-ratelimit-limit-tokens':'8000','x-ratelimit-remaining-tokens':'7900',
        'x-ratelimit-reset-tokens':'1s','x-ratelimit-remaining-requests':'999'}
    values.update(headers)
    return Gate(tmp_path, values, set(), clock.now, clock.sleep),clock

def dispatch(gate):
    gate.before(BaselineOptions(), 'q', '{"modality_intermediate_answers":[]}', 42)

def test_initial_and_subsequent_spacing(tmp_path):
    gate,clock=fixture(tmp_path)
    dispatch(gate);assert clock.value==90
    dispatch(gate);assert clock.value==180

def test_longer_token_reset_and_retry_after(tmp_path):
    gate,clock=fixture(tmp_path,**{'x-ratelimit-remaining-tokens':'0','x-ratelimit-reset-tokens':'2m','retry-after':'180'})
    dispatch(gate);assert clock.value==181

def test_429_persisted_and_propagates_beyond_exception_handlers(tmp_path):
    gate,_=fixture(tmp_path);dispatch(gate)
    gate.key='gsk_TESTSECRET'
    response=httpx.Response(429,headers={'retry-after':'60','x-ratelimit-limit-tokens':'8000'},
        json={'error':{'message':'gsk_TESTSECRET org_example rate limit'}})
    with pytest.raises(StopBatch):gate.response(response)
    row=json.loads((tmp_path/'01.json').read_text())
    assert row['http_status']==429 and row['headers']['retry-after']=='60'
    assert 'gsk_TESTSECRET' not in row['sanitized_error_body'] and 'org_example' not in row['sanitized_error_body']
    assert not issubclass(StopBatch,Exception)

def test_success_keeps_headers_usage_finish_reason(tmp_path):
    gate,_=fixture(tmp_path);dispatch(gate)
    gate.response(httpx.Response(200,headers={'x-ratelimit-limit-tokens':'8000','x-ratelimit-remaining-tokens':'7000'},
        json={'usage':{'prompt_tokens':72},'choices':[{'finish_reason':'length'}]}))
    row=json.loads((tmp_path/'01.json').read_text())
    assert row['usage']['prompt_tokens']==72 and row['finish_reasons']==['length']

def test_budget_and_unknown_state_stop_before_dispatch(tmp_path):
    gate,_=fixture(tmp_path,**{'x-ratelimit-remaining-tokens':None})
    with pytest.raises(StopBatch):dispatch(gate)
    assert gate.count==0
    gate,_=fixture(tmp_path)
    with pytest.raises(StopBatch):gate.before(BaselineOptions(),'q','{"modality_intermediate_answers":["'+'X'*30000+'"]}',42)
    assert gate.count==0

def test_reset_units():
    assert duration('1m26.4s')==86.4 and duration('547ms')==.547
    assert duration('2h')==7200 and duration('60')==60
    assert duration('invalid') is None
