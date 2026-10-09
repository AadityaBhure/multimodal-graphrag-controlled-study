"""Prepare fixed generated graph-relevant validation pools without test access."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.evaluation.benchmark import BenchmarkReader,digest
from research.experiments.runner import write,labels
from research.baselines.config import BaselineOptions
from research.baselines.stores import Stores
from research.rq1.candidates import build_pool,BOUNDARY
from research.rq1.contracts import Pool
from research.common.serialization import content_hash
from scripts.audit_stark_mag import process_memory
if __name__=='__main__':
    docs=ROOT/'documentation/phase7';dest=docs/'pools';dest.mkdir(parents=True,exist_ok=True)
    reader=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark')
    qs=[q for q in reader.records('validation') if q.provenance['source']=='generated' and 'G' in q.modality_class and not q.stress.conflict and not q.stress.unanswerable]
    assert len(qs)==16 and all(labels(q).status=='programmatically_verified' for q in qs)
    write(docs/'selection.json',{'query_ids':[q.query_id for q in qs],'count':len(qs),'rule':'all generated validation G/TG/GS/TGS normal and noisy; no outcome selection','missing_real_strata':['multi-hop-3+'],'boundary':BOUNDARY,'tuning':False})
    store=Stores(reader.root.parent,ROOT/'artifacts/phase7/work',BaselineOptions(),modalities=('graph',))
    previous={r['query_id']:r for r in json.loads((docs/'pool_manifest.json').read_text(encoding='utf-8'))['files']} if (docs/'pool_manifest.json').exists() else {}
    manifest=[]
    try:
        for q in qs:
            target=dest/(content_hash(q.query_id)+'.json')
            if target.exists():
                row=previous.get(q.query_id)
                if row is None or digest(target)!=row['sha256']:raise ValueError('Unowned or modified candidate snapshot')
                pool=Pool.model_validate_json(target.read_text(encoding='utf-8'))
                assert pool.question==q.question and pool.boundary==content_hash(BOUNDARY)
                overlay=reader.overlay(q)
                assert pool.overlay_hash==(content_hash(overlay) if overlay else None)
            else:
                source=ROOT/'documentation/phase6_closeout/runs/B2/records'/(content_hash(q.query_id)+'.json')
                record=json.loads(source.read_text(encoding='utf-8'));assert record['query_id']==q.query_id and not record['errors']
                seeds=[n['node_id'] for n in json.loads(record['output']['diagnostics'])['graph']['seeds']]
                pool=build_pool(store,q.query_id,q.question,seeds,reader.overlay(q),digest(source));write(target,pool.model_dump(mode='json'))
            manifest.append({'query_id':q.query_id,'path':target.relative_to(docs).as_posix(),'sha256':digest(target),'pool_hash':pool.fingerprint(),'nodes':len(pool.nodes),'edges':len(pool.edges)})
            completed={r['query_id'] for r in manifest}
            checkpoint_rows=manifest+[r for key,r in previous.items() if key not in completed]
            write(docs/'pool_manifest.json',{'files':checkpoint_rows,'resources':process_memory(),'boundary':BOUNDARY})
            print(q.query_id,len(pool.nodes),len(pool.edges),flush=True)
        assert store.index is None and store.modalities=={'graph'}
    finally:store.close()
    write(docs/'pool_manifest.json',{'files':manifest,'resources':process_memory(),'boundary':BOUNDARY})
