# Isolating context management, cross-modal fusion and retrieval control in multi-modal GraphRAG

A controlled, one-variable-at-a-time study of multi-modal GraphRAG over **text, graph and structured** views of the
STaRK-MAG scholarly corpus (700,244 papers, 1.87 million entities, 19.9 million relations), with a replayable
interactive application.

Retrieval-augmented systems that combine several knowledge sources change how sources are queried, how evidence is
fused and how the context is managed all at once, so it is unclear which design decision matters. This project freezes
the data, the retrievers, the language model, the prompt and the context budget, varies **one component at a time**
and only then integrates the winners.

| Study | Question | Strategies compared | Winner |
|---|---|---|---|
| RQ1 | Context management: which graph evidence survives a fixed budget? | raw order, fixed top-K, KG²RAG-, G-Retriever- and QAFD-RAG-inspired | CM-B1 fixed top-K |
| RQ2 | Cross-modal fusion: how to combine text, graph and structured evidence? | concatenation, labelled sections, KAG-, SAG- and MegaRAG-inspired | CF-B1 labelled sections |
| RQ3 | Retrieval control: which sources, in what order, when to stop? | all sources, rule router, Adaptive-RAG-, CRAG- and AGENT-G-inspired | AR-B1 rule router |
| RQ4 | Integration of the winners | INT-1 = AR-B1 → CM-B1 → CF-B1 | same answers, significantly better source selection than querying everything |

**Main findings.** No literature-inspired method improved answer quality with statistical support; the simple controls
won every component on combined quality and cost, and the learned and agentic controllers spent up to about 6,100 more
tokens per question for identical answers. Answer quality is bounded upstream, by retrieval coverage.

## What makes it a controlled study

- **Isolated views** joined only by the global node identifier: the text view (title + abstract, MiniLM + exact FAISS),
  the graph view (four official relation types, memory-mapped CSR) and the structured view (DuckDB, nullable attributes).
- **Verified benchmark:** gold answers are computed before wording; every multi-source question provably needs every
  source; noisy, conflicting and unanswerable variants are evaluation-time overlays.
- **Replay-verified execution:** every study is frozen by SHA-256; every model request is stored by the hash of its
  payload; results are rebuilt by a runner that refuses any request that differs (448 run records, 0 errors).
- **Correlation-aware statistics:** family-clustered bootstrap intervals, exact sign-flip tests with Holm correction,
  Pareto sets and an overall ranking.
- **327 automated tests**, exhaustive data and benchmark audits, and a checksummed results bundle.

## Run the application

The application presents every result and replays every recorded run step by step. It reads only the checksummed bundle
in `showcase/bundle/`, so it runs on any machine without the dataset, a GPU or a language model.

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
```

```bash
pip install -r showcase/requirements.txt
```

```bash
python showcase/launch.py
```

Then open <http://127.0.0.1:8501>. With Docker: `docker build -t mmg-showcase showcase` and
`docker run -p 8501:8501 mmg-showcase`.

**Live questions (`--profile full`)** additionally need the research environment (`requirements*.txt`), the built data
in `data/MMG_STARK_MAG/` (about 9 GB, not in Git), the trained AR-01 classifier and AR-02 cross-encoder under
`artifacts/phase9/` (not in Git), and [Ollama](https://ollama.com) serving `gpt-oss:20b`. See `showcase/README.md`.

## Data

The source corpus is the official STaRK-MAG release on Hugging Face,
[`snap-stanford/stark`](https://huggingface.co/datasets/snap-stanford/stark) (revision
`88269e23e90587f99476c5dd74e235a0877e69be`, CC-BY-4.0). The three views and the benchmark are derived from it
deterministically by the scripts in `scripts/` (`stage_stark_mag.py`, `audit_stark_mag.py`, `build_mmg_stark_mag.py`,
`build_benchmark.py`) and verified against the SHA-256 manifests committed under `documentation/`. The built data are
too large for GitHub and are therefore not included.

## Repository layout

| Path | Contents |
|---|---|
| `research/` | Research package: data build, benchmark, retrievers, all strategies, execution and analysis |
| `scripts/` | Command-line entry points: build, audit, run, report, freeze |
| `configs/` | Frozen configurations |
| `tests/` | Automated test suite (327 tests) |
| `showcase/` | Interactive application and its checksummed data bundle |
| `documentation/` | Phase reports, frozen plans, run records, analyses, decision log |
| `documentation/paper/` | Research papers: IEEE conference version (Word, PDF, LaTeX) and journal version (Word, PDF) |
| `documentation/report/` | B.Tech project report (Word, PDF) |
| `documentation/project_documentation/` | Full project documentation (Word, PDF) with figures and application screenshots |
| `app.py`, `src/`, `README.md` | The original demonstration (traditional RAG vs. basic GraphRAG), frozen as the project's starting point |

## Author

Aaditya Bhure, Department of Computer Science and Engineering, Symbiosis Institute of Technology, Nagpur.
