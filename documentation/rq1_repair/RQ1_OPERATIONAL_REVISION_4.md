# RQ1 operational revision 4 — query-major provider order (interleaving)

Date: 2026-10-12. Approved by the user ("option B", scientific quality to be preserved). No Groq call made.

## Why
The frozen runner executes one method for all 32 queries before the next. At ~190k tokens/day the run spans about three days, so different methods would reach the provider on different days and any provider drift would be confounded with method.

## Change
* `research/repair/schedule.py`: query-major order (all five methods for query 1, then query 2, …; queries sorted as the runner sorts them) and a resumable prefetch loop.
* `scripts/run_rq1_repair.py --execute`: stage A executes the unchanged frozen systems in that order with the runner's own seed (`seed_everything(query_seed)`), question and overlay; the dispatcher stores every provider response durably by payload identity. Stage B runs the unchanged Phase 5 runner per method exactly as before.
* `research/repair/dispatch.py`: `replay_only` mode for stage B. A payload without a completed stored response stops the run (it is never sent), so every recorded experiment payload is provably the one that reached the provider.

## What is unchanged (scientific quality)
* Payloads: question, context, prompt, model, temperature 0, low reasoning effort, per-query seed and 1,024 cap — the same frozen systems build them. Plan v4's scientific fields (cohort, configs, prompts, model, caps, call counts) are identical to the original v1 plan.
* Records, experiment identity and metrics come from the unchanged runner. Analysed latency is `intrinsic_total_ms = context_ms (measured in stage B by the runner) + generation_ms (provider latency recorded at the original call)`. The runner's wall-clock `total_ms` was already not an analysed metric (it included up to 90 s pacing per call); under replay it excludes the provider wait.
* Call budget: still 32 keyword + 160 final calls; replay adds none.

## Evidence
* Offline end-to-end check with the REAL frozen systems, inputs, encoder, reranker, seeds, overlays and the unchanged runner, fake provider (no network): `interleaving_offline_check.json` — 3 queries × 5 methods: 15 stage-A calls in verified query-major order, 15 runner records, **0 extra calls and 0 payload mismatches** in replay-only mode. (CM-03 used API-free test keywords; the harness reproduces the execute() stage A/B logic.)
* Tests: 230 passed (4 new: order, resumable prefetch, pause/resume, replay-only returns stored responses and stops on any payload change). `rev4_full_tests.xml`.
* Plan: v3 archived as `execution_plan_v3.json`; plan revision 4 changes only implementation hashes (`dispatch.py`, `schedule.py`, `run_rq1_repair.py`) and revision notes.

Resume behaviour: after a daily pause, rerunning `--execute` repeats the cheap keyword check (stored), recomputes the CM-03 local capacity check, skips completed stage-A pairs and continues.
