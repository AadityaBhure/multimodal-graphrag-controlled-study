# Phase Review Report

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
| train | 8,049 | 7,993 | 56 | 0 |
| validation | 2,721 | 2,665 | 56 | 0 |
| test | 2,720 | 2,665 | 55 | 0 |
| human_test | 81 | 0 | 0 | 81 |
| **Total** | **13,571** | **13,323** | **167** | **81** |

The generated portion comprises **42 distinct base constructions** (two per modality class per main split) and correlated stress variants. It must not be treated as 167 independent semantic questions. The complete official human preservation file still has **84** records.

## 3. Modality, reasoning, stress and answer distributions

| Modality class | Count |
| --- | ---: |
| T | 24 |
| G | 24 |
| S | 24 |
| TG | 24 |
| TS | 24 |
| GS | 23 |
| TGS | 24 |
| unverified | 13,404 |

Official QA does not provide verified modality/hop annotations. Its 13,404 retained records deliberately remain **unverified** rather than receiving fabricated T/G/S or hop labels. Generated records have verified operational source requirements. The schema extends the Phase 1 immutable Contract and preserves all requested fields; official hop_count/multi_hop are NULL, with unverified complexity/difficulty. Official records must remain outside verified modality/hop strata until reviewed.

Reasoning: **104 single-hop**, **32 multi-hop-2**, **31 multi-hop-3+**, **13,404 unverified**. Hop count is maximum required graph path length; direct text/structured constraints are single-hop. Modality count is a separate dimension.

Stress: **13,446 normal** (13,404 official + 42 generated), **41 noisy**, **42 conflict**, **42 unanswerable**. One GS test noisy variant was omitted because a required distractor could not be verified. Coverage was not forced with a weak replacement.

Answer-set sizes: **42 empty**, **6,534 singleton**, **5,252 with 2–5**, **1,698 with 6–20**, **24 with 21–100**, **21 with more than 100** papers. There are **36,706 unique gold papers**; their recorded years range from 1958 to 2019, with 952 NULL years. The complete annual distribution and joint modality/reasoning/stress table are in [benchmark_stats.json](../phase4/benchmark_stats.json).

The 24 normal graph-containing constructions have anchor traversal degrees from 3 to 60, graph candidate counts from 2 to 1264, and one-, two- or three-edge witness paths. Per-query characteristics are in the statistics file.

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

A separate full build, gold audit, review package and manifest were generated under `_build/phase4/regenerated`. **All 323 benchmark files are byte-identical**, including split JSONL, candidate sets, stress overlays, human-review HTML/evidence and manifest. Existing frozen outputs are verified rather than overwritten by the builder. No model/retrieval-quality outcomes were used to tune test content.

Benchmark root: `D:/codefiles/RAG_GraphRAG_Demo/data/MMG_STARK_MAG/benchmark/`.

| Artifact group | Bytes |
| --- | ---: |
| construction_records | 29,882,473 |
| human_review | 376,271,345 |
| root_query_and_audit_files | 18,288,024 |
| source_preservation | 2,813,303 |
| stress_cases | 76,717 |
| **Total excluding manifest** | **427,331,862** |

There are 322 checksummed payload files plus `benchmark_manifest.json`. Exact paths, sizes and SHA-256 are in [benchmark_manifest.json](../phase4/benchmark_manifest.json). Candidate-set deduplication reduces repeated intersection evidence. The regeneration copy is retained separately for audit.

Test content freeze ID: `702818cf3060ae8c1fa1970febf15c639724b464c25586776a3d868e63dbdbae`. **Content freeze is not human approval or paper-quality release.**

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
| Final construction | 126.21 | 1,717,436,416 |
| Final primary audit | 132.83 | 693,907,456 |
| Full separate regeneration/audit/review | 301.52 | 2,903,150,592 |

Working-set figures are measured process peaks, not the sum of concurrent machine usage. CSR is memory-mapped, SQL is bounded to 512 MB/two threads, and only the existing ~1.075 GB FAISS flat index is loaded for distractor selection. No full in-memory Python graph, GPU re-embedding, remote API, package installation or paid call was used. Final preservation check observed 326,565,830,656 free disk bytes before retention of any later review files.

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

**T / single-hop / normal** — `generated:32aedaf5549088f16710:normal`

Find all papers for which the abstract explicitly includes “in agreement with experimental results” (case-insensitive)?

Gold: 48 papers; first IDs: `[1178172, 1221315, 1224524, 1244989, 1255794, 1270248, 1273965, 1276550]`.

**G / single-hop / normal** — `generated:9473d2a3de718dd5f693:normal`

Find all papers for which the paper is written by Michiel Wouters?

Gold: 13 papers; first IDs: `[1232670, 1271883, 1321868, 1358215, 1407974, 1419252, 1440393, 1573442]`.

**S / single-hop / normal** — `generated:04d3e281ff6812948a9e:normal`

Find all papers for which the recorded publication year is at least 2016, and the recorded citation count is at least 0, and the recorded paper rank is 21520, and the recorded publication year is 2016, and the recorded citation count is 0?

Gold: 3 papers; first IDs: `[1654213, 1706556, 1711184]`.

**TG / single-hop / normal** — `generated:5fda0cfd16f49ff668f3:normal`

Find all papers for which the abstract explicitly includes “in agreement with experimental results” (case-insensitive); and the paper is written by S. Pelli?

Gold: 1 papers; first IDs: `[1483523]`.

**TS / single-hop / normal** — `generated:78150b13cf63c1f9ca36:normal`

Find all papers for which the abstract explicitly includes “in agreement with experimental results” (case-insensitive); and the recorded publication year is at least 2018, and the recorded citation count is at least 1?

Gold: 3 papers; first IDs: `[1734558, 1831050, 1839231]`.

**GS / single-hop / normal** — `generated:de2b1a000cb7f254bc5a:normal`

Find all papers for which the paper is written by Fubo Tian; and the recorded publication year is at least 2010, and the recorded citation count is at least 3?

Gold: 5 papers; first IDs: `[1188337, 1244989, 1372335, 1448206, 1625340]`.

**TGS / single-hop / normal** — `generated:7fe82d9a6cdfbdfdce67:normal`

Find all papers for which the abstract explicitly includes “good agreement with experimental data” (case-insensitive); and the paper is written by Alexander Zhuk; and the recorded publication year is at least 2010, and the recorded citation count is at least 16?

Gold: 1 papers; first IDs: `[1460124]`.

**G / multi-hop-2 / normal** — `generated:5692e57aa6e252201105:normal`

Which papers satisfy these requirements: at least one author is affiliated with Baoji University of Arts and Sciences?

Gold: 78 papers; first IDs: `[1182036, 1182771, 1185098, 1185697, 1185812, 1191797, 1191996, 1193013]`.

**TGS / multi-hop-3+ / normal** — `generated:4ebd7cba5e0a63ef364b:normal`

Return the papers meeting all of the following: the abstract explicitly includes “experimental data” and “the results indicate” (case-insensitive); and the paper is cited by a paper written by an author affiliated with Jawaharlal Nehru Technological University, Hyderabad; and the recorded publication date is at most 2015-08-01, and the recorded citation count is at most 99?

Gold: 3 papers; first IDs: `[1175635, 1455398, 1505484]`.

**S / single-hop / noisy** — `generated:04d3e281ff6812948a9e:noisy`

Find all papers for which the recorded publication year is at least 2016, and the recorded citation count is at least 0, and the recorded paper rank is 21520, and the recorded publication year is 2016, and the recorded citation count is 0?

Gold: 3 papers; first IDs: `[1654213, 1706556, 1711184]`.

**S / single-hop / conflict** — `generated:04d3e281ff6812948a9e:conflict`

Find all papers for which the recorded publication year is at least 2016, and the recorded citation count is at least 0, and the recorded paper rank is 21520, and the recorded publication year is 2016, and the recorded citation count is 0?

Gold: 3 papers; first IDs: `[1654213, 1706556, 1711184]`.

**S / single-hop / unanswerable** — `generated:04d3e281ff6812948a9e:unanswerable`

Find all papers for which the recorded publication year is at least 2016, and the recorded citation count is at least 0, and the recorded paper rank is 21520, and the recorded publication year is 2016, and the recorded citation count is 0, and the recorded publication year is greater than 2019?

Gold: 0 papers; first IDs: `[]`.

**unverified / unverified / official** — `official:synthetic:1`

Show me articles related to magnetic field studies within the Digitized Sky Survey discipline.

Gold: 1 papers; first IDs: `[1265762]`.

**unverified / unverified / official** — `official:human:0`

I am interested in holograms, monte carlo, quantum dimensions and 3-partite -- what is a paper I should read that publishes on this topic?

Gold: 5 papers; first IDs: `[1797078, 1334906, 1647914, 1558348, 1651610]`.

Complete examples, full gold lists and provenance are in [representative_examples.json](../phase4/representative_examples.json).

**STOP: Phase 4 construction is complete. Phase 5 has not begun.**
