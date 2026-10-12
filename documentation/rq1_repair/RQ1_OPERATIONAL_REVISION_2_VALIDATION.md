# RQ1 operational revision 2 — validation and re-freeze (Stage 1)

Date: 2026-10-12. Branch `wip/rq1-operational-revision-2`, rebased onto `master` (`2a7f288`). No Groq call, no generation, no test/human-test data.

## What revision 2 changes (operational only)
* Admission: pre-dispatch tokens = local o200k_harmony content tokens + 128 ≤ 8,000 (was content + 256 + 1,024). Basis: `GROQ_ADMISSION_SEMANTICS_DECISION.md` (completion cap not charged at admission). The 1,024 completion cap is still sent.
* Timing boundary: `initialise()` loads models/resources before the per-query timer; `initialisation_ms` is recorded separately.
* No change to methods, inputs, cohort, prompts, configs, model or caps.

## 1. Output equivalence — PASS
`timing_boundary_equivalence.json` (per-record evidence in `timing_equivalence/rows/`): original `system.py` @ `9e112a9` vs revision 2, same encoder/reranker, all 32 queries × 5 methods.

| Check | Result |
|---|---|
| Records compared | 160 / 160 (0 missing) |
| Context, retained IDs, evidence, ranked paper IDs, context tokens, diagnostics (excluding timing fields) | identical in all 160 |
| CM-01 internals (seeds, expansion, tree, DFS sequences, reranker triplets, scores, selection) | identical in all 32 |
| Independent reference: context SHA-256 from the pre-change `revised_capacity_audit.json` | 128 / 128 match (CM-B0, CM-B1, CM-01, CM-02) |
| CM-03 | identical old vs new with deterministic API-free TEST keywords (real keywords do not exist yet); no independent reference |

`CM01_SCIENTIFIC_OUTPUT_EQUIVALENCE = PASS` (previously NOT_RUN).

Measured with revision 2 (context_ms, median / max): CM-B0 102 / 169, CM-B1 98 / 176, CM-01 9,320 / 22,510, CM-02 20 / 218, CM-03 20,896 / 45,692 (test keywords). Initialisation outside the timer: CM-01 18.3 s, others < 0.1 s. The earlier timing-consistency finding still stands and is not changed: CM-02 edge scores and CM-03 query vectors come from staged offline inputs, while CM-01 computes its unit scores inside its timer, so latency comparisons favour CM-02/CM-03; this will be reported with the results.

## 2. Tests — PASS
Full suite: 220 passed (215 previous + 5 revision-2 tests), one existing DuckDB deprecation warning. `rev2_full_tests.xml`.

## 3. Preservation
`rev2_preservation.json` (written after this commit): Phase 5 data audit (695 payloads, MVP baseline, storage snapshot, release gate) plus git checks that, since checkpoint `159a48f`, only the revision-2 files, the plan and the decision log changed and that historical Phase 7/8, compliance-repair records, RQ1/RQ2 code, baselines, evaluation and configs are unchanged.

## 4. Re-freeze — DONE
* v1 plan archived byte-for-byte: `execution_plan_v1.json` (sha256 `5b76c347…`).
* `execution_plan.json` is now plan revision 2: same version `rq1-compliance-v1`, same 32 queries, 192 maximum calls, prompts, model and cap; adds the admission policy, overhead reserve, timing boundary, the superseded-plan hash and the equivalence-report hash; implementation hashes recomputed (10 files).
* `configs/CM-*.json`: re-saved byte-identical (write-once guard passed), so experiment identity is unchanged.
* The re-freeze only replaces a plan whose bytes equal the archived v1 copy.

## 5. Other operational change
`scripts/audit_rq1_repair_local.py` now writes `local_audit_progress_rev2.json` / `capacity_blocker_rev2.json`, so the v1 records (`local_audit_progress.json`: 64 rows under the old rule; `capacity_blocker.json`) stay unchanged.

REVISED_ADMISSION_POLICY_IMPLEMENTED = YES
RQ1_SCIENTIFIC_STATUS = INCOMPLETE (next: Stage 2, 128-record local audit)
