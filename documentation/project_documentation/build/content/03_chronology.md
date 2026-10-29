#! Part III · How the project unfolded

# Timeline and phases

The project was built in strictly ordered phases. Every phase ended with a written review report, a checkpoint commit and an explicit approval before the next phase could start ("stop gates"). Earlier results were never overwritten: when a later stage found a problem, the old artefacts were preserved and a corrected version was added next to them.

@figure figures/d_timeline.png | Project timeline, 4 to 18 October 2026. Each bar is a phase or milestone, coloured by kind of work. | 6.6

## Phase summary

Table: Phases, checkpoints and outcomes {w=1.35,0.75,0.95,3.0,0.55}
| Phase | Dates (Oct 2026) | Checkpoint | Outcome | Tests |
|---|---|---|---|---:|
| 0 · Freeze the original MVP | 4 | `4592d10` (tag `baseline-mvp-v1`) | Original demo (12 PDFs, 394 chunks, 74-node / 87-edge metadata graph) audited, inventoried and archived | 18 |
| 1 · Research scaffold | 4 | `ea88dcf` | `research/` package: configuration, contracts, hashing, seeding, logging; synthetic fixture | 39 |
| 2 · Acquire STaRK-MAG | 4 | `f8fc9a2` | Official release downloaded at a pinned revision, checksummed and fully audited | 51 |
| 3 · Build the three views | 4–6 | `3b34d9c` | Identity registry, text view with FAISS index, graph view in CSR form, structured view in DuckDB; 358 files, exhaustive audits | 68 |
| 4 · Benchmark | 6–7 | `262c4d1` | 13,571 questions; 167 generated and verified; stress overlays; leakage audits; human-review package | 84 |
| 5 · Evaluation harness | 7 | `721c27b` | Metrics, run-record schema, resumable runner, release gate for the test splits | 105 |
| 6 · Baselines B1–B4 | 7–8 | `a19bdd5`, `cd450bb` | Four retrieval baselines; retrieval-only closeout on 56 validation questions | 125 |
| 6.5 · Research UIs | 8 | `cd450bb` | Inspection interfaces for retrieval, context and fusion | 135 |
| 7 · First RQ1 diagnostic | 8–9 | `2600275` | Context-only comparison of five methods on 16 graph questions (preserved, superseded) | 161 |
| 8 · First RQ2 diagnostic | 9–11 | `18b32f0` | Context-only fusion comparison on 24 frozen bundles plus bounded generation samples (preserved, superseded) | 185 |
| Compliance audit and repair | 11–12 | `34c8503`, `9e112a9` | 93-requirement audit of Phases 7–8; faithful re-implementation of the RQ1 and RQ2 methods | 215 |
| 9 · RQ3 policies | 11–12 | `9ac21a5`, `c1298b0` | Five retrieval-control policies, durable model client, train/dev partition, analysis module | — |
| Completion plan and execution checks | 12 | `2a7f288` … `b010c7b` | Approved completion order; 128/128 real-input checks; operational revisions 2–4 | 230 |
| Two-week scope revision | 15 | `226aea4` | Order RQ1 → RQ3 → RQ2 → RQ4; RQ3 cohort of 28; fusion-isolation study dropped; locked test out of scope | — |
| RQ3 preparation and freeze | 16 | `cea56cc` … `9943df3` | Oracle labels, AR-02 calibration, AR-01 training, RQ3 plan frozen | 273 |
| RQ2 settings and freeze | 16 | `819e7c7`, `7572c95` | Settings S1–S12 approved; RQ2 plan frozen | — |
| RQ4 design and analysis plans | 17 | `5c1f1ae`, `3a6b8bd`, `43c06b3` | Integrated-system design and selection rules; RQ2 and RQ3 analysis plans, all frozen before any analysis | — |
| Final study runs | 17 | `cdf0825`, `a68d7ad`, `59a5665`, `31f3b14` | RQ1 (160 records), RQ3 (140), RQ2 (120) and RQ4 (28) run and analysed; 0 errors | — |
| Results, paper, overall ranking | 17 | `fddc781`, `e10d661` | Results package, paper draft, decision log; one overall winner per study | — |
| Showcase application | 17 | `aa8a689`, `9477904`, `7e3cfa5` | Content file, 11-page app on a checksummed bundle, explained empty answers | 327 |
| This documentation | 18 | — | Complete record with figures, diagrams and screenshots, rebuilt by script | 327 |

@figure figures/c_tests.png | Automated tests passing at each checkpoint. The suite grew from the 18 tests of the original demo to 327, and every phase ended with the full suite passing. | 6.4

## Phase 0 — freezing the starting point

The project began from a working demonstration: **Traditional RAG** (embed a question and search 394 word chunks of 12 research PDFs) and **Basic GraphRAG** (match the question to a curated 74-node / 87-edge metadata graph, follow bounded relations to candidate papers, then search only those papers' chunks). Both used the same `all-MiniLM-L6-v2` embeddings and one shared language model at temperature 0.

Phase 0 did not change any of it. It initialised Git, removed a credential-like value from an example configuration file, recorded the installed package versions and the SHA-256 of every input and storage artefact, archived the built indexes, ran the 18 existing tests, and tagged the result `baseline-mvp-v1`. From then on every phase re-checked that the 54 protected files and 4 storage files of this baseline were byte-identical, so the original demo could always be restored.

## Phase 1 — research scaffold and contracts

A separate `research/` package was created next to the untouched demo code. It defines immutable **data contracts** (Pydantic models) for evidence items, retrieval bundles, system outputs and run records; a **configuration** system with explicit precedence (defaults < YAML < overrides) whose canonical hash excludes credentials; deterministic **seeding** of Python and NumPy; **experiment identities** derived from a hash of the configuration; and structured **logging** with credential redaction. Missing values are explicitly `null`, and token or cost measurements must name their source; nothing unknown may be stored as zero. A tiny synthetic corpus (3 papers, 6 entities) tests the contracts. Tests: 39.

## Phase 2 — acquiring and auditing STaRK-MAG

The official STaRK-MAG release was downloaded from Hugging Face (`snap-stanford/stark`, pinned revision `88269e23…`) using the same download primitive as the official loader, without running the loader's own graph construction. Fifteen files (2.62 GB) were checksummed. A streaming audit read every one of the 1,872,968 node records and 19,919,698 stored edges with a peak memory of about 81 MiB, verified every endpoint type and count, and recorded every source quirk instead of fixing it: 22,049 papers lack date, year, citation count and rank; venue information is spread over several unreconciled fields; three human-written questions (30, 50 and 72) reference author nodes rather than papers. Nothing was filled in or repaired. Tests: 51.

## Phase 3 — building the three isolated views

The audited source was converted into **MMG-STaRK-MAG v1**: a canonical identity registry, a text view (one document per paper, embedded with MiniLM and indexed with exact FAISS), a graph view (all official edges plus separately tagged inverse rows in memory-mapped CSR arrays) and a structured view (a DuckDB table of nullable paper attributes with an explicit venue precedence). The three views are joined only by the global node ID and are audited for isolation: the text view contains no authors, years or venues; the graph view labels papers by title only; the structured view contains no text or relations. Builds are resumable, every output is checksummed (358 files, 4.12 GB), and embedding parity between the GPU export and CPU PyTorch was verified (maximum absolute difference 1.9 × 10⁻⁷). Details: Chapter 10. Tests: 68.

## Phase 4 — the benchmark

Phase 4 preserved all official questions byte for byte and added 167 **generated questions** whose correct answers are computed from the frozen data before any wording, with strict source necessity for every multi-source question and stress variants added as evaluation-time overlays. Independent audits recomputed every gold set, every candidate set (665,671 candidate IDs) and every witness path (2,336), scanned for leakage across splits, and regenerated the whole benchmark into a separate directory to confirm all 323 files were byte-identical. A browser-based **human-review package** of 3,390 items was prepared; no review decisions have been made yet. Details: Chapter 11. Tests: 84.

## Phase 5 — the evaluation harness

Phase 5 built the measuring instrument: exact paper-set metrics with explicit edge cases (Chapter 16), a strict run-record schema, and a **resumable runner** that commits each question atomically under an exclusive lock, refuses to mix incompatible runs, records failures as failures, and never passes gold answers or labels to a system. A **release gate** blocks any execution on the test or human-test splits until all 2,801 required human review decisions and a leakage attestation exist. Only synthetic systems were run in this phase. Tests: 105.

## Phase 6 — retrieval baselines

Four deliberately simple baselines were implemented behind the common interface: **B1** dense text retrieval, **B2** basic graph retrieval, **B3** typed read-only SQL, and **B4** all three with fixed source shares (Chapter 13). Shared generation settings (temperature 0, low reasoning effort, JSON output, 1,024-token completion cap, per-question seed, one grounding prompt, strict parser) were frozen. A retrieval-only closeout ran all four baselines on the 56 generated validation questions (224 runs, no model calls, 0 errors). It already showed the central fact of the project: each retriever finds correct papers only for its own kind of question, and dense text retrieval finds almost none for the exact-phrase text questions. Tests: 125.

## Phase 6.5 — research inspection interfaces

A separate Streamlit interface (port 8502) let a researcher run the baselines on any question, browse the data views, inspect evidence, compiled SQL and graph paths, and compare baselines on the same question. Two further inspection apps for context (8503) and fusion (8504) followed. These were research tools, not results. Tests: 135.

## Phases 7 and 8 — first diagnostics (preserved, superseded)

Phase 7 implemented the five context-management methods and compared them **context-only** (no model answers) on 16 graph-related validation questions. Phase 8 implemented the five fusion methods, froze 24 multi-source evidence bundles, compared the methods context-only, and ran two small, explicitly approved generation samples. Both phases are preserved as historical diagnostics. They are not the reported results, for the reason explained next.

## The compliance audit and the canonical re-implementation

Before any final experiment, a forensic audit compared the Phase 7 and 8 implementations requirement by requirement with the frozen method specification (the "Phase 1D" specification of the nine methods). Of **93 requirements, 32 passed, 41 deviated, 13 were missing, 4 were equivalent implementations and 3 could not be verified.** Examples: Phase 7 evaluated graph context only even for mixed questions; CM-02 used mean endpoint similarity instead of query-to-edge similarity; Phase 8's CF-02 used a lexical overlap instead of the specified one-call model selector; CF-03 used a different intermediate-answer contract.

The project's response defines its discipline: the historical code and results were left untouched, and **canonical re-implementations** were written in new modules, faithful to the specification, with every interpretation that the specification left open written down and frozen before any result existed. For CM-01, which assumes text-chunk-to-triple provenance that STaRK does not have, a **graph-native adaptation** was approved: one "provenance unit" per official relation, written from labels and IDs only (Chapter 19). All reported RQ1 and RQ2 results come from these canonical implementations.

## Phase 9 — retrieval-control policies

The five RQ3 policies were implemented after a specification consistency audit that found no unresolved conflict and recorded six interpretations (⚑1–⚑6) open to review. The phase added a shared deterministic rule router, a durable model client that stores every request by the hash of its payload, a frozen train/development partition of the training questions (7,302 / 747), the AR-01 classifier training pipeline, the AR-02 calibration pipeline and the analysis module with family-clustered statistics, Pareto sets and a failure taxonomy (Chapter 21).

## Planning, scope and the final runs

On 12 October a **completion plan** fixed the order of the remaining work, with a review stop after every stage. Execution checks validated the operational machinery on real inputs (128/128 offline checks) and introduced question-major call order with a replay-only runner (Chapter 15); none of these operational revisions changed any prompt, context, cap, model or cohort, and each was re-frozen with new hashes and a preservation audit.

On 15 October a **two-week scope revision**, frozen before any RQ2, RQ3 or RQ4 outcome existed, set the final order RQ1 → RQ3 → RQ2 → RQ4, reduced the RQ3 cohort to the 28 normal and noisy variants of all 14 families, dropped a separate fusion-isolation study, and placed the locked test out of scope, so all reported results are validation results. Cohort sizes were set by the available compute and time budget, not by outcomes.

On 16 October the AR-01 classifier was trained, AR-02 was calibrated, and the RQ3 and RQ2 plans were frozen. On 17 October the RQ4 design and the analysis plans of RQ2 and RQ3 were frozen before any of their records was analysed; then all four studies were run and analysed (448 records, 0 errors), the results package and paper were written, the overall ranking was added, and the showcase application was built. This document was produced on 18 October.

# Decision history and governance

## How decisions were made

- **Stop gates.** Each phase ended with a review report and an explicit approval; the next phase never started automatically.
- **Authority order.** When documents disagreed, the frozen method specification won over later choices, which won over the roadmap, which won over earlier contracts; historical reports were evidence of what happened, never authority to redefine a method.
- **Operational versus scientific changes.** A change that alters no prompt, context, cap, model or cohort (for example call order or resume logic) could be made with new hashes and a preservation audit. Anything else needed explicit approval and a new versioned record.
- **No outcome-driven changes.** No setting, prompt, threshold or cohort was changed after seeing results. Negative and inconclusive results are reported as such.

## The fifteen scientific invariants

1. The STaRK global node ID is the only key shared by the three views.
2. Text isolation: the text view holds title and abstract only.
3. Graph isolation: a paper's graph label is its title only; relations are the four official types.
4. Structured isolation: scalar paper attributes only.
5. The raw source is immutable.
6. The benchmark is immutable.
7. Baselines stay simple (no hidden rerankers, rewriting or routing).
8. One variable at a time (RQ1 context, RQ2 fusion, RQ3 control).
9. No gold answers or labels at inference time.
10. No use of the test or human-test splits for tuning or development.
11. Evidence always maps back to authoritative IDs.
12. NULL is not zero.
13. Waiting is not latency: pauses are never counted as method time.
14. Historical results stay preserved.
15. A method may change only to match its frozen specification or an explicitly approved dataset adaptation, never because of observed performance.

## Key decisions

Table: Key decisions from the decision log (condensed; full text in documentation/Research_Decision_Log.md) {w=0.6,1.0,4.6}
| ID | Date | Decision |
|---|---|---|
| P0 | 4 Oct | Preserve the original demo; record versions and checksums; archive storage; never change the baseline prompts or methods. |
| P1-03/04 | 4 Oct | Configuration precedence defaults < YAML < overrides; canonical configuration hash excludes credentials. |
| P2-05/07 | 4 Oct | Audit the whole source with streaming readers; report missing values and names faithfully, never fill them. |
| P3-02/06 | 4–6 Oct | Global STaRK integers are the physical join keys; keep all official edges and add tagged inverse traversal rows (never counted as source edges). |
| P3-09 | 6 Oct | Frozen MiniLM weights exported to ONNX; parity with CPU PyTorch verified (maximum absolute difference 1.9e-7). |
| P4-05/06 | 7 Oct | Compute gold before wording; require strict source necessity for answerable multi-source questions. |
| P4-09 | 7 Oct | Noise and conflict exist only as evaluation-time overlays; canonical stores never change. |
| P5-07 | 7 Oct | Test and human-test execution is gated by a hash-bound human release (2,801 decisions). |
| P6-09 | 8 Oct | Freeze baseline controls before looking at results; run only bounded validation work. |
| PR-02 | 12 Oct | Completion order with a review stop after every stage. |
| PR-05/06 | 12 Oct | Operational revisions: successful-call counting; question-major call order with a replay-only runner. No payload changes. |
| PR-07 | 15 Oct | Two-week scope revision (order, 28-question RQ3 cohort, fusion-isolation dropped, locked test out of scope), frozen before any RQ2–RQ4 outcome. |
| PR-09 | 16 Oct | RQ3 plan frozen: 23 code files and 18 artefacts including AR-01 (best epoch 7) and AR-02 (LOWER 0.40, UPPER 0.75). |
| PR-10 | 16 Oct | RQ2 settings S1–S12 approved; RQ2 limited to the primary 24-bundle study. |
| PR-11 | 17 Oct | RQ4 = one integrated system INT-1: selected policy → CM-B1 → selected fusion; selection rules fixed before any RQ2 or RQ3 outcome was analysed. |
| PR-12 | 17 Oct | One completion cap of 1,024 tokens for every model call (controllers, critics and repairs included), decided before any affected outcome was analysed, because shorter per-role caps truncated the reasoning of controller calls. |
| PR-14 | 17 Oct | All four studies complete with 0 errors; RQ4 selection by the frozen rules: AR-B1 → CM-B1 → CF-B1. |
| PR-15 | 17 Oct | Overall ranking: one winner per study by equal-weight ranks on the frozen Pareto axes; their combination equals INT-1. |
