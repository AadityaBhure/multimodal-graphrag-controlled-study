# Phase Review Report

PHASE: 6 — Research Baselines B1–B4

STATUS: **PASS — implementation, offline validation and the explicitly approved four-call Groq smoke are complete. Stopped before Phase 7.**

## 1. Checkpoint and preserved scope

Approved Phase 5 was committed as `721c27b2bddf0efca2cc62eeeb6e73e2d2c9ca01`. A clean working tree was confirmed before implementation. Before/after checks verify all 695 frozen payload files: 15 raw STaRK files, 358 Phase 3 representation files and 322 Phase 4 benchmark payload files, plus their manifest bindings. All 54 frozen MVP tracked files and four original storage files still match. `baseline-mvp-v1` remains `4592d102b363c7d55d3c85ee67efe89409ae96b5`. Also verified unchanged: 630 prior review-package/fixture files.

The source edge count remains **19,919,698 official directed edges**. The 19,919,698 derived inverses remain separately tagged traversal edges; no graph or index was rebuilt. Missing values, original 84 human records, the 81-record primary human split, all benchmark gold and all 13,404 unverified official modality/hop annotations remain unchanged.

## 2. Baseline implementation

**B1 — Traditional Text RAG.** Embed the natural-language query using the pinned MiniLM tokenizer and frozen ONNX weights; CPU float32, masked mean pooling/L2 normalization, 256-token input limit. Search the existing exact FAISS inner-product index of 700,244 papers and return fixed Top-5. Map FAISS rows to authoritative global IDs and load only the corresponding text rows. Evidence contains paper ID/title/abstract/content, with no authors, affiliations, topics or structured metadata. No reranking or query rewriting. Query encoding versus the original stored vector differed by only 1.36e-7 maximum absolute value, passing the frozen parity tolerance.

**B2 — Basic GraphRAG.** Resolve entities from graph labels only: a bounded lexical candidate scan followed by MiniLM similarity of graph labels. Exact source-name mentions are prioritized, then semantic similarity, then node ID. Keep 64 candidate labels and three seeds. Traverse the memory-mapped CSR breadth-first to depth two, with fixed node/edge/per-node caps. Follow only AUTHOR-WRITES-PAPER, AUTHOR-AFFILIATED_WITH-INSTITUTION, PAPER-CITES-PAPER and PAPER-HAS_TOPIC-FIELD_OF_STUDY, including separately tagged inverse traversal rows. Paper candidates are ordered by path length, seed rank and global ID. Context contains titles, source names and explicit supporting paths, never abstracts or structured attributes. Missing names remain NULL but nodes are traversable. No seeds means no candidates; the text FAISS index is never opened and no global Text RAG fallback exists.

**B3 — Structured Retrieval.** A deterministic supported-language parser emits a typed closed predicate plan. Numeric/date comparisons, ranges, exact string comparisons and explicit IS NULL/IS NOT NULL compile to parameterized read-only SQL with a fixed projection and global-ID ordering. Supported fields: publication year/date, citation count, paper rank, normalized venue namespace/ID/name and document type. DocType is not promoted into a venue taxonomy. Unsupported queries are recorded explicitly; no arbitrary SQL, unconstrained full-table retrieval or LLM SQL parser is used. The actual DuckDB store is attached READ_ONLY and rejected a write attempt.

**B4 — Fixed Multi-Source RAG.** Invoke Text, Graph and Structured independently for every query, including attempting the remaining sources after a failure. Reuse the same retrieval functions and immutable source cache. Concatenate Text, Graph and Structured sections in that order; each receives a fixed one-third of the common context safety cap. No routing, evidence intersection, entity alignment, score fusion, advanced graph pruning or context optimization. Combined ranking is first-occurrence source-order concatenation; its first five results are normally Text, so Recall@5 and full gold coverage intentionally answer different questions.

Implementation lives in `research/baselines/`. `scripts/run_baseline.py` is a thin command-line adapter to the existing Phase 5 runner, not a replacement experiment engine. `Baseline_Protocol.md` documents operation and supported query forms.

## 3. Frozen development configurations and generation

| Control | Value |
| --- | --- |
| Retrieval per source | Top-K = 5 |
| Graph seeds / lexical candidate pool | 3 / 64 |
| Graph depth | 2 |
| Graph node / scanned-edge / per-node-edge caps | 2,000 / 20,000 / 128 |
| DuckDB memory / worker threads | 512 MB / 2 |
| Context safety cap | 24,000 Unicode characters total |
| B4 source shares | 8,000 characters each, fixed |
| Generator | openai/gpt-oss-120b via Groq |
| Temperature / reasoning effort | 0 / low |
| Maximum completion tokens | 1,024 |
| Seed | Global 42, deterministic query-derived seed shared across methods |
| Output | Strict JSON object with integer answer_ids and optional explanation |
| Query embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Embedding revision | 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 |

All comparable baselines use one common grounding prompt and generation adapter. Answers can contain only paper IDs actually present in retained context. Malformed output, booleans/string IDs and unsupported paper IDs produce a typed parsing error rather than a fabricated answer. Empty answers are legitimate abstentions, not automatically evidence that the query is truly unanswerable.

Named configs are `configs/baselines/B1.json`–`B4.json`, matching `*-offline.json`, and the five-query `*-validation-offline.json` files. Controls were chosen before inspecting retrieval outcomes and were not tuned in response to this smoke test. Context truncation is a fixed safety rule; truncated/omitted evidence IDs are logged. Context token counts remain NULL because the generator's exact context-only tokenizer was not used; provider total prompt/completion usage is measured separately.

## 4. Runner, cache, provenance and failure integration

Every baseline returns SystemOutput with ranked global paper IDs, complete typed source evidence/provenance, final answer/parsed set, context, retained IDs, measured latency/calls/tokens and diagnostics. The existing runner supplies deterministic experiment identity, config/code/data hashes, seeding, per-query records/events, aggregate CSV/JSON and safe resume.

Two small backward-compatible Phase 5 integrations add optional SystemOutput diagnostics/errors and let error records retain partial evidence and measured telemetry. Failed answer IDs stay NULL. Generation/provider errors never expose credentials in artifacts. All previous tests continue to pass. New schemas are saved in this review package; prior Phase 5 schemas/artifacts remain unchanged.

Evidence caching is keyed by source implementation fingerprints, query, representation manifest, fixed options and seed. Cached bundles retain original retrieval diagnostics, including graph bounds and structured plans. Different content cannot overwrite a cache key. Stress injections occur after retrieval/caching, are source-specific and carry overlay provenance. Canonical data is never mutated. Graph overlays cannot introduce papers outside graph-selected candidates. Cache hits count as zero new retrieval/tool calls, while `source_invocations` records B4's three source-interface invocations.

## 5. Tests and audits

**125 tests passed, one pre-existing frozen Phase 3 DuckDB deprecation warning.** Twenty baseline tests cover Top-K/identity, graph candidate restrictions, null-name traversal, inverse tagging, no-seed/no-fallback, traversal budgets, parameterized SQL/injection/NULL behavior, supported-language parsing, unsupported intents, independent B4 calls, context limits, answer parsing, partial failures, measurement retention, immutable cache use, runner resume, stress isolation and identical Groq request controls/provider-usage recording through a mock transport.

Real-data offline validation adds canonical registry joins for every returned ID; MiniLM parity against a frozen vector; actual read-only DuckDB write rejection; confirmation that CSR arrays are numpy.memmap; confirmation B2 never loads the FAISS index; and byte-identical result files after resume for all four baselines. Final preservation audit verifies all frozen raw/representation/benchmark files and the original MVP. There were no package installations, model downloads or paper-embedding/index rebuilds. Runtime library versions and the exact tokenizer/ONNX fingerprint are recorded separately.

## 6. Representative validation results

Five validation queries were selected before execution: generated T, G, S and TGS normal queries, plus one official synthetic query. Each baseline ran retrieval on all five: **20 offline executions, zero LLM calls**. Offline answers are NULL, not fabricated empty sets; retrieval metrics remain available. The official query retains unverified modality/hop labels.

Representative source checks:

- Structured query `generated:2505e1a85cb296afd54b:normal` asks for recorded paper rank 19611, journal namespace, publication year 2015 and citation count 26. B3 returned the one gold paper: Recall@5 = 1 and full gold coverage = 1; Precision@5 = 0.2 under the approved fixed-K denominator.
- Graph query `generated:5692e57aa6e252201105:normal` asks for papers with an author affiliated with Baoji University of Arts and Sciences. B2 returned five valid graph-selected gold papers out of 78: Recall@5 = 5/78 = 0.0641025641. This illustrates the fixed Top-K recall ceiling.
- B1 obtained zero Recall@5 on these five examples. The generated text condition is an exact phrase predicate, while B1 performs semantic retrieval over the natural-language question. No baseline tuning or exact-match shortcut was added after seeing this outcome.
- B4 includes B3's exact structured match in its full union for the structured example, but not its first five text-priority positions. Its full gold coverage and Recall@5 must not be conflated.

Mean/range below are measured **uncached retrieval** times across the five-query offline run. They include lazy model/index initialization on the first query and are not steady-state performance benchmarks.

| Baseline | Mean retrieval ms | Range ms | Distinct returned IDs joined to registry |
| --- | ---: | ---: | ---: |
| B1 | 1400.78 | 426.41–5016.70 | 21 |
| B2 | 5619.05 | 2253.61–10759.14 | 21 |
| B3 | 11.30 | 0.26–43.31 | 6 |
| B4 | 7091.11 | 3462.02–11719.70 | 46 |

The actual API smoke used one common TGS validation query for all four baselines: `generated:69a22c3b4989b07ed6c3:normal`. It requires an exact abstract phrase, author affiliation with University of Insubria, recorded paper rank <= 20071 and journal namespace. None of the retrieved candidate sets supported the complete question; all four models returned an empty set. Answer set accuracy/F1 were therefore zero against its nonempty gold set. This is an observed baseline limitation, not an execution/parsing failure. No IDs were hallucinated or gold answers leaked into the prompt.

| Baseline | Retrieval ms | Generation ms | Input tokens | Output tokens | Answer IDs | Errors |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| B1 | 3939.74 | 8050.92 | 1675 | 64 | [] | 0 |
| B2 | 6926.84 | 700.62 | 941 | 55 | [] | 0 |
| B3 | 47.85 | 808.53 | 673 | 54 | [] | 0 |
| B4 | 57.90 | 770.51 | 2625 | 73 | [] | 0 |

B4's API run reused all three immutable source caches populated by B1–B3. Its retrieval-call count is zero while source_invocations is three; that cached latency must not be compared to the preceding uncached source timings. Each API run made exactly one generation call. These 24 executions are illustrative infrastructure/baseline checks, not a full validation benchmark or scientific ranking of methods.

Machine-readable tables are `comparison.csv` and `comparison.json`, produced from raw records. `representative_results.json` includes questions, retrieved evidence, paths/plans, model explanations and available metrics. Final offline runs are under `validated/B1`–`B4`; approved API runs under `groq_smoke/B1`–`B4`. Earlier development runs are retained under `development_runs/` with their original code hashes.

## 7. Resource and cost observations

Final offline validation took 82.169 seconds across all four methods, including verification, lazy loading, queries, registry audits and resume checks. Maximum observed working set was 2,099,560,448 bytes (1.955 GiB). Process peak counters are cumulative, not independent per-baseline memory measurements. The exact flat FAISS vectors alone require 1,075,574,784 bytes in RAM; CSR stays memory-mapped and Python traversal state is explicitly bounded. DuckDB execution is capped at 512 MB.

The four approved Groq runs took 29.836 seconds end-to-end and consumed **5,914 measured input tokens and 246 measured output tokens**. No further API calls or batches ran. Monetary cost remains NULL because no explicit pricing/config source was supplied; token usage is not a claim that the calls were free.

A hypothetical full 2,721-query validation pass across four baselines would involve 10,884 generation calls and an aggregate maximum of 11,145,216 completion tokens at the current per-call cap, plus input tokens and any future separately approved retries. A crude linear extrapolation of the five uncached retrieval samples gives B1 1.06 h, B2 4.25 h, B3 0.01 h and B4 5.36 h for retrieval alone. This is a capacity illustration, not a reliable forecast: it includes cold starts and omits generation time, rate limits and query-distribution effects. `capacity_estimate.json` records assumptions. **No such batch is approved or scheduled.** A larger run requires a separate resource/pricing review and explicit approval.

## 8. External approval and credentials

Automatic approval review initially blocked the Groq action before any request was sent, requiring explicit authorization for the question/evidence payload and external destination. This was unrelated to API-token expiration. Four exact request files and source provenance were prepared locally; the user then explicitly approved those four requests. The payload-checking smoke adapter verified that transmitted messages matched the previews and used the fixed https://api.groq.com endpoint, with zero retries. All four requests succeeded, confirming the configured credentials worked for this smoke.

Only the prepared generated validation question and public STaRK-derived evidence were sent. No credentials appear in the saved request payloads or logs. No test/human-test data was executed or sent.

## 9. Limitations and discrepancies

- B2 is deliberately basic and bounded. Its lexical candidate pool can miss aliases or distant semantic entities; seed ranking uses graph labels only. High-degree expansion truncation is deterministic but can miss relevant papers. Bounds and truncation are exposed, not disguised as exhaustive graph coverage.
- B3 is a supported-clause parser, not general semantic NL-to-SQL. It cannot prove text/graph requirements and does not execute arbitrary SQL. Supported structured clauses are logged even when other modalities in a composite query are outside its scope. Unsupported intent does not trigger a full-table fallback.
- B1 semantic retrieval can underperform the generated benchmark's exact operational phrase conditions. Top-5 ceilings limit recall for large gold sets. These small validation outcomes do not establish comparative research performance.
- B4 uses source-order concatenation without cross-source answer intersection or entity-aligned reasoning. Its union can contain useful evidence outside Top-5 and still lack all constraints for a given paper. The common generator may correctly abstain, yielding low benchmark answer scores.
- The fixed character budget is a safety limit, not a tokenizer-aware optimizer. Graph stress injections remain candidate-restricted; an out-of-candidate graph distractor is skipped. Structured/text overlays remain source-specific and retain source NULLs.
- Groq seeds/temperature align requested settings, but hosted generation is not guaranteed bitwise deterministic. Only four actual generation calls were made; broader reliability, rate-limit and quality estimates are unmeasured.
- Phase 5 release gating still blocks paper-quality test/human-test work pending complete human review. Official labels remain unverified. No new human reviews or semantic label repairs were fabricated.

## 10. Phase 7 readiness and stop gate

B1–B4 now provide fixed, source-separated implementations behind the common runner, with deterministic controls, evidence caching, provenance, bounded retrieval, strict answers, measured telemetry and validation artifacts. This supplies the baseline interfaces needed for later approved context-management work. Full comparative baseline experiments remain a separate, unapproved resource decision; current smoke results should not be used as paper-quality performance claims.

**Phase 6 stops here. Phase 7 and all nine advanced research methods have not begun.**
