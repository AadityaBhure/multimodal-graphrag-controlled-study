"""Read-only forensic comparison; writes only the new compliance audit namespace.

No model calls, retrieval, scientific method edits, or test/human-test execution.
The findings are source-review judgments, not generated claims of passing tests.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.evaluation.benchmark import BenchmarkReader, digest
from research.experiments.runner import labels

D = ROOT / 'documentation/compliance_repair'
SPEC = ROOT / 'documentation/specifications/phase9/Phase1D_Exact_Implementation_Specifications_9_Methods.docx'

# One entry per frozen algorithm step. PASS means inspected source implements
# this step; it is not a claim that the whole method/experiment is compliant.
FINDINGS = {
 'CM-01': (49, 'research/rq1/manager.py; research/rq1/candidates.py; research/rq1/graph.py', [
 ('EQUIVALENT_IMPLEMENTATION', 'Query embedding is prepared once in build_pool with the frozen MiniLM model.'),
 ('DEVIATION', 'Scores bounded graph node labels, not all retrievable source chunks.'),
 ('DEVIATION', 'Selects ten graph nodes rather than ten semantic source chunks.'),
 ('MISSING', 'No chunk_graph_links/source_chunk/source_evidence_ids mapping exists; graph relations have edge provenance only.'),
 ('DEVIATION', 'Expands one hop from selected nodes inside a pre-materialized B2 depth-two pool, not the specified chunk-linked seed universe.'),
 ('DEVIATION', 'mst_cost is 1 minus endpoint-to-endpoint cosine, not query-to-source-chunk cosine.'),
 ('PASS', 'Connected components are computed deterministically.'),
 ('DEVIATION', 'Minimum forest is over different weights; root is highest query-relevance node; serialization is node/edge records rather than once-per-source-chunk DFS.'),
 ('DEVIATION', 'Pinned approved BGE reranks node-label JSON sequences, not tree triplet representations.'),
 ('PASS', 'Components are sorted by descending measured reranker score, with stable ties.'),
 ('DEVIATION', 'Deduplicates node/edge IDs and budgets graph records, not the specified source chunk IDs/text representations.'),
 ('PASS', 'Returns the shared ContextPackage and method diagnostics.'),
 ]),
 'CM-02': (96, 'research/rq1/candidates.py; research/rq1/pcst.py; research/rq1/manager.py', [
 ('DEVIATION', 'Embeds query and node labels; never embeds edge descriptions.'),
 ('DEVIATION', 'Node cosine exists; edge relevance is mean endpoint/query cosine, not query/edge-text cosine.'),
 ('DEVIATION', 'Top three nodes but top five distinct edge-score levels rather than five edges.'),
 ('DEVIATION', 'Tie-level sharing and 0.99 decay are not exact edge rank prizes k..1; more than five edges can receive positive prizes.'),
 ('DEVIATION', 'PCST objective structure is present, but operates on noncontract edge prizes; disconnected output is silently replaced.'),
 ('PASS', 'Virtual prize nodes and reduced edge costs implement the standard positive edge-prize reduction.'),
 ('PASS', 'Invokes pinned pcst_fast 1.0.10 with one cluster and GW pruning.'),
 ('DEVIATION', 'Manager uses DFS, not BFS from highest-prize node.'),
 ('DEVIATION', 'Generic skip-to-fit serializer; no lowest-net-contribution leaf-branch pruning or repeated budget recomputation.'),
 ('PASS', 'Returns node/edge provenance and selected graph diagnostics; valid real outputs were connected.'),
 ]),
 'CM-03': (139, 'research/rq1/diffusion.py; research/rq1/candidates.py; research/rq1/manager.py', [
 ('MISSING', 'No deterministic LLM JSON keyword extraction or query-ID keyword cache.'),
 ('DEVIATION', 'Embeds raw question and node labels; no keyword embeddings.'),
 ('DEVIATION', 'Uses raw-question cosine, not maximum keyword-to-node cosine.'),
 ('DEVIATION', 'N_seed=20 is present, but ranking comes from the wrong semantic signal.'),
 ('UNVERIFIED', 'Product of shifted endpoint query cosines is implemented; no recorded equivalence to the required QAFD hybrid formulation.'),
 ('PASS', 'Sink capacity is one.'),
 ('PASS', 'Injects alpha=10 per selected seed.'),
 ('DEVIATION', 'Excess redistribution exists but has an early infeasibility return; per-node max-excess stopping differs from total-excess condition; no relabel state.'),
 ('DEVIATION', 'Uses support/max(support) >= .01 instead of raw x_v > .01.'),
 ('DEVIATION', 'Nonconvergence returns semantic nodes instead of current support; otherwise retains induced edges.'),
 ('PASS', 'Successful diffusion support is ordered by descending raw support, ties by stable node ID.'),
 ('DEVIATION', 'Generic serialization does not preserve or tag needed connectors.'),
 ('DEVIATION', 'No iterative lowest-x peripheral/leaf pruning; generic packing may remove connecting evidence.'),
 ('DEVIATION', 'Some flow diagnostics exist; keywords, per-node retained x values and timeout state are absent.'),
 ]),
 'CF-01': (190, 'research/rq2/fusion.py; scripts/prepare_phase8.py', [
 ('PASS', 'Consumes frozen source-partitioned evidence; no retriever dependency.'),
 ('DEVIATION', 'Explicit ID then unique normalized alias only; no final GLOBAL_ENTITY_RESOLVER interface; primary entity only.'),
 ('PASS', 'Groups source evidence under resolved canonical entity IDs.'),
 ('EQUIVALENT_IMPLEMENTATION', 'Unresolved evidence receives explicit unresolved:<evidence_id> groups.'),
 ('MISSING', 'Does not calculate max-member score/source coverage or sort groups by these keys; uses insertion order.'),
 ('DEVIATION', 'ENTITY heading and source/provenance fields exist, but explicit TEXT/GRAPH/STRUCTURED/PROVENANCE group subsections are absent.'),
 ('PASS', 'Source partition order and original retriever item order are preserved within each group.'),
 ('DEVIATION', 'Packs individual items directly instead of testing complete groups first.'),
 ('DEVIATION', 'No group_truncated flag or prescribed highest-ranked individual fallback.'),
 ('PASS', 'Returns context, retained evidence and alignment diagnostics.'),
 ]),
 'CF-02': (228, 'research/rq2/fusion.py; research/rq2/contracts.py', [
 ('PASS', 'Structural candidates are Graph and Structured.'),
 ('PASS', 'Semantic candidates are Text.'),
 ('MISSING', 'No preselection provenance-overlap deduplication; only shared input ID uniqueness.'),
 ('MISSING', 'No compact candidate manifest for a selector model.'),
 ('DEVIATION', 'Lexical query-token overlap replaces the one required joint SELECTOR_LLM call.'),
 ('MISSING', 'No model JSON, ID validation or schema repair because selector is lexical.'),
 ('PASS', 'Starts selected list with at most five structural items.'),
 ('PASS', 'Reserves ten minus selected structural count for semantic fill.'),
 ('DEVIATION', 'Text rank is preserved but provenance-overlap duplicate skipping is absent.'),
 ('DEVIATION', 'Zero-overlap structural items can be discarded even when fewer than ten total items exist.'),
 ('PASS', 'Serializes source-labelled evidence without intermediate answers.'),
 ('DEVIATION', 'Skip-to-fit packing does not follow semantic-tail-then-structural-tail removal policy.'),
 ('DEVIATION', 'Lexical scores and selection traces exist; no required selector LLM usage trace.'),
 ]),
 'CF-03': (267, 'research/rq2/system.py; research/rq2/generation.py', [
 ('PASS', 'Sources are separated before intermediate calls.'),
 ('DEVIATION', 'Uses final answer_ids prompt/schema instead of candidate_answer/supporting_evidence_ids/confidence; calls even empty sources; cap220 is preserved.'),
 ('DEVIATION', 'Validates answer paper IDs, not intermediate supporting evidence IDs.'),
 ('DEVIATION', 'Builds intermediate final-answer-ID objects rather than required grounded modality objects.'),
 ('DEVIATION', 'Reuses ordinary final prompt without explicit complementary fusion/contradiction instructions; restricts final IDs to union of intermediate answer_ids.'),
 ('PASS', 'Final answer format/parser is the shared baseline JSON integer paper-set contract.'),
 ('PASS', 'Stores raw intermediate and final responses, usage and journal bindings.'),
 ]),
}

EXTRA = [
 ('ALL RQ1','Phase1D Â§4 scope','DEVIATION','Mixed Text/Structured must pass through fixed baseline policy. Historical comparison supplies graph-only evidence even on TG/GS/TGS.', 'research/rq1/system.py'),
 ('ALL RQ1','Repair Â§5 cohort','MISSING','Historical cohort has 16 normal/noisy records. Required repair cohort has all 32 verified graph-dependent validation records including conflict/unanswerable.', 'scripts/prepare_phase7.py'),
 ('ALL RQ1','Phase1D Â§3.2 / deferred budget','EQUIVALENT_IMPLEMENTATION','Phase6 globally froze 24000 characters, replacing the deferred unspecified numerical token budget. Do not invent a new cap; exact context tokens remain NULL without identified tokenizer.', 'documentation/Phase_Reports/Phase_06_Research_Baselines.md'),
 ('ALL RQ1','Fixed upstream candidate identity','PASS','All five historical methods receive identical candidate hashes. This protects comparability but does not validate the chosen candidate semantics.', 'scripts/audit_phase7.py'),
 ('CM-B0','Roadmap raw control','PASS','Raw candidate order with global safety cap. Must acquire fixed mixed-source pass-through in repaired experiment.', 'research/rq1/manager.py'),
 ('CM-B1','Roadmap fixed TopK/depth control','PASS','Five paper nodes, depth2, retained parent paths; deterministic ordering. Must acquire fixed mixed-source pass-through.', 'research/rq1/manager.py'),
 ('CM-01','Â§4.1 configuration','PASS','k_seed10, m1 and approved BGE revision 55611d7bca2a7133960a6d3b71e083071bbfc312 retained. Seed unit/weights remain deviations.', 'research/rq1/contracts.py; research/rq1/reranker.py'),
 ('CM-01','Â§4.1 fallback','MISSING','No graph-linked chunk detection or semantic_only source-chunk fallback exists.', 'research/rq1/manager.py'),
 ('CM-01','Minimum/maximum tree equivalence','DEVIATION','For fixed connected vertices, sum(1-w)=(|V|-1)-sum(w); equivalent only with identical w and tie ordering. Historical w is endpoint cosine, contract w is query/source-chunk cosine. Algebra cannot establish equivalence between different signals.', 'research/rq1/candidates.py; research/rq1/graph.py'),
 ('CM-02','Â§4.2 configuration','PASS','k_node3,k_edge5,Ce.5,solver pinned; no tuning. These values do not excuse different prize definitions.', 'research/rq1/contracts.py'),
 ('CM-02','Â§4.2 fallback','DEVIATION','Highest-node fallback also occurs for missing edges/semantics or disconnected solutions, rather than only empty PCST output.', 'research/rq1/pcst.py'),
 ('CM-03','Â§4.3 numerical defaults','PASS','N_seed20,alpha10,sink1,support.01,epsilon.05,Nmax1000000 are configured. Interpretation of support/convergence differs.', 'research/rq1/contracts.py'),
 ('CM-03','Â§4.3 fallback','DEVIATION','Infeasible components/nonconvergence/empty support return top-five semantic nodes. Contract permits semantic_nodes only for no linked keyword/seed and current support at limit/timeout.', 'research/rq1/diffusion.py'),
 ('CF-B0','Roadmap raw concatenation','PASS','Raw source-order concatenation with deterministic atomic packing; no intelligent selector. No algorithm repair identified.', 'research/rq2/fusion.py'),
 ('CF-B1','Roadmap source separated','PASS','Fixed Text/Graph/Structured sections and source shares; no intelligent selector. No algorithm repair identified.', 'research/rq2/fusion.py'),
 ('ALL RQ2','Â§5 cached evidence invariant','PASS','24 cached bundle hashes verified; no fusion retrieval. Common raw incoming evidence remains fixed.', 'scripts/prepare_phase8.py; research/rq2/system.py'),
 ('CF-01','Â§5.1 fallback','MISSING','No source-separated fallback when all entity resolutions fail.', 'research/rq2/fusion.py'),
 ('CF-01','Â§5.1 real resolver usage','UNVERIFIED','Frozen preparation consults authoritative Phase3 ID/alias registries. Additional resolver fallback was not implemented; real calls cannot be claimed.', 'scripts/prepare_phase8.py'),
 ('CF-02','Â§5.2 defaults','PASS','Kstructural5,Kout10 fixed; lexical variant must be labelled historical ablation externally without changing its old files.', 'research/rq2/contracts.py'),
 ('CF-02','Â§5.2 fallback','MISSING','No selector repair-once/relevance fallback path.', 'research/rq2/fusion.py'),
 ('CF-03','Â§5.3 failures','DEVIATION','Any stage exception exits whole chain. Missing ERROR_NO_EVIDENCE continuation and final exact-once retry.', 'research/rq2/system.py; research/rq2/generation.py'),
 ('ALL','Phase1D Â§3 common contracts','EQUIVALENT_IMPLEMENTATION','Uses Phase1 shared immutable evidence and Phase5 RunRecord/SystemOutput adapters; field naming differs with explicit source/provenance retained.', 'research/common/contracts.py; research/evaluation/contracts.py'),
 ('ALL','Phase1D Â§7 no post-hoc tuning','PASS','Historical reports/configs record fixed defaults; repair may fix deviations but must freeze new configs before results.', 'configs/rq1; configs/rq2'),
 ('ALL RQ1','Answer-quality evidence','MISSING','All historical Phase7 answer metrics are NULL; no answer generation. Context-only findings cannot establish answer preservation.', 'documentation/Phase_Reports/Phase_07_RQ1_Context_Management.md'),
 ('ALL RQ2','Answer-quality scope','MISSING','v2 generated only the normal/conflict pair; this cannot close the 24-query primary study or supplementary isolation study.', 'documentation/phase8_generation_v2/Phase_08_V2_Review.md'),
 ('ALL','Required paired inference','MISSING','Historical descriptive Pareto tables do not supply required paired CIs/tests/Holm analysis for repaired answer-quality results.', 'documentation/phase7; documentation/phase8'),
 ('ALL','Acceptance test coverage','UNVERIFIED','Historical passing tests validate historical algorithms. New contract-specific tests and full regression suite are required; no repaired tests have run.', 'tests/test_rq1.py; tests/test_rq2.py'),
]

def main():
    D.mkdir(exist_ok=True)
    root=ET.fromstring(zipfile.ZipFile(SPEC).read('word/document.xml'))
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    paras=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in root.findall('.//w:p',ns)]
    (D/'phase1d_extracted.txt').write_text('\n'.join(f'{i}: {p}' for i,p in enumerate(paras)),encoding='utf-8')
    rows=[]
    for method,(paragraph,paths,findings) in FINDINGS.items():
        steps=re.split(r'(?<!\d)(\d+)\. ',paras[paragraph])[1:]
        pairs=list(zip(steps[::2],steps[1::2]))
        assert len(pairs)==len(findings),(method,len(pairs),len(findings))
        for (number,requirement),(status,actual) in zip(pairs,findings):
            rows.append(dict(method=method,requirement=f'Phase1D paragraph {paragraph}, step {number}: {requirement.strip()}',status=status,actual=actual,source=paths))
    rows.extend(dict(method=m,requirement=req,status=s,actual=a,source=p) for m,req,s,a,p in EXTRA)
    for row in rows:
        deviation=row['status'] in ('DEVIATION','MISSING')
        row['changes_scientific_meaning']=deviation if row['status']!='UNVERIFIED' else None
        row['affected_history']='Phase7 80 context-only records' if 'CM' in row['method'] or 'RQ1' in row['method'] else 'Phase8 context-only and v1/v2 bounded generation records' if 'CF' in row['method'] or 'RQ2' in row['method'] else 'Phase7/8 historical studies'
        row['repair']='Implement exact stated requirement in new namespace; preserve historical code/results.' if deviation else 'Verify before canonical execution.' if row['status']=='UNVERIFIED' else 'Reuse compliant behavior; regression-check.'
        row['rerun_required']=deviation if row['status']!='UNVERIFIED' else None
    reader=BenchmarkReader(ROOT/'data/MMG_STARK_MAG/benchmark')
    qs=sorted((q for q in reader.records('validation') if q.provenance['source']=='generated' and 'G' in q.modality_class and labels(q).status=='programmatically_verified'),key=lambda q:q.query_id)
    selection={'rule':'All verified generated validation records whose modality includes G; no outcome selection','count':len(qs),'query_ids':[q.query_id for q in qs], 'modality':dict(Counter(q.modality_class for q in qs)), 'stress':dict(Counter('conflict' if q.stress.conflict else 'noisy' if q.stress.noisy else 'unanswerable' if q.stress.unanswerable else 'normal' for q in qs)), 'benchmark_sha256':reader.manifest_hash,'final_answer_calls':len(qs)*5,'execution_started':False}
    (D/'rq1_cohort.json').write_text(json.dumps(selection,indent=2)+'\n',encoding='utf-8')
    from scripts.prepare_phase8 import load_inputs
    inputs=load_inputs()
    assert len(inputs)==24
    history={}
    for method in ('CM-B0','CM-B1','CM-01','CM-02','CM-03'):
        records=[json.loads(x) for x in (ROOT/f'documentation/phase7/runs/{method}/records.jsonl').read_text(encoding='utf-8').splitlines()]
        details=[json.loads(r['output']['diagnostics']) for r in records]
        history[method]={'records':len(records),'answer_null':sum(r['output']['answer'] is None for r in records),'fallbacks':dict(Counter(d.get('reason','unspecified') for d in details if d.get('fallback')))}
    (D/'historical_trace_summary.json').write_text(json.dumps(history,indent=2)+'\n',encoding='utf-8')
    (D/'matrix.json').write_text(json.dumps({'spec_sha256':digest(SPEC),'rows':rows},indent=2)+'\n',encoding='utf-8')
    header='''# RQ1/RQ2 forensic scientific compliance matrix

Authority: original Phase1D specification (SHA-256 recorded in matrix.json), then deferred global decisions, then roadmap. Later Phase7/8 reports are historical evidence only. The Phase9 addendum is not used.

Pre-repair checkpoint: `34c8503` (`PRE_RQ1_RQ2_COMPLIANCE_REPAIR`); working tree was clean immediately afterward. Raw/representation/benchmark checks: 695 payloads passed. Frozen MVP tag remains `4592d102b363c7d55d3c85ee67efe89409ae96b5`. B1â€“B4 and historical files have individual hashes in `compliance_repair/pre_repair_preservation.json`. Agentic modules remain placeholders. No repair API call, training, test/human-test experiment or Phase9/10 implementation occurred.

This is a source/config/trace audit, not a claim of repaired compliance. PASS applies only to the listed requirement. EQUIVALENT_IMPLEMENTATION requires preserved semantics; DEVIATION changes the contract; MISSING is absent behavior; UNVERIFIED must not be silently treated as PASS. Exact extracted algorithm text, findings, affected historical runs, required repair and rerun flags are machine-readable in `compliance_repair/matrix.json`. Every numbered algorithm step is covered below. Historical acceptance tests need contract-specific replacement/addition, not merely rerunning old expectations.

## Original mismatch: CM-01 source-chunk provenance (resolved by frozen adaptation)

Phase1D Â§4.1 steps 2â€“6 require retrievable source chunks, triples linked to those chunks, and cosine(query, source_chunk) weights. Steps 8â€“11 require once-per-source-chunk DFS text and triplet reranking. Current Graph edges have only edge_id, source_edge_id, source_id, relation, relation_id, target_id, derived_inverse. Graph nodes have labels, not source chunks. Text has paper_id/title/abstract/content. No authoritative chunk-to-triple extraction lineage or mapping policy was found in research/scripts/configs/Phase3/Phase7 records. `source_edge_id` identifies the official edge, not a text chunk.

Canonical cross-view identity alone does not establish source-chunk provenance: author-affiliation edges have no paper endpoint; a citation has two paper endpoints. Choosing titles versus title+abstract, assigning one/both/all neighboring papers to a triple, or inventing chunks from triples changes semantic seeds, weights and surviving evidence. It can also violate the title-only Graph boundary and fixed Text pass-through. The current node-only approximation is a deviation, not a safe silent default. The user subsequently froze canonical graph-native relation provenance units in `rq1_repair/CM01_Frozen_Provenance_Adaptation.txt`. This is an explicit dataset-specific adaptation, selected before repaired results to preserve modality isolation rather than optimize outcomes. It replaces only the unavailable textual source-chunk concept. No paper-text extraction provenance is fabricated. Historical findings below remain unchanged; new implementation validation is reported separately.

## Cohorts frozen before repaired outcomes

RQ1: 32 records; G/TG/GS/TGS each 8; normal/noisy/conflict/unanswerable each 8. This requires 160 final-answer calls, plus CM-03 keyword extraction calls. Exact token estimates require compliant, frozen contexts and will be reported before dispatch. No requests dispatched. RQ2: 24 original bundle hashes verified (TG/TS/GS/TGS each 6), untouched. Isolation selection/construction has not begun; no scientific completion claim is made.

## Algorithm and control findings

| Method | Requirement | Status | Actual behavior / evidence | Source |
|---|---|---|---|---|
'''
    def cell(s):return s.replace('|','\\|').replace('\n',' ')
    lines=[header]
    for r in rows:lines.append('| '+' | '.join(cell(str(r[k])) for k in ('method','requirement','status','actual','source'))+' |\n')
    lines.append('''
## Historical supersession policy

All original files remain preserved. Historical Phase7 is a graph-only, bounded, context-only comparison; its measured timings/context sizes describe those implementations, not compliant RQ1 answer quality. The endpoint-cost MST may be a valid maximum endpoint-similarity forest, but is not the required query/source-chunk tree. PCST distinct-level prizes and CM-03 semantic fallbacks are historical variants. Historical CF-02 is labelled **CF-02-LEXICAL-HISTORICAL** here only; original identifiers/records remain unchanged. CF-03 v1/v2 remains evidence of the old final-answer-ID intermediate contract, including failures and empty answers. No result is silently deleted or promoted to canonical repaired evidence. CF-B0/B1 evidence-preservation results remain useful; two paired generated answers remain only a bounded diagnostic.

## Current gate

RQ1_IMPLEMENTATION_COMPLIANCE = FAIL
RQ1_EXPERIMENTAL_COMPLIANCE = FAIL
RQ1_SCIENTIFIC_STATUS = INCOMPLETE
RQ2_IMPLEMENTATION_COMPLIANCE = FAIL
RQ2_PRIMARY_EXPERIMENT_STATUS = INCOMPLETE
RQ2_FUSION_ISOLATION_STATUS = INCOMPLETE
RQ2_SCIENTIFIC_STATUS = INCOMPLETE
PHASE_9_UNBLOCKED = NO

Repair is in progress in research/repair/rq1_compliance_v1. CM-01 provenance is resolved by the user-frozen graph-native adaptation. Historical CM-01 remains PRESERVED / NON-CANONICAL / SUPERSEDED FOR FINAL RQ1 INFERENCE. No repaired experiments or Phase9/10 work have begun. Implementation compliance must pass before dispatch.
''')
    (ROOT/'documentation/RQ1_RQ2_Compliance_Matrix.md').write_text(''.join(lines),encoding='utf-8')
    print(json.dumps({'requirements':len(rows),'classifications':dict(Counter(r['status'] for r in rows)),'rq1_queries':len(qs),'rq2_bundles_verified':len(inputs),'history':history},indent=2))

if __name__=='__main__':main()
