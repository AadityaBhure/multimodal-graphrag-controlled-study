# MMG-STaRK-MAG v1 physical representation contract

This contract implements the approved Phase 3 rules. Source truth is the official processed snapshot at Hugging Face revision `88269e23e90587f99476c5dd74e235a0877e69be`, audited in Phase 2. Data is local and ignored under `data/MMG_STARK_MAG/`; review metadata and scripts are tracked.

## Identity and field definitions

All physical cross-view join keys are signed 64-bit STaRK global node IDs. Paper IDs span 1,172,724–1,872,967. `canonical_id="stark:" + decimal(global_id)` is an additional stable string key, not a replacement MAG ID. `source_id` in the canonical registry is the original type-local source ID. In graph edges, `source_id` means the global ID of the edge's source endpoint. MAG IDs remain provenance only.

| Artifact | Fields and meanings |
| --- | --- |
| `canonical/canonical_entities.parquet` | `canonical_id`, authoritative `stark_node_id`, type-local `source_id`, `mag_id`, source `entity_type`, nullable `display_name` (paper title for papers). |
| `canonical/alias_registry.parquet` | NFKC/casefold/whitespace-normalized exact `alias`, `canonical_id`, `stark_node_id`, `entity_type`. NULL/empty labels produce no alias. Ambiguous aliases retain every entity association. No fuzzy or embedding resolver is built. |
| `text/text_documents.parquet` | Exactly `paper_id`, source `title`, source `abstract`, and `content=title+"\n\n"+abstract`. One full source paper per document. No stripping, chunking, metadata enrichment or graph expansion. |
| `graph/nodes.parquet` | `node_id`, `canonical_id`, `node_type`, nullable `label` and identical `search_text`. Paper label is title only; other labels are source DisplayName. Missing labels do not delete nodes. |
| `graph/edges.parquet` | Unique `edge_id`, original tensor-column `source_edge_id`, global `source_id`/`target_id`, official `relation`, numeric `relation_id`, boolean `derived_inverse`. Original edge ID equals source tensor column; inverse ID equals 19,919,698 plus that column. Inverse rows swap endpoints and retain the official relation name/code with `derived_inverse=true`; consumers must inspect this flag to interpret direction. |
| `graph/identity_mapping.json` | The already contiguous global node IDs are CSR row indices; no duplicate remapping table is needed. |
| `graph/adjacency/*.npy` | `indptr:uint64[N+1]`, `neighbors:uint32[2E]`, `edge_ids:int64[2E]`, `relation_ids:uint8[2E]`, `derived_inverse:bool[2E]`. Order is source ID, inverse flag, target ID, edge ID. Read with `np.load(..., mmap_mode="r", allow_pickle=False)`; neighbors of node u occupy `[indptr[u]:indptr[u+1]]`. |
| `structured/stark_mag.duckdb` | `papers_structured`: global `paper_id`; nullable DATE `publication_date`, INTEGER `publication_year`, BIGINT `citation_count`/`paper_rank`; nullable strings `document_type`, `venue_namespace`, `venue_id`, `venue_name`, `venue_type`. `papers_structured_source`: paper ID and JSON of original structured audit columns only. |
| `text/faiss/*` | Exact `IndexFlatIP`, 384-dimensional float32 unit vectors; score is cosine similarity. `row_to_paper_id.npy:int64` translates FAISS row ordinals to global paper IDs. Durable 4,096-paper vector/ID shards retain the same mapping. `model.onnx` and `encoder.json` preserve export/weight identities and backend parity evidence. |
| `manifest.json` | Version, configuration/hash, package and implementation versions/checksums, full artifact sizes/SHA-256, schemas, counts, source/inverse distinction, timing/resource observations and exhaustive audit results. |

Numeric relation codes remain official: 0=`author___affiliated_with___institution`, 1=`paper___cites___paper`, 2=`paper___has_topic___field_of_study`, 3=`author___writes___paper`. No additional semantic relations are introduced; inverse rows are traversal aids only. All stored duplicates, if any, remain source records; no deduplication claim is made.

## Structured normalization

Source `None`, numeric/string `-1`, empty string and floating NaN are missing sentinels and normalize to NULL. Zero is preserved. Date strings are parsed as dates; year is never obtained from the date, citation count is never recomputed from edges, and rank is never recalculated. Actual source dates all parsed successfully. No names are fabricated.

Venue selection takes the first pair with either its identifier or display name present:

1. JournalId / JournalDisplayName → `journal`.
2. ConferenceSeriesId / ConferenceSeriesDisplayName → `conference_series`.
3. ConferenceInstanceId / ConferenceInstancesDisplayName → `conference_instance`.
4. OriginalVenue → `original_venue`, with NULL ID and NULL type because this source does not specify a venue category.
5. Otherwise all venue fields are NULL.

Within a selected pair, a missing component stays NULL; lower-precedence fields do not fill it. Namespace disambiguates numeric IDs. `document_type` retains DocType separately, never as the venue taxonomy.

The audit JSON preserves Date, Year, PaperCitationCount, PaperRank, DocType, JournalId, JournalDisplayName, ConferenceSeriesId, ConferenceSeriesDisplayName, ConferenceInstanceId, ConferenceInstancesDisplayName, OriginalVenue, and ConferenceSeriesId.1. Nonfinite floats use reversible `{"nonfinite_float":"nan"}` encoding. The official immutable pickle remains the byte-authoritative source. No title, abstract, author, institution, topic or graph edge is added to these SQL tables.

## Embedding backend and limitations

The model remains `sentence-transformers/all-MiniLM-L6-v2`, with its existing 256-token limit, attention-mask mean pooling and L2 normalization. The research build exports the cached frozen weights to ONNX and uses CUDA float32 with TF32 disabled. It does not replace the MVP's CPU PyTorch installation or change MVP behavior. ONNX/PyTorch parity checks use 30 actual papers spanning the source plus short, Unicode and over-length examples; tolerances and measured errors are in `encoder.json`.

Text Parquet retains the entire source title/abstract even when the embedding model truncates its token input. One document remains one vector; no claim of whole-abstract token coverage or retrieval-quality evaluation is made. Float32 backend results meet the recorded tolerance; bitwise identity across hardware is not promised.

## Restart and verification

Use the existing project interpreter from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/build_mmg_stark_mag.py --stage nodes
.\.venv\Scripts\python.exe scripts/build_mmg_stark_mag.py --stage structured
.\.venv\Scripts\python.exe scripts/build_mmg_stark_mag.py --stage edges
.\.venv\Scripts\python.exe scripts/build_mmg_stark_mag.py --stage csr
.\.venv\Scripts\python.exe scripts/build_mmg_stark_mag.py --stage embeddings
.\.venv\Scripts\python.exe scripts/build_mmg_stark_mag.py --stage faiss
.\.venv\Scripts\python.exe scripts/validate_dataset.py
.\.venv\Scripts\python.exe scripts/build_mmg_stark_mag.py --stage manifest
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe scripts/check_phase3_preservation.py
```

Run large stages sequentially. Individual audits accept `--section nodes|sql|edges|csr|faiss` to release memory between processes. Builds use a pinned configuration/source lock, atomic file replacement, checksummed shard markers and checksummed completed-stage markers. Completed stages verify and reuse exact outputs. Incomplete node/edge/embedding shards resume; incomplete CSR/temporary DuckDB/FAISS work is rebuilt safely. Corrupt completed artifacts fail explicitly rather than silently mixing versions. A changed source/configuration requires a fresh versioned build directory. Preserve the implementation fingerprint in the manifest when reproducing this version.

DuckDB external sorting is bounded to 512 MB and two threads; CSR arrays are memory-mapped. FAISS's exact flat index necessarily materializes about 1.075 GB in memory, allocated once to avoid doubling it during growth. No full graph is instantiated in NetworkX or a Python graph container.

Phase 1 generic evidence contracts remain available for later method adapters; the physical schemas above are the authoritative Phase 3 storage contract. The Phase 1 synthetic text fixture was updated to the approved exact two-newline rule, superseding its earlier stripped/missing-abstract formatting rule.

## Information isolation and stop gate

Audits compare every source record to its allowed physical projection, exact text content and nullable structured values; compare every original/inverse edge against its tensor; compare every CSR entry; verify complete identity joins, SQL predicates, FAISS vector bytes and ID mapping. Naturally occurring words inside source titles/abstracts are not removed; isolation means no additional fields are injected.

The registry is a provenance/linking artifact. Text retrieval uses its own four-column representation; graph semantics use only graph labels; SQL uses only structured columns and structured audit JSON. Benchmark construction and research retrieval algorithms remain later phases.

All original 84 human QA records stay unchanged. In Phase 4, the primary paper-set `human_test` must exclude whole mixed/non-paper-answer queries, including known queries 30, 50 and 72, without repairing their answers. No derived benchmark, filtering or query generation occurs in Phase 3.
