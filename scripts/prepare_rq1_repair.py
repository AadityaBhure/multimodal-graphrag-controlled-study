"""Freeze validation-only shared graph candidates and baseline pass-through.

No generation. Historical candidate pools and B4 retrieval records are replayed;
new missing pools use the same frozen Phase7 materialization boundary.
"""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.common.serialization import content_hash,canonical_json
from research.evaluation.benchmark import BenchmarkReader,digest
from research.experiments.runner import labels
from research.common.contracts import EvidenceItem
from research.rq1.contracts import Pool
from research.rq1.candidates import build_pool,BOUNDARY
from research.baselines.stores import Stores
from research.baselines.config import BaselineOptions
from research.repair.rq1_compliance_v1.cm01 import canonical_units,cosine_scores
from research.repair.rq1_compliance_v1.context import pass_through

D=ROOT/'documentation/rq1_repair'

def save(path,value):
    text=canonical_json(value)+'\n'
    if path.exists():
        if path.read_text(encoding='utf-8')!=text:raise ValueError('Incompatible prepared artifact '+str(path))
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf-8',newline='\n') as f:f.write(text)

def main():
    r=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark')
    qs=sorted((q for q in r.records('validation') if q.provenance['source']=='generated' and 'G' in q.modality_class and labels(q).status=='programmatically_verified'),key=lambda q:q.query_id)
    assert len(qs)==32
    store=Stores(r.root.parent,ROOT/'artifacts/rq1_repair/work',BaselineOptions(),modalities=('graph',))
    rows=[]
    try:
        for q in qs:
            key=content_hash(q.query_id);path=D/'inputs'/(key+'.json')
            if path.exists():
                data=json.loads(path.read_text(encoding='utf-8'));assert data['query_id']==q.query_id and data['question']==q.question
                rows.append({'query_id':q.query_id,'path':path.relative_to(D).as_posix(),'sha256':digest(path)});continue
            start=time.perf_counter();old=ROOT/'documentation/phase7/pools'/(key+'.json')
            if old.exists():pool=Pool.model_validate_json(old.read_text(encoding='utf-8'))
            else:
                source=ROOT/'documentation/phase6_closeout/runs/B2/records'/(key+'.json')
                rec=json.loads(source.read_text(encoding='utf-8'));assert not rec['errors']
                seeds=[n['node_id'] for n in json.loads(rec['output']['diagnostics'])['graph']['seeds']]
                overlay=r.overlay(q)
                # Conflict overlays are deliberately not official relation units.
                pool=build_pool(store,q.query_id,q.question,seeds,overlay if q.stress.noisy else None,digest(source))
                pool=pool.model_copy(update={'overlay_hash':content_hash(overlay) if overlay else None})
            record_path=ROOT/'documentation/phase6_closeout/runs/B4/records'/(key+'.json')
            record=json.loads(record_path.read_text(encoding='utf-8'));assert not record['errors']
            items=tuple(EvidenceItem.model_validate(e) for e in record['output']['evidence'])
            sources=tuple(s for letter,s in [('T','text'),('G','graph'),('S','structured')] if letter in q.modality_class)
            passed,budget=pass_through(items,sources)
            units=canonical_units(pool);scores=cosine_scores(q.question,units,store.encode)
            qvector=store.encode([q.question])[0].tolist()
            # Map each observed physical edge back to the same canonical graph-only
            # relation description for CM02 edge-text similarity.
            edge_scores={key:scores[u.unit_id] for u in units for key,_,_ in u.provenance}
            # Explicit graph conflict evidence is held fixed, tagged, outside the
            # authoritative canonical-unit graph. It never becomes an official fact.
            conflicts=[e.model_dump(mode='json') for e in items if e.source_type=='graph' and ':overlay' in e.evidence_id and q.stress.conflict]
            data={'query_id':q.query_id,'question':q.question,'pool':pool.model_dump(mode='json'),
                'sources':sources,'pass_through':passed,'source_budget':budget,
                'baseline_evidence':[e.model_dump(mode='json') for e in items if e.source_type in sources],
                'graph_conflict_overlays':conflicts,'unit_scores':scores,'edge_scores':edge_scores,'query_vector':qvector,
                'benchmark_sha256':r.manifest_hash,'baseline_record_sha256':digest(record_path),
                'preparation_ms':(time.perf_counter()-start)*1000}
            save(path,data);rows.append({'query_id':q.query_id,'path':path.relative_to(D).as_posix(),'sha256':digest(path)})
            print(q.query_id,len(pool.nodes),len(units),flush=True)
    finally:store.close()
    save(D/'input_manifest.json',{'files':rows,'boundary':BOUNDARY,'count':len(rows),'test_human_test_used':False,'generation_calls':0})

if __name__=='__main__':main()
