#! Part I · Overview

# Executive summary

## The problem in one paragraph

Questions about scientific papers often combine three different kinds of knowledge: what a paper says (its title and abstract), how papers and people are connected (authors, institutions, citations, fields of study), and facts recorded about a paper (publication year, citation count, rank, venue). A retrieval-augmented language model that answers such questions has to find evidence in all three representations, decide which evidence fits into its limited context, combine evidence of very different shapes, and decide which source to search, in what order, and when to stop. Systems that do all of this usually change every design choice at once, so it is impossible to tell which choice helped. This project measures each of these decisions separately, under strictly controlled conditions, and then combines the best choices into one system.

## What was done

1. **Froze the starting point.** The original demonstration (Traditional RAG and a basic GraphRAG over 12 research PDFs) was audited and tagged so that research work could never change it.
2. **Built three isolated views of one corpus.** The official STaRK-MAG release (700,244 papers; 1,872,968 entities; 19,919,698 directed relations) was converted into a text view, a graph view and a structured view that share nothing except the official node ID.
3. **Built a verifiable benchmark.** 13,571 questions, including 167 generated questions whose correct answers are computed from the data before the question is worded, and whose multi-source questions provably need every listed source. Stress variants add distractors, contradicting facts and unanswerable versions.
4. **Built the measuring instrument.** A resumable evaluation harness with strict metrics, four simple retrieval baselines, and an execution protocol in which every model request is stored and every result can be replayed byte for byte.
5. **Ran four controlled studies.** Context management (RQ1), cross-modal fusion (RQ2) and retrieval control (RQ3) each compared five strategies (two simple controls and three methods adapted from published systems) while everything else stayed fixed; RQ4 combined the chosen components into one system. In total 448 run records were produced, with 0 errors.
6. **Analysed every study with paired statistics** that respect question families (bootstrap intervals, exact sign-flip tests, Holm correction), Pareto analysis, and an overall ranking that names one winner per study.
7. **Published the work.** A results package, a paper draft and an interactive showcase application (11 pages) that presents every number from a checksummed data bundle and lets an audience run questions through the studied pipelines.

## The answer

Table: The overall winner of each part {w=1.6,1.45,2.6,1.2}
| Part | Overall winner | Why it wins | Runner-up (rank total) |
|---|---|---|---|
| Part 1 · Context management (RQ1) | **CM-B1** · fixed top-K | Answer F1 {{RQ1.CM-B1.answer_f1}} (second only to CM-01's {{RQ1.CM-01.answer_f1}}) at the lowest input cost ({{RQ1.CM-B1.input_tokens}} tokens) and the second-best speed ({{RQ1.CM-B1.latency}}); rank total {{RQ1.overall.total.CM-B1}} | CM-01 and CM-02 ({{RQ1.overall.total.CM-01}}) |
| Part 2 · Cross-modal fusion (RQ2) | **CF-B1** · source-separated sections | Same answers as every other method; the cheapest ({{RQ2.CF-B1.input_tokens}} input tokens) and fastest ({{RQ2.CF-B1.latency}}); the only Pareto-optimal method; rank total {{RQ2.overall.total.CF-B1}} | CF-02 and CF-B0 ({{RQ2.overall.total.CF-02}}) |
| Part 3 · Retrieval control (RQ3) | **AR-B1** · rule router | Same answers as every other policy; the best source selection (source F1 {{RQ3.AR-B1.source_f1}}), fewest tokens ({{RQ3.AR-B1.total_tokens}}) and fastest ({{RQ3.AR-B1.latency}}); the only Pareto-optimal policy; rank total {{RQ3.overall.total.AR-B1}} | AR-02 ({{RQ3.overall.total.AR-02}}) |
| Part 4 · Integration (RQ4) | **INT-1** = AR-B1 → CM-B1 → CF-B1 | The selection rule written before any result was known picked exactly the three winners | — |

The combined system answers as well as any single policy (answer F1 {{RQ4.INT-1.answer_f1}}), selects sources significantly better than searching every source (source-selection F1 {{RQ4.test.source_f1.INT-1~AR-B0.delta}}, Holm p = {{RQ4.test.source_f1.INT-1~AR-B0.p_holm}}), and uses {{RQ4.test.total_tokens.INT-1~AR-B1.delta}} tokens more than the router on its own (Holm p {{RQ4.test.total_tokens.INT-1~AR-B1.p_holm|peq}}) because the fusion stage writes a larger context. Its latency does not differ significantly from either comparison.

@callout key | Five findings to remember
1. **No literature-inspired method improved answer quality with statistical support in any study.** In Part 1 every adjusted p-value for answer F1 is {{RQ1.test.answer_f1.CM-01~CM-B1.p_holm}}; in Parts 2 to 4 all strategies returned identical answers.
2. **The simplest strategy wins every part on overall performance,** and the elaborate methods cost significantly more: against the rule router, the agent AR-03 used {{RQ3.test.total_tokens.AR-03~AR-B1.delta}} and the trained router AR-01 {{RQ3.test.total_tokens.AR-01~AR-B1.delta}} tokens per question for the same answers.
3. **Answer quality is limited before the model sees the evidence.** At most {{RQ1.max.gold_coverage|pct}} of the correct papers reached the model's context in Part 1, and {{RQ2.support.UNSUPPORTABLE}} of the 24 fusion bundles contained no correct paper at all.
4. **Other strategies win in specific situations:** CM-01 when answer quality matters more than cost (F1 {{RQ1.CM-01.answer_f1}}, MRR {{RQ1.CM-01.mrr}}, at {{RQ1.ratio.input_tokens.CM-01/CM-B1}}× the tokens); CM-03 when every correct paper should reach the model (gold coverage {{RQ1.CM-03.gold_coverage}}); AR-03 when each search is expensive (wasted retrieval {{RQ3.AR-03.unnecessary_retrieval}}).
5. **Every number is reproducible.** Each study was frozen by checksum before it ran, every model request is stored, results are rebuilt by a replay that refuses any changed request, and the showcase bundle rebuilds byte for byte.
@end

## Main limitations

The cohorts are small (8 to 14 independent question families per study), the results are validation results rather than a locked test, the benchmark labels are verified by computation rather than by human reviewers, one answer model was used throughout, and some text questions use exact phrases that a meaning-based text retriever handles poorly. Chapter 32 discusses every limitation in detail.

# The project at a glance

## The pipeline that was studied

Every question flows through the same stages. Three of them are studied one at a time; the others stay fixed. The fourth study combines the best choice of each.

@figure figures/d_pipeline.png | The studied pipeline. A question passes through retrieval control (Part 3), the three fixed retrievers, context management (Part 1) and fusion (Part 2) before the shared answer model returns a set of paper IDs. Part 4 combines the best choice of each part. | 6.6

## Key numbers

Table: The project in numbers {w=2.6,1.4,2.6}
| Item | Value | Note |
|---|---:|---|
| Papers in the corpus | 700,244 | STaRK-MAG, official release |
| Entities (papers, authors, institutions, fields of study) | 1,872,968 | one global ID each |
| Official directed relations | 19,919,698 | writes, affiliated with, cites, has topic |
| Benchmark questions | 13,571 | train 8,049 · validation 2,721 · test 2,720 · human test 81 |
| Generated, programmatically verified questions | 167 | 42 base constructions × 4 variants, minus 1 |
| Independent question families used in the studies | 14 | 7 source combinations × 2 families (validation split) |
| Strategies compared | 15 + 1 | 5 per study for RQ1–RQ3, plus the integrated system |
| Run records analysed | 448 | RQ1 160 · RQ2 120 · RQ3 140 · RQ4 28; 0 errors |
| Automated tests | 327 | all passing when this document was built |
| Showcase application pages | 11 | 4 problem pages, 4 study pages, conclusions, try a question, reproducibility |

## What the project delivers

Table: Deliverables and where to find them {w=2.0,2.6,2.0}
| Deliverable | What it is | Location |
|---|---|---|
| Three-view dataset | Text, graph and structured representations of STaRK-MAG with manifests and audits | `data/MMG_STARK_MAG/` (not in Git; manifests in `documentation/phase3/`) |
| Benchmark | 13,571 questions with gold answers, stress overlays and a human-review package | `data/MMG_STARK_MAG/benchmark/`; protocol in `documentation/phase4/` |
| Research code | Contracts, data build, benchmark, evaluation harness, baselines, all studied methods | `research/`, `scripts/`, `configs/` |
| Study outputs | Frozen execution plans, run records, stored model calls and analyses for RQ1–RQ4 | `documentation/rq1_repair`, `documentation/rq2_repair`, `documentation/phase9`, `documentation/rq4` |
| Results package | Result tables, statistical tests, quality–cost figures and the overall ranking | `documentation/results/` |
| Paper draft | Research paper with abstract, methods, results, limitations | `documentation/paper/PAPER_DRAFT.md` |
| Decision log | Every scope and method decision with its evidence | `documentation/Research_Decision_Log.md` |
| Showcase application | Interactive 11-page presentation with recorded and live runs | `showcase/` |
| This documentation | The complete record, rebuilt from the frozen results by script | `documentation/project_documentation/` |
