# Phase 7 implementation protocol and decisions

Phase 7 starts from approved checkpoint `cd450bbd850fc8066c82b701310420d27e7f0df7`; the working tree was clean before implementation. Existing tracked Phase 0–6.5 code and artifacts remain unchanged. New code lives in `research/rq1/` because the user explicitly froze previous code, including the earlier placeholder modules. The existing ContextPackage and Phase 5 SystemInput/SystemOutput/runner/metrics are reused through an additive adapter.

## Fixed upstream boundary

All five methods consume the identical immutable Pool for a query. The pool contains only graph node IDs/types/source labels and official graph relationships; paper labels are titles, never abstracts. Missing labels and their semantic representations remain NULL. No context manager receives a store, retriever, SQL interface, benchmark record or gold answer.

The common materializer uses the exact seed IDs recorded by the unchanged B2 resolver in the approved closeout. It exposes a bounded graph candidate pool rather than B2's final five-paper answer evidence: breadth-first depth 2, at most 256 base nodes, 1,024 base traversal rows, and the original 128-row per-node scan cap. This is a **new shared RQ1 boundary**, not a modification of B2. First discovery in seed/CSR order determines parent paths and ordering. Every method receives the same pool hash. CM-01's one-hop expansion is restricted to this pre-materialized universe.

For noisy inputs, up to five existing benchmark graph distractor paths are added before any context method runs, with explicit evaluation-overlay flags; hard combined limits are 320 nodes and 1,536 edges. This common overlay policy is intentionally broader than B2's final-candidate-only noise injection and is recorded as an RQ1 adaptation. No source data or benchmark record is edited. Directed and derived-inverse provenance is retained; optimization uses an undirected local projection, not a changed source graph. Official source edge count remains 19,919,698; inverse traversal rows are not counted as additional source edges.

The frozen MiniLM ONNX encoder (revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`) encodes the query and available source labels. Node relevance is their cosine similarity. Edge relevance is the mean of available endpoint query similarities, or zero when neither has semantics. MST cost is 1 minus endpoint cosine, or 1 if either label is missing. These choices were implemented before reading comparison results. No text, abstract, structured attribute or SQL retrieval occurs.

## Context variants

| Method | Fixed mechanism |
| --- | --- |
| CM-B0 | Candidate node order followed by candidate edge order, with only atomic serialization and the global 24,000-character cap. |
| CM-B1 | First five candidate paper nodes with recorded depth at most 2, including their parent paths; deterministic DFS serialization. No adaptive scoring. |
| CM-01 | Top 10 semantically scored nodes; one-hop expansion within the pool; connected components; deterministic Kruskal minimum spanning forest on cost 1−cosine; DFS rooted at highest query relevance; cross-encoder component ranking; budget selection. |
| CM-02 | Top three node relevance ranks receive descending positive prizes. Top five distinct edge-relevance levels receive rank prizes shared across ties, with 0.99 tie-level decay. Fixed edge cost 0.5; edge prizes transform to reduced costs or virtual prize nodes; official pcst_fast with root −1, one cluster, GW pruning. No adaptive edge-cost reduction. |
| CM-03 | Top 20 available semantic nodes seed query-weighted excess-flow diffusion. Mass 10 per seed, sink capacity 1, epsilon .05, support threshold .01, and one million pushes maximum. Product of shifted endpoint cosine similarities weights edges; missing semantic labels use a neutral routing factor .5 without inventing labels or embeddings. Deterministic maximum-excess scheduling replaces random scheduling. |

CM-01 uses **BAAI/bge-reranker-large**, explicitly selected by the user on 2026-10-09, revision `55611d7bca2a7133960a6d3b71e083071bbfc312`. CPU float32, two threads, batch size one, 512-token pair limit. Organized components are reranked as units; their internal DFS order stays intact. Truncated component counts are logged. This is a context-organization adaptation, not the full KG²RAG system. [Official KG²RAG implementation](https://github.com/nju-websoft/KG2RAG/blob/main/code/kg_rag_distractor.py).

PCST uses the official unmodified `pcst_fast` 1.0.10 source, compiled locally with GNU C++ and pybind11 3.0.1 because the Windows pip build required unavailable Microsoft build tools. Solver/source/runtime checksums are recorded in `pcst_build.json`. Empty/disconnected output falls back to the deterministic highest-relevance node; missing semantics use the smallest ID with an explicit reason. Solver exceptions are errors, not hidden fallback successes. The virtual-node construction follows the G-Retriever approach; no neural graph encoder is implemented. [Official solver](https://github.com/fraenkel-lab/pcst_fast), [G-Retriever retrieval code](https://github.com/XiaoxinHe/G-Retriever/blob/main/src/dataset/utils/retrieval.py).

Diffusion conserves injected mass. Each push leaves the node at sink capacity and distributes excess proportional to query-weighted adjacency; accumulated support adds excess divided by weighted degree. Support is normalized by its maximum. Convergence requires no node exceeding capacity by epsilon. A component whose injected mass exceeds the sum of capacities plus the permitted residual cannot converge; this is detected before iteration. Nonconvergence, stranded excess or empty support uses the explicitly logged top-five semantic-node fallback. The fixed-capacity bounded-pool adaptation does not claim the original paper's statistical guarantees. It omits warm-start walks and degree-normalized sinks, uses the user's frozen defaults, and records these differences explicitly. [Official QAFD reference, pinned commit](https://github.com/Tarzanagh/QAFD-RAG/blob/2a3a42c8ea4e9c416de0a7fe53c04fab50b756ef/src/retrievers/flow_diffusion.py).

## Serialization and controls

The same graph JSON-line serializer and 24,000-character cap apply to every method. Nodes and edges are atomic; no partial facts are emitted. Edges require both endpoint nodes in the context. Selected trees serialize a parent edge with each child so a budget cut cannot leave a disconnected child. Repeated evidence IDs are omitted. This is graph selection/organization, not paraphrasing or learned compression.

Generation is off for the comparison. If explicitly enabled in a later approved sample, the adapter reuses the frozen Groq generator, prompt, temperature, seed and answer parser. No new generation prompt, model, retrieval routing, fusion, benchmark, embedding index or scientific metric is introduced. The final model remains `openai/gpt-oss-120b`, temperature 0, maximum completion 1,024, low reasoning effort. Global seed is 42 with the unchanged runner's query-derived seed.

Retrieval metrics in the comparison measure **selected paper nodes surviving context control**. Shared materialization latency is recorded once per pool and attributed equally in supplementary diagnostics; per-variant retrieval latency/calls are zero because the immutable pool is cached. Context latency is separate in diagnostics. Full original evidence is preserved in each RunRecord; retained IDs identify context survivors. Raw CM-B0 for the same pool is the explicit context-reduction reference.

Answer quality, generation latency, token usage, cost and annotated evidence coverage stay NULL when unmeasured. Redundancy is the existing exact evidence-ID metric, not a semantic-duplicate metric. The candidate contract already has unique IDs, so no semantic-redundancy advantage is inferred. No seed sweep or other tuning was performed; every variant used its frozen defaults.

## Commands and review UI

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe scripts/prepare_phase7.py
.\.venv\Scripts\python.exe scripts/run_phase7.py
.\.venv\Scripts\python.exe scripts/report_phase7.py
.\.venv\Scripts\python.exe scripts/audit_phase7.py
.\.venv\Scripts\python.exe -m streamlit run context_review_app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false
```

The new viewer is read-only. It displays the before/after pool, selected nodes/edges, exact context and diagnostics, and renders at most 25 edges. The approved research UI on 8502 and original demo are unchanged. The project pytest configuration limits discovery to `tests/`, avoiding third-party tests bundled in downloaded native source.

The existing runner refuses incompatible resumes. Pools and model files have checksums; pool identities exclude build timing but retain boundary and source provenance. A later checkpoint changes Git provenance; do not overwrite completed runs when reproducing under a new commit. Use a separate output directory in a copied run script or restore the recorded execution state. Dependencies: existing project Python 3.12.14, PyTorch/Transformers, plus pybind11 3.0.1, matplotlib 3.10.7, and the local official PCST build. `scripts/build_phase7_pcst.py` reproduces the Windows solver build; use the project venv. Model weights remain in ignored `artifacts/phase7/reranker/`.

Fresh environment setup: install the existing project dependencies, then `.\.venv\Scripts\python.exe -m pip install -r requirements-phase7.txt`, run `scripts/build_phase7_pcst.py` on this Windows GNU toolchain, and run `scripts/setup_phase7_reranker.py`. The latter downloads only the approved pinned model and verifies its recorded hashes. Candidate preparation rejects changed/unowned snapshots and preserves prior manifest ownership across resume. Config preparation refuses incompatible existing config files before execution.
