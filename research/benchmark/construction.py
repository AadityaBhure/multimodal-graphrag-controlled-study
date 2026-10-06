"""Deterministic candidate-set construction, wording and counterfactual checks."""
from copy import deepcopy
from itertools import combinations
import random
from research.common.serialization import content_hash

MODALITIES = {'T':('text',),'G':('graph',),'S':('structured',),'TG':('text','graph'),
              'TS':('text','structured'),'GS':('graph','structured'),'TGS':('text','graph','structured')}


def template_signature(conditions):
    """Split-blind operator skeleton; renaming a template cannot hide leakage."""
    skeleton={}
    for modality,c in conditions.items():
        if modality=='text':skeleton[modality]={'operator':c['operator'],'clause_count':len(c['phrases'])}
        elif modality=='graph':skeleton[modality]={'path_kind':c['kind']}
        else:skeleton[modality]=[(f['field'],f['operator']) for f in c['filters']]
    return content_hash(skeleton)


def intersection(sets):
    return set.intersection(*(set(s) for s in sets.values()))


def necessity(sets):
    gold = intersection(sets)
    if not gold:
        return False
    if len(sets)==1:
        return True
    return all(intersection({k:v for k,v in sets.items() if k!=m}) > gold for m in sets)


def text_conditions(source, split):
    phrases=source.config.text_claims[split]
    if split=='train':
        options=[{'operator':'all','phrases':[p]} for p in phrases]
    elif split=='validation':
        options=[{'operator':'any','phrases':list(pair)} for pair in combinations(phrases,2)]
    else:
        options=[{'operator':'all','phrases':[a,b]} for a in phrases[:6] for b in phrases[6:]]
    accepted=[]
    for condition in options:
        values=source.text(condition)
        if not 2<=len(values)<=10000:
            continue
        clauses=['contains(lower(label), ?)']*len(condition['phrases'])
        sep=' OR ' if condition['operator']=='any' else ' AND '
        graph_count=source.con.execute('SELECT count(*) FROM nodes WHERE ('+sep.join(clauses)+')',condition['phrases']).fetchone()[0]
        # No paper title or entity/topic label supplies the complete explicit claim.
        if graph_count==0:
            accepted.append(condition)
    return accepted


def anchors(source,paper,split):
    authors=[a for a,_ in source.adjacent(paper,3,True)]
    if split=='train':
        for author in authors:
            if 2<=source.degree(author)<=400 and source.label(author):
                yield {'kind':'author','anchor_id':author}
    else:
        seen=set()
        for author in authors:
            for institution,_ in source.adjacent(author,0,False):
                if institution in seen:
                    continue
                seen.add(institution)
                if source.degree(institution)<=80 and source.label(institution):
                    yield {'kind':'institution' if split=='validation' else 'institution_citations','anchor_id':institution}


def structured_condition(row,split,precision=False):
    if any(row[k] is None for k in ('publication_year','publication_date','citation_count','paper_rank')):
        return None
    if split=='train':
        filters=[('publication_year','>=',row['publication_year']),('citation_count','>=',row['citation_count'])]
    elif split=='validation':
        if row['venue_namespace'] is None:
            return None
        filters=[('paper_rank','<=',row['paper_rank']),('venue_namespace','=',row['venue_namespace'])]
    else:
        filters=[('publication_date','<=',str(row['publication_date'])),('citation_count','<=',row['citation_count'])]
    if precision:
        filters.extend([('paper_rank','=',row['paper_rank']),('publication_year','=',row['publication_year']),('citation_count','=',row['citation_count'])])
    return {'filters':[dict(field=f,operator=o,value=v) for f,o,v in filters]}


def wording(source,conditions,split):
    parts=[]
    if 'text' in conditions:
        c=conditions['text']
        quotes=['“'+p+'”' for p in c['phrases']]
        connective=' or ' if c['operator']=='any' else ' and '
        # Explicitly bounded textual assertion avoids pretending to have exhaustive synonym gold.
        parts.append('the abstract explicitly includes '+('at least one of ' if c['operator']=='any' else '')+connective.join(quotes)+' (case-insensitive)')
        if c.get('required_extra_phrase'):
            parts[-1]+=' and also explicitly includes “'+c['required_extra_phrase']+'”'
    if 'graph' in conditions:
        c=conditions['graph']; label=source.label(c['anchor_id'])
        if c['kind']=='author':
            clause=f'the paper is written by {label}'
        elif c['kind']=='institution':
            clause=f'at least one author is affiliated with {label}'
        else:
            clause=f'the paper is cited by a paper written by an author affiliated with {label}'
        if 'additional_author' in c:
            clause+=' and is also written by '+source.label(c['additional_author'])
        parts.append(clause)
    if 'structured' in conditions:
        names={'publication_year':'publication year','publication_date':'publication date','citation_count':'citation count',
               'paper_rank':'paper rank','venue_namespace':'normalized venue namespace','venue_id':'venue ID'}
        ops={'=':'is','>=':'is at least','<=':'is at most','>':'is greater than','<':'is less than'}
        parts.append('the recorded '+', and the recorded '.join(f"{names[f['field']]} {ops[f['operator']]} {f['value']}" for f in conditions['structured']['filters']))
    starts={'train':'Find all papers for which ', 'validation':'Which papers satisfy these requirements: ', 'test':'Return the papers meeting all of the following: '}
    return starts[split]+'; and '.join(parts)+'?'


def generate_bases(source):
    used_instances=set(); anchor_owners={}; records=[]; diagnostics={}
    for split_index,split in enumerate(('train','validation','test')):
        pool=text_conditions(source,split)
        if not pool:
            raise ValueError(f'No isolated text conditions for {split}')
        rng=random.Random(source.config.seed+split_index)
        rng.shuffle(pool)
        diagnostics[split]={'isolated_text_conditions':len(pool),'attempts':0,'rejections':{}}
        def reject(reason):
            r=diagnostics[split]['rejections'];r[reason]=r.get(reason,0)+1
        # Hardest intersections get first choice of deterministic construction instances.
        for cls in ('TGS','TG','GS','TS','G','S','T'):
            wanted=MODALITIES[cls]; selected=0
            for tc in pool:
                seeds=sorted(source.text(tc));rng.shuffle(seeds)
                for seed in seeds[:200]:
                    graph_options=list(anchors(source,seed,split)) if 'graph' in wanted else [None]
                    for gc in graph_options:
                        diagnostics[split]['attempts']+=1
                        if gc and anchor_owners.get(gc['anchor_id'],split)!=split:
                            reject('anchor_owned_by_other_split');continue
                        conditions={}
                        if 'text' in wanted:conditions['text']=tc
                        if gc:conditions['graph']=gc
                        # Three-hop graph output need not contain the seed; choose one output's recorded attributes.
                        try:
                            gset=source.graph(gc)[0] if gc else None
                        except ValueError:
                            reject('graph_budget');continue
                        eligible=(gset & source.text(tc)) if gc and 'text' in wanted else gset if gc else {seed}
                        if not eligible:
                            reject('empty_graph_text');continue
                        attribute_seeds=sorted(eligible)[:12] if split=='test' and gc else [seed]
                        for attribute_seed in attribute_seeds:
                            if 'structured' in wanted:
                                sc=structured_condition(source.row(attribute_seed),split,precision=cls=='S')
                                if sc is None:reject('missing_structured');continue
                                conditions['structured']=sc
                            key=content_hash(conditions)
                            if key in used_instances:
                                continue
                            sets=source.candidates(conditions); gold=intersection(sets)
                            if not 1<=len(gold)<=source.config.max_generated_answers:
                                reject('answer_size');continue
                            if not necessity(sets):
                                reject('redundant_modality');continue
                            # A relational anchor name must not appear in any answer's text.
                            if gc:
                                label=source.label(gc['anchor_id'])
                                if len(label.strip())<5:
                                    reject('ambiguous_short_anchor');continue
                                count=source.con.execute('SELECT count(*) FROM texts WHERE paper_id IN (SELECT unnest(?)) AND contains(lower(content),?)',[sorted(gold),label.lower()]).fetchone()[0]
                                if count:
                                    reject('anchor_text_leakage');continue
                                # Anchor must have a unique exact source name (avoid ambiguous natural-language wording).
                                count=source.con.execute('SELECT count(*) FROM nodes WHERE lower(label)=?',[label.lower()]).fetchone()[0]
                                if count!=1:
                                    reject('ambiguous_anchor');continue
                            used_instances.add(key)
                            if gc:anchor_owners[gc['anchor_id']]=split
                            record={'instance_id':key,'split':split,'modality_class':cls,'conditions':deepcopy(conditions),
                                    'gold':sorted(gold),'question':wording(source,conditions,split),
                                    'template_family':template_signature(conditions)}
                            records.append(record);selected+=1
                            print(f'Generated {split}/{cls} {selected}: {len(gold)} answers',flush=True)
                            break
                        if selected>=source.config.base_items_per_class_split:break
                    if selected>=source.config.base_items_per_class_split:break
                if selected>=source.config.base_items_per_class_split:break
            if selected<source.config.base_items_per_class_split:
                diagnostics[split]['rejections']['coverage_shortfall_'+cls]=source.config.base_items_per_class_split-selected
                print(f'Coverage shortfall {split}/{cls}: {selected}',flush=True)
    return records,diagnostics


def impossible_mutation(source,record):
    conditions=deepcopy(record['conditions'])
    if 'structured' in conditions:
        maximum=source.con.execute('SELECT max(publication_year) FROM papers').fetchone()[0]
        conditions['structured']['filters'].append(dict(field='publication_year',operator='>',value=maximum))
        rule={'kind':'year_above_observed_max','observed_max':maximum}
    elif 'text' in conditions:
        original=source.text(conditions['text'])
        candidates=['dna microarray','black hole','superconducting','protein folding','galaxy','semiconductor']
        selected=None
        for phrase in candidates:
            other=source.text({'operator':'all','phrases':[phrase]})
            if other and not (original & other):
                selected=phrase;break
        if selected is None:
            return None
        # Preserve original OR groups, applying the extra clause separately.
        conditions['text']['required_extra_phrase']=selected
        rule={'kind':'add_disjoint_abstract_claim','phrase':selected,'original_candidates':len(original)}
    else:
        original=source.graph(conditions['graph'])[0]
        selected=None
        for author in range(0,10000):
            if source.label(author) and len(source.label(author))>=5:
                papers={p for p,_ in source.adjacent(author,3,False)}
                if papers and not (papers&original):
                    selected=author;break
        if selected is None:return None
        conditions['graph']['additional_author']=selected
        rule={'kind':'add_disjoint_coauthor','author_id':selected}
    return conditions,rule
