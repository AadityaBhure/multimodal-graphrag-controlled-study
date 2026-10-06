"""Render the Phase 3 review from measured manifests; no dataset mutation."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.data.build import write_json
from scripts.audit_stark_mag import digest


def main():
    evidence = ROOT / "documentation/phase3"
    manifest = json.loads((evidence / "representation_manifest.json").read_text())
    preservation = json.loads((evidence / "preservation_environment.json").read_text())
    idempotence = json.loads((evidence / "idempotence.json").read_text())
    assert manifest["status"] == "validated" and idempotence["status"] == "pass"
    assert "68 passed" in (evidence / "pytest.txt").read_text()
    audits = {k: v["result"] for k, v in manifest["audits"].items()}
    stages = manifest["build_stages"]
    nodes, sql, edges, csr = (audits[k] for k in ("nodes", "sql", "edges", "csr"))
    encoder = stages["embeddings"]["encoder"]
    files = manifest["files"]
    sizes = {f["path"]: f["bytes"] for f in files}
    vector_files = [f for f in files if "/embeddings/vectors-" in f["path"]]
    id_files = [f for f in files if "/embeddings/ids-" in f["path"]]
    resource_table = "\n".join(f"| {k} | {v['elapsed_seconds']:.2f} | {v['resources']['peak_working_set_bytes']:,} |" for k, v in stages.items())
    audit_table = "\n".join(f"| {k} | PASS | {v['elapsed_seconds']:.2f} | {v['resources']['peak_working_set_bytes']:,} |" for k, v in manifest["audits"].items())
    entity_table = "\n".join(f"| {k} | {v:,} | {nodes['missing_values'].get(k, 0):,} |" for k, v in nodes["entity_counts"].items())
    relation_table = "\n".join(f"| `{k}` | {v:,} | {edges['derived_inverse'][k]:,} |" for k, v in edges["official"].items())
    artifact_rows = [
        ("Canonical entities", "1,872,968 rows", sizes["canonical/canonical_entities.parquet"]),
        ("Exact alias registry", "1,714,702 rows", sizes["canonical/alias_registry.parquet"]),
        ("Text documents", "700,244 rows / 4 columns", sizes["text/text_documents.parquet"]),
        ("Graph nodes", "1,872,968 rows", sizes["graph/nodes.parquet"]),
        ("Graph edges", "19,919,698 source + 19,919,698 derived rows", sizes["graph/edges.parquet"]),
        ("Identity mapping metadata", "1 file", sizes["graph/identity_mapping.json"]),
        ("CSR arrays", "5 files; 1,872,968 node rows / 39,839,396 traversal entries", sum(v for k,v in sizes.items() if k.startswith("graph/adjacency/"))),
        ("DuckDB", "700,244 rows in each of two tables", sizes["structured/stark_mag.duckdb"]),
        ("Embedding vectors", f"{len(vector_files)} shards; 700,244 × 384 float32", sum(f["bytes"] for f in vector_files)),
        ("Embedding shard IDs", f"{len(id_files)} shards; 700,244 global IDs", sum(f["bytes"] for f in id_files)),
        ("ONNX model", "1 frozen-weight export", sizes["text/faiss/model.onnx"]),
        ("Encoder provenance", "1 JSON file", sizes["text/faiss/encoder.json"]),
        ("FAISS IndexFlatIP", "700,244 vectors, dimension 384", sizes["text/faiss/index.faiss"]),
        ("FAISS row mapping", "700,244 int64 global IDs", sizes["text/faiss/row_to_paper_id.npy"])]
    artifact_table = "\n".join(f"| {name} | {count} | {size:,} |" for name, count, size in artifact_rows)
    sample = nodes["samples"]["paper"]
    sample_summary = {"canonical": sample["canonical"], "text_columns": list(sample["text"]),
                      "title": sample["text"]["title"], "abstract_excerpt_for_review_only": sample["text"]["abstract"][:220],
                      "content_rule": "Exact title + two newlines + full source abstract; excerpt is report-only",
                      "graph": sample["graph"], "structured": {k:v for k,v in sample["structured"].items() if k != "raw_source_json"}}
    report = f"""# Phase Review Report

PHASE: 3 — Build MMG-STaRK-MAG v1 Representations

STATUS: **PASS**

OBJECTIVE: Build complete, isolated Text/Graph/Structured representations linked through authoritative STaRK global node IDs, preserving the approved source and showcase baseline.

## Checkpoint and protected state

Approved Phase 2 was committed before implementation as `f8fc9a29f95b008a0216620449568f8bba4599a6`, with the working tree confirmed clean immediately afterward. The immutable `baseline-mvp-v1` still resolves to `4592d102b363c7d55d3c85ee67efe89409ae96b5`.

All {preservation['protected_baseline_files_verified']} protected baseline Git objects, {preservation['baseline_inventory_byte_checks']} original inventory byte hashes and {preservation['storage_files_verified']} original storage files pass preservation checks. All {preservation['baseline_package_versions_preserved']} package pins remain unchanged; pip check passes. The unchanged Streamlit app renders “RAG Retrieval Lab” without exceptions. New Phase 3 code/documentation remains available for review; no Phase 3 checkpoint commit was requested yet.

All 15 official downloaded/extracted source files retain their Phase 2 SHA-256. The raw manifest matches its Phase 2 review copy. Original 84 human QA records and official split files remain unchanged. Data remains ignored by Git.

## Exact output counts and sizes

Location: `D:/codefiles/RAG_GraphRAG_Demo/data/MMG_STARK_MAG/`.

| Artifact | Count | Bytes |
| --- | --- | ---: |
{artifact_table}
| **Total physical outputs** | **{len(files)} files, excluding the manifest itself and build cache** | **{manifest['output_bytes']:,}** |

The complete per-file list and SHA-256 checksums are in [representation_manifest.json](../phase3/representation_manifest.json), byte-identical to the dataset-root `manifest.json`. The manifest itself is checksummed by the documentation file manifest. Source files total 2,620,778,656 bytes, separate from these derived outputs. Retained staging/checkpoint/cache bytes: {preservation['build_cache_bytes']:,}; final free disk: {preservation['disk_free_bytes']:,} bytes. These caches remain intentionally available for recovery.

| Entity type | Nodes | NULL semantic labels |
| --- | ---: | ---: |
{entity_table}

Alias registry: {sql['distinct_aliases']:,} distinct normalized aliases; {sql['ambiguous_aliases_preserved']:,} ambiguous alias strings retain their entity associations. No invented labels or fuzzy mappings.

| Official relation representation | Official directed rows | Derived inverse rows |
| --- | ---: | ---: |
{relation_table}
| **Total** | **19,919,698** | **19,919,698** |

The source edge count is always **19,919,698**. The combined **39,839,396** counts traversal entries only. Inverse rows have swapped endpoints, retained relation name/code and explicit `derived_inverse=true`; `source_edge_id` links them back to the official tensor column.

## Structured values and normalization

Date, year, citation count and paper rank each retain **22,049 NULLs**, with 678,195 present values. Document type has 22,740 NULLs. No missing value is recomputed, inferred or zero-filled. All present dates parsed successfully; dates and years are preserved independently.

Venue precedence yields **677,353 journal**, **146 conference_series**, **0 conference_instance**, **301 original_venue** and **22,444 NULL** records. The 71 present conference-instance source records all select higher-precedence venues. Raw conference-instance fields remain available in the audit JSON. Missing members of a selected ID/name pair remain NULL; no lower-precedence fallback fills them. Original-only venues have NULL ID and type. DocType is stored separately as document_type.

The SQL audit table retains original structured source columns and sentinels, including ConferenceSeriesId.1. The immutable original pickle remains the byte-authoritative source. No paper title, abstract, author, affiliation, topic or graph relation is introduced as a structured query field.

## Validation / tests and leakage audit

**68 tests passed**, including 17 Phase 3 cases: exact whitespace/content isolation, NULL labels, zero preservation, venue precedence, alias collisions, ID mismatch rejection, synthetic CSR traversal, incomplete-CSR recovery, completed-artifact corruption rejection, exact FAISS equivalence/serialization and intentional embedding interruption/resume.

| Exhaustive audit | Status | Seconds | Process peak working set, bytes |
| --- | --- | ---: | ---: |
{audit_table}

- Every canonical/node/text/structured record was compared to its permitted raw-source projection; all 700,244 papers join across the three views. Identity keys are unique/non-NULL. Text physical schema has exactly four approved columns, with exact source title + two newlines + abstract.
- Graph paper semantic fields equal source title only; other labels equal actual DisplayName or NULL. All 1,872,968 nodes remain structurally represented. Every original/inverse edge was checked against its source tensor, including column uniqueness/coverage, relation code/name, endpoints and inverse flag.
- All 39,839,396 CSR entries match the sorted edge view, with monotonic offsets, valid dimensions and deterministic ordering. No node has zero degree in the stored traversal view. Known real traversal: paper 1172724 → author 36641 → papers 1172724 and 1475765. NULL-name author 9899 remains connected to paper 1451406.
- DuckDB matches the audited source projection in both directions with **zero mismatches**. NULL/date/year/citation/rank and venue predicates agree with the source-derived staging records. `publication_year >= 2000 AND citation_count >= 100` returns **8,316** canonical paper IDs; SQL NULL predicates each return **22,049** for the primary four fields.
- All 700,244 stored FAISS vectors reconstruct exactly from persisted shards; every index row maps to the expected global paper ID. All vectors are finite and L2-normalized. Nine deterministic vector queries return valid paper IDs and top scores approximately one. This verifies index integrity, not benchmark retrieval quality.
- Completed build stages were rerun and reused without changes to any physical output; manifest regeneration is byte-identical. Partial-shard recovery is tested, and corrupted completed outputs fail explicitly.

Information isolation passes at physical-schema and full source-value levels. Naturally occurring names/dates in a source title/abstract are preserved; no additional metadata is injected. The canonical registry is for identity/provenance, not an extra retrieval feature source. Research retrievers and benchmark evaluation are not implemented in this phase.

## Embeddings, packages and measured build resources

Interpreter: Python {manifest['python_version']} at `.\\.venv\\Scripts\\python.exe`.

Model: `{encoder['model']}`, pinned revision `{encoder['model_revision']}`. The frozen source-weight SHA-256 is `{encoder['source_weights_sha256']}`. The ONNX export, model metadata and all vectors are checksummed.

Research-only encoding uses ONNX Runtime CUDA float32, TF32 disabled, attention-mask mean pooling and L2 normalization. Model max length stays 256 tokens; full text stays in Parquet. Batch size was 64 throughout; {len(vector_files)} durable shards hold all papers. No quantization, approximate index, model substitution or MVP torch replacement occurred.

On 33 parity cases (30 actual papers plus short/Unicode/over-length text), maximum absolute ONNX/PyTorch error was **{encoder['parity_max_abs_error']:.12g}**, minimum cosine **{encoder['parity_min_cosine']:.12g}**. Both satisfy the recorded tolerances.

Core versions: {', '.join(f'{k} {v}' for k,v in manifest['packages'].items())}. Exact environment and additive CUDA runtime dependencies are recorded in [requirements.freeze.txt](../phase3/requirements.freeze.txt) and [preservation_environment.json](../phase3/preservation_environment.json). Pip itself is absent from the original freeze by pip's default behavior and is not claimed as a new dependency.

| Build stage | Elapsed seconds | Process peak working set, bytes |
| --- | ---: | ---: |
{resource_table}

Timings are measured per-stage, including local checks/writes; they are not end-to-end installation wall time. Working-set values are process lifetime peaks and can include memory-mapped pages. DuckDB used a 512 MB internal limit and two threads; CSR was memory-mapped. FAISS preallocates the exact flat vector storage once (~1.075 GB). No full graph was loaded into NetworkX or another in-memory Python graph.

The RTX 4060 Laptop GPU has 8,188 MiB reported memory. A build-time device sample is preserved in [gpu_sample.txt](../phase3/gpu_sample.txt); it is an observation, not a measured process peak. No paid generation/API call or cloud GPU was used. App smoke rendering made ordinary Hugging Face model-metadata requests through the unchanged MVP loader.

## Representation samples

```json
{json.dumps(sample_summary, indent=2, ensure_ascii=False)}
```

Missing-value example: paper **1172733** retains NULL date/year/citation/rank/document_type/venue fields. NULL-name example: author **9899** has NULL label/search_text and a valid CSR edge. Full samples, including exact unabridged source abstract and raw audit JSON, are preserved in the manifest. The prose excerpt above is only for review, never the stored document.

## Discrepancies and known issues

1. Earlier assumed source statistics are superseded by the Phase 2 audited counts above. Inverse traversal rows do not alter the official edge count.
2. Venue normalization is a documented transformation, not a pre-existing MAG taxonomy. Original-only venue type remains NULL. All 71 conference-instance values are lower-priority under the approved policy.
3. Missing names and structured values remain actual source limitations. Ambiguous aliases remain ambiguous. No semantic correctness or source deduplication claim is made.
4. The frozen model truncates embedding input at 256 tokens; full abstracts remain available as documents. GPU/CPU float32 outputs satisfy parity tolerances; bitwise cross-hardware reproducibility is not claimed.
5. Exact FAISS loading requires approximately 1.075 GB of vector memory plus runtime overhead. Raw source, recovery shards and final artifacts intentionally occupy separate disk space.
6. One non-failing DuckDB API deprecation warning remains for `fetch_record_batch`; current pinned-version tests and full audits pass. No acceptance blocker remains.
7. Original human QA queries 30, 50 and 72 contain non-paper/mixed answers. They remain unchanged. Phase 4 must exclude whole incompatible queries from primary paper-set human_test, never repair them. No benchmark is constructed here.

## Files created/modified and commands run

- Added `configs/phase3.yaml`, `requirements-phase3.txt`, `research/data/{{representations,build,embeddings,validation}}.py`, builder/validator/preservation/report scripts, and `tests/test_phase3_representations.py`.
- Extended research-only config and nullable contracts; updated the synthetic research text fixture to the approved exact separator rule.
- Added `documentation/phase3/` measured manifests/tests/environment/UI/idempotence evidence and physical contract; appended Dataset_Manifest and Research_Decision_Log; added this review report.
- Created ignored physical artifacts under `data/MMG_STARK_MAG/`; original raw bytes and MVP artifacts remain unchanged.

Commands used the project interpreter. Dependencies were installed with the Phase 0 freeze as pip constraints. Builder stages ran in order: nodes, structured, edges, csr, embeddings, faiss. Validator sections nodes/sql/edges/csr/faiss performed the full audits. Manifest generation and completed-stage reruns verified idempotence. `python -m pytest -q -p no:cacheprovider`, `python -m pip check`, the preservation script and Streamlit AppTest passed. Git trust overrides were scoped per command.

The full schema and exact runnable commands are in [Representation_Contract.md](../phase3/Representation_Contract.md). The documentation file manifest lists the final review/code checksums.

DECISIONS LOGGED: P3-01 through P3-13 in [Research_Decision_Log.md](../Research_Decision_Log.md).

SCIENTIFIC INVARIANTS CHECKED: frozen baseline behavior/parameters/prompts/tag/artifacts; same model weights and token limit; official directed edge count; separate inverse tagging; stable global identity; exact text isolation; title-only paper graph semantics; structured-only SQL; NULL preservation; unchanged original QA/splits; no benchmark or later algorithms.

REVIEW QUESTIONS FOR USER: No unresolved technical decision or manual action is required. This completed Phase 3 awaits your approval.

NEXT PHASE (NOT STARTED): **Phase 4 — Benchmark Construction Protocol**. The faithful views, complete indexes and isolation audits are ready. Preserve all 84 original human records and apply whole-query paper-set compatibility exclusions only during the approved Phase 4 work.

**STOP: Phase 3 complete. Phase 4 has not begun.**
"""
    target = ROOT / "documentation/Phase_Reports/Phase_03_Build_MMG_STaRK_MAG.md"
    target.write_text(report, encoding="utf-8")
    tracked = [*evidence.glob("*"), target, ROOT / "documentation/Research_Decision_Log.md",
               ROOT / "documentation/Dataset_Manifest.md", * (ROOT / "research/data").glob("*.py"),
               ROOT / "research/common/config.py", ROOT / "research/common/contracts.py", ROOT / "configs/phase3.yaml",
               ROOT / "requirements-phase3.txt", ROOT / "tests/test_phase3_representations.py",
               ROOT / "tests/fixtures/research/corpus.json", ROOT / "scripts/build_mmg_stark_mag.py",
               ROOT / "scripts/validate_dataset.py", ROOT / "scripts/check_phase3_preservation.py",
               ROOT / "scripts/check_phase3_idempotence.py", Path(__file__).resolve()]
    records = [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)}
               for p in sorted(set(tracked)) if p.is_file() and p.name != "file_manifest.json"]
    write_json(evidence / "file_manifest.json", {"files": records})
    print(target)


if __name__ == "__main__":
    main()
