# RQ2 analysis plan (frozen 2026-10-17, before any RQ2 canonical outcome exists)

Applies to `execution_plan.json` (rq2-canonical-v1): 24 frozen bundles = 8 base families × normal/noisy/conflict; methods CF-B0, CF-B1, CF-01, CF-02, CF-03. Implemented by `scripts/report_rq2_canonical.py`.

* Pre-specified pairs (7): CF-01, CF-02, CF-03 each vs CF-B0 and vs CF-B1; CF-B1 vs CF-B0.
* Statistical unit: base family (8). Paired per-bundle deltas; family-clustered bootstrap 95 % CI (10,000 replicates, seed 42); exact two-sided sign-flip test over the 8 family sums (smallest attainable p = 2/256); Holm across the 7 pairs, per metric. Significant only if Holm p < 0.05.
* **Primary metric: answer F1.** Secondary: exact match, input tokens, output tokens, LLM calls, intrinsic latency.
* Descriptive per method: answer F1/EM, precision, recall, MRR, recall@5, context characters, source coverage (text/graph/structured), retained-overlay count, LLM calls, tokens, intrinsic latency; CF-01 resolution counts, CF-02 selector fallbacks / invalid IDs, CF-03 per-source statuses and fusion retries.
* Strata (frozen before calls in `supportability.json`): FULLY / PARTIALLY / UNSUPPORTABLE; also modality (TG, TS, GS, TGS) and stress (normal, noisy, conflict). UNSUPPORTABLE bundles measure correct abstention only and are reported separately.
* Pareto set: maximise answer F1; minimise input tokens and intrinsic latency.
* Latency under replay: intrinsic_ms = `fusion_ms` (measured during replay) + recorded provider generation latency (`observation.generation_ms`); rate-limit waiting excluded.
* No re-running, prompt or setting change after viewing outcomes; test / human-test never used.
