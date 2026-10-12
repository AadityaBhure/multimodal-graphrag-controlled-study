# RQ1 operational revision 3 — call counting and daily token pause

Date: 2026-10-12. Approved by the user after the Stage 2 audit. No Groq call made.

## Problem found in Stage 2
* Groq exposes the per-minute token limit (8,000) and the per-day request limit (1,000) in response headers, but not the 200,000 tokens/day limit. The RQ1 run needs about 0.6 M tokens, so under revision 2 it would certainly receive daily-limit HTTP 429 responses.
* The plan names its cap `maximum_successful_calls = 192`, but the revision-2 dispatcher counted every attempt. The run needs exactly 192 successful calls, so the first 429 would have made completion impossible ("Approved request maximum reached").

## Change (`research/repair/dispatch.py`)
1. The 192 maximum counts successful calls only. A rate-limited attempt (HTTP 429: the provider refused before running the model, no output) does not consume it; it is resent later as the byte-identical payload (same stage identity = hash of stage + payload). Rate-limited attempts have their own bounded allowance (20); failed or ambiguous dispatches still stop for human review and are never retried.
2. A local rolling 24-hour token ledger. Before each request: if tokens charged in the last 24 h + (content + 128 + full 1,024 cap) would exceed 190,000, the run pauses cleanly without sending and reports when it can resume. Each completed call is charged max(provider usage total, observed minute-bucket debit), so the provider's unexplained extra debit is included.
3. Every attempt record now also stores `daily_window_tokens_before` and `daily_ledger_tokens`; all attempts, including refused ones, stay in `dispatch/attempts/`.

## Scientific impact: none
Plan revision 3 vs revision 2 (`execution_plan_v2.json`): identical cohort (32 queries), configs (byte-identical hashes), prompts, model, temperature, reasoning effort, seed policy, completion cap, admission rule, timing boundary and equivalence report. Only the implementation hashes of `research/repair/dispatch.py` and `scripts/run_rq1_repair.py` changed. Tests prove the sent payload and its stage identity are byte-for-byte the revision-2 ones.

Known limitation (unchanged by this revision): the run spans about 3 days; the provider does not guarantee identical outputs across days even at temperature 0 with a fixed seed. Every call's timestamp is recorded. Correction (2026-10-12): the frozen runner executes methods one after another (CM-03 keywords, then CM-B0, CM-B1, CM-01, CM-02, CM-03 for all 32 queries each), not interleaved per query, so different methods may run on different days; any provider drift would then be confounded with method and must be reported as a limitation.

## Validation
* Tests: 226 passed (6 new: byte-identical payload/identity, 429 does not consume a successful call and is resent identically, bounded 429 allowance, daily pause and resume after the window, ledger uses the larger observed debit, constants). `rev3_full_tests.xml`.
* Plan: v2 archived byte-for-byte as `execution_plan_v2.json`; `execution_plan.json` is plan revision 3 with the chain of superseded plans; line endings pinned in `.gitattributes`.
* Preservation: `rev2_preservation.json` re-run after this commit.

The ledger sees only this run's calls. Other use of the same Groq key (demo, other experiments) is invisible to it, so nothing else should use the key while RQ1 runs; any resulting 429 is absorbed by the allowance.
