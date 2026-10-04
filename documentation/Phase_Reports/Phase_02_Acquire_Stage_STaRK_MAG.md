# Phase 2 — Acquire and Stage STaRK MAG

PHASE: 2 — Acquire and Stage STaRK-MAG

STATUS: PASS — source staged and audited; upstream/schema findings recorded.

OBJECTIVE: Acquire immutable official source, document its actual content and verify structural completeness without building research views.

## Checkpoint before acquisition

Created non-destructive Phase 1 checkpoint commit **ea88dcfee5523f609b34fb597ae7a5884ed9899f** (`Checkpoint approved Phase 1 research scaffold and contracts`). `git status --porcelain` was empty afterward, before the first dataset download. No force reset, baseline rewrite or tag update occurred. `baseline-mvp-v1` still resolves to **4592d102b363c7d55d3c85ee67efe89409ae96b5**.

## 1. Exact acquisition method and source

Used the official MagSKB loader's download primitive, `huggingface_hub.hf_hub_download`, against the public repository [snap-stanford/stark](https://huggingface.co/datasets/snap-stanford/stark/tree/88269e23e90587f99476c5dd74e235a0877e69be). Pinned dataset revision: `88269e23e90587f99476c5dd74e235a0877e69be`. Inspected and saved official loader code at `b246b9490b1dc216892ce78303140014506932c1`.

Acquired `skb/mag/processed.zip`, both MAG schema JSON files, both MAG QA CSVs and all four official split index files. Extracted the six processed archive members unchanged. No raw OGB/MAG reconstruction was necessary because the official processed source already contains text, metadata and graph tensors. Public acquisition succeeded automatically without authentication, manual downloads or license-interaction steps. Upstream dataset card reports CC-BY-4.0; code license is MIT.

The full `load_skb`/MagSKB constructor was deliberately not invoked: it materializes metadata, may make the graph undirected, and constructs sparse adjacency. The download primitive is the same one the official constructor uses and does not perform those transformations.

## 2. Package and loader versions

- Project Python: 3.12.14 through `.\.venv\Scripts\python.exe`.
- huggingface-hub: 1.32.0 (acquisition).
- NumPy: 2.5.3 (chunked tensor audit).
- Existing PyTorch: 2.14.0; not imported by the full-source audit. Used only for a tiny serialization regression fixture.
- Requests: 2.34.2 (official source/package metadata inspection).
- `stark-qa`: official PyPI 1.1.0 metadata inspected, package not installed. Existing dependencies were sufficient; no packages were installed or upgraded.
- Audit parser: phase2-v1. Exact staging and audit script SHA-256 values are recorded in `raw_manifest.json`.

## 3. Download location and total size

`D:/codefiles/RAG_GraphRAG_Demo/data/MMG_STARK_MAG/raw/stark_mag/`

- 9 downloaded files: **486,879,729 bytes** (about 487 MB).
- 6 extracted official source files: **2,133,898,927 bytes**.
- Total staged source: **2,620,778,656 bytes** (about 2.62 GB), excluding manifest/cache metadata.
- Dedicated cache/pre-scan directory: `data/MMG_STARK_MAG/_build/`, about 488 MB.
- Combined source/cache disk use: about 3.11 GB.
- A new dataset-local `.gitignore` excludes large raw/cache files. Original repository `.gitignore` remains unchanged.

## 4. Checksums and manifest status

**Complete.** Raw manifest: `data/MMG_STARK_MAG/raw/stark_mag/raw_manifest.json`; identical review copy: `documentation/phase2/raw_manifest.json`.

All 15 source files have names, sizes, SHA-256 hashes, provenance and UTC acquisition timestamps. The processed ZIP matches the upstream LFS SHA-256 `7bfac742c1fb77694b3fab76be5088f9c3a636f47366188b70d3f378cfbd3053`. Small downloads match official Git blob IDs. Extracted bytes match archive members and CRCs. The complete audit reverified the manifest. Offline staging reruns reused the same files without downloads, preserving source bytes and original acquisition timestamps.

## 5. Actual entity types and counts

| Entity | Count |
| --- | ---: |
| Author | 1,104,554 |
| Institution | 8,701 |
| Field of study | 59,469 |
| Paper | 700,244 |
| **Total** | **1,872,968** |

All metadata records were streamed and checked against node type tensors and global node IDs. `mag_id`, source-local `id`, global `new_id` and `type` are present throughout. Exact contiguous global ID ranges are recorded in `documentation/phase2/node_id_ranges.json`.

## 6. Actual relation types and counts

| Expected relation | Actual source representation | Count |
| --- | --- | ---: |
| AUTHOR-WRITES-PAPER | `author___writes___paper` | 6,768,883 |
| AUTHOR-AFFILIATED_WITH-INSTITUTION | `author___affiliated_with___institution` | 1,029,162 |
| PAPER-CITES-PAPER | `paper___cites___paper` | 4,878,384 |
| PAPER-HAS_TOPIC-FIELD_OF_STUDY | `paper___has_topic___field_of_study` | 7,243,269 |
| **Total** | Stored directed edges | **19,919,698** |

All expected families are present. Every endpoint is within node bounds and every relation has its expected endpoint types. No self-loops were found. No reverse edges, deduplication or adjacency structures were created. Duplicate-edge detection was not performed; these are stored-edge counts.

## 7. Actual paper text and structured attributes

Paper records contain **35 fields**, fully listed with coverage and types in `documentation/Dataset_Manifest.md` and the machine-readable audit.

| Planned information | Stored field(s) | Nonmissing papers |
| --- | --- | ---: |
| Title | `title` | 700,244 |
| Abstract | `abstract` | 700,244 |
| Publication year | `Year` | 678,195 |
| Publication date | `Date` | 678,195 |
| Citation count | `PaperCitationCount` | 678,195 |
| Paper rank | `PaperRank` | 678,195 |
| Original venue name | `OriginalVenue` | 677,800 |
| Journal ID/name | `JournalId`, `JournalDisplayName` | 677,353 |
| Conference series ID/name | `ConferenceSeriesId`, `ConferenceSeriesDisplayName` | 146 |
| Conference instance ID/name | `ConferenceInstanceId`, `ConferenceInstancesDisplayName` | 71 |
| Document type (not a unified venue type) | `DocType` | 677,504 |

The four planned date/year/citation/rank fields are **available but incomplete**: 22,049 paper records have missing/sentinel values in each. No values were inferred, filled, recomputed or derived. Date/year pairs have zero disagreements when both are nonmissing. Missingness is classified as None/NaN/empty string/numeric -1/string '-1'; this does not certify every nonmissing value's scientific correctness.

Other paper fields include reference and estimated citation counts, original title, publisher, journal/conference metadata and joined conference columns. Non-paper entities have names, IDs, rank/count attributes, plus author affiliation and field hierarchy-level attributes.

## 8. Official query and split availability

- Synthetic QA CSV: **13,323** questions, **37,044** answer references; all answers reference paper nodes.
- Train: **7,993**; validation (`val`): **2,665**; test: **2,665**. IDs are unique, splits are disjoint, and their union covers the synthetic CSV exactly.
- `test-0.1`: **266** IDs, verified as a test subset.
- Human-generated evaluation CSV: **84** questions and **274** answer references. There is no separate human index file.
- Both CSVs contain exactly `id`, `query`, `answer_ids`. The official index files contain query IDs, not positional row indices.
- No benchmark files were created, relabeled or split by this project.

## 9. Discrepancies from the planned MMG STaRK MAG schema

1. **Venue normalization is not pre-supplied.** There are multiple venue identifiers/names and no single `venue_id`, `venue_name` or `venue_type` field. Phase 3 must explicitly document namespaces, precedence and any type mapping. `DocType` must not silently be treated as an already-defined venue taxonomy.
2. **Missing structured attributes and entity names.** Publication fields, citation count and rank are incomplete. Names are missing/sentinel for 140,792 authors, 16 institutions and 17,458 fields. These require explicit null/label/alias handling later.
3. **Joined field representations.** `ConferenceSeriesId` and `ConferenceSeriesId.1` are floats; other IDs are integers. There is no prebuilt canonical registry or title-plus-abstract `content` column. Original source keys/values remain intact.
4. **Human QA is not uniformly paper-set QA.** Human query 30 explicitly asks for an author and answers with author node 832321. Query 50 asks for a paper but includes author node 15775 alongside paper 1174913. Query 72 asks for a paper but answers with author node 98059. All IDs are in range. Preserve these records and decide their benchmark treatment explicitly later; query 30 is a scope mismatch, not automatically a bad label.
5. **Tensor backing storage differs from logical shape.** The edge-type file includes three rows of backing storage; its logical vector begins at element offset 39,839,396. Readers must honor serialized offsets/strides. Correct logical counts have been verified.

## 10. Resource observations

Initial free disk: about 339.7 GB; afterward about 336.6 GB. Initial free physical RAM was only about 0.8 GB on a machine with approximately 16.9 GB total physical memory.

The completed audit peaked at **84,443,136 bytes** (about **81 MiB**) working set and took **46.46 seconds** with the metadata opcode scan cached. Initial streaming opcode scan took about 84 seconds. Edge chunks contain 100,000 entries; the node-type array is about 15 MB. Only 88,982 referenced pickle memo entries were retained, avoiding a huge node dictionary. No full Python graph, NetworkX graph, torch SKB, CSR adjacency or research database was loaded or created.

Windows symlink support was unavailable for the download cache; Hugging Face's copy-based fallback worked, with disk overhead measured above. No user intervention was needed.

## 11. Tests and audits performed

- **51 tests passed in 1.18 seconds:** 18 frozen MVP tests, 21 Phase 1 cases and 12 new source-reader cases.
- New tests cover batched/shared pickle memo decoding, rejection of executable pickle globals, logical tensor storage offsets/strides/bounds, and missing-value classification.
- Complete source checksum verification and archive-member equivalence.
- All node metadata IDs/types, all stored edge endpoint types/ranges, node/relation counts and logical tensor dimensions audited.
- Every actual metadata key/type and missing/sentinel count inspected across the full metadata source.
- Synthetic QA paper references, human answer types and all official split invariants checked using safe literal parsing.
- Initial audit rejected non-paper human answers. Investigation distinguished source scope/label discrepancies; the final audit preserves and reports them as `pass_with_findings` rather than altering data or hiding the issue.
- Offline repeat acquisition completed without downloads.
- `pip check`: no broken requirements.
- Streamlit AppTest: Demo/Architecture/Dataset load; no error or exception elements.
- Baseline protection: 54 frozen tracked files and four original storage files match the immutable baseline. Phase 1 checkpoint and baseline commit IDs verified; no Phase 3 view directories exist.

## 12. Known issues

The source and schema findings in section 9 remain deliberately unresolved. No acquisition/access/hardware blocker remains. The audit does not establish semantic correctness of every label, deduplicate the graph, validate every publication-date string as a calendar date, or evaluate retrieval quality. Those claims are not required for source staging and are not made here.

No package installation occurred. No secrets were requested or transmitted, and acquisition used unauthenticated public download requests. No model calls occurred in Phase 2. Audit/source scripts and manifests are available for review; Phase 2 changes remain uncommitted pending phase review.

## 13. Phase 3 readiness

**Ready for approved Phase 3 construction of faithful source-linked views.** Necessary source tensors, metadata, titles/abstracts, structured attributes, canonical source IDs and all four relations are available and checksummed. Phase 3 must explicitly address venue normalization, missing labels/attributes and tensor layout details. Human-QA scope/label handling must be resolved before its use in the Phase 4 paper-set benchmark; the originals must remain preserved.

No Text/Graph/Structured research view, FAISS, CSR adjacency, DuckDB, derived benchmark, graph inverse edges or advanced algorithm has been built. Base config dataset version remains `unbuilt` until research views actually exist.

## Files created or modified

- `scripts/stage_stark_mag.py` and `scripts/audit_stark_mag.py`.
- `tests/test_stark_source_audit.py`.
- `data/MMG_STARK_MAG/.gitignore`; local ignored raw/cache directories.
- `documentation/Dataset_Manifest.md`.
- `documentation/phase2/`: raw manifest copy, full audit, node ranges, tests/UI/preservation/resource checks, pinned official loader/code/package/source metadata and final file checksums.
- `documentation/Research_Decision_Log.md`: appended P2-01 through P2-10.
- This Phase 2 review report.

## Commands run

All Python used `.\.venv\Scripts\python.exe`.

- `git add <explicit Phase 1 paths>`; `git diff --cached --check`; `git commit -m 'Checkpoint approved Phase 1 research scaffold and contracts'`; `git status --porcelain`; verify HEAD and baseline tag. All Git operations after sandbox initialization used command-scoped `-c safe.directory=D:/codefiles/RAG_GraphRAG_Demo`.
- Read-only official GitHub/Hugging Face/PyPI metadata requests, then pinned official source downloads.
- `python scripts/stage_stark_mag.py` with `HF_HUB_DISABLE_XET=1`: HTTP/resumable official acquisition, checksum verification, extraction and manifest generation.
- Streaming pickle opcode pre-scan and bounded tensor-header inspection.
- `python scripts/audit_stark_mag.py`: initial run found human-QA type discrepancies; final complete run records findings and all measured counts.
- `python -m pytest -q -p no:cacheprovider`: 51 pass.
- `python -m pip check`: pass.
- `python scripts/stage_stark_mag.py` with `HF_HUB_OFFLINE=1`: repeated integrity/resume check; final manifest includes parser/script hashes.
- Inline Streamlit AppTest, Git/blob/ZIP preservation comparisons, node-range checks, final secret scan and report checksum generation.

## Artifact counts and scientific invariants

9 downloads + 6 extracted members; 1 complete raw manifest with review copy; 1 full-source audit; 2 acquisition/audit scripts; 12 new tests; 10 decisions. Exact entity/edge/query counts are above.

Frozen MVP behavior/parameters/prompts/artifacts/tag preserved. Source immutable. No imputed fields, changed official questions, repaired answers, test tuning, algorithm implementation or scientific result claims. No downstream work started on the known QA discrepancy.

REVIEW QUESTIONS FOR USER: No immediate access action needed. Review the documented venue/missing-data and human-QA findings before subsequent construction/benchmark decisions.

NEXT PHASE (NOT STARTED): Phase 3 — Build MMG-STaRK-MAG v1 Representations.

STOP: Await explicit user approval; Phase 3 has not begun.
