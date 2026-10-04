# Traditional RAG and Basic Graph-Aware RAG

Local baseline over the same 12 research PDFs. Implementation follows
`documentation/Codex_Implementation_Spec_RAG_GraphRAG_MVP.docx`.
Traditional RAG searches PDF chunks directly. Basic GraphRAG first selects
papers through a curated metadata graph, then searches only those papers' chunks.
Both modes share normalized 384-dimensional `all-MiniLM-L6-v2` embeddings and
one Groq model at temperature 0. This is a metadata graph-aware baseline, not
Microsoft GraphRAG or an implementation of the research methods in the corpus.

## Setup

Use standard Windows CPython 3.11 or 3.12 from the project root. Avoid MSYS2
Python for this environment; it creates a different virtual-environment layout.
The existing `.venv` has been installed and verified with Windows CPython 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set your Groq key in `.env` only. Never commit this file. The supplied default
`llama-3.3-70b-versatile` was unavailable to the configured Groq account during
validation. The working local configuration uses:

```dotenv
GROQ_MODEL=openai/gpt-oss-120b
```

The key is optional for retrieval: missing keys disable generation while keeping
evidence visible. Internet is needed for installation, the first embedding-model
download, and Groq calls. Subsequent retrieval uses local artifacts and the cached
model. For explicitly offline retrieval, set `$env:HF_HUB_OFFLINE='1'` after the
model has been downloaded.

If activation is unavailable, use `.\.venv\Scripts\python.exe` instead of
`python`, and `.\.venv\Scripts\python.exe -m streamlit` instead of `streamlit`.

## Build

With the virtual environment activated:

```powershell
python scripts/build_all.py
```

The build parses all 12 supplied PDFs into 394 word chunks, creates normalized
embeddings and a FAISS IndexFlatIP, and persists a 74-node / 87-edge NetworkX
graph. It validates reloaded artifacts before reporting success. Individual PDF
errors are reported and skipped; fewer than five parsed PDFs aborts the build.

PDF filenames retain the supplied doubled `.pdf.pdf` suffix and are mapped
exactly in `data/metadata.json`. Do not rename files without updating metadata.

## Run

```powershell
streamlit run app.py
```

Open the local URL printed by Streamlit. The Demo tab exposes answers, evidence,
scores, timings, and the exact context/request messages. Basic GraphRAG also
shows seed nodes, retrieved relations, and ranked candidate papers. Architecture
explains the two paths; Dataset shows all 12 metadata records.
File watching is disabled in `.streamlit/config.toml` because Streamlit's module
scanner triggers irrelevant optional Transformers imports. Restart Streamlit
after code changes.

## Tests

```powershell
python -m pytest -q
```

Tests require built local artifacts and the cached embedding model, but make no
Groq calls. The suite checks chunking, real-corpus retrieval, traversal bounds,
ranking, context budgets, candidate-only supporting text, and generation errors.

## Demo

Start with these queries and expand their evidence:

| Mode | Question | Evidence to inspect |
| --- | --- | --- |
| Traditional RAG | How does G-Retriever select a compact subgraph? | P002 chunks |
| Traditional RAG | How does QAFD-RAG control graph retrieval? | P003 chunks |
| Basic GraphRAG | Which agentic retrieval approaches use self-reflection? | Agentic Retrieval seed, P011 candidate and text |
| Basic GraphRAG | Which fusion approaches combine text and graph information? | KAG P005 and MegaRAG P008 relations |

Additional rehearsal questions: “Which method uses late fusion?”, “How does
CRAG handle bad retrieval?”, “Which papers in Context Management use graph
retrieval?”, and “Which methods are related to graph retrieval and
agentic reasoning?”. Full observed results are in `documentation/demo_rehearsal.json`.
The late-fusion query retrieves MegaRAG among its evidence, but the selected
chunks did not establish late fusion in rehearsal; generation correctly reported
insufficient evidence. Prefer the four questions in the table for the live demo.

The configured Groq account imposed an 8,000-token-per-minute limit during
rehearsal. Space live queries about one minute apart. If rate-limited, evidence
stays visible; wait the duration in the error and click Run Query again. There
is no automatic retry or answer cache that conceals this limit.

Two-minute explanation:

- Traditional RAG embeds the question and compares it directly with PDF chunks.
  The top semantic chunks become the LLM's evidence.
- Basic GraphRAG matches the question to graph concepts, follows bounded explicit
  relationships, selects papers, and then retrieves PDF evidence within them.
- Both use the same embedding model, final LLM, and corpus. The retrieval
  representation is the primary difference.

## Troubleshooting and limits

- Missing/corrupt storage or mismatched vector dimensions: rerun
  `python scripts/build_all.py`.
- Missing metadata: restore `data/metadata.json` with the 12 paper mappings.
- Groq model errors: set `GROQ_MODEL` to a model available to your account.
- Graph relations are curated metadata, not automatically extracted claims.
  Traversal defaults to three seeds, two hops, and five candidate papers.
- Supporting text defaults to two chunks per graph-selected paper. The 24,000
  character context budget can omit later chunks; the UI marks which chunks
  actually entered the context. Graph formatting reserves at most one third
  of this budget for complete per-paper relation blocks.
- The final model may still misinterpret evidence. Inspect the exposed text and
  citations; the rehearsal is a demo check, not a scientific quality benchmark.
- `.gitignore` excludes `.env`, `.venv`, Python caches, and generated storage.
  Git initialization is optional and was not required for this local demo.
