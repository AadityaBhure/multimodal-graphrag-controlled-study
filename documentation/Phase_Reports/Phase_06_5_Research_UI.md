# Phase 6.5 Review Report — Research UI Integration

Status: implementation and functional validation complete; awaiting user review. Phase 7 has not begun.

## Phase boundary and preservation

Approved Phase 6 was checkpointed as `a19bdd5e30e33caa7c82a8a0095dcdd1e610693e`, with a clean working tree confirmed before implementation. `baseline-mvp-v1` remains at `4592d102b363c7d55d3c85ee67efe89409ae96b5`. The separate entry point is `research_app.py`; the original `app.py` is unchanged. The final audit passed: all 695 frozen payloads (7,165,516,177 bytes), 1,159 protected Phase 6 checkpoint files, the original storage snapshot and frozen tag are unchanged. See `../phase6_5/preservation.json` for the complete audit.

## Delivered interface

| Requirement | Implementation |
| --- | --- |
| Query playground | Editable question, B1–B4 selector, four representative presets, explicit retrieval button. |
| Dataset explorer | Real title search, text/structured/canonical records joined by STaRK ID, bounded CSR neighborhoods with derived inverse labels. |
| Evidence | Expandable text, graph paths and source nodes, structured values, compiled SQL with bound parameters, paper IDs and provenance. |
| Answer generation | Explicit Groq button on a retrieved snapshot; shared generator/parser and approved settings. No generation on page load, rerun, retrieval or comparison. |
| Method comparison | Sequential independent baselines on the same question; evidence and source-order rankings displayed without score normalization or fusion. |
| Performance | Retrieval/generation latency, calls, measured tokens, context characters, evidence retained and redundancy; unavailable values remain NULL. Historical Phase 6 table is read-only. |
| Execution trace | Config/fingerprint/representation identity, query seed, source diagnostics, retrieved versus retained evidence, exact context, answers, usage/errors and downloadable JSON. |

`ResearchService` executes the existing `BaselineSystem` with the approved offline config. Generation loads the corresponding approved Groq config, reuses the exact retained snapshot context, and validates answers against retained paper IDs. Baseline code and config files are unchanged. No benchmark record or gold-answer loader is used in the interactive execution path. Explorer records cannot enter generation context.

The service serializes retrieval and maintains one active baseline store; the independent explorer uses read-only data and memory-mapped CSR without loading FAISS. Paper pages contain 20 rows; neighborhoods contain at most 25 relationships. The general graph renderer additionally rejects more than 101 nodes or 100 edges. No full-graph visualization or NetworkX graph is created.

## Representative real-data checks

These are interface integration checks, not new scientific performance estimates. Latencies are individual measured retrieval observations and include cold-load effects; cache reuse can change later timings.

| Preset | Baseline | Returned papers | Retrieval latency | Result |
| --- | --- | ---: | ---: | --- |
| Refractory materials/divertor design title | B1 | 5 | 10.420 s | Source paper 1172724 retrieved. |
| Baoji University affiliation | B2 | 5 | 5.340 s | Graph evidence and affiliation paths returned. |
| Recorded rank/year/citations/journal attributes | B3 | 1 | 0.049 s | Paper 1592956 returned with structured provenance. |
| Difficult abstract + Insubria affiliation + structured conditions | B4 | 15 | 18.976 s | All three sources returned evidence; this does not establish a successful combined answer. |

Complete paper IDs, evidence, context and diagnostics are in `../phase6_5/B1_example.json` through `B4_example.json`. The explorer smoke verified paper 1172724 joins across all three identities, displayed 20 search rows and 16 relationships, and confirmed its FAISS index was not loaded.

## Validation and resources

- Full suite: **135 passed**, one pre-existing DuckDB `fetch_record_batch` deprecation warning, 23.52 seconds.
- Ten new UI/service tests cover initial idle behavior, explicit generation, rerun safety, stale inputs, preset loading, same-query comparison, bounded explorer separation, NULL metrics, snapshot-only generation, provider setup failure, DOT escaping, and unchanged-baseline delegation/cache behavior.
- All four real-data presets passed without retrieval errors. Integration duration: **47.101 seconds**. Peak working set: **1,495,572,480 bytes** (about 1.39 GiB); final working set after closing stores: 175,878,144 bytes.
- **Zero new Groq calls**; API generation is tested with deterministic mocks. No test/human-test experiment, paid batch, advanced method, benchmark mutation or representation rebuild occurred.
- Local server health returned `ok`. A real headless Edge session rendered the interface successfully; `../phase6_5/ui_preview.png` was visually inspected. Streamlit interaction tests exercise the controls without paid requests.
- Python 3.12.14 and existing Streamlit 1.64.0 environment; no added package dependencies.

## Limitations and operation

The UI is a local inspection tool. Session history is limited to 20 runs and disappears with the session; download JSON to retain an inspection. It reuses the baseline evidence cache but does not replace the Phase 5 experiment runner, release gating or durable experiment resume. Failed or completed generation snapshots require a new retrieval before an explicit retry. Groq availability and credentials are not re-tested live in this phase.

B3 retains the approved parser's supported-language limits; B2 retains bounded traversal and no global text fallback. B4 remains simple source-separated concatenation. Ad hoc questions have no supplied gold, so accuracy/Recall@K remain NULL. No cost estimate is fabricated, and context tokens remain NULL without a configured measurement. The difficult TGS case remains a documented limitation from Phase 6, not a repaired or tuned example.

Launch instructions: `../phase6_5/Research_UI_Guide.md`. The research interface runs separately at **http://127.0.0.1:8502**. Existing Phase 0 behavior and all scientific settings remain protected. Phase 6.5 is ready for review; Phase 7 requires approval.
