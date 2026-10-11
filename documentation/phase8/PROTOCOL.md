# Phase 8 controlled fusion protocol

Approved Phase 7 checkpoint: `2600275b90c1943202004b69452f8f7dcf841aee`. No prior tracked file is changed. Phase 8 is additive under `research/rq2`, `configs/rq2`, and this review directory.

## Frozen inputs and selection

Use all 24 programmatically verified generated validation TG/TS/GS/TGS questions with normal/noisy/conflict conditions. There are six questions per modality class and eight per stress condition. Eighteen are multi-hop-2 and six single-hop. No official annotation is inferred. No test/human-test experiment is permitted.

The approved Phase 6 closeout B4 per-query evidence is reused without retrieval. Freeze the complete `EvidenceItem` fields into a `RetrievalBundle` once. B4 appended overlays after its original mixed-source list; bundle construction partitions that list into Text/Graph/Structured while preserving every source's internal order. The same bundle bytes, IDs, scores, source ranks and provenance reach every variant. Existing stress overlays are already applied and are not applied again. Default bundle timing zeros denote replay, not historical retrieval measurements; the original measured observation is preserved separately.

Canonical/alias references are read from immutable Phase 3 Parquet during input preparation, not fusion. Exact-alias lookup includes global collisions. Fusion has no database, vector index, graph store, network client, or retriever. The generation adapter may call only the shared generator when explicitly enabled.

## Fixed representation rules

All methods have a 24,000-character safety cap. Evidence is serialized atomically, with source, canonical ID, complete content/payload, provenance, and overlay origin/hash. Bulky retrieval diagnostics remain in the frozen input and execution trace rather than the LLM context. Oversize items are skipped with remaining order preserved; no facts are truncated. Retained IDs make all omissions auditable.

* CF-B0 packs Text, Graph, Structured in that order, sharing the cap.
* CF-B1 uses `TEXT EVIDENCE`, `GRAPH EVIDENCE`, `STRUCTURED EVIDENCE`; each section receives 7,999 characters, including its heading, with two separators charged globally. No unused budget redistribution.
* CF-01 resolves the primary paper/entity associated with each evidence item, rather than extracting new concepts: valid exact canonical ID, valid metadata STaRK ID, globally unique exact normalized alias, unresolved. Normalization is Unicode NFKC, casefold and whitespace collapse, matching Phase 3. No approved probabilistic resolver exists, so none is invoked. Ambiguous aliases remain unresolved. Entity groups follow first occurrence; their source evidence remains distinct with full provenance. Group headings consume the common budget. This controlled adaptation does not reproduce full KAG.
* CF-02 scores Graph/Structured payloads by `|distinct query word tokens intersect payload word tokens| / |distinct query word tokens|`; zero-overlap candidates are excluded. Unicode `\w+`, casefold, no stopword or learned weighting. Ties retain original Graph-then-Structured pool order. Select at most five structural items, then Text in original rank fills to ten items. Atomic safety packing follows selection. Every candidate has selection/retention reasons and source recorded. This is a lexical contextual selector, not SAG's original LLM selector or SQL/event index. It is frozen, not tuned using results.
* CF-03 uses CF-B1's source-specific inputs. Three independent shared-generator calls are capped at 220 completion tokens each. Their answers use the unchanged strict paper-set parser, each restricted to its source's retained papers. The final context contains source-labeled raw intermediate responses, parsed IDs, evidence IDs and provenance. The final answer may use only the union of valid intermediate answer IDs. No additional source lookup is possible. The final call uses the unchanged 1,024-token cap; all four calls use `openai/gpt-oss-120b`, temperature zero, low reasoning effort and the same deterministic query seed. No response repair or retry. Invalid intermediate output stops final generation and preserves observed usage.

CF-03 offline output has NULL final context, ranking and answer metrics. Its prepared source counts/coverage refer to intermediate inputs, not a completed fused answer. Deterministic fake generators test the real four-stage control flow without representing those outputs as scientific generation results.

## Generation and durability

Use the frozen Phase 6 `PROMPT`, `GroqGenerator`, and `parse_answer`. Only question/context/seed enter generation. Benchmark gold remains inside the Phase 5 evaluator. No pricing estimate or input token estimate is invented.

The optional small sample is selected before generated outcomes: the lexicographically first TGS normal question and its conflict pair, all five variants. Maximum 16 calls, 11,560 completion tokens. Exact static payload previews and dynamic final-context bounds are in `generation_plan.json`. This plan is not authorization.

Every live stage has a locked content-addressed journal. A dispatch marker is written before the request; a completed response and checksum are written atomically. A crash or transport failure after dispatch is ambiguous and cannot be automatically retried. Completed stages can be replayed without new API calls. Experiment call/token totals describe original logical stage usage; cache-hit counters identify replay. Unmeasurable transport usage is NULL. Query-level records, identity, code/config provenance, errors and resume remain managed by the unchanged Phase 5 runner.

## Measurement interpretation

Phase 5 answer/retrieval/context metrics are unchanged. Fusion rankings mean retained-paper order; they are not fresh retrieval rankings. Source coverage is retained item count divided by incoming item count per source; an absent source gives NULL. Within-source entity redundancy is one minus unique canonical IDs divided by retained items; empty gives NULL. Exact-evidence-ID redundancy is separately supplied by Phase 5.

Exact-ID assignment and conflict-marker retention are invariants/diagnostics, not independently annotated alignment or conflict-handling accuracy. Those accuracy metrics remain NULL. Post-hoc report-only gold coverage excluding overlay items diagnoses stress confounding; it never enters selection or prompts. Pareto tables are descriptive, conditional on metric and cost, and never select an automatic winner. Answer-quality Pareto analysis remains unavailable without generated answers.

## Primary conceptual references

The user-approved adaptations above govern this study, not claims of full reproduction: [KAG official repository](https://github.com/OpenSPG/KAG), [SAG project](https://www.sag.wiki/en/project/paper), [MegaRAG paper](https://arxiv.org/abs/2512.20626).
