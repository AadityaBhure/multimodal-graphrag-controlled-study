#! Part IV · The data foundation

# The source corpus: STaRK-MAG

## What it is

STaRK-MAG is the academic part of STaRK, a semi-structured retrieval benchmark published by the Stanford SNAP group and built on the Microsoft Academic Graph. It combines paper text (titles and abstracts), a heterogeneous graph of papers, authors, institutions and fields of study, and structured paper attributes. The project uses the official processed release only (dataset licence recorded as CC-BY-4.0 on the dataset card; loader code under MIT).

## Acquisition

Table: Acquisition facts {w=2.2,4.0}
| Item | Value |
|---|---|
| Source | Hugging Face dataset `snap-stanford/stark`, revision `88269e23e90587f99476c5dd74e235a0877e69be` |
| Official loader code inspected | revision `b246b9490b1dc216892ce78303140014506932c1` (its download primitive was used; its graph construction was not run) |
| Downloaded files | 9 files, 486,879,729 bytes (processed archive, schema files, question CSVs, split index files) |
| Extracted members | 6 files, 2,133,898,927 bytes |
| Total staged source | 2,620,778,656 bytes, every file with a SHA-256 in the raw manifest |
| Audit | every node record and every stored edge read with streaming readers; peak memory about 81 MiB; 46 seconds |

## Entities

@figure figures/c_dataset.png | Composition of STaRK-MAG: entities by type (left) and official directed relations by type (right). | 6.6

Table: Entity types and their global ID ranges {w=1.6,1.2,2.6}
| Entity type | Count | Global node IDs |
|---|---:|---|
| Author | 1,104,554 | 0 – 1,104,553 |
| Institution | 8,701 | 1,104,554 – 1,113,254 |
| Field of study | 59,469 | 1,113,255 – 1,172,723 |
| Paper | 700,244 | 1,172,724 – 1,872,967 |
| **Total** | **1,872,968** | contiguous 0 – 1,872,967 |

## Relations

Table: Official directed relations {w=2.6,1.2,2.6}
| Relation (source representation) | Count | Meaning |
|---|---:|---|
| `author___writes___paper` | 6,768,883 | an author wrote a paper |
| `author___affiliated_with___institution` | 1,029,162 | an author is affiliated with an institution |
| `paper___cites___paper` | 4,878,384 | a paper cites another paper |
| `paper___has_topic___field_of_study` | 7,243,269 | a paper has a field of study |
| **Total stored directed edges** | **19,919,698** | every endpoint type verified; no self-loops |

The number 19,919,698 is always the source edge count. The graph view later adds one tagged inverse traversal row per edge (39,839,396 traversal rows in total); those are never reported as source edges.

## Paper attributes

Paper records carry 35 fields. The attributes used by the project:

Table: Paper attributes and their availability {w=2.2,2.2,1.4}
| Information | Source field(s) | Papers with a value |
|---|---|---:|
| Title | `title` | 700,244 |
| Abstract | `abstract` | 700,244 |
| Publication year | `Year` | 678,195 |
| Publication date | `Date` | 678,195 |
| Citation count | `PaperCitationCount` | 678,195 |
| Paper rank | `PaperRank` | 678,195 |
| Journal ID and name | `JournalId`, `JournalDisplayName` | 677,353 |
| Conference series | `ConferenceSeriesId`, `ConferenceSeriesDisplayName` | 146 |
| Conference instance | `ConferenceInstanceId`, `ConferenceInstancesDisplayName` | 71 |
| Original venue name | `OriginalVenue` | 677,800 |
| Document type | `DocType` | 677,504 |

## Official questions

Table: Official question sets {w=2.2,1.0,3.0}
| Set | Questions | Notes |
|---|---:|---|
| Synthetic (train / validation / test) | 13,323 (7,993 / 2,665 / 2,665) | 37,044 answer references, all papers; disjoint official splits |
| Human-written | 84 | 274 answer references; questions 30, 50 and 72 reference author nodes, so they are incompatible with a paper-set evaluation |

## Source quirks recorded, not repaired

1. **Missing attributes.** 22,049 papers have no date, year, citation count or rank. They stay missing (NULL); nothing is inferred or zero-filled, and year is never derived from date.
2. **Unreconciled venues.** Venue information is spread over journal, conference-series, conference-instance and original-venue fields; there is no single venue column. Phase 3 defines an explicit precedence.
3. **Missing names.** 140,792 authors, 16 institutions and 17,458 fields of study have no name. They remain unnamed (shown by ID) and are still traversable.
4. **Incompatible human questions.** Questions 30, 50 and 72 are preserved unchanged in the source records and excluded whole from the primary human-test split; their labels are never "repaired".
5. **Tensor storage layout.** The edge-type tensor's logical view starts at a storage offset; readers honour offsets and strides so relation counts are correct.

# Three isolated views: MMG-STaRK-MAG v1

## Design

The project's dataset, MMG-STaRK-MAG v1, turns the audited source into three views of the same papers that share **nothing except the official global node ID**. Each retriever can therefore use only its own kind of evidence, and any effect of combining sources is a real effect of combining them, not an artefact of overlapping content.

@figure figures/d_data_build.png | How the three views were built: the pinned official release is audited, given one identity per entity, and converted into a text view, a graph view and a structured view, each checksummed in one manifest. | 6.5

Table: What each view contains and what it never contains {w=1.1,2.6,2.5}
| View | Contains | Never contains |
|---|---|---|
| Text | `paper_id`, `title`, `abstract`, `content` = title + two newlines + abstract | authors, institutions, year, venue, citations, relations |
| Graph | nodes (papers labelled by **title only**; other entities by display name or NULL) and the four official relation types, with explicit direction | abstracts, years, dates, venues, citation counts, ranks |
| Structured | scalar paper attributes: year, date, citation count, rank, document type, venue namespace / ID / name / type | titles, abstracts, authors, relations |

## Identity registry

Every entity has one canonical identity `stark:<global node ID>` together with its type, type-local ID and MAG ID (1,872,968 rows). An **exact alias registry** maps normalised names (Unicode NFKC, case-folded, whitespace-collapsed) to entities: 1,714,702 aliases, 1,505,293 distinct normalised strings, of which 105,792 are ambiguous and keep all their associations. There is no fuzzy or semantic name matching anywhere in the data layer.

## Text view

- One document per paper: exactly the source title, two newlines, and the full source abstract (700,244 rows, 4 columns).
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` at pinned revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, frozen weights exported to ONNX, mean pooling over the attention mask and L2 normalisation, **input limit 256 tokens** (the full abstract stays stored even when the embedding sees only its beginning).
- Index: exact FAISS `IndexFlatIP` over 700,244 × 384 float32 unit vectors (1.08 GB), built once from 171 durable shards; every stored vector was reconstructed and mapped back to its paper ID in the audit.
- Parity: on 33 test cases the ONNX export matched CPU PyTorch with a maximum absolute difference of 1.9 × 10⁻⁷ and a minimum cosine of 0.99999994.

## Graph view

- **Nodes:** all 1,872,968 entities. A paper's label (and searchable text) is its title only.
- **Edges:** all 19,919,698 official directed edges, plus one *derived inverse* row per edge with swapped endpoints, the same relation name and `derived_inverse = true`, so traversal can follow a relation in both directions. Inverse rows are tagged and map back to the official edge (inverse ID = official ID + 19,919,698).
- **Relation codes:** 0 = author affiliated with institution, 1 = paper cites paper, 2 = paper has topic field of study, 3 = author writes paper.
- **Storage:** compressed sparse row arrays on disk, memory-mapped: `indptr` (uint64, one entry per node plus one), `neighbors` (uint32, 39,839,396 entries), edge IDs, relation IDs and the inverse flag. No full in-memory graph object is ever built.
- **Audit:** every one of the 39,839,396 CSR entries matched the sorted edge view; no node is isolated in the traversal view. Example path: paper 1172724 → author 36641 → papers 1172724 and 1475765.

## Structured view

A DuckDB database (`stark_mag.duckdb`) holds `papers_structured` (one row per paper) and `papers_structured_source` (the raw source columns for auditing).

Table: Columns of papers_structured {w=1.6,1.2,3.4}
| Column | Type | Rule |
|---|---|---|
| `paper_id` | integer | global node ID |
| `publication_date` | date | source value; NULL if missing |
| `publication_year` | integer | source value; never derived from the date |
| `citation_count` | integer | source value; never recomputed; zero stays zero |
| `paper_rank` | integer | source value |
| `document_type` | text | source DocType, kept separate from venue |
| `venue_namespace`, `venue_id`, `venue_name`, `venue_type` | text | by precedence journal > conference series > conference instance > original venue > NULL |

Missing values (`None`, `-1`, empty string, NaN) become SQL NULL. Venue precedence produced 677,353 journal venues, 146 conference series, 0 conference instances (all 71 instances also had a higher-priority venue), 301 original-venue-only records and 22,444 NULL venues; a missing part of the selected pair is never filled from a lower level. A sanity query, `publication_year >= 2000 AND citation_count >= 100`, returns 8,316 papers.

## Build, sizes and audits

Table: Physical outputs of the build (358 files, 4.12 GB) {w=2.4,2.4,1.4}
| Artefact | Content | Bytes |
|---|---|---:|
| Canonical entities | 1,872,968 rows | 61,890,397 |
| Exact alias registry | 1,714,702 rows | 45,743,542 |
| Text documents | 700,244 rows × 4 columns | 609,298,612 |
| Graph nodes | 1,872,968 rows | 89,737,909 |
| Graph edges | 19,919,698 official + 19,919,698 inverse rows | 388,218,335 |
| CSR arrays | 5 files, 39,839,396 traversal entries | 572,735,936 |
| DuckDB database | 700,244 rows in each of two tables | 97,005,568 |
| Embedding vectors and IDs | 171 shards, 700,244 × 384 float32 | 1,081,220,512 |
| ONNX model and provenance | frozen-weight export | 90,377,796 |
| FAISS index and row mapping | 700,244 vectors | 1,081,176,909 |

The build runs in stages (nodes, structured, edges, CSR, embeddings, FAISS), each checkpointed atomically so an interrupted build resumes without mixing versions, and a corrupted completed output is rejected. Five exhaustive audits (nodes, SQL, edges, CSR, FAISS) compare every output with its permitted source projection. Re-running completed stages changes no output, and the manifest regenerates byte-identically.

## One paper, three views

The showcase application shows how the three retrievers see the same paper. For the correct answer of the example question in Chapter 4, the text view holds the title and abstract (where the phrase "we derive analytical expressions" satisfies the text condition), the structured view holds the row that satisfies the rank and venue conditions, and the graph view shows the paper with its authors, fields of study and citations, including the path University of Insubria ← author → paper that satisfies the graph condition.

@screen p03_data__03 | "One paper, three views" in the application: the text view with the matching phrase highlighted, the structured row with each required condition checked, and the paper's graph neighbourhood with the proving path drawn in green. | 6.3

# The benchmark

## Composition

Table: Benchmark composition by split and source {w=1.4,1.4,1.2,1.2,1.0}
| Split | Official synthetic | Generated | Official human | Total |
|---|---:|---:|---:|---:|
| train | 7,993 | 56 | 0 | 8,049 |
| validation | 2,665 | 56 | 0 | 2,721 |
| test | 2,665 | 55 | 0 | 2,720 |
| human_test | 0 | 0 | 81 | 81 |
| **Total** | **13,323** | **167** | **81** | **13,571** |

All official questions are preserved byte for byte, with their original IDs and splits. Their modality and reasoning labels are not provided by the source and remain marked **unverified** (13,404 records); they are never used in verified strata. All studies in this project use **generated validation questions** only.

## Generated questions

Generated questions are built from **42 base constructions**: two for each of the seven source combinations in each of the three main splits. Every base question has up to four variants (normal, noisy, conflict, unanswerable), giving 168 variants minus one noisy variant that was omitted because no valid distractor could be verified: **167 generated questions**. The variants of one base question form a **family**; they are strongly correlated and are never treated as independent.

Table: Source combinations (modality classes) {w=0.8,2.4,3.0}
| Class | Sources a question needs | Example condition |
|---|---|---|
| T | text | the abstract explicitly includes "in agreement with experimental results" |
| G | graph | at least one author is affiliated with Baoji University of Arts and Sciences |
| S | structured | the recorded paper rank is at most 19611 and the venue namespace is journal and … |
| TG | text + graph | an abstract phrase and an author condition |
| TS | text + structured | an abstract phrase and year / citation conditions |
| GS | graph + structured | an author condition and year / citation conditions |
| TGS | all three | phrase, institution and rank / venue conditions (the example in Chapter 4) |

Reasoning depth is the length of the longest required graph path: 104 generated questions are single-hop, 32 two-hop and 31 three-hop or more. Stress: 42 normal, 41 noisy, 42 conflict and 42 unanswerable generated questions.

@figure figures/c_benchmark_generated.png | The 167 generated questions by source combination and variant (left) and by source combination and reasoning depth (right). Text-only, structured-only and text-plus-structured questions are single-hop by construction. | 6.4

## How a generated question is built

@figure figures/d_benchmark.png | Construction of a generated question: conditions are computed on the frozen data first, intersected into the gold answer set, checked for strict source necessity, worded from a template, and extended with stress overlays before audit and freeze. | 6.3

1. **Choose conditions.** For a source combination, choose conditions from the data with seed 42: an exact abstract phrase (text), an author, institution or citation path anchored on a uniquely named entity (graph), and parameterised predicates on recorded attributes (structured). Construction instances, anchors and operator skeletons are exclusive to one split.
2. **Compute candidate sets before wording.** Each condition is evaluated on the frozen views and stored as a sorted, hashed list of paper IDs. No language model is involved in defining the answer.
3. **Intersect.** The gold answer set is the exact intersection of the candidate sets.
4. **Check strict source necessity.** For every answerable multi-source question, dropping any one required source must strictly enlarge the answer set. Counter-example IDs are stored. Constructions that fail are rejected.
5. **Word the question** from a fixed template. The wording never contains an answer ID or a full answer title.
6. **Add stress variants as overlays** (next section).
7. **Audit and regenerate.** Every gold set, all 286 source-specific candidate-set references, all 665,671 candidate IDs and all 2,336 witness paths were recomputed independently; a complete regeneration into a separate directory reproduced all 323 files byte for byte.
8. **Freeze.** The benchmark manifest (SHA-256 `e07f1314…`) and a separate test-content freeze ID bind every file.

**Splits are structurally different on purpose.** Train uses single-claim, author and year-citation templates; validation uses either-of-two-phrases claims, institution paths and rank-namespace predicates; test uses two-phrase claims, three-hop citation paths and date-citation predicates. This prevents template leakage between splits but introduces a declared distribution shift (graph paths of one hop in train, two in validation, three in test). The benchmark is therefore not independent and identically distributed across splits.

## Stress variants

Stress variants never change the canonical data. They are evaluation-time **overlays** passed to systems as extra evidence:

- **Noisy (41):** hard distractors that fail the question's conditions: semantic neighbours of the answer that lack the required phrase, nearby citation detours that miss the graph condition, or structured rows that satisfy only part of the filter.
- **Conflict (42):** one fact about a correct paper is altered in an added record (for example a structured record claiming paper rank 20072 when the condition is "at most 20071"). The original record stays authoritative, so the correct answer does not change. Each overlay stores the original fact, the altered value and a reverse patch.
- **Unanswerable (42):** the valid question plus one verified disjoint condition (for example "and the recorded publication year is greater than 2019" when no paper can satisfy it), so the correct answer is provably empty.

@screen p03_data_conflict__05 | The application's "Variants of one question" tabs, here on the conflict variant of the example: the added evidence claims paper rank 20072 for the correct paper, which would break the condition, while the original record stays authoritative. | 6.3

## Statistics

@figure figures/c_benchmark_sizes.png | Answer-set sizes over all 13,571 questions (left) and publication years of the 36,706 distinct correct papers (right). | 6.6

Answer sets range from empty (42 questions, all unanswerable variants) to more than 100 papers (21 questions). The generated graph questions have anchor degrees from 3 to 60 and graph candidate sets from 2 to 1,264 papers.

## Representative generated questions

Table: Examples of generated questions (from the benchmark protocol) {w=0.9,4.1,1.0}
| Class | Question | Correct papers |
|---|---|---:|
| T | Find all papers for which the abstract explicitly includes "in agreement with experimental results" (case-insensitive)? | 48 |
| G | Find all papers for which the paper is written by Michiel Wouters? | 13 |
| TG | … the abstract explicitly includes "in agreement with experimental results"; and the paper is written by S. Pelli? | 1 |
| TS | … the abstract explicitly includes "in agreement with experimental results"; and the recorded publication year is at least 2018, and the recorded citation count is at least 1? | 3 |
| GS | … the paper is written by Fubo Tian; and the recorded publication year is at least 2010, and the recorded citation count is at least 3? | 5 |
| G (2-hop) | Which papers satisfy these requirements: at least one author is affiliated with Baoji University of Arts and Sciences? | 78 |
| TGS (3-hop) | … the abstract explicitly includes "experimental data" and "the results indicate"; and the paper is cited by a paper written by an author affiliated with Jawaharlal Nehru Technological University, Hyderabad; and the recorded publication date is at most 2015-08-01, and the recorded citation count is at most 99? | 3 |
| S (unanswerable) | … the recorded publication year is at least 2016, … and the recorded publication year is greater than 2019? | 0 |

## Human review status

A browser-based review package of **3,390 items** was prepared (all 2,720 test questions, all 81 human-test questions and 589 validation questions with their evidence, derivations and counter-examples). **No review decisions have been recorded.** The evaluation harness refuses to run on the test or human-test splits until all 2,801 test and human-test decisions and a leakage attestation exist. Every "verified" label in this project therefore means *verified by computation*, not by a human reviewer.

## Which questions each study uses

Table: Study cohorts (all generated validation questions) {w=1.0,0.9,0.9,2.2,1.6}
| Study | Questions | Families | Which families | Variants |
|---|---:|---:|---|---|
| RQ1 (Part 1) | 32 | 8 | families whose question needs the graph (G, TG, GS, TGS; 2 each) | normal, noisy, conflict, unanswerable |
| RQ2 (Part 2) | 24 | 8 | families whose question needs several sources (TG, TS, GS, TGS; 2 each) | normal, noisy, conflict |
| RQ3 (Part 3) | 28 | 14 | every family (7 source combinations × 2) | normal, noisy |
| RQ4 (Part 4) | 28 | 14 | every family | normal, noisy |

The validation split has 56 generated questions in 14 families. RQ1 needs graph evidence, so it uses the 8 graph families with all four variants. RQ2 needs several sources, so it uses the 8 multi-source families with the three variants that have evidence (an unanswerable variant has nothing to fuse). RQ3 and RQ4 use all 14 families with the normal and noisy variants, a reduction from 56 to 28 questions decided in the scope revision before any outcome existed.

## Known limitations of the benchmark

- Only 42 independent base constructions exist (14 in validation); variants are correlated, so effective sample sizes are small.
- Some generated wording is mechanical and template-like; results do not establish natural-language generality.
- Text conditions are exact phrases, while the text retriever is meaning-based; this mismatch is reported, not fixed.
- The shared paper corpus is transductive across splits (the same papers can appear in several splits); overlapping answer papers alone are not leakage, and the automated leakage scans cannot rule out every paraphrase.
- Labels are verified by computation; human review is outstanding.
