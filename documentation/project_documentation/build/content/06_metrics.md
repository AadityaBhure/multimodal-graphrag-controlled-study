#! Part VI · Measuring

# Metrics

Every metric is computed **per question** from the run record and then averaged over the questions of a study. Measures that were not observed are NULL and are excluded from averages (with the count of missing values reported), never counted as zero.

## Notation

For one question, let **P** be the set of paper IDs the system returned (duplicates removed), **G** the verified set of correct papers (possibly empty), and **H** = |P ∩ G| the number of correct papers returned. A failed or unparseable answer is NULL, which is different from a valid empty answer (an abstention).

## Answer quality

Table: Answer-quality metrics {w=1.3,2.2,2.2,0.6}
| Metric | Formula | Edge cases | Better |
|---|---|---|---|
| Precision | H / \|P\| | P empty: 1 if G is also empty, else 0 | ↑ |
| Recall | H / \|G\| | G empty: 1 if P is also empty, else 0 | ↑ |
| **Answer F1** (primary) | 2 · precision · recall / (precision + recall) | 0 when precision + recall = 0; both sets empty gives 1 | ↑ |
| Exact match | 1 if P = G, else 0 | both empty gives 1 | ↑ |
| Answerability correctness | 1 if (P non-empty) = (G non-empty) | — | ↑ |
| F1 (answerable) | mean F1 over questions with non-empty G | unanswerable variants left out | ↑ |

The unanswerable variants make an important special case: when no paper is correct, returning nothing scores 1 and returning anything scores 0. In Part 1, a quarter of the questions are unanswerable, so a method that abstains on every question already reaches an average answer F1 of 0.250 (Chapter 19).

#### Worked examples

- P = {1, 2, 2}, G = {2, 3, 4}: duplicates removed, P = {1, 2}; H = 1; precision 1/2, recall 1/3, F1 = 2 · (1/2 · 1/3) / (1/2 + 1/3) = 0.4; exact match 0; answerability 1.
- G = {P1, P2, P3}, P = {P2, P3, P5}: precision 2/3, recall 2/3, F1 0.667, exact match 0. The application's metrics page lets an audience change both sets and watch the four scores update.

@screen p04_metrics__04 | The metric playground on the "Metrics and statistics" page: choose the correct and the returned papers and the four answer metrics update immediately. | 6.3

## Evidence quality

These measure how well the correct papers are placed in front of the model, independent of what it answers. They are NULL for questions whose correct answer is empty.

Table: Evidence-quality metrics {w=1.2,3.6,0.6}
| Metric | Definition | Better |
|---|---|---|
| MRR | Reciprocal rank of the first correct paper in the method's ranked evidence (1 = first place, 0 if none appears) | ↑ |
| Recall@K | Correct papers among the first K distinct ranked papers ÷ \|G\| (K = 1, 5, 10) | ↑ |
| Precision@K | Correct papers among the first K positions ÷ K (even if fewer than K papers were returned) | ↑ |
| nDCG@K | Binary discounted cumulative gain of the first K, divided by the ideal value for min(K, \|G\|) correct papers | ↑ |
| **Gold coverage** | Share of the correct papers that appear anywhere in the context given to the model | ↑ |

Gold coverage is an upper bound on what an answer can achieve: a paper the model never sees cannot be returned. Example: ranking (9, 2, 2, 1) with G = {1, 2, 3} becomes (9, 2, 1) after removing the duplicate; MRR = 1/2, Recall@3 = Precision@3 = 2/3, Precision@5 = 2/5, nDCG@3 = 0.531.

## Retrieval-control metrics

Retrieval-control policies (Part 3) are judged on which sources they search. Each question's **oracle source set R** comes from its verified construction (T → {text}, G → {graph}, TG → {text, graph}, …). It is used only for evaluation and is never visible to a policy. Let **S** be the set of sources the policy actually searched.

Table: Retrieval-control metrics {w=1.5,3.4,0.6}
| Metric | Definition | Better |
|---|---|---|
| Source precision | \|S ∩ R\| ÷ \|S\| | ↑ |
| Source recall | \|S ∩ R\| ÷ \|R\| | ↑ |
| **Source-selection F1** | harmonic mean of source precision and source recall | ↑ |
| Exact source set | 1 if S = R | ↑ |
| Wasted retrieval | \|S \ R\| ÷ \|S\| (0 when nothing was searched) | ↓ |
| Required-source miss | \|R \ S\| ÷ \|R\| | ↓ |
| Covered step | the first retrieval call after which the searched sources include all of R | — |
| **Stopping accuracy** | 1 if a covered step exists and the policy made exactly that many retrieval calls (it stopped as soon as it had every needed source) | ↑ |
| Premature stop | R never covered, and the policy stopped for a non-budget reason | ↓ |
| Over-retrieval | R covered, but more calls were made after the covered step | ↓ |
| Step-limit exhaustion | R never covered, and a step or iteration limit ended the run | ↓ |

Example: a text-plus-graph question (R = {text, graph}) and a policy that searches text, graph and structured. Then S = {text, graph, structured}: source precision 2/3, recall 1, source F1 0.8, wasted retrieval 1/3, covered step 2, three calls made, so stopping accuracy is 0 and the run counts as over-retrieval.

## Cost

Table: Cost metrics {w=1.5,3.4,0.6}
| Metric | Definition | Better |
|---|---|---|
| Input tokens | tokens sent to the model per question, summed over all its calls (as reported by the model server) | ↓ |
| Output tokens | tokens written by the model per question, summed over all calls | ↓ |
| Tokens | input + output tokens | ↓ |
| Model calls | number of language-model calls per question (answers, controllers, selectors, critics, repairs) | ↓ |
| Retrieval calls (searches) | number of retriever invocations per question | ↓ |
| Latency | intrinsic time per question: recorded retrieval time + model compute time + local computation; waiting is excluded | ↓ |
| Context characters / tokens | size of the final context given to the answer call | ↓ |

## Supportability (fusion only)

Fusion cannot recover evidence that was never retrieved. Before any fusion call, each RQ2 evidence bundle was classified from its evidence and its gold set (evaluator side only, never visible to a method): **fully supportable** if every correct paper is the canonical paper of some evidence item in the bundle, **partially supportable** if at least one is, **unsupportable** if none is. For an unsupportable bundle the best possible behaviour is a correct abstention.

# Statistical analysis

## Why paired, family-clustered tests

Two methods are always compared **on the same questions**, so the analysis looks at the difference per question rather than comparing two averages. Variants of one base question (normal, noisy, conflict, unanswerable) share their conditions and usually behave alike, so treating them as independent would overstate certainty. Every test therefore resamples or permutes **whole families**. A study with 8 families has 8 independent units, not 32.

@figure figures/d_statistics.png | The statistical procedure for one pre-specified pair of methods and one metric. | 6.4

## The procedure

1. **Per-question differences.** For each question *q*, d(q) = A(q) − B(q).
2. **Family sums.** For each family *f*, S_f = the sum of d over its questions; n_f = the number of its questions.
3. **95 % bootstrap interval.** Draw the families with replacement as many times as there are families, compute the mean difference ΣS_f ÷ Σn_f over the drawn families, and repeat 10,000 times with a fixed seed (42). The interval runs from the 2.5th to the 97.5th percentile of these 10,000 means.
4. **Exact sign-flip test.** If A and B were equally good, each family's sum would be as likely positive as negative. Enumerate all 2^F ways of flipping the signs of the F family sums and compute each flipped total. The two-sided p-value is the share of sign patterns whose total is at least as far from zero as the observed total. With 8 families there are 256 patterns, with 14 families 16,384.
5. **Holm correction.** Several pairs are tested for the same metric, so their p-values are adjusted with the Holm step-down method: sort the m p-values ascending; the i-th smallest is multiplied by (m − i + 1); adjusted values are made non-decreasing and capped at 1.
6. **Decision.** A difference is significant only if its Holm-adjusted p-value is below 0.05.

## A worked example on real results

The application's metrics page runs the exact test live on recorded data. For Part 3, comparing the rule router (AR-B1) with always searching everything (AR-B0) on source-selection F1:

@figure figures/c_stats_example.png | The statistics of one real comparison (AR-B1 − AR-B0, source-selection F1, 14 families). 1: the 14 family sums; 2: the totals of all 16,384 sign-flip patterns, with the observed total in red; 3: the 10,000 family-bootstrap means with the 95 % interval in blue. The recomputed p-value and interval match the frozen analysis exactly. | 6.6

- 10 of the 14 families favour the router, none favours searching everything and four are ties, for an observed total of +4.933 over 28 questions.
- Exactly 32 of the 16,384 sign patterns give a total at least as far from zero: the observed pattern and its mirror image, each 16 times over because flipping the four zero-sum families changes nothing. So p = 32 / 16,384 = 0.002.
- Seven pairs are tested for source-selection F1 in Part 3; Holm multiplies the smallest p-value by 7, giving an adjusted p = {{RQ3.test.source_f1.AR-B1~AR-B0.p_holm}}: **significant**.
- The family bootstrap gives a mean difference of {{RQ3.test.source_f1.AR-B1~AR-B0.delta}} with a 95 % interval of {{RQ3.test.source_f1.AR-B1~AR-B0.ci}}.

## The power limit of 8-family studies

The exact sign-flip test cannot produce a p-value smaller than 2 ÷ 2^F, which happens when every family points in the same direction. With F = 8 families (Parts 1 and 2) the floor is 2/256 = 0.0078; with F = 14 (Parts 3 and 4) it is 2/16,384 = 0.00012.

Holm then multiplies the smallest p-value by the number of pairs m. **With 8 families the smallest attainable adjusted p-value is 10 × 0.0078 = 0.078 for the 10 pairs of Part 1 and 7 × 0.0078 = 0.055 for the 7 pairs of Part 2, both above 0.05.** No difference in Parts 1 and 2 could therefore be declared significant, however consistent it was. Part 2 shows this concretely: CF-02 used exactly one more model call than CF-B1 on every bundle and CF-03 used 2.75 more, every family pointing the same way (p = 0.008), yet the Holm-adjusted p-value is 0.055. In Parts 1 and 2, "not significant" means "not testable at this size"; their comparisons are descriptive, and the conclusions in Chapters 19 and 20 are worded accordingly. Parts 3 and 4, with 14 families, can and do detect differences.

## Pareto sets

A method is **Pareto-optimal** when no other method is at least as good on every axis and strictly better on at least one. The axes of each study were fixed in its analysis plan:

Table: Pareto axes of each study {w=1.0,2.6,2.6}
| Study | Higher is better | Lower is better |
|---|---|---|
| RQ1 | answer F1, MRR | input tokens, latency |
| RQ2 | answer F1 | input tokens, latency |
| RQ3 | answer F1, source-selection F1 | total tokens, latency |

A method outside the Pareto set is beaten on every axis at once by some other method. A method inside it is a defensible choice for some budget. Pareto analysis is descriptive: it uses the means and does not test significance.

## Failure taxonomy

For Part 3 every run also receives zero or more failure labels that separate controller failures from retriever weaknesses, for example *wrong initial routing*, *required source never selected*, *premature stop*, *excessive retrieval*, *unnecessary source selected*, *retriever failure despite correct routing*, *evaluator misclassification*, *validator false accept*, *structured intent failure*, *agent schema failure* and *insufficient evidence*. The labels are descriptive counts (Chapter 21).

# Overall ranking

## Why an overall ranking

Pareto sets often contain several methods, and the statistical tests rarely separate them. The user of this project asked for one clear winner per part, which the integrated system then combines. The overall ranking (decision PR-15) provides it. It was **defined after the results were known**, so it is a transparent summary of the frozen means, not a significance test and not a replacement for any frozen analysis.

## The rule

@figure figures/d_ranking.png | The overall ranking: rank each method on every Pareto axis of its study, add the ranks, and pick the lowest total; a scaled-score average serves as a robustness check. The three winners, chained in pipeline order, equal the integrated system chosen earlier by the frozen RQ4 rule. | 6.5

1. Take the Pareto axes of the study (table above).
2. On each axis, rank the five methods from 1 (best) to 5 (worst). Tied methods share the average of the ranks they span (for example two methods tied for 4th and 5th both get 4.5).
3. Add the ranks; every axis counts equally. The lowest **rank total** wins.
4. Ties on the total go to the higher answer F1, then to fewer tokens, then to a fixed order: B1, 01, 02, 03, B0.
5. **Robustness check:** min-max scale every axis to [0, 1] (1 = best) and average the scaled scores per method. The ranking is considered robust when the highest average picks the same winner.

## The results

Table: Overall ranking results {w=1.0,1.2,1.0,1.3,1.2,1.4}
| Study | Winner (rank total) | Runner-up | Scaled-score check | Same winner? | Quality-first alternative |
|---|---|---|---|---|---|
| RQ1 | CM-B1 ({{RQ1.overall.total.CM-B1}}) | CM-01 and CM-02 ({{RQ1.overall.total.CM-01}}) | CM-B1 ({{RQ1.overall.scaled.CM-B1}} vs {{RQ1.overall.scaled.CM-01}}) | yes | CM-01 |
| RQ2 | CF-B1 ({{RQ2.overall.total.CF-B1}}) | CF-02 and CF-B0 ({{RQ2.overall.total.CF-02}}) | CF-B1 ({{RQ2.overall.scaled.CF-B1}} vs {{RQ2.overall.scaled.CF-02}}) | yes | CF-B1 |
| RQ3 | AR-B1 ({{RQ3.overall.total.AR-B1}}) | AR-02 ({{RQ3.overall.total.AR-02}}) | AR-B1 ({{RQ3.overall.scaled.AR-B1}} vs {{RQ3.overall.scaled.AR-02}}) | yes | AR-B1 |

Both aggregations pick the same winner in every study. Chained in pipeline order, the winners give **AR-B1 → CM-B1 → CF-B1**, which is exactly the integrated system INT-1 that the frozen RQ4 rule (highest answer F1 within the Pareto set, with context management fixed to CM-B1 in advance) had already selected. A *quality-first* rule (highest answer F1 within the Pareto set) would pick CM-01 instead of CM-B1 in Part 1 and the same winners in Parts 2 and 3; CM-01 is therefore reported as the situational choice when answer quality matters more than cost.

@figure figures/c_overall_totals.png | Rank totals of every method in the three single-component studies (lower is better). | 6.6
