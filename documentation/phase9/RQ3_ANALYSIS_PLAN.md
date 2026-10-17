# RQ3 analysis plan (frozen 2026-10-17, before any RQ3 record is analysed)

Applies to the frozen Phase 9 plan (`execution_plan.json`, 28-query cohort = 14 base families × normal/noisy). Metric definitions are those in `PHASE9_SPEC_CONSISTENCY_AUDIT.md` and `research/agentic/analysis.py`; this document only fixes which comparisons are tested and how latency is measured under the replay protocol. Implemented by `scripts/report_phase9.py`.

## Comparisons
* Policies: AR-B0 (always all), AR-B1 (rule router), AR-01 (Adaptive-RAG), AR-02 (CRAG), AR-03 (AGENT-G).
* Pre-specified pairs (7): AR-01, AR-02, AR-03 each vs AR-B0 and vs AR-B1; AR-B1 vs AR-B0.
* Statistical unit: base family (14). Paired per-query deltas; family-clustered bootstrap 95 % CI (10,000 replicates, seed 42); exact two-sided sign-flip test over the 14 family sums; Holm correction across the 7 pairs, separately per metric.
* **Primary metric: answer F1.** Secondary (same pairs, Holm per metric): source-selection F1, unnecessary-retrieval rate, stopping accuracy, retrieval calls, total tokens, intrinsic latency.
* A difference is called significant only if Holm-adjusted p < 0.05. No winner is declared otherwise.

## Descriptive
* Per-policy means of all frozen metrics (answer F1/EM, recall@5, source F1/precision/recall/exact, unnecessary retrieval, required-source miss, stopping accuracy, premature stop, over-retrieval, max-step exhaustion, retrieval calls, LLM calls, tokens, intrinsic latency).
* Strata: stress (normal, noisy) and modality class (T, G, S, TG, TS, GS, TGS; 2 families each).
* Pareto set: maximise answer F1 and source F1; minimise total tokens and intrinsic latency.
* Failure taxonomy (`failure_labels`) counts per policy.

## Latency under replay
Records are written by the unchanged runner replaying stored responses, so runner wall-clock time excludes provider and retrieval time. Analysed latency is therefore **intrinsic_ms = recorded retrieval latency + recorded provider (LLM) latency + local compute measured during replay** (`timings_ms.retrieval + timings_ms.llm_intrinsic + total_latency_ms − provider_wait`), which equals the latency a single live execution would have, excluding rate-limit waiting.

## Recorded adaptation (found while validating on smoke records)
`failure_labels` reads `tool_call['detail']['plan']`, a field the policy trace does not record (it records the retriever `status`; the unit-test fixture had the field). The report supplies `detail.plan = None` exactly for the three structured-parser statuses that return no plan (`rejected_sql_language`, `unsupported_no_structured_filter`, `unsupported_structured_disjunction`), so the frozen taxonomy definition is applied as written. The frozen module is not edited (its hash is part of the execution plan).

## Not done
No re-running, re-thresholding, re-training or prompt change after viewing outcomes; test / human-test never used.
