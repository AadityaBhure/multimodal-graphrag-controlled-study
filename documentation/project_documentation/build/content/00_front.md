@titlepage

#* Document information

This document is the complete record of the Multi-Modal GraphRAG project, from the first commit to the finished showcase application. It explains the problem, the gaps the project addresses, every algorithm that was studied and how it works, the data, the benchmark, the metrics, the statistics, every result and its interpretation, the history of decisions, and the web application built to present the work. Explanations move from the high level (what and why) to the low level (exact settings, formulas and file names).

Table: Document facts {w=1.6,4.6}
| Item | Value |
|---|---|
| Project | Multi-Modal GraphRAG: a controlled study of how a retrieval-augmented language model should use text, graph and structured views of the same scientific corpus |
| Author | Aaditya Bhure |
| Period covered | 4 October 2026 (first commit) to 18 October 2026 (this document) |
| Repository | `D:/codefiles/RAG_GraphRAG_Demo` (branch `master`, commit `7e3cfa5`) |
| Answer model | `gpt-oss:20b`, served locally with Ollama 0.40.5, for every method and every study |
| Status of results | Validation results on frozen, programmatically verified questions. The locked test set is out of scope. |
| Where the numbers come from | The frozen analysis file of each study, exported into the checksummed showcase data bundle (`showcase/bundle`, SHA-256 `d864377175cf…`). Placeholders in the source text are bound to that bundle when this document is built, so no study number is typed by hand. |
| Verification when this document was built | Full test suite: 327 passed. Showcase bundle rebuild: byte-identical. |
| How to rebuild this document | `documentation/project_documentation/build/` (see Appendix I) |

#* How to read this document

The document follows the order in which the work was done and in which it should be understood: the problem, how it was split into parts, the data, the system, the measures, the four studies, the combined result, and finally the application that presents everything. Each part starts with a short overview, so a reader can stop at any depth.

Table: Reading paths {w=1.8,4.4}
| If you want to… | Read |
|---|---|
| Understand the project and its answer in ten minutes | Chapter 1 (Executive summary) and Chapter 23 (Combined result) |
| Present the work live | Part VIII (the showcase application), especially Chapter 27 (page-by-page guide) and Chapter 30 (presentation script) |
| Understand the research | Parts II to VII in order |
| Understand one algorithm | The method sections of Chapters 19 to 22; each has a plain-language idea, the exact steps, the frozen settings and a flowchart |
| Reproduce or audit a number | Part V (system and execution protocol), Part VI (metrics and statistics) and Appendices B, C, D, H and I |

#### Conventions

- **Method identifiers.** CM = context management (Part 1, RQ1), CF = cross-modal fusion (Part 2, RQ2), AR = adaptive retrieval control (Part 3, RQ3), INT-1 = the integrated system (Part 4, RQ4). Suffix B0 and B1 mark the two simple controls of a study; 01, 02 and 03 mark the three methods adapted from published systems. B1 to B4 without a prefix are the four retrieval baselines.
- **Parts and research questions.** "Part 1" in the application is RQ1, "Part 2" is RQ2, and so on. Both names are used.
- **Number formats.** Rates and scores have three decimals (0.283); token counts are whole numbers with thousands separators (4,982); latency is in seconds with one decimal (17.8 s); p-values have three decimals; differences carry an explicit sign (+0.014, −772). Rounding is half-up.
- **Arrows and stars.** ↑ means higher is better and ↓ means lower is better. ★ marks a Pareto-optimal method (no other method is at least as good on every axis and strictly better on one).
- **Significant.** A difference is called significant only when its Holm-adjusted p-value is below 0.05. Otherwise the text says "not significant", even when one mean is larger.
- **Family.** The variants of one base question (normal, noisy, conflict, unanswerable) form a family; families, not questions, are the independent units in every statistical test.
- **NULL is not zero.** A measure that was not observed is reported as "n/a", never as 0.

#~ Contents

@toc

#~ List of figures

@lof

#~ List of tables

@lot
