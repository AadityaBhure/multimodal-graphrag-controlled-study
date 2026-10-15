# RQ1 — canonical context-management results (repaired, validation)

Date: 2026-10-15. Plan revision 4 (`execution_plan.json`); records in `runs/`, statistics in `analysis.json` (`scripts/report_rq1_repair.py`). Historical Phase 7 results are preserved unchanged and are not merged with these numbers.

## 1. What was run
* Cohort: 32 verified generated validation queries = 8 independent base families × 4 stress variants (normal, noisy, conflict, unanswerable); modalities G, TG, GS, TGS (8 each). No test / human-test data.
* Methods: CM-B0 (raw), CM-B1 (fixed top-K), CM-01 (KG²RAG-inspired), CM-02 (PCST), CM-03 (QAFD flow diffusion); fixed pass-through of Text/Structured for mixed queries; shared generator `openai/gpt-oss-120b`, temperature 0, low reasoning, 1,024 cap, frozen prompt.
* Integrity: 192/192 provider calls successful (32 CM-03 keyword + 160 final), 0 rate-limited, 0 failed; calls in query-major order over 2026-10-12…15; the unchanged runner replayed all 160 records with 0 extra calls and 0 payload mismatches; 160/160 records, 0 errors, 0 null answers.

## 2. Main results (all 32 queries; mean, family-clustered bootstrap 95 % CI for F1)
| Method | F1 | F1 answerable (24) | EM | MRR* | Recall@5* | Gold coverage | Context tokens | Input tokens | Output tokens | Context ms | Intrinsic ms** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CM-B0 | 0.250 [0.25, 0.25] | 0.000 | 0.250 | 0.295 | 0.012 | 0.225 | 4,215 | 4,526 | 96 | 56 | 1,171 |
| CM-B1 | 0.264 [0.25, 0.287] | 0.019 | 0.250 | 0.353 | 0.137 | 0.221 | 1,132 | 1,443 | 126 | 56 | 1,093 |
| CM-01 | 0.312 [0.25, 0.424] | 0.083 | 0.250 | 0.359 | 0.013 | 0.175 | 4,698 | 5,009 | 176 | 3,785 | 5,116 |
| CM-02 | 0.251 [0.25, 0.252] | 0.001 | 0.250 | 0.187 | 0.001 | 0.085 | 1,181 | 1,491 | 105 | 16 | 1,058 |
| CM-03 | 0.250 [0.25, 0.25] | 0.000 | 0.250 | 0.171 | 0.129 | 0.298 | 3,225 | 3,731 | 217 | 30,701 | 32,435 |

\* over the 24 answerable queries (empty gold excluded). \*\* context_ms + provider generation_ms (pacing excluded).

## 3. Paired F1 comparisons (cluster = base family; exact sign-flip over 8 families; Holm)
| Pair | Mean Δ F1 | 95 % CI | p | p (Holm) |
|---|---|---|---|---|
| CM-B0 − CM-B1 | -0.014 | [-0.037, 0.000] | 0.5 | 1.00 |
| CM-B0 − CM-01 | -0.062 | [-0.174, 0.000] | 0.5 | 1.00 |
| CM-B1 − CM-01 | -0.048 | [-0.137, 0.000] | 0.5 | 1.00 |
| CM-B1 − CM-02 | +0.014 | [0.000, 0.036] | 0.5 | 1.00 |
| CM-B1 − CM-03 | +0.014 | [0.000, 0.037] | 0.5 | 1.00 |
| CM-01 − CM-02 | +0.062 | [0.000, 0.173] | 0.5 | 1.00 |
| CM-01 − CM-03 | +0.062 | [0.000, 0.174] | 0.5 | 1.00 |
| CM-B0 − CM-02 | -0.001 | [-0.002, 0.000] | 1.0 | 1.00 |
| CM-B0 − CM-03 | +0.000 | [0.000, 0.000] | 1.0 | 1.00 |
| CM-02 − CM-03 | +0.001 | [0.000, 0.002] | 1.0 | 1.00 |

**No pairwise F1 difference is statistically supported** (all Holm-adjusted p = 1.00). With 8 families the smallest attainable two-sided sign-flip p is 2/256; the observed differences come from one or two families.

## 4. Strata (F1 / MRR by modality)
| Modality | CM-B0 | CM-B1 | CM-01 | CM-02 | CM-03 |
|---|---|---|---|---|---|
| G | 0.250 / 1.000 | 0.307 / 1.000 | 0.500 / 1.000 | 0.252 / 0.667 | 0.250 / 0.333 |
| GS | 0.250 / 0.169 | 0.250 / 0.265 | 0.250 / 0.417 | 0.250 / 0.056 | 0.250 / 0.172 |
| TG | 0.250 / 0.000 | 0.250 / 0.125 | 0.250 / 0.000 | 0.250 / 0.000 | 0.250 / 0.159 |
| TGS | 0.250 / 0.012 | 0.250 / 0.021 | 0.250 / 0.020 | 0.250 / 0.024 | 0.250 / 0.020 |

* Every method answers all 8 unanswerable queries correctly (empty set) — this alone gives F1 = 0.25.
* **Only the two graph-only (G) families produce any correct answers.** For every multi-source query (TG, GS, TGS) all five methods returned empty answers (F1 = 0 on the 18 answerable multi-source queries).
* Stress type does not change the picture (answerable F1 is nearly identical across normal / noisy / conflict).

## 5. Pareto set (maximise F1, MRR; minimise input tokens, intrinsic ms)
Non-dominated: **CM-B1, CM-01, CM-02**. Dominated: CM-B0 (by CM-B1); CM-03 (by CM-B1, CM-02).

## 6. Findings
1. **No context-management method gives a statistically supported answer-quality gain** on this cohort; answer quality is near the floor for every method.
2. **CM-01** has the highest F1 (0.312; answerable 0.083) and MRR (0.359), driven by the two G families, at about 3.5× the input tokens and about 4.7× the intrinsic latency of CM-B1.
3. **CM-B1** (fixed top-K) is the cheapest strong control: about a third of CM-B0's tokens with equal or better F1 and MRR; it dominates CM-B0 and CM-03.
4. **CM-02** is the smallest and fastest context but has the lowest gold coverage (0.085) and a low MRR.
5. **CM-03** keeps the most gold papers in context (coverage 0.298) but converged in only 5/32 queries (the rest stopped at N_max = 1,000,000), is by far the slowest (mean intrinsic ≈ 32 s) and produced no correct answers on answerable queries.
6. The main bottleneck is **upstream evidence for multi-source queries**, not context management: gold coverage is below 0.30 for every method and the generator abstains on multi-source queries.

## 7. Limitations
* 8 independent families; exploratory validation, not benchmark-wide inference. Validation only (no locked test, per the two-week scope).
* Timing asymmetry (recorded before execution): CM-02 edge scores and CM-03 query vectors come from staged offline inputs while CM-01 computes its unit scores inside its timer, so latency favours CM-02/CM-03.
* Provider calls spanned four days; query-major ordering spreads any provider drift across methods.
* Analysis fix: the `fallback` diagnostic counted `False` as a fallback (CM-B0/B1 showed 1.0); corrected to `bool(fallback)` (all methods 0.0). Primary metrics unaffected.

## 8. Carried to RQ4 (decision for the human gate)
Empirically supported candidates are the Pareto set CM-B1, CM-01, CM-02. Suggested: **CM-01** as the quality-oriented candidate and **CM-B1** as the efficient control; no method is claimed best.

RQ1_SCIENTIFIC_STATUS = COMPLETE (validation, two-week scope) — pending human review
