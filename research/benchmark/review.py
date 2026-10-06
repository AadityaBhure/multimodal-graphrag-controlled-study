"""Manual review package and deterministic content freeze; no automated approvals."""
from collections import Counter
import html
from importlib.metadata import version
import json
from pathlib import Path

from research.benchmark.build import SPLITS,load_jsonl,write,jsonl
from research.common.serialization import content_hash,canonical_json
from scripts.audit_stark_mag import digest
from research.common.config import PROJECT_ROOT


def review_package(source,output):
    queries=[q for split in SPLITS for q in load_jsonl(output/(split+'.jsonl'))]
    validation=[q for q in queries if q['split']=='validation' and q['provenance']['source']!='generated']
    validation.sort(key=lambda q:content_hash({'seed':source.config.seed,'query':q['query_id']}))
    count=round(len(validation)*source.config.validation_review_fraction)
    selected={q['query_id'] for q in validation[:count]}
    selected.update(q['query_id'] for q in queries if q['split'] in ('test','human_test') or q['split']=='validation' and q['provenance']['source']=='generated')
    rows=[q for q in queries if q['query_id'] in selected]
    paper_ids=sorted({p for q in rows for p in q['gold_answer_ids']})
    titles=source.titles(paper_ids)
    papers={p:{'paper_id':p,'title':titles[p]} for p in paper_ids}
    values=source.con.execute('SELECT paper_id,abstract FROM texts WHERE paper_id IN (SELECT unnest(?))',[paper_ids]).fetchall()
    for paper,abstract in values:papers[paper]['abstract']=abstract
    cursor=source.con.execute('SELECT * FROM papers WHERE paper_id IN (SELECT unnest(?))',[paper_ids])
    columns=[d[0] for d in cursor.description]
    for values in cursor.fetchall():
        row=dict(zip(columns,values));papers[row['paper_id']]['structured']={k:str(v) if k=='publication_date' and v is not None else v for k,v in row.items()}
    # Readable local graph context; citation lists are explicitly bounded previews.
    entity_ids=set()
    for paper in paper_ids:
        authors=[a for a,_ in source.adjacent(paper,3,True)]
        topics=[f for f,_ in source.adjacent(paper,2,False)]
        affiliations={a:[i for i,_ in source.adjacent(a,0,False)] for a in authors}
        citations=[p for p,_ in source.adjacent(paper,1,False)]
        cited_by=[p for p,_ in source.adjacent(paper,1,True)]
        entity_ids.update(authors);entity_ids.update(topics)
        for values in affiliations.values():entity_ids.update(values)
        papers[paper]['graph_context']={'authors':authors,'affiliations':affiliations,'topics':topics,
              'cites_preview':citations[:20],'cites_total':len(citations),'cited_by_preview':cited_by[:20],'cited_by_total':len(cited_by),
              'preview_is_complete_graph':False}
    labels=dict(source.con.execute('SELECT node_id,label FROM nodes WHERE node_id IN (SELECT unnest(?))',[sorted(entity_ids)]).fetchall())
    for row in papers.values():
        graph=row['graph_context']
        graph['authors']=[{'node_id':a,'name':labels[a], 'institutions':[{'node_id':i,'name':labels[i]} for i in graph['affiliations'][a]]} for a in graph['authors']]
        graph['topics']=[{'node_id':f,'name':labels[f]} for f in graph['topics']]
        del graph['affiliations']
    review=[]
    quarantine=set(json.loads((output/'eligibility.json').read_text(encoding='utf-8'))['quarantined_query_ids'])
    for q in rows:
        generated=q['provenance']['source']=='generated'
        record=json.loads((output/q['gold_evidence']['construction_record']).read_text(encoding='utf-8')) if generated else None
        evidence={'conditions':record['conditions'],'candidate_counts':{m:r['count'] for m,r in record['candidate_sets'].items()},
                  'intersection_gold_size':len(q['gold_answer_ids']),'necessity_counterexamples':record['modality_necessity_counterexamples'],
                  'graph_witness_paths':record['graph_witness_paths'],'mutation':record['mutation']} if record else {
                  'source_record':q['gold_evidence'],'limitation':'Official source supplies answers, not verified view-specific derivations. Inspect the supplied paper evidence and frozen graph before approving semantics or modality/hop labels.'}
        if q['provenance'].get('stress_record'):
            evidence['stress_overlay']=json.loads((output/q['provenance']['stress_record']).read_text(encoding='utf-8'))
        item={'query_id':q['query_id'],'split':q['split'],'question':q['question'],'modality_class':q['modality_class'],
              'reasoning':q['reasoning'],'stress':q['stress'],'gold_answer_ids':q['gold_answer_ids'],
              'paper_titles':[{'paper_id':p,'title':titles[p]} for p in q['gold_answer_ids']], 'derivation_evidence':evidence,
              'modality_rationale':('Each recorded source predicate is evaluated independently; dropping any required source enlarges the original answer set. Text claims are absent from graph labels; relational anchor names are absent from answer texts. Unanswerable variants inherit the verified parent construction.' if generated else 'Unverified: reviewer must identify required sources and check authoritative answers; no automatic modality label was guessed.'),
              'quarantined_for_leakage_review':q['query_id'] in quarantine,'decision':'pending','reviewer':'','reason':'',
              'corrected_modality_annotation':'','corrected_hop_annotation':'','gold_source_must_not_be_edited':True}
        review.append(item)
    jsonl(output/'human_review/review_items.jsonl',review)
    jsonl(output/'human_review/paper_evidence.jsonl',[papers[p] for p in paper_ids])
    summary={'all_test_items':sum(q['split']=='test' for q in rows),'all_human_test_items':sum(q['split']=='human_test' for q in rows),
             'validation_items':sum(q['split']=='validation' for q in rows),'official_validation_sample':count,
             'total_review_items':len(rows),'paper_evidence_records':len(papers),'decisions_recorded':0,
             'pending':len(rows),'required_before_paper_quality_use':'Every final test/human_test item must be passed by a human; adjudicate duplicate quarantine and official modality/gold semantics. Validation sample must be reviewed. Rejections require a new version, never editing official answers.'}
    write(output/'human_review/review_summary.json',summary)
    payload=canonical_json({'items':review,'papers':papers,'review_content_id':content_hash([(q['query_id'],q['question'],q['gold_answer_ids']) for q in rows])}).replace('<','\\u003c')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>MMG benchmark human review</title>
<style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;background:#f7f9fc;color:#15243c}header,article{background:white;border:1px solid #dce3ed;padding:24px;border-radius:12px;margin:16px 0}button,select,input,textarea{font:inherit;padding:8px;margin:5px}button{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f4f8;padding:14px}textarea{width:95%}li{margin:8px}small{color:#54647a}.warning{color:#8b3713}#question{font-size:22px}details{margin:12px 0}</style>
<header><h1>Phase 4 · Human verification</h1><p>This is a pending review package, not an approved test release. Official answers remain unchanged. Paper context is read-only; citation previews are bounded.</p>
<select id="split"><option value="">All splits</option><option>test</option><option>human_test</option><option>validation</option></select><input id="search" placeholder="Find query ID or question"><button id="previous">Previous</button><button id="next">Next</button><span id="position"></span><p id="progress"></p></header>
<article><small id="identity"></small><p id="question"></p><p id="taxonomy"></p><p id="quarantine" class="warning"></p><p id="rationale"></p><details><summary>Derivation, candidate counts and stress evidence</summary><pre id="derivation"></pre></details><h3>Authoritative answer papers</h3><ul id="answers"></ul>
<label>Decision <select id="decision"><option>pending</option><option>pass</option><option>reject</option></select></label><input id="reviewer" placeholder="Reviewer name"><textarea id="reason" placeholder="Reason; confirm wording, gold completeness, modality necessity, stress and leakage. Never repair official answers."></textarea><input id="modality" placeholder="Verified modality (official items)"><input id="hop" placeholder="Verified hop count (official items)"><button id="save">Save review locally</button><button id="export">Export decisions JSON</button></article>
<script id="data" type="application/json">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('data').textContent);const $=id=>document.getElementById(id);let pos=0;
const key='mmg-phase4-'+data.review_content_id;let decisions=JSON.parse(localStorage.getItem(key)||'{}');
function filtered(){let s=$('search').value.toLowerCase();return data.items.filter(x=>(!$('split').value||x.split===$('split').value)&&(!s||(x.query_id+' '+x.question).toLowerCase().includes(s)))}
function show(){let list=filtered();pos=Math.max(0,Math.min(pos,list.length-1));let x=list[pos];if(!x)return;$('identity').textContent=x.query_id+' · '+x.split;$('question').textContent=x.question;$('taxonomy').textContent=x.modality_class+' · '+x.reasoning.complexity+' · '+JSON.stringify(x.stress);$('rationale').textContent=x.modality_rationale;$('quarantine').textContent=x.quarantined_for_leakage_review?'Potential cross-split duplicate: adjudication required.':'';$('derivation').textContent=JSON.stringify(x.derivation_evidence,null,2);$('answers').replaceChildren();x.paper_titles.forEach(p=>{let li=document.createElement('li'),d=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent=p.paper_id+' — '+p.title;pre.textContent=JSON.stringify(data.papers[p.paper_id],null,2);d.append(summary,pre);li.append(d);$('answers').append(li)});let r=decisions[x.query_id]||x;['decision','reviewer','reason'].forEach(k=>$(k).value=r[k]||'');$('modality').value=r.corrected_modality_annotation||'';$('hop').value=r.corrected_hop_annotation||'';$('position').textContent=(pos+1)+' / '+list.length;$('progress').textContent=Object.values(decisions).filter(x=>x.decision==='pass').length+' passed; '+data.items.length+' total required review items. Export decisions to preserve them outside this browser.'}
$('next').onclick=()=>{pos++;show()};$('previous').onclick=()=>{pos--;show()};$('split').onchange=()=>{pos=0;show()};$('search').oninput=()=>{pos=0;show()};$('save').onclick=()=>{let x=filtered()[pos];if(!x)return;if($('decision').value!=='pending'&&(!$('reviewer').value.trim()||!$('reason').value.trim())){alert('A reviewer and reason are required.');return}decisions[x.query_id]={query_id:x.query_id,decision:$('decision').value,reviewer:$('reviewer').value,reason:$('reason').value,corrected_modality_annotation:$('modality').value,corrected_hop_annotation:$('hop').value,reviewed_at:new Date().toISOString()};localStorage.setItem(key,JSON.stringify(decisions));show()};$('export').onclick=()=>{let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({benchmark:'MMG-STaRK-MAG-benchmark-v1',decisions:Object.values(decisions)},null,2)],{type:'application/json'}));a.download='human_review_decisions.json';a.click();URL.revokeObjectURL(a.href)};show();</script></html>'''
    path=output/'human_review/review.html';path.write_text(page.replace('PAYLOAD',payload),encoding='utf-8')
    return summary


def freeze_manifest(source,output):
    query_checksums={split:digest(output/(split+'.jsonl')) for split in SPLITS}
    files=[{'path':p.relative_to(output).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
           for p in sorted(output.rglob('*')) if p.is_file() and p.name!='benchmark_manifest.json']
    manifest={'schema_version':'1.0','benchmark_version':source.config.benchmark_version,'phase':4,
              'phase3_checkpoint':'3b34d9c234f9861455eea5fc7fd34a939f87518e',
              'representation_manifest_sha256':digest(source.root/'manifest.json'),'configuration':source.config.model_dump(mode='json'),
              'config_hash':content_hash(source.config.model_dump(mode='json')),'query_file_sha256':query_checksums,
              'test_content_freeze_id':content_hash({k:v for k,v in query_checksums.items() if k in ('test','human_test')}),
              'content_frozen':True,'paper_quality_release':'blocked_pending_human_review_and_leakage_adjudication',
              'human_reviewed_count':0,'official_labels_repaired':False,'llm_calls':0,
              'implementation_sha256':{p.relative_to(PROJECT_ROOT).as_posix():digest(p) for p in sorted((PROJECT_ROOT/'research/benchmark').glob('*.py'))},
              'files':files,'total_bytes_excluding_manifest':sum(f['bytes'] for f in files),
              'packages':{p:version(p) for p in ('numpy','pyarrow','duckdb','faiss-cpu','pydantic')}}
    write(output/'benchmark_manifest.json',manifest)
    return manifest
