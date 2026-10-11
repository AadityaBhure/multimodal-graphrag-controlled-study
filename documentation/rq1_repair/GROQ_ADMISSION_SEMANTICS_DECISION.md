# Groq admission-semantics decision (RQ1 operational revision 2) — PARTIAL, paused

Status: the probe is done and decisive. The operational code revision is **written but not validated or re-frozen**; the work was paused by the user's schedule change to Phase 9 / RQ3. The unvalidated code lives only on branch `wip/rq1-operational-revision-2`, not on `master`; `execution_plan.json` on `master` is the unchanged v1 plan.

## 1. Purpose
Decide whether Groq charges `max_completion_tokens` at admission, because 8 required CM-01 requests exceed 8,000 only if it does.

## 2. Pre-probe provider state
Last provider call (diagnostic C2) was ~11 minutes earlier; its response showed `x-ratelimit-reset-tokens` 11.76 s. The bucket refills 8,000/min, so it was full by the documented rule. Groq exposes remaining tokens only on responses; no extra call was spent. Record: `provider_diagnostic/admission_probe_pre_dispatch.json`.

## 3. Probe payload
Synthetic Test B payload (system ~1,437 filler tokens + 4-token suffix, `json_object`, `reasoning_effort=low`, temperature 0, seed 42), **`max_completion_tokens = 7000`**. No benchmark content. Provider prompt expected 1,543 ⇒ requested total 8,543 > 8,000.

## 4–7. Result
HTTP **200**, `finish_reason=stop`, content `{"ok":true}`. Usage: prompt 1,543, completion 25 (11 reasoning), total 1,568. Headers: limit 8,000; remaining 6,005; reset 14.962 s; requests 999/1000. Record: `provider_diagnostic/call_04_admission_probe.json`.

## 8. Conclusion
`MAX_COMPLETION_CAP_CHARGED_AT_ADMISSION = NO` (n = 1 probe, bucket full). A request whose prompt + cap (8,543) exceeds the 8,000 TPM limit was admitted. Output tokens are not free: the bucket debit after the response was 1,995, i.e. 427 above the provider's `total_tokens` (1,568) — an unexplained extra debit that appears larger with a larger cap (cap 48: −24; cap 1,024: −6…+326; cap 7,000: +427).

## 9. Scientific implications
None. The 1,024-token cap, prompts, contexts, cohort and model are unchanged. The 8 "oversized" CM-01 requests are admissible; no truncation, skipping or substitution is needed.

## 10. Operational implications
The old rule (`content + 256 + 1,024 ≤ 8,000`) was too conservative. Not tested by the probe: a request whose *actual* output pushes its total above the bucket (realistic outputs are 25–142 tokens, so the worst static request needs ≈ 7.4–7.6 k).

## 11. Revised admission policy (proposed; implemented only on the WIP branch)
`pre-dispatch = local o200k_harmony content tokens + 128 ≤ 8,000`; 128 = 102 measured provider-minus-local overhead (12/12 research-shaped requests) + 26 stated allowance (25 %). The 1,024 cap is still sent. Actual debit is observed per response from headers and gates the next call; 90 s start spacing exceeds the worst-case refill time (66 s).

## 12. Revised static capacity audit
`revised_capacity_audit.csv/json`: all 160 statically constructable requests (128 finals + 32 keyword) **fit**; maximum pre-dispatch requirement **7,405** (CM-01 `6f03efc3…:conflict`); minimum headroom 595. The 32 CM-03 final requests are dynamic; their sound upper bounds also fit (max 7,352) but CM-03 is not cleared. About 0.57–0.60 M tokens in total ⇒ ~3 days at 200 k TPD.

## 13–17. Timing boundary, equivalence, tests, preservation, re-freeze — NOT COMPLETE
* Timing-boundary code (`initialise()` outside the per-query timer; `initialisation_ms` recorded separately) is on `wip/rq1-operational-revision-2`; 27 targeted tests passed there.
* The 32-query × 5-method original-vs-new equivalence run (`scripts/validate_timing_boundary_equivalence.py`) had not finished when work paused (CM-03 diffusion with test keywords is very slow). `CM01_SCIENTIFIC_OUTPUT_EQUIVALENCE = NOT_RUN`.
* Re-freeze of `execution_plan.json`, new operational checkpoint and the full regression run for that revision: **not done**.
* Timing-boundary consistency finding for the human: CM-02's query-specific `edge_scores` and CM-03's `query_vector` are read from staged offline inputs, whereas CM-01 recomputes its query-specific unit scores inside its timer; current latency comparison therefore favours CM-02/CM-03. Not changed.
* Unit-score reuse for CM-01: `NOT_AUTHORISED`.

## 18–19. Remaining blockers / next action
RQ1/RQ2 repair is paused by user decision. To resume: validate the WIP revision (equivalence, tests, preservation), re-freeze with a versioned plan, commit, then continue to the 128-record local audit and CM-03 keyword stage.

REVISED_ADMISSION_POLICY_IMPLEMENTED = NO (WIP branch only)
RQ1_SCIENTIFIC_STATUS = INCOMPLETE
RQ2_SCIENTIFIC_STATUS = INCOMPLETE
PHASE_9_UNBLOCKED = NO (superseded by the user's schedule change; see Phase 9 work)
