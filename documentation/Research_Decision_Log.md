# Research Decision Log

## Phase 0 — 2026-10-04

- Preserve the existing lowercase `documentation/` directory. Windows paths are case-insensitive; do not create a second `Documentation/` tree.
- Use the existing Windows CPython 3.12.14 virtual environment explicitly. Plain `python` resolves to a different MSYS2 interpreter.
- No Git repository existed in the project or its parent chain. Initialize local Git and preserve the current baseline; no remote or publication is configured.
- Remove a credential-like value from `.env.example` before committing. Leave the user's `.env` untouched and ignored. Recommend rotating the exposed example credential.
- Capture installed package versions and artifact checksums. Preserve built storage in a ZIP archive because working storage is ignored by Git. Do not rebuild or alter working retrieval artifacts.
- Store the configuration snapshot as JSON-compatible YAML, avoiding new dependencies for Phase 0.
- Add an audit script only; leave app.py and src retrieval/generation behavior unchanged.
- Initial live request failed under restricted networking. Automatic review then required explicit approval for transmitting excerpts to Groq. User granted approval; both live checks subsequently succeeded using the existing model.
- Sandbox process setup later failed. Approved elevated commands completed local audit work; no research design or environment substitution was made.
- Live answer checks are smoke tests, not a scientific evaluation. Record grounding/citation limitations rather than changing baseline prompts or methods.

## Phase 1 — 2026-10-04

Authorization: Phase 0 explicitly approved; implement scaffold only and stop before Phase 2.

| ID | Decision | Reason and validation | Research impact |
| --- | --- | --- | --- |
| P1-01 | Keep `research/` independent of `src/`; reserve later algorithm modules with docstrings only. | Import/dependency-boundary tests and baseline hash checks. | No MVP behavior or advanced method implemented. |
| P1-02 | Use Pydantic 2.13.5 and PyYAML 6.0.3, already installed; declare them in `requirements-research.txt`. | No package upgrades; `pip check` passes. | Baseline requirements/environment unchanged. |
| P1-03 | Resolve defaults < YAML < explicit `RESEARCH__` overrides; read credentials only in config, with optional dotenv < environment. | Reject unknown/duplicate keys and unsafe YAML; test precedence and secret-free hashes. | No algorithm reads arbitrary environment settings. |
| P1-04 | Hash canonical JSON of effective public configuration, retaining portable relative paths and excluding credentials. | Two fresh processes produce identical hashes; changed controls change hashes. | Credentials do not affect experiment identity. |
| P1-05 | Use frozen contracts, tuples and canonical JSON object strings for flexible payload/metadata/params fields. | Mutation, source-partition, duplicate-ID, invalid-number and round-trip tests. | RQ2 input can be preserved exactly; actual caching remains later work. |
| P1-06 | Missing source attributes remain null. Text uses stripped title plus two newlines plus abstract; title alone if missing. | Missing-abstract and date consistency checks. | No invented STaRK IDs; actual loader mappings deferred. |
| P1-07 | Seed Python and NumPy explicitly; optionally accept a supplied PyTorch module. | Repeated RNG draws match; bounds validated. | No claim of cross-hardware, process-hash or API determinism. |
| P1-08 | Experiment IDs hash config plus method/split/revision/trial. Preserve manifests; log to console and JSONL with owned handlers. | Collision rejection, repeat-open, redaction and cleanup tests. | Contracts only, not the Phase 5 evaluation/resume engine. |
| P1-09 | Use three fictional papers and six entities; keep dataset/benchmark versions `unbuilt`. | Cross-view joins and hand-computed author/year intersection. | Fixture is not a benchmark; no STaRK acquisition. |
| P1-10 | Unknown tokens/cost are null; measured tokens require a counter and costs a currency. | Contract validation and round trips. | Avoid fabricated measurements. |
| P1-11 | Append this log; keep all other baseline-tracked files and storage immutable. | 54 Git object checks and four storage byte comparisons. | Baseline tag remains at the approved commit. |

Execution notes: sandbox launcher setup still fails, so approved elevated local commands were used. Git trust was scoped to individual commands. Pytest cache writing crossed sandbox ownership, so final tests used `-p no:cacheprovider`; coverage was unchanged. An initial test found a Windows rooted-path validation bug; it was fixed before acceptance. No external calls or package installs were required.

## Phase 2 — 2026-10-04

Authorization: Phase 1 approved; acquire/stage official STaRK-MAG automatically, audit actual source, and stop before Phase 3.

| ID | Decision | Evidence and validation | Research impact |
| --- | --- | --- | --- |
| P2-01 | Commit approved Phase 1 before acquisition. | Checkpoint `ea88dcfee5523f609b34fb597ae7a5884ed9899f`; working tree verified clean before download. Baseline tag remains `4592d102b363c7d55d3c85ee67efe89409ae96b5`. | Non-destructive recovery point; no baseline changes. |
| P2-02 | Use official processed archive and QA/schema files via the same `hf_hub_download` primitive as MagSKB. | Pin HF revision `88269e23e90587f99476c5dd74e235a0877e69be` and upstream code `b246b9490b1dc216892ce78303140014506932c1`. Public ungated access succeeded. | Exactly official source bytes; no alternative dataset or reprocessing. |
| P2-03 | Do not instantiate the full SKB constructor or install its broad graph/LLM dependency stack. | Installed Hugging Face library suffices; constructor would load metadata and build/undirect adjacency. No environment changes; pip check passes. | Honors Phase 2 resource/scope constraints; no research graph constructed. |
| P2-04 | Preserve archive plus exact extracted members; keep cache/pre-scan under `_build/`. | Official LFS SHA-256 and small-file Git blob checks; all extracted members checked against ZIP bytes/CRCs; offline reruns pass. | Source remains unchanged and restartable; generated manifests are separate metadata. |
| P2-05 | Audit serialized data using restricted pickle decoding and chunked tensor reads. | All 1,872,968 node records and 19,919,698 stored edges audited; peak about 81 MiB. Regression tests cover memo reuse and tensor offsets/strides. | No giant Python graph, NetworkX, sparse adjacency or derived view. |
| P2-06 | Read logical tensor views, not all backing storage. | Edge-types tensor starts at storage offset 39,839,396; backing file includes three rows. Test verifies nonzero-offset tensor reading. | Prevents false relation counts and corrupt interpretation. |
| P2-07 | Report source missing values and names faithfully; do not fill them now. | 22,049 missing paper Date/Year/PaperCitationCount/PaperRank values; missing entity names counted. | No fabricated structured facts or aliases. |
| P2-08 | Defer unified venue mapping/type policy to Phase 3 review/implementation. | Multiple journal/conference/original-venue fields exist; no single venue_id/name/type column. | No silent schema derivation. |
| P2-09 | Preserve and flag three human QA references to author nodes. | Human query 30 explicitly asks for an author; queries 50/72 ask for papers but contain author gold IDs. Synthetic QA is entirely paper-referenced. | No label correction/remapping/filtering; paper-set benchmark policy remains a later explicit decision. |
| P2-10 | Count source directed edges; do not synthesize inverse edges or deduplicate. | Four expected endpoint/relation combinations verified across every stored edge. | Keeps acquisition separate from Phase 3 graph representation choices. |

The source audit is complete with documented findings. Phase 3 views are not built. No external access, licensing or hardware blocker required user intervention; limited free RAM was handled with streaming. These source discrepancies do not authorize changes to the frozen research questions or benchmark ground truth.

## Phase 3 — 2026-10-04

Authorization: Phase 2 approved; build isolated MMG-STaRK-MAG v1 representations and stop before any benchmark work. The user's explicit Phase 3 rules supersede earlier assumed counts and formatting.

| ID | Decision | Evidence and validation | Research impact |
| --- | --- | --- | --- |
| P3-01 | Checkpoint approved Phase 2 before implementation. | Commit `f8fc9a29f95b008a0216620449568f8bba4599a6`; clean working tree verified before changes. | Non-destructive recovery; immutable baseline tag retained. |
| P3-02 | Use global STaRK integers as all physical join keys; retain `stark:<global_id>`, type-local ID and MAG ID in registry. | Full source registry equality, uniqueness and cross-view joins. | No MAG/global-ID ambiguity. Existing contiguous global IDs directly index CSR. |
| P3-03 | Preserve exact title + two newlines + abstract, one paper/document. | Exhaustive equality against raw metadata and four-column schema. | Supersedes P1-06 stripping/missing-abstract formatting; MVP chunking untouched. |
| P3-04 | NULL names/attributes stay NULL; zero remains zero. | Full source comparison and sentinel/zero tests. | No date-derived year, recomputed citation count/rank or fabricated aliases. |
| P3-05 | Apply approved venue precedence using either present member of each ID/name pair; do not fill its missing component from lower levels. | Full source validation plus pair/priority tests. Original-only namespace has NULL ID/type; DocType stays separate. | Normalization is explicit, no invented venue taxonomy. All raw structured audit columns retained. |
| P3-06 | Keep all 19,919,698 official directed edges and add an equal number of tagged inverse traversal rows. | Every source tensor column and inverse checked; original coverage/uniqueness validated. | 39,839,396 is traversal storage size, never the official source edge count. |
| P3-07 | Stream metadata/Parquet and external-sort edges into memory-mapped CSR. | Bounded batches, 512 MB DuckDB limit, real/synthetic paths and full CSR equality. | No full NetworkX graph or giant in-memory metadata dictionary. |
| P3-08 | Exact aliases use NFKC/casefold/whitespace normalization; retain ambiguous associations. | 1,714,702 aliases, 105,792 ambiguous normalized strings; collision regression. | No semantic/fuzzy alias resolution is added. |
| P3-09 | Use frozen MiniLM weights with a pinned ONNX CUDA float32 export, mean pooling/L2 normalization and the original 256-token limit. | 33-case CPU PyTorch parity: maximum absolute difference 1.8998980522155762e-07, minimum cosine 0.9999999403953552. Model revision/weight/export hashes recorded. | Practical GPU build without replacing CPU torch or changing the showcase. Full text remains in Parquet; embedding truncation remains explicit. |
| P3-10 | Exact FAISS inner-product storage preallocated once; durable vector/ID shards retained. | Regression equivalence to normal `add`, serialization roundtrip, full reconstruction/mapping audit. | Avoids index-growth memory duplication; no approximate index or quantization. |
| P3-11 | Lock source/configuration; atomically checkpoint shards/stages; reject corrupt completed outputs. | Intentional embedding interruption/resume, partial-CSR recovery, corruption rejection and full-build reuse checks. | Restartable builds do not silently mix versions. |
| P3-12 | Add only required research dependencies, constrained by the original package freeze. | All 81 baseline pins retained, pip check and unchanged Streamlit smoke pass. | No baseline package upgrade, prompt change or paid generation call. |
| P3-13 | Preserve original human QA and defer whole-query exclusions to Phase 4. | Source hashes verify all 84 records unchanged; no benchmark directory constructed. | Primary future human_test must exclude mixed/non-paper queries whole, including IDs 30/50/72; never repair their labels. |

Implementation notes: Windows sandbox process initialization required automatically reviewed elevated commands. Git trust is scoped per command. An initial byte-to-Git preservation comparison flagged checkout CRLF conversion; exact Phase 0 inventory SHA-256 and Git-filtered object identity both confirmed the baseline file was unchanged. No access/hardware blocker required user intervention.
