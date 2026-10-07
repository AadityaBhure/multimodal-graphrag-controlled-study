# Phase 5 execution protocol

Use the project interpreter from the project root. Configurations are explicit YAML or JSON mappings (JSON is accepted by the duplicate-key-rejecting YAML loader). No environment variable changes their evaluation controls.

```powershell
.\.venv\Scripts\python.exe scripts/run_experiment.py --config configs/phase5-scripted.json --benchmark tests/fixtures/evaluation/benchmark --responses tests/fixtures/evaluation/responses.json --output artifacts/experiments/my-fixture-run
.\.venv\Scripts\python.exe scripts/run_experiment.py --config configs/phase5-validation-smoke.json --output artifacts/experiments/my-validation-adapter-check
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe scripts/audit_phase5_preservation.py
```

Repeat the identical command and directory to resume. A changed config, code tree, package version, system fingerprint, benchmark hash, selected query set or release artifact requires a new output directory. Never delete an incompatible manifest to force resume. Error records are terminal; an intentional retry uses a new config ID/output directory. The runner does not retry paid operations automatically.

`research.evaluation.contracts.EvaluationSystem` requires `system_id`, `version`, `fingerprint` and `execute(SystemInput) -> SystemOutput`. All later systems must implement this interface, initialize themselves from the explicitly named configuration, and version their implementation and external resources. `SystemInput` contains no gold or annotation labels. Model IDs, retrieval controls and optional context/fusion/agentic method IDs are declared in RunnerConfig. System adapters report measured substage durations/calls/tokens in Observation. The runner independently measures total execution elapsed time.

The Phase 5 CLI registers only `synthetic-fixture` (fixed empty response) and `synthetic-scripted` (prewritten response file, hashed into identity). New methods must later be deliberately registered; neither dynamic arbitrary imports nor B1–B4 are provided here.

Artifacts: `manifest.json`, atomic `records/<query-hash>.json`, atomic numbered `events/*.json`, derived `records.jsonl`, `events.jsonl`, `aggregate.json`, `aggregate.csv`, and `status.json`. The lock file is persistent but its OS lock releases when the process exits. Per-query files are authoritative; materialization reconstructs truncated/missing derived JSONL and tables. Partial runs set `INCOMPLETE` in status and `run_complete=false` on every table row. A complete run may still contain errors, shown separately by `n_errors` and status.

RetrievalBundle cache use is opt-in through `research.experiments.evidence_cache.EvidenceCache`. Its key binds query content, source representation, retriever/version, retrieval parameters and seed; a different bundle under an existing key is refused. Systems must pass only immutable measured evidence to this cache. No cache is prepopulated from real retrieval, and the runner does not silently cache final answers.

Stress overlays are read from hash-verified Phase 4 files. Noise exposes distractor IDs/paths; conflict exposes the mutated fact with source/field identity. Authoritative facts, gold constraints, similarity-to-gold IDs, expected behavior and inverse repairs are withheld. Canonical stores remain the source of truth. Later adapters are responsible for applying these injections to their evaluation-time evidence streams; the synthetic adapter intentionally performs no retrieval. Unanswerable queries already have the frozen mutated question and empty gold; no canonical mutation is performed.

To publish a separate release artifact after actual human review, export decisions from the Phase 4 review UI. An authorized release operator can run:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_experiment_release.py --export path/to/human_review_decisions.json --output artifacts/reviews/release.json --released-by "Actual reviewer" --leakage-adjudicated
```

This command creates no decisions. It rejects an incomplete review, duplicates, wrong benchmark version and an existing release file; it binds the explicit operator attestation to the current benchmark manifest and test freeze ID. It needs attributed, timestamped passing decisions for every test and human-test query. The original browser export names the benchmark version but does not contain a strong freeze hash; the release operator must ensure the exported decisions came from this frozen review package. Release metadata is an audit attestation, not a cryptographic signature or proof that a person reviewed the content. Validation-review items can be included; the final-run gate specifically requires 100% test and human-test coverage plus leakage adjudication.

Set config mode to `paper_test`, select test/human_test and pass `--release artifacts/reviews/release.json`. Both initial execution and resume check the release gate. Development is limited to train/validation. This project currently has no real release artifact and no real test runs. Corrected annotation fields in exports are preserved as review metadata but do not override frozen cohort labels.

Metric definitions, availability rules, validation and limitations are in the Phase 5 Review Report. JSON Schemas in this directory define query results, events, release metadata and later agent/fusion annotation inputs. Phase 1 result contracts remain import-compatible; Phase 5 adds a stricter execution record rather than silently changing old serialization.
