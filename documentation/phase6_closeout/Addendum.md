# Phase 6 closeout addendum

PASS. All 56 programmatically verified generated validation records were evaluated by each unchanged B1–B4 baseline (224 query executions). No test/human-test or official unverified records were evaluated. No generation or API calls occurred. Phase 7 has not begun.

Selection was fixed before execution: 8 queries each in T, G, S, TG, TS, GS, TGS; 24 single-hop and 32 multi-hop-2; 14 each normal, noisy, conflict and unanswerable. These are operational/programmatic annotations, not a claim of completed human review. No higher-hop validation strata exist in this selection.

## Machine-generated retrieval comparison

| Baseline | Cohort | Queries | Available / NULL | Recall@5 | Precision@5 | MRR | nDCG@5 | Gold coverage |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| B1 | hop/multi-hop-2 | 32 | 24 / 8 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B1 | hop/single-hop | 24 | 18 / 6 | 0.000000 | 0.000000 | 0.018519 | 0.000000 | 0.001035 |
| B1 | modality/G | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B1 | modality/GS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B1 | modality/S | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B1 | modality/T | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.055556 | 0.000000 | 0.003104 |
| B1 | modality/TG | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B1 | modality/TGS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B1 | modality/TS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B1 | overall | 56 | 42 / 14 | 0.000000 | 0.000000 | 0.007937 | 0.000000 | 0.000443 |
| B1 | stress/conflict | 14 | 14 / 0 | 0.000000 | 0.000000 | 0.023810 | 0.000000 | 0.001330 |
| B1 | stress/noisy | 14 | 14 / 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B1 | stress/normal | 14 | 14 / 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B1 | stress/unanswerable | 14 | 0 / 14 | NULL | NULL | NULL | NULL | NULL |
| B2 | hop/multi-hop-2 | 32 | 24 / 8 | 0.011966 | 0.300000 | 0.291667 | 0.287598 | 0.011966 |
| B2 | hop/single-hop | 24 | 18 / 6 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B2 | modality/G | 8 | 6 / 2 | 0.039864 | 1.000000 | 1.000000 | 1.000000 | 0.039864 |
| B2 | modality/GS | 8 | 6 / 2 | 0.008000 | 0.200000 | 0.166667 | 0.150393 | 0.008000 |
| B2 | modality/S | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B2 | modality/T | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B2 | modality/TG | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B2 | modality/TGS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B2 | modality/TS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B2 | overall | 56 | 42 / 14 | 0.006838 | 0.171429 | 0.166667 | 0.164342 | 0.006838 |
| B2 | stress/conflict | 14 | 14 / 0 | 0.006838 | 0.171429 | 0.166667 | 0.164342 | 0.006838 |
| B2 | stress/noisy | 14 | 14 / 0 | 0.006838 | 0.171429 | 0.166667 | 0.164342 | 0.006838 |
| B2 | stress/normal | 14 | 14 / 0 | 0.006838 | 0.171429 | 0.166667 | 0.164342 | 0.006838 |
| B2 | stress/unanswerable | 14 | 0 / 14 | NULL | NULL | NULL | NULL | NULL |
| B3 | hop/multi-hop-2 | 32 | 24 / 8 | 0.000000 | 0.000000 | 0.027778 | 0.000000 | 0.084063 |
| B3 | hop/single-hop | 24 | 18 / 6 | 0.333333 | 0.100000 | 0.351852 | 0.333333 | 0.334833 |
| B3 | modality/G | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B3 | modality/GS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.055556 | 0.000000 | 0.002921 |
| B3 | modality/S | 8 | 6 / 2 | 1.000000 | 0.300000 | 1.000000 | 1.000000 | 1.000000 |
| B3 | modality/T | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B3 | modality/TG | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B3 | modality/TGS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.055556 | 0.000000 | 0.333333 |
| B3 | modality/TS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.055556 | 0.000000 | 0.004500 |
| B3 | overall | 56 | 42 / 14 | 0.142857 | 0.042857 | 0.166667 | 0.142857 | 0.191536 |
| B3 | stress/conflict | 14 | 14 / 0 | 0.142857 | 0.042857 | 0.214286 | 0.142857 | 0.288894 |
| B3 | stress/noisy | 14 | 14 / 0 | 0.142857 | 0.042857 | 0.142857 | 0.142857 | 0.142857 |
| B3 | stress/normal | 14 | 14 / 0 | 0.142857 | 0.042857 | 0.142857 | 0.142857 | 0.142857 |
| B3 | stress/unanswerable | 14 | 0 / 14 | NULL | NULL | NULL | NULL | NULL |
| B4 | hop/multi-hop-2 | 32 | 24 / 8 | 0.000000 | 0.000000 | 0.065104 | 0.000000 | 0.095696 |
| B4 | hop/single-hop | 24 | 18 / 6 | 0.000000 | 0.000000 | 0.052736 | 0.000000 | 0.335868 |
| B4 | modality/G | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.166667 | 0.000000 | 0.039864 |
| B4 | modality/GS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.072917 | 0.000000 | 0.009587 |
| B4 | modality/S | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.105556 | 0.000000 | 1.000000 |
| B4 | modality/T | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.031818 | 0.000000 | 0.003104 |
| B4 | modality/TG | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| B4 | modality/TGS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.020833 | 0.000000 | 0.333333 |
| B4 | modality/TS | 8 | 6 / 2 | 0.000000 | 0.000000 | 0.020833 | 0.000000 | 0.004500 |
| B4 | overall | 56 | 42 / 14 | 0.000000 | 0.000000 | 0.059803 | 0.000000 | 0.198627 |
| B4 | stress/conflict | 14 | 14 / 0 | 0.000000 | 0.000000 | 0.083775 | 0.000000 | 0.296491 |
| B4 | stress/noisy | 14 | 14 / 0 | 0.000000 | 0.000000 | 0.047817 | 0.000000 | 0.149695 |
| B4 | stress/normal | 14 | 14 / 0 | 0.000000 | 0.000000 | 0.047817 | 0.000000 | 0.149695 |
| B4 | stress/unanswerable | 14 | 0 / 14 | NULL | NULL | NULL | NULL | NULL |

## Metrics and interpretation

Tables are computed from validated Phase 5 RunRecord files using the existing aggregate() and metric functions. Means exclude NULL and publish n_available/n_null. Full JSON/CSV tables include all existing metrics, K=1/5/10, and modality × complexity × stress intersections. CSV unavailable values are explicitly NULL; JSON uses null. Marginal cohorts overlap and must not be summed.

Retrieval precision divides by K, even for fewer results. Rankings are deduplicated; recall uses the gold-set denominator, MRR the first relevant rank, and nDCG binary relevance. Empty-gold/unanswerable retrieval metrics are NULL, not zero. All answer metrics, generation latency, token usage, estimated cost and unsupported agent/fusion metrics are NULL. Evidence coverage is NULL because gold evidence IDs are unavailable. See full tables for each metric’s availability.

B4 ranking remains source-order concatenation: Recall@5 is generally Text-first, while gold coverage measures its full returned set. Stress inputs use existing benchmark overlays and unchanged baseline overlay behavior, without mutating canonical data. Results describe this small controlled validation set, not general benchmark accuracy.

## Resources and preservation

| Baseline | Wall seconds | Retrieval seconds (sum) | Process peak bytes | LLM calls |
| --- | ---: | ---: | ---: | ---: |
| B1 | 61.604 | 55.411 | 1382522880 | 0 |
| B2 | 773.113 | 765.904 | 1382522880 | 0 |
| B3 | 6.177 | 0.782 | 1382522880 | 0 |
| B4 | 551.392 | 543.702 | 2340888576 | 0 |

Peak memory is a cumulative process high-water mark; wall time includes setup, runner validation and file materialization. Initial execution overlapped regression and preservation checks, so these are not isolated latency measurements. Resume reuses completed records; original per-query measured latencies remain authoritative.

No tuning occurred. Only the new experiment ID and query selection differ from the original offline-validation configs. Seed 42, K values, retrieval parameters, graph budgets, context budgets, embeddings and baseline algorithms are unchanged. baseline_preservation.json records before/after SHA-256 values for every original baseline implementation/config. Full frozen-data preservation is recorded separately in preservation.json.

Original pre-checkpoint execution command: `.\.venv\Scripts\python.exe scripts/closeout_phase6.py`. Raw records, manifests, events, status and aggregate tables are under runs/B1–B4. These retain the existing deterministic runner identity and incompatible-run refusal. The checkpoint changes Git provenance: use `--output documentation/phase6_closeout_rerun` for a new reproduction, rather than overwriting these frozen runs. An interrupted run can resume only with its original code/config/provenance. To verify saved tables without retrieval, run `.\.venv\Scripts\python.exe scripts/validate_phase6_closeout.py`.

Closeout complete; checkpoint and stop for review. No Phase 7 work is included.

Validation: 135 regression tests passed (one pre-existing DuckDB deprecation warning). The closeout audit recomputed all 224 records and verified 2,240 marginal comparison rows; no failures. See validation.json and pytest.txt.

The separate intersection audit also recomputed and matched all 4,480 modality × complexity × stress metric rows. The final post-run preservation audit passed for all 695 frozen payloads and the original Phase 6 implementations/configs. No tuning occurred.
