# MMG-STaRK-MAG benchmark v1 — Phase 4 protocol

Phase 3 checkpoint: `3b34d9c234f9861455eea5fc7fd34a939f87518e`. The working tree was clean after this checkpoint, before Phase 4 implementation. The original baseline tag, 15 raw files and 358 representation artifacts remain immutable. All commands use `.\.venv\Scripts\python.exe`; no new dependencies or model calls are needed.

## What is frozen

`data/MMG_STARK_MAG/benchmark/` contains the four query splits, both original-record JSONL exports, byte-identical source CSV/split copies, construction records and deduplicated candidate sets, stress overlays, audit/statistics reports, human-review package and benchmark manifest. The manifest records query hashes and a test-content freeze ID. Content freeze does **not** mean human approval or permission to run final experiments. Paper-quality use remains blocked pending human review.

Original synthetic queries retain their audited 7,993/2,665/2,665 train/validation/test boundaries and original IDs. Official human questions retain all 84 original records; primary `human_test` contains the 81 whole queries whose answer IDs are all papers. Queries 30, 50 and 72 are excluded whole, with untouched originals, original answer IDs/types and reasons preserved. No source answer is repaired.

## Contracts and honest annotation

`BenchmarkQuery`, `Reasoning` and `Stress` extend the existing Phase 1 `Contract`. All required question, answer, split, taxonomy, evidence and provenance fields are present. IDs use namespaced query IDs plus unchanged `source_query_id`; paper IDs remain authoritative integer STaRK IDs.

Generated items have verified T/G/S/TG/TS/GS/TGS labels, recorded graph path depth and orthogonal stress flags. Hop count is the maximum required relational path length; direct text/structured predicates count as single-hop. Multiple modalities do not automatically mean multiple graph hops.

The official files do **not** supply verified modality, hop or evidence derivation annotations. Official imports therefore have `modality_class="unverified"`, empty modalities, NULL hop/multi-hop and unverified difficulty. This is a documented schema extension rather than fabricated TGS/one-hop labels. Their original gold is authoritative supplied QA, checked for identity/provenance, **not independently semantically recomputed from arbitrary natural language**. They can support overall official-source comparisons only after the required review; they must not be silently included in verified modality/hop strata.

## Generated construction and source necessity

There are two base instances for each of seven modality classes in each main split: 42 bases. Selection uses seed 42 and deterministic ordering. The system computes source candidate sets and intersections before wording. Persisted sorted candidate sets have individual SHA-256, counts and exact predicates. Each generated answer is recomputed independently during audit.

- **Text:** explicit case-insensitive abstract claims, using one clause, an OR pair, or an AND pair. Example claims concern agreement with experiments or reported calculations. The full claim condition must be absent from every graph label, including paper titles and field labels. Templates explicitly state the bounded claim criterion; they do not pretend literal matching establishes exhaustive synonym/paraphrase relevance. Human review must reject scientifically weak or misleading wording. This controlled operational definition is narrower than a general semantic retrieval benchmark.
- **Graph:** author→paper, institution→author→paper, or institution→author→paper→cited-paper paths. The anchor must have a unique source name; it must not occur in answer text. Witness edge IDs/directions remain tied to immutable CSR. Inverse rows are traversal aids, never additional source facts.
- **Structured:** parameterized year/citation, rank/venue-namespace, or date/citation predicates. Structured-only instances add precise recorded constraints to avoid enormous answer sets. NULLs never satisfy a numeric comparison and are never filled. Query wording refers to recorded values and explicitly calls venue classification a normalized namespace.
- **Combined:** exact set intersections. For each answerable multi-source item, dropping each source individually must produce a strict superset; counterexample paper IDs are saved. Redundant combinations are rejected.

No answer ID or full answer title is placed into generated wording. The general source-preserving benchmark does not use model retrieval success as truth.

## Splits and leakage scope

Construction instances and graph anchors remain in one split, including all paired stress variants. Actual split-blind operator signatures are computed from predicate structure, arity and graph path kind; template renaming cannot hide shared operator templates. Exact duplicates are rejected/flagged except explicit within-split normal/noise/conflict pairs that intentionally keep the same question and gold while changing input evidence.

The split families deliberately differ: single-claim/author/year-citation in train, OR-claim/institution/rank-namespace in validation, AND-claim/three-hop-citation/date-citation in test. This avoids template reuse but introduces a known distribution shift and associates graph depth with split. It is **not** an IID or perfectly balanced depth experiment. The controlled extension has only two base instances per class/split; stress variants are correlated, not independent extra semantic questions. Report results by source and family rather than treating 167 variants as 167 independent constructions.

The paper corpus is shared across splits (transductive retrieval); overlapping answer papers alone are not leakage. Official and generated queries are never assigned a different official split. Exact normalized-question scans cover all queries. A bounded official cross-split scan checks shared word shingles followed by token Jaccard and sequence similarity; it cannot certify absence of all semantic paraphrases. Findings, if any, are preserved and quarantined via `eligibility.json`, not fixed by modifying official records. Human reviewers must resolve semantic/template leakage beyond these checks.

## Stress overlays

- Unanswerable: preserve the valid parent question/conditions/answers; append a verified disjoint abstract claim, a disjoint coauthor requirement, or a year above the observed source maximum. Recompute and persist the empty intersection. These are controlled constructions, not retrieval-failure labels; out-of-range-year cases are deliberately simple and must be reported as such.
- Noise: frozen-vector nearest neighbors that violate the text predicate, nearby graph citation detours that violate the required path, and structured rows satisfying the first but not all filters. IDs, similarities/paths and failed conditions are recorded. Noise uses only the required modalities. One GS test noise variant is omitted because a required distractor was unavailable; no weak replacement is fabricated.
- Conflict: a structured field, graph endpoint or abstract is changed only in an explicit evaluation-input overlay. Original fact, altered payload, origin, inverse patch and expected handling are retained. Canonical evidence remains authoritative and gold unchanged. No overlay executor or evaluation runner is implemented.

## Human verification

Open `human_review/review.html` in a browser (or serve that directory locally). It contains 3,390 pending review items: all 2,720 test, all 81 human_test, and 589 validation items (533 official, a deterministic 20% sample, plus all 56 generated validation variants). No automated decision is presented as human verification. Train is not part of the mandatory package.

Each item has question, taxonomy, gold IDs/readable titles, source candidates/derivation or an explicit official-evidence gap, source-necessity rationale, stress payload, pass/reject/reason/reviewer fields and editable verified modality/hop annotations. 10,316 paper evidence records provide full source abstracts, structured records and readable author/institution/topic context. Citation lists are marked bounded previews; reviewers must consult frozen CSR for complete paths when needed.

Review decisions save to browser local storage and export separately as JSON. Export them to retain work; the benchmark JSONL and original answers are never modified. A rejected official item must be excluded/qualified through a reviewed new benchmark version, never relabeled. Before paper-quality experiments, every final test/human_test question must be manually passed, all relevant official modality/gold semantics checked, validation spot checks completed, and any leakage findings adjudicated. Full train annotation is optional; unverified annotations must remain excluded from stratified claims.

## Reproduction and phase boundaries

```powershell
.\.venv\Scripts\python.exe scripts/build_benchmark.py
.\.venv\Scripts\python.exe scripts/audit_benchmark.py
.\.venv\Scripts\python.exe scripts/prepare_benchmark_review.py
.\.venv\Scripts\python.exe scripts/check_benchmark_regeneration.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

The builder verifies an existing frozen output and refuses to overwrite corrupted files. For a complete regeneration use a separate `--output` path; the dedicated regeneration script rebuilds all artifacts in `_build/phase4/regenerated`, reruns audits and compares every byte. Physical dataset artifacts and raw sources are checked before and afterward. Regeneration requires the exact pinned local Phase 3 representations and installed environment. No remote service is called.

Phase 5 metrics/experiment runner, B1–B4 retrievers, advanced algorithms and final test experiments are not implemented. Phase 4 delivers the construction/audit/review substrate; human approval remains an explicit gate before Phase 5 and paper-quality test use.
