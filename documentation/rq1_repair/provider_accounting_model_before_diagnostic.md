# Provider token-accounting model — written BEFORE any diagnostic API call

Date: 2026-10-11. Code state: repair checkpoint `9e112a9b74c5bbef5fdfee09a6951c4f983f609d` (parent `34c8503` = PRE-repair). No provider call had been made by this diagnostic when this file was written. All numbers below come from existing local artifacts (code, frozen records, and the already-recorded Phase 8 v2 Groq responses). Nothing here changes any scientific payload.

## 1. How the current admission equation is computed (code facts)

`research/repair/dispatch.py::Dispatcher.call` (frozen in `execution_plan.json`, SHA-256 `c18748aec9fa…`):

```
tokens   = sum(len(tiktoken.get_encoding('o200k_harmony').encode(m['content'], disallowed_special=()))
                for m in payload['messages'])          # system + user message CONTENT only
reserved = tokens + 256 + cap                           # cap = max_completion_tokens (1024 for final and keyword calls)
limit    = min(8000, int(headers['x-ratelimit-limit-tokens']))   # hard-capped at 8000 even if the provider reports more
if reserved > limit: raise Paused('... cannot repair by waiting')
```

The same formula is duplicated in `scripts/audit_rq1_repair_local.py` (`PROMPT` + user message, `+256+1024`) and in `scripts/run_rq1_repair.py::execute` for the CM-03 pre-check.

| Quantity | Local definition | Includes |
|---|---|---|
| local content tokens | `o200k_harmony` BPE of the two message strings | system text, user text (question + evidence). **Excludes** chat/role template tokens, the provider's default system block, `response_format`, and `reasoning_effort` text, if any is injected. |
| system-message tokens | 156 (the frozen final-answer `PROMPT`) | constant for every final call |
| user-message tokens | `QUESTION\n` + question + `\n\nEVIDENCE\n` + context | varies per query/method |
| schema/format text | not counted | `response_format={'type':'json_object'}` is a request parameter, not a message |
| chat-envelope reserve | constant **256** | an engineering margin (see §3) |
| completion allowance | `max_completion_tokens` = 1024 | counted at its full cap, not at expected usage |
| provider `prompt_tokens` / `total_tokens` / reasoning / cached | recorded after the call from `result.usage` (`input_tokens`, `output_tokens`); reasoning and `prompt_tokens_details.cached_tokens` are **not** captured by the dispatcher | |

## 2. Empirical evidence already on disk (no new API use)

`documentation/phase8_generation_v2/http_dispatches/01…16.json` hold provider `usage` and rate-limit headers for 16 paced research-shaped Groq requests (2 messages, `json_object`, `reasoning_effort=low`, `max_completion_tokens=1024`). I rebuilt the exact payload for the 10 requests whose records carry the full context, confirmed each rebuilt payload SHA-256 equals the recorded `payload_sha256`, and compared with the pinned local tokenizer (`scratchpad/historical_accounting.py`, reproduced into `provider_diagnostic.json`):

* `provider prompt_tokens − local content tokens = 102` for **all 10** requests (local content 1,072–5,175 tokens). The difference is exactly constant, not proportional to size.
* The earlier one-message tiny request (`"Hi"`, no system message) returned 72 provider prompt tokens, consistent with a fixed provider template of ~71 tokens plus ~31 extra tokens when a system (developer) message is present.
* `usage.prompt_tokens_details.cached_tokens` appeared in 6 of the 16 responses, always exactly **256** (never another value), without any deliberate priming. The other 10 responses carried no cached-token field. Caching is automatic, best-effort and in 256-token blocks.
* Rate-limit header accounting (bucket 8,000, refilled between calls): `8000 − x-ratelimit-remaining-tokens` is within [−6, +326] of `total_tokens` for **all** requests, **including the 5 matched requests with `cached_tokens = 256`** (their residuals were +13…+326, never ≈ −256). So the cached 256 tokens were **still charged** against the minute bucket in the header accounting. The positive residuals up to +326 are unexplained (refill during the ~1 s request would bias the other way).
* Reasoning tokens are included in `completion_tokens` (`completion_tokens_details.reasoning_tokens`), they are not additional.

## 3. Origin of the 256 reserve

I found no measurement, library constant, or provider document behind it. It appears first in `documentation/rq1_repair/Implementation_Decisions.md` as "measured content + 256 chat-envelope reserve + unchanged completion cap", replacing the earlier Phase 8 v2 heuristic (`ceil(chars/4) × 1.25 + cap`). It is therefore classified **intentionally conservative, arbitrary margin** (not empirical). The only recorded constants nearby are the provider's cache-block size (256) and the measured provider-vs-local gap (102); neither is cited in the decision text.

## 4. What this file does NOT establish (open before the diagnostic)

1. Whether Groq's **pre-admission** check charges `prompt + max_completion_tokens` (the dispatcher assumes yes) or `prompt + expected output`. No existing artifact discriminates these.
2. Whether `cached_tokens` is excluded from the **pre-admission** check (the post-call header accounting says it is not excluded).
3. Whether the 102-token gap is the same for a payload with different message count or no `response_format`.
4. Whether anything beyond the 8,000/min bucket (e.g. the 200,000/day token limit) is enforced per request; daily token usage is not exposed in any header.

## 5. Diagnostic plan that follows (separate operational identity)

Identity `groq-accounting-diagnostic-v1`, stored under `documentation/rq1_repair/provider_diagnostic/`, never read by the RQ1 runner or analysis. At most three provider completions (limit allowed: four; no retries, no research content): A minimal two-message request; B a deterministic synthetic ~1.6k-token static-prefix request that also acts as the cache prime (C1); C2 the same prefix with a different tiny suffix. These test items 3 and 2 only through the post-call usage/header accounting. Item 1 cannot be answered inside the authorized three-test design, because every authorized call keeps a tiny completion cap.
