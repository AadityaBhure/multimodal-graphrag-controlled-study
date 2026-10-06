"""Evidence-only perturbations; never writes canonical data or evaluates systems."""
from copy import deepcopy
import numpy as np


class StressBuilder:
    def __init__(self,source):
        self.source=source
        self.index=None

    def noise(self,record,sets):
        s=self.source; result={}
        if 'text' in sets:
            import faiss
            if self.index is None:
                faiss.omp_set_num_threads(2)
                self.index=faiss.read_index(str(s.root/'text/faiss/index.faiss'))
            query_paper=record['gold'][0]
            query=self.index.reconstruct(query_paper-1172724).reshape(1,-1)
            scores,rows=self.index.search(query,256)
            result['text']=[{'paper_id':int(row)+1172724,'cosine_similarity':float(score),
                              'similar_to_paper_id':query_paper,'violates':'explicit abstract predicate'}
                             for row,score in zip(rows[0],scores[0]) if int(row)+1172724 not in sets['text']][:3]
        if 'structured' in sets:
            first={'filters':record['conditions']['structured']['filters'][:1]}
            partial=s.structured(first)-sets['structured']
            result['structured']=[{'paper_id':p,'satisfies_filter_indices':[0], 'violates':'complete structured predicate'} for p in sorted(partial)[:3]]
        if 'graph' in sets:
            result['graph']=[]
            paths=s.graph(record['conditions']['graph'])[1]
            for paper in record['gold'][:20]:
                for inverse in (False,True):
                    for other,edge in s.adjacent(paper,1,inverse):
                        if other not in sets['graph']:
                            result['graph'].append({'paper_id':other,'path':paths[paper]+[dict(source=paper,target=other,edge_id=edge,relation_id=1,derived_inverse=inverse)],
                                                    'violates':'required graph path pattern; citation detour is irrelevant'})
                            break
                    if result['graph']:break
                if result['graph']:break
        return result if all(result.values()) else None

    def conflict(self,record):
        s=self.source; paper=record['gold'][0]
        if 'structured' in record['conditions']:
            row=s.row(paper); first=record['conditions']['structured']['filters'][0]
            field=first['field']; before=row[field]
            if isinstance(before,int):
                after=first['value']-1 if first['operator']=='>=' else first['value']+1
            elif field=='publication_date':
                before=str(before);after='9999-12-31' if first['operator']=='<=' else '0001-01-01'
            else:
                after=str(before)+' [COUNTERFACTUAL]'
            payload={'source':'structured','paper_id':paper,'field':field,'before':before,'after':after,
                     'authoritative_fact':{field:before},'mutated_conflicting_evidence':{field:after}}
        elif 'graph' in record['conditions']:
            path=s.graph(record['conditions']['graph'])[1][paper]
            edge=deepcopy(path[0]); original=edge['source']
            first,last=(0,1104554) if original<1104554 else (1104554,1113255)
            replacement=next(n for n in range(first,min(last,first+1000)) if n!=original and not any(t==edge['target'] for t,_ in s.adjacent(n,edge['relation_id'],edge['derived_inverse'])))
            changed=deepcopy(edge);changed['source']=replacement
            payload={'source':'graph','paper_id':paper,'field':'source','before':original,'after':replacement,
                     'authoritative_fact':edge,'mutated_conflicting_evidence':changed}
        else:
            before=s.abstract(paper)
            after='This counterfactual abstract denies the experimental agreement, method, and conclusions reported by the authoritative source.'
            payload={'source':'text','paper_id':paper,'field':'abstract','before':before,'after':after,
                     'authoritative_fact':{'abstract':before},'mutated_conflicting_evidence':{'abstract':after}}
        payload.update({'mutation_origin':'benchmark_evaluation_overlay_only','canonical_data_modified':False,
                        'inverse_patch':{'field':payload['field'],'replace_with':payload['before']},
                        'expected_behavior':'Prefer immutable canonical evidence, flag the contradiction, and retain the original gold set.'})
        return payload
