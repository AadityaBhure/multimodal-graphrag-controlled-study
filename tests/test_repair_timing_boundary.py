"""Initialisation is outside the per-query timer and changes no scientific output."""
import time
from test_repair_cm01 import fixture,encoder
from research.repair.rq1_compliance_v1.cm01 import canonical_units,cosine_scores
from research.repair.rq1_compliance_v1.context import pass_through
from research.repair.rq1_compliance_v1.system import RepairedContextSystem
from research.common.contracts import EvidenceItem,Provenance
from research.common.serialization import content_hash
from research.evaluation.contracts import SystemInput
import json

class SlowReranker:
    def __init__(self):self.loaded=0;self.calls=0
    def load(self):
        time.sleep(.2);self.loaded+=1
    def __call__(self,query,texts):
        self.calls+=1;return [0.]*len(texts)

def data_for():
    p=fixture();units=canonical_units(p);scores=cosine_scores(p.question,units,encoder)
    items=tuple(EvidenceItem(evidence_id=s,source_type=s,canonical_id='stark:1',score=0.,provenance=(Provenance(dataset_version='fixture',source_id='1',locator='fixture'),),payload='{"paper_id":1,"content":"constant"}') for s in ('text','structured'))
    sources=('text','graph','structured');passed,budget=pass_through(items,sources)
    return p,{p.query_id:{'query_id':p.query_id,'question':p.question,'pool':p.model_dump(mode='json'),'sources':sources,
        'pass_through':passed,'source_budget':budget,'graph_conflict_overlays':[],
        'baseline_evidence':[e.model_dump(mode='json') for e in items],'unit_scores':scores,
        'edge_scores':{k:scores[u.unit_id] for u in units for k,_,_ in u.provenance},'query_vector':[1,0]}}

def run(method,initialise):
    p,data=data_for();reranker=SlowReranker()
    system=RepairedContextSystem(method,data,encoder,reranker,{p.query_id:()})
    init=system.initialise() if initialise else None
    out=system.execute(SystemInput(query_id=p.query_id,question=p.question,seed=42))
    return system,reranker,out,init

def test_model_load_is_outside_context_timer_and_recorded_separately():
    system,reranker,out,init=run('CM-01',True)
    d=json.loads(out.diagnostics)
    assert init>=200 and d['initialisation_ms']==init and d['initialised_lazily_inside_execute'] is False
    assert reranker.loaded==1 and d['context_ms']<150           # no model load inside the per-query timer
    system.initialise();assert reranker.loaded==1               # idempotent
    system.execute(SystemInput(query_id='synthetic',question='query',seed=42));assert reranker.loaded==1

def test_forgotten_initialise_is_flagged_and_still_outside_context_timer():
    _,reranker,out,_=run('CM-01',False)
    d=json.loads(out.diagnostics)
    assert d['initialised_lazily_inside_execute'] is True and d['context_ms']<150 and reranker.loaded==1

def test_initialisation_changes_no_scientific_output_for_any_method():
    for method in ('CM-B0','CM-B1','CM-01','CM-02','CM-03'):
        a=run(method,True)[2];b=run(method,False)[2]
        assert a.context==b.context and a.retained_evidence_ids==b.retained_evidence_ids
        assert content_hash([e.model_dump(mode='json') for e in a.evidence])==content_hash([e.model_dump(mode='json') for e in b.evidence])
        da,db=json.loads(a.diagnostics),json.loads(b.diagnostics)
        for k in ('context_ms','initialisation_ms','initialised_lazily_inside_execute'):da.pop(k);db.pop(k)
        assert da==db
