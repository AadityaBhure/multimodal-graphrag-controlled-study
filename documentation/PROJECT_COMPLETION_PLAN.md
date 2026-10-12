# Project completion plan (approved 2026-10-12)

Order: RQ1 → RQ2 → RQ1/RQ2 closeout → RQ3 (resume) → RQ4 → locked final test → results/paper.
Every stage ends with a stop for human review. Historical Phase 7/8 results stay preserved; canonical results are added next to them.

| Stage | Work | Groq | Gate |
|---|---|---|---|
| 0 | Housekeeping: commit Phase 9 lite edits, log the re-sequencing, record superseded status records, isolate the demo from research artifacts | none | log entry |
| 1 | RQ1-A: validate `wip/rq1-operational-revision-2` (output equivalence 32 × 5, full tests, preservation), re-freeze as execution plan v2, checkpoint on master | none | equivalence report |
| 2 | RQ1-B: finish the 128-record real-input audit (CM-01/02/03), recompute capacity incl. CM-03 dynamic sizes, re-confirm cohort | none | audit summary |
| 3 | RQ1-C: durable run, 32 keyword + 160 final calls (~0.6 M tokens, ~3 days) | ~3 days | completion count |
| 4 | RQ1-D: clustered paired statistics, Holm, Pareto, stress strata, failure taxonomy, canonical RQ1 report | none | RQ1 approval |
| 5 | RQ2-A: audit CF-B0/B1/CF-01 resolver; build canonical CF-02 (one selector call) and CF-03 (per-source partial answers + fusion); tests; freeze plan | none | code/plan review |
| 6 | RQ2-B: supportability classification of the 24 bundles before any call; primary run; separate fusion-isolation study (≥12 evidence-complete queries, never merged); canonical RQ2 report | ~2–4 days (estimate after stage 5) | RQ2 approval |
| 7 | RQ1/RQ2 closeout: cross-RQ consistency, preservation, candidates carried to RQ4 | none | closeout |
| 8 | RQ3 resume: rebase `research/phase9-rq3`, finish graph pool, labels, AR-01 training, AR-02 calibration, freeze, 56 × 5 run, analysis, report | ~7 days | RQ3 approval |
| 9 | RQ4 / Phase 10 integration, ablations, integrated UI | TBD | Phase 10 review |
| 10 | Phase 11 locked final test — needs the 2,801 human test/human-test reviews + leakage attestation (start reviews early, in parallel) | TBD | release attestation |
| 11 | Phase 12 results and paper | none | — |

Groq stages share one 200 k tokens/day quota and run sequentially; offline work for the next stage runs during quota waits. CPU-heavy jobs (CM-03 diffusion, graph pool) are not run concurrently.

## Superseded status records (kept unchanged as historical files)

These files are covered by preservation records and are not edited. Their current status is:

* `documentation/rq1_repair/execution_status.json` (`blocked_before_dispatch`, 8,308 reserved tokens): superseded by `documentation/rq1_repair/GROQ_ADMISSION_SEMANTICS_DECISION.md` — the completion cap is not charged at admission; all 160 static requests fit under `content + 128 ≤ 8,000`. RQ1 is incomplete, not blocked; it resumes at Stage 1.
* `documentation/Phase_Reports/Phase_09_Agentic_Retrieval_Review.md` (`NOT_STARTED_MISSING_PHASE1D_SPECIFICATION`): superseded by `documentation/phase9/PHASE9_SPEC_CONSISTENCY_AUDIT.md` and `PHASE9_METHOD_IMPLEMENTATION_REPORT.md` on branch `research/phase9-rq3` — implementation complete, no scientific run, no frozen plan. Paused until Stage 8.
* `CLAUDE_MASTER_HANDOFF_MULTIMODAL_GRAPHRAG.md` §22 ("Phase 9 NOT STARTED") — untracked handoff note, superseded as above.
