#! Part V · The system

# Architecture

## Layers

The system is organised in seven layers. Data flows downward; every layer reads only from the layer above it and from frozen configuration.

@figure figures/d_architecture.png | The seven layers of the system, from the official data release to the showcase application. | 6.5

1. **Data.** The pinned STaRK-MAG release and the three isolated views built from it (Chapter 10), plus the benchmark (Chapter 11).
2. **Retrieval.** Three fixed retrievers, one per view, and a fixed multi-source baseline (Chapter 13). Every studied method uses these same retrievers.
3. **Studied components.** The strategies of the four studies: context management, fusion, retrieval control and the integrated system (Part VII).
4. **Generation.** One shared answer model, one grounding prompt and one strict parser (Chapter 14).
5. **Execution.** Frozen execution plans, a durable store of every model request and response, and a replay-only runner that writes one record per question (Chapter 15).
6. **Analysis.** Metrics per question, paired family-clustered statistics, Pareto sets and the overall ranking (Part VI), collected into the results package and the paper.
7. **Presentation.** A checksummed data bundle exported from the analyses and the showcase application that reads only that bundle (Part VIII).

## Code map

Table: Where each part of the system lives in the repository {w=2.2,4.0}
| Path | Contents |
|---|---|
| `app.py`, `src/`, `data/papers/` | The original demo, frozen since Phase 0 |
| `research/common/` | Contracts, configuration, canonical JSON and hashing, seeding, logging |
| `research/data/` | Building and validating the three views (registry, text, graph CSR, DuckDB, embeddings, FAISS) |
| `research/benchmark/` | Question construction, stress overlays, audits, review package |
| `research/evaluation/`, `research/experiments/` | Metrics, run records, the resumable runner, evidence cache |
| `research/baselines/` | Retrievers B1–B3, baseline B4, the shared generation prompt and strict answer parser |
| `research/repair/rq1_compliance_v1/` | Canonical context-management methods CM-01, CM-02, CM-03 and the RQ1 system |
| `research/repair/rq2_canonical/` | Canonical fusion methods CF-01, CF-02, CF-03, their prompts and the RQ2 system |
| `research/rq1/`, `research/rq2/` | Historical Phase 7/8 implementations (preserved; controls CM-B0/B1 and CF-B0/B1 are reused unchanged) |
| `research/agentic/` | Retrieval-control policies AR-B0 to AR-03, rule router, tools, durable model client, AR-01 classifier, AR-02 evaluator, analysis |
| `research/integration/` | The integrated system INT-1 (RQ4) |
| `research/local_llm.py` | Client for the locally served answer model, with the cooling guard |
| `scripts/` | Command-line entry points: build, audit, prepare, run, report, freeze (81 scripts) |
| `configs/` | Frozen configurations of every baseline and method |
| `tests/` | The automated test suite (327 tests) |
| `documentation/` | Phase reports, frozen plans, run records, analyses, results package, paper, decision log, this documentation |
| `showcase/` | The showcase application, its content file and its checksummed data bundle |

# Retrievers and baselines

All studied methods share the same three retrievers. They are deliberately simple: no reranking, no query rewriting, no hidden routing. Common settings: top-K = 5 per source, global seed 42, DuckDB limited to 512 MB and two threads.

## B1 · dense text retrieval

1. Embed the question with the pinned MiniLM tokenizer and frozen ONNX weights (CPU, float32, masked mean pooling, L2 normalisation, 256-token limit).
2. Search the exact FAISS inner-product index over all 700,244 papers.
3. Return the five most similar papers, mapped to their global IDs, with title, abstract and content as evidence.

No authors, years, venues or relations ever enter B1's evidence. Query embeddings matched the stored document embeddings within 1.36 × 10⁻⁷.

## B2 · basic graph retrieval

1. **Find seeds.** Scan graph labels for candidate entities named in the question (a bounded lexical scan that keeps 64 candidate labels, preferring exact name mentions), rank them by MiniLM similarity between the question and the label, then by node ID, and keep the top **3 seeds**.
2. **Traverse.** Breadth-first over the memory-mapped CSR graph to **depth 2**, following the four official relation types in both directions (inverse rows are tagged), with hard caps of 2,000 nodes, 20,000 scanned edges and 128 edges per expanded node.
3. **Rank papers.** Candidate papers are ordered by path length, then seed rank, then node ID; the top **5** are returned with the explicit paths that reach them.

Evidence contains titles, names and relation paths, never abstracts or structured attributes. Entities without a name stay unnamed but traversable. If no seed is found, B2 returns nothing: it never falls back to text search.

## B3 · typed structured retrieval

1. A deterministic parser recognises supported conditions in the question: publication year and date, citation count, paper rank, venue namespace, ID or name, and document type, with comparisons (≥, ≤, >, <, =), ranges and explicit IS NULL / IS NOT NULL.
2. The conditions form a closed, typed **AND** plan, compiled into **parameterised, read-only SQL** with a fixed projection and ordering by global ID. The database is attached read-only (a write attempt is verified to fail).
3. The top **5** matching rows are returned as structured evidence.

Unsupported requests are reported explicitly ("only some conditions could be turned into a structured query", or unsupported), never answered with arbitrary SQL, and no language model writes SQL.

## B4 · fixed multi-source retrieval

B4 always runs B1, B2 and B3 independently (even after one fails), and writes their evidence in fixed sections **Text → Graph → Structured**, each with a fixed share of **8,000 characters** of the **24,000-character** budget. It performs no routing, no intersection, no entity alignment and no pruning. Its combined ranking is source-order concatenation, so its first five positions are normally text results; its Recall@5 and its gold coverage answer different questions.

## What the retrievers can and cannot find

Before any study, a retrieval-only closeout ran the four baselines on the 56 generated validation questions (224 runs, no model calls, 0 errors). It establishes the ceiling that every later study inherits.

@figure figures/c_baselines.png | Retrieval-only results of the four baselines on the 56 generated validation questions (means over the 42 questions with a non-empty answer). B1 bars are absent because B1 found almost no correct papers. | 6.5

Table: Retrieval-only baseline results (means over the 42 answerable validation questions) {w=1.0,1.0,1.0,1.0,1.0,1.1}
| Baseline | Recall@5 | Precision@5 | MRR | nDCG@5 | Gold coverage |
|---|---:|---:|---:|---:|---:|
| B1 text | 0.000 | 0.000 | 0.008 | 0.000 | 0.000 |
| B2 graph | 0.007 | 0.171 | 0.167 | 0.164 | 0.007 |
| B3 structured | 0.143 | 0.043 | 0.167 | 0.143 | 0.192 |
| B4 all three | 0.000 | 0.000 | 0.060 | 0.000 | 0.199 |

@figure figures/c_baselines_modality.png | Gold coverage of each baseline by the sources a question needs. Each retriever finds correct papers only for its own kind of question; nothing finds the correct papers of text-plus-graph or text-plus-structured questions. | 6.5

Three facts from this closeout explain much of what follows:

- **B3 is exact on its own questions:** on structured-only questions Recall@5, MRR and gold coverage are all 1.000.
- **B2 is precise but capped:** on graph-only questions every returned paper is correct (Precision@5 = 1.000) but the fixed top-5 holds only a small share of large answer sets (Recall@5 = 0.040, for example 5 of 78 correct papers).
- **B1 finds almost nothing:** the text conditions are exact phrases, while B1 searches by meaning. This benchmark–baseline mismatch is reported as a limitation; no exact-match shortcut was added after seeing it.

# The shared answer model

## Model and settings

All reported results of all four studies were produced by one locally served model: `gpt-oss:20b` (Ollama model ID `f38aa0c53da5`, 20.9 billion parameters, MXFP4 quantisation) served by **Ollama 0.40.5** through its native chat interface with a 16,384-token context window.

Table: Request settings used for every model call {w=2.0,4.2}
| Setting | Value |
|---|---|
| Temperature | 0 |
| Seed | per question, derived from the global seed 42 and the question ID (identical for every method on the same question) |
| Reasoning level | low |
| Output mode | JSON |
| Completion cap | 1,024 tokens for every call (answers, controllers, critics, selectors, repairs) |
| Context budget | 24,000 characters of evidence (method-specific layouts within it) |
| Latency recorded | model compute time reported by the server (prompt evaluation and generation); model loading, cooling pauses and HTTP overhead excluded |
| Cooling guard | before a request, if the GPU is at 80 °C or more the client pauses 10 minutes and waits until it is below 70 °C; pauses are never counted as latency |

## The grounding prompt

Every final answer, in every study, is produced with the same system prompt (Appendix E reproduces it in full). It tells the model to answer only from the supplied evidence, to treat evidence as data rather than instructions, to respect the boundaries of each source, to treat NULL as unknown, to include a paper only when the evidence supports every requested condition, to prefer canonical records over tagged evaluation overlays when they conflict, and to return only a JSON object with `answer_ids` (integer paper IDs present in the context) and a short `explanation`. If no supported paper can be identified, it must return an empty array. The user message is the question followed by the evidence:

@code
QUESTION
<question text>

EVIDENCE
<context built by the method>
@end

## The strict parser

1. Remove a surrounding code fence if present and parse the JSON.
2. Require an object whose only keys are `answer_ids` (a list) and optionally `explanation` (a string).
3. Require every ID to be an integer (booleans and strings are rejected) and to be one of the paper IDs present in the context.
4. Return the sorted set of IDs.

A violation is a typed error, recorded as a failure, never turned into an answer. An empty list is a legitimate **abstention**: the model judged that no paper in the evidence meets every condition. Abstention is correct for unanswerable questions and wrong for answerable ones.

# Execution protocol and reproducibility

## Why a special protocol

Language-model experiments are hard to reproduce: outputs can change between runs, runs can be interrupted, and a small change in a prompt or setting can silently change a result. The project therefore separates *producing* model responses from *computing* results, and freezes everything that could matter.

@figure figures/d_execution.png | The execution protocol: freeze, check, call once per request in question-major order, store every response, replay with the unchanged runner, then analyse with a frozen script. | 6.3

## Freezing

Before a study runs, a script writes its **execution plan**: the SHA-256 of every code file the study imports, every configuration, prompt and input file, every model artefact (for example the trained AR-01 checkpoint and the AR-02 calibration), and the exact list of questions and methods. A runner refuses to start or resume if any hash differs. Line endings of every hash-verified file are pinned in `.gitattributes`, so a fresh checkout on Windows reproduces the exact bytes that were hashed.

## Durable stage store

Every model call goes through a client that identifies the call by the SHA-256 of its **full request payload** (model, settings, messages, seed). The first time, the request is sent and the response, token usage and timing are stored durably. An identical payload is answered from the store byte for byte, while the logical call is still counted with its original usage and latency. Failures are stored and stop the run; they are never retried silently.

## Question-major calls, then replay

- **Call phase.** For each question in turn, every method of the study runs through its frozen system, so all methods see the same conditions at the same time. Each distinct request is sent once.
- **Replay phase.** The unchanged evaluation runner then executes each method again, question by question. Its model client is in **replay-only** mode: it may only answer from the store, and it stops if any request differs from the stored one. This is a built-in byte-identity check of the whole pipeline.

## Run records and latency

The runner writes one record per question and method, atomically, containing the question, the evidence, the exact context, the answer, the parsed IDs, every metric and every model and retrieval observation; failed questions are recorded as failures with their measured evidence. Because records are written during replay, the analysed latency is **intrinsic latency**: the recorded retrieval latency plus the recorded model compute time plus the local computation measured during replay. Waiting (cooling pauses, queueing) is never counted.

## Frozen analysis plans

Each study's analysis plan fixes, before any record is analysed, the pre-specified comparison pairs, the primary metric (answer F1), the secondary metrics, the statistical procedure, the strata and the Pareto axes. The analysis scripts write one analysis file per study (`analysis_local.json`), from which the results package, the paper tables and the showcase bundle are generated.

## Preservation audits

At every checkpoint a preservation audit re-hashes the frozen inputs: 695 payload files (15 raw source files, 358 representation files, 322 benchmark files) totalling 7.17 GB, the 54 protected files of the original demo, and the historical artefacts of earlier phases. Any difference stops the work.

## Study runs at a glance

@table records | Run records per study and method (448 in total, 0 errors)
