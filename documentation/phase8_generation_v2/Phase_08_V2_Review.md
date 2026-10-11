# Phase 8 v2 — bounded diagnostic generation sample

This is a two-query paired diagnostic, not benchmark-wide evidence. The original failed run is unchanged. Phase 9 has not begun.

Execution status: **FINISHED**. Requests: **16 / 16 maximum**. Final answers available: **10 / 10**.
Known usage: **47,277 input / 1,238 output tokens**. Provider error responses: **0**. Provider `length` finish reasons: **[]**.

| Method | Answers | Set accuracy | Precision | Recall | F1 | Exact Match | Answerability | Calls | Input tokens | Output tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CF-B0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2 | 10170 | 242 |
| CF-B1 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2 | 7208 | 193 |
| CF-01 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2 | 10387 | 203 |
| CF-02 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2 | 8566 | 140 |
| CF-03 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 8 | 10946 | 460 |

## Normal versus conflict outcomes

| Method | Condition | Answer IDs | F1 | API generation ms | Total ms including pacing | Final context chars | Errors |
|---|---|---|---:|---:|---:|---:|---|
| CF-B0 | conflict | () | 0.0 | 1257.7187 | 90683.5297 | 20550.0 |  |
| CF-B0 | normal | () | 0.0 | 1112.4022 | 89833.5473 | 20044.0 |  |
| CF-B1 | conflict | () | 0.0 | 866.0708 | 89625.0316 | 13283.0 |  |
| CF-B1 | normal | () | 0.0 | 924.8557 | 90051.0909 | 12777.0 |  |
| CF-01 | conflict | () | 0.0 | 1117.0352 | 90027.7095 | 20886.0 |  |
| CF-01 | normal | () | 0.0 | 945.3175 | 89822.7775 | 20359.0 |  |
| CF-02 | conflict | () | 0.0 | 883.2307 | 89793.0952 | 17421.0 |  |
| CF-02 | normal | () | 0.0 | 1039.4007 | 90140.0725 | 17421.0 |  |
| CF-03 | conflict | () | 0.0 | 3171.1366 | 359795.3284 | 3160.0 |  |
| CF-03 | normal | () | 0.0 | 2603.3558 | 359761.205 | 2931.0 |  |

## Interpretation and conflict handling

Both frozen questions have gold set {1258814}. The normal bundle lacks this paper; the conflict bundle adds only its tagged conflicting-rank overlay, not the canonical Text/Graph support needed for the full conjunction. Do not equate paper-ID presence with sufficient evidence. Empty answers score zero against the nonempty gold set but may reflect missing upstream support. Fusion was not allowed to repair this with new retrieval.
Conflict-handling accuracy remains NULL: no independent conflict-action annotation exists, and canonical support is absent. Inspect explanations below for explicit conflict recognition; recognition alone does not prove a correct grounded answer.
Observed explanations do not explicitly adjudicate the tagged conflicting rank. All six CF-03 intermediates abstained because their individual modality could not establish the entire conjunction. The frozen final parser allows only the union of intermediate answer IDs; that union was empty for both queries, so CF-03 could not introduce a paper at final fusion. This is a limitation of the approved late-fusion contract, not evidence that complementary facts were successfully reconciled. No algorithm or prompt was changed in response.
API generation latency excludes the operational pacing wait. Phase 5 total latency includes the initial/inter-request waits and is therefore a scheduling measurement, not intrinsic model speed. CF-03 makes additional calls by design. Token use is provider-measured. Missing/failed metrics remain NULL.
The descriptive trade-off table compares quality with context size, latency, requests and tokens only for methods with both final answers. With two paired queries, especially tied/zero quality, a nondominated point is not scientific superiority. **No RQ2 winner is selected.**

## Final explanations and CF-03 intermediates

### CF-B0 — generated:69a22c3b4989b07ed6c3:conflict — final

```json
{"answer_ids":[],"explanation":"No paper in the provided evidence meets all required conditions; none have both the specified abstract wording and a recorded author affiliation with University of Insubria while also satisfying the rank and venue constraints."}
```

### CF-B0 — generated:69a22c3b4989b07ed6c3:normal — final

```json
{"answer_ids":[],"explanation":"No paper in the provided evidence meets all required conditions (abstract containing the specified phrase, University of Insubria affiliation, rank ≤20071, and journal venue)."}
```

### CF-B1 — generated:69a22c3b4989b07ed6c3:conflict — final

```json
{"answer_ids":[],"explanation":"No paper in the provided evidence meets all required conditions; affiliation information for University of Insubria is absent."}
```

### CF-B1 — generated:69a22c3b4989b07ed6c3:normal — final

```json
{"answer_ids":[],"explanation":"No paper in the provided evidence has an abstract containing the required phrases, nor can affiliation, rank, and venue conditions be verified for such a paper."}
```

### CF-01 — generated:69a22c3b4989b07ed6c3:conflict — final

```json
{"answer_ids":[],"explanation":"No paper in the provided evidence meets all criteria; none have author affiliation information linking to University of Insubria."}
```

### CF-01 — generated:69a22c3b4989b07ed6c3:normal — final

```json
{"answer_ids":[],"explanation":"No provided paper has an abstract containing the required phrases, and none include affiliation data; therefore no paper meets all criteria."}
```

### CF-02 — generated:69a22c3b4989b07ed6c3:conflict — final

```json
{"answer_ids":[],"explanation":"No provided abstract contains the required phrases, and no other evidence meets all criteria."}
```

### CF-02 — generated:69a22c3b4989b07ed6c3:normal — final

```json
{"answer_ids":[],"explanation":"No provided paper has an abstract containing the required phrases, nor evidence of University of Insubria affiliation, rank, or journal venue."}
```

### CF-03 — generated:69a22c3b4989b07ed6c3:conflict — text

```json
{"answer_ids":[],"explanation":"No provided abstracts contain the required phrases, and no other evidence meets all conditions."}
```

### CF-03 — generated:69a22c3b4989b07ed6c3:conflict — graph

```json
{"answer_ids":[],"explanation":"No provided evidence includes abstracts with the required phrases, nor affiliation or rank/venue details, so no paper meets all conditions."}
```

### CF-03 — generated:69a22c3b4989b07ed6c3:conflict — structured

```json
{"answer_ids":[],"explanation":"No provided evidence includes abstracts containing the required phrases, so no paper meets all conditions."}
```

### CF-03 — generated:69a22c3b4989b07ed6c3:conflict — final

```json
{"answer_ids":[],"explanation":"No provided abstracts contain the required phrases, and no evidence shows an author affiliated with University of Insubria together with rank ≤20071 and journal venue."}
```

### CF-03 — generated:69a22c3b4989b07ed6c3:normal — text

```json
{"answer_ids":[],"explanation":"No provided abstracts contain the required phrases, and no other evidence meets all conditions."}
```

### CF-03 — generated:69a22c3b4989b07ed6c3:normal — graph

```json
{"answer_ids":[],"explanation":"No evidence provides abstracts containing the required phrases, so no paper meets all conditions."}
```

### CF-03 — generated:69a22c3b4989b07ed6c3:normal — structured

```json
{"answer_ids":[],"explanation":"No provided evidence includes abstracts, so none can be confirmed to contain the required phrases."}
```

### CF-03 — generated:69a22c3b4989b07ed6c3:normal — final

```json
{"answer_ids":[],"explanation":"No provided abstracts contain the required phrases, and no other evidence meets all conditions."}
```

## Provenance and review gate

The prepared v2 configs, query seeds, frozen evidence, fusion implementations and generation settings are unchanged. Static outgoing payload hashes are checked against the prepared previews; late final contexts are constructed by the frozen CF-03 implementation. No retries or repairs are permitted. HTTP logs retain rate-limit headers, response usage and finish reasons without credentials.
Artifacts: `per_query_comparison.csv`, `method_comparison.csv`, `tradeoffs.csv`, `stage_outputs.json`, `http_dispatches/`, `stage_journal/`, per-method Phase 5 records and manifests. Preservation/test results accompany this report. **Stop for human review; do not begin Phase 9.**

## Post-execution validation

30 relevant tests passed after execution. The audit recomputed all ten query records, verified 14 static payload hashes and two dynamic late-fusion requests, and confirmed request-start intervals of 90.000–90.015 seconds. All 550 original Phase 8 files, frozen scientific code/configs and 695 protected data payloads remain unchanged. No test/human-test experiment was executed. Review date: 11 October 2026, Asia/Calcutta; provider execution date: 10 October 2026.
