# STaRK MAG Source Dataset Manifest

Phase 2 stages official processed source; this is not the derived MMG-STaRK-MAG v1 dataset.

## Acquisition and provenance

The official [MagSKB loader](https://github.com/snap-stanford/stark/blob/b246b9490b1dc216892ce78303140014506932c1/stark_qa/skb/mag.py) calls `huggingface_hub.hf_hub_download` for `snap-stanford/stark`, file `skb/mag/processed.zip`. The acquisition script uses that same official download primitive, pinned to dataset revision `88269e23e90587f99476c5dd74e235a0877e69be`, and stages the schema and all `qa/mag/` files from the same revision. It does not instantiate `MagSKB`, whose constructor loads the whole metadata dictionary, potentially makes edges undirected and builds sparse adjacency. None of those transformations was run.

Source repository: [Stanford STaRK on Hugging Face](https://huggingface.co/datasets/snap-stanford/stark/tree/88269e23e90587f99476c5dd74e235a0877e69be). Official code revision: `b246b9490b1dc216892ce78303140014506932c1`. The saved dataset-card metadata labels the dataset CC-BY-4.0; the saved code LICENSE is MIT. The public repository was ungated and required no manual access, credentials or license-interaction step.

- Project interpreter: Windows CPython 3.12.14, `.venv/Scripts/python.exe`.
- Acquisition library: huggingface-hub 1.32.0.
- Audit library: NumPy 2.5.3, standard-library pickle/ZIP/CSV readers with restricted decoding.
- Existing environment also contains PyTorch 2.14.0 and Requests 2.34.2.
- Official `stark-qa` PyPI release inspected: 1.1.0; not installed or invoked. No dependency installation was necessary. Its graph-construction dependencies were unnecessary for source staging/audit.
- Parser version: `phase2-v1`; exact staging/audit script hashes are in the raw manifest.
- Location: `D:/codefiles/RAG_GraphRAG_Demo/data/MMG_STARK_MAG/raw/stark_mag/`.
- Downloaded files: 9, totaling **486,879,729 bytes**.
- Extracted archive members: 6, preserved byte-for-byte.
- Total staged source: **2,620,778,656 bytes** (about 2.62 GB; excludes the generated manifest and download cache).
- `raw_manifest.json` resides in the raw directory; an identical review copy is in `documentation/phase2/raw_manifest.json`.
- Each file has a SHA-256, size, provenance and UTC acquisition timestamp. LFS archive checksum matches upstream; small files match upstream Git blob IDs. Extracted bytes match their archive members, whose CRCs were also checked.

## Actual entity inventory

Counts are computed from stored tensors and cross-checked against every streamed node metadata record, not copied from published estimates.

| Entity type | Count |
| --- | ---: |
| author | 1,104,554 |
| institution | 8,701 |
| field_of_study | 59,469 |
| paper | 700,244 |
| **Total** | **1,872,968** |

Global node IDs are contiguous integers 0–1,872,967. In the stored source, authors occupy 0–1,104,553; institutions 1,104,554–1,113,254; fields of study 1,113,255–1,172,723; papers 1,172,724–1,872,967. `node_info.pkl` keys and `new_id` agree with tensor positions. Every record has `mag_id`, `id` (source type-local identifier), `new_id` and `type`. No new canonical IDs have been created.

## Actual relation inventory

| Stored relation name | Direction | Count |
| --- | --- | ---: |
| `author___affiliated_with___institution` | author → institution | 1,029,162 |
| `author___writes___paper` | author → paper | 6,768,883 |
| `paper___cites___paper` | paper → paper | 4,878,384 |
| `paper___has_topic___field_of_study` | paper → field_of_study | 7,243,269 |
| **Total** | | **19,919,698** |

All four expected relation families exist. The audit checked endpoint ranges and actual endpoint node types for every stored edge. These are stored directed edge counts; the audit did not add reverse edges or deduplicate relationships. There are no self-loops. Full duplicate-edge detection was not performed and is not implied by these counts.

`edge_index.pt` is logically int64 shape `[2, 19919698]`; `edge_types.pt` is int64 shape `[19919698]`; `node_types.pt` is int64 shape `[1872968]`. A crucial serialization detail: both edge tensor files contain 59,759,094 int64 storage elements (three rows), but the edge-type tensor is a **view starting at storage offset 39,839,396**. A reader must honor shape, strides and offset; it must not treat every stored integer as a relation. The custom chunk reader and regression test validate this behavior. Legacy tensor headers omit byte-order metadata; little-endian interpretation yields the validated node types, bounds and references. Source files remain untouched.

## Actual paper attributes

Every listed key occurs in all 700,244 paper records. Nonmissing counts below classify None, NaN, empty string, numeric -1 and string '-1' as missing; they are presence/sentinel audits, not a semantic correctness guarantee.

| Source field | Records containing key | Nonmissing values | Missing/sentinel values |
| --- | ---: | ---: | ---: |
| `id` | 700,244 | 700,244 | 0 |
| `mag_id` | 700,244 | 700,244 | 0 |
| `PaperRank` | 700,244 | 678,195 | 22,049 |
| `DocType` | 700,244 | 677,504 | 22,740 |
| `OriginalTitle` | 700,244 | 678,195 | 22,049 |
| `BookTitle` | 700,244 | 511 | 699,733 |
| `Year` | 700,244 | 678,195 | 22,049 |
| `Date` | 700,244 | 678,195 | 22,049 |
| `Publisher` | 700,244 | 651,330 | 48,914 |
| `JournalId` | 700,244 | 677,353 | 22,891 |
| `ConferenceSeriesId` | 700,244 | 146 | 700,098 |
| `ConferenceInstanceId` | 700,244 | 71 | 700,173 |
| `ReferenceCount` | 700,244 | 678,195 | 22,049 |
| `PaperCitationCount` | 700,244 | 678,195 | 22,049 |
| `EstimatedCitationCount` | 700,244 | 678,195 | 22,049 |
| `OriginalVenue` | 700,244 | 677,800 | 22,444 |
| `JournalRank` | 700,244 | 677,353 | 22,891 |
| `JournalDisplayName` | 700,244 | 677,353 | 22,891 |
| `JournalPaperCount` | 700,244 | 677,353 | 22,891 |
| `JournalCitationCount` | 700,244 | 677,353 | 22,891 |
| `ConferenceSeriesRank` | 700,244 | 146 | 700,098 |
| `ConferenceSeriesDisplayName` | 700,244 | 146 | 700,098 |
| `ConferenceSeriesPaperCount` | 700,244 | 146 | 700,098 |
| `ConferenceSeriesCitationCount` | 700,244 | 146 | 700,098 |
| `ConferenceInstancesDisplayName` | 700,244 | 71 | 700,173 |
| `ConferenceSeriesId.1` | 700,244 | 71 | 700,173 |
| `Location` | 700,244 | 71 | 700,173 |
| `StartDate` | 700,244 | 71 | 700,173 |
| `EndDate` | 700,244 | 71 | 700,173 |
| `ConferenceInstancesPaperCount` | 700,244 | 71 | 700,173 |
| `ConferenceInstanceCitationCount` | 700,244 | 71 | 700,173 |
| `type` | 700,244 | 700,244 | 0 |
| `new_id` | 700,244 | 700,244 | 0 |
| `title` | 700,244 | 700,244 | 0 |
| `abstract` | 700,244 | 700,244 | 0 |

### Mapping implications for the planned structured view

- `publication_date` has a direct source: `Date`; `publication_year` has `Year`. Both have 678,195 nonmissing values and 22,049 missing values. The stored date year agrees with stored `Year` in all nonmissing pairs. No year was derived from a date.
- `citation_count` has a direct source: `PaperCitationCount`, with 678,195 nonmissing values. `EstimatedCitationCount` and `ReferenceCount` are separate source fields and were not substituted.
- `paper_rank` has a direct source: `PaperRank`, with 678,195 nonmissing values. No rank was computed from citations.
- Venue information exists, but there is **no single source column named `venue_id`, `venue_name`, or `venue_type`**. Candidates include `OriginalVenue` (677,800 nonmissing), `JournalId`/`JournalDisplayName` (677,353), `ConferenceSeriesId`/`ConferenceSeriesDisplayName` (146), and `ConferenceInstanceId`/`ConferenceInstancesDisplayName` (71).
- `DocType` exists (677,504 nonmissing) but is a document-type attribute, not an already-defined unified venue taxonomy. Venue precedence, identifier namespaces and any derived venue type must be explicitly documented in Phase 3; none was silently selected here.
- `ConferenceSeriesId` and `ConferenceSeriesId.1` are serialized as floats. Future normalization must validate integer-valued IDs and preserve missingness; the `.1` column is a separate joined field, not a newly generated key.
- `title` and `abstract` both have 700,244 nonmissing string values. `OriginalTitle` is a separate metadata attribute with missing entries. There is no stored canonical `content` field; title-plus-abstract composition belongs to Phase 3.

### Non-paper attributes

Authors contain `id`, `mag_id`, `Rank`, `DisplayName`, `LastKnownAffiliationId`, `PaperCount`, `CitationCount`, `type`, `new_id`. Institutions contain the same shared fields without `LastKnownAffiliationId`. Fields of study also contain `Level`.

DisplayName is missing/sentinel for 140,792 authors, 16 institutions and 17,458 fields of study. Phase 3 needs an explicit missing-label/alias policy; it must not fabricate names. The full field types and samples are preserved in `documentation/phase2/audit_stark_mag.json`.

## Official questions and splits

Both CSVs have columns `id`, `query`, `answer_ids`. Gold answers are serialized lists of integer IDs, parsed using `ast.literal_eval`, never `eval`.

- Synthetic QA: 13,323 queries, 37,044 answer references, 6,872 multi-answer questions, no empty answer lists. Every answer reference points to a paper node.
- Official split files contain query IDs, not row offsets: train 7,993; val 2,665; test 2,665. They are disjoint and together cover every synthetic query exactly once.
- `test-0.1.index`: 266 IDs, verified as a subset of test, not an additional disjoint split.
- Human-generated evaluation: 84 queries, 274 answer references, 34 multi-answer questions. It is a separate CSV, not an additional official `.index` file. ID namespaces should remain separate from synthetic queries.

### Human evaluation discrepancies with the planned paper-set benchmark

| Human query ID | Non-paper answer ID | Actual node type | Observation |
| --- | ---: | --- | --- |
| 30 | 832321 | author | The question explicitly asks for an author; this is outside the planned paper-set answer scope, not automatically a corrupt label. |
| 50 | 15775 | author | The question asks for a paper; its gold list contains paper 1174913 and author 15775. |
| 72 | 98059 | author | The question asks for a paper; its sole gold answer refers to an author. |

All 274 human references are within node bounds, but only 271 point to papers. Original questions and gold lists remain unchanged. Do not silently remove, remap or repair these records. Their benchmark treatment requires an explicit documented decision during benchmark construction/review. These findings do not prevent acquiring the source or building faithful views after Phase 3 approval.

## Resource and verification observations

The acquisition began with about 339.7 GB free disk space. Source plus retained resumable cache uses about 3.11 GB; free space afterward was about 336.6 GB. Cache and pre-scan files are under the dedicated `data/MMG_STARK_MAG/_build/` directory, excluded from Git along with raw data.

Only about 0.8 GB physical RAM was free at the initial check. The full audit used a 14,983,744-byte node-type array, a 1,872,968-byte coverage mask, edge batches of 100,000 and 88,982 referenced pickle memo entries. It streamed all 1,872,968 metadata rows instead of materializing the 1.16 GB pickle as a giant dictionary. Measured peak working set was 84,443,136 bytes (about 81 MiB). The complete audit took 46.46 seconds with the pre-scan cached; initial opcode scanning took about 84 seconds.

Audit status is `pass_with_findings` because the original human QA contains non-paper answers. All source-integrity, shape, node-coverage, edge-endpoint and primary-split checks completed. Offline acquisition reruns rechecked the same files without network access, preserving acquisition timestamps and source bytes.

No FAISS index, CSR adjacency, DuckDB database, canonical registry, research text/graph/structured view, benchmark or advanced algorithm was created.

## File checksums

| Staged relative filename | Bytes | SHA-256 |
| --- | ---: | --- |
| `qa/mag/split/test-0.1.index` | 1,376 | `618090b8caaa97d6f757b28cb9a9d2fbd6a258254c9ad5810ba65639e281130c` |
| `qa/mag/split/test.index` | 13,804 | `a82b75974a5726f8b96fffac5eadcdd426df5a2370508e2538b0b19d8ec46e63` |
| `qa/mag/split/train.index` | 41,258 | `234c070513f77816346dd8049b26e6c65b7049252e9d3ab6ef213bf3035f516f` |
| `qa/mag/split/val.index` | 13,763 | `a3f8e6a6ce441bb0e00e3d2057bb4232793f3f4a528c776600e70d50433f0a25` |
| `qa/mag/stark_qa/stark_qa.csv` | 2,729,579 | `2bde0b3f70dcbb25f594eaab70c123e91a505ba60958374669384b018bb4f1c5` |
| `qa/mag/stark_qa/stark_qa_human_generated_eval.csv` | 13,523 | `3951bfb21976e1fb97664e0db75caf3c90aba0468e8bc6d75579c0e20c0f3471` |
| `skb/mag/processed.zip` | 484,062,494 | `7bfac742c1fb77694b3fab76be5088f9c3a636f47366188b70d3f378cfbd3053` |
| `skb/mag/schema/mag.json` | 2,578 | `1a741bb3fff019551b03f8b92a7be9fd9ba0cc866e0277e1724b187db1c6b218` |
| `skb/mag/schema/reduced_mag.json` | 1,354 | `13767037e25246e48a56819d4658d8933956e0da94c5160c511c4074daacf7ea` |
| `extracted/processed/edge_types.pt` | 478,073,460 | `47c49916363995859f04ce4c822e9faa6dba5d9b76f57f926dd6ee84d6b4fa29` |
| `extracted/processed/node_types.pt` | 14,984,500 | `3487665ea4fa9b5f9ac28b868203ff414cc9e3f1dd942f97258e5c3f20f1d33d` |
| `extracted/processed/edge_index.pt` | 478,073,460 | `8542449e21113fa4f265c496498bedfec892215b3d9deab38143c3c109da776b` |
| `extracted/processed/edge_type_dict.pkl` | 152 | `26c5bbc4483e430c089ea4696fa37fa4fe1cfabd328975695d5ab18e90206a56` |
| `extracted/processed/node_info.pkl` | 1,162,767,283 | `cc83e452eefd1b4588d48dc154d9c4a2e3efda6464b72678e4db7b410b3d8668` |
| `extracted/processed/node_type_dict.pkl` | 72 | `4ab254b0e6f3c3a029dbd9f3d29b0f37a550f8b1743dbd78d8df828d6a379947` |

## Phase 3 representation addendum

The acquisition sections above describe the Phase 2 checkpoint. Phase 3 builds the approved source-linked representations under the same ignored dataset root. The immutable official source still contains **19,919,698 directed edges**; a further **19,919,698 tagged inverse edges** support traversal only.

The physical schema, exact content/NULL/venue policy, field definitions, model backend, identity mapping and reproducible commands are in [the Phase 3 contract](phase3/Representation_Contract.md). The generated review copy [representation_manifest.json](phase3/representation_manifest.json) contains every output size and SHA-256, schemas, full-source audits and resource measurements. [The Phase 3 report](Phase_Reports/Phase_03_Build_MMG_STaRK_MAG.md) records acceptance results and samples.

Text, graph and structured records join on the same integer global STaRK paper ID. Registry string IDs are `stark:<global_id>`; original type-local and MAG IDs remain provenance. Missing structured values/names are NULL. Text contains only title/abstract; graph semantics contain paper titles or actual entity names; structured SQL contains only structured source attributes. The audit source columns remain available separately in DuckDB.

All 84 human QA records remain unchanged. The approved future Phase 4 policy is whole-query exclusion for mixed/non-paper answer queries in primary `human_test`, including known queries 30, 50 and 72. No benchmark has been constructed.
