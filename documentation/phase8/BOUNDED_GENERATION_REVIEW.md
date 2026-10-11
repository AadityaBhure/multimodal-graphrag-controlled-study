# Phase 8 — bounded diagnostic generation sample

The explicitly approved frozen plan was executed once on 10 October 2026. Only `generated:69a22c3b4989b07ed6c3:normal` and its `:conflict` pair were used, across CF-B0, CF-B1, CF-01, CF-02 and CF-03. No retries, repair calls, prompt/cap changes, tuning, new retrieval or benchmark edits occurred. This is **not benchmark-wide evidence**.

## Execution outcome

**11 Groq requests were attempted, below the authorized maximum of 16.** Two returned valid JSON; nine raised `RateLimitError`. The frozen runner sorts query IDs, so conflict executes before normal. There was one final answer (CF-B0 conflict) and one intermediate answer (CF-03 conflict Text). CF-03 stops on a failed intermediate, leaving five planned downstream calls unexecuted. No additional calls will be made under this completed run.

The preserved provider exception class establishes a rate-limit failure, not an expired API key. The frozen adapter did not retain the provider response body/headers, so the exact rate-limit dimension and reset time are unavailable. Dispatch markers for failed calls remain unchanged; they are not safe-to-retry markers. The per-query records associate those dispatches with their `RateLimitError` outcomes.

| Method | Requests | Valid provider responses | Rate-limit errors | Known input tokens | Known output tokens |
|---|---:|---:|---:|---:|---:|
| CF-B0 | 2 | 1 | 1 | 5,165 | 100 |
| CF-B1 | 2 | 0 | 2 | 0* | 0* |
| CF-01 | 2 | 0 | 2 | 0* | 0* |
| CF-02 | 2 | 0 | 2 | 0* | 0* |
| CF-03 | 3 | 1 intermediate | 2 | 1,805 | 54 |
| Total | **11** | **2** | **9** | **6,970 known** | **154 known** |

*Zero known tokens means no completed response supplied a usage measurement. It does **not** assert zero provider accounting for failed calls. Failed-call input/output tokens and full per-method usage totals remain NULL. The exact request counts above come from the journal, while the frozen runner's incomplete observation fields remain NULL. Known measured generation time totals 2,073.6854 ms across the two completed responses; complete batch generation latency is unavailable.

## Answers and normal/conflict comparison

Both queries have gold paper set `{1258814}`. The one completed final answer, CF-B0 conflict, returned `[]`:

> No paper in the provided evidence meets all required conditions; none have both the specified abstract wording and a recorded author affiliation with University of Insubria while also satisfying the rank and venue constraints.

| Method / condition | Set accuracy | Precision | Recall | F1 | Answerability correctness |
|---|---:|---:|---:|---:|---:|
| CF-B0 conflict | 0 | 0 | 0 | 0 | 0 |
| CF-B0 normal | NULL | NULL | NULL | NULL | NULL |
| CF-B1 normal and conflict | NULL | NULL | NULL | NULL | NULL |
| CF-01 normal and conflict | NULL | NULL | NULL | NULL | NULL |
| CF-02 normal and conflict | NULL | NULL | NULL | NULL | NULL |
| CF-03 normal and conflict | NULL | NULL | NULL | NULL | NULL |

Exact Match is also zero for CF-B0 conflict. Its measured generation latency is **1,411.0393 ms**, total query latency **1,420.2797 ms**, and context size **20,550 characters**. The remaining failed final answers are unavailable, not incorrect empty sets. There is no completed normal final answer, so a paired normal-versus-conflict effect cannot be estimated.

## CF-03 intermediate behavior and errors

CF-03 conflict's Text intermediate returned:

```json
{"answer_ids":[],"explanation":"No provided abstracts contain the required phrases, and no other evidence meets all conditions."}
```

It parsed successfully, used 1,805 input / 54 output tokens and took **662.6461 ms**. The following Graph call raised `RateLimitError`. Structured and final fusion calls were not made. CF-03 normal's first Text call also raised `RateLimitError`; its other three stages were not called.

Both received responses were valid JSON accepted by the unchanged parser. **Zero observed malformed outputs or parser failures** occurred. No truncation was observed in the received text, and usage was below the respective caps. The frozen adapter does not retain `finish_reason`, so an explicit provider-level truncation audit is unavailable. No synthetic intermediate was substituted for a missing response.

CF-03's original failed-run `context` and context-related metrics contain its **prepared source inputs**, because execution failed before final-context construction. They are not a generated late-fusion context. The diagnostic export therefore sets `final_context_characters=NULL`; raw records are preserved unchanged. Its conflict total latency was 738.0233 ms and normal total latency 68.6290 ms, both partial/failure execution measurements.

## Conflict handling and evidence limits

The normal frozen bundle contains no evidence for gold paper 1258814. The conflict bundle adds only `structured:paper:1258814:overlay`, with conflicting rank 20,072 against the requested upper bound 20,071. It does not add the canonical paper's text/graph support. Thus the completed empty answer is wrong against benchmark gold, but the cached inputs cannot support the full gold conjunction.

CF-B0 did not explicitly identify/adjudicate the conflict. With no completed normal counterpart and no canonical supporting evidence for the gold paper, **correct conflict handling cannot be established**. Conflict-handling correctness remains NULL. It would be misleading to attribute the zero answer score solely to fusion or to claim that abstention proves successful conflict resolution.

## Trade-offs and interpretation

The ordinary machine-generated cohort/Pareto exports were recomputed. Only CF-B0 has an available final answer score, so any mechanical frontier containing it is a **single-observation, incomplete-data artifact**, not a comparative Pareto advantage. The other methods cannot be ranked against it on answer quality, calls, tokens or generation latency. Fast rate-limit rejection is not an efficiency benefit.

The offline context-size comparisons still describe the 24-query frozen-bundle study. The live sample does not establish whether entity alignment, structural selection or late fusion improves reasoning. No final RQ2 winner is selected, and no inference is generalized to the benchmark.

## Artifacts and review gate

* `generation/*/records.jsonl`: unchanged runner records, metrics, errors and provenance.
* `generation_journal/*.json`: durable stage dispatches and complete responses.
* `bounded_generation_diagnostics.csv` / `.json`: per-query answer metrics, attempted requests, known partial usage, latency and final-context availability.
* `bounded_generation_stage_outputs.json`: both raw responses and measured usage.
* `bounded_generation_call_audit.json`: request budget, failure and partial-usage accounting.
* `generation_authorization_audit.json`: preflight validation of all 14 prepared static payloads and the 459-file prior review package.
* `preservation.json`: post-execution frozen-evidence, metric and protected-artifact audit.

The approved bounded execution is finished, including its failures. No retry or replacement batch has been scheduled. **Stop for review; Phase 9 has not begun.**
