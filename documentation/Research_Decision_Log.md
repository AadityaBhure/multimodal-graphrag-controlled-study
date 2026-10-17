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

## Phase 4 — 2026-10-06–07

Authorization: the user's pasted request approved Phase 3 and authorized benchmark construction only, followed by a mandatory review stop.

| ID | Decision | Evidence and validation | Research impact |
| --- | --- | --- | --- |
| P4-01 | Checkpoint all approved Phase 3 implementation/contracts before benchmark work. | Commit `3b34d9c234f9861455eea5fc7fd34a939f87518e`; clean tree confirmed afterward; baseline tag unchanged. | Recoverable phase boundary; raw and representation artifacts remain immutable. |
| P4-02 | Preserve original CSV/split bytes and logical original-record JSONL; namespace project query IDs while retaining source IDs. | Complete source equality/provenance checks across 13,323 synthetic and 84 human records. | No rewritten questions or repaired/deleted source answers. |
| P4-03 | Derive primary human compatibility from authoritative entity IDs; exclude an entire incompatible query. | IDs 30/50/72 excluded whole; 81 retained; original IDs/types/reasons saved. | Mixed query 50 retains both original answers in preservation evidence, with neither copied as a repaired benchmark query. |
| P4-04 | Extend the Phase 1 Contract for benchmark records; leave absent official taxonomy annotations explicitly unverified. | Schema rejects inconsistent answerability, modality and hop labels; official provenance distinguishes supplied gold from recomputed generated gold. | Avoids fabricating official modality/hop/semantic-correctness claims. Official strata need human annotation. |
| P4-05 | Use exact operational abstract claims, graph paths and nullable parameterized predicates; compute candidates and gold before wording. | All 167 generated variants and 286 source-set references recomputed; 665,671 candidate identities and 2,336 graph witnesses checked. | No LLM ground truth or wording calls; text scope is explicit and narrower than unrestricted semantic relevance. |
| P4-06 | Require strict source necessity for answerable combinations. | Dropping any required modality enlarges the answer set; counterexample IDs persisted; redundant combinations rejected. | Multi-source labels represent actual recorded predicate necessity, not incidental evidence overlap. |
| P4-07 | Use split-exclusive construction instances, anchors and actual split-blind operator skeletons. | Structural signatures ignore condition values and template/split names; regression and full audit check disjointness. | Prevents template renaming from hiding leakage. Creates declared operator/hop distribution shift rather than IID splits. |
| P4-08 | Keep paired normal/noise/conflict variants in the same split; detect unexpected duplicates separately. | Exact and bounded cross-split shingle/Jaccard/sequence scans; no unexpected exact/high-similarity findings. | Paired variants are correlated. No claim of exhaustive semantic paraphrase detection. |
| P4-09 | Verify empty sets from deterministic condition mutations; create noise/conflict only as external evidence overlays. | 42 empty-answer proofs, 41 noise cases, 42 reversible conflicts; every source hash unchanged. | No retrieval-failure labels or canonical-store contamination. One GS noise case omitted for unavailable distractor. |
| P4-10 | Prefer defensible small generated coverage over forced balance. | 42 base constructions cover seven modalities in three splits; complete imbalance/degree/year/answer-size statistics. | 167 variants are not 167 independent semantic questions; some stress cases deliberately simple. |
| P4-11 | Freeze content hashes separately from human approval; package review work before asking for manual verification. | 3,390 pending reviews, zero approvals; all test/human_test plus 20% official validation and all generated validation; 10,316 evidence records. | Paper-quality release remains blocked pending actual human decisions and official annotation/semantic review. |
| P4-12 | Regenerate the complete benchmark into a separate directory and compare all bytes; preserve Phase 5 stubs. | Full regeneration/audits and baseline/environment/source/representation checks; no evaluation metrics or runner implemented. | Reproducible Phase 4 artifacts with a strict approval gate before subsequent implementation. |

Execution notes: an initial Windows-default decoding failure was fixed with explicit UTF-8; no source data was changed. The integrated browser tool could not initialize its sandbox; an isolated headless browser was used for review-page rendering. The review page stores human decisions only in browser local storage/export, never in canonical source or frozen question files.

## Phase 5 decisions — 2026-10-07

| ID | Decision | Evidence and validation | Research impact |
| --- | --- | --- | --- |
| P5-01 | Checkpoint approved Phase 4 before implementation. | `262c4d1636b7b3023d7d8863eb7105a4354513a1`; clean working tree confirmed. | Frozen benchmark, representations, raw source and baseline remain unchanged. |
| P5-02 | Score paper sets using canonical integer IDs; exact match means exact set equality. | Hand-computed set/empty/duplicate tests. | Ordering and repeated answers cannot inflate results; failure is NULL, not a valid empty answer. |
| P5-03 | Distinguish unavailable observations from measured zero. | Strict nullable telemetry, token provenance, explicit pricing and baseline requirements. | No invented timing, token, price, evidence, faithfulness or agent/fusion measurements. |
| P5-04 | Use frozen operational labels only for generated queries; keep official labels unverified. | Full read-only audit counts 13,404 unverified records. | Human release decisions do not silently relabel or repair benchmark records. |
| P5-05 | Make experiment identity depend on named configuration, code/package versions, benchmark/representation hashes, selection, system fingerprint and release. | Independent-run identity and mismatch tests. | Compatible resume only; timestamps and measured timing are not identity inputs. |
| P5-06 | Commit each query atomically under an exclusive process lock; derive JSONL/tables from raw records. | Interruptions, partial completion, completed-record recovery and mixed-version rejection tests. | No duplicate completed queries; failed queries remain explicit terminal errors; incomplete tables are marked. |
| P5-07 | Gate test/human-test execution on a separate, hash-bound human release artifact. | Missing/incomplete/duplicate/wrong-version/revoked metadata rejected; real benchmark remains blocked. | Requires all 2,801 test and human-test passing reviews plus explicit leakage adjudication; no automatic approvals. |
| P5-08 | Pass only question, query ID, seed and sanitized stress injections to systems. | Both overlay types tested and all actual overlays parsed read-only. | Gold, source grading criteria, annotation labels and conflict authority are excluded from system input. |
| P5-09 | Cache optional immutable RetrievalBundle values by source/config/query/version hashes. | Cache roundtrip, collision and corruption tests. | Infrastructure for later controlled evidence reuse; no RQ algorithm implemented. |
| P5-10 | Run only fixed synthetic systems in Phase 5. | Five tiny fixture queries, 57 real validation adapter checks, zero retrieval/LLM calls. | Infrastructure verification only; no baseline performance or scientific results claimed. |

## Phase 6 decisions — 2026-10-07

| ID | Decision | Evidence and validation | Research impact |
| --- | --- | --- | --- |
| P6-01 | Checkpoint approved Phase 5 before baseline implementation. | `721c27b2bddf0efca2cc62eeeb6e73e2d2c9ca01`; clean tree confirmed; protected artifact hashes verified before work. | Recoverable phase boundary; baseline tag and frozen data remain unchanged. |
| P6-02 | B1 uses the frozen exact FAISS index and pinned MiniLM ONNX weights/tokenizer for CPU query encoding. | Query/document embedding parity max absolute error 1.36e-7; canonical-ID joins audited. | No paper re-embedding, index rebuild, reranking or representation modification. |
| P6-03 | B2 resolves a bounded graph-label candidate pool, ranks seeds by MiniLM label similarity, then uses bounded breadth-first CSR traversal. | Source-boundary, missing-name, no-seed/no-fallback, inverse-edge and budget tests; full data uses read-only memory maps. | Title/name/relationship evidence only; no abstract access or global Text RAG fallback. |
| P6-04 | B3 uses deterministic supported-language parsing into a closed typed AND predicate plan. | Parameterized SQL, fixed projection/order, explicit NULL operators, injection tests and actual DuckDB write rejection. | Unsupported intents are explicit; no arbitrary SQL or extra parser LLM call. |
| P6-05 | B4 invokes all three source interfaces independently, even after a source failure, then concatenates fixed source sections. | Independent-call, partial-failure, context-budget and cache tests. | No routing, entity alignment, advanced pruning or context optimization. |
| P6-06 | Share Groq model, temperature zero, low reasoning effort, seed policy, JSON output contract and fixed token/context caps. | Mock transport contract plus four approved actual Groq calls. | Grounded IDs only; invalid answers preserve evidence/usage and expose typed errors. |
| P6-07 | Extend Phase 5 output with optional diagnostics/errors so failures can retain measured evidence and telemetry. | Previous tests still pass; new baseline runner failure/resume test passes. | Backward-compatible defaults; failed answers remain NULL rather than fake empty sets. |
| P6-08 | Reuse immutable source evidence with implementation-versioned cache keys; inject stress separately. | Cache retains retrieval diagnostics and includes source-code fingerprints; structured overlay NULLs preserved; B2 candidate restrictions enforced. | B4 API smoke can reuse B1–B3 evidence without reretrieval; cached latency is explicitly distinguished. |
| P6-09 | Freeze controls before inspecting results and execute only bounded validation work. | Five offline queries per baseline; one shared validation query per baseline for API smoke; no test/human-test execution. | Illustrative checks only, not scientific performance estimates; no parameters tuned in response to outcomes. |
| P6-10 | Treat external-data approval as distinct from API token availability. | Automatic review initially rejected the four Groq payloads; exact previews were prepared and the user explicitly approved them; four calls then succeeded. | No request bypass, hidden extra calls or large paid batch. |

## Phase 6.5 decisions — 2026-10-08

| ID | Decision | Evidence and validation | Research impact |
| --- | --- | --- | --- |
| P6.5-01 | Checkpoint approved Phase 6 before UI integration. | `a19bdd5e30e33caa7c82a8a0095dcdd1e610693e`; clean working tree confirmed before implementation. | Frozen baseline and approved scientific implementations preserved. |
| P6.5-02 | Add a separate Streamlit entry point that delegates retrieval to existing BaselineSystem and approved configs. | Four real-data retrieval checks and unchanged-baseline delegation tests. | No new algorithms, tuning or scientific experiments. |
| P6.5-03 | Generate only on an explicit button action from an existing evidence snapshot. | Mock tests cover stale-input rejection, repeated-rerun behavior, context-only IDs, shared generation settings and setup errors. | No gold-answer access, hidden generation or additional API calls during implementation. |
| P6.5-04 | Bound explorer pages and keep interactive metrics distinct from benchmark results. | Cross-view ID check, 25-relationship cap, NULL metric tests, small Graphviz views. | No full graph rendering or fabricated accuracy/token/cost metrics. |

## Program re-sequencing — 2026-10-12

| ID | Decision | Evidence and validation | Research impact |
| --- | --- | --- | --- |
| PR-01 | Phase 9 / RQ3 implementation was started before RQ1/RQ2 completion by explicit user decision (2026-10-11, "Demo first, evaluation continues"); no RQ3 scientific run, training or calibration for the study was executed. | Branch `research/phase9-rq3` (`0c1af0c`); only demo-labelled lite assets exist under ignored `artifacts/phase9/lite`. | RQ3 code is paused; it does not use any RQ1/RQ2 repair output. |
| PR-02 | Approved completion order: RQ1 → RQ2 → RQ1/RQ2 closeout → RQ3 resume → RQ4 → locked final test → paper, with a review stop after every stage. | `documentation/PROJECT_COMPLETION_PLAN.md`. | Restores the handoff order for the remaining work. |
| PR-03 | Superseded status records are not edited; their current status is recorded in the completion plan. | `rq1_repair/execution_status.json` and `Phase_Reports/Phase_09_Agentic_Retrieval_Review.md` remain byte-unchanged. | Preserves historical records. |
| PR-04 | The professor demo (branch `demo/professor-integrated-product-2026-10-12`) is never merged into research branches and must not read study artifacts that later research stages write. | Demo isolation change on the demo branch. | Research runs cannot change demo behaviour and vice versa. |
| PR-05 | RQ1 operational revision 3: the 192-call maximum counts successful calls only (rate-limited attempts resend the byte-identical payload within an allowance of 20) and a rolling 24 h local ledger pauses before 190,000 tokens/day. | Stage 2 found the hidden 200k TPD limit plus attempt-counting would make the run impossible to complete; plan revision 3 differs from v2 only in two implementation hashes; 226 tests pass. | None: payloads, configs, cohort, prompts and caps unchanged. |
| PR-06 | RQ1 operational revision 4: provider calls are made in query-major order (all five methods per query) by the unchanged systems; the unchanged runner then replays stored responses with the dispatcher in replay-only mode. | Removes day-to-day provider drift as a method confound; offline check with real systems: 15/15 pairs, 0 extra calls, 0 payload mismatches; 230 tests pass. | None on payloads or records; scientific plan fields identical to v1. |
| PR-07 | Two-week scope revision (user, 2026-10-15): order RQ1 → RQ3 → RQ2 → RQ4; RQ3 cohort = 28 queries (all 14 families × normal + noisy); RQ2 fusion-isolation study dropped; Phase 11 locked test out of scope. | Free Groq quota allows ~2.7M tokens in two weeks; frozen in `SCOPE_REVISION_2026-10-15.json` before any RQ2/RQ3/RQ4 outcome exists. | Narrower scope, reported as validation-only results with stated limitations; no method, prompt or model change. |
| PR-08 | RQ1 canonical analysis: no statistically supported F1 difference (all Holm p = 1.00, 8 families); Pareto set {CM-B1, CM-01, CM-02}; analysis-script fix: `fallback` diagnostic counted False as a fallback. | `rq1_repair/RQ1_CANONICAL_RESULTS.md`, `analysis.json`; primary metrics unaffected by the fix. | RQ1 complete (validation); candidates for RQ4 decided at the human gate. |
| PR-09 | Phase 9 / RQ3 plan frozen (`documentation/phase9/execution_plan.json`, plan_sha256 0a2cc277...): 28-query cohort (scope revision), 23 code files, 18 artifacts incl. AR-01 (t5-base, best epoch 7, trained on CUDA with the frozen recipe) and AR-02 (Platt, LOWER 0.40 / UPPER 0.75); query-major prefetch + replay-only runner; rolling 24 h ledger. | 273 tests pass; all 41 frozen hashes verified after a simulated fresh checkout; line endings pinned. | Frozen before any RQ3 validation outcome; device is engineering-only (not reported separately, per user). |
| PR-10 | User decisions 2026-10-16: RQ1 canonical results approved; RQ4 context-management candidates CM-01 (quality) and CM-B1 (efficient control). RQ2 settings S1–S12 approved as proposed. RQ2 scope option A (primary 24-bundle study only; fusion-isolation study dropped). | AskUserQuestion answers; `rq2_repair/RQ2_CANONICAL_SETTINGS.md`. | RQ2 frozen before any RQ2 canonical outcome; supportability strata (computed pre-call): FULLY 2, PARTIALLY 6, UNSUPPORTABLE 16. |
| PR-11 | RQ4 option C (user, 2026-10-17): one integrated system INT-1 = selected RQ3 policy -> CM-B1 (graph) -> selected RQ2 fusion -> shared answer; selection rules R-AR / R-CF fixed now; compared with AR-B0 and the selected policy alone on the 28-query cohort. Schedule: as fast as possible (no fixed two-week target); all Groq-independent work runs in parallel. | `documentation/rq4/RQ4_DESIGN.md`, frozen before any RQ2/RQ3 outcome is analysed. | CM-01 not integrated (reported as not tested in RQ4). |
