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
