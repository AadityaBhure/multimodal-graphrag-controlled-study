"""Machine-generated RQ1 cohort comparisons and descriptive Pareto plots."""
from pathlib import Path
from collections import defaultdict
import csv,io,json,statistics,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.evaluation.contracts import RunRecord
from research.evaluation.aggregate import aggregate
from research.evaluation.metrics import retrieval_metrics
from research.experiments.runner import write
from research.rq1.contracts import METHODS,Pool
D=ROOT/'documentation/phase7'
def export(name,rows):
    write(D/(name+'.json'),rows);buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(rows[0]));w.writeheader();w.writerows({k:'NULL' if v is None else v for k,v in r.items()} for r in rows);(D/(name+'.csv')).write_text(buf.getvalue(),encoding='utf-8',newline='')
def frontier(rows,quality,cost):
    valid=[r for r in rows if r[quality] is not None and r[cost] is not None]
    return [r['method'] for r in valid if not any(s[quality]>=r[quality] and s[cost]<=r[cost] and (s[quality]>r[quality] or s[cost]<r[cost]) for s in valid)]
def main():
    tables=[];measurements=[];summary=[];examples=[]
    for method in METHODS:
        records=[RunRecord.model_validate_json(x) for x in (D/'runs'/method/'records.jsonl').read_text(encoding='utf-8').splitlines()]
        assert len(records)==16 and all(not r.errors and r.observation.llm_calls==0 for r in records)
        for row in aggregate(records):tables.append({'method':method,**row})
        for label in ('1','2-10','11+'):
            subset=[r for r in records if ('1' if len(r.gold_ids)==1 else '2-10' if len(r.gold_ids)<=10 else '11+')==label]
            if subset:tables.extend({'method':method,**row,'cohort':'answer_set_size/'+label} for row in aggregate(subset) if row['cohort']=='overall')
        for r in records:
            d=json.loads(r.output.diagnostics);measurements.append({'method':method,'query_id':r.query_id,'modality':r.labels.modality,'depth':r.labels.hop,'stress':'+'.join(r.stress),'gold_count':len(r.gold_ids),
                'context_characters':r.metrics['context_characters'],'context_ms':d['context_ms'],'total_ms':r.total_latency_ms,'retrieval_ms':r.observation.retrieval_ms,'common_candidate_build_ms':d['common_upstream']['common_candidate_build_ms'],
                'selected_nodes':d['selected_node_count'],'selected_edges':d['selected_edge_count'],'fallback':int(d['fallback']),'fallback_reason':d.get('reason'),'converged':d.get('converged'),'iterations':d.get('iterations'),
                'gold_coverage':r.metrics['gold_coverage'],'recall@5':r.metrics['recall@5'],'mrr':r.metrics['mrr'],'redundancy':r.metrics['redundancy'],'context_reduction':r.metrics['context_reduction'],'answer_f1':r.metrics['f1'],'evidence_coverage':r.metrics['evidence_coverage']})
        mean=lambda name: statistics.mean(r.metrics[name] for r in records if r.metrics[name] is not None) if any(r.metrics[name] is not None for r in records) else None
        rows=measurements[-16:];summary.append({'method':method,'queries':len(records),'gold_coverage':mean('gold_coverage'),'recall@5':mean('recall@5'),'mrr':mean('mrr'),'ndcg@5':mean('ndcg@5'),'context_characters':mean('context_characters'),'context_reduction':mean('context_reduction'),'context_ms':statistics.mean(x['context_ms'] for x in rows),'total_ms':statistics.mean(x['total_ms'] for x in rows),'redundancy':mean('redundancy'),'evidence_coverage':mean('evidence_coverage'),'answer_f1':None,'fallback_count':sum(x['fallback'] for x in rows),'converged_count':sum(x['converged'] is True for x in rows),'llm_calls':0})
        ordered=sorted(records,key=lambda r:(r.metrics['gold_coverage'] or 0,r.query_id))
        for kind,r in [('lowest_coverage',ordered[0]),('highest_coverage',ordered[-1])]:examples.append({'kind':kind,'method':method,'query_id':r.query_id,'gold_coverage':r.metrics['gold_coverage'],'context_characters':r.metrics['context_characters'],'diagnostics':json.loads(r.output.diagnostics),'context':r.output.context,'retained_evidence_ids':r.output.retained_evidence_ids,'quality_interpretation':'retrieval/context survival only; no generated answer'})
    export('cohort_comparison',tables);export('per_query_comparison',measurements);export('summary',summary);write(D/'representative_cases.json',examples)
    pareto=[]
    for quality,cost in [('gold_coverage','context_characters'),('gold_coverage','context_ms'),('gold_coverage','redundancy'),('answer_f1','context_characters'),('evidence_coverage','redundancy')]:
        strong=frontier(summary,quality,cost)
        for row in summary:pareto.append({'quality':quality,'cost':cost,'method':row['method'],'pareto_strong':row['method'] in strong if strong else None,'quality_value':row[quality],'cost_value':row[cost],'status':'descriptive_frontier' if strong else 'unavailable_no_measured_quality'})
    export('pareto',pareto)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,4.5))
    for ax,cost,label in zip(axes,['context_characters','context_ms','redundancy'],['Mean context characters','Mean context processing (ms)','Exact evidence-ID redundancy']):
        strong=frontier(summary,'gold_coverage',cost)
        for row in summary:
            ax.scatter(row[cost],row['gold_coverage'],marker='*' if row['method'] in strong else 'o',s=100,label=row['method'])
        ax.set_xlabel(label);ax.set_ylabel('Mean retained-paper gold coverage');ax.grid(alpha=.2)
    fig.suptitle('RQ1 validation trade-offs — 16 paired queries; no generation; stars = descriptive Pareto frontier')
    handles,names=axes[0].get_legend_handles_labels();fig.legend(handles,names,loc='lower center',ncol=5)
    axes[1].set_xscale('log');axes[1].set_xlabel('Mean context processing (ms, log scale)')
    fig.tight_layout(rect=(0,.09,1,1));fig.savefig(D/'pareto.png',dpi=160);fig.savefig(D/'pareto.svg');plt.close(fig)
    from research.evaluation.benchmark import BenchmarkReader
    queries={q.query_id:q for q in BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark').records('validation')};upstream=[]
    for path in sorted((D/'pools').glob('*.json')):
        pool=Pool.model_validate_json(path.read_text(encoding='utf-8'));q=queries[pool.query_id]
        ids=[n.node_id for n in pool.nodes if n.node_type=='paper']
        upstream.append({'query_id':q.query_id,'modality':q.modality_class,'depth':q.reasoning.complexity,'stress':'noisy' if q.stress.noisy else 'normal','candidate_papers':len(ids),**retrieval_metrics(ids,q.gold_answer_ids,(1,5,10))})
    export('upstream_reference',upstream)
    print('Reported',len(tables),'cohort rows and',len(measurements),'query records')
if __name__=='__main__':main()
