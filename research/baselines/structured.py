"""Closed typed predicates, deterministic supported-language parsing, no supplied SQL."""
from datetime import date
import re
from typing import Literal
from pydantic import Field, StrictInt, StrictStr, model_validator
from research.common.config import ConfigSection

NUMERIC={'publication_year','citation_count','paper_rank'}
STRING={'venue_namespace','venue_id','venue_name','document_type'}


class Predicate(ConfigSection):
    field: Literal['publication_year','publication_date','citation_count','paper_rank','venue_namespace','venue_id','venue_name','document_type']
    op: Literal['=','!=','<','<=','>','>=','is_null','is_not_null']
    value: StrictInt | StrictStr | None = None

    @model_validator(mode='after')
    def valid(self):
        if self.op in ('is_null','is_not_null'):
            if self.value is not None:raise ValueError('NULL predicates have no value')
        elif self.value is None:raise ValueError('Use explicit NULL operators')
        elif self.field in NUMERIC:
            if type(self.value) is not int or self.value<0:raise ValueError('Numeric predicate needs nonnegative integer')
        elif self.field=='publication_date':
            if not isinstance(self.value,str):raise ValueError('Date requires ISO string')
            date.fromisoformat(self.value)
        elif not isinstance(self.value,str) or self.op not in ('=','!='):
            raise ValueError('String fields require exact string equality/inequality')
        if self.field=='venue_namespace' and self.value is not None and self.value not in ('journal','conference_series','conference_instance','original_venue'):
            raise ValueError('Unknown venue namespace')
        return self


class QueryPlan(ConfigSection):
    predicates: tuple[Predicate,...] = Field(min_length=1,max_length=16)
    conjunction: Literal['and'] = 'and'


def compile_plan(plan,limit):
    plan=QueryPlan.model_validate(plan)
    clauses=[];args=[]
    for p in plan.predicates:
        if p.op in ('is_null','is_not_null'):
            clauses.append(p.field+(' IS NULL' if p.op=='is_null' else ' IS NOT NULL'))
        else:
            clauses.append(p.field+' '+p.op+' ?');args.append(p.value)
    # Fixed projection/order; identifiers/operators originate exclusively from enums.
    sql='SELECT paper_id,publication_year,publication_date,citation_count,paper_rank,venue_namespace,venue_id,venue_name,document_type FROM papers WHERE '+' AND '.join(clauses)+' ORDER BY paper_id LIMIT ?'
    if type(limit) is not int or not 1<=limit<=100:raise ValueError('Invalid result limit')
    return sql,args+[limit]


def parse_question(question):
    """Recognize explicit structured clauses; other modalities remain unsupported."""
    text=question.lower().replace('\u201c','"').replace('\u201d','"')
    if re.search(r'\b(select|insert|delete|update|drop|attach|pragma|copy|union)\b',text) or '--' in text or '/*' in text:
        return None,'rejected_sql_language'
    predicates=[]
    names={'publication year':'publication_year','citation count':'citation_count','paper rank':'paper_rank',
           'publication date':'publication_date','normalized venue namespace':'venue_namespace','venue namespace':'venue_namespace',
           'venue name':'venue_name','venue id':'venue_id','document type':'document_type'}
    operators={'at most':'<=','at least':'>=','greater than':'>','less than':'<','before':'<','after':'>','not equal to':'!=','equal to':'=','exactly':'=','':'='}
    for label,field in names.items():
        pattern=r'\b'+label+r'\s+(?:is\s+)?(not null|null|missing|known)\b'
        for m in re.finditer(pattern,text):
            predicates.append(Predicate(field=field,op='is_null' if m[1] in ('null','missing') else 'is_not_null'))
        if field in NUMERIC:
            pattern=r'\b'+label+r'\s+(?:is\s+)?(?:(at most|at least|greater than|less than|before|after|not equal to|equal to|exactly)\s+)?(\d+)\b'
            for m in re.finditer(pattern,text):predicates.append(Predicate(field=field,op=operators[m[1] or ''],value=int(m[2])))
            for m in re.finditer(r'\b'+label+r'\s+(?:is\s+)?between\s+(\d+)\s+and\s+(\d+)',text):
                predicates.extend([Predicate(field=field,op='>=',value=int(m[1])),Predicate(field=field,op='<=',value=int(m[2]))])
        elif field=='publication_date':
            for m in re.finditer(r'\bpublication date\s+(?:is\s+)?(?:(before|after|at least|at most|exactly)\s+)?(\d{4}-\d{2}-\d{2})',text):
                predicates.append(Predicate(field=field,op=operators[m[1] or ''],value=m[2]))
        elif field=='venue_namespace':
            for m in re.finditer(r'\b'+label+r'\s+(?:is\s+)?(journal|conference_series|conference_instance|original_venue)\b',text):
                predicates.append(Predicate(field=field,op='=',value=m[1]))
        else:
            # Preserve case for exact source strings.
            for m in re.finditer(r'\b'+label+r'\s+(?:is\s+)?"([^"\n]{1,200})"',question,flags=re.I):
                predicates.append(Predicate(field=field,op='=',value=m[1]))
    for m in re.finditer(r'\bpublished\s+(in|before|after|since)\s+(\d{4})\b',text):
        predicates.append(Predicate(field='publication_year',op={'in':'=','before':'<','after':'>','since':'>='}[m[1]],value=int(m[2])))
    for m in re.finditer(r'\b(at least|at most|more than|fewer than)\s+(\d+)\s+citations\b',text):
        predicates.append(Predicate(field='citation_count',op={'at least':'>=','at most':'<=','more than':'>','fewer than':'<'}[m[1]],value=int(m[2])))
    unique={p.model_dump_json():p for p in predicates}
    if not unique:return None,'unsupported_no_structured_filter'
    # Disjunction between structured clauses is not silently converted to AND.
    if re.search(r'\bor\s+(?:the recorded\s+)?(?:publication|citation|paper rank|venue|document)',text):
        return None,'unsupported_structured_disjunction'
    return QueryPlan(predicates=tuple(unique.values())),'recognized_structured_clauses_only'
