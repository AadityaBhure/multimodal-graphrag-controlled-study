# Phase 0 — Freeze and Audit the Working MVP

PHASE: 0 — Freeze and Audit the Working MVP

STATUS: PASS (baseline smoke verification; answer limitations recorded below)

OBJECTIVE: Preserve the working showcase and record a reproducible baseline before research changes.

## Files created or modified

- `.env.example`: replace credential-like value with an empty placeholder; `.env` remains untouched and ignored.
- `scripts/audit_baseline.py`: inventory, explicit live checks, offline evidence checks, and Streamlit AppTest.
- `configs/baseline_mvp_snapshot.yaml`: effective non-secret configuration and artifact counts.
- `documentation/Research_Decision_Log.md`: Phase 0 decisions.
- `documentation/baseline_phase0/`: package freeze, inventory/checksums, pytest output, UI result, live/offline query records, storage archive, and secret-scan result.
- This phase report and a local Git baseline reference `baseline-mvp-v1`.
- No changes to `app.py`, `src/`, existing tests, input PDFs, metadata, or working indexes.

## Commands run

Commands used the project interpreter `.\.venv\Scripts\python.exe` unless stated otherwise.

- `git status --short` and `git rev-parse --show-toplevel`: initially reported no repository; parent directories checked before initialization.
- `python -m pytest -q`: 18 passed in 0.84 seconds; saved repeat: 18 passed in 0.77 seconds.
- `python -m pip freeze`: saved to `documentation/baseline_phase0/requirements.freeze.txt`.
- `python -m pip check`: no broken requirements found.
- `python scripts/audit_baseline.py text`: first attempt returned a connection error; after explicit user approval, network-enabled rerun succeeded.
- `python scripts/audit_baseline.py text --offline`: evidence available, generation intentionally disabled.
- `python scripts/audit_baseline.py graph --offline`: graph evidence and candidate-restricted supporting chunks verified.
- `python scripts/audit_baseline.py ui`: all three tabs loaded, zero exceptions/errors.
- `python scripts/audit_baseline.py inventory`: effective configuration, input/source/storage inventory and SHA-256 hashes.
- `python scripts/audit_baseline.py graph`: approved live request succeeded.
- Inline Python: archive the four storage files; inspect returned evidence; scan local files and DOCX/ZIP members for configured secrets and Groq-key patterns.
- `git init`, explicit staging, cached-diff checks, baseline commit, and annotated `baseline-mvp-v1` tag. Resolve the exact commit using `git rev-parse baseline-mvp-v1^{commit}`. Git commands after initialization used `git -c safe.directory=D:/codefiles/RAG_GraphRAG_Demo` because sandbox/user ownership differed; no global Git configuration was changed.

## Validation and tests

- Python 3.12.14; normalized 384-dimensional all-MiniLM-L6-v2 embeddings; FAISS IndexFlatIP.
- Existing suite: 18/18 pass. Coverage includes real-corpus retrieval, graph bounds/ranking, candidate-only supporting chunks, context budgets, and generation error handling.
- Traditional live query: “How does G-Retriever select a compact subgraph?” Returned five P002 chunks and an answer explaining relevance prizes, PCST and edge costs, citing P002. Core explanation agrees with retrieved evidence.
- Graph live query: “Which agentic retrieval approaches use self-reflection?” Returned three seeds, five candidate papers and six supporting chunks in final context; generated an answer citing P011/P012. P011 evidence explicitly supports AGENT-G self-reflection. Broader claims require caution as noted below.
- Streamlit AppTest executes the actual app script: Demo, Architecture and Dataset present; no UI errors/exceptions. This is not a browser screenshot/layout review.
- Package dependency consistency passes.
- Secret scan passes for configured credential values and Groq-key patterns, including document/archive contents. This is a bounded scan, not proof against every possible unknown secret format.

## Artifact counts

- 12 metadata papers and 12 PDFs.
- 394 chunks and 394 embedding vectors; dimension 384.
- Graph: 74 nodes and 87 edges.
- Four existing storage artifacts preserved in `storage_snapshot.zip`.
- Two successful live query records, two offline records, one UI smoke record.
- Effective generation model: `openai/gpt-oss-120b`, temperature 0.
- Chunk size/overlap 450/75 words; text top-K 5; graph seeds 3, depth 2, maximum papers 5, chunks per paper 2; context cap 24,000 characters.

## Decisions logged

See `documentation/Research_Decision_Log.md`. No research algorithm or experimental control was changed.

## Known issues

- A credential-like value was present in `.env.example` before sanitization. It was not committed. The credential owner should rotate/revoke it because it was exposed; the audit does not establish whether it is active.
- The graph answer contains zero-width characters inside citations. It also makes a broad negative statement about other approaches; retrieved evidence cannot establish universal absence. P012's self-reflection wording includes general background rather than clean method-specific attribution. These are baseline generation limitations, not validated research findings. No prompt changes were made.
- README references an older MVP specification DOCX that is absent from this checkout. The full implementation roadmap is present.
- The package freeze captures installed versions, but cannot guarantee future remote API behavior or bit-identical generated text. The cached model is external to the repository; a fresh machine needs the named model available/downloaded.
- The original failed network check was superseded by successful approved checks. Live checks make two successful API calls; they do not establish benchmark-level quality or latency.

## Scientific invariants checked

- Same existing embedding and generation models in both modes; temperature 0.
- Existing retrieval parameters, prompts, corpus and storage unchanged.
- Secrets omitted from snapshots/reports; `.env` ignored.
- Baseline artifact hashes and installed versions recorded; local archive preserves original indexes.
- No dataset acquisition, research scaffold, advanced methods, tuning, benchmark construction or test campaign started.
- No research result, superiority or novelty claims made.

## Restore and reproduce

Check out `baseline-mvp-v1` in a separate directory. Recreate a Windows CPython 3.12.14 virtual environment and install the frozen requirements. Extract `documentation/baseline_phase0/storage_snapshot.zip` into that directory to restore storage. Configure credentials locally through `.env`; never commit them. Ensure the named embedding model is cached; the audit deliberately defaults to offline model loading. Run pytest and the audit modes above. Live modes transmit demo queries and retrieved excerpts to Groq and require network access and a valid key.

REVIEW QUESTIONS FOR USER: None required to assess this phase; review the documented answer limitations.

NEXT PHASE (NOT STARTED): Phase 1 — Research Scaffold, Configuration, and Experiment Contracts.

STOP: Await explicit user approval before starting Phase 1.
