"""Recompute paired summaries from immutable Phase5 repair records."""
from pathlib import Path
import itertools,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.evaluation.contracts import RunRecord
from research.common.serialization import content_hash
from research.repair.dispatch import write
from scripts.run_rq1_repair import D,METHODS

def cluster(qid):return qid.rsplit(':',1)[0]

def summary(values):
    valid={q:float(v) for q,v in values.items() if v is not None}
    groups=sorted({cluster(q) for q in valid})
    if not valid:return {'n':0,'n_null':len(values),'mean':None,'median':None,'ci95':None,'independent_query_families':0}
    x=np.array(list(valid.values()));ci=None
    if len(groups)>1:
        grouped={g:[v for q,v in valid.items() if cluster(q)==g] for g in groups}
        rng=np.random.default_rng(42)
        picks=rng.integers(0,len(groups),size=(10000,len(groups)))
        sums=np.array([sum(grouped[g]) for g in groups]);counts=np.array([len(grouped[g]) for g in groups])
        samples=sums[picks].sum(axis=1)/counts[picks].sum(axis=1)
        ci=np.quantile(samples,[.025,.975]).tolist()
    return {'n':len(valid),'n_null':len(values)-len(valid),'mean':float(x.mean()),'median':float(np.median(x)),
        'ci95':ci,'independent_query_families':len(groups),'distribution':sorted(valid.values())}

def paired(a,b):
    delta={q:a[q]-b[q] if a[q] is not None and b[q] is not None else None for q in sorted(a.keys()&b.keys())}
    result=summary(delta);result['per_query_delta']=delta
    valid={q:v for q,v in delta.items() if v is not None};groups=sorted({cluster(q) for q in valid})
    if len(groups)>1:
        sums=np.array([sum(v for q,v in valid.items() if cluster(q)==g) for g in groups])
        observed=abs(sum(valid.values()))
        extreme=sum(abs(float(np.dot(sums,signs)))>=observed-1e-12 for signs in itertools.product((-1,1),repeat=len(groups)))
        result['p_cluster_sign_permutation']=extreme/(2**len(groups))
    else:result['p_cluster_sign_permutation']=None
    return result

def main():
    records={};hashes={}
    for method in METHODS:
        files=sorted((D/'runs'/method/'records').glob('*.json'))
        rows=[RunRecord.model_validate_json(p.read_text(encoding='utf-8')) for p in files]
        assert len(rows)==32,method
        assert all(r.split=='validation' and r.source_type=='generated' and r.labels.status=='programmatically_verified' for r in rows)
        records[method]={r.query_id:r for r in rows};hashes[method]=content_hash([r.model_dump(mode='json') for r in rows])
    query_ids=set(records[METHODS[0]])
    assert all(set(rows)==query_ids for rows in records.values())
    cohorts={'all':query_ids}
    for q,r in records[METHODS[0]].items():
        for name in ['modality:'+r.labels.modality,'reasoning:'+r.labels.hop]+['stress:'+s for s in r.stress]:cohorts.setdefault(name,set()).add(q)
    values={}
    for method,rows in records.items():
        values[method]={}
        for q,r in rows.items():
            m=dict(r.metrics);d=json.loads(r.output.diagnostics) if r.output and r.output.diagnostics else {}
            m.update(context_management_ms=d.get('context_ms'),selected_graph_nodes=d.get('selected_node_count'),selected_graph_edges=d.get('selected_edge_count'),
                fallback=float(d.get('fallback') is not None) if r.output else None,
                convergence=float(d['convergence']) if d.get('convergence') is not None else None)
            m['intrinsic_total_ms']=d['context_ms']+r.observation.generation_ms if d.get('context_ms') is not None and r.observation.generation_ms is not None else None
            values[method][q]=m
    tables=[]
    for method in METHODS:
        for cohort,ids in sorted(cohorts.items()):
            for metric in sorted({k for q in ids for k in values[method][q]}):
                tables.append({'method':method,'cohort':cohort,'metric':metric,**summary({q:values[method][q].get(metric) for q in sorted(ids)})})
    comparisons=[]
    for a,b in itertools.combinations(METHODS,2):
        comparisons.append({'a':a,'b':b,'metric':'f1',**paired({q:values[a][q]['f1'] for q in query_ids},{q:values[b][q]['f1'] for q in query_ids})})
    valid=sorted((r for r in comparisons if r['p_cluster_sign_permutation'] is not None),key=lambda r:r['p_cluster_sign_permutation'])
    running=0.
    for i,row in enumerate(valid):
        running=max(running,min(1.,(len(valid)-i)*row['p_cluster_sign_permutation']));row['p_holm']=running
    init={m:json.loads((D/'initialisation'/(m+'.json')).read_text(encoding='utf-8'))['initialisation_ms'] for m in METHODS if (D/'initialisation'/(m+'.json')).exists()}
    write(D/'analysis.json',{'initialisation_ms_per_method':init,'record_fingerprints':hashes,'tables':tables,'paired_f1':comparisons,
        'statistical_unit':'base query family; stress variants remain paired within family',
        'bootstrap_seed':42,'bootstrap_replicates':10000,'limitations':'Only 8 base query families; exploratory validation, not benchmark-wide inference. NULL values excluded and counted. No automatic winner.'})
    print('Recomputed',len(tables),'summaries and',len(comparisons),'paired comparisons')

if __name__=='__main__':main()
