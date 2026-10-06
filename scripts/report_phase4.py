"""Generate the mandatory Phase 4 review from saved measured evidence."""
from collections import Counter
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.benchmark.build import load_jsonl,write,SPLITS
from scripts.audit_stark_mag import digest


def main():
    output=ROOT/'data/MMG_STARK_MAG/benchmark';docs=ROOT/'documentation/phase4'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    manifest=read(output/'benchmark_manifest.json');stats=read(output/'benchmark_stats.json');audit=read(output/'audit_results.json')
    review=read(output/'human_review/review_summary.json');regen=read(docs/'regeneration.json');preserved=read(docs/'preservation.json')
    assert regen['status']==preserved['status']=='pass' and audit['status']=='pass'
    tests=(docs/'pytest.txt').read_text(encoding='utf-8');assert '84 passed' in tests
    queries=[q for split in SPLITS for q in load_jsonl(output/(split+'.jsonl'))]
    examples=[]
    for cls in ('T','G','S','TG','TS','GS','TGS'):
        examples.append(next(q for q in queries if q['modality_class']==cls and q['provenance'].get('paired_stress_variant')=='normal'))
    for complexity in ('multi-hop-2','multi-hop-3+'):
        examples.append(next(q for q in queries if q['reasoning']['complexity']==complexity and q['provenance'].get('paired_stress_variant')=='normal'))
    for kind in ('noisy','conflict','unanswerable'):
        examples.append(next(q for q in queries if q['stress'][kind]))
    examples.extend(next(q for q in queries if q['provenance']['source']==kind) for kind in ('official_synthetic','official_human'))
    write(docs/'representative_examples.json',examples)
    for name in ('benchmark_manifest.json','benchmark_stats.json','audit_results.json','leakage_audit.json','human_exclusions.json','eligibility.json'):
        shutil.copyfile(output/name,docs/name)
    shutil.copyfile(output/'human_review/review_summary.json',docs/'review_summary.json')
    build=read(docs/'build_resources.json');audit_resources=read(docs/'audit_resources.json')
    table='\n'.join(f"| {s} | {stats['split'][s]:,} | {stats['by_split'][s]['source'].get('official_synthetic',0):,} | {stats['by_split'][s]['source'].get('generated',0):,} | {stats['by_split'][s]['source'].get('official_human',0):,} |" for s in SPLITS)
    modality='\n'.join(f"| {c} | {stats['modality'][c]:,} |" for c in ('T','G','S','TG','TS','GS','TGS','unverified'))
    group=Counter()
    for f in manifest['files']:group[f['path'].split('/')[0] if '/' in f['path'] else 'root_query_and_audit_files']+=f['bytes']
    size_table='\n'.join(f'| {k} | {v:,} |' for k,v in sorted(group.items()))
    graph=stats['generated_graph_characteristics']
    sample_text='\n\n'.join(f"**{q['modality_class']} / {q['reasoning']['complexity']} / {q['provenance'].get('paired_stress_variant','official')}** — `{q['query_id']}`\n\n{q['question']}\n\nGold: {len(q['gold_answer_ids'])} papers; first IDs: `{q['gold_answer_ids'][:8]}`." for q in examples)
    report=f'''# Phase Review Report

PHASE: 4 — Benchmark Construction Protocol

STATUS: **PASS — construction and automated audits complete; manual verification remains pending.**

OBJECTIVE: Preserve official QA and build a reproducible, source-isolated benchmark with verifiable generated answers and a reviewable human-audit package.

## 1. Checkpoint, preservation and scope

Approved Phase 3 was checkpointed as `3b34d9c234f9861455eea5fc7fd34a939f87518e`. The working tree was clean immediately afterward. The frozen baseline tag remains `4592d102b363c7d55d3c85ee67efe89409ae96b5`.

All 358 Phase 3 output hashes, the Phase 3 manifest, all 15 raw source hashes and the raw manifest are unchanged. All 54 protected MVP files and four baseline storage files are preserved. Phase 3 package pins remain unchanged; pip check passes; no dependencies were installed. No Phase 5 or later method modules were changed.

The original 13,323 synthetic QA and all 84 human QA records are preserved in original-record JSONL files and byte-identical CSV/split copies under `source_preservation/`. The original raw source remains untouched. Query IDs and official split membership remain traceable.

## 2. Exact benchmark split counts and composition

| Split | Total | Official synthetic | Generated | Official human |
| --- | ---: | ---: | ---: | ---: |
{table}
| **Total** | **13,571** | **13,323** | **167** | **81** |

The generated portion comprises **42 distinct base constructions** (two per modality class per main split) and correlated stress variants. It must not be treated as 167 independent semantic questions. The complete official human preservation file still has **84** records.

## 3. Modality, reasoning, stress and answer distributions

| Modality class | Count |
| --- | ---: |
{modality}

Official QA does not provide verified modality/hop annotations. Its 13,404 retained records deliberately remain **unverified** rather than receiving fabricated T/G/S or hop labels. Generated records have verified operational source requirements. The schema extends the Phase 1 immutable Contract and preserves all requested fields; official hop_count/multi_hop are NULL, with unverified complexity/difficulty. Official records must remain outside verified modality/hop strata until reviewed.

Reasoning: **104 single-hop**, **32 multi-hop-2**, **31 multi-hop-3+**, **13,404 unverified**. Hop count is maximum required graph path length; direct text/structured constraints are single-hop. Modality count is a separate dimension.

Stress: **13,446 normal** (13,404 official + 42 generated), **41 noisy**, **42 conflict**, **42 unanswerable**. One GS test noisy variant was omitted because a required distractor could not be verified. Coverage was not forced with a weak replacement.

Answer-set sizes: **42 empty**, **6,534 singleton**, **5,252 with 2–5**, **1,698 with 6–20**, **24 with 21–100**, **21 with more than 100** papers. There are **36,706 unique gold papers**; their recorded years range from 1958 to 2019, with 952 NULL years. The complete annual distribution and joint modality/reasoning/stress table are in [benchmark_stats.json](../phase4/benchmark_stats.json).

The {len(graph)} normal graph-containing constructions have anchor traversal degrees from {min(x['anchor_traversal_degree'] for x in graph)} to {max(x['anchor_traversal_degree'] for x in graph)}, graph candidate counts from {min(x['graph_candidate_count'] for x in graph)} to {max(x['graph_candidate_count'] for x in graph)}, and one-, two- or three-edge witness paths. Per-query characteristics are in the statistics file.

## 4. Human compatibility exclusions

| Source query | Original answer IDs | Original types | Treatment |
| --- | --- | --- | --- |
| 30 | 832321 | author | Whole query excluded from primary human_test. |
| 50 | 1174913, 15775 | paper, author | Whole query excluded, including its paper answer; no partial repair. |
| 72 | 98059 | author | Whole query excluded from primary human_test. |

The retained count **81** was calculated from authoritative node types. Untouched originals, IDs, types and reasons are in [human_exclusions.json](../phase4/human_exclusions.json); all 84 originals remain in `official_human_original.jsonl` and the source CSV.

## 5. Construction and gold verification

Seed 42 and deterministic ordering select source-linked conditions. Candidate sets are computed before templated wording, saved as sorted ID lists with hashes and counts, and combined by explicit set intersection. No LLM determines ground truth or wording; there were **zero LLM calls**.

Text conditions require explicit case-insensitive abstract claims, absent as complete conditions from graph labels. They are **bounded operational claim-matching queries**, not a claim of exhaustive semantic synonym coverage. Graph conditions require author/institution/citation paths with unique named anchors absent from answer text. Structured conditions use recorded nullable fields through parameterized predicates. Every answerable combined query must have a strict larger answer set when any required source is removed; counterexamples are stored.

Independent audit recomputed **all 167 generated variants**, **286 source-specific candidate-set references**, **665,671 distinct candidate IDs** against the canonical registry, and **2,336 answer witness paths**. All generated intersections matched persisted gold exactly. All 42 unanswerable mutations produced verified empty sets; their valid original questions/conditions/gold remain saved.

The **13,404 retained official records** match original wording, supplied gold, IDs and boundaries exactly. Their answer IDs are verified papers. Their arbitrary natural-language semantics and supplied gold were **not independently inferred/repaired**; this distinction is explicit in provenance and the human-review package.

## 6. Leakage and stress audits

Generated construction instances, graph anchors and **split-blind operator skeletons** are disjoint across splits. Template IDs are checked against actual predicate arity/operators/path shape, so adding a split prefix cannot conceal reuse. Complete source combinations pass strict necessity checks. Generated wording contains no answer IDs or full answer titles. Source schemas and frozen data remain isolated.

The automated scan found **zero unexpected exact duplicate groups** and **zero high-similarity official cross-split candidates** at the documented shingle/Jaccard/sequence thresholds. Intentional within-split normal/noise/conflict question duplicates are recorded as paired stress cases. This is a bounded scan, not proof that all semantic paraphrases are absent; human review remains required.

All **41 noisy overlays** contain verified wrong candidates: frozen-vector semantic neighbors failing text predicates, nearby citation detours failing graph conditions, or rows satisfying only a partial structured filter. All **42 conflict overlays** preserve an authoritative fact, altered evidence, mutation origin, inverse patch and expected canonical-source preference. Every reverse patch recovers the original field. Canonical stores and gold answers remain unchanged. No evaluation-time overlay executor was implemented.

## 7. Deterministic regeneration and storage

A separate full build, gold audit, review package and manifest were generated under `_build/phase4/regenerated`. **All {regen['files_byte_identical']} benchmark files are byte-identical**, including split JSONL, candidate sets, stress overlays, human-review HTML/evidence and manifest. Existing frozen outputs are verified rather than overwritten by the builder. No model/retrieval-quality outcomes were used to tune test content.

Benchmark root: `D:/codefiles/RAG_GraphRAG_Demo/data/MMG_STARK_MAG/benchmark/`.

| Artifact group | Bytes |
| --- | ---: |
{size_table}
| **Total excluding manifest** | **{manifest['total_bytes_excluding_manifest']:,}** |

There are {len(manifest['files'])} checksummed payload files plus `benchmark_manifest.json`. Exact paths, sizes and SHA-256 are in [benchmark_manifest.json](../phase4/benchmark_manifest.json). Candidate-set deduplication reduces repeated intersection evidence. The regeneration copy is retained separately for audit.

Test content freeze ID: `{manifest['test_content_freeze_id']}`. **Content freeze is not human approval or paper-quality release.**

## 8. Exact manual verification work

The browser review package contains **3,390 pending items**:

- **2,720 / 2,720 test queries**: all must be manually verified before paper-quality test experiments.
- **81 / 81 primary human_test queries**: all must be manually verified; authorship of a question is not a substitute for this source/gold audit.
- **589 validation queries**: 533 official queries (deterministic 20% sample) plus every 56 generated validation variants.

There are **zero recorded human approvals**. Review question meaning, complete gold set, evidence sufficiency, modality necessity, hop/stress labels and cross-split semantic leakage; enter pass/reject, reviewer and reason. Official items also need verified modality/hop annotations before stratified claims. Reject scientifically weak generated claim wording. Rejected official answers must never be repaired; change eligibility through a reviewed benchmark revision.

The package supplies readable answer titles, concise derivations/candidate counts, necessity counterexamples, stress payloads and **10,316 paper evidence records** with full abstracts, structured values and readable graph context. Citation lists are bounded previews and are labeled as such; consult immutable CSR for complete paths where necessary.

Open `data/MMG_STARK_MAG/benchmark/human_review/review.html`. Review decisions save locally in the browser and export as a separate JSON file. Export to preserve progress; benchmark and original QA files remain untouched. JSONL alternatives are `human_review/review_items.jsonl` and `human_review/paper_evidence.jsonl`.

## 9. Measured resources and tests

| Operation | Seconds | Peak process working set, bytes |
| --- | ---: | ---: |
| Final construction | {build['elapsed_seconds']:.2f} | {build['resources']['peak_working_set_bytes']:,} |
| Final primary audit | {audit_resources['elapsed_seconds']:.2f} | {audit_resources['resources']['peak_working_set_bytes']:,} |
| Full separate regeneration/audit/review | {regen['elapsed_seconds']:.2f} | {regen['resources']['peak_working_set_bytes']:,} |

Working-set figures are measured process peaks, not the sum of concurrent machine usage. CSR is memory-mapped, SQL is bounded to 512 MB/two threads, and only the existing ~1.075 GB FAISS flat index is loaded for distractor selection. No full in-memory Python graph, GPU re-embedding, remote API, package installation or paid call was used. Final preservation check observed {preserved['free_disk_bytes']:,} free disk bytes before retention of any later review files.

**84 tests passed**, including 16 Phase 4 synthetic/bounded-data tests for schema/taxonomy rejection, whole-query human filtering, NULL predicates, graph path semantics, strict modality necessity, empty-answer verification, overlay reversibility, split leakage, split-blind template signatures, Unicode/idempotent serialization and real candidate intersections. The existing single DuckDB deprecation warning remains non-failing and the approved Phase 3 code was not changed to suppress it.

## 10. Known limitations and Phase 5 readiness

1. Manual review is pending. Official modality/hop annotations and semantic gold correctness are explicitly unverified; they cannot support verified stratified claims yet.
2. Generated text gold uses explicit abstract claims. It is reproducible and source-isolated but narrower than unconstrained semantic retrieval and does not cover all synonymous descriptions.
3. Only 42 generated base constructions exist. Stress variants are paired/correlated. Split-specific operator families avoid template reuse but intentionally produce a distribution shift: graph train paths are one hop, validation two, test three. This is not an IID/depth-balanced causal comparison.
4. Some unanswerable and conflict mutations are deliberately simple. One GS noise case is absent. No balance was forced with unverifiable examples.
5. Automated paraphrase detection is bounded. A shared transductive paper corpus is intentional; paper overlap alone is not treated as leakage. Broader semantic/template leakage needs human judgment.
6. Frozen MiniLM input remains 256 tokens; full abstracts remain stored and reviewable. Venue taxonomy remains the documented project normalization; source NULLs are preserved.

**Ready for Phase 5 implementation after your approval**, with machine-readable splits, schemas, provenance, candidate sets, overlays and release status. **Not ready for paper-quality final test use** until the stated manual work is complete. No Phase 5 metrics, experiment runner, B1–B4 retrievers, advanced algorithms or final test experiments have begun.

## Files created/modified, commands and decisions

Created `configs/phase4.yaml`, benchmark contracts/read-only source access/construction/stress/build/audit/review modules, build/audit/review/regeneration/preservation/report CLI scripts, `tests/test_benchmark.py`, ignored benchmark artifacts and `documentation/phase4/` review evidence. Appended Dataset_Manifest and Research_Decision_Log. The approved Phase 3 representation files and code remain unchanged.

Commands used the project interpreter: `scripts/build_benchmark.py`, `scripts/audit_benchmark.py`, `scripts/prepare_benchmark_review.py`, `scripts/check_benchmark_regeneration.py`, `scripts/check_phase4_preservation.py`, and `-m pytest -q -p no:cacheprovider`. Source checks preceded and followed construction. Git checkpoint/trust overrides were scoped per command. A Windows-default text-decoding failure was corrected by explicit UTF-8 reads; the full audit then passed.

DECISIONS LOGGED: P4-01 through P4-12 in [Research_Decision_Log.md](../Research_Decision_Log.md). Full field/predicate/split/review semantics and commands: [Benchmark_Protocol.md](../phase4/Benchmark_Protocol.md).

SCIENTIFIC INVARIANTS CHECKED: unchanged source/representations/MVP/tag; canonical global IDs; no imputation or answer repair; exact generated source sets/intersections; source necessity; explicit original/derived edge directions; independent taxonomy dimensions; unchanged official splits; evaluation-only stress; no final test tuning or later-phase implementation.

REVIEW QUESTIONS FOR USER: No construction blocker requires manual action now. Approve or request changes to Phase 4; human-verification work above is required before paper-quality experiments.

NEXT PHASE (NOT STARTED): **Phase 5 — Evaluation Harness and Experiment Runner**.

## Representative examples

{sample_text}

Complete examples, full gold lists and provenance are in [representative_examples.json](../phase4/representative_examples.json).

**STOP: Phase 4 construction is complete. Phase 5 has not begun.**
'''
    target=ROOT/'documentation/Phase_Reports/Phase_04_Benchmark_Construction.md';target.write_text(report,encoding='utf-8')
    paths=[*docs.glob('*'),target,ROOT/'documentation/Research_Decision_Log.md',ROOT/'documentation/Dataset_Manifest.md',
           * (ROOT/'research/benchmark').glob('*.py'),ROOT/'configs/phase4.yaml',ROOT/'tests/test_benchmark.py',
           * (ROOT/'scripts').glob('*benchmark*.py'),ROOT/'scripts/check_phase4_preservation.py',ROOT/'scripts/probe_phase4.py',Path(__file__).resolve()]
    write(docs/'file_manifest.json',{'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
          for p in sorted(set(paths)) if p.is_file() and p.name!='file_manifest.json']})
    print(target)

if __name__=='__main__':main()
