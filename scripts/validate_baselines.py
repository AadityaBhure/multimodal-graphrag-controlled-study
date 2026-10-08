"""Bounded offline validation, embedding parity and source-identity checks for B1--B4."""
from pathlib import Path
import json
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.evaluation.benchmark import BenchmarkReader,read_json
from research.experiments.config import RunnerConfig
from research.experiments.runner import run,materialize,write
from research.baselines.config import BaselineOptions
from research.baselines.stores import Stores,literal
from research.baselines.system import BaselineSystem,SOURCES
from research.baselines.generation import OfflineGenerator
from scripts.audit_stark_mag import process_memory

if __name__=='__main__':
    dataset=ROOT/'data/MMG_STARK_MAG';reader=BenchmarkReader(dataset/'benchmark')
    qs=list(reader.records('validation'))
    selected=[next(q for q in qs if q.modality_class==c and not any(getattr(q.stress,n) for n in ('noisy','conflict','unanswerable'))) for c in ('T','G','S','TGS')]
    selected.append(next(q for q in qs if q.provenance['source']=='official_synthetic'))
    options=BaselineOptions(cache=False);results=[];started=time.perf_counter()
    for baseline in SOURCES:
        begin=time.perf_counter()
        config=RunnerConfig(config_id=f'{baseline}-offline-validation-v1',system_id=baseline,system_version='1',
            embedding_model=options.embedding,query_ids=tuple(q.query_id for q in selected),retrieval_parameters=options.model_dump())
        write(ROOT/f'configs/baselines/{baseline}-validation-offline.json',config.model_dump(mode='json'))
        store=Stores(dataset,ROOT/'artifacts/phase6/work'/baseline,options,modalities=SOURCES[baseline])
        system=BaselineSystem(config,store,OfflineGenerator())
        output=ROOT/f'documentation/phase6/validated/{baseline}'
        run(config,reader.root,output,system)
        records=materialize(output)
        assert not any(r.errors for r in records),[(r.query_id,r.errors) for r in records if r.errors]
        # Validation-only audit: authoritative registry is never injected into retrieval context.
        all_ids=sorted({int(e.canonical_id.split(':')[1]) for r in records for e in r.output.evidence})
        if all_ids:
            rows=store.con.execute('SELECT stark_node_id,canonical_id,entity_type FROM read_parquet('+literal(dataset/'canonical/canonical_entities.parquet')+') WHERE stark_node_id IN ('+','.join('?' for _ in all_ids)+')',all_ids).fetchall()
            assert len(rows)==len(all_ids) and all(t=='paper' and c==f'stark:{i}' for i,c,t in rows)
        parity=None
        if baseline=='B1':
            paper=int(store.mapping[0]);content=store.texts([paper])[paper]['content']
            encoded=store.encode([content])[0];stored=store.index.reconstruct(0)
            parity={'paper_id':paper,'max_abs_error':float(np.max(np.abs(encoded-stored))),'cosine':float(encoded@stored)}
            assert np.allclose(encoded,stored,atol=2e-5,rtol=1e-4),parity
        if baseline=='B2':
            assert store.index is None and all(isinstance(a,np.memmap) for a in store.csr.values())
            assert all(e.source_type=='graph' and 'abstract' not in json.loads(e.payload) for r in records for e in r.output.evidence)
        if baseline=='B3':
            try:store.con.execute('DELETE FROM structured.papers_structured WHERE paper_id=-1')
            except Exception:readonly=True
            else:raise AssertionError('Structured database was writable')
        before=(output/'records.jsonl').read_bytes();run(config,reader.root,output,system)
        assert before==(output/'records.jsonl').read_bytes()
        results.append({'baseline':baseline,'query_count':len(records),'elapsed_seconds':time.perf_counter()-begin,
            'resources':process_memory(),'registry_ids_verified':len(all_ids),'query_embedding_parity':parity,
            'llm_calls':sum(r.observation.llm_calls for r in records),'resume_byte_identical':True,
            'retrieval_latency_ms':[r.observation.retrieval_ms for r in records],
            'sources':list(SOURCES[baseline]),'representation_manifest_sha256':store.manifest_hash})
        store.close()
        print(baseline,'offline PASS',flush=True)
    write(ROOT/'documentation/phase6/offline_resources.json',{'elapsed_seconds':time.perf_counter()-started,'baselines':results,
        'selected_query_ids':[q.query_id for q in selected],'scope':'validation_only_no_generation'})
