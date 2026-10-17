# Multi-Modal GraphRAG: A Controlled Study of Context Management, Cross-Modal Fusion and Agentic Retrieval over Text, Graph and Structured Views of a Scientific Corpus

*Draft. Tables and figures: `documentation/results/RESULTS.md`. All results are validation results; the locked test set is out of scope.*

## Abstract
We study how a retrieval-augmented LLM should use three heterogeneous representations of the same scientific corpus — text (title and abstract), a knowledge graph (authors, institutions, citations, fields of study) and structured metadata (year, citations, rank, venue, document type). On MMG-STaRK-MAG, a three-view conversion of STaRK-MAG joined only by the official node ID, we evaluate, one variable at a time, five context-management strategies (RQ1), five cross-modal fusion strategies (RQ2) and five retrieval-control policies (RQ3), then one integrated system (RQ4), against frozen baselines, with family-clustered paired statistics. No method improved answer quality with statistical support in any study; answer quality is bounded by upstream evidence, which rarely contains every required paper for multi-source questions. The methods differed significantly in efficiency: a deterministic rule router selected sources better than querying every source and was the cheapest policy, while the learned and agentic controllers spent more tokens without answer gains. The integrated system inherited the router's source selection at a modest token cost.

## 1. Introduction
Retrieval-augmented generation increasingly draws on more than one kind of knowledge: free text, entity–relation graphs and tabular records. Each representation answers different parts of a question (topic claims in abstracts, authorship and citation paths in a graph, numeric and categorical attributes in a table), and many questions need several of them at once. Three design questions follow: what should survive a limited context budget (context management), how evidence from different representations should be combined (fusion), and which representation to query, in what order and when to stop (retrieval control). Integrated systems usually change all three at once, which makes it hard to attribute effects.

This work isolates each question. We freeze the corpus, the retrievers, the generator, the prompt and the budget, vary one component at a time against simple controls, and only then integrate. Contributions:
1. **MMG-STaRK-MAG**, three deliberately isolated views (text, graph, structured) of the official STaRK-MAG release joined only by its global node ID, with an audited, resumable build.
2. A **benchmark protocol** that computes gold sets before wording, verifies strict source necessity for every multi-source query, and adds evaluation-time stress overlays (noisy, conflict, unanswerable) without mutating canonical data.
3. A **controlled evaluation** of 15 retrieval-pipeline variants (9 literature-inspired methods, 6 simple controls) plus one integrated system, with family-clustered paired statistics, Pareto analysis and a failure taxonomy, under a reproducible operational protocol for a rate-limited free-tier LLM provider.
4. Evidence that, under a fixed generator and frozen retrievers, simple controls (fixed top-K context, source-separated fusion, rule routing) are Pareto-optimal, and that the dominant limitation is upstream evidence coverage rather than context management, fusion or retrieval control.

"Multi-modal" here means heterogeneous knowledge representations, not images or audio.

## 2. Related work and method sources
The studied methods are adaptations of published mechanisms, re-implemented under one frozen interface; we make no claim to reproduce the original systems.
* **Context management (RQ1).** KG²RAG-inspired expansion and organisation of graph evidence (seed relations, one-hop expansion, spanning tree, depth-first linearisation, cross-encoder ordering); a G-Retriever-inspired prize-collecting Steiner tree (PCST) subgraph; a QAFD-RAG-inspired query-aware flow-diffusion selector.
* **Fusion (RQ2).** KAG-inspired entity alignment (mutual indexing of knowledge and source chunks; only the alignment principle is used); SAG-inspired dual-path selection (an LLM selects up to five structural items jointly, a semantic path fills to ten); MegaRAG-inspired late fusion (source-specific reasoning, then a fusion stage).
* **Retrieval control (RQ3).** Adaptive-RAG-inspired query-complexity routing with a trained classifier; CRAG-inspired corrective retrieval with a calibrated relevance evaluator; an AGENT-G-inspired agent with validator and commentor roles.
[Citations to be inserted from `data/papers/` P001–P012.]

## 3. Data and benchmark
### 3.1 Corpus and views
STaRK-MAG (Hugging Face `snap-stanford/stark`, revision `88269e23…`) contains 1,872,968 entities (700,244 papers, 1,104,554 authors, 8,701 institutions, 59,469 fields of study) and 19,919,698 directed edges (writes 6,768,883; affiliated-with 1,029,162; cites 4,878,384; has-topic 7,243,269). MMG-STaRK-MAG v1 builds three views joined only by the global node ID:
* **Text:** one document per paper (title + abstract); exact inner-product FAISS index over 700,244 × 384 unit vectors from `all-MiniLM-L6-v2` (frozen weights, ONNX export, 256-token input limit; parity with CPU PyTorch: max |Δ| 1.9e-7).
* **Graph:** memory-mapped CSR adjacency over the official edges plus tagged derived-inverse traversal rows (39,839,396 traversal rows; never reported as source edges).
* **Structured:** DuckDB table of nullable paper attributes; missing values stay NULL (22,049 papers lack date/year/citation/rank); year is never derived from date; explicit venue precedence.

### 3.2 Benchmark
13,571 queries: 13,323 official synthetic and 81 compatible official human queries (unverified modality/hop labels) plus 167 generated, programmatically verified queries = 42 base constructions (2 per modality class T, G, S, TG, TS, GS, TGS × 3 splits) × stress variants (normal, noisy, conflict, unanswerable), minus one infeasible variant. Gold sets are computed from exact text claims, graph paths and parameterised structured predicates before any wording; for every answerable multi-source query, dropping any required modality strictly enlarges the answer set (counterexamples persisted). Stress variants are evaluation-time overlays: noisy (hard distractors), conflict (one altered fact in the overlay only; canonical evidence stays authoritative), unanswerable (verified empty answer set). Variants of one base form a *family* and are analysed as correlated. Splits are structurally different by design (prevents template leakage; introduces a stated distribution shift).

## 4. System and baselines
All variants share frozen retrievers: **B1** dense text retrieval (top 5), **B2** graph retrieval (3 label-matched seeds, breadth-first to depth 2 with node/edge caps, top 5 papers with paths), **B3** deterministic parser → typed AND predicates → read-only parameterised SQL (no LLM SQL), and **B4** fixed multi-source concatenation (Text → Graph → Structured, 8,000 characters per source, 24,000 total). The shared generator for all methods and studies is `gpt-oss:20b` served locally (temperature 0, low reasoning effort, JSON output, 1,024-token cap for every call, per-query seed) with one grounding prompt and a strict parser that accepts only paper IDs present in the context.

## 5. Methods
### 5.1 RQ1 — context management (graph evidence)
CM-B0 raw order cut at the budget; CM-B1 fixed top-K (5 best papers and their paths); CM-01 KG²RAG-inspired (graph-native provenance units, semantic seeds, one-hop expansion, maximum spanning forest, DFS serialization, pinned BGE reranker, dedup, budget); CM-02 PCST-inspired (node/edge prizes from query similarity, `pcst_fast`, connected subgraph); CM-03 QAFD-inspired (LLM keyword extraction, keyword-seeded flow diffusion with hybrid conductance, support threshold, connector-preserving pruning). Text and Structured evidence of mixed queries pass through unchanged.
### 5.2 RQ2 — cross-modal fusion
All methods receive the byte-identical cached bundle and may not retrieve. CF-B0 raw concatenation; CF-B1 source-separated sections; CF-01 entity alignment (explicit ID → exact normalised alias → type-constrained registry resolver; groups ordered by max relevance, source coverage, entity ID; complete groups first, truncation flagged); CF-02 one LLM selector call over a compact manifest (≤ 5 structural items, one schema repair, relevance fallback) plus semantic fill to 10; CF-03 one reasoning call per non-empty source (JSON finding with supporting evidence IDs validated against that source) and one grounded fusion call (one retry).
### 5.3 RQ3 — retrieval control
AR-B0 always queries Text, Graph, Structured; AR-B1 a deterministic cue router; AR-01 a t5-base classifier (no retrieval / one source / multi-step, ≤ 3 steps with a sufficiency controller) trained on a frozen train partition (7,302 train / 747 dev by hashed query ID; labels from a retrieval-only oracle) with dev-loss early stopping (best epoch 7); AR-02 a MiniLM cross-encoder evaluator with Platt calibration on the dev partition (745 queries) and GOOD/AMBIGUOUS/BAD thresholds (0.40 / 0.75) chosen by a frozen grid rule, ≤ 2 corrective rounds; AR-03 an agent (one tool per step, ≤ 4 iterations) with validator and commentor roles and loop guards. All share tools, evidence memory, fixed context (8,000 characters per queried source) and the generator.
### 5.4 RQ4 — integration
INT-1 = the RQ3 policy selected by a pre-registered rule (highest answer F1 within the Pareto set; ties by tokens) → CM-B1 on graph evidence → the RQ2 method selected by the analogous rule → that method's answer. CM-B1 was fixed before results for cost reasons; CM-01 is reported as not integrated.

## 6. Experimental protocol
* **Cohorts (validation only).** RQ1: 32 verified queries with a graph component (8 families × 4 stress). RQ2: 24 frozen multimodal bundles (8 families × normal/noisy/conflict), stratified before any call into fully (2) / partially (6) / un-supportable (16) by whether the bundle contains the gold papers. RQ3 and RQ4: 28 queries (all 14 families × normal and noisy; reduced from 56 by a scope decision recorded before outcomes).
* **Freezing.** Every study freezes code, configs, prompts, inputs and models by raw-byte SHA-256 in an execution plan before any call; runners refuse to start or resume on any change. No setting is tuned after outcomes; test and human-test data are never used.
* **Execution.** Every model call is stored durably by the hash of its full request; failures are recorded, never silently retried. Model calls are made in query-major order (all methods for a query, then the next) through the frozen systems; the unchanged Phase 5 runner then replays the stored responses per method in a replay-only mode that stops instead of sending if any request differs (a built-in byte-identity check). Analysed latency = recorded retrieval latency + model compute time + local compute.
* **Statistics.** Paired per-query deltas; family-clustered bootstrap 95 % CI (10,000, seed 42); exact two-sided sign-flip test over family sums; Holm correction over pre-specified pairs per metric; significance only at Holm p < 0.05. Pareto sets and a multi-label failure taxonomy are descriptive.

## 7. Results
### 7.1 RQ1 — context management (32 queries, 8 families)
No method improved answer F1 with statistical support (all Holm p = 1.00; with 8 families the smallest attainable p is 2/256). Every method answered the 8 unanswerable queries correctly (empty set); correct answers on answerable queries came only from the graph-only families. CM-01 had the highest F1 (0.283; 0.045 on answerable queries) and MRR (0.359) at about 3.5x the input tokens and 2.3x the latency of CM-B1 (1,416 tokens, 7.6 s); CM-B1 dominated CM-B0 and CM-03; CM-02 was fastest (6.5 s) with the lowest MRR; CM-03 was slowest (40.7 s). Pareto set: CM-B1, CM-01, CM-02. Gold coverage (the share of correct papers present in the context) was at most 0.34 for every method (CM-03 0.338, CM-01 0.175), which indicates that upstream retrieval, not context management, limits answer quality.

### 7.2 RQ2 — cross-modal fusion (24 bundles, 8 families)
All five methods returned an empty answer on all 24 bundles (answer F1 = 0), including the 2 fully supportable bundles where the gold paper was present in the context: the generator judged that no paper satisfied every condition (both are conflict variants). Differences are therefore in cost only: CF-B1 was cheapest and fastest (3,485 input tokens, 8.4 s) and the only Pareto-optimal method; CF-02 needed 2 calls and CF-03 3.75 calls per bundle (19.6 s). CF-01 resolved every evidence item by explicit ID (global resolver used 0 times); the CF-02 selector picked 0.58 structural items on average with no fallbacks; CF-03 produced 66 grounded source findings and 6 no-evidence sources, with no fusion retries.

### 7.3 RQ3 — retrieval control (28 queries, 14 families)
All five policies produced identical answers (F1 0.154, EM 0.143), so answer quality did not separate them. Efficiency did, with statistical support: AR-B1 (rule router) selected sources better than AR-B0 (source-selection F1 0.876 vs 0.700, Holm p = 0.014) and used fewer tokens (1,622 vs 2,251, p = 0.008); AR-01 (+2,168 tokens vs AR-B0, +2,796 vs AR-B1) and AR-03 (+5,467, +6,096) cost significantly more without answer gains; AR-03 wasted almost no retrieval (0.01) but needed 6.5 model calls per query. Pareto set: AR-B1 only.

### 7.4 RQ4 — integration (28 queries)
The frozen rules selected AR-B1 -> CM-B1 -> CF-B1 (INT-1). INT-1 matched AR-B0 and AR-B1 on answers (F1 0.154) and kept AR-B1's source selection, significantly better than AR-B0 (+0.176 source F1, Holm p = 0.004); it used significantly more tokens than AR-B1 alone (+772, p < 0.001) because the fusion stage's context is larger, with no significant latency difference. Under the frozen top-5 graph retriever, CM-B1 removed no graph evidence for this single-graph-call policy.

## 8. Limitations
* Small cohorts of correlated variants (8 or 14 independent families); exploratory validation, not benchmark-wide inference; no locked test; labels are programmatically, not human, verified (2,801 human reviews outstanding).
* Upstream evidence is often insufficient (RQ2: 16 of 24 bundles contain no gold paper), so many comparisons measure correct abstention.
* Benchmark/baseline mismatch: exact-phrase text predicates versus dense retrieval (B1 near zero).
* RQ1 latency comparison favours CM-02/CM-03 (query-specific scores staged offline) over CM-01 (computed inside its timer).
* Under the frozen top-5 graph retriever, CM-B1 prunes only when a policy issues more than one graph call.
* One generator model; cohort sizes were fixed by the available compute and time budget.

## 9. Reproducibility
Raw data, representations and benchmark are verified against recorded SHA-256 manifests (695 payloads); each study's execution plan lists every frozen file hash; line endings of hash-verified files are pinned; every provider attempt (including rate-limited ones) is stored with headers and usage; the decision log (`documentation/Research_Decision_Log.md`) records every scope and operational decision with its evidence.
