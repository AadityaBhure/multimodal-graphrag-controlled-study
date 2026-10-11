# Phase 9 specification consistency audit

Branch `research/phase9-rq3` (from `159a48f`, the RQ1/RQ2 diagnostics preservation checkpoint). Date 2026-10-11.

Sources read in full: `Phase1D_Exact_Implementation_Specifications_9_Methods.docx` §6, §7, §8, §9 (SHA-256 `55d89906…`, text extract `compliance_repair/phase1d_extracted.txt` lines 300–474), `Codex_Full_Project_Implementation_Roadmap.docx` Phase 9, and the **active** addendum `documentation/Phase9_Frozen_Settings_Addendum.md` (SHA-256 `14b40e90…`, byte-identical to `specifications/phase9/revision_2/…`; revision 1 `b94fbd14…` is superseded and kept only for history).

Authority order applied: Phase 1D > deferred global choices > roadmap > approved Phase 0–6 contracts > addendum (only where Phase 1D is silent) > historical reports.

Classes: **C** CONSISTENT · **O** PHASE1D_OVERRIDES_ADDENDUM · **F** ADDENDUM_FILLS_UNSPECIFIED_DETAIL · **U** UNRESOLVED_RESEARCH_MEANING_CONFLICT.

## Result

**No U items.** One historical conflict (AR-01 subquery-failure fallback) was verified as already corrected in the active addendum. Six interpretations (marked ⚑) are documented below; none changes the research question, and each is resolved deterministically by the authority order or fixed as a documented engineering default before any validation outcome exists. A human may veto any ⚑ item before the primary run.

## RQ3 shared frame

| Rule | Phase 1D | Addendum / roadmap / prompt | Class |
|---|---|---|---|
| Variable under study | when/which source, retries, correction, stopping | same | C |
| Fixed | retrievers, context policy "fixed per-source budget", source-separated concatenation, generator, answer prompt | "fixed source-separated serialization … common 24,000-character cap"; roadmap "simple deterministic fusion/context" | C |
| Downstream stack used here | tool outputs → fixed per-source budget → source-separated context (Text→Graph→Structured) → shared generator | B4's `build_context` rule applied **per source with a fixed 8,000-character budget** (= 24,000 ÷ 3), so a source's serialization is identical whatever other sources were called; ≤ 24,000 total | F ⚑1 |
| No RQ1/RQ2 winner used | forbidden ("may not use a stronger fusion method") | same | C |
| Retrievers | one identical implementation for all AR variants (frozen B1/B2/B3) | same; addendum "must not change B1/B2/B3" | C |
| Test/human-test | no leakage | forbidden throughout | C |
| Gold at inference | validator cannot access gold | same; oracle source labels evaluation-only | C |

⚑1: Phase 1D says "fixed per-source budget" without a number. 8,000 chars/source reproduces B4 exactly for the three-source case (AR-B0) and keeps per-source evidence invariant across policies. Alternative (equal shares over active sources, as in the RQ1 pass-through) would make a source's text depend on the policy, confounding RQ3.

## AR-B0, AR-B1

| Rule | Source | Class |
|---|---|---|
| AR-B0 always calls Text+Graph+Structured, no routing | roadmap; prompt §8 | C (Phase 1D silent) |
| Fixed order Text→Graph→Structured | prompt; addendum §3.4 / Phase 1D CF order | F |
| AR-B1 deterministic cue router, no LLM, no learning, default Text, source order Text→Graph→Structured, retrieves every routed source once then stops | addendum §1; roadmap "route by explicit rules"; Phase 1D defines only the "shared rule router" role | F |
| Shared router used by AR-01 (B,C) and AR-02 (initial source, AMBIGUOUS order) | Phase 1D + addendum | C |
| Rule table frozen, no tuning | addendum §1 | C |

## AR-01

| Rule | Phase 1D | Addendum | Class |
|---|---|---|---|
| Classifier / labels / input | t5-base; A/B/C; raw question; AdamW; seed 42 | same | C |
| Epochs | "training epochs by dev loss" | max 10, patience 2, lr 3e-5, wd 0.01, src 256 / tgt 2 tokens, no label smoothing/balancing | F |
| Label rule | run A/B/C on train/dev queries, cheapest strategy meeting a *pre-registered* criterion, else C | criterion = `gold_paper_coverage == 1.0` of a retrieval-only oracle (A succeeds only for empty gold; B = router's first source; C = ≤3 sources with the raw query); label = cheapest success, else C | F ⚑2 |
| Data | train/dev only, no test | official train + generated train, deterministic 90/10 by SHA-256(query_id); 56-query primary cohort, official validation, test, human-test excluded | F ⚑3 |
| A | no retrieval, generator gets query only | same | C |
| B | router picks ONE source, one call | router's first source | C |
| C | ≤3 retrieval steps; per step: subquery → router source → retrieve → append non-duplicate → sufficiency stop | step 1 raw query + first router source; controller JSON `{sufficient,next_subquery,reason}` after every retrieval except the last; gpt-oss-120b, T=0, low effort, cap 128; fallback to first unqueried in T→G→S | F |
| **Subquery generation failure** | "stop retrieval and generate from accumulated evidence" | revision 2: one schema repair, then "immediately stop further retrieval, generate the final answer from the evidence accumulated so far … do not choose another unqueried source" | **C (verified; revision 1 conflicted and is superseded)** |
| Invalid classifier output | route B, `fallback='single_step'` | silent | C (Phase 1D applies) |
| Max retrieval calls | 3 | 3 | C |

⚑2: the C-label oracle uses the raw query over up to three sources, whereas inference-time C uses controller-written subqueries; labels are therefore a deterministic proxy, a limitation to be reported (label success of C is not needed: if B fails the label is C regardless).
⚑3: the addendum fixes a query-ID hash split. Official queries are independent. The 56 generated *train* queries (14 base families × 4 stress variants) can straddle the 90/10 boundary; the number of straddling families will be measured and reported (≤ 0.7 % of the pool). I keep the frozen rule (changing it needs human approval) rather than regrouping.

## AR-02

| Rule | Phase 1D | Addendum | Class |
|---|---|---|---|
| Evaluator | `cross-encoder/ms-marco-MiniLM-L-6-v2`, local, score (query, evidence); Platt on validation | revision pinned; pair max 512; Platt on the 10 % dev partition, lbfgs, C=1, balanced, max_iter 1000, state 42 | F ⚑4 |
| Aggregation GOOD/BAD/AMBIGUOUS | `max≥UPPER` GOOD; `max≤LOWER and all≤LOWER` BAD; else AMBIGUOUS | same; empty evidence BAD | C |
| Thresholds | grids LOWER {.20…​.40}, UPPER {.60…​.80}, LOWER<UPPER, macro-F1, frozen before evaluation | same + tie-breaks (error, margin, lower LOWER, lower UPPER); freeze before the 56-query run | F |
| Initial source | shared router, one retrieval | same | C |
| GOOD | stop | — | C |
| AMBIGUOUS | highest-priority unqueried source; merge; re-evaluate | adds fallback T→G→S order | F |
| BAD | all remaining unqueried sources in parallel; merge; re-evaluate | deterministic T→G→S merge order | F |
| **Correction rounds** | config row "max correction rounds = 2"; step 7 reads "Maximum correction rounds = 2 total evaluations after the first retrieval" | "maximum two correction rounds beyond the initial retrieval" | C ⚑5 |
| Still BAD after all sources | `status='insufficient_evidence'` | silent | C |
| Evaluator failure | classify AMBIGUOUS | same | C |
| Web / strip refinement | disabled | disabled | C |

⚑4: Phase 1D says "validation split"; the addendum operationalises it as the dev partition carved from training, which is stricter (never touches validation/test). Accepted.
⚑5: step 7's sentence is ambiguous (could mean one correction + one re-evaluation). Resolved by the explicit config row "max correction rounds = 2", the roadmap ("max 2 correction rounds") and the addendum: **up to two correction rounds, each followed by one re-evaluation (≤ 3 evaluations including the initial)**. With three sources two rounds can exhaust them. Flagged for veto.

Engineering defaults (no research-meaning change; documented, deterministic): the evaluator's text for an evidence item is a fixed rendering — Text: stored title + abstract; Graph: title plus verbalised relation path with node labels; Structured: `field: value` lines. The same rendering is used for calibration and inference. When the final state is BAD with no sources left the answer is still generated (status recorded as `insufficient_evidence`).

## AR-03

| Rule | Phase 1D | Addendum | Class |
|---|---|---|---|
| AgentAction schema | 9 fields, source ∈ text/graph/structured/stop, reason_code ∈ textual/relational/numeric/hybrid/correction | exactly the Phase 1D schema | C |
| One tool per iteration, T = 4 | yes | yes | C |
| Loop | Agent → tool → dedup → candidate → validator → (reject) commentor | same; counts, caps (agent 256, validator 256, commentor 128, repair 128), prompts, who sees what | F |
| Validator schema | `accept`, `error_type` enum, `unsupported_claims` | same | C |
| Malformed JSON | repair once; if repair fails the iteration is counted and the shared router supplies the next source | same + at most one tool, `schema_repair_failed=true`; successful repair does not consume an iteration | C |
| Loop guard | same normalized action twice without new evidence → forced feedback; again → stop insufficient | normalization defined | C |
| After iteration 4 | "return INSUFFICIENT_EVIDENCE / best supported partial answer, depending on evaluation protocol" | choose INSUFFICIENT_EVIDENCE, no unsupported partial | F |
| Structured tool | read-only, shared SQL adapter, errors → `structured_query_error` | same | C |
| Commentor | cannot add evidence | same; not called after accept or after iteration 4 | C |

⚑6 (engineering defaults for cases both documents leave open; rare failure paths): (a) `INSUFFICIENT_EVIDENCE` is recorded as status and answered as the empty paper set, matching the final prompt's "if no supported paper can be identified, return an empty array"; (b) Agent `stop` → generate from evidence memory and return that answer without a validator call (Phase 1D: "break and generate"); (c) validator JSON unrepairable → treated as a reject with `error_type='insufficient_evidence'` and a logged `validator_schema_failure`; (d) commentor JSON unrepairable → the fixed feedback string used by the loop guard; (e) the Agent emitting an unknown source or an invalid action counts as a malformed output and goes through the repair/router path.

## Training, calibration and tuning discipline

| Rule | Class |
|---|---|
| No tuning of AR-B1, AR-03 prompts, thresholds or labels after viewing the 56-query cohort | C |
| Search spaces: only LOWER/UPPER grids; AR-01 epochs by dev loss; AR-03 none | C (Phase 1D §7) |
| Eligible pools: official train + generated train only; dev = 10 % hash partition | F (addendum) — prompt §14 asks for family-level splitting only "if not already frozen"; it is frozen, see ⚑3 |

## Evaluation-only definitions frozen here (before any outcome exists)

* Oracle source set R from the verified modality label (T→{text}, G→{graph}, S→{structured}, TG, TS, GS, TGS) — never exposed to any policy.
* `covered_step` = the first retrieval call (counting every retrieval call in order) after which the retrieved sources ⊇ R, else none.
* **`stopping_accuracy` = 1 iff `covered_step` exists and the total number of retrieval calls equals `covered_step`** (the policy stopped as soon as the required evidence was in hand); else 0.
* `premature_stop` = R never covered and the policy stopped for a non-budget reason (class A, router exhausted, sufficiency/GOOD/accept); `max_step_exhaustion` = R never covered and the stop reason was a step/iteration/loop-guard limit; `over_retrieval` = R covered but more calls were made than `covered_step`.
* Source metrics: exact source-set accuracy, precision, recall, F1 of the set of called sources against R; unnecessary-retrieval rate = |S∖R| / |S| (0 when S is empty); required-source miss rate = |R∖S| / |R|.
* Primary cohort: the verified generated validation set — 56 queries = 14 independent base families × 4 stress variants (7 modality classes × 2 families); statistics resample the 14 families.

## Verdict

PHASE9_SPEC_AUDIT = PASS (no unresolved research-meaning conflict). Implementation proceeds under the active addendum (revision 2) with the ⚑ items above as the recorded interpretations.
