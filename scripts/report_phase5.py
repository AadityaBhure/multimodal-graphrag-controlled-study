"""Assemble the Phase 5 review report from saved tests, audits and raw results."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.evaluation.benchmark import digest,read_json
from research.experiments.runner import write

if __name__=='__main__':
    docs=ROOT/'documentation/phase5'
    preservation=read_json(docs/'preservation.json')
    resources=read_json(docs/'sample_resources.json')
    environment=read_json(docs/'environment.json')
    samples=[]
    for name in ('sample_experiment_v3','validation_smoke_v3'):
        folder=docs/name
        files=[p for p in folder.rglob('*') if p.is_file()]
        manifest=read_json(folder/'manifest.json')
        status=read_json(folder/'status.json')
        samples.append({'directory':name,'files_including_lock':len(files),'bytes_including_lock':sum(p.stat().st_size for p in files),
                        'experiment_id':manifest['experiment_id'],**status})
    write(docs/'sample_inventory.json',samples)
    table='\n'.join(f"| `{s['directory']}` | {s['completed_queries']} | {s['errors']} | {s['files_including_lock']} | {s['bytes_including_lock']:,} |" for s in samples)
    totals=sum(g['bytes'] for g in preservation['groups'].values())
    report=f'''# Phase Review Report

PHASE: 5 — Evaluation Harness and Experiment Runner

STATUS: **PASS — infrastructure implemented and validated; stopped for approval before Phase 6.**

The approved Phase 4 checkpoint is `262c4d1636b7b3023d7d8863eb7105a4354513a1`. The working tree was confirmed clean immediately afterward. Phase 5 changes remain available for review as uncommitted additions plus the appended decision log. The frozen `baseline-mvp-v1` tag still resolves to `4592d102b363c7d55d3c85ee67efe89409ae96b5`.

## 1. Implemented metrics and exact behavior

The benchmark answer type is `paper_set`; all set comparisons use the original integer STaRK IDs. Let P be the deduplicated predicted answer set, G the gold set and H = |P intersection G|. Missing/unparseable output is `None`, distinct from a valid empty predicted set. A failed system produces NULL answer metrics and an explicit error, never a successful unanswerable result.

| Metric | Formula and edge cases |
| --- | --- |
| Set accuracy | 1 if P = G, otherwise 0. |
| Exact Match | Exact equality of normalized paper-ID sets; equivalent to set accuracy for this benchmark. No unsupported text-reference exact-match score is invented. |
| Answer precision | H / |P| for nonempty P. If P is empty: 1 only if G is also empty, else 0. |
| Answer recall | H / |G| for nonempty G. If G is empty: 1 only if P is also empty, else 0. |
| Answer F1 | 2PR/(P+R); 0 when P+R = 0. Both empty gives 1; exactly one empty gives 0. |
| Answerability correctness | 1 if bool(P) = bool(G), otherwise 0. Missing prediction is NULL. |
| Recall@K | Number of relevant IDs in the first K distinct ranked paper IDs divided by |G|. |
| Precision@K | Relevant IDs in first K distinct positions divided by K, including when fewer than K candidates were returned. |
| MRR | Reciprocal rank of first relevant paper, or 0 if none; computed across the full returned ranking. |
| nDCG@K | Binary DCG = sum of relevance/log2(rank+1), divided by ideal DCG with min(K, |G|) relevant IDs. |
| Gold coverage | Fraction of gold paper IDs present anywhere in the distinct ranking. |
| Evidence coverage | Fraction of explicit gold evidence IDs retrieved. No evidence annotation or an empty required-evidence target gives NULL. Paper answers are not reinterpreted as proof/evidence annotations. |
| Context characters | Python Unicode character count of the supplied context; NULL when context is unobserved, 0 for measured empty context. |
| Context tokens | Adapter-measured count only with an identified tokenizer. No character-to-token approximation. |
| Evidence retained | Distinct retained evidence IDs intersect distinct retrieved IDs, divided by number of distinct retrieved IDs. Empty/unknown denominator gives NULL. |
| Redundancy | 1 - distinct retained evidence IDs / retained evidence ID occurrences; observed empty sequence gives 0, missing sequence gives NULL. This measures exact ID repetition, not semantic overlap. |
| Context reduction | 1 - current character count / positive comparable baseline character count. Baseline identity is required. NULL without it; negative values explicitly indicate expansion. |
| Retrieval/generation latency | Nonnegative milliseconds reported by the system adapter, or NULL if not measured. |
| Total latency | Runner wall-clock elapsed milliseconds around input preparation, system execution and output validation; excludes initial loading, scoring and artifact writes. |
| Calls/tokens | Nullable nonnegative retrieval, tool and LLM call counts; input/output tokens require measurement-source identity. Zero only when explicitly observed. |
| Estimated cost | (input_tokens * input_price_per_million + output_tokens * output_price_per_million) / 1,000,000. Requires both measured token counts and explicit source, currency, prices and matching single model ID. Otherwise NULL. |

Ranking duplicates are removed after their first occurrence before cutoff/rank computation. With nonempty G, an observed empty ranking gives zero retrieval scores. Missing ranking or empty G gives NULL for all retrieval metrics, because a relevant-item denominator/ideal ranking is unavailable. Missing evidence is distinguished from an observed empty evidence list: explicit nonempty evidence targets yield NULL for the former and zero coverage for the latter. Identical duplicate evidence objects are retained for audit; conflicting content under one evidence ID is rejected.

Agent/fusion metric slots are always NULL in this phase: source-selection accuracy, unnecessary retrieval rate, stopping accuracy, fusion coverage, entity-alignment correctness and conflict handling. `AgentFusionAnnotations` supplies nullable future evaluation targets; it implements no algorithm or inferred label. The roadmap's answer relevance and faithfulness slots are also NULL because no supported semantic judge was specified.

## 2. Experiment-record schema

`RunRecord.schema.json` is the machine-readable strict schema. Each record contains: schema version; deterministic experiment ID; UTC-aware timestamp; query ID; split; source type; verified/unverified modality and hop labels plus original human-review status; stress conditions; system/config IDs and config hash; model IDs and embedding model; global/per-query seeds; retrieval parameters; evidence IDs; final answer and parsed answer IDs; gold IDs; complete SystemOutput (ranking, evidence content/payload/provenance, context and measurements); nullable metric map; total latency; token/call/substage observations; typed errors; and provenance.

Provenance includes dataset and benchmark versions, benchmark/representation manifest hashes, query hash, original source annotations, Git checkpoint plus exact research source hashes, Python/package versions, seed controls, pricing source/config, release attestation hash and optional context/fusion/agentic method identifiers. Saved config contains the complete declared controls. `RunEvent.schema.json` validates timestamped query lifecycle events. Unknown fields, non-finite metric values, negative counts and invalid identifiers are rejected. Phase 1 contracts remain unchanged and import-compatible.

## 3. Runner lifecycle

1. Load an explicitly named duplicate-key-checked YAML/JSON config; require matching system ID/version.
2. Verify frozen split hashes and schema; validate selection and unique IDs; check source representation-manifest binding when present.
3. For paper-test mode, enforce the separate release gate before creating the experiment directory.
4. Hash configuration, benchmark, representation, dataset version, query selection, code/packages, system fingerprint and release into the experiment ID. Acquire an exclusive process lock; create or exactly compare the manifest.
5. Seed Python and NumPy globally and per query. Validate completed records; execute only missing queries. Systems receive question, ID, seed and sanitized overlay, never gold or modality/hop labels.
6. Record start/pending state, call the common interface, capture evidence/context/answer/measurements, score applicable metrics and atomically persist one result. Exceptions become typed terminal error records with unavailable metrics NULL. Interruptions remain resumable.
7. Validate results and rebuild JSONL/events, status and aggregate JSON/CSV exclusively from raw per-query files. Check loaded split/benchmark hashes again on successful completion.

Only two synthetic systems are registered in the CLI. No B1/B2/B3/B4, RQ methods, full graph loading, model download, embedding build, retrieval execution or LLM experiment was added. Noise and conflict injections are separate serialized evaluation inputs; immutable canonical stores remain unchanged.

## 4. Resume and reproducibility

The same declared run has the same ID/config hash. Query seeds are derived from global seed and query ID, so resumed order does not change random streams. Seed logs explicitly note that Python process hash seed, remote providers, hardware and unregistered libraries are not guaranteed deterministic. Measured wall-clock timings and timestamps are naturally variable.

Each authoritative query/event file is flushed and atomically promoted from a same-directory temporary file. OS locking prevents concurrent writers and releases on process exit. Resume skips completed query records, recovers a pending interrupted query, and recognizes a committed result whose cleanup was interrupted. Derived JSONL can be rebuilt after a torn/incomplete export. Incompatible existing experiment manifests and nonempty unowned directories are refused, not overwritten. Terminal errors are not silently retried; a deliberate retry requires a new config/output. Power-loss durability ultimately depends on the filesystem/device, and an interrupted external call may have executed before its result was durably saved.

Optional immutable RetrievalBundle caching binds query content, source representation, retriever ID/version, parameters and seed. Existing cache entries cannot be replaced with different evidence. It is infrastructure for later fixed-evidence comparisons and is not used to invent baseline retrieval in this phase.

## 5. Aggregation and cohort rules

Macro means use available per-query values only, accompanied by total query count, available count, NULL count and error count. NULLs never become zeros. Tables expose `run_complete`; status records expected/completed queries and an explicit INCOMPLETE marker. A completed run may still contain errors, visibly counted.

Cohorts include overall; official_overall (official synthetic plus retained official human); separate official_synthetic, generated and official_human source groups; generated_controlled; human_test; split; verified modality; verified hop complexity; normal/noisy/conflict/unanswerable stress; source-by-modality and split-by-source. Stress groups can overlap if the contract carries multiple stress flags. Paired generated variants remain correlated; no independent-sample significance claims are made.

All **13,404 official records remain under modality/unverified and hop/unverified**. Generated labels mean programmatically verified construction labels, not completed human review. Review/export corrections never silently change frozen annotations. Mixed experiment IDs, config hashes, dataset/benchmark versions, representation/benchmark hashes and duplicate query IDs are rejected before producing aggregate tables.

## 6. Human-review/release gating

Development mode permits train/validation only. Paper-test mode permits test/human_test only and requires separate `ReleaseMetadata`: exact benchmark-manifest SHA-256 and test-content freeze ID; released status; attributed release operator; explicit leakage adjudication; and one attributed, timestamped passing decision with reason for every required query. Both splits are required regardless of which is being executed: **2,720 test + 81 human-test = 2,801 reviews**. Missing, duplicate, incomplete, mismatched or non-passing metadata is refused. The gate is rechecked on resume.

`prepare_experiment_release.py` consumes Phase 4 browser decision exports, validates complete coverage and writes a new separate release artifact. It never creates review decisions or edits benchmark files. The frozen browser export carries the benchmark version, so an explicit release operator attests its binding to the exact current review package. This is an auditable human attestation, not identity authentication or cryptographic proof of review. Validation reviews remain part of Phase 4's review package; the final-run gate specifically enforces the user-required 100% test/human-test coverage and leakage approval.

The **real benchmark is still blocked**. No actual human approvals, annotation repairs, release artifacts or real test executions were fabricated. Positive gate tests use tiny synthetic-only records.

## 7. Tests and hand-verified examples

Final full suite: **105 passed, 1 existing warning**, including 21 new Phase 5 tests. The warning is the frozen Phase 3 DuckDB `fetch_record_batch` deprecation; that implementation was preserved. See `documentation/phase5/pytest.txt`.

- P = [1,2,2], G = [2,3,4]: precision 1/2, recall 1/3, F1 0.4, exact/set accuracy 0, answerability 1.
- P = [], G = []: all answer scores 1. Exactly one empty: all answer scores 0. Missing prediction: all answer scores NULL.
- Ranking [9,2,2,1], G = [1,2,3]: distinct ranking [9,2,1], MRR 0.5, Recall@3 = Precision@3 = 2/3, Precision@5 = 0.4, nDCG@3 = 0.5307212739772434.
- Context `abcd`, retrieved [a,b,b], retained [a,a], identified count 2 tokens, baseline 8 characters: retained coverage 0.5, redundancy 0.5, reduction 0.5.
- Explicit synthetic rates 2/4 per million, 100 input/50 output tokens: cost 0.0004; without explicit pricing or measured usage it is NULL.

Integration tests cover strict record/log schemas, unknown/non-finite values, malformed configs, deterministic independent-run identity and retrieval scores, byte-identical resume, interruption and partial markers, terminal errors without secret exception leakage, committed-result recovery, locking, config/system-fingerprint mismatch, cache immutability, cohort NULL counts, mixed-version rejection, release export/gate failures, both stress injections, checksum tampering, source preservation and unobserved versus empty evidence.

## 8. Sample synthetic experiment artifacts

The current review examples use the final code/schema:

| Directory under documentation/phase5 | Queries | Errors | Files including lock | Bytes including lock |
| --- | ---: | ---: | ---: | ---: |
{table}

Each directory includes manifest, raw records/events, JSONL, aggregate CSV/JSON and status. The five-query example uses fixed prewritten evidence/answers with hand-checkable outcomes. The 57-query validation smoke covers all 56 real generated validation variants plus one official synthetic query, using a fixed empty response with no retrieval. These are **infrastructure artifacts, not scientific baseline results**. All real stress inputs were parsed; no gold is passed to systems.

Tiny fixture benchmark and response files are in `tests/fixtures/evaluation`. Named configs are `configs/phase5-scripted.json` and `configs/phase5-validation-smoke.json`. Earlier development samples are preserved under `documentation/phase5/development_runs`; their recorded code hashes identify their earlier implementations. Current experiment IDs are `{samples[0]['experiment_id']}` and `{samples[1]['experiment_id']}`.

## 9. Resource usage and preservation

Final sample creation plus immediate fixture resume: {resources['elapsed_seconds']:.3f} seconds; peak working set {resources['resources']['peak_working_set_bytes']:,} bytes ({resources['resources']['peak_working_set_bytes']/2**20:.2f} MiB). Zero LLM calls, zero retrieval calls, no measured billed tokens or costs. Process memory is for the sample process, not an invented whole-session peak. The full-suite wall time is recorded in pytest.txt; full-suite peak memory was not instrumented.

Final read-only preservation audit: {preservation['elapsed_seconds']:.3f} seconds; peak {preservation['resources']['peak_working_set_bytes']:,} bytes. **695 payload files / {totals:,} bytes** checked: 15 raw files (2,620,778,656 bytes), 358 representation files (4,117,405,659 bytes), 322 benchmark payload files (427,331,862 bytes), plus their manifest bindings. Before/after manifest hashes agree. All 54 frozen baseline Git files and four original storage files match. Original 84 human records remain in the unchanged source preservation package; the primary human-test split remains 81.

Environment: project Python 3.12.14; {environment['preserved_package_pins']} Phase 3 package pins unchanged; zero installs. `pip check`: {environment['pip_check']}. About {preservation['free_disk_bytes']/2**30:.2f} GiB free disk was observed at audit. No full graph, FAISS index or model was loaded by the Phase 5 runs.

## 10. Known limitations

- Real paper-quality evaluation awaits actual complete test/human-test review and release attestation. Official semantic gold and modality/hop annotations were not repaired.
- Actual benchmark gold is a paper answer set. A universal typed gold-evidence-ID annotation is unavailable, so evidence coverage remains NULL for real records; answer-paper retrieval coverage is separately computed when ranking exists. Construction witness paths are not silently promoted into exhaustive evidence gold.
- Exact Match is set equality for this paper-set benchmark; semantic answer relevance, groundedness and agent/fusion judging remain unsupported NULL slots.
- Substage latencies, calls and tokens rely on explicit adapter measurements. The runner measures total elapsed time independently; it cannot infer remote provider usage. Pricing currently supports one explicitly identified billed model per run.
- Context redundancy detects repeated evidence IDs, not semantic redundancy. Token counts and comparable-baseline claims carry source identities and depend on adapter correctness.
- Resume provides durable query-level results and local concurrency control, not transactional exactly-once execution of external paid services. Hard power loss and nondeterministic remote/hardware behavior are outside the guarantee.
- The runner materializes selected query records and aggregate records in memory. The audited 13,571-query benchmark is small relative to the graph, but arbitrary huge evidence payloads or much larger benchmarks would require streaming aggregation/bounded payload policy. Current measured sample peak is reported rather than extrapolated.
- The release process is an attributed audit workflow, not cryptographic reviewer authentication. Stress application inside a real retrieval pipeline and concrete algorithm adapters belong to later approved phases.

## 11. Phase 6 readiness and stop gate

Shared interfaces, nullable metric contracts, deterministic runner, immutable evidence-cache support, safe resume, aggregate validation, review-release gating, fixture data, machine schemas, test evidence and operating instructions are ready for Phase 6 baseline adapters. Development/validation can proceed after approval; real test reporting remains separately gated.

**Phase 5 stops here. Phase 6, B1–B4, RQ1/RQ2/RQ3 methods and expensive LLM experiments have not begun.**
'''
    (ROOT/'documentation/Phase_Reports/Phase_05_Evaluation_Harness.md').write_text(report,encoding='utf-8')
    files=[]
    paths=list((ROOT/'research/evaluation').glob('*.py'))+list((ROOT/'research/experiments').glob('*.py'))+list((ROOT/'tests/fixtures/evaluation').rglob('*'))+list(docs.rglob('*'))
    paths += [ROOT/'tests/test_evaluation.py', ROOT/'documentation/Phase_Reports/Phase_05_Evaluation_Harness.md',ROOT/'documentation/Research_Decision_Log.md']
    paths += list((ROOT/'scripts').glob('*phase5*.py'))+[ROOT/'scripts/run_experiment.py',ROOT/'scripts/prepare_experiment_release.py']+list((ROOT/'configs').glob('phase5*'))
    for p in sorted(set(paths)):
        if p.is_file() and p.name!='file_manifest.json' and p.suffix not in ('.lock','.tmp'):
            files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)})
    write(docs/'file_manifest.json',{'phase':5,'files':files,'total_bytes':sum(f['bytes'] for f in files)})
    print('Phase 5 review report and file manifest generated:',len(files),'files')
