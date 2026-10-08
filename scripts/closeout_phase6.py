"""Phase 6 closeout: all verified generated validation queries, frozen controls, no API."""
from pathlib import Path
from collections import Counter
import csv,io,json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.evaluation.benchmark import BenchmarkReader,digest
from research.evaluation.aggregate import aggregate
from research.evaluation.contracts import RunRecord
from research.experiments.config import load_runner_config,RunnerConfig
from research.experiments.runner import run,write,labels
from research.baselines.config import BaselineOptions
from research.baselines.stores import Stores
from research.baselines.system import BaselineSystem,SOURCES
from research.baselines.generation import OfflineGenerator
from scripts.audit_stark_mag import process_memory
DOCS=ROOT/'documentation/phase6_closeout'

def export(name,rows):
    write(DOCS/(name+'.json'),rows)
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader()
    writer.writerows({k:'NULL' if v is None else v for k,v in row.items()} for row in rows)
    (DOCS/(name+'.csv')).write_text(stream.getvalue(),encoding='utf-8')

def main():
    DOCS.mkdir(exist_ok=True)
    reader=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark')
    queries=sorted((q for q in reader.records('validation') if q.provenance['source']=='generated'),key=lambda q:q.query_id)
    assert len(queries)==56 and all(labels(q).status=='programmatically_verified' for q in queries)
    protected=list((ROOT/'research/baselines').glob('*.py'))+list((ROOT/'configs/baselines').glob('*'))
    before={p.relative_to(ROOT).as_posix():digest(p) for p in protected if p.is_file()}
    write(DOCS/'selection.json',{'split':'validation','source':'generated','annotation_status':'programmatically_verified',
        'query_ids':[q.query_id for q in queries],'modality_counts':dict(Counter(q.modality_class for q in queries)),
        'complexity_counts':dict(Counter(q.reasoning.complexity for q in queries)),
        'stress_counts':dict(Counter(n for q in queries for n in (tuple(s for s in ('noisy','conflict','unanswerable') if getattr(q.stress,s)) or ('normal',)))),
        'selection_rule':'All generated validation records, fixed before execution; no outcome-based filtering.'})
    resources=[];tables=[];counts=[];cross=[]
    for method in SOURCES:
        original=load_runner_config(ROOT/f'configs/baselines/{method}-validation-offline.json')
        config=RunnerConfig.model_validate({**original.model_dump(mode='json'),'config_id':method+'-closeout-generated-validation-v1','query_ids':[q.query_id for q in queries]})
        assert config.retrieval_parameters==original.retrieval_parameters and not config.model_ids
        write(DOCS/(method+'-config.json'),config.model_dump(mode='json'))
        start=time.perf_counter();options=BaselineOptions.model_validate(config.retrieval_parameters)
        store=Stores(reader.root.parent,ROOT/'artifacts/phase6/work'/method,options,modalities=SOURCES[method])
        generator=OfflineGenerator()
        try:
            system=BaselineSystem(config,store,generator,ROOT/'artifacts/phase6/cache')
            run(config,reader.root,DOCS/'runs'/method,system)
            memory=process_memory()
        finally:generator.close();store.close()
        elapsed=time.perf_counter()-start
        records=[RunRecord.model_validate_json(line) for line in (DOCS/'runs'/method/'records.jsonl').read_text(encoding='utf-8').splitlines()]
        assert len(records)==56 and {r.query_id for r in records}=={q.query_id for q in queries}
        assert all(r.split=='validation' and r.source_type=='generated' and r.labels.status=='programmatically_verified' and r.observation.llm_calls==0 and r.answer_ids is None and not r.errors for r in records)
        rows=[{'baseline':method,**row} for row in aggregate(records) if row['cohort']=='overall' or row['cohort'].startswith(('modality/','hop/','stress/'))]
        tables.extend(rows)
        for name,n in sorted(Counter((r.labels.modality,r.labels.hop,'+'.join(r.stress)) for r in records).items()):
            selected=[r for r in records if (r.labels.modality,r.labels.hop,'+'.join(r.stress))==name]
            cross.extend({'baseline':method,'modality':name[0],'complexity':name[1],'stress':name[2],**row} for row in aggregate(selected) if row['cohort']=='overall')
        counts.extend({'baseline':method,'cohort':row['cohort'],'n_queries':row['n_queries'],'n_errors':row['n_errors']} for row in rows if row['metric']=='mrr')
        resources.append({'baseline':method,'wall_seconds':elapsed,'memory':memory,'queries':len(records),'llm_calls':sum(r.observation.llm_calls for r in records),'retrieval_ms_sum':sum(r.observation.retrieval_ms for r in records)})
        write(DOCS/'resources.json',resources)
        print(method,'PASS',len(records),'queries',round(elapsed,2),'seconds',flush=True)
    assert before=={p:digest(ROOT/p) for p in before}
    write(DOCS/'baseline_preservation.json',{'status':'pass','before_sha256':before,'after_sha256':{p:digest(ROOT/p) for p in before},'retrieval_parameters_unchanged':True,'tuning_performed':False})
    export('comparison',tables);export('cohort_counts',counts);export('intersection_comparison',cross)
    metrics=['recall@5','precision@5','mrr','ndcg@5','gold_coverage']
    text=['# Phase 6 closeout addendum','',
        'PASS. All 56 programmatically verified generated validation records were evaluated by each unchanged B1–B4 baseline (224 query executions). No test/human-test or official unverified records were evaluated. No generation or API calls occurred. Phase 7 has not begun.','',
        'Selection was fixed before execution: 8 queries each in T, G, S, TG, TS, GS, TGS; 24 single-hop and 32 multi-hop-2; 14 each normal, noisy, conflict and unanswerable. These are operational/programmatic annotations, not a claim of completed human review. No higher-hop validation strata exist in this selection.','',
        '## Machine-generated retrieval comparison','',
        '| Baseline | Cohort | Queries | Available / NULL | Recall@5 | Precision@5 | MRR | nDCG@5 | Gold coverage |',
        '| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |']
    for count in counts:
        selected={r['metric']:r for r in tables if r['baseline']==count['baseline'] and r['cohort']==count['cohort']}
        row=selected['mrr'];values=['NULL' if selected[m]['mean'] is None else f"{selected[m]['mean']:.6f}" for m in metrics]
        text.append('| '+' | '.join([count['baseline'],count['cohort'],str(count['n_queries']),f"{row['n_available']} / {row['n_null']}",*values])+' |')
    text+=['','## Metrics and interpretation','',
        'Tables are computed from validated Phase 5 RunRecord files using the existing aggregate() and metric functions. Means exclude NULL and publish n_available/n_null. Full JSON/CSV tables include all existing metrics, K=1/5/10, and modality × complexity × stress intersections. CSV unavailable values are explicitly NULL; JSON uses null. Marginal cohorts overlap and must not be summed.','',
        'Retrieval precision divides by K, even for fewer results. Rankings are deduplicated; recall uses the gold-set denominator, MRR the first relevant rank, and nDCG binary relevance. Empty-gold/unanswerable retrieval metrics are NULL, not zero. All answer metrics, generation latency, token usage, estimated cost and unsupported agent/fusion metrics are NULL. Evidence coverage is NULL because gold evidence IDs are unavailable. See full tables for each metric’s availability.','',
        'B4 ranking remains source-order concatenation: Recall@5 is generally Text-first, while gold coverage measures its full returned set. Stress inputs use existing benchmark overlays and unchanged baseline overlay behavior, without mutating canonical data. Results describe this small controlled validation set, not general benchmark accuracy.','',
        '## Resources and preservation','',
        '| Baseline | Wall seconds | Retrieval seconds (sum) | Process peak bytes | LLM calls |','| --- | ---: | ---: | ---: | ---: |']
    for r in resources:text.append(f"| {r['baseline']} | {r['wall_seconds']:.3f} | {r['retrieval_ms_sum']/1000:.3f} | {r['memory']['peak_working_set_bytes']} | 0 |")
    text+=['','Peak memory is a cumulative process high-water mark; wall time includes setup, runner validation and file materialization. Resume reuses completed records; original per-query measured latencies remain authoritative.','',
        'No tuning occurred. Only the new experiment ID and query selection differ from the original offline-validation configs. Seed 42, K values, retrieval parameters, graph budgets, context budgets, embeddings and baseline algorithms are unchanged. baseline_preservation.json records before/after SHA-256 values for every original baseline implementation/config. Full frozen-data preservation is recorded separately in preservation.json.','',
        'Reproduce/resume: `.\\.venv\\Scripts\\python.exe scripts/closeout_phase6.py`. Raw records, manifests, events, status and aggregate tables are under runs/B1–B4. These retain the existing deterministic runner identity and incompatible-run refusal. Do not change research code before resuming an interrupted run.','',
        'Closeout complete; checkpoint and stop for review. No Phase 7 work is included.']
    (DOCS/'Addendum.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=DOCS)
    DOCS=parser.parse_args().output.resolve()
    main()
