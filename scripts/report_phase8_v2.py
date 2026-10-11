"""Machine-generate the bounded paced sample report without editing the old run."""
import csv
import io
import json
import statistics
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.experiments.runner import write
from research.rq2.contracts import METHODS
from research.evaluation.contracts import RunRecord
from scripts.prepare_phase8 import load_inputs
D=ROOT/'documentation/phase8_generation_v2'

def export(name,rows):
    write(D/(name+'.json'),rows)
    if not rows:return
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=list(rows[0]));writer.writeheader()
    writer.writerows({k:'NULL' if v is None else v for k,v in r.items()} for r in rows)
    (D/(name+'.csv')).write_text(buf.getvalue(),encoding='utf-8',newline='')

def mean(rows,key):
    values=[r[key] for r in rows if r[key] is not None]
    return statistics.mean(values) if values else None

def main():
    inputs=load_inputs();rows=[];stages=[];summary=[]
    journal=[json.loads(p.read_text(encoding='utf-8')) for p in (D/'stage_journal').glob('*.json')]
    http=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((D/'http_dispatches').glob('[0-9][0-9].json'))]
    for method in METHODS:
        path=D/method/'records.jsonl'
        records=[RunRecord.model_validate_json(l) for l in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []
        own=[]
        for r in records:
            d=json.loads(r.output.diagnostics) if r.output else {}
            chain=[j for j in journal if j['binding']==inputs[r.query_id].fingerprint()+method]
            completed=[j for j in chain if j['status']=='complete']
            row={'method':method,'query_id':r.query_id,'condition':'+'.join(r.stress),'answer_ids':r.answer_ids,
                'answer':r.answer,'gold_ids':r.gold_ids,'errors':','.join(e.code for e in r.errors),
                **{k:r.metrics[k] for k in ('set_accuracy','precision','recall','f1','exact_match','answerability_correctness')},
                'requests':len(chain),'completed_provider_responses':len(completed),
                'input_tokens':r.observation.input_tokens,'output_tokens':r.observation.output_tokens,
                'known_input_tokens':sum(j['usage'].get('input_tokens') or 0 for j in completed),
                'known_output_tokens':sum(j['usage'].get('output_tokens') or 0 for j in completed),
                'generation_ms':r.observation.generation_ms,'total_ms_including_pacing':r.total_latency_ms,
                'final_context_characters':None if method=='CF-03' and r.errors else r.metrics['context_characters'],
                'conflict_handling_accuracy':None,'experiment_id':r.experiment_id}
            rows.append(row);own.append(row)
            stages.extend({'method':method,'query_id':r.query_id,**s} for s in d.get('stage_results',[]))
        summary.append({'method':method,'query_records':len(own),'answers_available':sum(r['f1'] is not None for r in own),
            **{k:mean(own,k) for k in ('set_accuracy','precision','recall','f1','exact_match','answerability_correctness','generation_ms','total_ms_including_pacing','final_context_characters')},
            'requests':sum(r['requests'] for r in own),'known_input_tokens':sum(r['known_input_tokens'] for r in own),
            'known_output_tokens':sum(r['known_output_tokens'] for r in own)})
    export('per_query_comparison',rows);export('method_comparison',summary);write(D/'stage_outputs.json',stages)
    tradeoffs=[]
    for cost in ('final_context_characters','generation_ms','total_ms_including_pacing','requests','known_input_tokens','known_output_tokens'):
        eligible=[s for s in summary if s['answers_available']==2 and s[cost] is not None]
        for s in summary:
            strong=not any(o['f1']>=s['f1'] and o[cost]<=s[cost] and (o['f1']>s['f1'] or o[cost]<s[cost]) for o in eligible) if s in eligible else None
            tradeoffs.append({'method':s['method'],'quality':'mean_f1','cost':cost,'quality_value':s['f1'],'cost_value':s[cost],
                'descriptive_frontier':strong,'interpretation':'two-query diagnostic only; no automatic winner'})
    export('tradeoffs',tradeoffs)
    status=json.loads((D/'execution_status.json').read_text())
    failures=[h for h in http if h.get('http_status',0)>=400]
    truncations=[h['sequence'] for h in http if 'length' in h.get('finish_reasons',[])]
    total_input=sum((h.get('usage') or {}).get('prompt_tokens',0) for h in http)
    total_output=sum((h.get('usage') or {}).get('completion_tokens',0) for h in http)
    lines=['# Phase 8 v2 — bounded diagnostic generation sample','',
        'This is a two-query paired diagnostic, not benchmark-wide evidence. The original failed run is unchanged. Phase 9 has not begun.','',
        f"Execution status: **{status['status']}**. Requests: **{len(http)} / 16 maximum**. Final answers available: **{sum(r['f1'] is not None for r in rows)} / 10**.",
        f"Known usage: **{total_input:,} input / {total_output:,} output tokens**. Provider error responses: **{len(failures)}**. Provider `length` finish reasons: **{truncations}**.",'',
        '| Method | Answers | Set accuracy | Precision | Recall | F1 | Exact Match | Answerability | Calls | Input tokens | Output tokens |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(v):return 'NULL' if v is None else str(round(v,4)) if isinstance(v,float) else str(v)
    for s in summary:
        lines.append('| '+' | '.join(fmt(s[k]) for k in ('method','answers_available','set_accuracy','precision','recall','f1','exact_match','answerability_correctness','requests','known_input_tokens','known_output_tokens'))+' |')
    lines+=['','## Normal versus conflict outcomes','',
        '| Method | Condition | Answer IDs | F1 | API generation ms | Total ms including pacing | Final context chars | Errors |',
        '|---|---|---|---:|---:|---:|---:|---|']
    for r in rows:lines.append('| '+' | '.join(fmt(r[k]) for k in ('method','condition','answer_ids','f1','generation_ms','total_ms_including_pacing','final_context_characters','errors'))+' |')
    lines+=['','## Interpretation and conflict handling','',
        'Both frozen questions have gold set {1258814}. The normal bundle lacks this paper; the conflict bundle adds only its tagged conflicting-rank overlay, not the canonical Text/Graph support needed for the full conjunction. Do not equate paper-ID presence with sufficient evidence. Empty answers score zero against the nonempty gold set but may reflect missing upstream support. Fusion was not allowed to repair this with new retrieval.',
        'Conflict-handling accuracy remains NULL: no independent conflict-action annotation exists, and canonical support is absent. Inspect explanations below for explicit conflict recognition; recognition alone does not prove a correct grounded answer.',
        'Observed explanations do not explicitly adjudicate the tagged conflicting rank. All six CF-03 intermediates abstained because their individual modality could not establish the entire conjunction. The frozen final parser allows only the union of intermediate answer IDs; that union was empty for both queries, so CF-03 could not introduce a paper at final fusion. This is a limitation of the approved late-fusion contract, not evidence that complementary facts were successfully reconciled. No algorithm or prompt was changed in response.',
        'API generation latency excludes the operational pacing wait. Phase 5 total latency includes the initial/inter-request waits and is therefore a scheduling measurement, not intrinsic model speed. CF-03 makes additional calls by design. Token use is provider-measured. Missing/failed metrics remain NULL.',
        'The descriptive trade-off table compares quality with context size, latency, requests and tokens only for methods with both final answers. With two paired queries, especially tied/zero quality, a nondominated point is not scientific superiority. **No RQ2 winner is selected.**','',
        '## Final explanations and CF-03 intermediates','']
    for s in stages:
        lines += [f"### {s['method']} — {s['query_id']} — {s['source']}",'','```json',s['raw'],'```','']
    lines+=['## Provenance and review gate','',
        'The prepared v2 configs, query seeds, frozen evidence, fusion implementations and generation settings are unchanged. Static outgoing payload hashes are checked against the prepared previews; late final contexts are constructed by the frozen CF-03 implementation. No retries or repairs are permitted. HTTP logs retain rate-limit headers, response usage and finish reasons without credentials.',
        'Artifacts: `per_query_comparison.csv`, `method_comparison.csv`, `tradeoffs.csv`, `stage_outputs.json`, `http_dispatches/`, `stage_journal/`, per-method Phase 5 records and manifests. Preservation/test results accompany this report. **Stop for human review; do not begin Phase 9.**']
    (D/'Phase_08_V2_Review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Generated v2 review:',len(rows),'query records;',len(http),'requests')

if __name__=='__main__':main()
