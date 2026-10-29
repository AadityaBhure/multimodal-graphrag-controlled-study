# Multi-Modal GraphRAG — Project Brief for Research-Paper Writing

**Project:** Multi-Modal GraphRAG: Fusing Text, Graph, and Structured Data for Enhanced LLM Reasoning
**Repository:** `D:/codefiles/RAG_GraphRAG_Demo/` (git; branches listed in §19)
**Author of the project:** Aaditya Bhure
**State captured:** 2026-10-12, about 10:30 IST (UTC+5:30), from files read in the repository on that day
**Audience:** a Claude instance (or any careful writer) that must turn this project into a research paper
**Purpose of this file:** give a complete, ordered, high-level → low-level account of what the project is, what has been built, what has been measured, what has *not* been measured, and what may and may not be claimed.

---

## 0. How to use this document (read first)

### 0.1 The five rules that override everything else

1. **No final scientific result exists yet for RQ1, RQ2, RQ3 or RQ4.** Every number in §10–§13 is either preliminary (historical, non-canonical for the final inference) or from a small demonstration study. The paper must not state or imply a winning method, an improvement, a ranking, or state-of-the-art performance.
2. **Negative and inconclusive results are acceptable and must be reported as such.** The project's standing rule: make methods faithful to the frozen specification and report honestly; never "improve" a method after seeing its results.
3. **Never fill a gap with a plausible number.** If a result is marked `PENDING` here, write `[PENDING: <what is needed>]` in the manuscript. Do not interpolate, estimate or round up.
4. **NULL is not zero.** Unmeasured metrics are stored as null/N/A. Do not convert them.
5. **Distinguish three things in every method description:** (a) the reference paper's mechanism, (b) the project's controlled adaptation of it, (c) the implementation as actually run. The project explicitly forbids claiming that its methods reproduce the full reference papers, or that cross-paper published numbers are comparable to its own.

### 0.2 Evidence tags used in this document

| Tag | Meaning |
|---|---|
| `[VERIFIED]` | The statement was read directly from a repository file (path given) during the capture of this brief. |
| `[REPORTED]` | The statement comes from a project report/handoff written by a previous agent session and was not re-verified in this capture. Treat as probable, check before quoting precisely. |
| `[DERIVED]` | Computed by the capture session from repository data (e.g. file counts). |
| `[PENDING]` | Does not exist yet. |

### 0.3 Deterministic reading order for the writer

1. §1 (summary) and §2 (status ledger) — know what exists.
2. §3–§4 (problem, design) — framing.
3. §5–§8 (data, benchmark, evaluation, generator) — the experimental substrate.
4. §9–§13 (baselines, RQ1–RQ4) — methods and the numbers that exist.
5. §14 (prototype/UI), §15 (provider constraints), §16 (chronology).
6. §17 (governance), §18 (limitations).
7. §20 (how to write the paper): claims allowed/forbidden, section skeleton, number sources.
8. §21 (open items you cannot resolve from this file).

### 0.4 Source-of-truth precedence (when two sources disagree)

1. `Phase1D_Exact_Implementation_Specifications_9_Methods.docx` (method semantics)
2. Later globally frozen choices (generator, reranker, budgets)
3. `Codex_Full_Project_Implementation_Roadmap.docx` (phase order, stop gates)
4. Approved Phase 0–6 contracts and `documentation/Research_Decision_Log.md`
5. Explicit user-approved dataset-specific adaptations (e.g. CM-01 graph-native provenance unit)
6. `documentation/Phase9_Frozen_Settings_Addendum.md` (revision 2) — only where Phase 1D is silent
7. Historical Phase 7/8 reports (evidence of what happened, **not** authority to redefine a method)

### 0.5 Known stale document

`CLAUDE_MASTER_HANDOFF_MULTIMODAL_GRAPHRAG.md` (repository root, untracked) was written on 2026-10-11 **before** Phase 9 began and says "Phase 9/RQ3 has not started" and "latest checkpoint 34c8503". Both are now outdated (see §16). Use that file for history of Phases 0–8 only; use *this* file for current state.

---

## 1. Executive summary

**What the project is.** A controlled research codebase that studies how a retrieval-augmented LLM should use three *heterogeneous* knowledge representations of the same scientific corpus: **Text** (paper title + abstract), **Graph** (authors, institutions, citations, fields of study) and **Structured** (SQL metadata: year, citations, rank, venue, document type). "Multi-modal" here means these heterogeneous representations, **not** images/audio/video.

**The data.** The official STaRK-MAG release (1,872,968 entities, 700,244 papers, 19,919,698 directed edges) is converted into three deliberately isolated views joined only by the official global node ID (MMG-STaRK-MAG v1). A benchmark of 13,571 queries is assembled: official synthetic and human queries (unverified labels) plus 167 generated, programmatically verified, labelled multi-modal queries with stress variants (noisy, conflict, unanswerable).

**The research questions.** RQ1 context management (what survives the context budget), RQ2 cross-modal fusion (how the three evidence streams are combined), RQ3 agentic retrieval (which source to query, in what order, when to stop), RQ4 integration (combined effect). Design principle: *one variable at a time first, integration second.* The method inventory is: 4 baselines (B1–B4), 9 literature-derived experimental methods (CM-01/02/03, CF-01/02/03, AR-01/02/03) and 6 simple controls (CM-B0/B1, CF-B0/B1, AR-B0/B1).

**Where the work stands (2026-10-12).**
- Infrastructure, data views, benchmark, evaluation harness and baselines B1–B4: **complete and audited**.
- RQ1 and RQ2: historical (Phase 7/8) experiments were run and are preserved, but a forensic audit found 41 deviations from the frozen method contract. A canonical repair was implemented but is **paused before any repaired research request was sent**. So RQ1/RQ2 have **no canonical result**.
- RQ3: all five policies are **implemented and unit-tested**; the controlled 56-query study has **not been run**; the training/calibration data pool is partly built (graph part 1,652 of 4,404 records, stalled).
- RQ4: **not started**.
- An integrated, professor-facing **prototype application** (Streamlit) exists on a separate branch and demonstrates the pipeline with live and recorded runs and a "Research Lab" tab of preliminary comparisons.

**What the paper can honestly be today.** A testbed/benchmark/protocol/infrastructure paper with a rigorous methodology section, a careful account of the audit-and-repair process, preliminary diagnostic observations, and clearly marked pending results. It cannot be a "method X beats Y" paper until the pending studies run (§20).

---

## 2. Status ledger (as of 2026-10-12)

| Component | Status | Evidence |
|---|---|---|
| Phase 0 – frozen MVP (12-PDF RAG + GraphRAG demo) | Complete; git tag `baseline-mvp-v1` → `4592d102…` | `[VERIFIED]` `documentation/Phase_Reports/Phase_00_*.md`, `git tag` |
| Phase 1 – research scaffold/contracts | Complete | `[REPORTED]` Phase 1 report; commit `ea88dcf` |
| Phase 2 – STaRK-MAG acquisition/audit | Complete | `[VERIFIED]` `documentation/Dataset_Manifest.md`, commit `f8fc9a2` |
| Phase 3 – MMG-STaRK-MAG v1 (3 views, indexes) | Complete | `[VERIFIED]` `documentation/phase3/Representation_Contract.md`, commit `3b34d9c` |
| Phase 4 – benchmark | Complete (content frozen); **human review not done** (3,390 pending) | `[VERIFIED]` `documentation/phase4/Benchmark_Protocol.md`, commit `262c4d1` |
| Phase 5 – evaluation harness/runner | Complete | `[REPORTED]` Phase 5 report; commit `721c27b` |
| Phase 6 – baselines B1–B4 + closeout | Complete (retrieval-only validation, 224 runs, no generation) | `[VERIFIED]` `documentation/phase6_closeout/Addendum.md`, commits `a19bdd5`, `cd450bb` |
| Phase 6.5 – research inspection UIs (ports 8502–8504) | Complete | `[REPORTED]` |
| Phase 7 – RQ1 original experiment | Complete but **non-canonical** (Graph-context only; method-fidelity deviations) | `[VERIFIED]` `Phase_07_*.md`, commit `2600275` |
| Phase 8 – RQ2 original experiment | Complete but **non-canonical** (CF-02/CF-03 deviations; upstream evidence insufficient) | `[VERIFIED]` `Phase_08_*.md`, commit `18b32f0` |
| RQ1/RQ2 compliance audit | Complete: 93 requirements audited | `[VERIFIED]` `documentation/compliance_repair/matrix.json` |
| RQ1/RQ2 canonical repair | **Paused** by user decision (2026-10-11). Code checkpointed; **0 repaired research requests sent**; 64/128 offline real-input checks done | `[VERIFIED]` `documentation/rq1_repair/*`, commit `9e112a9` |
| Groq admission/accounting diagnostics | Complete; admission semantics decided | `[VERIFIED]` `documentation/rq1_repair/GROQ_ADMISSION_SEMANTICS_DECISION.md` |
| RQ1 operational revision 2 | Written, **unvalidated**, only on branch `wip/rq1-operational-revision-2`; equivalence check NOT_RUN | `[VERIFIED]` same file |
| Phase 9 / RQ3 – spec consistency audit | Complete, no unresolved research-meaning conflict | `[VERIFIED]` `documentation/phase9/PHASE9_SPEC_CONSISTENCY_AUDIT.md` |
| Phase 9 / RQ3 – five policies implemented | Complete + unit tests | `[VERIFIED]` `documentation/phase9/PHASE9_METHOD_IMPLEMENTATION_REPORT.md`, `research/agentic/` |
| Phase 9 – frozen train/dev partition | Complete (7,302 / 747) | `[VERIFIED]` `documentation/phase9/partition/ar01_partition.json` |
| Phase 9 – retrieval pool for AR-01 labels / AR-02 calibration | **Partial and stalled**: text 4,299/4,299 ✔, structured 840/840 ✔, graph 1,652/4,404 ✘ (newest file 2026-10-11 14:25; no worker process running on 2026-10-12) | `[DERIVED]` file counts in `artifacts/phase9/pool/` vs. partition |
| Phase 9 – AR-01 training, AR-02 calibration (scientific) | **Not done** (needs complete pool). Only throw-away "lite" versions exist for the demo | `[VERIFIED]` no `documentation/phase9/ar01`, `/calibration`; `artifacts/phase9/lite/` exists |
| Phase 9 – frozen execution plan; primary 56-query run | **Not created / not run** | `[VERIFIED]` `scripts/run_phase9.py` requires `documentation/phase9/execution_plan.json`; absent; no `documentation/phase9/runs` |
| Phase 10 – RQ4 integrated system (formal) | **Not started** | `[VERIFIED]` `configs/rq4/README.md` only |
| Phase 11 – locked final test campaign | **Not started**; blocked by 2,801 required human review decisions | `[REPORTED]` |
| Phase 12 – results package/manuscript | **Not started** | |
| Professor demo / integrated prototype | Built; separate branch/worktree; port 8506 | `[VERIFIED]` `PROFESSOR_DEMO_README.md` (demo branch) |

Test suite: 255 tests are collected on the Phase 9 branch `[DERIVED: pytest --collect-only]`. At the pre-generation repair checkpoint 215 passed (1 known DuckDB deprecation warning) `[VERIFIED]` `documentation/rq1_repair/PROVIDER_AND_CM01_DIAGNOSTIC_REPORT.md`. The full suite was **not** re-run during this capture.

---

## 3. The research problem

### 3.1 Motivation (as framed by the project)
Real corpora describe the same entities in different forms: prose (abstracts), explicit relations (who wrote what, who is affiliated where, who cites whom), and scalar metadata (year, citations, rank, venue). A question such as *"Find all papers whose abstract says X, written by an author affiliated with institution Y, published at least in year Z with at least N citations"* needs all three. Three engineering questions follow, and the project isolates each as one research question:

- **How much and which evidence should reach the LLM?** (context management)
- **How should evidence of different kinds be combined?** (fusion)
- **Which sources should be queried, in what order, and when should retrieval stop?** (agentic retrieval)

### 3.2 Frozen research questions
| RQ | Question | The only variable | Held fixed |
|---|---|---|---|
| RQ1 Context Management | How can retrieved evidence be selected, ranked, pruned, deduplicated, compressed or budgeted while preserving information needed for grounded answers? | Context-management method | retrieval universe, non-RQ1 evidence pass-through, generator, answer prompt, shared budgets |
| RQ2 Cross-Modal Fusion | Which representation/fusion strategy most effectively combines Text, Graph and Structured evidence? | Fusion method | **byte-identical cached evidence bundle** per query; no fusion method may retrieve |
| RQ3 Agentic Retrieval | Can adaptive retrieval decide which sources to call, in what order, and when to stop, while reducing unnecessary retrieval? | Retrieval-control policy | B1/B2/B3 retrievers, downstream context policy, fusion policy, generator, answer prompt |
| RQ4 Integration | What is the combined effect of the empirically justified RQ1–RQ3 choices? | The combination | — (no winner is fixed in advance) |

### 3.3 Experimental philosophy
"One variable at a time first, integration second." Consequences that appear throughout the code and must appear in the paper's method section:
- RQ1 must not become a new retriever. RQ2 must not retrieve new evidence. RQ3 must not use stronger retrievers/fusion/context than its controls.
- Baselines stay deliberately simple (no hidden rerankers, query rewriting, routing, compression).
- Negative and inconclusive results are preserved, never overwritten.
- Test and human-test splits are never used for tuning or development.

### 3.4 What is *not* claimed about novelty
The roadmap states that no novelty/state-of-the-art claim may be added automatically; it requires "a separate literature-and-results review". The literature inventory in the project's earlier documents lists about 40 items, of which 12 were reviewed in depth and 9 retained as primary experimental adaptations `[REPORTED]`. A tenth item (`P040`) is an integrated-architecture/novelty reference, not an experimental method `[REPORTED]`. Do not claim that all 40 were deeply reviewed.

---

## 4. High-level architecture

### 4.1 Target pipeline
```
USER QUERY
  → AGENTIC RETRIEVAL       (RQ3: WHAT / WHERE / ORDER / STOP)
      ├── TEXT retriever        (dense, FAISS)
      ├── GRAPH retriever       (entity resolution + bounded CSR traversal)
      └── STRUCTURED retriever  (typed, parameterised, read-only DuckDB)
  → CROSS-MODAL FUSION      (RQ2: HOW evidence is combined)
  → CONTEXT MANAGEMENT      (RQ1: HOW MUCH survives the budget)
  → SHARED FINAL LLM (openai/gpt-oss-120b, temperature 0)
  → GROUNDED ANSWER + PROVENANCE + METRICS
```
Answers are **sets of paper IDs**, not free text. The generator may only cite paper IDs present in the context; a hallucinated ID makes the output a typed parse error, not an answer. An empty list is a legitimate abstention.

### 4.2 Three isolated views, one identity space
All three views are keyed by the authoritative integer **STaRK global node ID** (`canonical_id = "stark:<id>"`). Isolation rules (scientific invariants, §17.3):
- **Text view** receives only `paper_id, title, abstract, content = title + "\n\n" + abstract` — no authors, institutions, year, venue, citations, relations.
- **Graph view** uses node labels only (paper label = title **only**, never the abstract) and the four official relation types.
- **Structured view** uses only scalar paper metadata; no abstracts, authors or graph relations.

### 4.3 Repository code map (high level)
| Area | Path | Notes |
|---|---|---|
| Frozen original MVP | `app.py`, `src/`, `data/papers/`, `data/metadata.json`, `storage/` | 12 PDFs, kept immutable |
| Shared contracts/config/logging | `research/common/` | Pydantic contracts, canonical JSON, hashing, seeding |
| Dataset build/validation | `research/data/` | nodes, structured, edges, CSR, embeddings, FAISS, audits |
| Benchmark | `research/benchmark/` | construction, stress overlays, audit, review package |
| Evaluation + runner | `research/evaluation/`, `research/experiments/` | metrics, resumable atomic runner, evidence cache |
| Baselines B1–B4 | `research/baselines/` | |
| RQ1 (historical Phase 7) | `research/rq1/`, `configs/rq1/` | |
| RQ1 repair (canonical, paused) | `research/repair/` (`rq1_compliance_v1/`, `dispatch.py`) | |
| RQ2 (historical Phase 8) | `research/rq2/`, `configs/rq2/` | |
| RQ3 (Phase 9) | `research/agentic/` | 14 modules |
| Scripts | `scripts/` | build, run, report, audit, diagnose, phase9, demo |
| Tests | `tests/` | |
| Research inspection UIs | `research_app.py` (8502), `context_review_app.py` (8503), `fusion_review_app.py` (8504) | read-only/debug |
| Integrated product UI | `integrated_demo_app.py`, `research/product/` (demo branch) | port 8506 |

Placeholder-only modules (one-line stubs) still exist for `research/context/*`, `research/fusion/*`, `research/retrieval/*`, `research/generation/`; the real RQ1/RQ2 code lives in `research/rq1`, `research/rq2`, `research/repair`.

---

## 5. Data foundation

### 5.1 Source: STaRK-MAG `[VERIFIED]` `documentation/Dataset_Manifest.md`
- Official Hugging Face dataset `snap-stanford/stark`, revision `88269e23e90587f99476c5dd74e235a0877e69be`; upstream code revision `b246b9490b1dc216892ce78303140014506932c1`. Dataset-card licence CC-BY-4.0 (recorded), code licence MIT.
- Staged: 9 downloaded files, 486,879,729 bytes; 6 extracted members; 2,620,778,656 bytes total; every file SHA-256-recorded; raw data is immutable.

| Entity type | Count |
|---|---:|
| Paper | 700,244 |
| Author | 1,104,554 |
| Institution | 8,701 |
| Field of study | 59,469 |
| **Total** | **1,872,968** |

Global IDs are contiguous 0–1,872,967 (authors 0–1,104,553; institutions 1,104,554–1,113,254; fields 1,113,255–1,172,723; papers 1,172,724–1,872,967).

Official directed edges `[REPORTED]` (Phase 2 report): `WRITES` 6,768,883; `AFFILIATED_WITH` 1,029,162; `CITES` 4,878,384; `HAS_TOPIC` 7,243,269; **total 19,919,698**. After adding one *derived inverse traversal entry* per edge, the traversal store holds 39,839,396 rows. **Never describe 39.8 M as the number of source edges.**

Source data quirks preserved: 22,049 papers have missing Date/Year/Citation/Rank (kept NULL); multiple unreconciled venue fields (resolved by an explicit precedence in Phase 3); some entities have no name (shown by ID, never invented).

QA in the source: 13,323 synthetic queries (train 7,993 / validation 2,665 / test 2,665) and 84 human-written queries. Human queries 30, 50, 72 reference author nodes or mixed answer types and are incompatible with a paper-set evaluation (kept in preservation records, excluded whole from the primary human test set, never "repaired").

### 5.2 MMG-STaRK-MAG v1 `[VERIFIED]` `documentation/phase3/Representation_Contract.md`
| Artifact | Content |
|---|---|
| `canonical/canonical_entities.parquet`, `alias_registry.parquet` | identity registry; exact NFKC/casefold/whitespace-normalised aliases (1,714,702 aliases, 105,792 ambiguous normalised strings `[REPORTED]`); no fuzzy resolver |
| `text/text_documents.parquet` + `text/faiss/*` | one document per paper; exact `IndexFlatIP`, 700,244 × 384 float32 unit vectors; `all-MiniLM-L6-v2` (revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`), frozen weights exported to ONNX (CUDA float32, TF32 off), mean pooling + L2 normalisation, **256-token input limit** (full abstract still stored) |
| `graph/nodes.parquet`, `edges.parquet`, `adjacency/*.npy` | memory-mapped CSR (`indptr uint64[N+1]`, `neighbors uint32[2E]`, `edge_ids`, `relation_ids`, `derived_inverse`); no full-graph NetworkX object is ever built |
| `structured/stark_mag.duckdb` | `papers_structured` (paper_id, publication_date, publication_year, citation_count, rank, document_type, venue_namespace/id/name/type) + `papers_structured_source` (raw audit columns) |

Relation codes: 0 `author___affiliated_with___institution`, 1 `paper___cites___paper`, 2 `paper___has_topic___field_of_study`, 3 `author___writes___paper`. Inverse rows swap endpoints, keep the official relation name, and carry `derived_inverse = true`.

Structured normalisation: source `None`, `-1`, empty string and NaN → NULL; zero stays zero; year is never derived from date; citation count is never recomputed. Venue precedence: Journal > ConferenceSeries > ConferenceInstance > OriginalVenue > NULL (a missing component of the selected pair is **not** filled from a lower level).

Reported scale: 358 derived files, ~4.117 GB `[REPORTED]`. Embedding backend parity versus CPU PyTorch: max absolute difference 1.9e-07, minimum cosine 0.99999994 `[VERIFIED]` Decision Log P3-09.

---

## 6. Benchmark

### 6.1 Composition `[VERIFIED]` `documentation/phase4/Benchmark_Protocol.md`, `data/MMG_STARK_MAG/benchmark/benchmark_stats.json`
| Split | Official synthetic | Official human | Generated | Total |
|---|---:|---:|---:|---:|
| train | 7,993 | — | 56 | 8,049 |
| validation | 2,665 | — | 56 | 2,721 |
| test | 2,665 | — | 55 | 2,720 |
| human_test | — | 81 | — | 81 |
| **Total** | | | **167** | **13,571** |

- Generated queries = **42 base constructions** (2 per modality class × 7 classes × 3 splits) × stress variants (normal, noisy, conflict, unanswerable) = 168, minus one omitted GS test noise case (no valid distractor available) = **167**. The variants of one base share a *family* and are correlated: **167 variants are not 167 independent questions.**
- Taxonomy: modality ∈ {T, G, S, TG, TS, GS, TGS}; reasoning ∈ {single-hop, multi-hop-2, multi-hop-3+}; stress ∈ {normal, noisy, conflict, unanswerable}.
- Official records carry **unverified** modality/hop labels (13,404 records) and must not be used in verified modality/hop strata.
- Answer-set sizes across the benchmark: 0 (42), 1 (6,534), 2–5 (5,252), 6–20 (1,698), 21–100 (24), 101+ (21).

### 6.2 How generated queries are built
1. Compute candidate sets and exact intersections **before** any wording; the LLM may phrase a question but never defines gold.
2. Text predicates are explicit case-insensitive abstract claims (e.g. "the abstract explicitly includes *'in agreement with experimental results'*"); Graph predicates are author→paper, institution→author→paper, or institution→author→paper→cited-paper paths; Structured predicates are parameterised year/citation, rank/venue-namespace or date/citation conditions; combined queries are exact set intersections.
3. **Source necessity:** for each answerable multi-source item, dropping any one required modality must enlarge the answer set (a strict superset), with counterexample IDs persisted.
4. No answer ID or title appears in the wording.
5. Splits are *structurally* different on purpose (single-claim/author/year-citation in train; OR-claim/institution/rank-namespace in validation; AND-claim/three-hop-citation/date-citation in test), which prevents template leakage but introduces a known distribution shift and associates graph depth with split. It is not an IID benchmark.

### 6.3 Stress overlays (never mutate canonical data)
- **Unanswerable:** a valid question plus a verified disjoint condition, so the answer set is provably empty (42 empty-answer proofs).
- **Noisy:** hard distractors injected as evaluation-time overlay evidence (nearest-neighbour text distractors, near-miss graph detours, partially matching structured rows).
- **Conflict:** one fact is altered *in an evaluation overlay only*, with original fact, altered payload and expected handling stored; canonical evidence stays authoritative.

### 6.4 Human review gate (not satisfied)
3,390 review items are packaged (validation 589, test 2,720, human_test 81) in `data/MMG_STARK_MAG/benchmark/human_review/review.html`; **zero approvals exist**. A paper-quality *final test* requires all 2,801 test+human_test decisions plus leakage adjudication. Therefore every "verified" label in this project means *programmatically verified*, not human-verified. The paper must say so.

### 6.5 Known benchmark limitations (state them in the paper)
- Only 42 independent base constructions; stress variants are correlated.
- Some generated wording is mechanical.
- Some generated Text queries are exact-phrase predicates, while the Text baseline B1 is dense/semantic: a mismatch to report, not to fix (B1 gets 0 on these; §9.3).
- The paper corpus is shared across splits (transductive retrieval); overlapping answer papers alone are not leakage.
- Leakage scans (exact-normalised and bounded shingle/Jaccard/sequence) cannot certify absence of all paraphrases.

---

## 7. Evaluation and experiment infrastructure (Phase 5) `[REPORTED]`

### 7.1 Metrics
- **Answer:** set accuracy, exact match, precision, recall, F1, answerability correctness (answers iff gold non-empty). For an empty prediction against empty gold, precision = recall = 1.
- **Retrieval:** Recall@K, Precision@K (denominator is K), MRR, nDCG@K (binary), gold coverage (share of gold papers present anywhere). K ∈ {1, 5, 10}. Empty-gold (unanswerable) retrieval metrics are NULL, not zero.
- **Context:** characters, measured tokens (only with an identified tokenizer), reduction vs. a named baseline, evidence retained, exact-ID redundancy.
- **System:** retrieval/method/generation/total latency, retrieval-call and LLM-call counts, provider-measured tokens; cost only if an explicit price source exists (none configured → cost NULL).
- **Provider waiting is never counted as method latency**; it is recorded separately as `provider_wait_ms`.

### 7.2 Runner properties
Deterministic experiment identity (hash of configuration, code, packages, benchmark and representation hashes, selection, system fingerprint); atomic per-query commits under an exclusive lock; safe resume; refusal of incompatible resumes; error records preserved (failed answers stay NULL); final-test execution gated by a hash-bound human-release artifact; systems receive only `question, query_id, seed` and sanitised stress overlays (never gold, labels or annotations); optional immutable evidence cache keyed by source implementation fingerprints.

### 7.3 Statistics frozen for RQ3 `[VERIFIED]` `research/agentic/analysis.py`
- Paired per-query deltas between methods; **family-clustered** resampling (variants of one base are not independent).
- 95 % CI by family-clustered bootstrap: 10,000 resamples, seed 42.
- Exact **sign-flip permutation test** over families (allowed when 2 ≤ families ≤ 20; for the 14-family primary cohort that is 2^14 = 16,384 sign patterns).
- **Holm** correction across comparisons; a paired standardised effect over family means.
- **Pareto analysis** (a method is non-dominated unless another is ≥ on all axes and > on one); an unmeasured axis makes a pair incomparable. *Note:* this "incomparable on NULL" behaviour is an **uncommitted** edit in the working tree (§19.3) and must be reviewed before the primary run.
- Multi-label **failure taxonomy** separating controller failures from retriever weakness (e.g. `wrong_initial_routing`, `required_source_never_selected`, `premature_stop`, `excessive_retrieval`, `retriever_failure_despite_correct_routing`, `evaluator_misclassification`, `validator_false_accept`, `structured_intent_failure`, `loop_or_repeated_action`, `insufficient_evidence`, `final_generator_or_parsing_failure`).

---

## 8. The shared generator and provider constraints

### 8.1 Generator (frozen for all comparable experiments) `[VERIFIED]` `documentation/Phase_Reports/Phase_06_*.md`
`openai/gpt-oss-120b` via Groq; temperature 0; reasoning effort low; `max_completion_tokens` 1,024; JSON-object output; per-query deterministic seed (global 42); one common grounding prompt; strict parser rejecting hallucinated IDs, booleans, strings-as-IDs and malformed objects. The embedding model is `all-MiniLM-L6-v2` throughout. Context safety cap: 24,000 characters total (8,000 per source in the fixed stack).

### 8.2 Provider limits (Groq free tier, organisation console) `[REPORTED]` handoff §19.2, `[VERIFIED]` diagnostics
RPM 30, RPD 1,000, **TPM 8,000**, **TPD 200,000** for `openai/gpt-oss-120b`. The user cannot pay for an upgrade. Consequences for the experimental design: every large experiment is multi-day and must be resumable; individual requests must fit the 8,000-token-per-minute bucket; provider failures are recorded, never silently retried.

### 8.3 Measured provider accounting `[VERIFIED]` `documentation/rq1_repair/PROVIDER_AND_CM01_DIAGNOSTIC_REPORT.md`, `GROQ_ADMISSION_SEMANTICS_DECISION.md`
- Provider `prompt_tokens` − local `o200k_harmony` content tokens = **102 in 12 of 12** research-shaped requests (constant; 74 without `response_format`).
- Prompt caching: **not confirmed** (`CACHE_NOT_CONFIRMED`); not used for admission.
- Admission probe (one synthetic call, n = 1, bucket full): a request whose prompt + `max_completion_tokens` (7,000) exceeded 8,000 was admitted (HTTP 200) ⇒ `MAX_COMPLETION_CAP_CHARGED_AT_ADMISSION = NO`. Output tokens are still debited afterwards (an unexplained extra debit of up to ~+427 tokens observed).
- Revised operational admission rule (used by the Phase 9 client): `local content tokens + 128 ≤ 8,000`; the 1,024 cap is still sent unchanged. 128 = 102 measured overhead + 26 stated allowance.
- This rule is **operational, not scientific**: it changes no prompt, context, cap, model or cohort. The earlier rule (`content + 256 + 1,024 ≤ 8,000`) would have blocked 8 required RQ1 CM-01 requests (two base families × four stress variants, all Graph-only); under the revised rule all 160 statically constructable RQ1 requests fit (max 7,405).
- Daily-token arithmetic: the full repaired RQ1 run is ≈0.57–0.60 M provider tokens ⇒ about 3 days at 200 k TPD.

---

## 9. Baselines B1–B4 (Phase 6) `[VERIFIED]` `documentation/phase6/Baseline_Protocol.md`, `Phase_06_Research_Baselines.md`

| ID | Name | Behaviour (frozen) |
|---|---|---|
| **B1** | Traditional Text RAG | Embed query with the pinned MiniLM ONNX encoder (CPU fp32); exact FAISS inner product over 700,244 papers; fixed Top-5; evidence = paper ID/title/abstract; no reranking, no query rewriting. |
| **B2** | Basic GraphRAG | Resolve entities from graph labels only (bounded lexical scan keeping 64 candidate labels, exact source-name mentions prioritised, then MiniLM label similarity, then node ID); **3 seeds**; breadth-first over the memory-mapped CSR to **depth 2** with caps 2,000 nodes / 20,000 scanned edges / 128 edges per node; candidate papers ordered by path length, seed rank, global ID; evidence = titles, names and explicit paths, never abstracts; no seeds ⇒ no candidates (never falls back to the Text index). |
| **B3** | Structured retrieval | Deterministic supported-language parser → closed typed AND-predicate plan → parameterised **read-only** DuckDB (write attempt verified rejected); fields: year/date, citations, rank, venue namespace/id/name, document type; unsupported intents are returned as explicit "unsupported", never as arbitrary SQL, and there is no LLM SQL parser. |
| **B4** | Fixed multi-source | Always runs B1, B2, B3 independently (even after one fails); concatenates sections in Text → Graph → Structured order; each section gets a fixed one-third (8,000 chars) of the 24,000-character cap; no routing, intersection, entity alignment or advanced pruning. Combined ranking = first-occurrence source order, so Recall@5 is usually Text-first while gold coverage measures the whole union. |

Common settings: Top-K 5 per source, seed 42, DuckDB 512 MB / 2 threads.

### 9.1 Phase 6 closeout run `[VERIFIED]` `documentation/phase6_closeout/Addendum.md`
56 programmatically verified generated **validation** records × 4 baselines = 224 **retrieval-only** executions, zero LLM calls, zero errors, no test/human-test, no tuning. Cohort: 8 queries per modality class (T, G, S, TG, TS, GS, TGS); 24 single-hop + 32 multi-hop-2; 14 per stress condition. The 14 unanswerable queries have NULL retrieval metrics (42 available / 14 NULL).

### 9.2 Overall retrieval results (means over the 42 available queries)
| Baseline | Recall@5 | Precision@5 | MRR | nDCG@5 | Gold coverage |
|---|---:|---:|---:|---:|---:|
| B1 | 0.000000 | 0.000000 | 0.007937 | 0.000000 | 0.000443 |
| B2 | 0.006838 | 0.171429 | 0.166667 | 0.164342 | 0.006838 |
| B3 | 0.142857 | 0.042857 | 0.166667 | 0.142857 | 0.191536 |
| B4 | 0.000000 | 0.000000 | 0.059803 | 0.000000 | 0.198627 |

Notable strata: B3 on Structured-only queries achieves Recall@5 = MRR = gold coverage = 1.0; B2 on Graph-only queries has Precision@5 = MRR = 1.0 but Recall@5 ≈ 0.040 (the fixed Top-5 ceiling: e.g. 5 of 78 gold papers); B1 ≈ 0 everywhere.

### 9.3 How to interpret these numbers (include in the paper)
- B1's near-zero result is a **benchmark/baseline mismatch** (exact-phrase predicates vs. dense semantic retrieval), kept as a limitation; no exact-match shortcut was added to B1 after seeing it.
- B2/B3 are strong only on their own modality; B4 has the highest union coverage but its Top-5-by-position metrics are Text-first.
- These are small controlled retrieval-only results on 42 queries, not benchmark-wide accuracy.

Resources: wall time B1 62 s, B2 773 s, B3 6 s, B4 551 s; B4 peak 2.34 GB `[VERIFIED]` same file (not isolated latency benchmarks).

---

## 10. RQ1 — Context management

### 10.1 Candidate methods (frozen design, `Phase1D` §4)
| ID | Name | Reference paper | Core mechanism as frozen |
|---|---|---|---|
| CM-B0 | Raw control | — | Candidate order, atomic serialisation, 24,000-char global cap |
| CM-B1 | Fixed top-K control | — | First 5 candidate papers (depth ≤ 2) + parent paths, deterministic DFS serialisation |
| **CM-01** | KG²RAG-inspired | *Knowledge Graph-Guided Retrieval Augmented Generation* (arXiv 2502.06864) | semantic seeds (k=10) → 1-hop expansion → connected components → maximum spanning tree → deterministic DFS → cross-encoder ranking → dedup → budget. Reranker `BAAI/bge-reranker-large` rev `55611d7bca2a7133960a6d3b71e083071bbfc312`, CPU fp32, 2 threads, batch 1, 512-token pairs |
| **CM-02** | G-Retriever-inspired PCST | *G-Retriever* (arXiv 2402.07630) | top k_node=3 nodes and k_edge=5 edges by query similarity; rank prizes k..1; edge cost C_e=0.5; official `pcst_fast` 1.0.10 (compiled locally); connected-subgraph serialisation. No GNN/soft prompt |
| **CM-03** | QAFD-RAG-inspired | *Query-Aware Flow Diffusion for Graph-Based RAG with Retrieval Guarantees* | cached deterministic keyword extraction → N_seed=20 → query-aware edge weights → training-free flow diffusion (alpha 10, sink capacity 1, support threshold 0.01, ε 0.05, N_max 1,000,000) |

Scope rule: CM-01/02/03 change **only Graph evidence**. Text-only and Structured-only evidence is not modified; in mixed queries Text/SQL evidence passes through a fixed baseline policy.

### 10.2 Historical Phase 7 experiment (preliminary, non-canonical for final inference) `[VERIFIED]` `documentation/Phase_Reports/Phase_07_RQ1_Context_Management.md`
- Design: shared immutable bounded Graph candidate pool per query (BFS depth 2 from B2's recorded seeds; ≤256 base nodes, ≤1,024 traversal rows, 128 per node; up to 5 noise paths added, hard caps 320 nodes / 1,536 edges); **no generation** (answer metrics NULL); 161 tests passed at that point.
- Cohort: 16 verified generated validation records (4 each G, TG, GS, TGS; 8 normal + 8 noisy; all multi-hop-2; paired base/noisy ⇒ 8 independent instances). No real multi-hop-3+ stratum.
- Mean gold-paper coverage of the common pool before any context control: 0.736595.

| Method | Gold coverage | Recall@5 | MRR | nDCG@5 | Mean chars | Reduction vs CM-B0 | Context ms | Fallbacks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CM-B0 | 0.546374 | 0.136966 | 0.328984 | 0.343291 | 23,962.0 | 0.00 % | 65.64 | 0/16 |
| CM-B1 | 0.136966 | 0.136966 | 0.343750 | 0.351780 | 1,782.1 | 92.56 % | 62.10 | 0/16 |
| CM-01 | 0.138821 | 0.134013 | 0.312500 | 0.276748 | 21,303.9 | 11.10 % | 5,884.26 | 0/16 |
| CM-02 | 0.000391 | 0.000391 | 0.125000 | 0.042395 | 1,504.8 | 93.72 % | 64.85 | 0/16 |
| CM-03 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 6,442.7 | 73.09 % | 108.97 | 12/16 |

Diagnostics: PCST produced a valid structure on 16/16 inputs; diffusion converged on 4/16 and fell back on 12/16 with reason `component_mass_exceeds_sink_capacity` (injected mass 10/seed vs sink capacity 1 on small components). Descriptive Pareto (coverage vs. size): CM-B0, CM-B1, CM-01, CM-02 non-dominated; CM-03 dominated. **No winner was selected.**
CM-01's context latency of 5.9 s includes a one-time lazy load of the 2.26 GB reranker; a later profile shows ≈4.0–4.5 s per query with a warm model, dominated by the BGE forward pass (~2.2 s) and MiniLM embedding of provenance units (~1.5 s) `[VERIFIED]` diagnostic report §16.

### 10.3 Why Phase 7 is not canonical `[VERIFIED]` handoff §14.3, `compliance_repair/matrix.json`
1. It evaluated **Graph context only** even for mixed-modality queries, violating the pass-through rule.
2. A forensic compliance audit (93 requirements; see §12.1) found fidelity deviations in CM-01 (provenance/tree formulation), CM-02 (e.g. query-to-edge-text similarity was replaced by mean endpoint similarity; five distinct edge-score *levels* instead of five edges; tie-level sharing and 0.99 decay instead of exact rank prizes k..1) and CM-03 (fallback/convergence semantics).
Phase 7 remains preserved as a **Graph-context diagnostic sub-experiment**.

### 10.4 The CM-01 graph-native adaptation (user-approved, frozen before any repaired result) `[VERIFIED]` handoff §17
STaRK has no source-text-chunk ↔ graph-triple extraction provenance, which the literal CM-01 assumes. Inventing it would change the science and leak Text into Graph. The approved adaptation defines a **Graph Provenance Unit** = one authoritative Graph relation, deterministically serialised from labels/IDs only:
- `WRITES`: "Author <a> writes Paper <p>."
- `AFFILIATED_WITH`: "Author <a> is affiliated with Institution <i>."
- `CITES`: "Paper <A> cites Paper <B>."
- `HAS_TOPIC`: "Paper <p> has topic <f>."
Allowed: IDs, types, Graph labels (paper title), relation, edge provenance. Forbidden: abstract, year/date, venue, citations, rank, SQL values. Derived inverse rows map to the same canonical official edge (dedupe on canonical identity). Semantic seeds = top-10 cosine over unit serialisations **inside the shared candidate graph only** (CM-01 must not become a global edge retriever); edge weight = cosine(query, unit serialisation). Fallbacks: `graph_semantic_units` (units but no usable structure) or empty context `no_graph_relation_evidence` — **never** a Text fallback.

### 10.5 Canonical repair state `[VERIFIED]` `documentation/rq1_repair/*`
- Repaired CM-01/02/03, a common adapter and a durable dispatcher are implemented in `research/repair/` and checkpointed (`9e112a9`, 84 files). Historical implementations untouched.
- Planned cohort: **32** verified generated validation inputs (G, TG, GS, TGS = 8 each; each stress condition = 8). Planned workload: 32 keyword calls + 160 final-answer calls; ≈1.15 M conservatively estimated input tokens.
- Offline audit: 64 of 128 required real-input checks done (CM-B0 and CM-B1 for all 32); CM-01, CM-02, CM-03 outstanding. The runner refuses dispatch until all 128 pass.
- **Zero repaired research requests have been sent.** The run is paused by the user's schedule change to Phase 9 (demo first).
- An operational revision 2 (admission rule, untimed model load) exists only on `wip/rq1-operational-revision-2`; its 32 × 5 original-vs-new equivalence run did not finish (`CM01_SCIENTIFIC_OUTPUT_EQUIVALENCE = NOT_RUN`).
- A timing-boundary inconsistency is documented (CM-01 recomputes query-specific unit scores inside its timer; CM-02/CM-03 read staged offline inputs) and favours CM-02/03 in latency comparisons; not changed.
- `RQ1_SCIENTIFIC_STATUS = INCOMPLETE`.

---

## 11. RQ2 — Cross-modal fusion

### 11.1 Candidate methods (frozen design, `Phase1D` §5)
| ID | Name | Reference | Frozen behaviour |
|---|---|---|---|
| CF-B0 | Raw concatenation control | — | Source-order concatenation, atomic evidence, 24,000-char cap |
| CF-B1 | Source-separated control | — | Labelled Text/Graph/Structured sections with fixed shares of the budget |
| **CF-01** | KAG-inspired early fusion | *KAG: Boosting LLMs in Professional Domains via Knowledge Augmented Generation* (arXiv 2409.13731) | Attach canonical entity IDs (order: explicit ID → exact normalised alias → project resolver; no LLM invention); group evidence per entity; unresolved evidence goes to an explicit UNALIGNED group; groups ordered by max member relevance, then source coverage, then entity ID; provenance preserved; no retrieval |
| **CF-02** | SAG-inspired mid-level fusion | *SAG: SQL-Retrieval Augmented Generation with Query-Time Dynamic Hyperedges* (arXiv 2606.15971) | structural candidates = Graph + Structured; semantic = Text; **exactly one** selector-LLM call over structural candidates returning JSON IDs (≤5, invalid IDs dropped); Text fills to K_out=10 in retriever order; selector failure after one repair ⇒ relevance-score structural fallback (flagged) |
| **CF-03** | MegaRAG-inspired late fusion | *MegaRAG: Multimodal Knowledge Graph-Based RAG* (arXiv 2512.20626) | per non-empty source, one call returning `{candidate_answer, supporting_evidence_ids, confidence}` (≤220 tokens); one final fusion call over these grounded objects; a source failure becomes `ERROR_NO_EVIDENCE` for that source only; final failure retried once, then error |

Critical invariant: every fusion method receives the **same cached evidence bundle**; none may retrieve.

### 11.2 Historical Phase 8 experiment (preliminary, non-canonical) `[VERIFIED]` `Phase_08_RQ2_Cross_Modal_Fusion.md`, `phase8_generation_v2/Phase_08_V2_Review.md`
- Cohort: **24 frozen multimodal validation bundles** (6 each TG, TS, GS, TGS; 6 single-hop + 18 multi-hop-2; 8 normal / 8 noisy / 8 conflict), inputs taken from the approved B4 closeout; 5 methods × 24 = 120 context-only records, zero errors; 185 tests at that point.
- Historical CF-02 used **deterministic query-token overlap**, not the frozen LLM selector; historical CF-03 used a different intermediate-answer contract. Both are therefore non-canonical (preserved as "historical lexical ablation" and "historical late-fusion variant").

| Method | Mean context chars | Fusion ms | Gold coverage | Gold coverage excl. overlays | Mean source coverage |
|---|---:|---:|---:|---:|---:|
| CF-B0 | 15,818.7 | 1.016 | 0.086855 | 0.002000 | 0.960069 |
| CF-B1 | 12,672.0 | 4.061 | 0.086855 | 0.002000 | 0.946701 |
| CF-01 | 16,093.8 | 4.189 | 0.086855 | 0.002000 | 0.957292 |
| CF-02 (historical lexical) | 11,895.1 | 6.335 | 0.002000 | 0.002000 | 0.713542 |
| CF-03 | NULL (final context not built offline); prepared inputs 12,672.0 | 4.600 (preparation only) | NULL | NULL | 0.946701 |

Observations to report: CF-01 resolved all 372 evidence assignments by exact IDs but found only **one** cross-source entity group in 24 inputs (alignment barely exercised); historical CF-02 selected 5 Graph + 5 Text for every query and **no Structured evidence survived**; the headline coverage gain of CF-B0/B1/CF-01 over CF-02 in the conflict stratum is dominated by tagged overlay IDs and is **not** correct reasoning.

### 11.3 Generation samples (bounded diagnostics, not benchmark evidence)
1. **First attempt (2026-10-10):** two-query plan, at most 16 requests; 11 made → 2 valid responses, 9 `RateLimitError`, no retries (failure preserved). Known usage 6,970 input / 154 output tokens.
2. **Provider diagnostic:** model list HTTP 200; tiny completion HTTP 200 (72 in / 1 out); observed token limit 8,000, request limit 1,000.
3. **Paced v2 (executed 2026-10-10):** 16/16 requests, 10/10 final answers, zero provider errors; 47,277 input / 1,238 output tokens; request starts ≥90 s apart. **All five methods returned empty answer sets** on the chosen normal and conflict pair, so all answer metrics are 0. The frozen evidence for gold `{1258814}` lacked the canonical support, so this is **not** evidence that fusion is useless. CF-03: 8 calls and 11,406 tokens across the pair vs. CF-B1: 2 calls and 7,401 tokens at tied zero quality.

### 11.4 Why Phase 8 is not canonical, and the planned repair `[VERIFIED]`
- CF-02 must be the one-call LLM selector; CF-03 must use the grounded-intermediate contract (a source may return a *partial* constraint; it need not solve the whole conjunction).
- Upstream evidence is frequently insufficient. The repaired RQ2 therefore requires **two separate experiments that must never be merged numerically**:
  1. *Primary frozen-bundle study:* the same 24 bundles, each pre-classified FULLY / PARTIALLY / UNSUPPORTABLE from the query and evidence (not from model outcomes); report all 24 and the strata.
  2. *Fusion-isolation study:* validation-only, ≥12 evidence-complete queries (ideally 3 each of TG/TS/GS/TGS), deterministic selection frozen before any LLM call, authoritative evidence only (no synthetic facts, no visible gold flags).
- Status: **not started** (depends on RQ1 repair closing). `RQ2_SCIENTIFIC_STATUS = INCOMPLETE`.

### 11.5 The compliance audit that triggered the repair `[VERIFIED]` `documentation/compliance_repair/matrix.json`, `RQ1_RQ2_Compliance_Matrix.md`
93 requirements audited against the original Phase 1D text at pre-repair checkpoint `34c8503`: **32 PASS, 41 DEVIATION, 13 MISSING, 4 EQUIVALENT_IMPLEMENTATION, 3 UNVERIFIED.** This audit is itself a reportable methodological contribution (a forensic requirement-by-requirement check of a literature-adaptation study). It is a source/config/trace audit, not a claim that the repair already complies.

---

## 12. RQ3 — Agentic retrieval (Phase 9)

### 12.1 Candidate policies (frozen design, `Phase1D` §6 + Addendum rev 2)
| ID | Name | Reference | Decision studied |
|---|---|---|---|
| AR-B0 | Always retrieve everything | — | none: Text → Graph → Structured every time |
| AR-B1 | Rule router | — | deterministic keyword cues, no LLM/learning |
| **AR-01** | Adaptive-RAG-inspired | *Adaptive-RAG* (arXiv 2403.14403) | how much retrieval (A none / B single / C multi-step ≤3) |
| **AR-02** | CRAG-inspired | *Corrective RAG* (arXiv 2401.15884) | was retrieval good enough? |
| **AR-03** | AGENT-G-inspired | *AGENT-G: An Agentic Framework for Graph RAG* (OpenReview g2C947jjjQ) | which tool, query, retry, stop |

Fixed downstream stack for **all** policies: identical tools wrapping the unchanged B1/B2/B3 functions → fixed per-source budget of **8,000 characters** (a documented interpretation: 24,000 ÷ 3, reproducing B4 for the three-source case and making a source's text independent of the policy) → source-separated sections in Text → Graph → Structured order for the sources actually queried → shared final generator (frozen prompt, 1,024 cap, frozen parser). No RQ1 pruning and no RQ2 fusion.

### 12.2 Shared deterministic rule router (AR-B1; also the "base source router" inside AR-01/02/03) `[VERIFIED]` Addendum §1, `research/agentic/rule_router.py`
Normalise (NFKC, lowercase, collapse whitespace). Match cues:
- **Text:** abstract, title, text, content, phrase, wording, mention(s/ed), contain(s/ing).
- **Graph:** author(s/ed), written by, writes, affiliat*, institution, university, cites, cited by, references, referenced by, topic, field of study.
- **Structured:** year, publication year, date, rank, paper rank, citation count, numeric "N citations" comparisons, journal, conference, venue, document type, doctype, before, after, between, at least, at most, more than, less than, greater than, fewer than, `>=`, `<=`, `>`, `<`.
Output = matched sources in fixed order Text → Graph → Structured; if none match, `Text` only. AR-B1 queries every routed source once in that order, then stops. The cue table is frozen and must not be tuned. Caveat for the paper: generated queries are template-based and contain these very cue words, which flatters the router.

### 12.3 Policy behaviour (as implemented) `[VERIFIED]` `PHASE9_METHOD_IMPLEMENTATION_REPORT.md`, Addendum
- **AR-01:** `t5-base` (`google-t5/t5-base`, revision `a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1`) predicts A/B/C from the raw question. A: no retrieval (generator sees the question only). B: first router source, one call. C: ≤3 distinct sources; after each retrieval except the last, a controller LLM returns `{sufficient, next_subquery, reason}` (gpt-oss-120b, T=0, low effort, cap 128); `sufficient` stops; otherwise the sub-query is routed and the first *unqueried* source is used. **If the controller fails after one schema repair, retrieval stops and the answer is generated from the evidence gathered so far** (this was a conflict between an early addendum draft and Phase 1D; Phase 1D won). Invalid classifier output → route B.
  - Training: AdamW, lr 3e-5, weight decay 0.01, seed 42, max 10 epochs, checkpoint with minimum dev loss, patience 2, source length 256, target length 2, no label smoothing/balancing.
  - Labels: retrieval-only oracle on train/dev only. A succeeds only when gold is empty; B = router's first source succeeds iff `gold_paper_coverage == 1.0`; C = up to 3 sources with the raw query succeeds iff accumulated coverage is 1.0; label = cheapest success, else C.
- **AR-02:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`, pair max 512) scores `(query, rendered evidence)`; Platt calibration (lbfgs, C=1.0, balanced, max_iter 1000, seed 42) fit on the dev partition only; state = GOOD if `max(p) ≥ UPPER`, BAD if all `p ≤ LOWER` (and empty evidence), else AMBIGUOUS; threshold grid LOWER ∈ {0.20…0.40}, UPPER ∈ {0.60…0.80}, LOWER < UPPER, macro-F1 objective with a fixed tie-break chain (lower error, wider margin, lower LOWER, lower UPPER). GOOD stops; AMBIGUOUS adds the highest-priority unqueried source; BAD adds all remaining in T → G → S order; up to **two correction rounds** each followed by one re-evaluation (≤3 evaluations); evaluator failure ⇒ AMBIGUOUS; no web search, no strip refinement.
- **AR-03:** Agent emits a strict JSON `AgentAction` (`iteration, source ∈ {text, graph, structured, stop}, retrieval_query, domain, entities, relations, structured_intent, reason_code, stop_reason`), **one tool per iteration**, cumulative evidence memory; a generator produces a candidate each iteration; a Validator (JSON `{accept, error_type, unsupported_claims}`; never sees gold) accepts or rejects; on rejection a Commentor (sees only query, last action, validator result) gives feedback; max **T=4** iterations; loop guard (same normalised action twice without new evidence ⇒ forced feedback; again ⇒ `INSUFFICIENT_EVIDENCE`); one deterministic schema-repair call per malformed output (successful repair consumes no iteration; failed repair ⇒ iteration counted and the router supplies the source). Caps: agent 256, validator 256, commentor 128, repair 128 tokens. After a rejected iteration 4 the result is `INSUFFICIENT_EVIDENCE` (recorded as status, answered as the empty paper set).
- **Durable LLM client:** stage identity = SHA-256 of the full payload; identical payloads are reused byte-for-byte (every logical call still counted with its original usage/latency); paced single-in-flight; 429/failure persisted and raised as a `ProviderPause` that stops the run for later resume; local daily ledger stops at 195 k of the 200 k/day limit.

### 12.4 Data discipline for RQ3 `[VERIFIED]` `documentation/phase9/partition/ar01_partition.json`
- Eligible pool: official train (7,993) + generated train (56) = **8,049**. Partition rule: dev iff `int(sha256(query_id)[:16], 16) % 100 < 10`. Result **7,302 train / 747 dev** (partition SHA-256 `8e066422729570405049817a60fb2e75ed220b4ef800cec3ea6644d697ce843d`).
- Four of the 14 generated train families straddle train/dev (reported limitation).
- The 56-query primary cohort, official validation, test and human-test are **never** read for training, early stopping, calibration or thresholds.
- Pool retrieval uses the unchanged B1/B2/B3 functions: train queries only need the router's first source; dev queries need all three. Raw question only.

### 12.5 Evaluation design for RQ3 (frozen before any outcome) `[VERIFIED]` `PHASE9_SPEC_CONSISTENCY_AUDIT.md`
- **Primary cohort:** the 56 programmatically verified generated **validation** queries = 14 independent base families (7 modality classes × 2 families) × 4 stress variants. Statistics resample the 14 families.
- Oracle required-source set R from the verified modality label (T→{text}, G→{graph}, S→{structured}, TG→{text,graph}, …); used only in analysis, never by a policy.
- `covered_step` = the first retrieval call after which the called sources ⊇ R. **`stopping_accuracy` = 1 iff `covered_step` exists and total retrieval calls equal it.** `premature_stop`, `max_step_exhaustion` and `over_retrieval` are defined from it. Source precision/recall/F1/exact of called sources vs. R; unnecessary-retrieval rate = |S∖R| / |S| (0 when S is empty); required-source miss rate = |R∖S| / |R|.
- Six recorded interpretations (⚑1–⚑6) in the audit are open to human veto before the primary run: (1) 8,000 chars/source, (2) the C-label oracle uses the raw query (a proxy for controller-written sub-queries), (3) the hash-based partition lets 4 families straddle, (4) "validation split" operationalised as the dev partition from train, (5) "max correction rounds = 2" read as two corrections each followed by a re-evaluation, (6) engineering defaults for rare failure paths.

### 12.6 Current RQ3 status
- Implemented and unit-tested (offline fakes only): `tests/test_phase9_foundations.py`, `tests/test_phase9_policies.py`, `tests/test_phase9_analysis.py`.
- **Not done:** complete retrieval pool → AR-01 labels → T5 training → AR-02 calibration → frozen `execution_plan.json` (code and artifact hashes) → primary 56-query run for 5 policies → analysis. `run_phase9.py` refuses to run the primary mode without the frozen plan.
- Cost outlook `[REPORTED]`: free-tier quota (200 k tokens/day) makes the full primary run about 7 days (user's estimate recorded in project notes).

### 12.7 Lite demonstration study (NOT the scientific study) `[VERIFIED]` `.worktrees/demo/demo_assets/lab/rq3_lite.json`
Purpose: let the demo show all five policies. Definitions: one generated **train**-split question per modality class (7 questions: T, G, S, TG, TS, GS, TGS), real retrievers, real model; AR-01 is a lightly trained throw-away model (commit message: 1 epoch) and AR-02 uses a lite calibration (Platt coef 0.366, intercept 0.148; thresholds LOWER 0.40, UPPER 0.60; fit on 278 dev queries; 2,790 items) from a partial pool. AR-01 may have seen some of these questions during training. The lite pipeline writes only to `artifacts/phase9/lite/`.

| Policy | Answer F1 | Source F1 | Wasted retrieval | Stopping acc. | Retrieval calls | LLM calls | Tokens | Compute ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AR-B0 | 0.222 | 0.700 | 0.429 | 0.571 | 3.00 | 1.00 | 2,131 | 25,315 |
| AR-B1 | 0.222 | 1.000 | 0.000 | 1.000 | 1.71 | 1.00 | 1,386 | 764 |
| AR-01 | 0.222 | 0.843 | 0.238 | 0.429 | 2.43 | 2.71 | 3,475 | 10,401 |
| AR-02 | 0.222 | 0.843 | 0.238 | 0.571 | 2.43 | 1.00 | 1,732 | 5,698 |
| AR-03 | 0.222 | 0.876 | 0.000 | 0.429 | 1.43 | 5.29 | 5,765 | 6,085 |

Reading: answer quality is identical for all policies on 7 questions (the hybrid and phrase questions returned no supported paper for every policy), so differences are only in cost and source selection. AR-B0's compute time includes a 62-second cold start on its first query. **Do not present these as RQ3 results**: n = 7, one question per class, train split, flattered rule router (cue words in templates), lightly trained learners.

### 12.8 AR-01 lite training data (illustrates label imbalance, not a result)
Lite labels over the partial pool: train A 9 / B 1,089 / C 3,921; dev A 2 / B 106 / C 402; 2,520 pool records were missing at labelling time `[VERIFIED]` `artifacts/phase9/lite/labels.json`. Strong C-dominance (≈78 %) is expected to be re-examined once the complete pool exists; the scientific run must log class counts and imbalance (no resampling is allowed by the addendum).

---

## 13. RQ4 — Integration

Not started. The roadmap's Phase 10: choose one or more *justified* integration candidates from the RQ1–RQ3 Pareto results (no single winner assumed), create RQ4 configs, implement the integrated flow through the same interfaces, define conflict-resolution precedence, run validation first, freeze the test configuration only after review, compare against B1–B4 and strong single-component variants, and run ablations removing one component at a time (−agentic, −fusion, −context-management). Phase 11 (locked test campaign) additionally requires the complete 2,801-decision human review and a frozen code/config/benchmark. The integrated *prototype* in §14 is a demonstration of the architecture, **not** an RQ4 result.

---

## 14. The integrated prototype (demo application)

Location: branch `demo/professor-integrated-product-2026-10-12`, git worktree `.worktrees/demo`; entry `integrated_demo_app.py`; code `research/product/`; launcher `scripts/run_professor_demo.ps1`; port **8506**; config `configs/demo/professor_demo.yaml` `[VERIFIED]`. It is a presentation artifact; its settings never feed research experiments (`DEMO-ONLY`: 5,000 chars/source and a 512-token cap versus the research 8,000 chars/source and 1,024-token cap).

### 14.1 What it does
A question goes through a retrieval policy (default Auto = deterministic Rule Router AR-B1, because no RQ3 policy is approved) → Text / Graph / Structured retrieval → source-separated fusion → fixed-budget context → grounded LLM answer. **Run mode** is *Live* (real retrieval + Groq call, local interactive ledger capped at 40,000 tokens) or *Recorded example* (replays a real earlier run, badged RECORDED with its original timestamp, never shown as live). If Groq fails the app shows "Generation temporarily unavailable" together with evidence, graph and trace; it never fabricates an answer.

### 14.2 Interface map (9 tabs + sidebar)
Sidebar: Example library (11 curated questions, none from test/human-test), question box, **Where should it look?** (Auto / Text / Graph / Structured / All Sources), Run mode, Advanced strategy selector (AR-B1, AR-B0, AR-01, AR-02, AR-03; AR-01/02 appear only once their local assets exist), Run Query.
Tabs: **Answer** (plain-English summary, grounded answer box, KPI tiles, pipeline strip) · **Reasoning** (policy trace: router cue hits / classifier probabilities / evaluator states / agent-validator-commentor steps / retrieval steps) · **Graph View** (interactive subgraph built only from the evidence the Graph retriever returned; shapes P/A/I/F; edges WRITES, AFFILIATED_WITH, CITES, HAS_TOPIC) · **Evidence** (Text abstracts, Structured predicates + parameterised SQL + rows, exact fused context) · **Metrics & Charts** · **Compare Strategies** (same question through several policies) · **Research Lab** (RQ1/RQ2/RQ3 candidate descriptions, score cards, Pareto charts, failure table, RQ4 "combine" preview; every panel carries a banner stating it is preliminary/lite) · **Metric Guide** · **Architecture & Status**.

### 14.3 Recorded real runs `[VERIFIED]` (11 runs, recorded 2026-10-11)
| Example | Policy | Sources | Answered papers | LLM calls | Tokens in/out |
|---|---|---|---:|---:|---|
| graph_institution_mit | Rule Router | Graph | 5 | 1 | 1,178 / 111 |
| graph_all_four_types | Rule Router | Graph | 2 | 1 | 955 / 137 |
| graph_author_papers | Rule Router | Graph | 2 | 1 | 924 / 91 |
| text_cesium | Rule Router | Text | 4 | 1 | 1,321 / 78 |
| structured_citations | Rule Router | Structured | 1 | 1 | 352 / 84 |
| tg_university_topic | Rule Router | Text+Graph | 0 (declined) | 1 | 1,941 / 86 |
| ts_phrase_metadata | Rule Router | Text+Structured | 0 (declined) | 1 | 1,704 / 65 |
| gs_coauthor_field | Rule Router | Graph+Structured | 0 (declined) | 1 | 950 / 111 |
| tgs_all_three | Rule Router | Text+Graph+Structured | 0 (declined) | 1 | 2,400 / 93 |
| unanswerable_phrase | Rule Router | Text | 0 (declined) | 1 | 711 / 66 |
| agentic_ar03_example | Agent + Critic (AR-03) | Graph | 5 | 3 | 2,916 / 284 |

Observation worth a sentence in a case-study section: single-source questions are answered; the hybrid questions are honestly declined because no single paper is jointly supported by the retrieved evidence — consistent with the upstream-evidence-insufficiency finding of §11.

---

## 15. Operational findings worth reporting (engineering lessons)

1. **Forensic compliance auditing before final inference** caught 41 deviations that unit tests and an approved phase review had not (§11.5). The project's response was to preserve all historical runs and build a new, namespaced repair rather than edit history.
2. **Provider constraints are an experimental-design variable.** A free-tier 8,000 TPM / 200 k TPD limit forces durable, resumable, paced execution; the paper should describe the durable-stage design (payload-hash identity, byte-identical reuse, provider-pause semantics) and the measured accounting facts (§8.3) because they affect reproducibility.
3. **Operational vs. scientific changes** are strictly separated: a change that alters no prompt/context/cap/model/cohort may change the dispatcher; anything else needs explicit approval and a new versioned record.
4. **Latency honesty:** first-call model loads contaminated early CM-01 timings (71 s vs. ≈4 s steady state); provider waiting is reported separately.
5. **Fixed-K metrics vs. union coverage** diverge for B4; state which one a table reports.

---

## 16. Chronology (deterministic order; times IST) `[VERIFIED]` `git log`

| Date | Commit | Event |
|---|---|---|
| 2026-10-04 15:19 | `4592d10` (tag `baseline-mvp-v1`) | Phase 0: MVP frozen (12 PDFs; Traditional RAG + Basic GraphRAG) |
| 2026-10-04 15:38 | `ea88dcf` | Phase 1: research scaffold |
| 2026-10-04 19:58 | `f8fc9a2` | Phase 2: STaRK-MAG acquired/audited |
| 2026-10-06 23:26 | `3b34d9c` | Phase 3: MMG-STaRK-MAG v1 |
| 2026-10-07 00:34 | `262c4d1` | Phase 4: benchmark + review package |
| 2026-10-07 09:28 | `721c27b` | Phase 5: evaluation harness |
| 2026-10-08 15:28 | `a19bdd5` | Phase 6: baselines B1–B4 |
| 2026-10-08 16:39 | `cd450bb` | Phase 6.5 UIs + Phase 6 closeout (224 retrieval-only runs) |
| 2026-10-09 15:09 | `2600275` | Phase 7: RQ1 original experiment |
| 2026-10-10 | (within `18b32f0`) | Phase 8 offline study; first bounded generation (9/11 rate-limited); paced v2 (16/16) |
| 2026-10-11 09:04 | `18b32f0` | Phase 8 checkpoint |
| 2026-10-11 09:36 | `34c8503` | `PRE_RQ1_RQ2_COMPLIANCE_REPAIR` (93-requirement audit; zero repair calls) |
| 2026-10-11 12:24 | `9e112a9` | RQ1/RQ2 repair pre-generation checkpoint (blocked by Groq admission) |
| 2026-10-11 13:15 | `159a48f`, `81646d0` | Diagnostics preserved; WIP operational revision 2 (unvalidated) |
| 2026-10-11 | — | User decision: demo first, evaluation continues; RQ1/RQ2 repair paused |
| 2026-10-11 13:41 | `995dce9` | Phase 9: spec audit, five policies, durable LLM client, partition (no results) |
| 2026-10-11 14:12 | `3817c5d` | Demo: integrated professor-facing product |
| 2026-10-11 14:13–14:18 | `25350cd`, `0ca2c38` | Phase 9: analysis module, fixed downstream config, freeze script, implementation report |
| 2026-10-11 14:25 | — | Last graph-pool retrieval record written; pool workers then stopped |
| 2026-10-11 18:56–19:06 | `3670632`, `18268bf` | Demo: structured UI; readable Graph View layout |
| 2026-10-12 09:59 | `408df9b` | Demo: Research Lab tab |
| 2026-10-12 10:22 | `89fb76b` | Demo: lite RQ3 results for all five policies |

---

## 17. Governance, invariants, stop gates

### 17.1 Process rules
- Work proceeds phase by phase with a **mandatory stop and human review after each phase**; the next phase never starts automatically.
- Do not invent new completion criteria after a phase is approved; a repair exists only because concrete deviations from the frozen contract were found.
- Normal engineering questions are decided by safe deterministic defaults, documented and tested; anything that changes research meaning stops for the user.
- Hard blockers: unavailable authoritative data, research-meaning conflicts, destructive operations, meaningful paid spend, infeasible hardware, unavoidable secrets.

### 17.2 Preservation
Raw data, benchmark gold/questions, historical Phase 7/8 artifacts and the frozen MVP are immutable. Preservation audits re-hash them: 695 raw/representation/benchmark payloads; 54 MVP baseline files + 4 storage files; 2,874 tracked historical/code/config files with 0 differences at the repair checkpoint `[VERIFIED]` diagnostic report §5. A fresh checkout on Windows with `core.autocrlf=true` changes line endings and would trip hash-frozen code checks; use the working tree or `-c core.autocrlf=false`.

### 17.3 Fifteen scientific invariants
1. STaRK global node ID is the cross-view key. 2. Text isolation. 3. Graph isolation (paper label = title only). 4. Structured isolation. 5. Raw source immutable. 6. Benchmark immutable. 7. Baselines stay simple. 8. One variable at a time (RQ1 context, RQ2 fusion, RQ3 control). 9. No gold at inference. 10. No test/human-test tuning or use. 11. Evidence maps back to authoritative IDs. 12. NULL is not zero. 13. Provider waiting is not intrinsic latency. 14. Historical results stay preserved. 15. A method may change only to match the frozen contract or an explicitly approved dataset adaptation — never from observed performance.

### 17.4 Prohibited claims (reproduced from the project's own "must not" list)
Do not claim: SOTA, publication success or patentability; that all ~40 papers were deeply reviewed; that 39.8 M are source edges; any RQ winner; that official records have verified modality/hop labels; that provider waiting is method latency; that the demo's lite study is RQ3.

---

## 18. Limitations and threats to validity (comprehensive; use selectively in the paper)

**Data/benchmark**
1. Only 42 independent generated base constructions; 167 variants are correlated.
2. Generated queries are template-generated and mechanical in places; results do not establish natural-language generality.
3. Official records have unverified modality/hop labels; **no human review has been completed** (3,390 pending; 2,801 needed for final test).
4. Train/validation/test families differ deliberately (distribution shift), with graph depth associated with split.
5. Exact-phrase Text queries vs. dense retrieval (B1 mismatch).
6. The MiniLM embedding truncates input at 256 tokens while full abstracts are stored.
7. Leakage scans are bounded and cannot rule out all paraphrase leakage.

**Methods**
8. All nine methods are *adaptations*, not reproductions; training-based components of the originals (T5-Large, GNN/soft prompts, fine-tuned evaluators, KAG-Solver) are replaced or omitted.
9. CM-01 uses the graph-native provenance-unit adaptation because STaRK lacks chunk↔triple provenance.
10. CM-03's frozen defaults (mass 10 per seed, sink capacity 1) cause frequent fallback on small components; the original statistical guarantees are not claimed.
11. The rule router is flattered by cue words in template queries.
12. The AR-01 C-label oracle uses the raw query, a proxy for the inference-time controller; four families straddle the train/dev split.
13. Shared downstream stack uses 8,000 chars/source (interpretation ⚑1).

**Experiments/statistics**
14. RQ1/RQ2 have no canonical result; Phase 7/8 numbers are small, partly confounded (overlay IDs inflate coverage), and in Phase 8 upstream evidence often lacked the gold paper.
15. Fourteen independent families ⇒ wide intervals; exact tests have limited power. Say so.
16. API determinism: a fixed seed does not guarantee identical remote outputs.
17. Timing: first-call lazy loads, overlapping background work and the CM-01 timing-boundary inconsistency mean latencies are operational observations, not isolated benchmarks.
18. Single provider/model (Groq, gpt-oss-120b); admission-semantics finding is n = 1; prompt caching unconfirmed.

**Prototype**
19. The demo uses different budgets/caps from the research configuration and its recorded set is small and curated.

---

## 19. Reproducibility and repository state

### 19.1 Environment
Windows 11; use `.venv\Scripts\python.exe` (CPython 3.12.14). Plain `python` resolves to an unrelated MSYS2 interpreter. The repository is owned by a different Windows user, so git commands need `git -c safe.directory=<path>` (or `*`). Key pinned artifacts: MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; BGE reranker revision `55611d7bca2a7133960a6d3b71e083071bbfc312`; T5 revision `a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1`; cross-encoder revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`; PCST `pcst_fast` 1.0.10; Phase 1D spec SHA-256 prefix `55d89906…`; Phase 9 addendum rev 2 prefix `14b40e90…` (byte-identical to `documentation/specifications/phase9/revision_2/…`); partition SHA-256 `8e066422…`; benchmark manifest SHA-256 `e07f1314…`.

### 19.2 Branches and worktrees `[VERIFIED]`
| Branch | Where | Meaning |
|---|---|---|
| `master` | — | repair checkpoint `9e112a9` + diagnostics `159a48f` |
| `wip/rq1-operational-revision-2` | — | unvalidated operational revision 2 (`81646d0`) |
| `research/phase9-rq3` | main checkout `D:/codefiles/RAG_GraphRAG_Demo` | Phase 9 code/docs (HEAD `0ca2c38`) |
| `demo/professor-integrated-product-2026-10-12` | worktree `.worktrees/demo` | prototype app (HEAD `89fb76b`); **must not be merged into research branches** |

### 19.3 Uncommitted state to be aware of `[VERIFIED]` `git diff`
On `research/phase9-rq3` the working tree contains uncommitted edits to `research/agentic/analysis.py`, `research/agentic/ar01_model.py`, `scripts/phase9_build_labels.py`, `scripts/phase9_calibrate_ar02.py`, `scripts/phase9_train_ar01.py`:
- `--lite` modes and a `max_epochs` parameter, all demo-only (they write only under `artifacts/phase9/lite/`);
- **`analysis.py` Pareto change** (unmeasured axis ⇒ incomparable instead of ignored). This one touches scientific analysis code, was made after the Phase 9 implementation commit, and should be reviewed and frozen (or reverted) *before* the primary run, because the frozen plan hashes implementation files.
Also: a demo process (`scripts/demo_lite_rq3.py --methods AR-01`, started 10:18 on 2026-10-12) was running when this brief was captured.
Untracked: `CLAUDE_MASTER_HANDOFF_MULTIMODAL_GRAPHRAG.md`, `artifacts/phase9/`, `tmp/`, and this file.

### 19.4 Key commands (from the project's reports)
```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe scripts/run_baseline.py --config configs/baselines/B1-offline.json --offline --output <dir>
.\.venv\Scripts\python.exe scripts/prepare_phase7.py ; scripts/run_phase7.py ; scripts/report_phase7.py ; scripts/audit_phase7.py
.\.venv\Scripts\python.exe scripts/prepare_phase8.py ; scripts/run_phase8.py ; scripts/report_phase8.py ; scripts/audit_phase8.py
.\.venv\Scripts\python.exe scripts/phase9_prepare_partition.py
.\.venv\Scripts\python.exe scripts/phase9_retrieve_pool.py <text|graph|structured> <shard> <nshards> [reverse]
.\.venv\Scripts\python.exe scripts/phase9_build_labels.py ; phase9_train_ar01.py ; phase9_calibrate_ar02.py
.\.venv\Scripts\python.exe scripts/run_phase9.py --mode primary --methods AR-B0 AR-B1 AR-01 AR-02 AR-03     # needs frozen execution_plan.json
powershell -ExecutionPolicy Bypass -File scripts\run_professor_demo.ps1     # demo branch, port 8506
```
Do **not** invoke Groq-using commands without the project owner's approval; the free-tier quota is shared between research and demo.

### 19.5 Where each paper number comes from
| Paper element | Machine-readable source |
|---|---|
| Dataset counts | `documentation/Dataset_Manifest.md`, `data/MMG_STARK_MAG/manifest.json` |
| Benchmark counts/stats | `data/MMG_STARK_MAG/benchmark/benchmark_stats.json`, `benchmark_manifest.json` |
| Baseline results | `documentation/phase6_closeout/` (tables, `runs/B1–B4`) |
| Historical RQ1 | `documentation/phase7/` (`cohort_comparison.csv`, `per_query_comparison.csv`, `pareto.csv`, `representative_cases.json`) |
| Historical RQ2 | `documentation/phase8/` and `documentation/phase8_generation_v2/` (`method_comparison.csv`, `stage_outputs.json`) |
| Audit | `documentation/compliance_repair/matrix.json`, `RQ1_RQ2_Compliance_Matrix.md` |
| Provider facts | `documentation/rq1_repair/`, `documentation/groq_diagnostic/` |
| RQ3 spec/interpretations | `documentation/phase9/PHASE9_SPEC_CONSISTENCY_AUDIT.md`, `Phase9_Frozen_Settings_Addendum.md` |
| RQ3 results | `[PENDING]` future `documentation/phase9/runs/` |
| Prototype lab data | `.worktrees/demo/demo_assets/lab/*.json` (preliminary/lite only) |

---

## 20. How to write the paper from this material

### 20.1 What kind of paper is supportable *now*
**Type A (supportable today):** a testbed + protocol + audit paper — "A controlled testbed for multi-modal GraphRAG: heterogeneous representations of a scientific corpus, a verified-by-construction benchmark with stress overlays, a frozen one-variable-at-a-time protocol, a forensic compliance audit, and preliminary diagnostics." Results sections contain only baselines (§9) and clearly labelled preliminary observations (§10.2, §11.2–11.3), with the RQ3 study and RQ1/RQ2 repaired studies marked pending.
**Type B (not yet supportable):** a comparative-results paper ("method X is best") — requires the canonical RQ1/RQ2 runs, the RQ3 primary study, human review of at least the validation items used, and, for any generalisation claim, the locked final test (Phase 11). Do not write Type B text with invented numbers; write the skeleton with `[PENDING]` markers.

### 20.2 Suggested section skeleton (Type A, extendable to Type B)
1. **Introduction** — heterogeneous evidence (Text/Graph/Structured), three engineering questions, contributions as listed in §20.3.
2. **Related work** — the nine retained methods (titles/arXiv IDs in §10–§12) and the 12 MVP papers in `data/papers/` (P001–P012). Verify bibliographic details (authors, venues, years) from the PDFs; this brief intentionally does not supply them.
3. **Problem formulation and design** — §3, §4.1.
4. **MMG-STaRK-MAG v1** — §5, with isolation invariants.
5. **Benchmark** — §6, including the limitations in §6.5.
6. **Evaluation protocol and statistics** — §7 (metrics, family-clustered inference, Pareto, failure taxonomy, NULL semantics).
7. **Systems** — §8 (shared generator), §9 (baselines), §10.1/§11.1/§12.1–12.3 (methods as *adaptations*), §10.4 (CM-01 adaptation).
8. **Compliance audit and repair methodology** — §11.5, §10.3, §10.5 (frame as methodological contribution; be explicit that the historical numbers are retained but non-canonical).
9. **Results** — §9.2 (baselines), then *preliminary diagnostics* §10.2, §11.2–§11.3, with `[PENDING]` placeholders for canonical RQ1, RQ2 (primary + isolation) and RQ3 primary study; the §12.7 lite table only in a demonstration/system section, labelled as such.
10. **System demonstration** — §14.
11. **Limitations and threats to validity** — §18.
12. **Reproducibility statement** — §19, §17.2.
13. **Conclusion/future work** — pending studies, human review, RQ4, locked test.

### 20.3 Contribution statements that are currently defensible
- A reproducible construction of three isolated, identity-linked views of STaRK-MAG with documented isolation rules and exhaustive audits.
- A benchmark construction method with computed-before-wording gold, strict source-necessity checks and non-mutating stress overlays (with honest correlation/limit statements).
- A frozen one-variable-at-a-time protocol with explicit fallbacks, tuning policies and stop gates.
- A forensic compliance audit that found 41 deviations in earlier experiments and a preservation-first repair process.
- Measured facts about running such studies on a free-tier provider (§8.3).
- An open-architecture prototype demonstrating the pipeline with grounded, source-restricted answers.

### 20.4 Claims allowed vs. forbidden
| Allowed (with the stated hedge) | Forbidden |
|---|---|
| "Baseline B3 retrieved all gold papers on the 6 available Structured-only validation queries" (retrieval-only, small n) | "B3 is better than B2" / any general ranking |
| "In a 16-query Graph-context diagnostic, CM-B1 cut context by 92.6 % while retaining 0.137 gold coverage vs. 0.546 for the raw control" | "CM-B1 is the best context method" |
| "Under the frozen defaults CM-03 fell back on 12 of 16 inputs" | "CM-03 does not work" (defaults are paper-derived; not tuned) |
| "Five fusion methods returned empty answers on a two-query diagnostic where the frozen bundle lacked the gold paper" | "Fusion does not help" |
| "In a 7-question demonstration all five policies tied on answer F1; they differed in calls/tokens" | Any statement that a policy is better |
| "Forty-one of 93 audited requirements deviated from the specification" | "RQ1/RQ2 are repaired/validated" |
| "The system declines when no single paper is jointly supported" (demo) | "The system is accurate on hybrid questions" |

### 20.5 Writing rules (deterministic)
1. Every number must trace to a file in §19.5; cite the artifact in a footnote or appendix table.
2. State n, cohort, split and whether labels are programmatically or human verified next to every result.
3. Report uncertainty at the family level (14 families) once RQ3 runs; until then do not use words such as "significant".
4. Call unavailable measures "not measured", never zero.
5. Always separate retrieval/coverage metrics from answer-quality metrics; coverage is an upper bound, not accuracy.
6. When describing a method, give (a) reference mechanism, (b) project adaptation, (c) what was run (e.g. "historical lexical CF-02" vs. "canonical one-call CF-02").
7. Describe the demo's lite study only as a demonstration.
8. If asked to "write the results" before §12.6 items finish, produce placeholders and a table template with column definitions, not numbers.

---

## 21. Open items and things this brief could not resolve

1. **Bibliographic metadata** (authors, venues, years) of the nine retained methods and the other three MVP papers are not recorded in the repository text I read; take them from the PDFs in `data/papers/` and `documentation/specifications`.
2. **Whether the graph-pool retrieval workers will be restarted** and when the primary RQ3 study will run is a decision for the project owner; the free-tier quota implies a multi-day run.
3. **The six RQ3 interpretations (⚑1–⚑6)** are open to human veto before the primary run.
4. **Uncommitted `analysis.py` Pareto edit** must be decided (keep/revert) and then frozen.
5. **Handoff-only facts** (marked `[REPORTED]`): Phase 1/5 test counts, Phase 2 per-relation edge counts, 358-file/4.117 GB build size, alias counts, the ~40-paper literature inventory, Groq console limits. Re-verify before quoting to the digit.
6. **Human review** has not started; the final-test gate (2,801 decisions) and validation spot-checks remain.
7. **Repaired RQ1/RQ2** timing: RQ1 repair cannot resume until operational revision 2 is validated (equivalence run) and re-frozen; RQ2 repair follows RQ1.
8. The demo branch's Research Lab data is a *copy* of preliminary numbers, not a new measurement; it must be refreshed from canonical artifacts when those exist.
9. This brief itself is untracked; commit it deliberately if it should be part of the record.

---

## 22. Glossary

| Term | Meaning |
|---|---|
| STaRK-MAG | Official Microsoft-Academic-Graph-based semi-structured retrieval benchmark from Stanford SNAP |
| MMG-STaRK-MAG v1 | This project's derived dataset: three isolated views joined by global node ID |
| View / modality | Text, Graph or Structured representation (not image/audio/video) |
| T, G, S, TG, TS, GS, TGS | Modality classes of a query (which views the answer needs) |
| Family | A base construction and its stress variants (normal/noisy/conflict/unanswerable); the independent unit for statistics |
| Gold coverage | Fraction of gold papers present anywhere in the retrieved/retained evidence (an upper bound on answer recall) |
| Overlay | Evaluation-time modification (noise, conflict, unanswerable) applied to the input stream, never to canonical data |
| Programmatically verified | Label derived by exact computation in construction; not human-reviewed |
| CM-xx / CF-xx / AR-xx | Context-management / cross-modal-fusion / agentic-retrieval candidate methods (B0/B1 = controls) |
| Provenance unit | One authoritative graph relation serialised deterministically (CM-01 adaptation) |
| Admission rule | Local pre-dispatch check that a request fits the provider's token-per-minute bucket |
| Provider pause | Clean stop on quota/429 so the run can resume later without losing completed records |
| Intrinsic latency | Total time minus provider (rate-limit) waiting |
| Pareto set | Methods not beaten on every axis by another method |
| Stop gate | Mandatory human-review stop after a phase |
