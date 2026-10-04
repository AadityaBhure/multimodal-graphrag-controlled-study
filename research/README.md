# Research scaffold

Phase 1 supplies configuration, immutable versioned contracts, reproducibility
helpers, structured logging, experiment directory identity and synthetic tests.
Reserved modules contain no algorithms. There is no dataset download, graph
build, benchmark generator, evaluation runner or LLM call in this package.
The existing showcase remains in `src/` and `app.py` with its own frozen settings.

## Setup and checks

Use the project's Windows CPython 3.12.14 environment. Dependencies are declared
in `requirements-research.txt` in addition to the unchanged `requirements.txt`.
The required PyYAML and Pydantic versions were already installed in Phase 0.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_scaffold.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe scripts/check_research_scaffold.py
```

## Configuration

`research.common.config.load_config()` reads `configs/base.yaml` by default.
Precedence is schema defaults, YAML, then explicitly named environment overrides.
Supported overrides are `RESEARCH__SEED` and `RESEARCH__<SECTION>__<FIELD>` for
fields in `models`, `dataset`, `paths`, and `logging`. Unknown prefixed settings,
unknown YAML keys, duplicate YAML keys and unsafe YAML objects are rejected.
Example: `RESEARCH__LOGGING__LEVEL=DEBUG`. Models and controls remain logged and
hashed, and changing them still requires the experiment's scientific approval.

Credentials are accepted only by this loader. `GROQ_API_KEY` in the supplied or
process environment overrides an explicitly supplied `dotenv_path`. No `.env`
is automatically loaded, no environment variables are mutated, and no directory
is created while loading configuration. Never serialize or log raw credentials.
The secret is excluded from the public config and its SHA-256 hash. Paths stay
relative in that hash for portability and resolve explicitly against the project.
Dataset and benchmark versions remain `unbuilt` until their approved phases.

## Contracts

`research.common.contracts` defines all ten roadmap contracts plus typed
provenance, timings, calls, metrics and errors. Contracts are frozen and reject
unknown fields. JSON round trips preserve tuple-based evidence and provenance.
Structured payloads, metadata and experiment params are canonical JSON object
strings: parse a copy with `json.loads`, then construct a new validated object
to change evidence. Do not use Pydantic's unchecked `model_construct` or
`model_copy(update=...)` on external inputs. Use `model_validate` instead.

Evidence IDs must be unique in a retrieval bundle and each source partition must
match its evidence type. `canonical_bytes()` and `bundle_hash()` allow later
RQ2 code to persist and verify exactly identical input bundles, including their
timings and calls. No retrieval caching is implemented in Phase 1.

Unknown dataset IDs and structured fields use null, not invented values. Tiny
fixture entities have no actual STaRK/MAG IDs. Text content is the stripped title
plus two newlines and the stripped abstract, or title alone for a missing abstract.
Full real-dataset relation and leakage validation is deferred to Phase 3.
Token counts require an identified tokenizer/counter; unknown token counts,
cost and usage remain null. Numeric timings are milliseconds, cost carries a
currency, and record timestamps must be timezone-aware.

`research.common.interfaces` defines dependency protocols. Fusion consumes a
bundle without a retriever argument and returns a ContextPackage. Context
management accepts either raw evidence bundles (RQ1) or a fused ContextPackage
(integration). These are interface contracts, not enforced experiment controls;
retrieval-isolation checks belong to the later fusion implementation.

## Reproducibility and experiment directories

`seed_everything(seed)` seeds Python and NumPy. An explicitly supplied PyTorch
module additionally enables its deterministic settings; the helper never imports
PyTorch implicitly. It cannot guarantee remote API or cross-hardware equality,
and it does not change the process hash seed after startup.

`ExperimentSpec` identifies method, split, code revision and repeat/trial number.
`prepare_experiment(config, spec)` creates
`artifacts/experiments/exp-<sha256>/manifest.json`. Identity includes the public
config (including seed and dataset/benchmark versions) and the spec. Reopening
the same manifest is safe; a conflicting manifest is rejected, never overwritten.
Directory identity alone is not a resumable evaluation runner; that is Phase 5.

Use `ExperimentLogger` as a context manager for append-only UTF-8 JSONL and
console output. Supply configured secret values to its `secrets` argument; it
also redacts sensitive fields recursively and recognizable Groq keys. It owns
and closes its handlers without changing root or showcase logging. Do not log
arbitrary confidential inputs expecting heuristic redaction to catch everything.

## Test fixture

`tests/fixtures/research/corpus.json` contains three fictional papers, one author,
one institution, one field, five graph edges, three text records and three
structured records. It includes a missing abstract and a hand-checkable
author/year intersection. It is only a unit-test fixture, not a research benchmark.
