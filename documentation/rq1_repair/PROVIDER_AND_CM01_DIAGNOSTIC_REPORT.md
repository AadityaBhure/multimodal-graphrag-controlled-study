# Provider accounting diagnostic, static capacity audit and CM-01 performance audit

Date: 2026-10-11. Scope of this step: checkpoint the repair, characterise Groq token accounting with tiny non-research calls, audit static capacity, profile CM-01. **No repaired research request was sent. No scientific code, config, prompt, cap, model, cohort or plan file was changed.** Stopped for human review.

## 1. Executive summary

1. The repair is now checkpointed: `9e112a9b74c5bbef5fdfee09a6951c4f983f609d` (parent `34c8503…` = PRE-repair). 215 tests pass; preservation audit passes.
2. **The 71-second CM-01 figure is not a per-query cost.** Re-running the unchanged CM-01 on the blocked query reproduces the exact blocked context (SHA-256 `9bd8fb8f…`) in **4.0–4.5 s** (three runs). The 71 s was the first CM-01 call of a process, which lazily loads the 2.26 GB BGE reranker inside the timed region (15.5 s with a warm file cache here; the extra time in the original run is not reproducible and is most plausibly cold disk / contention — I cannot prove which).
3. **Provider overhead is a constant 102 tokens, not 256.** Provider `prompt_tokens` − local `o200k_harmony` content tokens = **102 in 12 of 12** research-shaped requests (10 historical Phase 8 v2 + 2 new), for local sizes 1,072–5,175 tokens. Without `response_format` it was 74 (Test A).
4. **Prompt caching is not confirmed and cannot rescue the oversized requests.** The new identical-prefix pair reported no `cached_tokens`; in the 6 historical responses that did report `cached_tokens = 256` (5 rebuilt exactly, residual +13…+326), the minute-bucket consumption was still the full total. The real common prefix for the blocked Graph-only requests is only 185–208 local tokens (≤ 1 provider cache block of 256).
5. **Static audit: 8 of 128 constructible final-answer requests exceed the frozen 8,000 admission rule — all CM-01, all Graph-only (two base query families × 4 stress variants).** Worst: `generated:6f03efc321dca0622d99:conflict`, 7,277 content tokens → reservation 8,557 (+557). With the *measured* 102-token overhead instead of 256 the same eight are still over (+154 … +403). They are over even with **no** envelope at all (content + 1,024 > 8,000). No reserve policy and no caching can fit them *if the provider charges the 1,024 completion cap at admission*. That one premise is **unmeasured**; the authorised design (tiny caps) could not test it.
6. Daily budget: ≈ 0.57–0.60 M provider tokens in total ⇒ about 3 days (2.9–3.1) at the stated 200,000 TPD even if everything became admissible.

Recommendation: **Case C under the frozen conservative rule (`GROQ_FREE_TIER_INSUFFICIENT_FOR_UNCHANGED_PAYLOAD`), with one explicit, cheap, human-approvable probe that could reverse it (§20–22).**

## 2. Repository checkpoint created

| | |
|---|---|
| Commit | `9e112a9b74c5bbef5fdfee09a6951c4f983f609d`, `checkpoint: rq1-rq2 compliance repair pre-generation` |
| Parent | `34c85038636b1223d1664042e0ce0f0640403dd0` (PRE-repair) |
| Time | 2026-10-11 12:24:15 +05:30 |
| Detail | `REPAIR_PRE_GENERATION_CHECKPOINT.md` |

## 3. Files included / excluded

84 files committed (code under `research/repair/`, five repair scripts, four test files, `requirements-rq-repair.txt`, frozen inputs/configs/plan, compliance matrix and `compliance_repair/`, capacity-blocker evidence, provider preflight, inventory/test/preservation records). Excluded and left untracked: `CLAUDE_MASTER_HANDOFF_MULTIMODAL_GRAPHRAG.md`, `tmp/pdfs/qafd_equations.png`. `.env` and all other ignored material untouched; no secret-like pattern in any staged file. Inventory with SHA-256: `pre_checkpoint_inventory.json`, `PRE_CHECKPOINT_INVENTORY.md`.

**Created after the checkpoint and intentionally NOT committed** (pending your approval): `provider_accounting_model_before_diagnostic.md`, `provider_diagnostic.json`, `provider_diagnostic/`, `cm01_profile.json`, `cm01_unit_score_reuse_check.json`, `current_capacity_audit.{csv,json}`, this report, `REPAIR_PRE_GENERATION_CHECKPOINT.md`, and the three diagnostic scripts (`scripts/diagnose_groq_accounting.py`, `scripts/diagnose_static_capacity.py`, `scripts/profile_cm01.py`). None is part of `execution_plan.json`; every hash-frozen file was re-verified unchanged afterwards.

## 4. Pre-diagnostic test status

`.venv\Scripts\python.exe -m pytest -p no:cacheprovider`: **215 passed, 1 warning** (known DuckDB deprecation). Equals the recorded baseline. `pre_checkpoint_full_tests.xml`.

## 5. Preservation status

PASS (`pre_checkpoint_preservation.json`): 695 payloads; MVP tag `baseline-mvp-v1` → `4592d102…`; 54 baseline + 4 storage files; 2,874 tracked historical/code/config files re-hashed with 0 differences (312 Phase 7, 641 Phase 8/8-v2); `research/agentic/*` still placeholders; no repair `runs/`, `dispatch/`, `keywords/`, `local_audit.json`; zero repair API requests; test/human-test untouched. Re-checked after all diagnostics: tracked tree unmodified, `execution_plan.json` code/config hashes all match.

## 6. Current token-admission policy

`reserved = Σ len(o200k_harmony.encode(message.content)) + 256 + max_completion_tokens(=1024) ≤ min(8000, x-ratelimit-limit-tokens)` (`research/repair/dispatch.py`). Local content only; excludes the provider's chat template and `response_format`. The 256 has no recorded measurement or citation (arbitrary conservative margin). Full model: `provider_accounting_model_before_diagnostic.md`.

## 7. Test A results (2 messages, no `response_format`, cap 1)

Local 7 tokens (6 + 1); provider `prompt_tokens` **81** ⇒ difference **74**; `completion_tokens` 1; total 82; no cached/reasoning details; `finish_reason=length` (expected). Header: remaining 7,918 of 8,000 ⇒ 82 consumed = provider total exactly.

## 8. Test B results (research-shaped: system 1,437 + user 4 local tokens, `json_object`, cap 48)

Local **1,441**; provider prompt **1,543** ⇒ difference **102**; completion 25 (11 reasoning); total 1,568; `{"ok":true}`. Header: remaining 6,456 ⇒ 1,544 consumed. B also served as the cache prime (C1); a separate C1 call was not spent.

## 9. Test C (cache) results — C2 repeat of B's prefix, different 4-token suffix

Local 1,441; provider prompt **1,543** (same); completion 42 (28 reasoning); total 1,585. **`prompt_tokens_details` absent ⇒ no `cached_tokens` reported.** Provider-side `prompt_time` 0.072 s vs 0.208 s for B (a hint of prefix reuse, but only a hint — not provider-reported cache accounting). Header: remaining 6,432 ⇒ 1,568 consumed ≈ B's 1,544 (+24): **no rate-limit discount.** Classification: **`CACHE_NOT_CONFIRMED`**. Not used in admission.

## 10. Actual common-prefix analysis

Computed with the pinned tokenizer on the 128 constructible final payloads (CM-B0, CM-B1, CM-01, CM-02), `current_capacity_audit.json → common_prefix_by_query`:

| Query class | system tokens | user common prefix | local common prefix |
|---|---:|---:|---:|
| Graph-only (blocked family; e.g. `5692e5…:conflict`) | 156 | 29–52 (31 for the blocked query) | **185–208** (**187** for the blocked query) |
| Mixed (Text/Structured pass-through precedes the Graph part) | 156 | up to ~1,700 | up to 1,879 |

For Graph-only queries the user message diverges right after `EVIDENCE\n[GRAPH]\n{"…` (node vs unit serialization), so the cacheable prefix is the system prompt + question header only. Provider-side the prefix additionally contains ≤102 template tokens (split unknown). Observed caching granularity is 256 tokens (every `cached_tokens` seen was exactly 256). So at most **one** block (256) could ever be cached for the oversized Graph-only requests. Prefix hash for the diagnostic synthetic pair: `6828b018…` (`provider_diagnostic.json`); per-query real-prefix hashes are in the audit JSON. No message reordering was attempted or recommended.

## 11. Provider-token-accounting model (empirical)

* `provider_prompt_tokens = local_content_tokens + C`, with **C = 102** for every research-shaped request (2 messages + `json_object`, 12/12), **C = 74** without `response_format` (1 request). C is independent of size over 1,072–5,175 local tokens ⇒ a constant, not a ratio. Hypothesis (unproven): `json_object` mode injects ~28 template tokens.
* Rate-limit bucket consumption in the headers ≈ provider `total_tokens` (prompt + actual completion), residual −24…+326 in 13 matched observations (unexplained positive residuals; no sign of cache discount).
* Reasoning tokens are inside `completion_tokens`.
* **Not measured:** whether admission charges `prompt + max_completion_tokens` (assumed by the dispatcher) or `prompt + actual output`; whether cached tokens are discounted at admission; the 200,000 TPD limit (not exposed in headers).

## 12. Current 256-reserve analysis

1. Chosen as an unmeasured, conservative design margin (no source recorded).
2. It was meant to cover unknown chat-template overhead.
3. The provider's `prompt_tokens` **does** include template overhead (102) that the local count omits.
4. `tiktoken o200k_harmony` undercounts the provider by exactly that constant, never by a proportion.
5. Approximately constant (74 without `response_format`, 102 with).
6. Maximum observed positive undercount in A/B/C: **102**; across all 12 research-shaped observations: **102**.
7. A margin covering the observation plus a stated allowance: 102 + 26 (25 % of the observed constant) = **128**. That allowance is my choice, not a measurement.

## 13. Blocked-request recalculation (`5692e5…:conflict`, CM-01)

| | Tokens |
|---|---:|
| A. current: 7,028 + 1,024 + 256 | **8,308** (+308) |
| B. content + cap, no reserve | **8,052** (+52) |
| C. measured: 7,028 + 102 (provider prompt 7,130) + 1,024 | **8,154** (+154) |
| D. verified reusable cache | **0** confirmed (≤256 hypothetically, and not discounted in observed accounting) |
| E. effective demand if cap charged at admission | **8,154**; if cap not charged: 7,130 + actual output (≈25–140 observed ⇒ ≈7.2 k) |

Even granting a full 256-token cache discount, the worst of the eight requests (7,277 + 102 + 1,024 = 8,403) would still be 8,147. Caching alone cannot fit all eight.

## 14. Full static RQ1 capacity audit

`current_capacity_audit.csv/json` — 128 constructible final requests (CM-B0, CM-B1, CM-01, CM-02 × 32), 32 keyword requests, 32 CM-03 final requests marked `DYNAMIC_NOT_YET_CONSTRUCTABLE` (sound upper bound only: fixed parts + fractional-knapsack bound on the graph budget).

* Max reservation (current rule): **8,557** — CM-01, `6f03efc321dca0622d99:conflict` (Graph-only).
* Over 8,000: **8**. Between 7,500 and 8,000: **4** (all CM-B0 of family `6f03ef…`, 7,664–7,845). Below 7,500: **116**.
* Headroom (8,000 − reservation): min −557, p10 584, p25 2,580, median 3,726, p75 5,564, p90 5,993, max 6,221. Only 4 requests have 0–500 tokens of headroom.
* Per method, over 8,000: CM-01 8/32, CM-B0 0/32 (max 7,845), CM-B1 0/32 (max 4,058), CM-02 0/32 (max 4,447). By modality for CM-01: Graph-only max 8,557; TG 6,258; TGS 6,132; GS 5,425.
* Keyword requests: max reservation 1,407 — all fit.
* **CM-03 final calls (32) all depend on keyword generation**; their upper bounds exceed 8,000 for the same 8 Graph-only queries (8,299–8,504), so up to 8 more may be oversized; unknowable until keywords exist.
* Daily budget estimate: ≈ 399 k (static finals incl. 102 overhead) + 6 k (keywords) + ≈ 138–164 k (CM-03 finals) + ≈ 29–58 k completion ⇒ **0.57–0.60 M tokens ⇒ about 3 days (2.9–3.1) at 200 k TPD** (assumes TPD counts prompt + completion).

## 15. Requests that remain oversized

All Graph-only, all CM-01 (exceed by current rule / by measured-overhead rule): `6f03ef…` conflict +557/+403, normal +503/+349, noisy +497/+343, unanswerable +467/+313; `5692e5…` unanswerable +448/+294, noisy +364/+210, normal +364/+210, conflict +308/+154. Under *no* envelope at all (content + 1,024) all 8 are still over. These are two of the eight base query families, so they cannot be skipped or substituted.

## 16. CM-01 performance profile (`cm01_profile.json`, blocked query, unchanged code)

Per execute (3 runs, identical context hash; `all_runs_identical_context = true`, `context_matches_capacity_blocker = true`): wall **4.45 s cold-start-after-load, 4.07 s, 4.00 s**.

| Component (warm run) | Seconds | Share |
|---|---:|---:|
| BGE forward pass (1 tree, truncated 4,964→512 tokens) | 2.21 | ≈ 55 % |
| MiniLM embedding of 342 units (12 ONNX batches of ≤32) | 1.50 | ≈ 38 % |
| Reference CM-B0 context (for the baseline-size metric) | 0.07 | 2 % |
| tokenisation, evidence build, canonical units (×2), forest, DFS, packing, pydantic, tiktoken | ≈ 0.2 | ≈ 5 % |

One-time costs: imports 0.54 s; load of all 32 staged inputs (68 MB JSON) 1.58 s; MiniLM ONNX session 0.76 s; BGE construction incl. SHA-256 of 2.26 GB weights 2.5 s; **BGE weight/tokenizer load 15.5 s** (lazy: occurs inside the first CM-01 `execute`). Peak working set 3.5 GB. 342 units → 101 expanded → forest of 96 edges → a single DFS tree. Disk/mmap: none per query (graph evidence is in the staged JSON).

## 17. Top runtime contributors

BGE forward (scientific) > MiniLM unit embedding (partly duplicate, below) > one-time BGE load (measurement artefact, below).

## 18. Pure engineering optimisation opportunities

| # | Item | Class | Saving |
|---|---|---|---|
| 1 | Untimed explicit `reranker.load()` before the first timed `execute` | B | removes 15–70 s one-off contamination of `context_management_ms` for the first CM-01 record of a run |
| 2 | Reuse the staged `unit_scores` inside `organize()` instead of re-embedding units (they are computed with the same function in `prepare_rq1_repair.py`) | B | ≈ 1.5 s of ≈ 4 s per query |
| 3 | Memoise unit embeddings across the 4 stress variants of a family (~342 of 342 units shared) | C | up to ≈ 1.1 s per extra variant |
| 4 | Remove duplicate `canonical_units`/`evidence`/reference-context computation | B | ≈ 0.1 s |
| 5 | BGE forward pass | A (scientific) | none allowed |
| 6 | MiniLM batch composition, BGE threads/batching/max length | A (scientific) | none allowed |

## 19. Is each optimisation scientifically neutral?

1. **Neutral by construction.** Weights, inputs and order are unchanged; only *when* loading happens. Latency hygiene improves.
2. **Verified bit-identical**: for all 32 staged queries, recomputing with the same encoder and function reproduces `unit_scores` exactly (`cm01_unit_score_reuse_check.json`, `all_bit_identical = true`, max |Δ| = 0). Would preserve candidate IDs, seeds, scores, forest, DFS, reranker inputs, context hash. Requires code change + re-freeze.
3. **Not guaranteed byte-identical**: ONNX results can differ in the last bit when the batch composition (padding length) differs. Requires an equivalence test before any use; I do not recommend it (saving is small).
4. Neutral, negligible gain; not worth a re-freeze.
5–6. **Not authorised** (approximate search, smaller reranker, shorter input, different truncation, fewer trees, reduced context, changed scoring).

Since a full 32-query CM-01 pass costs ≈ 2 min while the dispatcher spaces calls 90 s apart, CM-01 runtime is **not** a practical blocker. Case E applies only to item 1 (latency hygiene), not to feasibility.

## 20. Recommended operational path

1. Do **not** adopt caching in admission (`CACHE_NOT_CONFIRMED`; cannot fit all eight even in the best hypothetical case).
2. Do **not** change the 256 reserve as a fix: replacing it by a measured formula would be more principled but resolves nothing for the eight requests. Candidate measured policies, for reference (all scientific effect: NONE; all unchanged for the 8 oversized requests):

| Policy | Formula | Basis | Margin | Blocked request | Worst request | Fits 8,000? |
|---|---|---|---|---:|---:|---|
| P0 current | content + 256 + 1,024 | arbitrary | 256 | 8,308 | 8,557 | no |
| P1 measured | content + 102 + 1,024 | constant observed 12/12 | none | 8,154 | 8,403 | no |
| P2 measured + allowance | content + 128 + 1,024 | 102 + 25 % | 26 | 8,180 | 8,429 | no |
| P3 *only if the cap is not charged at admission* | content + 128 + max observed output (≤ ~300) | needs probe | 26 | ≈ 7.5 k | ≈ 7.7 k | yes (conditional) |

3. Run the **one admission-semantics probe** below (needs your approval; it needs a large `max_completion_tokens`, which this instruction excluded). If the cap is not charged, the unchanged requests fit and only a re-frozen dispatcher admission rule is needed. If it is charged, Case C stands: stop under frozen §22.
4. Independently of the probe, adopt engineering item 1 (and optionally 2) with a re-freeze.

Probe design (1 call, synthetic only): send Test B's 1,543-token prompt with `max_completion_tokens = 7,000` (requested total 8,543 > 8,000). HTTP 200 ⇒ the cap is not charged at admission (the 8 requests then need ≈ 7.1–7.4 k prompt tokens: they fit). HTTP 429 "requested > limit" ⇒ cap is charged.

## 21. Remaining blockers

* Admission semantics of `max_completion_tokens` unmeasured (decisive).
* 8 required CM-01 requests (+ up to 8 CM-03) exceed 8,000 under the frozen conservative rule, unchangeable by any authorised means.
* CM-03 keyword generation required before its 32 finals can be audited.
* 200 k TPD ⇒ about 3 days (2.9–3.1) of paced execution at minimum.
* 128-record offline audit (CM-02, CM-03 real-input) still incomplete in `local_audit.json`; the new static audit covers CM-B0/B1/CM-01/CM-02 payload sizes but is not a substitute.
* CRLF/`core.autocrlf` caveat for any fresh checkout (see checkpoint note).

## 22. Exact decisions requiring human approval

1. Authorise the single admission-semantics probe (synthetic; 1 call; may return 429)? — or authorise another route (§below).
2. If the cap is not charged: approve an admission-rule revision (measured overhead + stated margin; cap no longer an admission term) and a re-freeze of `execution_plan.json`.
3. If the cap is charged: choose among (a) stay stopped per §22; (b) provider switch to a host of the same open weights (adds a backend variable; needs your explicit approval and documentation); (c) paid Groq tier; (d) changing the 1,024 completion cap — this is a generation parameter, prohibited without your approval (historical outputs used only 25–140 tokens, but that is an observation, not authorisation).
4. Approve engineering items 1 (and optionally 2) with re-freeze, or defer.
5. Whether to commit the uncommitted diagnostic artefacts and the two untracked files.

## Final status

REPAIR_CHECKPOINT_CREATED = YES
REPAIR_CHECKPOINT_SHA = 9e112a9b74c5bbef5fdfee09a6951c4f983f609d

FULL_TEST_SUITE = PASS
PRESERVATION_AUDIT = PASS

PROVIDER_DIAGNOSTIC_CALLS = 3
PROVIDER_AUTH = PASS

CACHE_CONFIRMED = NO
CACHEABLE_COMMON_PREFIX_TOKENS = 187

CURRENT_RESERVE_TOKENS = 256
MEASURED_PROVIDER_OVERHEAD = 102 (74 without response_format)
RESERVE_POLICY_CHANGE_RECOMMENDED = NO

BLOCKED_REQUEST_CURRENT_RESERVATION = 8308
BLOCKED_REQUEST_MEASURED_EFFECTIVE_REQUIREMENT = 8154 (if completion cap is charged at admission; about 7.2k if not — unmeasured)
BLOCKED_REQUEST_CAN_FIT_8000_UNCHANGED = INCONCLUSIVE

STATIC_CAPACITY_AUDIT_COMPLETE = YES
OVERSIZED_REQUIRED_REQUESTS_FOUND = 8

CM01_PROFILE_COMPLETE = YES
CM01_PRIMARY_RUNTIME_BOTTLENECK = BGE cross-encoder forward pass (~2.2 s of ~4 s per query); the 71 s was a one-time lazy BGE model load, not per-query cost
BYTE_IDENTICAL_OPTIMIZATION_AVAILABLE = YES

RQ1_SCIENTIFIC_STATUS = INCOMPLETE
RQ2_SCIENTIFIC_STATUS = INCOMPLETE
PHASE_9_UNBLOCKED = NO

STOP FOR HUMAN REVIEW.
