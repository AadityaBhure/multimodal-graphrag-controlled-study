#! Part II · The problem

# Background: the ideas this project builds on

This chapter explains, in plain language, the concepts used throughout the document. Readers who know retrieval-augmented generation can skip to Chapter 4.

## Language models and retrieval-augmented generation

A large language model (LLM) writes text by predicting what comes next, based on what it learned during training and on the text it is given in its prompt. It cannot look up facts it was never shown, and it can state wrong facts confidently. **Retrieval-augmented generation (RAG)** reduces this risk: before the model answers, a retriever searches a document collection for evidence, and the evidence is placed in the prompt (the *context*). The model is instructed to answer only from that evidence.

A RAG system therefore has two halves. The retrieval half decides *what evidence* the model sees; the generation half decides *what answer* the model writes from it. A perfect model cannot answer correctly if the retriever never found the right evidence, and a perfect retriever is wasted if the evidence is presented badly or cut off.

In this project the model does not write free text. It must return a **set of paper IDs** in a strict JSON format, using only IDs that appear in its context, plus a short explanation. That makes answers exactly measurable: the returned set is compared with the verified set of correct papers.

## Three kinds of knowledge about the same papers

Knowledge about scientific papers comes in three very different shapes:

- **Text** — what a paper says: its title and abstract, written in natural language. It is searched by meaning (semantic similarity) or by words.
- **Graph** — how things are connected: authors write papers, authors are affiliated with institutions, papers cite papers, papers have topics (fields of study). It is searched by following relations from a starting entity.
- **Structured data** — facts recorded about a paper in table columns: publication year and date, citation count, rank, venue, document type. It is searched with exact conditions, such as "year ≥ 2015 and venue type = journal".

In this project **"multi-modal" means these three heterogeneous representations**, not images, audio or video. Each representation can check only part of a typical question, so many questions need two or three of them at once.

## GraphRAG

**GraphRAG** is the family of RAG systems that use a graph as (part of) their evidence. Instead of, or in addition to, retrieving text passages, the system finds entities in a knowledge graph, explores their neighbourhoods and gives the model relations and paths (for example "Author A writes Paper P; Paper P cites Paper Q"). Graph evidence is good at multi-step relational questions ("papers by authors at institution X") that text search handles poorly. Many published GraphRAG systems build their graph by extracting it from text; here the graph is the official relation data of the corpus, kept strictly separate from the text.

## Dense retrieval, embeddings and FAISS

A **sentence embedding model** turns a piece of text into a vector of numbers (here 384 numbers) so that texts with similar meaning get vectors that point in similar directions. **Dense retrieval** embeds the question and every document, then returns the documents whose vectors are most similar to the question's vector (the largest inner product of unit vectors, which equals cosine similarity). This project uses the `all-MiniLM-L6-v2` model, which reads at most 256 tokens of each document, and **FAISS**, a library for fast vector search; the index used here is exact (`IndexFlatIP`), so it compares the question with every one of the 700,244 papers rather than approximating.

Dense retrieval finds papers *about* a topic. It is weak at exact conditions, such as "the abstract contains the exact phrase *we derive analytical expressions*", because a paper with that exact phrase need not be the most similar in meaning.

## Graph traversal and CSR storage

Graph retrieval starts from **seed entities** that match names in the question (for example an institution), then follows relations outward. **Breadth-first search (BFS)** visits all neighbours at distance 1, then distance 2, and so on, up to a depth limit. The graph here has almost 40 million traversal entries, too large to load as a Python graph object, so it is stored in **compressed sparse row (CSR)** form: one array lists, for every node, where its neighbour list starts, and other arrays list the neighbours, the relation types and the edge IDs. The arrays are memory-mapped from disk, so only the parts that are visited are read.

## Structured retrieval with SQL

Structured data is stored in a **DuckDB** database (an embedded analytical SQL engine). Structured retrieval turns the conditions in a question into a **parameterised, read-only SQL query** (the condition values are passed as parameters, never pasted into the SQL text), so the query can neither modify data nor be injected with arbitrary SQL. Missing values are stored as SQL NULL and are never treated as zero.

## Context window, budget and tokens

A model reads its input as **tokens** (word pieces; roughly four characters of English per token). The amount it can read at once is its **context window**, and every token costs compute time. The project gives every method the same **context budget** of 24,000 characters (8,000 per source when the three sources have fixed shares). **Context management** decides which evidence survives that budget: what to keep, in what order, and what to drop. **Input tokens** (what the model reads) dominate the cost of a call; **output tokens** (what it writes) dominate its time.

## Fusion

When evidence comes from several sources, it must be combined into one context. The simplest **fusion** pastes the sources one after another. More elaborate fusion aligns evidence that describes the same entity, selects the most useful items from each source, or reasons over each source separately and then merges the conclusions ("late fusion"). Fusion decides *how* evidence is presented, not *what* is retrieved.

## Adaptive and agentic retrieval

Searching every source for every question is wasteful: a question about publication years needs only the structured data. **Adaptive retrieval** decides how much retrieval a question needs (none, one source, or several steps). **Corrective retrieval** checks whether retrieved evidence looks good enough and searches further only if it does not. **Agentic retrieval** gives a language-model "agent" tools (one per source) and lets it choose an action at each step, with a validator that checks whether a draft answer is supported. These policies trade extra model calls for fewer or better searches.

## Rerankers, cross-encoders and calibration

A **cross-encoder** reads a question and one evidence item together and outputs a relevance score. It is more accurate than comparing separate embeddings but slower, so it is used to **rerank** a short list. Its raw scores are not probabilities; **Platt calibration** fits a logistic curve that maps raw scores to probabilities on held-out data, so thresholds such as "probability ≥ 0.75" are meaningful.

## Steiner trees and flow diffusion

Two of the studied context-management methods use classic graph algorithms:

- A **prize-collecting Steiner tree (PCST)** chooses one connected subgraph that collects as much "prize" (relevance of nodes and edges to the question) as possible while paying a cost for every edge it includes. The result is small and connected.
- **Flow diffusion** places "mass" on seed nodes and lets it spread along edges, more easily along edges that are relevant to the question. Nodes that accumulate enough mass form a relevant region around the seeds.

## Text classifiers

A **classifier** maps an input to one of a few labels. One studied policy uses `t5-base`, a sequence-to-sequence model, fine-tuned to read a question and output one of three labels (no retrieval, one source, multi-step). It is trained on separate training questions with labels produced by an automatic "oracle" that checks which cheapest retrieval route would have found every correct paper.

# Problem statement

## Motivation

Real collections describe the same entities in different forms: prose (abstracts), explicit relations (who wrote what, who works where, who cites whom) and scalar facts (year, citations, rank, venue). A question such as "papers whose abstract says X, written by an author at institution Y, published in a journal with rank at most Z" needs all three. A system answering it must make three engineering decisions, and each can make or break the answer:

1. **Which sources to query, in what order, and when to stop** (retrieval control).
2. **How to combine evidence of different shapes** (fusion).
3. **How much and which evidence reaches the model** (context management).

Published systems usually change all three decisions at once and are evaluated on benchmarks that do not verify whether a question truly needs several sources. It is therefore unclear which decision made the difference, whether the elaborate techniques pay for their extra cost, and where answer quality is really lost.

## Formal statement

Let the corpus have three views of the same set of papers: a text view V_T (title and abstract), a graph view V_G (entities and official relations) and a structured view V_S (recorded attributes), joined only by a global paper ID. A question *q* has a verified correct answer set *G*(*q*), a set of paper IDs computed from the data (it may be empty). A system retrieves evidence from some of the views, builds a context within a fixed budget, and asks a fixed language model to return an answer set *A*(*q*) containing only paper IDs present in the context.

The goal is to choose the **retrieval-control policy**, the **context-management strategy** and the **fusion strategy** so that *A*(*q*) matches *G*(*q*) as closely as possible (answer F1, exact match), the correct papers reach the model early and completely (MRR, gold coverage), the right sources are queried (source-selection F1), and the cost is low (tokens, model calls, searches, latency). Each choice is evaluated while the others are held fixed; differences count only when a paired statistical test supports them.

## A worked example

The application's first page uses a real benchmark question that needs all three sources:

@callout note | Example question (TGS, validation split)
Which papers satisfy these requirements: the abstract explicitly includes at least one of "we derive an exact expression" or "we derive analytical expressions" (case-insensitive); and at least one author is affiliated with University of Insubria; and the recorded paper rank is at most 20071, and the recorded normalized venue namespace is journal?
@end

Each source can check only its own conditions. Computed on the frozen data before the question was worded:

Table: How many papers pass each condition of the example question {w=3.2,1.2}
| Conditions checked | Papers that pass |
|---|---:|
| Text only (the abstract contains one of the phrases) | 111 |
| Graph only (an author is affiliated with University of Insubria) | 479 |
| Structured only (rank ≤ 20071 and venue namespace = journal) | 130,859 |
| Text and graph | 2 |
| Text and structured | 12 |
| Graph and structured | 152 |
| **All three = the correct answer** | **1** |

The single correct paper is *Thermoelectric efficiency of three-terminal quantum thermal machines* (`stark:1258814`). Leaving out any one source lets wrong papers through: without the text condition 151 wrong papers would also qualify, without the graph condition 11, and without the structured condition 1. This is the property the benchmark verifies for every multi-source question ("strict source necessity").

@screen p01_problem__03 | The application's first page shows the example question with each condition highlighted in the colour of the source that can check it, the number of papers that pass each source alone, the overlap chart (logarithmic scale) and the counter-examples that prove every source is necessary. | 6.4

## Why the problem is hard

1. **Each source can check only part of a question,** so the answer lies in the overlap of several sources, and a retriever that misses one condition returns many wrong papers.
2. **Retrieved evidence is usually larger than a model can use well,** so something must decide what survives the budget.
3. **The three sources look completely different** (sentences, relations, table rows), so combining them is not obvious.
4. **Querying every source for every question is slow and wasteful,** but skipping a needed source loses the answer.
5. **Changing all of these at once makes it impossible to tell which change helped.**

## What counts as better

Table: Success criteria used throughout {w=1.4,4.6}
| Criterion | Measured by |
|---|---|
| Right answers | Answer F1 and exact match against the verified correct papers |
| Right evidence | Whether the correct papers reach the model (gold coverage) and how early they are ranked (MRR) |
| Right sources | Source-selection F1, wasted retrieval and stopping accuracy (retrieval control only) |
| Lower cost | Input and output tokens, model calls, retrieval calls and time per question |
| Proven differences | A difference counts only if a paired, family-clustered test supports it after Holm correction |

# Research gaps addressed

This chapter states the gaps in practice that motivated the study design. It is framed by the project's own design rationale, not by a systematic literature review, and makes no claim that no other work addresses these points. The project explicitly makes no novelty or state-of-the-art claim.

Table: Gaps and how the project addresses each {w=1.7,2.4,2.4}
| Gap | Why it matters | How this project addresses it |
|---|---|---|
| **1. Attribution.** Integrated systems change retrieval control, fusion and context handling at the same time. | When several components change together, an improvement (or a failure) cannot be attributed to any one of them. | One variable at a time: each study changes only one component while data, retrievers, model, prompt and budget stay fixed; integration comes last (Chapter 6). |
| **2. Mixed representations.** Graphs are often extracted from the same text that is also retrieved. | If the graph is derived from the text, "graph evidence" and "text evidence" overlap, and the value of each representation is unclear. | Three deliberately isolated views of one corpus, joined only by the official node ID; the graph uses official relations and titles only (Chapter 10). |
| **3. Unverified multi-source questions.** Benchmarks rarely prove that a "multi-hop" or "hybrid" question really needs every source. | A question that one source can answer alone does not test fusion or routing. | Gold answers computed before wording, and strict source necessity: dropping any required source provably enlarges the answer set, with counter-examples stored (Chapter 11). |
| **4. Robustness tested in isolation.** Noise, conflicting facts and unanswerable questions are seldom tested together. | A method can look good on clean questions and fail on realistic ones. | Every base question has normal, noisy, conflict and unanswerable variants, added as evaluation-time overlays that never change the canonical data (Chapter 11). |
| **5. Cost under-reported.** Quality is often reported without tokens, calls or latency. | An elaborate method that costs four times as much for no gain is not an improvement. | Every study reports tokens, model calls, searches and latency next to quality, computes Pareto sets and ranks methods on quality and cost together (Chapters 16 and 18). |
| **6. Dependent questions treated as independent.** Variants of one question are strongly correlated. | Treating 32 variants as 32 independent observations overstates certainty. | Paired, family-clustered statistics: bootstrap over families, exact sign-flip tests over family sums, Holm correction (Chapter 17). |
| **7. Irreproducible model runs.** Model outputs change between runs and services. | Results that cannot be replayed cannot be audited. | Every study is frozen by checksum before it runs; every model request and response is stored; results are rebuilt by a replay that refuses any changed request (Chapter 15). |

# Research questions and decomposition

## The four research questions

Table: The four research questions {w=0.7,2.2,1.5,1.9}
| RQ | Question | What changes | What stays fixed |
|---|---|---|---|
| **RQ1** Context management | How should retrieved graph evidence be selected, ordered and trimmed so that the answer survives a fixed budget? | How graph evidence is selected, ordered and pruned | The retrieved evidence; text and structured evidence (passed through unchanged); the answer model and prompt; the 24,000-character budget |
| **RQ2** Cross-modal fusion | How should evidence from text, graph and structured data be combined into one context? | How the three evidence streams are aligned, selected and combined | Every method receives the byte-identical cached evidence bundle and may not retrieve anything new; the answer model; the budget |
| **RQ3** Retrieval control | Can a policy decide which sources to query, in what order and when to stop, without losing answers? | The retrieval-control policy | The three retrievers; the context format (8,000 characters per queried source); the answer model and prompt |
| **RQ4** Integration | What happens when the best choice from each part is combined into one system? | The combination, chosen by a rule fixed before any result was known | The questions, data, retrievers and answer model |

## One variable at a time

The guiding principle is **one variable at a time first, integration second**. Inside a study, every strategy sees the same questions, the same evidence (or the same retrievers) and the same answer model, prompt and budget, so a difference between strategies can only come from the strategy. Three rules follow and are enforced in the code:

- Context management (RQ1) may not become a new retriever: it only selects, orders and trims graph evidence that was already retrieved.
- Fusion (RQ2) may not retrieve: every fusion method receives a byte-identical, cached evidence bundle.
- Retrieval control (RQ3) may not use stronger retrievers, fusion or context handling than its controls: all policies share the same tools and the same fixed downstream stack.

Each study compares **five strategies: two simple controls and three methods adapted from published systems.** The controls are deliberately simple (raw order, a fixed top-K, raw concatenation, source-separated sections, always-search-everything, a keyword rule router); a sophisticated method must beat them to be worth its cost.

## The strategies studied

Table: Inventory of studied strategies {w=0.75,1.7,1.9,2.2}
| ID | Name | Inspired by | Core idea |
|---|---|---|---|
| CM-B0 | Raw order | — (control) | Keep graph evidence in retrieved order until the budget is full |
| CM-B1 | Fixed top-K | — (control) | Keep the 5 best-ranked papers and the paths that reach them |
| CM-01 | KG²RAG-inspired | Knowledge Graph-Guided RAG (KG²RAG) | Seed relations, one-hop expansion, maximum spanning trees, depth-first writing, cross-encoder reranking |
| CM-02 | G-Retriever-inspired | G-Retriever (prize-collecting Steiner tree) | One small connected subgraph with the best prize minus cost |
| CM-03 | QAFD-RAG-inspired | Query-Aware Flow Diffusion for graph-based RAG | Relevance flows from keyword-matched seeds; keep the high-flow region |
| CF-B0 | Raw concatenation | — (control) | Paste text, graph and structured evidence one after another |
| CF-B1 | Source-separated | — (control) | Three labelled sections, each with a third of the budget |
| CF-01 | KAG-inspired entity alignment | KAG (knowledge-augmented generation) | Group all evidence about the same entity before writing the context |
| CF-02 | SAG-inspired dual-path selection | SAG (SQL-retrieval augmented generation with dynamic hyperedges) | The model selects up to 5 structural items; text fills the remaining slots |
| CF-03 | MegaRAG-inspired late fusion | MegaRAG (multimodal knowledge-graph RAG) | Reason over each source separately, then fuse the findings |
| AR-B0 | Always search everything | — (control) | Query text, graph and structured for every question |
| AR-B1 | Rule router | — (control) | Fixed keyword cues decide which sources a question needs |
| AR-01 | Adaptive-RAG-inspired | Adaptive-RAG (query-complexity routing) | A trained classifier picks no retrieval, one source or multi-step |
| AR-02 | CRAG-inspired | Corrective RAG (CRAG) | A calibrated evaluator decides whether to search further |
| AR-03 | AGENT-G-inspired | AGENT-G (agentic graph RAG) | An agent picks one tool per step; a validator checks the draft answer |
| INT-1 | Integrated system | — | The selected policy, CM-B1 and the selected fusion method in one pipeline |

All methods are *adaptations* of the published mechanisms, re-implemented under one frozen interface. The project makes no claim to reproduce the original systems; training-heavy parts of some originals (for example graph neural networks or large fine-tuned evaluators) are replaced or omitted, and every adaptation is documented in the method sections of Part VII.

## Scope and non-goals

- **In scope:** text, graph and structured views of STaRK-MAG; generated, programmatically verified validation questions; five strategies per component; one integrated system; quality, cost and statistical analysis; a presentation application.
- **Out of scope:** images, audio or video; claims of novelty or state-of-the-art performance; the locked test set (it requires 2,801 human review decisions that have not been made); tuning any setting after seeing results; comparisons with published numbers from other papers.
