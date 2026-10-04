# Phase 1 — Research Scaffold Configuration and Experiment Contracts

PHASE: 1 — Research Scaffold, Configuration, and Experiment Contracts

STATUS: PASS

OBJECTIVE: Establish validated interchangeable research contracts, central configuration and reproducibility infrastructure alongside the unchanged showcase.

## Files created or modified

- `research/`: 33 Python files covering all requested package areas. Common modules implement configuration, contracts, canonical serialization/hashing, seeding, logging and Protocol interfaces. Experiment contracts define identity/manifests/directories. Later algorithm modules are docstring-only placeholders.
- `research/README.md`: setup, API conventions, limitations and reproduction commands.
- `configs/base.yaml`: effective research defaults, frozen model choices and explicit unbuilt dataset versions.
- `configs/baselines/`, `configs/rq1/`, `configs/rq2/`, `configs/rq3/`, `configs/rq4/`: reserved configuration directories with explanatory README files only.
- `requirements-research.txt`: separate declarations for already-installed Pydantic/PyYAML; MVP requirements unchanged.
- `tests/fixtures/research/corpus.json`: deterministic synthetic corpus.
- `tests/test_research_scaffold.py`: 21 collected research test cases.
- `scripts/check_research_scaffold.py`: offline configuration, baseline-integrity and synthetic logging check.
- `artifacts/{experiments,plots,tables}/`: directory conventions, plus one synthetic manifest/log demonstration beneath `artifacts/experiments/exp-<sha256>/`.
- `documentation/Research_Decision_Log.md`: appended P1-01 through P1-11; Phase 0 entries preserved.
- `documentation/phase1/`: saved pytest output, UI smoke result, scaffold/integrity result, credential-scan result and file checksum manifest.
- `documentation/Phase_Reports/Phase_01_Research_Scaffold.md`: this report.

## Commands run

Use the explicit `.\.venv\Scripts\python.exe` interpreter for all Python commands below.

- Inspected Git status, local instructions, baseline snapshot and decision log. Read the roadmap contracts and exact Phase 1 acceptance criteria. The initial XML read attempted unavailable lxml; standard-library ElementTree completed the read without installing anything.
- Imported Pydantic/PyYAML: versions 2.13.5/6.0.3, already installed.
- `python -m pytest tests/test_research_scaffold.py -q`: initial result 20 pass / 1 failure; the failure identified Windows rooted-path acceptance. Fixed the guard. Initial cache warnings resulted from sandbox/user ownership.
- `python -m pytest -q -p no:cacheprovider`: final result 39 passed in 1.12 seconds. Cache disabled only to avoid ownership warnings.
- `python -m pip check`: no broken requirements found.
- Inline Python Streamlit AppTest with `HF_HUB_OFFLINE=1`: executed `app.py` and saved new results under `documentation/phase1/`, without touching the Phase 0 audit files.
- `python scripts/check_research_scaffold.py`: 54 protected files verified against `baseline-mvp-v1`, all four storage files matched the archived baseline bytes, two fresh-process config hashes matched, synthetic directory and dual-output log created.
- `git -c safe.directory=D:/codefiles/RAG_GraphRAG_Demo diff --check`: pass. Git trust settings are per-command; no global Git changes.
- Inline credential scan: Git-visible working files and DOCX/ZIP contents checked against configured credential values and recognizable Groq-key patterns; no findings; `.env` excluded.
- Inline file-manifest generation: SHA-256 checksums for Phase 1 source/config/test/documentation artifacts.

Sandbox process setup remained unavailable, so approved elevated local commands were used. No network calls, package installations, LLM generation or dataset downloads occurred in Phase 1.

## Validation and tests

- **39 tests pass:** all 18 existing MVP tests plus 21 new research cases.
- All ten roadmap contracts serialize/deserialize through JSON; fixture entity references join across text/graph/structured views.
- Frozen bundles reject mutation, duplicate evidence IDs and misplaced source types; nested payload strings cannot be mutated through a parsed copy.
- Invalid numeric values, abstract flags, dates and context-size declarations are rejected.
- Configuration tests cover override precedence, secret exclusion, hash stability/change sensitivity, unknown/duplicate keys, unsafe YAML, schema versions, temperature and path traversal.
- Python/NumPy seeding repeats deterministic draws and rejects invalid seeds.
- Experiment identity is deterministic; conflicting existing manifests are rejected without overwriting them.
- Both console and JSONL receive equivalent parseable records, credentials are redacted recursively, and handlers are closed without duplicates or root-logger changes.
- All research modules import successfully. Boundary tests prohibit research modules outside config from importing environment readers or the frozen `src` package.
- Streamlit loads Demo, Architecture and Dataset with zero exceptions and zero UI error elements.
- Baseline tag still resolves to `4592d102b363c7d55d3c85ee67efe89409ae96b5`; 54 protected tracked files and four storage artifacts match it. The only modified baseline-tracked file is the append-only decision log.

## Artifact counts

- 33 research Python files; ten primary contract classes plus supporting typed contracts.
- 21 new research test cases; 39 total passing tests.
- Synthetic fixture: 6 entities/nodes, 5 edges, 3 paper text records and 3 structured records; one missing abstract.
- 1 base configuration and 5 reserved method-config directories.
- 1 synthetic experiment workspace containing a manifest and JSONL event file; no answers, metrics or benchmark results generated.
- 5 Phase 1 evidence files including the file checksum manifest.
- 11 decisions logged.
- Unchanged MVP: 12 PDFs, 394 chunks/vectors, 74 graph nodes and 87 edges.

## Decisions logged

See P1-01 through P1-11 in `documentation/Research_Decision_Log.md`. The choices cover package isolation, existing dependencies, explicit configuration precedence, secret-free portable hashes, immutable evidence, missing-value/text serialization rules, deterministic seeding, experiment/log lifecycle, synthetic fixtures, unknown metrics and preservation boundaries.

## Known issues and limits

- No blocking issue remains for Phase 1.
- Contracts and placeholders do not implement retrieval, advanced methods, benchmark construction, evaluation or resumable runs. These belong to later approved phases.
- Real STaRK IDs/types and physical loader mappings remain unverified; missing values in fixtures are explicit nulls.
- The synthetic workspace is a contract smoke demonstration, not a research run. Its revision field references the frozen baseline parent; the new Phase 1 files remain available as working-tree changes and their exact bytes are captured by the file manifest. No experimental claim relies on this demonstration.
- PyTorch is supported only when explicitly supplied to the seed helper; the acceptance tests exercise Python/NumPy. Remote API and cross-hardware determinism are not promised.
- Credential scanning/redaction covers configured values and named patterns, not every imaginable unknown secret format.
- Existing Phase 0 answer-quality/citation limitations remain unchanged. No new live calls were needed to verify an unchanged generator.
- UI validation uses Streamlit AppTest, not browser visual inspection.

## Scientific invariants checked

- MVP retrieval algorithms, prompts, parameters, source corpus, baseline configuration/report/artifacts and tag are unchanged.
- Research configuration is independent; model defaults match the approved baseline; no scientific controls were tuned.
- Evidence has explicit source partitions and provenance; immutable serialization supports later identical-input fusion experiments.
- Missing metrics are not fabricated; tokens require an identified counter and costs a currency.
- Synthetic fixtures are explicitly marked and do not masquerade as STaRK data or benchmark ground truth.
- No test-set tuning, research evaluation, winner selection or result claims.
- No Phase 2 work: no STaRK download, raw staging directory, credentials request, loader integration or data transformation.

REVIEW QUESTIONS FOR USER: None needed beyond approval of the completed phase.

NEXT PHASE (NOT STARTED): Phase 2 — Acquire and Stage STaRK-MAG.

STOP: Await explicit user approval before any Phase 2 work.
