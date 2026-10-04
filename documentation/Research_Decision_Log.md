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
