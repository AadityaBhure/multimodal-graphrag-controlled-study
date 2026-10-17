# RQ4 — integrated system design (frozen 2026-10-17, before any RQ2 / RQ3 outcome is analysed)

Decision (user, 2026-10-17): option C — one integrated system; context management fixed to **CM-B1** now. Priority is completing the study, not maximal quality. Validation only, on the RQ3 cohort (28 queries = 14 families × normal/noisy; `SCOPE_REVISION_2026-10-15.json`).

## Pipeline (one system, `INT-1`)
1. **Retrieval control (AR)** — the RQ3 policy selected by rule R-AR below runs exactly as frozen in Phase 9 (same tools, prompts, caps, AR-01/AR-02 artifacts). Its accumulated evidence memory is the integrated system's evidence. Controller-internal calls (AR-01 controller, AR-02 evaluator, AR-03 agent/validator/commentor and its candidate answers) are part of the AR stage.
2. **Context management (CM-B1)** — applied to the Graph evidence only, at evidence-item level: keep the graph items of the 5 best-ranked papers (retriever rank order) with their paths; Text and Structured evidence pass through unchanged (as in RQ1's fixed pass-through).
3. **Fusion (CF)** — the RQ2 method selected by rule R-CF below fuses the Text / CM-B1 Graph / Structured items exactly as frozen in RQ2 (24,000-character budget, same prompts and caps; CF-02 selector / CF-03 per-source calls included).
4. **Answer** — the CF method's final answer (shared answer contract, `openai/gpt-oss-120b`, temperature 0, low reasoning, 1,024 cap, per-query seed). This replaces the AR policy's own final answer.

## Component selection rules (fixed now, applied mechanically after each study)
* **R-AR**: among the RQ3 Pareto set (answer F1, source F1 ↑; tokens, intrinsic latency ↓), pick the policy with the highest mean answer F1; ties → fewer mean total tokens → policy order AR-B1, AR-01, AR-02, AR-03, AR-B0.
* **R-CF**: among the RQ2 Pareto set (answer F1 ↑; input tokens, intrinsic latency ↓), pick the method with the highest mean answer F1; ties → fewer mean total tokens → order CF-B1, CF-01, CF-02, CF-03, CF-B0.
* No component is re-chosen after viewing RQ4 outcomes.

## Comparison (no extra Groq calls for baselines)
* `INT-1` vs **AR-B0** (RQ3 always-all control, same 28 queries, already run) and vs the **selected AR policy alone** (RQ3 record, same 28 queries). Same family-clustered statistics as RQ3 (bootstrap, exact sign-flip over 14 families, Holm over the 2 pairs; primary answer F1; secondary tokens, latency, source F1).
* B4 (Phase 6) is reported descriptively only where frozen records exist for these queries (different downstream budget).

## Execution
Same operational stack: content+128 admission, rolling 24 h ledger shared with the other studies, query-major provider order not needed (single system), replay-only runner, durable stages; frozen plan before any call. Estimated ≈ 0.3 M tokens (≈ 1.7 days).

## Code-freeze constraint
Integration code lives on branch `research/rq4-integration` and is merged to `master` only after the RQ2 run has finished (running studies refuse to resume if `research/` source changes).
