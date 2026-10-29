#! Part VIII · The showcase application

# Purpose and design principles

The showcase application turns the project into an interactive presentation. It is built first for **presenting live** (a projector, a guided story, large text on demand) and second for **sharing** (every view has a link, and the app can be deployed with no research code or data). It replaces the earlier demonstration application, which is retired and kept only as an archived branch.

Design principles:

- **One story, in order.** The navigation follows the logic of the research: the problem → its four parts → the data and the measures → each study → the verdict → hands-on exploration → proof of reproducibility.
- **Every number from one verified source.** The app reads only a checksummed data bundle exported from the frozen study outputs. It never recomputes a result and never types a number in its text.
- **Text bound to data.** All on-screen text lives in one content file. Findings name their numbers with placeholders that are resolved from the bundle, so text and results cannot drift apart.
- **Deterministic.** The same bundle and content always render the same screens: fixed method colours, fixed ordering, deterministic number formatting, precomputed graph layouts.
- **Explain, do not just show.** Every page starts with what it shows and why; metrics carry their definitions; empty answers state where the correct paper was lost.
- **Honest about status.** Recorded runs are replays of the evaluated pipelines; live runs are marked as demonstrations that are not part of the results.

# How the application is built

## Technology

Table: Technology of the showcase application {w=1.6,4.6}
| Part | Choice |
|---|---|
| Framework | Streamlit 1.64 with file-based pages (`st.navigation`, `st.Page`) |
| Charts | Altair (Vega-Lite) with fixed method colours, fixed ordering and formatted labels |
| Graph drawings | A self-contained SVG view (inline HTML in an iframe) with a deterministic layout precomputed by the bundle builder; labels are escaped data, never HTML |
| Step timelines, cards, callouts | Small HTML components styled by one CSS sheet with light and dark colour tokens |
| Data | The checksummed bundle in `showcase/bundle/` |
| Text | `showcase/content/content.yaml` |
| Pinned requirements | streamlit 1.64.0, altair 6.3.0, pandas 3.0.6, numpy 2.5.3, pyarrow 25.0.1, PyYAML 6.0.3 |

## Files

Table: Files of the showcase application {w=1.9,4.3}
| File | Role |
|---|---|
| `showcase/app.py` | Entry point: page configuration, navigation sections, CSS, bundle check, sidebar (profile badge, presentation toggle, bundle checksum) |
| `showcase/launch.py` | Starts Streamlit with the theme and server flags (same command locally and in the container); `--profile`, `--port`, `--address` |
| `showcase/config.py` | Deployment settings from environment variables: profile, model server URL, live runs per session (8), question length (500 characters), live timeout (900 s) |
| `showcase/content/content.yaml` | All on-screen text: page introductions, method descriptions and steps, findings with placeholders, metric definitions, statistics explanations, situations, glossary |
| `showcase/lib/bundle.py` | Read-only bundle access with SHA-256 verification of every file at start-up |
| `showcase/lib/content.py` | Loads the content file and resolves placeholders against the bundle |
| `showcase/lib/fmt.py` | Deterministic number formatting (rates, tokens, seconds, p-values, signs, true minus sign, no negative zero) |
| `showcase/lib/ui.py` | The UI kit: page header, "On this page" strip, sections, callouts, cards, KPI tiles, score tables, test tables, answer boxes, ranking table, winner and situation cards, navigation footer |
| `showcase/lib/study.py` | One template for the Part 1–3 pages |
| `showcase/lib/charts.py` | Altair charts: method bars with intervals, quality–cost scatter, grouped bars, stacked counts, sign-flip histogram, family bars, overlap bars |
| `showcase/lib/explorer.py` | "Look inside one question" explorers of Parts 1–4 |
| `showcase/lib/graph_view.py`, `trace_view.py`, `traces.py` | Graph drawing, step-by-step timelines of retrieval-control traces, trace normalisation |
| `showcase/lib/metrics.py` | Answer metrics identical to the research code; detection of correct papers in a context or in retrieved evidence |
| `showcase/lib/live.py` | The live run engine of the full profile |
| `showcase/pages/p01_problem.py` … `p11_repro.py` | One file per page |
| `scripts/build_showcase_bundle.py` | Builds the bundle from the frozen outputs; `--check` confirms it is reproduced byte for byte |
| `tests/test_showcase.py` | The application's tests |

## The data bundle

@figure figures/a_bundle.png | The bundle pipeline: the builder exports the frozen outputs into nine checksummed files; the app verifies every checksum at start-up and the pages read only the bundle, with their text bound to it through the content file. | 6.2

The builder reads the frozen analysis file of each study, the run records, the stored model requests, the benchmark records, paper titles and the overall ranking, and writes nine files. Output is deterministic: JSON with sorted keys, gzip with a fixed timestamp, and line endings pinned in Git. A manifest stores the SHA-256 of every file and a bundle checksum over the `name:hash` lines.

@table bundle | Files of the showcase data bundle

@table sources | Frozen sources the bundle is built from (with their checksums)

At start-up the app re-hashes every file; if any file or the bundle checksum does not match, the affected content is withheld and an error is shown. `python scripts/build_showcase_bundle.py --check` rebuilds the bundle in memory and compares it byte for byte with the committed files; it reported **IDENTICAL** when this document was built.

## Text bound to data

A finding is written once in the content file with short placeholders, and a `values` map binds each placeholder to a bundle key. For example:

@code
- text: "CM-01 had the highest answer F1 ({F1}) and MRR ({MRR}), but used about {RATIO}x the input tokens of CM-B1."
  values: {F1: RQ1.methods.CM-01.answer_f1, MRR: RQ1.methods.CM-01.mrr, RATIO: RQ1.ratio.input_tokens.CM-01/CM-B1}
@end

Table: Placeholder key forms {w=2.4,3.8}
| Key form | Meaning |
|---|---|
| `RQx.methods.M.metric` | mean of a metric for one method |
| `RQx.test.metric.A~B.delta \| p \| p_holm` | paired test of A against B (B~A is the same test with the sign flipped) |
| `RQx.test.metric.max_p_holm` | largest adjusted p over all pairs of a metric |
| `RQx.ratio.metric.A/B` | ratio of two method means |
| `RQx.max.metric` | largest method mean |
| `RQ2.support.CLASS` | number of RQ2 bundles in a supportability class |
| `RQ4.selection.key` | a component chosen by the frozen RQ4 rule |
| `RQx.overall.winner`, `RQx.overall.total.M` | overall winner of a part; a method's rank total |
| `RQx.strata.dim.value.M.metric` | mean within one question group (for example modality.G) |
| `RQx.n.dim.value` | number of questions in that group |

A binding may end in `|pct`, `|ratio`, `|tokens`, `|rate`, `|p` or `|text` to override the default format. Tests verify that every placeholder resolves and that "+{X}" values read correctly. Numbers are formatted deterministically: rates with three decimals, tokens as integers with separators, latency in seconds with one decimal, p-values with three decimals, half-up rounding, a true minus sign and never a negative zero.

## Two profiles

@figure figures/a_profiles.png | The two profiles: "showcase" runs anywhere from the bundle alone; "full" adds live runs through the research code and the local model server. | 6.2

- **showcase** (default; used by the container): all pages; "Try a question" replays recorded runs. Needs only the pinned requirements and the bundle.
- **full**: adds a live run builder. A `LiveEngine` runs the frozen integrated-system code (`research/integration`) with any retrieval policy and any fusion method, CM-B1 fixed, over the real data, answered by `gpt-oss:20b` on the local model server. Requests identical to recorded ones are answered from the recorded responses (read-only); new responses are kept in `artifacts/showcase/live_stages`, so repeating a run is instant. One live run executes at a time; each browser session may start 8; readiness checks (research code, data, model server) are shown before anything can run, together with the GPU temperature.

## Theme and presentation mode

Colours are defined as tokens with light and dark palettes. The app follows the configured theme first and the browser's preference otherwise, and the launch script sets a light theme with a blue accent. **Presentation mode** (a sidebar toggle, or `?present=1` in the address) collapses the sidebar and enlarges text for projection. Method colours are fixed everywhere: grey for B0 controls, slate for B1 controls, blue for 01, green for 02, magenta for 03 and violet for the integrated system; the three sources are indigo (text), teal (graph) and orange (structured).

# Navigation and storyline

@figure figures/a_map.png | The eleven pages in four sections, in storyline order. | 6.4

@screencrop p01_problem__view 0,0,375,1000 | The sidebar: navigation in four sections, the "Live questions enabled" badge of the full profile, the presentation-mode toggle and the verified bundle checksum. | 2.3

Every page starts with a small kicker (its section), a title, a one-line introduction and an **"On this page"** strip of links to its sections. Every page ends with links to the previous and next page, so a presenter can walk the whole story with the footer alone. Explorer choices are written into the address bar (`?q=` for the question, `?m=` for the strategy), so a link reopens exactly the same view.

@screen p01_problem__view | The first screen of the application (sidebar expanded), as an audience first sees it. | 6.4

@screen p01_present__view | The same page in presentation mode: the sidebar is collapsed and the text is larger for projection. | 6.4

# Page-by-page guide

## The problem

**Purpose.** Open the talk: what the problem is, a real example, why it is hard and what counts as better.

**When to use it.** First, for two to three minutes. The overlap chart makes the core idea concrete: each source alone admits hundreds or thousands of papers, but only their overlap is the answer.

**What is on it.**

1. **The problem** — a one-paragraph statement and three cards describing the text, graph and structured views.
2. **A real question** — the three-source example question with each condition highlighted in the colour of the source that can check it; three cards with the number of papers each source alone admits (111, 479, 130,859); the overlap chart on a logarithmic scale down to the single correct paper; and the counter-examples that prove each source is necessary (Figure in Chapter 4).
3. **Why it is hard** — five numbered reasons.
4. **What counts as better** — four criteria cards: right answers, right evidence, lower cost, proven differences.

@screen p01_problem__02 | "The problem" section: the statement and the three views. | 6.2

@screen p01_problem__04 | "Why it is hard": five reasons. | 6.2

@screen p01_problem__05 | "What counts as better": the four success criteria. | 6.2

## Four parts

**Purpose.** Show how the problem is decomposed and the principle of one variable at a time.

**What is on it.**

1. **The pipeline** — Question → Retrieval control (Part 3) → Retrievers → Context management (Part 1) → Fusion (Part 2) → Answer model, with the studied stages highlighted, and the principle callout.
2. **The four parts** — one card per research question with its question, what changes, what stays fixed and what it is judged by, each with a link to its page.
3. **How they fit together** — three sentences on controls, methods and the pre-registered combination.

@screen p02_parts__02 | "The pipeline" with the three studied stages and the guiding principle. | 6.4

@screen p02_parts__03 | "The four parts": question, what changes, what stays fixed and how each part is judged. | 6.4

## Data and benchmark

**Purpose.** Show what the systems search and what they are tested on.

**What is on it.**

1. **Three views of one corpus** — the size of each view (700,244 documents; 1,872,968 nodes and 19,919,698 relations; 700,244 rows) and an expandable chart of relations by type.
2. **One paper, three views** — the correct answer of the example question as each retriever sees it, with the matching phrase highlighted, the structured conditions ticked, and an interactive graph drawing of the paper's neighbourhood with the proving path in green (Figure in Chapter 10).
3. **The benchmark** — question families (14), variants per family (4), validation questions (56) and the families per source combination.
4. **Variants of one question** — four tabs (normal, noisy, conflict, unanswerable), each showing the variant's question, what was added at evaluation time and its correct answer (the conflict tab is shown in Chapter 11).
5. **Which questions each part uses** — the cohort table of the four studies.

@screen p03_data__02 | "Three views of one corpus" with the relations chart expanded. | 6.2

@screen p03_data__04 | "The benchmark": families, variants and validation questions. | 6.2

@screen p03_data__05 | "Variants of one question" on the normal tab. | 6.2

@screen p03_data__06 | "Which questions each part uses". | 6.2

## Metrics and statistics

**Purpose.** Define every measure and show, on real data, when a difference counts.

**What is on it.**

1. **Metrics** — cards for every metric in four groups (answer quality, evidence, retrieval control, cost), each with a plain definition, a formula, its direction and why it matters.
2. **Try the answer metrics** — the playground: choose correct and returned papers and watch precision, recall, F1 and exact match update (Figure in Chapter 16).
3. **When is a difference real?** — five numbered steps: same questions, families, bootstrap, sign flips, Holm.
4. **Sign-flip test on real results** — pick one of four recorded comparisons; the page runs the exact test live, shows the per-family differences and the distribution of all sign-flip totals, and reproduces the reported p-value.
5. **Reasonable trade-offs** — the Pareto definition.
6. **Protocol** — the four rules that protect every result.

@screen p04_metrics__02 | Metric cards: answer quality and evidence. | 6.2

@screen p04_metrics__03 | Metric cards: retrieval control and cost. | 6.2

@screen p04_metrics__05 | "When is a difference real?": the statistical procedure in five steps. | 6.2

@screen p04_metrics__06 | The live sign-flip test on a recorded comparison; the computed p-value equals the reported one. | 6.2

@screen p04_metrics__07 | The Pareto definition. | 6.2

@screen p04_metrics__08 | The protocol rules. | 6.2

## Part 1 · Context management

The three single-component study pages (Parts 1–3) share one template; this section describes it once on Part 1, and the next two sections show what differs.

**What is on it.**

1. **The question** — the research question, what changes, what stays fixed, what it is judged by, and a banner naming the overall winner of the part with a one-sentence reason.
2. **The five strategies** — one card per strategy (control or method, Pareto badge, one-line idea, origin, cost) and a **step-by-step** selector that draws the chosen strategy's steps as a flow.
3. **Results** — the score table (best value per column highlighted, ★ for Pareto), a CSV download, the quality-against-cost scatter, and a bar chart of any chosen metric with family-bootstrap whiskers.
4. **Overall winner** — the ranking table (rank and value per axis, rank total, scaled score), a callout explaining the winner's ranks and the scaled-score check, and cards for the situations in which another strategy is the better pick.
5. **Is any difference real?** — the paired test table of the chosen metric with the verdict for each pair, a summary callout and a download of all tests.
6. **What we found** — numbered findings, with every number bound to the bundle.
7. **Breakdown** — the means by variant or by the sources a question needs, as a grouped bar chart.
8. **Look inside one question** — the explorer: filter by variant and sources, pick any question, see the correct answer, choose a strategy (or two side by side), and inspect what it returned, why, its metrics, the exact graph evidence it kept (drawn) and the exact context the model received.

@screen p05_rq1__01 | Part 1 page header: cohort, families and number of strategies. | 6.2

@screen p05_rq1__02 | "The question" with the overall-winner banner. | 6.2

@screen p05_rq1__03 | "The five strategies" with the step-by-step view of CM-01. | 6.2

@screen p05_rq1__04 | "Results": score table, quality-against-cost scatter and the metric bar chart with intervals. | 6.2

@screen p05_rq1__05 | "Overall winner": the ranking table, the explanation and the situations in which another strategy is better. | 6.2

@screen p05_rq1__06 | "Is any difference real?": paired tests of answer F1 for all ten pairs. | 6.2

@screen p05_rq1__07 | "What we found": findings bound to the bundle. | 6.2

@screen p05_rq1__08 | "Breakdown" by the sources a question needs or by variant. | 6.2

@screen p05_rq1__09 | The explorer's question picker and correct-answer box (the result view is shown in Chapter 19). | 6.2

## Part 2 · Fusion

Same template as Part 1, with three differences: the tests can be shown for several metrics (answer F1, exact match, input and output tokens, model calls, latency); a **"Could the evidence support an answer?"** section shows the supportability counts (2 fully, 6 partially, 16 not supportable), the classification rule and how each fusion method behaved; and the explorer shows each method's context composition, its model calls (including the selector, per-source reasoning and fusion calls) and the explanation of every empty answer.

@screen p06_rq2__02 | Part 2: the question and the overall winner (CF-B1). | 6.2

@screen p06_rq2__03 | Part 2: the five fusion strategies with the step-by-step view of CF-01. | 6.2

@screen p06_rq2__04 | Part 2 results: identical (empty) answers, so the scatter shows cost against latency. | 6.2

@screen p06_rq2__05 | Part 2 overall ranking and situations. | 6.2

@screen p06_rq2__06 | Part 2 paired tests (answer F1 shown; other metrics selectable). | 6.2

@screen p06_rq2__09 | "Could the evidence support an answer?": the supportability classes and the behaviour of each fusion method. | 6.2

## Part 3 · Retrieval control

Same template, with tests for seven metrics and a **"How each policy stopped"** section: a stacked bar of the stop reasons over the 28 questions and an expandable table of failure labels per policy. The explorer shows each policy's decisions as a step-by-step timeline: rule cues, classifier route, controller judgements, evaluator states, agent actions, drafts, validator verdicts and commentor feedback, each search with its query and result, and the stop reason.

@screen p07_rq3__02 | Part 3: the question and the overall winner (AR-B1). | 6.2

@screen p07_rq3__03 | Part 3: the five policies with the step-by-step view of AR-01. | 6.2

@screen p07_rq3__04 | Part 3 results: the score table. | 6.2

@screen p07_rq3__05 | Part 3 results: source selection against cost, and the metric bar chart. | 6.2

@screen p07_rq3__06 | Part 3 overall ranking and the four situations. | 6.2

@screen p07_rq3__07 | Part 3 paired tests (answer F1 shown; seven metrics selectable). | 6.2

@screen p07_rq3__09 | Part 3 breakdown by the sources a question needs. | 6.2

@screen p07_rq3__10 | "How each policy stopped" with the failure labels expanded. | 6.2

@screen p07_rq3__11 | Part 3 explorer: question picker and correct answer (the side-by-side result is shown in Chapter 21). | 6.2

## Part 4 · Combined system

**Purpose.** Show that the three winners, combined, are exactly the system chosen by the rule fixed in advance, and what the combination achieves.

**What is on it.**

1. **The three winners combined** — the pipeline of winners with their rank totals and runners-up, a callout confirming that the pre-registered rule picked the same three, and the rule itself (expandable).
2. **Results** — INT-1 against AR-B0 and AR-B1, with a CSV download.
3. **Is any difference real?** — tests for answer F1, source-selection F1, tokens and latency.
4. **What we found** — four bound findings.
5. **Look inside one question** — the three stages of the combined system for any question: the router's decisions, what CM-B1 kept, what CF-B1 wrote, the model call and the exact context (shown in Chapter 22).
6. **Final scoreboard** — one row per part: overall winner, Pareto set, highest answer F1, cheapest, and what the tests support.

@screen p08_rq4__02 | "The three winners combined" with the pre-registered rule expanded. | 6.2

@screen p08_rq4__03 | Part 4 results. | 6.2

@screen p08_rq4__04 | Part 4 paired tests. | 6.2

@screen p08_rq4__05 | Part 4 findings. | 6.2

@screen p08_rq4__07 | The final scoreboard of the four parts. | 6.2

## Conclusions

**Purpose.** The verdict in one screen: the winner of each part, the combined system, when to pick something else, the key findings, limitations and next steps.

@screen p09_summary__01 | Conclusions: the verdict. | 6.2

@screen p09_summary__02 | The three winners, each with its reason, rank total and runner-up. | 6.2

@screen p09_summary__03 | The combined system and its key figures. | 6.2

@screen p09_summary__04 | When to pick something else: every situational choice of Parts 1–3. | 6.2

@screen p09_summary__05 | Key findings. | 6.2

@screen p09_summary__06 | Limitations. | 6.2

## Try a question

**Purpose.** Let the audience see the pipelines work on a question of their choice, step by step.

**Recorded runs** (both profiles). Choose one of six recorded pipelines: the combined system (AR-B1 → CM-B1 → CF-B1) or any of the five Part 3 policies with their fixed answer step. Optionally compare it with a second pipeline side by side. Filter and pick any of the 28 Part 3 questions. Each result shows the pipeline strip, the answer box (✔ or ✘ per paper, or an explanation of an empty answer), the sources searched against the sources needed, five KPI tiles (answer F1, searches, model calls, tokens, time), the step-by-step trace, what context management and fusion did, the model calls and the exact context the model received.

@screen p10_try__01 | Try a question, recorded mode: pipeline choice, comparison choice, question filters, the question and its correct answer. | 6.2

@screen p10_try__02 | A recorded run of the combined system: the answer, KPIs, step-by-step trace and the context-management and fusion summaries. | 6.2

@screen p10_try_expanded__02 | The same run with "Model calls" and "Exact context the model received" expanded: every call's tokens and time, and the exact text the model read. | 6.2

@screen p10_try_compare__02 | Two recorded pipelines side by side on the same question: the combined system and the AR-03 agent. | 6.2

**Live run** (full profile only). The builder offers any retrieval policy and any fusion method (CM-B1 fixed), an optional second pipeline, and either a benchmark question (scored against its correct answer) or the user's own question (not scored, at most 500 characters). A status panel lists the readiness checks and the GPU temperature. Live answers are labelled as demonstrations; a session may start 8 live runs; repeating a run is answered from stored responses.

@screen p10_try_live__01 | The live run builder: readiness status, policy and fusion choices, comparison toggle, question source and the run button with the remaining session allowance. | 6.2

@screen p10_try_liverun__02 | A live run of AR-B1 → CM-B1 → CF-B1. Its single model call was answered from the recorded responses, so the run took 0.2 s while reporting the original 7.3 s of model compute. | 6.2

## Reproducibility

**Purpose.** Show how every number can be traced and re-run.

**What is on it.** How results are protected (frozen plans, one bundle, stored model calls, the protocol rules); this app's data (bundle checksum, verification of each of the nine files, the frozen sources with their checksums, the run records per study and method, and a JSON download of all results); the setup (answer model, retrievers, evaluation scope); and the rebuild commands.

@screen p11_repro__02 | "How results are protected". | 6.2

@screen p11_repro__03 | "This app's data": the bundle checksum, the verified files and the frozen sources. | 6.2

@screen p11_repro__04 | Run records per study and method, and the results download. | 6.2

@screen p11_repro__05 | Setup. | 6.2

@screen p11_repro__06 | Rebuild commands. | 6.2

# Interactive features in depth

## Explorers and shareable links

Every study page ends with an explorer over its recorded runs. Variant and source filters narrow the list of questions; the question picker shows the source combination, variant and a short form of each question. The explorer opens on an informative question: one where the default strategy returned correct papers (normal variant first, then the highest F1), otherwise one where a correct paper reached the model, otherwise the running example. The chosen question and strategy are written into the address (`?q=…&m=…`), so copying the link shares exactly that view.

## Graph drawings

Graph evidence is drawn as an interactive SVG with a deterministic layout computed when the bundle is built (component packing with minimum node spacing). Node shapes and colours encode the type (paper, author, institution, field of study); rings mark the correct answers, the papers the model returned and the retriever seeds or the entity named in the question; green arrows mark the path that proves the answer. The drawing supports fit, zoom, relation-label and node-name toggles, and hover or click for details. Large graphs are capped for display (for example 60 of 69 nodes), and the caption says so; the cap never affects the context.

## Step-by-step timelines

Retrieval-control runs are normalised into ordered steps (plan, route, classify, search, decide, evaluate, agent, draft, validate, comment, stop) and drawn as a timeline with icons, source chips, cues, queries, result counts and timings, ending with the stop reason. Tests check that every trace is ordered and complete.

## Explained answers

An empty answer is never shown as a bare "wrong". The answer box explains where the correct papers were lost, using two counts recorded for every run: whether a correct paper was among the retrieved evidence (*gold retrieved*) and whether it reached the model's context (*gold seen*).

@figure figures/a_answer_tree.png | How the answer box explains a result. A non-empty answer lists each paper as correct or wrong; an empty answer states whether no paper was correct, the retrievers never returned the correct paper, the strategy left it out of the context, or the model saw it and judged that no paper met every condition. | 6.2

## Downloads

Score tables and test tables can be downloaded as CSV on every study page, and the Reproducibility page offers all study results as one JSON file.

# Quality assurance, running and deployment

## Tests

The application's tests (`tests/test_showcase.py`, 36 test cases) cover:

Table: What the showcase tests verify {w=2.4,3.8}
| Test | What it checks |
|---|---|
| Bundle checksums verify | every bundle file matches the manifest and the bundle checksum |
| Bundle matches the frozen analyses | the exported numbers equal the analysis files of the studies |
| Bundle rebuild is byte-identical | rebuilding the bundle reproduces every file exactly |
| Content has no stray YAML keys | YAML parsing did not split values containing commas into stray keys |
| Every placeholder resolves | every finding's placeholders resolve, and "+{X}" values are non-negative |
| Formatting is deterministic (parametrised) | rounding, signs, separators and units for every number kind |
| Answer scores match the research metrics (parametrised) | the app's metric code equals `research.evaluation.metrics` on edge cases |
| Traces are ordered and complete | every retrieval-control trace has ordered steps ending in a stop |
| Every page renders (both profiles) | all 11 pages run without exceptions under Streamlit's AppTest |
| Explorers respond to choices | changing question and strategy changes the view |
| Overall winners are reproducible | the overall ranking recomputed from the means equals the stored winners, the content and RQ4 |
| Answer explanations are consistent | *gold seen* never exceeds *gold retrieved*; in Part 2, gold is retrieved exactly when a bundle is not unsupportable |

When this document was built, the complete project suite passed (**327 passed**, one known deprecation warning from DuckDB), and the bundle check reported **IDENTICAL**.

## Running

@code
python showcase/launch.py                               # recorded results, http://127.0.0.1:8501
python showcase/launch.py --port 8610 --profile full    # also live runs (research data + local model server)
python scripts/build_showcase_bundle.py                 # rebuild the bundle from the frozen outputs
python scripts/build_showcase_bundle.py --check         # confirm the committed bundle is reproduced byte for byte
python -m pytest tests/test_showcase.py -q              # the application's tests
@end

Table: Environment variables {w=2.0,1.6,2.6}
| Variable | Default | Meaning |
|---|---|---|
| `SHOWCASE_PROFILE` | `showcase` | `showcase` (replay only) or `full` (adds live runs) |
| `SHOWCASE_OLLAMA_URL` | `http://127.0.0.1:11434` | model server for the full profile |
| `SHOWCASE_LIVE_RUNS` | 8 | live runs allowed per browser session |
| `PORT` | 8501 | port used by the launch script and the container |

## Deploying

The container runs the showcase profile with no research code or data inside:

@code
docker build -t mmg-showcase showcase
docker run --rm -p 8501:8501 mmg-showcase              # http://localhost:8501
@end

It is based on `python:3.12-slim`, installs only the pinned requirements, runs as a non-root user and has a health check on Streamlit's health endpoint. On hosted Streamlit services the entry point is `showcase/app.py` with `showcase/requirements.txt`. The app adapts its styling to a dark browser theme if the host does not apply the launch theme.

# Presentation script

A suggested walk-through of about fifteen minutes. Turn on presentation mode first.

Table: Suggested live presentation {w=0.6,1.5,4.1}
| Time | Page | What to show and say |
|---|---|---|
| 0:00 | The problem | Read the example question; point at the three counts (111, 479, 130,859) and the overlap chart ending at 1 paper. "Each source checks part of the question; the answer is the overlap." |
| 1:30 | Four parts | Point at the pipeline: three studied stages, one at a time, then combined. "Only one component changes in each study." |
| 3:00 | Data and benchmark | Show one paper in three views and the green proving path; open the conflict tab. "Answers are computed before questions are worded; stress variants never change the data." |
| 4:30 | Metrics and statistics | Change the playground sets; then run the sign-flip example. "Families, not questions, are independent; the p-value is computed live and matches the report." |
| 6:00 | Part 1 | Winner banner; quality–cost scatter; ranking table; one situation card (CM-01 for quality). Open the explorer: CM-01 returns 14 correct papers of 78. |
| 8:00 | Part 2 | Supportability: 16 of 24 bundles hold no correct paper. Explorer: the correct paper reached the model, which still abstained. "Fusion cannot recover what retrieval missed." |
| 9:30 | Part 3 | Same answers for all policies; the router chooses sources best and cheapest; "How each policy stopped". Explorer side by side: router vs agent. |
| 11:30 | Part 4 | The three winners combined equal the pre-registered choice; final scoreboard. |
| 12:30 | Conclusions | The verdict, when to pick something else, limitations. |
| 13:30 | Try a question | Replay the combined system on a question the audience picks; open "Exact context the model received". With the full profile, run a live pipeline. |
| 15:00 | Reproducibility | Bundle checksum and verified files. "Every number on screen is traceable to a frozen file." |
