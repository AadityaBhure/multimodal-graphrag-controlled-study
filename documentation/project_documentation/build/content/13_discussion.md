#! Part IX · Discussion

# Lessons learned

## About the research question

1. **Look upstream first.** In every study the decisive question was whether the correct papers reached the model at all. Measuring gold coverage, supportability and "gold retrieved / gold seen" made the bottleneck visible; without them, the identical answers of Parts 2 to 4 would be uninterpretable.
2. **Simple controls are hard to beat on cost.** A fixed top-K, labelled sections and keyword routing matched the elaborate methods on answers and beat them on tokens and time. Any elaborate method should be compared with such controls, with cost reported next to quality.
3. **More evidence in the context is not more answers.** CM-03 placed the most correct papers in the context and produced no correct answer on answerable questions; the model needs evidence that shows every condition, not just the right paper IDs.
4. **Agents and learned routers trade model calls for search savings.** AR-03 nearly eliminated wasted searches but needed six to seven model calls per question; AR-01's classifier, trained on multi-step-dominated labels, sent every question down the multi-step route.

## About method

1. **Audit before the final runs.** A requirement-by-requirement audit found 41 deviations in implementations that had passed unit tests and phase reviews. Rebuilding them faithfully, without touching the history, was cheaper than defending unfaithful results.
2. **Freeze everything that can change a result, and check it mechanically.** Hash-frozen plans, pinned line endings and a runner that refuses on any mismatch removed whole classes of silent errors.
3. **Separate calling the model from computing results.** Storing every request by its hash and replaying results in a mode that refuses any changed request made runs resumable, auditable and byte-reproducible.
4. **Plan the statistics with the cohort size in mind.** With 8 families and 7 to 10 Holm-adjusted pairs, significance was unattainable in Parts 1 and 2. Fewer pre-specified pairs or more families would have made those studies decisive.
5. **NULL is not zero, and waiting is not latency.** Keeping unmeasured values missing and excluding pauses from latency kept every reported number meaningful.
6. **Bind text to data.** Writing findings with placeholders that resolve against the frozen results (in the app and in this document) prevents numbers in prose from drifting away from the data.

# Limitations and threats to validity

## Data and benchmark

1. **Few independent units.** The validation split has 14 independent families (8 per study for Parts 1 and 2); results are exploratory validation results, not benchmark-wide inference.
2. **Verified by computation, not by people.** No human review decisions exist yet (3,390 items prepared; 2,801 needed for the locked test).
3. **Template wording.** Generated questions are mechanical; the rule router benefits from cue words in the templates, and the phrase "at least one" also misleads it.
4. **Exact phrases versus meaning-based retrieval.** Text conditions are exact abstract phrases, which the dense text retriever rarely finds; text-dependent questions are therefore mostly unanswerable for every strategy.
5. **Distribution shift by design.** Splits use structurally different templates (graph paths of one hop in train, two in validation, three in test).
6. **Embedding truncation.** The embedding model reads at most 256 tokens of each abstract.
7. **Bounded leakage checks.** Automated scans cannot rule out every paraphrase across splits.

## Methods

8. **Adaptations, not reproductions.** All nine literature-inspired methods are re-implemented under one frozen interface; training-heavy parts of the originals (graph neural networks and soft prompts, fine-tuned evaluators, large classifiers, solvers) are replaced or omitted.
9. **CM-01's graph-native provenance units** replace the original's text-to-triple provenance, which the dataset does not provide.
10. **CM-03's frozen parameters** (mass 10 per seed, sink capacity 1) let the diffusion converge on only 5 of 32 questions; the original's guarantees are not claimed.
11. **AR-01's labels** come from a retrieval-only oracle that uses the raw question, a proxy for the controller-written sub-queries at inference; four training families straddle the train/development partition; the labels are imbalanced and were not rebalanced.
12. **CM-B1 in the integrated system** removes nothing under the frozen top-5 graph retriever for a single-graph-call policy.

## Experiments and statistics

13. **Limited statistical power,** especially the unattainable Holm significance in Parts 1 and 2.
14. **Many comparisons measure correct abstention:** 16 of 24 fusion bundles contain no correct paper, and a quarter of Part 1's questions are unanswerable.
15. **Latency asymmetry in Part 1:** CM-01 computes its question-specific scores inside its timer while CM-02 and CM-03 use scores staged offline.
16. **The overall ranking was defined after the results.** It is a transparent summary of frozen means, reported as such; a quality-first rule would choose CM-01 in Part 1.
17. **Reduced scope.** The RQ3 and RQ4 cohort uses the normal and noisy variants only (28 of 56), a separate fusion-isolation study was dropped, and the locked test is out of scope; these decisions were frozen before the affected outcomes existed.

## System and model

18. **One answer model** (`gpt-oss:20b`, temperature 0, low reasoning effort, 1,024-token cap). Results may differ with a stronger model, longer outputs or a larger context window.
19. **Determinism is per stored response.** A fixed seed and temperature 0 do not guarantee identical outputs on different hardware or software; reproducibility rests on the stored responses and the replay check.

## Application

20. **Recorded runs only for the evaluated pipelines.** The showcase profile replays six recorded pipelines; any other combination needs the full profile with the research data and the model server. In side-by-side views at laptop widths, the pipeline strip and KPI tiles are cramped (a fix has been proposed separately).

# Future work

1. **Improve upstream retrieval coverage** for multi-source questions: lexical or hybrid text retrieval for exact phrases, larger or adaptive graph top-K, and using structured filters to restrict candidates for the other sources. This is the most promising step, because every study was limited before generation.
2. **Complete the human review** of the test and human-test splits (2,801 decisions) and run the locked final test.
3. **Repeat the comparisons with a stronger answer model** and longer completion and context limits, to see whether the elaborate methods gain once evidence is sufficient.
4. **Run the fusion-isolation study** on evidence-complete bundles, so fusion is tested where an answer is possible.
5. **Increase power:** more families per study, fewer pre-specified pairs, or a hierarchical analysis across studies.
6. **Use more natural questions** (paraphrased or human-written, with verified source necessity) to test the rule router without template cues.
7. **Integrate the quality-oriented alternative** (CM-01) in a second integrated system once retrieval coverage improves.
8. **Application:** compact side-by-side layouts, a pre-recorded grid of all 25 retrieval × fusion combinations for deployments without a model server, and a public deployment.

# Conclusion

The project set out to measure, one decision at a time, how a retrieval-augmented language model should use text, graph and structured views of the same scientific corpus. It built three strictly isolated views of STaRK-MAG, a benchmark whose answers are computed before its questions are worded and whose multi-source questions provably need every source, an execution protocol in which every model call is stored and every result replayed, and four controlled studies with paired, family-clustered statistics.

One method wins each component on overall performance: **fixed top-K context management (CM-B1), source-separated fusion (CF-B1) and rule-based routing (AR-B1).** Their combination, INT-1, which the frozen selection rule had chosen before the overall ranking existed, answers as well as any single policy (answer F1 {{RQ4.INT-1.answer_f1}}), selects sources significantly better than searching everything ({{RQ4.test.source_f1.INT-1~AR-B0.delta}} source-selection F1, Holm p = {{RQ4.test.source_f1.INT-1~AR-B0.p_holm}}) and costs {{RQ4.test.total_tokens.INT-1~AR-B1.delta}} tokens more than the router alone. In every study the winner is the simplest strategy: no literature-inspired method improved answer quality with statistical support, and the most elaborate ones cost significantly more (AR-03 {{RQ3.test.total_tokens.AR-03~AR-B1.delta}} and AR-01 {{RQ3.test.total_tokens.AR-01~AR-B1.delta}} tokens against the router). Specific situations still favour other methods: CM-01 when answer quality matters more than cost, CM-03 when every correct paper must reach the model, AR-03 when every search is expensive.

The clearest lesson is where quality is lost: **before generation.** At most {{RQ1.max.gold_coverage|pct}} of the correct papers reached the context in Part 1, and {{RQ2.support.UNSUPPORTABLE}} of 24 fusion bundles contained no correct paper at all. Better upstream retrieval, followed by a human-reviewed locked test, is the next step. Every number in this document, in the paper and in the showcase application can be traced to a frozen, checksummed file and rebuilt by script.
