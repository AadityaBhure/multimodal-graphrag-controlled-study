"""Benchmark integrity/leakage audits; contains no retrieval-quality metrics."""
import ast
from collections import Counter,defaultdict
from difflib import SequenceMatcher
import json
import re
import unicodedata
import numpy as np
import pyarrow.parquet as pq

from research.benchmark.build import SPLITS,load_jsonl,read_official,write
from research.benchmark.contracts import BenchmarkQuery
from research.benchmark.construction import intersection,necessity,wording,template_signature
from research.common.serialization import content_hash
from scripts.audit_stark_mag import digest


def norm(text):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',text).casefold()))


def leakage_scan(queries):
    exact=defaultdict(list);families=defaultdict(set);instances=defaultdict(set)
    for q in queries:
        exact[norm(q['question'])].append(q)
        if q['provenance']['source']=='generated':
            families[q['provenance']['template_family']].add(q['split'])
            instances[q['provenance']['construction_instance']].add(q['split'])
    assert all(len(s)==1 for s in families.values()),'Generated template across splits'
    assert all(len(s)==1 for s in instances.values()),'Construction instance across splits'
    exact_findings=[];paired=0
    for values in exact.values():
        if len(values)<2:continue
        base={q['provenance'].get('base_query_id',q['query_id']) for q in values}
        if len(base)==1 and len({q['split'] for q in values})==1:
            paired+=len(values)-1
        else:
            exact_findings.append({'query_ids':[q['query_id'] for q in values], 'splits':sorted({q['split'] for q in values})})
    # Source queries cannot be rewritten/deleted to make this audit artificially clean.
    originals=[q for q in queries if q['provenance']['source']!='generated']
    postings=defaultdict(list);tokens=[]
    for i,q in enumerate(originals):
        words=norm(q['question']).split();tokens.append(set(words))
        for shingle in set(tuple(words[j:j+3]) for j in range(len(words)-2)):
            postings[shingle].append(i)
    candidates=set()
    for values in postings.values():
        if 2<=len(values)<=20:
            for a in range(len(values)):
                for b in range(a+1,len(values)):
                    i,j=values[a],values[b]
                    if originals[i]['split']!=originals[j]['split']:
                        candidates.add((i,j))
    near=[]
    for i,j in sorted(candidates):
        a,b=tokens[i],tokens[j]
        jac=len(a&b)/max(1,len(a|b))
        if jac>=.8:
            ratio=SequenceMatcher(None,norm(originals[i]['question']),norm(originals[j]['question']),autojunk=False).ratio()
            if ratio>=.88:
                near.append({'query_ids':[originals[i]['query_id'],originals[j]['query_id']],
                             'token_jaccard':jac,'sequence_ratio':ratio,'classification':'potential_official_paraphrase_requires_review'})
    return {'generated_template_split_disjoint':True,'construction_instances_split_disjoint':True,
            'intentional_within_split_paired_stress_duplicate_count':paired,'unexpected_exact_duplicate_groups':exact_findings,
            'official_cross_split_near_duplicates':near,'near_duplicate_candidate_pairs_checked':len(candidates),
            'semantic_paraphrase_exhaustiveness':'not claimed; human review required',
            'shared_corpus_policy':'Transductive shared paper corpus; answer overlap alone is not split leakage. Generated anchor IDs and complete construction families are split-exclusive.'}


def check_path(source,path):
    for i,edge in enumerate(path):
        if i:assert path[i-1]['target']==edge['source']
        assert (edge['target'],edge['edge_id']) in set(source.adjacent(edge['source'],edge['relation_id'],edge['derived_inverse']))


def audit(source,output):
    queries=[q for split in SPLITS for q in load_jsonl(output/(split+'.jsonl'))]
    ids=[q['query_id'] for q in queries];assert len(ids)==len(set(ids))
    for q in queries:
        BenchmarkQuery.model_validate(q)
        assert all(1172724<=i<=1872967 for i in q['gold_answer_ids'])
    originals,splits=read_official(source)
    assert load_jsonl(output/'official_human_original.jsonl')==originals['human']
    assert load_jsonl(output/'official_synthetic_original.jsonl')==originals['synthetic']
    raw=source.root/'raw/stark_mag/qa/mag'
    for path in raw.rglob('*'):
        if path.is_file():assert digest(path)==digest(output/'source_preservation'/path.relative_to(raw))
    by_source={(kind,r['id']):r for kind,rs in originals.items() for r in rs}
    human_expected=[]
    for row in originals['human']:
        answer=ast.literal_eval(row['answer_ids'])
        if all(1172724<=i<=1872967 for i in answer):human_expected.append(row['id'])
    assert sorted(q['source_query_id'] for q in queries if q['split']=='human_test')==sorted(human_expected)
    official=0;generated=0;empty=0;noise=0;conflicts=0;anchor_splits=defaultdict(set)
    source_set_checks=0;path_checks=0;complete_candidates=set()
    checked_text=set()
    operator_splits=defaultdict(set)
    for q in queries:
        if q['provenance']['source']!='generated':
            kind='human' if q['split']=='human_test' else 'synthetic'
            original=by_source[(kind,q['source_query_id'])]
            assert q['question']==original['query'] and q['gold_answer_ids']==ast.literal_eval(original['answer_ids'])
            assert q['provenance']['original_row_sha256']==content_hash(original)
            assert q['split']==('human_test' if kind=='human' else splits[original['id']])
            official+=1;continue
        generated+=1
        record=json.loads((output/q['gold_evidence']['construction_record']).read_text(encoding='utf-8'))
        base_conditions=record['mutation']['original_conditions'] if record['mutation'] else record['conditions']
        signature=template_signature(base_conditions)
        assert record['template_family']==signature
        operator_splits[signature].add(q['split'])
        assert q['question']==wording(source,record['conditions'],q['split'])
        sets=source.candidates(record['conditions'])
        if 'text' in record['conditions']:
            condition=record['conditions']['text'];key=content_hash(condition)
            if key not in checked_text:
                clauses=['contains(lower(label), ?)']*len(condition['phrases'])
                separator=' OR ' if condition['operator']=='any' else ' AND '
                assert source.con.execute('SELECT count(*) FROM nodes WHERE ('+separator.join(clauses)+')',condition['phrases']).fetchone()[0]==0
                checked_text.add(key)
        for modality,ref in record['candidate_sets'].items():
            path=output/ref['path'];assert digest(path)==ref['sha256']
            values=json.loads(path.read_text(encoding='utf-8'));assert values==sorted(sets[modality])
            assert len(values)==ref['count'] and all(1172724<=i<=1872967 for i in values)
            complete_candidates.update(values);source_set_checks+=1
        gold=sorted(intersection(sets));assert gold==q['gold_answer_ids']==record['gold_answer_ids']
        if q['answerable']:
            assert necessity(sets),'Source combination is redundant'
        else:
            assert record['mutation'] and not gold;empty+=1
            original=record['mutation']['original_conditions']
            assert sorted(intersection(source.candidates(original)))==record['mutation']['original_gold_answer_ids']
            assert record['mutation']['original_question']==wording(source,original,q['split'])
        for paper,path in record['graph_witness_paths'].items():
            assert path[-1]['target']==int(paper);check_path(source,path);path_checks+=1
        if 'graph' in record['conditions']:
            anchor=record['conditions']['graph']['anchor_id'];anchor_splits[anchor].add(q['split'])
            label=source.label(anchor)
            assert source.con.execute('SELECT count(*) FROM nodes WHERE lower(label)=?',[label.lower()]).fetchone()[0]==1
            assert source.con.execute('SELECT count(*) FROM texts WHERE paper_id IN (SELECT unnest(?)) AND contains(lower(content),?)',[gold,label.lower()]).fetchone()[0]==0
        # Question carries conditions/anchors, never generated answer identifiers or full answer titles.
        assert not any(str(p) in q['question'] for p in gold),'Answer ID in wording'
        for paper in gold:
            title=source.label(paper)
            if title and len(norm(title).split())>=5:
                assert norm(title) not in norm(q['question']),'Answer title leaked in wording'
        if q['stress']['noisy']:
            overlay=json.loads((output/q['provenance']['stress_record']).read_text(encoding='utf-8'))
            assert overlay['canonical_data_modified'] is False
            for modality,distractors in overlay['distractors'].items():
                assert distractors
                for d in distractors:
                    assert d['paper_id'] not in sets[modality] and d['paper_id'] not in gold
                    if modality=='graph':check_path(source,d['path'])
                    if modality=='structured':
                        first={'filters':record['conditions']['structured']['filters'][:1]}
                        assert d['paper_id'] in source.structured(first)
                    if modality=='text':assert np.isfinite(d['cosine_similarity']) and d['cosine_similarity']>0
            noise+=1
        if q['stress']['conflict']:
            overlay=json.loads((output/q['provenance']['stress_record']).read_text(encoding='utf-8'))
            assert overlay['canonical_data_modified'] is False and overlay['before']!=overlay['after']
            assert overlay['inverse_patch']['replace_with']==overlay['before']
            assert overlay['mutated_conflicting_evidence'][overlay['field']]==overlay['after']
            assert overlay['authoritative_fact'][overlay['field']]==overlay['before']
            if overlay['source']=='structured':assert str(source.row(overlay['paper_id'])[overlay['field']])==str(overlay['before'])
            elif overlay['source']=='text':assert source.abstract(overlay['paper_id'])==overlay['before']
            else:check_path(source,[overlay['authoritative_fact']])
            conflicts+=1
    assert all(len(v)==1 for v in anchor_splits.values()),'Anchor entity crosses generated splits'
    assert all(len(v)==1 for v in operator_splits.values()),'Split-blind construction operator template leakage'
    # Identity check against canonical registry, not only numeric bounds.
    count=source.con.execute("SELECT count(*) FROM registry WHERE entity_type='paper' AND stark_node_id IN (SELECT unnest(?))",[sorted(complete_candidates)]).fetchone()[0]
    assert count==len(complete_candidates)
    assert pq.read_schema(source.root/'text/text_documents.parquet').names==['paper_id','title','abstract','content']
    leakage=leakage_scan(queries)
    flagged={qid for g in leakage['unexpected_exact_duplicate_groups'] for qid in g['query_ids']}
    flagged.update(qid for g in leakage['official_cross_split_near_duplicates'] for qid in g['query_ids'])
    # Eligibility is separate from immutable source questions/gold and requires explicit adjudication.
    write(output/'eligibility.json',{'paper_quality_release':'blocked_pending_manual_verification',
          'quarantined_query_ids':sorted(flagged),'quarantine_reason':'potential_duplicate_or_cross_split_paraphrase; adjudicate before primary use',
          'no_official_query_rewritten_or_removed':True})
    write(output/'leakage_audit.json',leakage)
    result={'status':'pass_with_review_findings' if flagged else 'pass','schema_valid_queries':len(queries),
            'official_logically_unchanged':official,'generated_gold_recomputed':generated,'source_candidate_sets_recomputed':source_set_checks,
            'canonical_candidate_ids_verified':count,'graph_witness_paths_verified':path_checks,'verified_unanswerable':empty,
            'verified_noisy_overlays':noise,'verified_reversible_conflicts':conflicts,'human_original_count':len(originals['human']),
            'human_retained_count':len(human_expected),'human_excluded_count':len(originals['human'])-len(human_expected),
            'official_gold_semantics':'authoritative supplied labels preserved; not independently inferred or repaired',
            'generated_gold_semantics':'exact operational predicates; all intersections recomputed',
            'modality_isolation':'source schemas, graph-label claim absence, anchor-text exclusion and strict ablations at construction; candidate-set necessity recomputed',
            'quarantined_query_count':len(flagged),'full_semantic_review_pending':True}
    write(output/'audit_results.json',result)
    return queries,result


def statistics(source,queries,output=None):
    result={}
    for key,operation in [('split',lambda q:q['split']),('modality',lambda q:q['modality_class']),
           ('reasoning',lambda q:q['reasoning']['complexity']),('source',lambda q:q['provenance']['source']),
           ('stress',lambda q:next((k for k,v in q['stress'].items() if k!='schema_version' and v),'normal')),
           ('answer_set_size',lambda q:'0' if not q['gold_answer_ids'] else '1' if len(q['gold_answer_ids'])==1 else '2-5' if len(q['gold_answer_ids'])<=5 else '6-20' if len(q['gold_answer_ids'])<=20 else '21-100' if len(q['gold_answer_ids'])<=100 else '101+')]:
        result[key]=dict(sorted(Counter(operation(q) for q in queries).items()))
    result['by_split']={split:{'source':dict(Counter(q['provenance']['source'] for q in queries if q['split']==split)),
                                    'modality':dict(Counter(q['modality_class'] for q in queries if q['split']==split))} for split in SPLITS}
    ids=sorted({p for q in queries for p in q['gold_answer_ids']})
    result['unique_gold_papers']=len(ids)
    years=source.con.execute('SELECT publication_year,count(*) FROM papers WHERE paper_id IN (SELECT unnest(?)) GROUP BY publication_year ORDER BY publication_year',[ids]).fetchall()
    result['unique_gold_paper_year_distribution']={str(year):n for year,n in years}
    generated=[q for q in queries if q['provenance']['source']=='generated']
    result['generated_joint_taxonomy']=dict(Counter('|'.join((q['modality_class'],q['reasoning']['complexity'],next((k for k,v in q['stress'].items() if k!='schema_version' and v),'normal'))) for q in generated))
    if output is not None:
        details=[]
        for q in generated:
            if q['provenance']['paired_stress_variant']!='normal' or 'graph' not in q['modalities']:continue
            record=json.loads((output/q['gold_evidence']['construction_record']).read_text(encoding='utf-8'))
            condition=record['conditions']['graph'];lengths=[len(p) for p in record['graph_witness_paths'].values()]
            details.append({'query_id':q['query_id'],'anchor_id':condition['anchor_id'],'anchor_traversal_degree':source.degree(condition['anchor_id']),
                            'graph_candidate_count':record['candidate_sets']['graph']['count'],'witness_paths':len(lengths),
                            'min_path_edges':min(lengths),'max_path_edges':max(lengths)})
        result['generated_graph_characteristics']=details
    return result
