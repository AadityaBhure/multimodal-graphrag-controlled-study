# Research UI launch guide

From `D:\codefiles\RAG_GraphRAG_Demo`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run research_app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true --browser.gatherUsageStats false
```

Open http://127.0.0.1:8502. The existing Phase 0 `app.py` remains unchanged and can run separately on its usual port. Use the existing project environment and staged dataset; no new dependencies or dataset downloads are required.

1. In **Query playground**, load a representative example or enter a question. Select B1, B2, B3 or B4 and press **Retrieve evidence — no LLM**.
2. Expand evidence to inspect text, graph paths, structured records, provenance and SQL predicates. The answer-generation button alone sends the current question and retained context to Groq, using the existing project credential configuration and approved generation settings. Missing credentials produce a recorded setup error. Changing the question or method requires retrieval again; ordinary reruns do not generate.
3. In **Dataset explorer**, search paper titles, open a STaRK paper ID, or inspect a node's paginated neighborhood. NULL attributes remain unknown; inverse traversal rows are explicitly identified.
4. In **Compare methods**, run any selected baselines on the same question without generation. Their evidence stays source-separated.
5. **Performance** shows measured latency, calls, context statistics and available token usage. Gold-dependent metrics are NULL for these ad hoc inspections. Historical Phase 6 results are available read-only.
6. **Execution trace** shows source diagnostics, evidence inclusion, the exact constructed context, generation status and provenance. Download an inspection JSON before closing the session if you want to retain it.

The interface keeps the last 20 inspections in session memory. Retrieval caches and temporary work live under ignored `artifacts/research_ui/`; this is not a benchmark experiment runner or persistent experiment database. Use **Release loaded data** to close loaded stores. First retrieval may take tens of seconds; the exact FAISS index occupies about 1 GiB. Explorer pages show 20 papers or 25 relationships, never the full graph.

The four presets demonstrate Text title retrieval, Graph affiliation traversal, an exact Structured predicate match, and the previously difficult TGS query. The TGS preset demonstrates retrieved evidence, not a claim of successful question answering.

Validation commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe scripts/check_research_ui.py
.\.venv\Scripts\python.exe scripts/audit_phase6_5_preservation.py
```

The integration smoke writes only Phase 6.5 review artifacts and ignored UI caches, and makes zero API calls. The preservation script checks the Phase 6 checkpoint and frozen payloads; its HEAD assertion intentionally requires the recorded phase boundary.
