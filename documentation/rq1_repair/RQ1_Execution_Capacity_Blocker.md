# RQ1 repair: provider-capacity blocker

Date: 2026-10-11. Status: **BLOCKED BEFORE REPAIR GENERATION**.

The repaired CM-01 context for `generated:5692e57aa6e252201105:conflict` cannot pass the frozen conservative dispatch policy against the last observed Groq 8,000-token limit. This is a local preflight result, not a newly received HTTP 429 or an authentication failure.

| Capacity component | Tokens |
|---|---:|
| Unchanged system/user message content, local `tiktoken-0.12.0:o200k_harmony` | 7,028 |
| Frozen completion cap | 1,024 |
| Chat-envelope reserve | 256 |
| Required reserved capacity | **8,308** |
| Last observed provider limit | **8,000** |

Even excluding the chat-envelope reserve, content plus completion allowance is 8,052. These are pre-dispatch token bounds, not measured provider usage for this request. Waiting for an ordinary reset cannot satisfy this reservation against an unchanged 8,000-token capacity. No context shortening, cap reduction, prompt change, query substitution, or parameter tuning was performed.

The exact context hash, query hash, diagnostics, memory observation and calculation are in `capacity_blocker.json`. The context SHA-256 is `9bd8fb8f9752923f3de479b554aadf53e8afc635a8748fe28cb089add486b740`. This is the first oversized repaired-method request encountered; it is **not** a claim that 8,308 is the maximum across the whole cohort. A larger quota must be followed by a complete capacity audit before dispatch.

## Completed work and checks

- All 32 eligible verified generated validation inputs staged; G/TG/GS/TGS each 8, stress conditions each 8. No test/human-test experiment.
- Additive CM-01 provenance adaptation, CM-02 repair, CM-03 repair, common adapter and durable dispatcher implemented. Historical implementations/results remain unchanged.
- 64 real-input offline checks passed: all 32 queries for each control CM-B0 and CM-B1. The subsequent CM-01 capacity check stopped the audit. CM-02 real-input audit and CM-03 keyword-dependent real-input audit remain outstanding.
- Full suite: **215 passed**, one existing DuckDB deprecation warning. See `pre_execution_full_tests.xml`.
- Preservation audit: **1,013 historical/code/config files unchanged**, 695 dataset/representation/benchmark payloads verified, frozen MVP preserved. See `pre_execution_preservation.json`.
- Environment dependency check: no broken requirements. Added local tokenizer dependency is pinned in `requirements-rq-repair.txt`.
- New configurations and code hashes frozen in `execution_plan.json`; the runner refuses dispatch without a completed 128-record deterministic offline audit.
- Parser failures now retain raw output, evidence, context and measured usage. Dispatch persistence reuses the unchanged Phase 5 flushed/atomic writer.
- Paired-analysis code and hand-computable tests prepared before outcomes. Stress variants are clustered by base query family; they are not treated as independent questions.

## API status and budget

Earlier preflight at **2026-10-11 09:57:10 +05:30** succeeded: models listing HTTP 200 and one tiny completion HTTP 200, with 72 input and 1 output token. Observed limits were 8,000 tokens and 1,000 requests; remaining 7,927 tokens and 999 requests. This established availability at that timestamp, not unlimited quota. See `provider_preflight/diagnostic.json`.

**No repaired keyword or final-answer request has been dispatched.** Planned workload remains 32 keyword + 160 final calls, maximum 196,608 completion tokens and approximately 1.15 million conservatively estimated input-content tokens. Minimum pacing duration is 4h48m, excluding additional local/provider time. Monetary cost remains NULL without an explicit pricing source. No billing or plan change was made.

## Required resolution

Provide sufficient Groq token-rate capacity for the unchanged model and payloads, then re-audit the complete cohort against the confirmed capacity. An ordinary quota reset or replacing an otherwise valid API key is not established as a solution. This report does not authorize a plan upgrade or scientific changes. It does not claim the provider itself rejected this unsent payload.

The stop follows the user's frozen adaptation §22 resource-limit exception. Implementation/experimental compliance is not certified by tests alone; the complete real-input audit, RQ1 generation/analysis, RQ1 checkpoint and subsequent RQ2 repair remain outstanding. No completion checkpoint has been claimed.

RQ1_SCIENTIFIC_STATUS = INCOMPLETE
RQ2_SCIENTIFIC_STATUS = INCOMPLETE
PHASE_9_UNBLOCKED = NO
