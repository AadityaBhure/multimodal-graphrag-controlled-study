# Phase 9 / RQ3 — method implementation report

Branch `research/phase9-rq3`. Authority and interpretations: `PHASE9_SPEC_CONSISTENCY_AUDIT.md` (no unresolved research-meaning conflict; items ⚑1–⚑6 recorded there). RQ1/RQ2 canonical repairs are paused and untouched; no repaired CM-01/02/03 or canonical CF-02/03 code is used anywhere in RQ3.

## 1. Module map (`research/agentic/`)

| Module | Role |
|---|---|
| `rule_router.py` | Shared deterministic cue router (addendum §1). AR-B1 uses every routed source; AR-01/02/03 use it as the "base source router". No LLM, no learning, no gold. |
| `tools.py` | The only retrieval entry point for every policy: wraps the UNCHANGED frozen B1/B2/B3 functions; durable result cache keeps the original measured latency. Also the fixed downstream stack: `fixed_context` (per-source budget 8,000 chars, Text→Graph→Structured sections for queried sources only, frozen Phase 6 overlay injection) and the shared final generator `generate_final` (frozen prompt, 1,024 cap, frozen parser). |
| `evidence.py` | Cumulative de-duplicated evidence memory; deterministic text rendering for the CRAG evaluator; paper-ID sets. |
| `llm.py` | Durable, paced, single-in-flight Groq client. Stage identity = payload hash; byte-identical payloads reuse the recorded response (every logical call still counted with original usage/latency). Admission = content tokens + 128 ≤ 8,000 (completion cap sent unchanged, not charged at admission — `groq-admission-probe-v1`). Provider waiting recorded separately. 429/failure persisted, never silently retried; `ProviderPause` stops the run and it resumes later. Local daily-token ledger (195 k of the 200 k/day limit). |
| `prompts.py` | Versioned controller/critic prompts (addendum §2.3, §4 wording + schema/tool documentation), caps (controller 128, agent/validator 256, commentor 128, repair 128) and a prompt-version hash. |
| `controllers.py` | Strict JSON validation + exactly one deterministic repair call per controller/critic output; no heuristic extraction. |
| `policies.py` | Common execution frame (`Policy.execute`), `AlwaysAll` (AR-B0), `RuleRouted` (AR-B1). |
| `adaptive_rag.py` | AR-01. |
| `ar01_model.py` | t5-base route classifier: training (addendum §2.2) and deterministic greedy inference (invalid output → B). |
| `crag.py` | AR-02: cross-encoder evaluator, Platt calibration, threshold grid search with the addendum's tie-break chain, corrective policy. |
| `agent_g.py` | AR-03: Agent → one tool → candidate → Validator → Commentor loop, T=4, loop guard, schema repair. |
| `partition.py`, `analysis.py`, `factory.py` | Frozen train/dev partition; metrics, family-clustered statistics, Pareto, failure taxonomy; policy construction from frozen artifacts. |

## 2. Policies

* **AR-B0** — always Text→Graph→Structured with the raw query, then stop.
* **AR-B1** — router sources once, in order, then stop; default Text.
* **AR-01** — `t5-base` (`google-t5/t5-base` @ `a9723ea7…`) predicts A/B/C from the raw question. A: no retrieval. B: first router source, one call. C: ≤3 distinct sources; after each retrieval except the last the controller returns `{sufficient,next_subquery,reason}`; sufficient stops; otherwise the subquery is routed to the first unqueried source. **Controller failure after one repair stops retrieval and generates from the accumulated evidence** (verified to be the revision-2 addendum rule; tested). Invalid classifier output → B (`fallback='single_step'`).
* **AR-02** — `cross-encoder/ms-marco-MiniLM-L-6-v2` @ `233902d2…` scores (query, rendered evidence); Platt-calibrated; GOOD stops, AMBIGUOUS adds the highest-priority unqueried source, BAD adds all remaining in T→G→S order; ≤2 correction rounds (⚑5); evaluator failure → AMBIGUOUS; no web, no strip refinement.
* **AR-03** — exact Phase 1D `AgentAction` schema, one tool per iteration, cumulative evidence, generator candidate each iteration, strict validator/commentor JSON, forced feedback then termination on repeated no-evidence actions, `INSUFFICIENT_EVIDENCE` after a rejected iteration 4, T=4. The validator never receives gold; the commentor receives only query, last action and validator result.

All five share: identical tools, evidence memory, fixed context, final generator, answer parser, per-query seed.

## 3. Engineering defaults (documented, no research-meaning change)

Fixed 8,000 chars/source; queried-but-empty sources keep an empty labelled section; structured tool grammar documented in the Agent prompt; Graph entities appended to the query string (the frozen B2 accepts a query only; relations are logged but cannot strengthen it); `INSUFFICIENT_EVIDENCE` is recorded as a status and answered as the empty paper set; stop → generate without validator; unrepairable validator → reject with `validator_schema_failure`; unrepairable commentor → the loop-guard feedback string; AR-02 still generates an answer when the final state is BAD (status `insufficient_evidence` recorded).

## 4. Data discipline

* Partition: `documentation/phase9/partition/ar01_partition.json` — pool 8,049 (7,993 official-synthetic + 56 generated train), SHA-256(query_id) % 100 < 10 ⇒ dev. **7,302 train / 747 dev.** Four of the 14 generated families straddle train/dev (⚑3, reported as a limitation).
* Validation (including the 56-query primary cohort), official validation, test and human-test are never read for training, early stopping, calibration or thresholds. Labels use the retrieval-only oracle on the train split only; Platt/thresholds use the dev partition only (queries with empty gold excluded).
* Retrieval for labelling/calibration reuses the unchanged B1/B2/B3 functions through durable shard workers (`scripts/phase9_retrieve_pool.py`): train queries need only the router's first source; dev queries all three.
* Oracle source sets come from the verified modality labels and are used only in `analysis.py`.

## 5. Tests

`tests/test_phase9_foundations.py` (router, partition, evidence, durable LLM incl. 429/resume/admission, strict controllers), `tests/test_phase9_policies.py` (AR-B0/B1; AR-01 A/B/C, invalid classifier, max 3, sufficient stop, **subquery-failure stop rule**; AR-02 GOOD/AMBIGUOUS/BAD, ≤2 rounds, evaluator failure, grid and tie-breaks, Platt determinism; AR-03 accept, reject→comment→accept, one tool/iteration, T=4, loop guard, JSON repair and repair failure, stop action; identical downstream stack), `tests/test_phase9_analysis.py` (hand-computed metric definitions, sign-flip exactness, Holm, Pareto, failure taxonomy). Offline fakes only: no store, model or API.
