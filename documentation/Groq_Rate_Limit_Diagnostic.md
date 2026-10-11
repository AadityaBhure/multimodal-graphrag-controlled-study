# Groq rate-limit diagnostic

**Conclusion: `HEALTHY_NOW`.** Diagnostic performed **10 October 2026, 12:14:38–12:14:39 IST (Asia/Calcutta)**. This confirms current usability only, not unlimited quota or capacity for the full research batch.

| Check | Observed outcome |
|---|---|
| Local credential | Present; value never printed or persisted |
| Authentication / model list | HTTP **200**; `openai/gpt-oss-120b` listed |
| Tiny completion | HTTP **200**, returned model `openai/gpt-oss-120b` |
| Request | One user message `Hi`; temperature 0; low reasoning effort; **1 completion token** |
| Usage | **72 input + 1 output = 73 tokens** |
| Finish reason | `length`, expected at the deliberately minimal cap; not an API failure |
| Exception / sanitized error | **NULL / NULL**, both requests succeeded |
| Probes | One model-list GET, one completion POST; **zero retries** |

## Observed headers

Model-list response exposed only `date: Sat, 10 Oct 2026 06:44:39 GMT` among the captured date/rate-limit headers. No rate-limit or retry-after headers were present on that response.

Completion response:

| Header | Exact value |
|---|---|
| `date` | `Sat, 10 Oct 2026 06:44:39 GMT` |
| `x-ratelimit-limit-requests` | `1000` |
| `x-ratelimit-remaining-requests` | `999` |
| `x-ratelimit-reset-requests` | `1m26.4s` |
| `x-ratelimit-limit-tokens` | `8000` |
| `x-ratelimit-remaining-tokens` | `7927` |
| `x-ratelimit-reset-tokens` | `547ms` |
| `retry-after` | Not present |

No other rate-limit headers were exposed. These are point-in-time values, not current balances after this report was written.

Groq documents these request headers as **daily request limits (RPD)** and token headers as **tokens per minute (TPM)**. Organization-level limits can include separate input/output limits, but those were not exposed here. Reset durations should be used as returned; `1m26.4s` does not mean a new allocation of 1,000 requests every 86 seconds. [Official rate-limit documentation](https://console.groq.com/docs/rate-limits).

## What can be concluded about the earlier failures?

**The exact historical binding constraint cannot be recovered.** The old run retained `RateLimitError` classes but not the 429 bodies, rate-limit headers or retry-after values. It would be unsupported to label those failures as an expired key, spend exhaustion or a proven specific quota.

The most plausible explanation is **minute-based token pressure**: the previous rapid batch received responses measuring 6,970 input and 154 output tokens, while individual full-context calls can require several thousand input tokens. That pattern is consistent with the now-observed 8,000 TPM capacity. It remains an inference, not a provider-confirmed historical diagnosis.

| Possible restriction | Finding |
|---|---|
| RPM | Not exposed in this response; historical exhaustion cannot be established |
| TPM | **8,000**, with **7,927 remaining** after the tiny request; plausible prior bottleneck |
| Separate input/output minute limits | Not exposed; unknown |
| RPD | **1,000**, with **999 remaining** at observation; not exhausted then |
| TPD | Not exposed; cannot determine remaining daily tokens |
| Organization-level | Documented general rate-limit scope; exact historical binding scope not confirmed by an error body |
| Project-level | No project quota details exposed; no current block observed |
| Monthly spend/quota | Not exposed; no current blocking spend failure observed; remaining allowance unknown |
| Model-specific access/restriction | This model was listed and successfully served the tiny request; larger-call capacity remains bounded |
| Another provider restriction | No present error indicates one; historical restriction remains unconfirmed |

There is **no evidence that account/key replacement or a plan/spend change is currently required**. Waiting should address a transient minute bucket if that is the constraint; it cannot resolve a payload exceeding a single bucket's capacity, daily exhaustion, or a spend restriction. This probe cannot promise that waiting alone will make every full-context request succeed.

## Prepared Phase 8 rerun — not executed

A separate **`phase8-generation-v2-paced`** plan and five new named configs are prepared in [rerun_v2/plan.json](groq_diagnostic/rerun_v2/plan.json). The same frozen queries, evidence, implementations, prompts, model, caps and seeds are bound by checksums. Old runs, journals and configs are unchanged. New output root: `documentation/phase8_generation_v2`; new journal: `documentation/phase8_generation_v2/stage_journal`. Phase 5 will derive distinct experiment IDs from the new config identities upon execution; no executed experiment ID is claimed yet.

Budget: **at most 16 requests**, **11,560 completion tokens**. Fourteen static payloads total 185,835 characters: roughly **46,465 input tokens at four characters/token**, plus two dynamic final contexts. Including dynamic inputs and output caps gives a rough **71,000-token planning envelope**, not a tokenizer measurement or guaranteed bound. The largest static request estimates 6,550 input-plus-capped-output tokens before safety margin. Original measured usage is retained separately; no research token setting is changed.

Proposed cadence: one request in flight, **at least 90 seconds between request starts**, including an initial 90-second cooldown; approximately **24 minutes minimum** for all 16 calls. Before each dispatch, account for observed remaining tokens/reset and estimated next-request input plus the unchanged completion cap, with 25% input-estimate headroom. Wait longer when headers require it. A rough estimate cannot guarantee admission, especially if other clients share the organization. If the unchanged payload cannot fit, stop for review rather than shrink evidence or caps.

**Stop the entire rerun on its first new 429**, persisting sanitized body/headers and `retry-after`; do not issue a retry, continue downstream stages, or auto-resume ambiguous dispatches. Any later resumption must wait at least the exposed retry-after/reset window and be reviewed separately. This stricter policy prevents repeated 429 bursts.

**Recommendation:** review this diagnosis and the prepared v2 plan before authorizing execution. No Phase 8 rerun was started. **Phase 9 has not begun.**

Evidence: [sanitized diagnostic JSON](groq_diagnostic/diagnostic.json). The diagnostic verified **550 existing Phase 8 files** unchanged; no benchmark/data artifacts were accessed for writing. The local probe has an exclusive dispatch guard to prevent accidental repeated probing.
