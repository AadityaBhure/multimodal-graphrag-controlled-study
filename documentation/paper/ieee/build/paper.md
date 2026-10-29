%title Multi-Modal GraphRAG: A Controlled Study of Context Management, Cross-Modal Fusion, and Retrieval Control over Text, Graph, and Structured Knowledge
%author Aaditya Bhure
%affil Department and institution to be completed
%email aadityabhure001@gmail.com

@abstract
Retrieval-augmented generation (RAG) increasingly draws on heterogeneous knowledge: unstructured text, knowledge graphs, and structured records. Integrated systems, however, change how sources are queried, how evidence is fused, and how the context is managed all at once, so it remains unclear which design decision matters. We present a controlled, one-variable-at-a-time study of multi-modal GraphRAG. We build MMG-STaRK-MAG, three strictly isolated views (text, graph, structured) of the STaRK-MAG scholarly corpus (700,244 papers, 1.87 M entities, 19.9 M relations) joined only by a global identifier, and a benchmark whose answers are computed before questions are worded and whose multi-source questions provably require every source. With frozen retrievers and one locally served language model, we compare five strategies each for context management, cross-modal fusion, and retrieval control (two simple controls and three adaptations of published methods per component), and then integrate the winners. Every model call is stored and replay-verified, and differences are tested with family-clustered paired statistics and Holm correction. No literature-inspired method improved answer quality with statistical support. A deterministic rule router selected sources significantly better than querying every source (source-selection F1 {{RQ3.AR-B1.source_f1}} vs. {{RQ3.AR-B0.source_f1}}, Holm-adjusted *p* {{RQ3.test.source_f1.AR-B1~AR-B0.p_holm|peq}}) at the lowest cost, whereas learned and agentic controllers spent up to {{RQ3.test.total_tokens.AR-03~AR-B1.delta|abs}} more tokens per question for identical answers. Ranking methods jointly on quality and cost yields one winner per component (fixed top-K context, source-separated fusion, rule routing) whose combination equals the pre-registered integrated system. Answer quality is bounded upstream: on average at most {{RQ1.max.gold_coverage|pct}} of the correct papers reached the model's context, and {{RQ2.support.UNSUPPORTABLE}} of 24 fusion bundles contained none.
@end
@keywords Retrieval-augmented generation, GraphRAG, knowledge graphs, heterogeneous data fusion, context management, adaptive retrieval, LLM agents, controlled experiments, reproducibility.

# Introduction {#sec:intro}

Large language models (LLMs) answer questions fluently but cannot consult facts they were never shown, and they can state wrong facts with confidence. Retrieval-augmented generation (RAG) addresses this by retrieving evidence from an external collection and asking the model to answer from that evidence [@lewis2020;gao2023]. Real collections, however, describe the same entities in several forms. A scholarly corpus contains what each paper *says* (its title and abstract), how papers and people are *connected* (authorship, affiliation, citation, topic), and facts *recorded* about each paper (publication year, citation count, rank, venue). A question such as "papers whose abstract states *X*, written by an author affiliated with institution *Y*, published in a journal with a rank of at most *Z*" needs all three representations at once.

A system that answers such questions must make three design decisions. It must decide **which sources to query, in what order, and when to stop** (retrieval control); **how to combine evidence of very different shapes** (cross-modal fusion); and **which evidence survives a limited context budget** (context management). Each decision has attracted elaborate methods: graph-based context construction [@he2024gretriever;zhu2025kg2rag;zhou2026qafd], knowledge-aligned or late fusion [@liang2024kag;wu2026sag;hsiao2025megarag], and adaptive, corrective, or agentic retrieval control [@jeong2024adaptive;yan2024crag;agentg2025]. Yet each method is usually proposed inside its own pipeline and evaluated on its own corpus, retrievers, model, prompt, and budget. Integrated systems change several decisions at once, so a reported gain cannot be attributed to any single component, and numbers from different papers are not comparable.

This paper isolates each decision. We freeze the corpus, the retrievers, the language model, the prompt, and the context budget; vary one component at a time against deliberately simple controls; and only then integrate the best choices. We ask four research questions:

- **RQ1 (context management).** How should retrieved graph evidence be selected, ordered, and trimmed so that the answer survives a fixed context budget?
- **RQ2 (cross-modal fusion).** How should evidence from text, graph, and structured sources be combined into one context?
- **RQ3 (retrieval control).** Can a policy decide which sources to query, in what order, and when to stop, without losing answers?
- **RQ4 (integration).** What is the combined effect of the best choice for each component?

[[fig:framework]] summarizes the framework. In every study the answer is a set of paper identifiers that can be scored exactly against a verified answer set, and every comparison reports quality and cost together with paired statistics that respect the correlation between variants of the same question.


## Key Highlights

The study has the following distinctive features.

@fig framework | fig_framework.png | Overview of the controlled framework. Three isolated views of one corpus feed three fixed retrievers. Retrieval control (RQ3), context management of graph evidence (RQ1), and cross-modal fusion (RQ2) are studied one at a time under a shared language model; the best choice of each is then combined (RQ4). The evaluation layer computes quality and cost metrics and family-clustered paired tests. | wide | 7.0

- **Isolated, identity-joined views.** Text, graph, and structured representations of the same 700,244 papers share nothing except the official node identifier, so any benefit of combining sources is a real benefit of combining them.
- **Verified-by-construction benchmark.** Gold answers are computed from the frozen data before any question is worded; for every multi-source question, dropping any required source provably enlarges the answer set; noisy, conflicting, and unanswerable variants are added as evaluation-time overlays that never alter the canonical data.
- **One variable at a time.** Fifteen strategies (nine adaptations of published methods and six simple controls) are compared under one frozen interface, and an integrated system is built by a selection rule fixed before any result was known.
- **Replay-verified execution.** Every model request is stored under the hash of its full payload, and results are rebuilt by a runner that refuses to proceed if any request differs; the four studies ({{RQ1.cohort.queries}}, {{RQ2.cohort.queries}}, {{RQ3.cohort.queries}}, and {{RQ4.cohort.queries}} questions; 16 strategies) produced 448 run records with 0 errors.
- **Correlation-aware statistics.** Paired differences are tested with family-clustered bootstrap intervals and exact sign-flip tests with Holm correction [@holm1979;efron1993;cameron2008], complemented by Pareto analysis and a transparent overall ranking.
- **A clear, practical answer.** The simplest strategy wins every component on combined quality and cost, the integrated system inherits the router's significantly better source selection, and the dominant limitation is located upstream, in retrieval coverage.
- **Open and inspectable.** All figures and tables are regenerated from checksummed study outputs, and an interactive application replays every recorded run step by step.

## Organization of the Paper

[[sec:lit]] reviews related work, compares it with the problem studied here, and identifies the research gaps. [[sec:method]] formalizes the data, the pipeline, and every strategy, and describes how the problem was solved: the execution protocol, metrics, and statistics. [[sec:results]] reports and discusses the results. [[sec:conclusion]] concludes and lists limitations and future work, and [[sec:availability]] describes data and code availability.

# Literature Review {#sec:lit}

## Related Work

### Retrieval-augmented generation
RAG couples a retriever with a generator so that answers are conditioned on retrieved evidence [@lewis2020]; surveys organize the many variants that followed [@gao2023]. Two observations from this line of work motivate context management: models use long contexts unevenly, attending less to evidence in the middle of the input [@liu2024lost], and compressing or selecting evidence can reduce cost while preserving answers [@jiang2024longllmlingua]. Active and self-reflective variants decide during generation whether and what to retrieve [@jiang2023flare;asai2024selfrag].

### Graph-based RAG
GraphRAG systems retrieve entities, relations, and paths from a knowledge graph. GraphRAG [@edge2024graphrag] builds an entity graph from text with an LLM and summarizes graph communities; G-Retriever [@he2024gretriever] selects a compact subgraph with a prize-collecting Steiner tree [@goemans1995;hegde2015pcst]; KG²RAG [@zhu2025kg2rag] expands semantically retrieved seeds through a knowledge graph and organizes them into connected, reranked paragraphs; QAFD-RAG [@zhou2026qafd] lets relevance flow through the graph along query-aware edge weights, building on local flow diffusion [@fountoulakis2020flow]; Think-on-Graph [@sun2024tog] lets the LLM explore the graph by beam search; and HippoRAG [@gutierrez2024hipporag] uses personalized graph propagation as long-term memory. A recent survey reviews the area [@peng2024survey].

### Fusion of heterogeneous knowledge
Several systems combine unstructured and structured knowledge. UniK-QA [@oguz2022unikqa] linearizes tables and knowledge-base triples into text; StructGPT [@jiang2023structgpt] lets the LLM reason over structured interfaces; HybridRAG [@sarmah2024hybridrag] concatenates vector and graph retrieval; KAG [@liang2024kag] aligns knowledge-graph entities with source chunks through mutual indexing; SAG [@wu2026sag] indexes events and entities in SQL and selects structural evidence at query time; MegaRAG [@hsiao2025megarag] reasons over each modality before a final fusion stage; and query-driven multimodal GraphRAG [@bu2025qdmm] builds local graphs on demand from text, tables, and images.

### Adaptive and agentic retrieval control
Adaptive-RAG [@jeong2024adaptive] trains a small classifier to route each question to no retrieval, single-step, or multi-step retrieval; CRAG [@yan2024crag] scores retrieved evidence with a lightweight evaluator and triggers corrective actions; interleaved reasoning and retrieval [@trivedi2023ircot] and reasoning-acting agents [@yao2023react] decide the next retrieval step from intermediate reasoning; AGENT-G [@agentg2025] equips an agent with a retriever bank and a critic of validator and commentor roles for hybrid textual and relational questions; and agent-orchestrated adaptive RAG [@maharjan2026agent] adds decomposition and bounded reflection.

### Benchmarks and evaluation methodology
STaRK [@wu2024stark] evaluates retrieval over semi-structured knowledge bases, including an academic base derived from the Microsoft Academic Graph [@wang2020mag], which is the source corpus of this study. Methodological work in NLP stresses significance testing and the danger of treating dependent samples as independent [@dror2018]; clustered resampling [@cameron2008], exact permutation tests [@good2005], and family-wise error control [@holm1979] address these concerns.

## Comparison With the Current Research Problem

[[tab:lit]] positions representative works with respect to the problem studied here: the component they address, the knowledge they use, their core mechanism, and their role in this study. The nine mechanisms marked in the last column are re-implemented as adaptations under one frozen interface (Sections III-D to III-F); the remaining works inform the design.

@table lit | Representative related work and its relation to the present study | wide | 1.15,1.0,0.75,2.55,1.05
| Work | Focus | Knowledge | Core mechanism | Role here |
|---|---|---|---|---|
| RAG [@lewis2020] | retrieve and generate | text | dense retrieval conditioning a generator | baseline B1 |
| GraphRAG [@edge2024graphrag] | graph construction | text → graph | LLM-extracted entity graph, community summaries | design input |
| G-Retriever [@he2024gretriever] | context management | graph | prize-collecting Steiner tree subgraph (+ GNN soft prompt) | CM-02 |
| KG²RAG [@zhu2025kg2rag] | context management | text + graph | seed expansion, spanning-tree organization, reranking | CM-01 |
| QAFD-RAG [@zhou2026qafd] | context management | graph | query-aware flow diffusion from keyword seeds | CM-03 |
| Think-on-Graph [@sun2024tog] | retrieval control | graph | LLM beam search over the knowledge graph | design input |
| KAG [@liang2024kag] | fusion | text + graph | mutual indexing, entity alignment, logical forms | CF-01 |
| SAG [@wu2026sag] | fusion | text + structured | event–entity SQL index, query-time selection | CF-02 |
| MegaRAG [@hsiao2025megarag] | fusion | text + graph + image | per-modality reasoning, then late fusion | CF-03 |
| QD multimodal GraphRAG [@bu2025qdmm] | integrated | text, graph, table, image | query-driven local graph construction | design input |
| Adaptive-RAG [@jeong2024adaptive] | retrieval control | text | complexity classifier routes retrieval depth | AR-01 |
| CRAG [@yan2024crag] | retrieval control | text | retrieval evaluator triggers corrections | AR-02 |
| AGENT-G [@agentg2025] | retrieval control | text + graph | agent, retriever bank, validator and commentor | AR-03 |
| STaRK [@wu2024stark] | benchmark | text + relations | retrieval over semi-structured knowledge bases | source data |
| **This study** | **all three, then integration** | **text, graph, structured (isolated)** | **controlled comparison of 15 strategies + 1 integrated system** | — |

The comparison exposes the gap between these works and the research problem. Each mechanism was proposed for a different combination of sources and evaluated inside its own system, so the literature offers many candidate answers to RQ1–RQ3 but no common ground on which to compare them. The problem studied here requires (i) the three knowledge forms to be available as separate sources over the same entities, (ii) questions whose answers provably need several sources, (iii) every candidate strategy to run against identical evidence, retrievers, model, prompt, and budget, and (iv) quality and cost to be judged together with statistics suited to small, correlated question sets.

## Review Outcome

The review leads to four outcomes (RO).

- **RO1. Effects are not attributable.** Mechanisms for the three components are evaluated inside different systems with different corpora, retrievers, models, prompts, and budgets; reported gains cannot be attributed to one component or compared across papers.
- **RO2. Sources are often entangled.** When a graph is extracted from the same text that is also retrieved, graph and text evidence overlap, and the value of each representation is confounded.
- **RO3. Multi-source questions are rarely verified.** Benchmarks seldom guarantee that every listed source is necessary for a question, and robustness to distractors, conflicting facts, and unanswerable questions is seldom tested together with source necessity.
- **RO4. Cost and uncertainty are under-reported.** Elaborate controllers add model calls and tokens, yet quality is often reported without cost, and small sets of related question variants call for correlation-aware significance testing [@dror2018].

## Problem Identification

The review outcomes translate into four research gaps (RG), one per research question ([[tab:gaps]]). RG1–RG3 concern the three pipeline components and RG4 their combination; the methods that address them are presented in Sections III-D to III-G.

@table gaps | Research gaps derived from the review and how they are addressed | col | 0.55,1.75,0.7
| Gap | Description | Addressed by |
|---|---|---|
| RG1 | No controlled comparison of graph-context strategies under a fixed budget with identical evidence | RQ1, [[sec:cm]] |
| RG2 | No controlled comparison of fusion strategies on byte-identical multi-source evidence | RQ2, [[sec:cf]] |
| RG3 | No controlled comparison of source-selection policies with the same retrievers and context format | RQ3, [[sec:ar]] |
| RG4 | Unknown combined effect of empirically chosen components | RQ4, [[sec:int]] |

**Problem statement.** Let a corpus offer a text view, a graph view, and a structured view of the same papers, joined only by a global identifier. Each question $q$ has a verified answer set $G(q)$ of paper identifiers, possibly empty. A system queries some of the views, builds a context within a fixed budget, and asks a fixed LLM for an answer set $A(q)$ that may only contain identifiers present in the context. For each component in turn, with all others held fixed, find the strategy that makes $A(q)$ match $G(q)$ most closely while keeping cost (tokens, model calls, searches, latency) low; accept a difference only when a paired, correlation-aware test supports it; and finally measure the combination of the chosen strategies.

[[fig:example]] illustrates why such questions are hard. In a validation question requiring all three sources, each source alone admits between 111 and 130,859 papers, while exactly one paper satisfies all conditions; removing any single source admits between 1 and 151 wrong papers.

@fig example | fig_example.png | Candidate papers that satisfy the conditions of one three-source benchmark question, per source and per intersection (log scale). Only the paper in the triple intersection is correct; every source is necessary. | col | 3.3

# Method {#sec:method}

## Overview: What Is Studied and How {#sec:overview}

*What* is studied are the three components of a multi-source RAG pipeline (retrieval control, context management, and fusion) and their combination. *How* they are studied is a controlled protocol: in each study exactly one component varies across five strategies while the data, retrievers, LLM, prompt, and budget stay fixed; the study is frozen by checksum before it runs; every model call is stored and replay-verified; and differences are tested with paired, family-clustered statistics. We write T, G, and S for the text, graph, and structured sources and TG, TS, GS, and TGS for the combinations that a question requires. [[tab:design]] lists the four study designs.

## Data Modeling {#sec:data}

### Three isolated views
Let $𝒩$ be the set of entities of STaRK-MAG [@wu2024stark;wang2020mag], each with a global identifier, and $𝒫⊂𝒩$ its papers. The **text view** $V_T$ holds one document per paper, the exact title followed by the abstract, embedded with a frozen MiniLM sentence encoder [@reimers2019sbert;wang2020minilm] (384 dimensions, 256-token input) and indexed exactly with FAISS [@johnson2021faiss]. The **graph view** $V_G=(𝒩,ℰ)$ holds the four official relation types (writes, affiliated-with, cites, has-topic), where a paper's label is its title only; each of the 19,919,698 directed edges also receives a tagged inverse row for traversal, stored as memory-mapped compressed sparse rows. The **structured view** $V_S$ is a DuckDB table [@raasveldt2019duckdb] of nullable paper attributes (year, date, citation count, rank, venue, document type), in which missing values remain NULL. The views share nothing except the identifier: the text view contains no authors, years, or venues, the graph view contains no abstracts or attributes, and the structured view contains no text or relations. [[tab:data]] summarizes the corpus and the benchmark.

### Verified multi-source questions
Each generated question $q$ requires a set of sources $M(q)⊆{T,G,S}$. For each required source $m$, a condition is evaluated on the frozen view before any wording, giving a candidate set $C_m (q)$: an exact abstract phrase for text, an authorship, affiliation, or citation path for the graph, and parameterized predicates for structured data. The gold set is their intersection,

@eq gold | G(q)=⋂_(m∈M(q))▒C_m (q)

and every multi-source question must satisfy **strict source necessity**:

@eq necessity | ∀m∈M(q):  G_(−m) (q)=⋂_(m'∈M(q)∖{m})▒C_(m') (q)⊋G(q)

Questions are worded from templates and never contain an answer identifier or title. Each base question has up to four **variants**: normal; *noisy*, which adds hard distractors that fail one condition; *conflict*, which adds one altered fact about a correct paper while the canonical record stays authoritative; and *unanswerable*, which adds a provably disjoint condition so that $G(q)=∅$. The variants of one base question form a **family**, the independent unit of all statistics. [[alg:bench]] summarizes the construction; an independent audit recomputed every gold set, all 665,671 candidate identifiers, and all 2,336 witness paths, and a full regeneration reproduced all benchmark files byte for byte.

@table design | Design of the four studies (all questions are programmatically verified validation questions) | wide | 0.55,1.65,1.55,2.15,1.6
| Study | Cohort | What changes | What stays fixed | Metrics |
|---|---|---|---|---|
| RQ1 | 32 questions: 8 families (2 each for G, TG, GS, TGS) × 4 variants (normal, noisy, conflict, unanswerable) | selection, order, and pruning of graph evidence | graph candidate pool; text and structured evidence passed through; LLM; prompt; 24,000-character budget | F1 (primary); MRR, gold coverage, tokens, latency |
| RQ2 | 24 frozen bundles: 8 families (2 each for TG, TS, GS, TGS) × 3 variants (normal, noisy, conflict) | combination of text, graph, structured evidence | byte-identical bundles, no retrieval; LLM; prompt; 24,000-character budget | F1 (primary); EM, MRR, model calls, tokens, latency |
| RQ3 | 28 questions: 14 families (2 for each of the 7 source combinations) × 2 variants (normal, noisy) | which source, in which order, when to stop | retrievers B1–B3; 8,000 characters per queried source; LLM; prompt | F1 (primary); source-selection F1, wasted retrieval, stopping accuracy, calls, tokens, latency |
| RQ4 | the 28 questions of RQ3 | combination of the selected components | questions, data, retrievers, LLM, prompt | F1 (primary); source-selection F1, tokens, latency |

@table data | Corpus (MMG-STaRK-MAG) and benchmark statistics | col | 1.55,1.45
| Item | Value |
|---|---:|
| Papers / authors | 700,244 / 1,104,554 |
| Institutions / fields of study | 8,701 / 59,469 |
| Official directed relations | 19,919,698 |
| writes / affiliated / cites / has-topic | 6.77 M / 1.03 M / 4.88 M / 7.24 M |
| Graph traversal rows (with tagged inverses) | 39,839,396 |
| Structured rows / with missing attributes | 700,244 / 22,049 |
| Benchmark questions | 13,571 |
| train / validation / test / human test | 8,049 / 2,721 / 2,720 / 81 |
| Generated, verified questions | 167 |
| Validation families used | 14 (7 combinations × 2) |

## Retrieval and Generation Model {#sec:pipeline}

All strategies share three deliberately simple retrievers, each returning its top five results. **B1** embeds the question and returns the five most similar papers from the exact FAISS index. **B2** resolves up to three seed entities from graph labels and traverses breadth-first to depth 2 under fixed caps (2,000 nodes, 20,000 scanned edges, 128 edges per node), returning the five best-ranked papers with their paths. **B3** parses supported conditions into a typed conjunctive plan compiled into parameterized, read-only SQL. A fourth baseline, **B4**, runs all three and writes their evidence in fixed sections. None of them reranks, rewrites queries, or falls back to another source.

@alg bench | Verified multi-source question construction
Input: frozen views $V_T,V_G,V_S$; source combination $M$; split; seed 42
Output: question $q$, gold set $G(q)$, stress variants
choose one condition per $m∈M$ from split-exclusive anchors
**for each** $m∈M$ **do** compute $C_m (q)$ on the frozen view (sorted, hashed)
$G(q)←⋂_m▒C_m (q)$
**for each** $m∈M$ **with** $|M|>1$ **do**
> **if** $G_(−m) (q)=G(q)$ **then reject** the construction **else** store counter-examples
word $q$ from a template (no answer identifiers or titles)
add overlays: noisy distractors, one conflicting fact, one disjoint condition ($G=∅$)
recompute all sets independently; regenerate and compare bytes
**return** $q$, $G(q)$, variants
@end

Writing $π$ for the retrieval-control policy, $κ$ for context management of graph evidence, $φ$ for fusion, and $g$ for the LLM, a question is answered as

@eq pipeline | A(q)=g(q,φ(E_T,κ(E_G),E_S)),  E=⋃_(t=1)^k▒ℛ_(s_t) (q_t)

where $π$ chooses the source $s_t$ and query $q_t$ of each step $t$ and the number of steps $k$, and the evidence of each source is collected in $E_T$, $E_G$, and $E_S$. The serialized context must satisfy $|"ser"(c)|≤B$, with $B$ = 24,000 characters. The LLM is **gpt-oss:20b** [@openai2025gptoss], served locally by Ollama 0.40.5 [@ollama] with temperature 0, a per-question seed, low reasoning effort, JSON output, and a 1,024-token completion cap for every call. A single grounding prompt instructs it to answer only from the evidence, to require every condition, to treat NULL as unknown, and to prefer canonical records over tagged overlays. A strict parser accepts only integer paper identifiers present in the context; anything else is recorded as a failure, and an empty set is a valid abstention.

## RG1 → RQ1: Context Management Strategies {#sec:cm}

Context management decides which graph evidence reaches the model. All five strategies receive the same bounded candidate pool per question (a depth-2 neighbourhood of B2's seeds with at most 256 base nodes and 1,024 base edges), and text and structured evidence pass through unchanged. [[fig:cm]] illustrates the five strategies on a toy graph.

@fig cm | fig_rq1_methods.png | The five context-management strategies of RQ1 on a schematic candidate graph for the question "papers with an author affiliated with institution I". Filled nodes and dark edges are kept in the context. (a) Raw order keeps records until the budget is full. (b) Fixed top-K keeps the five best-ranked papers and their paths. (c) KG²RAG-inspired: seed relations, one-hop expansion, and maximum spanning trees (thick edges), reranked. (d) PCST-inspired: one connected subgraph trading prizes (★) against edge costs. (e) Flow diffusion: mass spreads from keyword seeds (red rings); nodes above a threshold are kept. | wide | 7.0

**CM-B0 (raw order)** writes node and edge records in candidate order and stops at the first record that does not fit. **CM-B1 (fixed top-K)** keeps the first five papers in retriever order (path length, seed rank, identifier) together with the parent paths that connect them to their seeds, serialized depth-first.

**CM-01 (KG²RAG-inspired)** [@zhu2025kg2rag]. The original links text chunks to the graph triples extracted from them; STaRK provides no such provenance, so we use *graph-native provenance units*: one sentence per official relation, written from labels and identifiers only (e.g., "Author *a* writes Paper *p*."). With MiniLM embeddings $𝐡$, each unit $u_e$ of edge $e$ is weighted by its similarity $w(e)=cos(𝐡_q,𝐡_(u_e))$ to the question, the ten best units become seeds, the graph is expanded by one hop inside the pool, and each connected component $K_k$ is organized as a maximum spanning tree computed with Kruskal's algorithm [@kruskal1956]:

@eq mst | T_k=〖"arg max"〗_(T∈𝒯(K_k))⁡〖∑_(e∈T)▒w(e)〗

Each tree is written depth-first from its highest-weight edge, scored with a BGE cross-encoder reranker [@xiao2024cpack], deduplicated, and packed into the budget in rank order ([[alg:cm01]]).

**CM-02 (G-Retriever-inspired)** [@he2024gretriever]. The three nodes and five edges most similar to the question receive rank prizes $π$ (3, 2, 1 and 5 to 1); every edge costs $c_e=0.5$; and the prize-collecting Steiner tree problem [@goemans1995]

@eq pcst | T^*=〖"arg min"〗_T⁡〖(∑_(e∈E(T))▒c_e+∑_(v∉V(T))▒π_v)〗

is solved with the pcst_fast solver [@hegde2015pcst] (unrooted, one tree, edge prizes via virtual nodes). The resulting connected subgraph is written breadth-first and trimmed leaf by leaf to the budget. The original's graph neural network and soft prompt are omitted.

@alg cm01 | CM-01 graph-native KG²RAG context construction
Input: question $q$, candidate pool $(𝒱,ℰ)$, budget $B_G$
Output: graph context
build one provenance unit $u_e$ per official edge $e∈ℰ$ (labels and identifiers only)
score $w(e)=cos(𝐡_q,𝐡_(u_e))$; seeds $←$ the 10 best units
expand one hop around the seeds inside the pool
**for each** connected component $K_k$ **do**
> $T_k←$ maximum spanning tree of $K_k$ under $w$ (Kruskal; ties by unit ID)
> serialize $T_k$ depth-first from its highest-weight edge
rank the trees with the cross-encoder; remove duplicate units
**return** trees in rank order while they fit in $B_G$
@end

**CM-03 (QAFD-RAG-inspired)** [@zhou2026qafd]. One LLM call extracts the question's keywords; the 20 nodes most similar to any keyword become seeds with mass 10 each. With the non-negative cosine similarity

@eq hsim | H(a,b)=(1+cos(𝐡_a,𝐡_b))/2

mass is pushed along edges with query-aware conductance

@eq conductance | w(u,v)=H(u,v)(1+1/4 (H(u,q)+H(v,q)))

where every node can retain at most one unit of mass (sink capacity), following local flow diffusion [@fountoulakis2020flow]. Diffusion stops when the total excess is at most $ε=0.05$ or after $10^6$ pushes. With the excess and the support

@eq support | "ex"(v)=max(0,x_v−1),  𝒮={v:x_v>τ}

for $τ=0.01$, the support plus the connectors between its nodes is pruned from the outside in until it fits ([[alg:cm03]]).

## RG2 → RQ2: Cross-Modal Fusion Strategies {#sec:cf}

Fusion decides how the three evidence streams are presented. To isolate it completely, every method receives the **byte-identical cached evidence bundle** of each question (the top-5 evidence of B1, B2, and B3 plus the variant's overlays) and may not retrieve. [[fig:cf]] contrasts the context layouts.

@fig cf | fig_rq2_methods.png | Context layouts of the five fusion strategies of RQ2 on the same evidence bundle. (a) Raw concatenation in source order, cut at the budget. (b) Three labelled sections with a third of the budget each. (c) Evidence grouped by aligned entity. (d) An LLM selects up to five structural items; text fills the remaining slots. (e) One reasoning call per source, then a grounded fusion call. | wide | 7.0

@alg cm03 | CM-03 query-aware flow diffusion
Input: question $q$, candidate pool, budget $B_G$
Output: graph context
keywords $←$ LLM($q$) (one call, strict JSON)
seeds $←$ 20 nodes with the highest keyword similarity; $x_v←10$ for each seed
**while** $∑_v▒"ex"(v)>ε$ **and** pushes $<10^6$ **do**
> $v←$ node with the largest excess (ties by ID)
> push $"ex"(v)$ to neighbours in proportion to $w(v,u)$ from [[eq:conductance]]
$𝒮←{v:x_v>τ}$ plus connector nodes
prune the lowest-mass outer nodes of $𝒮$ until it fits $B_G$
**return** serialized $𝒮$
@end

**CF-B0 (raw concatenation)** writes all items in source order until the budget is reached. **CF-B1 (source-separated)** writes labelled TEXT, GRAPH, and STRUCTURED sections, each limited to 8,000 characters.

**CF-01 (KAG-inspired entity alignment)** [@liang2024kag] attaches every evidence item to an entity in a fixed order (explicit identifier, then a unique exact normalized alias, then a registry lookup restricted to the item's entity type); unresolved items form UNALIGNED groups. Groups are ordered by their best member relevance, then by the number of sources they cover, then by entity identifier, and written whole until the budget is full. No model invents entities.

**CF-02 (SAG-inspired dual path)** [@wu2026sag] treats graph and structured items as *structural* and text items as *semantic* candidates. One selector call reads a compact manifest of the structural candidates (one line each: identifier, source, relevance, the first 200 characters, provenance) and returns at most five identifiers; one schema repair is allowed, otherwise the five most relevant items are used. Text items then fill the context to ten items in retriever order.

**CF-03 (MegaRAG-inspired late fusion)** [@hsiao2025megarag] reasons over each non-empty source separately and fuses the findings ([[alg:cf03]]).

@alg cf03 | CF-03 late fusion with grounded findings
Input: question $q$, bundle with sources ${T,G,S}$
Output: answer $A(q)$
**for each** source $s$ with evidence **do**
> $f_s←$ LLM($q$, evidence of $s$ only) as {candidate_answer, supporting_ids, confidence}
> **if** supporting_ids $⊄$ IDs($s$) **or** the call fails **then** $f_s←$ NO_EVIDENCE
$A(q)←$ LLM($q$, ${f_s}$), citing only papers supported by some $f_s$
**if** the fusion call fails **then** retry once, **else return** $A(q)$
@end

Fusion cannot recover evidence that was never retrieved. Before any model call, each bundle $b$ with evidence papers $P(b)$ was therefore assigned a supportability class, used only for analysis:

@eq supp | "class"(b)={■("FULLY"&"if " G(q)⊆P(b)@"PARTIALLY"&"if " G(q)∩P(b)≠∅@"UNSUPPORTABLE"&"otherwise")┤

## RG3 → RQ3: Retrieval-Control Policies {#sec:ar}

Retrieval control decides which sources to query, in which order, and when to stop. All policies share the same tools (the unchanged B1–B3), a cumulative evidence memory, and a fixed downstream context (labelled sections of 8,000 characters for the sources actually queried), so the policy is the only variable. [[fig:ar]] shows their control flow.

**AR-B0** always queries text, graph, and structured with the raw question. **AR-B1 (rule router)** normalizes the question (NFKC, lowercase) and matches a frozen cue table: text cues (e.g., "abstract", "mentions"), graph cues (e.g., "author", "affiliated", "cites"), and structured cues (e.g., "year", "rank", "at least", "≥"). It queries every matched source once in the order text, graph, structured; with no match it queries text. The cue table was frozen before any result and serves as the base router of AR-01 and AR-02.

@fig ar | fig_rq3_methods.png | Control flow of the five retrieval-control policies of RQ3. (a) Always query all three sources. (b) Frozen keyword cues select the sources. (c) A trained classifier chooses no retrieval, one source, or multi-step retrieval with an LLM sufficiency check. (d) A calibrated cross-encoder rates the evidence and triggers corrections. (e) An agent chooses one tool per step; a validator accepts or a commentor returns feedback. | wide | 7.0

**AR-01 (Adaptive-RAG-inspired)** [@jeong2024adaptive]. A t5-base model [@raffel2020t5] predicts a route: A (no retrieval), B (the router's first source), or C (up to three steps, with an LLM controller returning {sufficient, next_subquery} after each step). Training labels come from a retrieval-only oracle on separate training questions:

@eq label | ℓ(q)=min{ℓ∈(A,B,C):"succ"_ℓ (q)}

where A succeeds only for an empty gold set, B succeeds if the router's first source retrieves every gold paper, and C if up to three sources do; the label defaults to C. A hash-based partition of the 8,049 training questions gave 7,302 training and 747 development questions; the model (AdamW, learning rate $3×10^(−5)$, weight decay 0.01) kept the epoch with the lowest development loss (epoch 7, loss 0.2170).

**AR-02 (CRAG-inspired)** [@yan2024crag]. A MiniLM cross-encoder trained on MS MARCO [@nogueira2019monobert;bajaj2016msmarco] scores each (question, evidence) pair; Platt scaling [@platt1999], fitted on the development partition only (7,498 labelled items from 745 questions), maps a raw score $s$ to a probability

@eq platt | p=1/(1+e^(−(a s+b))),  a=0.376,  b=0.102

and the evidence state follows

@eq state | "state"(q)={■("GOOD"&"if " max_i⁡p_i≥U@"BAD"&"if " max_i⁡p_i≤L@"AMBIGUOUS"&"otherwise")┤

with $L=0.40$ and $U=0.75$ chosen by macro-F1 from a frozen grid on 2,235 development states ([[alg:ar02]]).

**AR-03 (AGENT-G-inspired)** [@agentg2025]. An LLM agent chooses one action per iteration (a source with a query, or stop); after each tool call a candidate answer is generated and an LLM validator, which never sees gold data, accepts or rejects it; on rejection an LLM commentor returns feedback ([[alg:ar03]]).

@alg ar02 | AR-02 calibrated corrective retrieval
Input: question $q$; router order; thresholds $L,U$
Output: answer $A(q)$
query the router's first source; rounds $←0$
**loop**
> $p_i←$ Platt(cross-encoder($q$, item $i$)) for all items; state by [[eq:state]]
> **if** state = GOOD **or** rounds = 2 **or** no source is left **then break**
> **if** AMBIGUOUS **then** add the next unqueried source **else** add all remaining
> rounds $←$ rounds + 1
**return** $g(q,"fixed context")$
@end

@alg ar03 | AR-03 agent–validator–commentor loop
Input: question $q$; at most $T=4$ iterations
Output: answer $A(q)$ or INSUFFICIENT_EVIDENCE
**for** $i=1,…,T$ **do**
> action $←$ agent($q$, feedback, memory) (one schema repair allowed)
> **if** action = stop **then return** $g(q,"memory")$
> run exactly one tool; add new evidence to memory
> $Â←g(q,"memory")$; verdict $←$ validator($q$, $Â$, memory)
> **if** verdict accepts **then return** $Â$
> feedback $←$ commentor($q$, action, verdict); stop on repeated empty actions
**return** INSUFFICIENT_EVIDENCE (empty answer)
@end

## RG4 → RQ4: Integration {#sec:int}

The integrated system **INT-1** chains the selected policy, context management on graph evidence, and the selected fusion method, whose answer becomes the system's answer. The components were selected by rules fixed before any RQ2 or RQ3 result was analysed: context management was fixed to CM-B1 for cost, and the policy and fusion method are the Pareto-optimal strategies with the highest answer F1,

@eq select | m^*=〖"arg max"〗_(m∈𝒫)⁡〖F_1 (m)〗

with ties broken by fewer tokens and then by a fixed order. INT-1 is compared with AR-B0 and with the selected policy alone on the same 28 questions.

## How the Problem Was Solved: Execution and Evaluation Protocol {#sec:protocol}

### Freezing and replay-verified execution
Before a study runs, its execution plan records the SHA-256 of every code file, configuration, prompt, input file, model artefact, and the exact cohort; a runner refuses to start or resume if any hash differs. Every model request is stored durably under the hash of its full payload. Calls are made question by question for all methods (question-major order), after which the unchanged evaluation runner replays each method with a store-only client that stops on any request that differs from the stored one ([[fig:protocol]]). Failures are recorded, never silently retried.

@fig protocol | fig_protocol.png | Execution and analysis protocol: freeze, verify, call once per request in question-major order, replay with a byte-identity check, then analyse with a frozen plan. | col | 3.3

### Metrics
For a question with returned set $A$ and gold set $G$,

@eq prf | P=|A∩G|/|A|,  R=|A∩G|/|G|,  F_1=2PR/(P+R)

with the conventions that an empty prediction for an empty gold set scores 1 and an empty prediction for a non-empty gold set scores 0; exact match is $𝟙[A=G]$. Evidence quality is measured by the mean reciprocal rank of the first correct paper and by gold coverage, the share of correct papers present in the model's context:

@eq gc | "GC"(q)=|G(q)∩"IDs"(c(q))|/|G(q)|

For retrieval control, with $S$ the set of queried sources and $R$ the sources a question requires (known from its construction and used only for evaluation),

@eq source | "SF"_1=(2|S∩R|)/(|S|+|R|),  "WR"=|S∖R|/|S|

and stopping accuracy is 1 when the policy stops exactly at the first step after which all required sources have been queried. Cost is measured by input and output tokens over all model calls, model and retrieval calls, and intrinsic latency $L=t_"ret"+t_"LLM"+t_"loc"$ (retrieval time, model compute time, and local computation; waiting is excluded). [[tab:metrics]] summarizes the metrics.

@table metrics | Metrics (↑ higher is better, ↓ lower is better) | col | 0.95,1.85,0.3
| Metric | Definition | |
|---|---|:-:|
| Answer F1 | set F1 of returned vs. gold papers, [[eq:prf]] | ↑ |
| Exact match (EM) | returned set equals gold set | ↑ |
| MRR | reciprocal rank of first correct paper | ↑ |
| Gold coverage (GC) | share of gold papers in the context, [[eq:gc]] | ↑ |
| Source F1 (SF1) | F1 of queried vs. required sources, [[eq:source]] | ↑ |
| Wasted retrieval (WR) | share of queried sources not needed, [[eq:source]] | ↓ |
| Stopping accuracy | stopped exactly when all needed sources were in hand | ↑ |
| Tokens | input + output tokens over all model calls | ↓ |
| Calls / searches | model calls / retriever calls per question | ↓ |
| Latency | retrieval + model compute + local time | ↓ |

### Statistical analysis
For a pair of methods (A, B) and a metric, let $d(q)$ be the per-question difference, $S_f$ its sum over the questions of family $f$, and $n_f$ their number. Confidence intervals come from a family bootstrap [@efron1993;cameron2008] with 10,000 resamples (seed 42):

@eq boot | Δ̂_b=(∑_(f∈ℬ_b)▒S_f)/(∑_(f∈ℬ_b)▒n_f )

where each resample $ℬ_b$ draws $F$ families with replacement; the 2.5th and 97.5th percentiles of the 10,000 resampled means form the 95% interval. The two-sided *p*-value is an exact sign-flip test over all $2^F$ sign patterns of the $F$ family sums [@good2005],

@eq signflip | p=〖1/2^F〗 ∑_(σ∈{±1}^F)▒𝟙[T(σ)≥T(𝟏)]

with the test statistic

@eq tstat | T(σ)=|〖∑_(f=1)^F▒〖σ_f S_f〗〗|

and the $k$ pre-specified pairs of each metric are adjusted with Holm's method [@holm1979]:

@eq holm | p̃_((i))=min{1,max_(j≤i)⁡〖(k−j+1) p_((j))〗}

A difference is called significant only if $p̃<0.05$. The smallest attainable unadjusted *p*-value is $2∕2^F$: 0.0078 with 8 families and 0.00012 with 14.

### Pareto sets and overall ranking
A method is Pareto-optimal if no other method is at least as good on every frozen axis of its study and strictly better on one. The axes are answer F1, MRR, input tokens, and latency for RQ1; answer F1, input tokens, and latency for RQ2; and answer F1, source F1, tokens, and latency for RQ3. To name one winner per study, each method is ranked from 1 to 5 on every axis (ties share the average rank) and the ranks are summed:

@eq rank | R(m)=∑_(a∈𝒜)▒r_a (m),  m^*=〖"arg min"〗_m⁡R(m)

with ties broken by higher answer F1 and then fewer tokens. As a robustness check, the mean of min–max scaled axis scores must pick the same winner:

@eq scaled | s(m)=〖1/|𝒜|〗 ∑_(a∈𝒜)▒〖(v_a (m)−v_a^"min")/(v_a^"max"−v_a^"min")〗

The overall ranking was defined after the results were known; it summarizes the frozen means and is not a significance test. [[alg:stats]] summarizes the analysis of one study.

@alg stats | Family-clustered comparison and overall ranking of one study
Input: per-question records; pre-specified pairs; Pareto axes $𝒜$
Output: tests, Pareto set, winner
**for each** metric **and** pair (A, B) **do**
> compute $d(q)$, family sums $S_f$, sizes $n_f$
> bootstrap CI by [[eq:boot]]; exact sign-flip $p$ by [[eq:signflip]] and [[eq:tstat]]
> Holm-adjust the $p$-values of the metric by [[eq:holm]]
compute the Pareto set on $𝒜$
rank every method on every axis; $R(m)$ by [[eq:rank]]; check by [[eq:scaled]]
**return** tests, Pareto set, $m^*$
@end

### Implementation details
[[tab:settings]] lists the frozen settings. All runs used one workstation; the 448 analysed records of the four studies completed with 0 errors. The complete suite of 327 automated tests passed, and all figures and tables in this paper are regenerated from the checksummed study outputs.

@table settings | Frozen implementation settings | col | 1.1,1.9
| Component | Setting |
|---|---|
| LLM | gpt-oss:20b via Ollama 0.40.5; T = 0; per-question seed; low reasoning; JSON; 1,024-token cap per call |
| Embeddings | all-MiniLM-L6-v2 (ONNX), 384-d, 256 tokens |
| Retrieval | top-5 per source; B2: 3 seeds, depth 2 |
| Context | 24,000 characters; 8,000 per section |
| CM-01 | 10 seeds; 1 hop; Kruskal MST; bge-reranker-large |
| CM-02 | prizes 3-2-1 / 5…1; $c_e=0.5$; pcst_fast 1.0.10 |
| CM-03 | 20 seeds; mass 10; sink 1; $ε=0.05$; $τ=0.01$ |
| CF-02 | ≤ 5 structural items; 10 items total |
| AR-01 | t5-base; best epoch 7 of ≤ 10 |
| AR-02 | ms-marco-MiniLM-L-6-v2; $L=0.40$, $U=0.75$; ≤ 2 rounds |
| AR-03 | ≤ 4 iterations; validator and commentor |
| Statistics | 10,000 bootstrap resamples; exact sign-flip; Holm |

# Results and Discussion {#sec:results}

## Results

### RQ1: context management
[[tab:rq1]] and [[fig:rq1bars]] report the results on 32 questions. Answer quality was near its floor for every strategy: all five abstained correctly on the 8 unanswerable variants, which alone yields an F1 of 0.250, and CM-B0 and CM-03 returned no paper for any answerable question. CM-01 achieved the highest F1 ({{RQ1.CM-01.answer_f1}}; {{RQ1.CM-01.answerable_f1}} on answerable questions) and MRR ({{RQ1.CM-01.mrr}}) at {{RQ1.ratio.input_tokens.CM-01/CM-B1}}× the input tokens and {{RQ1.ratio.latency.CM-01/CM-B1}}× the latency of CM-B1. CM-B1 used about a third of the raw control's input tokens ({{RQ1.CM-B1.input_tokens}} vs. {{RQ1.CM-B0.input_tokens}}) with equal or better F1 and MRR. CM-02 was the fastest ({{RQ1.CM-02.latency}}) but ranked correct papers lowest (MRR {{RQ1.CM-02.mrr}}), and CM-03 kept the most correct papers in the context (gold coverage {{RQ1.CM-03.gold_coverage}}) yet was the slowest ({{RQ1.CM-03.latency}}); its diffusion converged on only 5 of 32 questions.

@results rq1 | RQ1 | answer_f1,answerable_f1,answer_em,mrr,gold_coverage,input_tokens,latency,llm_calls | RQ1 context management: means over 32 questions (★ Pareto-optimal; best value per column in bold) | wide

@fig rq1bars | fig_rq1_bars.png | RQ1 per strategy with family-clustered 95% bootstrap intervals: (a) answer F1, (b) MRR, (c) gold coverage, (d) input tokens. ★ marks the Pareto set. | col | 3.35

No pair differed significantly in answer F1 (every Holm-adjusted *p*-value was {{RQ1.test.answer_f1.CM-01~CM-B1.p_holm}}): all differences came from the two graph-only families. The Pareto set is {CM-B1, CM-01, CM-02} ([[fig:rq1scatter]]); CM-B1 dominates CM-B0 and CM-03. By source combination ([[fig:rq1strata]]), correct answers came only from the graph-only families, where CM-01 reached F1 {{RQ1.strata.modality.G.CM-01.answer_f1}} against {{RQ1.strata.modality.G.CM-B1.answer_f1}} for CM-B1; on the 18 answerable multi-source questions no strategy returned a correct paper.

@fig rq1scatter | fig_rq1_scatter.png | RQ1 quality against cost. Circles are Pareto-optimal (★), triangles are dominated; up and to the left is better. | col | 3.2

@fig rq1strata | fig_rq1_strata.png | RQ1 by the sources a question needs: (a) answer F1 and (b) gold coverage (8 questions per group). The value 0.25 in (a) is the share of correctly abstained unanswerable variants. | col | 3.3

### RQ2: cross-modal fusion
All five fusion strategies returned an empty answer on all 24 bundles, so answer F1 and exact match are 0.000 for every method ([[tab:rq2]]). Supportability, fixed before any call, explains most of this ([[fig:rq2]]a): {{RQ2.support.UNSUPPORTABLE}} bundles contain no correct paper, {{RQ2.support.PARTIALLY_SUPPORTABLE}} contain some, and only {{RQ2.support.FULLY_SUPPORTABLE}} contain all; both fully supportable bundles are conflict variants in which the model judged that no paper met every condition. The strategies therefore differ only in cost and ranking. CF-B1 was the cheapest ({{RQ2.CF-B1.input_tokens}} input tokens) and fastest ({{RQ2.CF-B1.latency}}) and is the only Pareto-optimal method; CF-02 needed two calls and CF-03 {{RQ2.CF-03.llm_calls}} on average, while CF-03 ranked a correct paper earliest (MRR {{RQ2.CF-03.mrr}}). CF-01 resolved every evidence item by its explicit identifier and never needed its registry lookup, and the CF-02 selector kept on average only {{RQ2.diag.CF-02.mean_selected}} structural items per bundle.

@results rq2 | RQ2 | answer_f1,mrr,input_tokens,llm_calls,latency | RQ2 cross-modal fusion: means over 24 bundles (★ Pareto-optimal; best in bold) | col

@fig rq2 | fig_rq2.png | RQ2: (a) supportability of the 24 bundles, fixed before any model call; (b) input tokens, (c) latency, and (d) model calls per bundle. | col | 3.35

No RQ2 difference reached significance. Several cost differences had the same sign in all eight families, e.g., CF-03 used {{RQ2.test.llm_calls.CF-03~CF-B1.delta|abs}} more calls per bundle than CF-B1 (unadjusted *p* = 0.008, the minimum attainable with eight families), but with seven pairs per metric their Holm-adjusted *p*-values were at least 0.055 ([[sec:discussion]]).

### RQ3: retrieval control
All five policies produced identical answers (F1 {{RQ3.AR-B1.answer_f1}}, EM {{RQ3.AR-B1.answer_em}}), so efficiency separated them ([[tab:rq3]], [[fig:rq3scatter]]). The rule router selected sources best (source F1 {{RQ3.AR-B1.source_f1}}) at the lowest cost ({{RQ3.AR-B1.total_tokens}} tokens, {{RQ3.AR-B1.latency}}) and is the only Pareto-optimal policy. Querying every source wasted {{RQ3.AR-B0.unnecessary_retrieval|pct}} of the searches. The agent wasted almost none ({{RQ3.AR-03.unnecessary_retrieval}}) but needed {{RQ3.AR-03.llm_calls}} model calls per question and was the only policy to miss required sources ({{RQ3.AR-03.required_source_miss}}).

With 14 families, RQ3 can detect differences ([[fig:rq3forest]]). The router chose sources significantly better than querying everything ({{RQ3.test.source_f1.AR-B1~AR-B0.delta}} source F1, Holm-adjusted *p* {{RQ3.test.source_f1.AR-B1~AR-B0.p_holm|peq}}), with significantly less wasted retrieval, fewer searches, fewer tokens ({{RQ3.test.total_tokens.AR-B1~AR-B0.delta}} per question), and lower latency. Against the router, the learned and agentic policies cost significantly more for the same answers: AR-01 used {{RQ3.test.total_tokens.AR-01~AR-B1.delta|abs}} and AR-03 {{RQ3.test.total_tokens.AR-03~AR-B1.delta|abs}} more tokens per question (both Holm-adjusted *p* {{RQ3.test.total_tokens.AR-03~AR-B1.p_holm|peq}}), and even AR-02 used {{RQ3.test.total_tokens.AR-02~AR-B1.delta|abs}} more (*p* {{RQ3.test.total_tokens.AR-02~AR-B1.p_holm|peq}}); all three were also significantly slower. No policy selected sources significantly better than the router.

@results rq3 | RQ3 | answer_f1,source_f1,unnecessary_retrieval,stopping_accuracy,required_source_miss,retrieval_calls,llm_calls,total_tokens,latency | RQ3 retrieval control: means over 28 questions (★ Pareto-optimal; best in bold) | wide

@fig rq3scatter | fig_rq3_scatter.png | RQ3 source selection against cost (answer F1 is identical for all policies). AR-B1 is the only Pareto-optimal policy. | col | 3.2

@fig rq3forest | fig_rq3_forest.png | RQ3 paired differences with 95% family-bootstrap intervals and Holm-adjusted *p*-values (* significant): (a) source-selection F1, (b) tokens, (c) latency. | col | 3.35

[[fig:rq3stops]] shows how the policies ended. The classifier of AR-01 chose the multi-step route for every question; its controller judged the evidence sufficient after one search on {{RQ3.stop.AR-01.sufficient}} questions, and the three-search limit ended the other {{RQ3.stop.AR-01.max_multi_steps}}. AR-02 rated the evidence GOOD on {{RQ3.stop.AR-02.good}} questions, reached its round limit on {{RQ3.stop.AR-02.max_correction_rounds}}, and exhausted the sources on {{RQ3.stop.AR-02.sources_exhausted}}. The validator of AR-03 accepted a draft answer on {{RQ3.stop.AR-03.validator_accepted}} questions, {{RQ3.fail.AR-03.validator_false_accept}} of them wrongly, and the iteration limit ended the other {{RQ3.stop.AR-03.max_iterations_rejected}}. A retriever failure despite correct routing was recorded on {{RQ3.fail.AR-B1.retriever_failure_despite_correct_routing}} of the 28 questions for each of AR-B0, AR-B1, AR-01, and AR-02, their joint most frequent failure label; for AR-03 the most frequent label was a false acceptance by the validator.

@fig rq3stops | fig_rq3_stops.png | RQ3 stop reasons over the 28 questions: stops decided by the policy (solid), fixed plans completed (light), and limits reached (hatched). | col | 3.4

### RQ4: integration
The frozen rules selected **{{RQ4.sel.R-AR}} → {{RQ4.sel.CM}} → {{RQ4.sel.R-CF}}**. INT-1 gave the same answers as both comparisons (F1 {{RQ4.INT-1.answer_f1}}), kept the router's source selection, significantly better than querying everything ({{RQ4.test.source_f1.INT-1~AR-B0.delta}} source F1, Holm-adjusted *p* {{RQ4.test.source_f1.INT-1~AR-B0.p_holm|peq}}), and used {{RQ4.test.total_tokens.INT-1~AR-B1.delta|abs}} more tokens per question than the router alone (*p* {{RQ4.test.total_tokens.INT-1~AR-B1.p_holm|peq}}), because the CF-B1 fusion stage writes every evidence item as a full record with identifier, payload, and provenance instead of the router's compact lines (7,964 vs. 5,287 context characters on average; [[tab:rq4]], [[fig:rq4]]). Latency did not differ significantly. Under the frozen top-5 graph retriever, CM-B1 removed no graph evidence for this single-graph-call policy.

@fig rq4 | fig_rq4.png | RQ4: (a) source-selection F1, (b) tokens, and (c) latency of AR-B0, AR-B1, and the integrated system INT-1. | col | 3.3

@results rq4 | RQ4 | answer_f1,source_f1,retrieval_calls,total_tokens,latency | RQ4 integrated system vs. AR-B0 and AR-B1 on 28 questions | col | AR-B0,AR-B1,INT-1

### Statistical summary
[[tab:sig]] lists every difference that survived Holm correction. All of them come from RQ3 and RQ4, whose 14 families give the tests enough resolution.

@table sig | All paired differences that remain significant after Holm correction (RQ3 and RQ4; Δ = A − B with family-bootstrap 95% CI; 14 families) | col | 0.95,0.62,0.52,0.93,0.48
| Pair (A − B) | Metric | Δ | 95% CI | *p* (Holm) |
|---|---|---:|---:|---:|
| AR-B1 − AR-B0 | SF1 | {{RQ3.test.source_f1.AR-B1~AR-B0.delta|nounit}} | {{RQ3.test.source_f1.AR-B1~AR-B0.ci|nounit}} | {{RQ3.test.source_f1.AR-B1~AR-B0.p_holm}} |
| AR-B1 − AR-B0 | WR | {{RQ3.test.unnecessary_retrieval.AR-B1~AR-B0.delta|nounit}} | {{RQ3.test.unnecessary_retrieval.AR-B1~AR-B0.ci|nounit}} | {{RQ3.test.unnecessary_retrieval.AR-B1~AR-B0.p_holm}} |
| AR-03 − AR-B0 | WR | {{RQ3.test.unnecessary_retrieval.AR-03~AR-B0.delta|nounit}} | {{RQ3.test.unnecessary_retrieval.AR-03~AR-B0.ci|nounit}} | {{RQ3.test.unnecessary_retrieval.AR-03~AR-B0.p_holm}} |
| AR-B1 − AR-B0 | searches | {{RQ3.test.retrieval_calls.AR-B1~AR-B0.delta|nounit}} | {{RQ3.test.retrieval_calls.AR-B1~AR-B0.ci|nounit}} | {{RQ3.test.retrieval_calls.AR-B1~AR-B0.p_holm}} |
| AR-03 − AR-B0 | searches | {{RQ3.test.retrieval_calls.AR-03~AR-B0.delta|nounit}} | {{RQ3.test.retrieval_calls.AR-03~AR-B0.ci|nounit}} | {{RQ3.test.retrieval_calls.AR-03~AR-B0.p_holm}} |
| AR-B1 − AR-B0 | tokens | {{RQ3.test.total_tokens.AR-B1~AR-B0.delta|nounit}} | {{RQ3.test.total_tokens.AR-B1~AR-B0.ci|nounit}} | {{RQ3.test.total_tokens.AR-B1~AR-B0.p_holm}} |
| AR-01 − AR-B0 | tokens | {{RQ3.test.total_tokens.AR-01~AR-B0.delta|nounit}} | {{RQ3.test.total_tokens.AR-01~AR-B0.ci|nounit}} | {{RQ3.test.total_tokens.AR-01~AR-B0.p_holm}} |
| AR-03 − AR-B0 | tokens | {{RQ3.test.total_tokens.AR-03~AR-B0.delta|nounit}} | {{RQ3.test.total_tokens.AR-03~AR-B0.ci|nounit}} | {{RQ3.test.total_tokens.AR-03~AR-B0.p_holm}} |
| AR-01 − AR-B1 | tokens | {{RQ3.test.total_tokens.AR-01~AR-B1.delta|nounit}} | {{RQ3.test.total_tokens.AR-01~AR-B1.ci|nounit}} | {{RQ3.test.total_tokens.AR-01~AR-B1.p_holm}} |
| AR-02 − AR-B1 | tokens | {{RQ3.test.total_tokens.AR-02~AR-B1.delta|nounit}} | {{RQ3.test.total_tokens.AR-02~AR-B1.ci|nounit}} | {{RQ3.test.total_tokens.AR-02~AR-B1.p_holm}} |
| AR-03 − AR-B1 | tokens | {{RQ3.test.total_tokens.AR-03~AR-B1.delta|nounit}} | {{RQ3.test.total_tokens.AR-03~AR-B1.ci|nounit}} | {{RQ3.test.total_tokens.AR-03~AR-B1.p_holm}} |
| AR-B1 − AR-B0 | latency (s) | {{RQ3.test.latency.AR-B1~AR-B0.delta|nounit}} | {{RQ3.test.latency.AR-B1~AR-B0.ci|nounit}} | {{RQ3.test.latency.AR-B1~AR-B0.p_holm}} |
| AR-01 − AR-B0 | latency (s) | {{RQ3.test.latency.AR-01~AR-B0.delta|nounit}} | {{RQ3.test.latency.AR-01~AR-B0.ci|nounit}} | {{RQ3.test.latency.AR-01~AR-B0.p_holm}} |
| AR-03 − AR-B0 | latency (s) | {{RQ3.test.latency.AR-03~AR-B0.delta|nounit}} | {{RQ3.test.latency.AR-03~AR-B0.ci|nounit}} | {{RQ3.test.latency.AR-03~AR-B0.p_holm}} |
| AR-01 − AR-B1 | latency (s) | {{RQ3.test.latency.AR-01~AR-B1.delta|nounit}} | {{RQ3.test.latency.AR-01~AR-B1.ci|nounit}} | {{RQ3.test.latency.AR-01~AR-B1.p_holm}} |
| AR-02 − AR-B1 | latency (s) | {{RQ3.test.latency.AR-02~AR-B1.delta|nounit}} | {{RQ3.test.latency.AR-02~AR-B1.ci|nounit}} | {{RQ3.test.latency.AR-02~AR-B1.p_holm}} |
| AR-03 − AR-B1 | latency (s) | {{RQ3.test.latency.AR-03~AR-B1.delta|nounit}} | {{RQ3.test.latency.AR-03~AR-B1.ci|nounit}} | {{RQ3.test.latency.AR-03~AR-B1.p_holm}} |
| INT-1 − AR-B0 | SF1 | {{RQ4.test.source_f1.INT-1~AR-B0.delta|nounit}} | {{RQ4.test.source_f1.INT-1~AR-B0.ci|nounit}} | {{RQ4.test.source_f1.INT-1~AR-B0.p_holm}} |
| INT-1 − AR-B1 | tokens | {{RQ4.test.total_tokens.INT-1~AR-B1.delta|nounit}} | {{RQ4.test.total_tokens.INT-1~AR-B1.ci|nounit}} | {{RQ4.test.total_tokens.INT-1~AR-B1.p_holm}} |

No answer-quality difference is among them: every significant difference concerns source selection or cost.

@table rank | Overall winners (rank totals over the Pareto axes; lower is better) | col | 0.5,0.95,1.0,0.75,0.6
| Study | Winner | Runner-up | Scaled check | Quality-first |
|---|---|---|---|---|
| RQ1 | CM-B1 ({{RQ1.overall.total.CM-B1}}) | CM-01, CM-02 ({{RQ1.overall.total.CM-01}}) | CM-B1 ({{RQ1.overall.scaled.CM-B1}}) | CM-01 |
| RQ2 | CF-B1 ({{RQ2.overall.total.CF-B1}}) | CF-02, CF-B0 ({{RQ2.overall.total.CF-02}}) | CF-B1 ({{RQ2.overall.scaled.CF-B1}}) | CF-B1 |
| RQ3 | AR-B1 ({{RQ3.overall.total.AR-B1}}) | AR-02 ({{RQ3.overall.total.AR-02}}) | AR-B1 ({{RQ3.overall.scaled.AR-B1}}) | AR-B1 |

### Overall ranking
[[tab:rank]] and [[fig:ranking]] report the overall ranking. CM-B1 wins RQ1 with a rank total of {{RQ1.overall.total.CM-B1}} (second on F1, MRR, and latency, first on tokens), CF-B1 wins RQ2 ({{RQ2.overall.total.CF-B1}}; first on both cost axes with F1 tied), and AR-B1 wins RQ3 ({{RQ3.overall.total.AR-B1}}; first on source F1, tokens, and latency). The scaled-score check selects the same winner in every study. Chained in pipeline order, the winners are exactly INT-1, which the frozen rule had selected before the ranking was defined. A quality-first rule would choose CM-01 in RQ1 and the same winners elsewhere.

@fig ranking | fig_ranking.png | Overall ranking per study: rank on each Pareto axis (1 = best; darker is better), rank total, and scaled score. The outlined row is the winner. | col | 3.3

## Discussion {#sec:discussion}

### Why the simplest strategies win
Three effects combine. First, answers did not separate the strategies: in RQ1 no difference was significant (and, as shown below, none could be), and in RQ2–RQ4 every strategy returned identical answers, so cost and evidence selection decided the ranking. Second, the elaborate methods act after retrieval: rerankers, Steiner trees, diffusion, entity alignment, model-based selection, per-source reasoning, trained routers, calibrated evaluators, and agents all reorganize evidence that the retrievers already returned and cannot recover correct papers that were never retrieved, yet they add model calls, tokens, and time. Third, the controls are well matched to the questions: the rule router benefits from cue words in templated questions, and the fixed top-K follows the retriever's own ranking. These findings concern this corpus, these retrievers, and this model; they do not show that the elaborate mechanisms are ineffective in general.

### Where answer quality is lost
[[fig:bottleneck]] locates the loss before generation. In a retrieval-only check of the four baselines on 56 validation questions, the structured retriever found every correct paper of structured-only questions and a third of those of three-source questions, the graph retriever found 4% of the correct papers of graph-only questions, and the dense text retriever found almost none (0.003 on text-only questions), because text conditions are exact phrases while the retriever searches by meaning; no retriever found a correct paper of any text-and-graph question. Consequently, in RQ3 every policy answered the structured-only questions exactly (F1 {{RQ3.strata.modality.S.AR-B1.answer_f1}}), the graph-only questions weakly ({{RQ3.strata.modality.G.AR-B1.answer_f1}}, since a top-5 holds few of their many correct papers), and no other combination at all; the overall F1 of {{RQ3.AR-B1.answer_f1}} is exactly this mixture. The same pattern bounds RQ1 (gold coverage of at most {{RQ1.max.gold_coverage}}) and RQ2 ({{RQ2.support.UNSUPPORTABLE}} unsupportable bundles). Even where the correct paper was present, the model abstained when it could not verify every condition, which is the behaviour the grounding prompt requests.

@fig bottleneck | fig_bottleneck.png | Where answer quality is lost: (a) retrieval-only gold coverage of the four baselines by the sources a question needs (56 validation questions); (b) answer F1 of every RQ3 policy by the sources a question needs (4 questions per group). | col | 3.3

@table situations | Situations in which another strategy measured better (descriptive) | col | 0.42,1.15,0.55,1.4
| Study | Situation | Pick | Evidence |
|---|---|---|---|
| RQ1 | answer quality matters more than cost | CM-01 | F1 {{RQ1.CM-01.answer_f1}}, MRR {{RQ1.CM-01.mrr}}; {{RQ1.ratio.input_tokens.CM-01/CM-B1}}× tokens |
| RQ1 | every correct paper must reach the model | CM-03 | GC {{RQ1.CM-03.gold_coverage}}; slowest ({{RQ1.CM-03.latency}}) |
| RQ1 | speed is the priority | CM-02 | {{RQ1.CM-02.latency}}; lowest MRR |
| RQ2 | a correct paper should rank early | CF-03 | MRR {{RQ2.CF-03.mrr}} vs. {{RQ2.CF-B1.mrr}}; {{RQ2.CF-03.llm_calls}} calls |
| RQ2 | exactly two sources needed | CF-02 | fewest tokens on TG, TS, and GS bundles |
| RQ3 | each search is expensive | AR-03 | WR {{RQ3.AR-03.unnecessary_retrieval}} vs. {{RQ3.AR-B1.unnecessary_retrieval}} |
| RQ3 | text-only questions | AR-03 | SF1 {{RQ3.strata.modality.T.AR-03.source_f1}} vs. {{RQ3.strata.modality.T.AR-B1.source_f1}} |
| RQ3 | graph-only questions | AR-01 | SF1 {{RQ3.strata.modality.G.AR-01.source_f1}} vs. {{RQ3.strata.modality.G.AR-B1.source_f1}} |

### When another strategy is preferable
The winners are the best overall choice, but in specific situations another strategy measured better ([[tab:situations]]). These group-level differences are descriptive (4–8 questions per group) and were not tested.

### Statistical power
The exact sign-flip test cannot return a *p*-value below $2∕2^F$. With $F=8$ families this floor is 0.0078, and Holm multiplies the smallest *p*-value by the number of pairs, so the smallest attainable adjusted *p*-values were $10×0.0078=0.078$ in RQ1 and $7×0.0078=0.055$ in RQ2, both above 0.05. No difference in RQ1 or RQ2 could have been declared significant however consistent it was; their conclusions rest on the means and on consistency across families. With 14 families, RQ3 and RQ4 could detect differences and did. Future studies should either use more families or pre-specify fewer pairs.

### Implications for practice
Four guidelines follow. (i) Measure upstream coverage (gold coverage, supportability) before optimizing downstream components; no downstream method recovered what retrieval missed. (ii) Treat simple controls as strong baselines and always report cost: a fixed top-K, labelled sections, and keyword routing matched the elaborate methods' answers at a fraction of their cost. (iii) Match the retriever to the condition type: exact phrases call for lexical or hybrid text retrieval. (iv) Make experiments replayable: storing every request by its hash made multi-day runs resumable and every number auditable.

### Threats to validity
*Internal validity* is protected by freezing, identical inputs, question-major call order, and replay verification; a recorded timing asymmetry slightly favours CM-02 and CM-03 in latency, because their query-specific scores were staged offline while CM-01 computes them inside its timer. *Construct validity*: answer F1 against verified sets is exact, but gold coverage is an upper bound rather than accuracy, and template wording flatters the rule router. *External validity*: one corpus, three simple retrievers, and one model; the methods are adaptations, not reproductions. *Statistical conclusion validity*: small cohorts of correlated variants, analysed at the family level as described above.

# Conclusion {#sec:conclusion}

This paper studied, one component at a time, how a retrieval-augmented LLM should use text, graph, and structured views of the same scholarly corpus. On isolated, identity-joined views and a benchmark with verified source necessity, under frozen retrievers and one LLM, one strategy won each component on combined quality and cost: fixed top-K context management (CM-B1), source-separated fusion (CF-B1), and rule-based routing (AR-B1). Their combination, INT-1, which the pre-registered rule had already selected, answered as well as any single policy (F1 {{RQ4.INT-1.answer_f1}}), selected sources significantly better than querying every source ({{RQ4.test.source_f1.INT-1~AR-B0.delta}} source F1), and used {{RQ4.test.total_tokens.INT-1~AR-B1.delta|abs}} more tokens per question than the router alone. No literature-inspired method improved answer quality with statistical support, and the most elaborate controllers cost significantly more. The clearest lesson is where quality is lost: before generation, in retrieval coverage.

## Limitations and Future Work

**Limitations.** The cohorts are small (8–14 independent families), so the results are exploratory validation results rather than a locked test, and in RQ1 and RQ2 significance was unattainable. Labels are verified by computation; human review of the test sets (2,801 decisions) is outstanding. Text conditions are exact phrases that a meaning-based retriever rarely finds, and template wording favours the rule router. One corpus, one set of simple retrievers, and one LLM were used. All literature methods are adaptations: training-heavy components of the originals were replaced or omitted, CM-01 uses graph-native provenance units, and CM-03 converged on few questions under its frozen parameters. Under the frozen top-5 graph retriever, CM-B1 prunes only for policies with several graph calls.

**Future work.** (i) Raise upstream coverage with lexical or hybrid text retrieval, adaptive graph top-K, and structured filters that restrict candidates for the other sources, then repeat the component studies where answers are possible. (ii) Complete the human review and run the locked test. (iii) Repeat the comparisons with a stronger LLM and larger budgets. (iv) Evaluate fusion on evidence-complete bundles. (v) Increase statistical power with more families and fewer pre-specified pairs. (vi) Test on natural, human-written multi-source questions with verified source necessity.

# Dataset and Code Availability {#sec:availability}

## Dataset

All experiments use the official STaRK-MAG release [@wu2024stark;wang2020mag]:

- **Source:** https://huggingface.co/datasets/snap-stanford/stark
- **Revision:** 88269e23e90587f99476c5dd74e235a0877e69be
- **Licence:** CC-BY-4.0, as recorded on the dataset card.

The three views of MMG-STaRK-MAG and the benchmark are derived deterministically from this release by the released build scripts and are verified against recorded SHA-256 manifests (benchmark manifest e07f1314…). No human-review decisions are released, and the test and human-test splits were never used.

## Code Availability

The complete code will be released on GitHub (link to be added):

- **Repository:** https://github.com/[account]/[repository]

It contains the data build, benchmark construction, retrievers, all strategies, the execution protocol, the analyses, the generators of every figure and table in this paper, and an interactive showcase application with the recorded runs. Each study is accompanied by its frozen execution plan, stored model requests, run records, and analysis files, so every number can be rebuilt without calling the model again.

# *References

@refs
