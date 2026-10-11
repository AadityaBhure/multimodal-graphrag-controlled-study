# Phase 9 pre-implementation review — missing Phase 1D specification

Date: 11 October 2026 (Asia/Calcutta).

**Stopped before controller implementation, as explicitly requested.** No Phase 9 experiment, training, calibration, model download or API call has been performed. No Phase 7/8 method, result or configuration was changed. Phase 10 has not begun.

## Checkpoint and preservation

Approved Phase 8 checkpoint: **`18b32f069618ac6918505b704e86df4ab5e860b2`**. The working tree was confirmed clean immediately afterward, before adding this report and the preservation record.

[Pre-implementation preservation audit](../phase9/preimplementation_preservation.json): PASS. Verified all 695 raw/representation/benchmark payloads; the frozen MVP tag and 54 baseline files plus four original storage files; 338 Phase 7 review files; 113 Phase 8 v2 review-package files; and 550 original Phase 8 files. Counts describe overlapping verification groups, not disjoint artifact totals. Historical positive, negative and inconclusive results remain unchanged.

## Specification search

`Phase1D_Exact_Implementation_Specifications_9_Methods.docx` was **not found** in the repository or documentation directory. Searches included hidden repository paths, Phase1D/Phase_1D filename variants, and textual references in documentation/configuration/research files. The existing `Codex_Full_Project_Implementation_Roadmap.docx` was inspected directly; it contains high-level Phase 9 adaptations, but not the exact specification filename or Platt-calibration details. `configs/rq3/README.md` still reserves configurations for the implementation phase, and the agentic modules are placeholders.

No search of unrelated personal directories was performed. The separate planning artifact may exist outside this repository, as the user indicated.

## Settings that are already frozen

| System | Available explicit specification |
|---|---|
| AR-B0 | Text → Graph → Structured → Stop, always all three |
| AR-B1 | Deterministic query-feature rules; no LLM or learned controller; log fired rules, order and stop reason |
| AR-01 | `t5-base`; A = no retrieval, B = one retrieval, C = multi-step; maximum three retrieval steps; training labels from train/development only |
| AR-02 | MiniLM cross-encoder + Platt calibration; GOOD stops, AMBIGUOUS retrieves one next source, BAD retrieves remaining sources; at most two corrective rounds; no public web or strip compression |
| AR-03 | Strict JSON actions from Text/Graph/Structured/STOP; one retrieval tool per iteration; T=4; validator/commentor; repeated-action and loop guards; read-only validated Structured tool |

All systems must delegate to unchanged B1/B2/B3 retrievers and share simple deterministic source-separated downstream serialization. The primary validation cohort is all 56 generated validation queries. Labels/gold are evaluator-only. No test/human-test execution or Phase 10 work is authorized here.

The Phase 9 request supplies `openai/gpt-oss-120b`, temperature zero and low reasoning effort as the AR-03 live-controller default unless the missing Phase 1D document explicitly specifies another controller model. This is not authorization to invent its missing prompts or token caps.

## Exact unresolved scientific settings

| Component | Missing information to supply or freeze |
|---|---|
| AR-B1 routing | Exact query features, keyword/pattern rules, combinations, source priority/order, no-rule fallback, tie handling and stop rule. The roadmap contains no actual rule table. |
| AR-01 class-to-retrieval behavior | A/B/C meanings and maximum depth are known. Which source B uses; source choice/order for each C step; evidence feedback, early stopping and fallback behavior are not specified. No new mapping has been substituted. |
| AR-01 labels and training | Exact A/B/C label-construction procedure, eligible training/development records, handling of unanswerable cases, partition/sampling procedure and class balance. No approved classifier checkpoint or training artifact exists in the inspected repository. The training recipe, model revision, input format/length, label output format, decoding and confidence computation also need specification for a reproducible classifier. |
| AR-02 evaluator | Exact MiniLM cross-encoder model/checkpoint/revision; evaluator input representation; text/graph/structured evidence serialization for scoring; per-item versus aggregate scoring and aggregation rule; input-length policy. “MiniLM cross-encoder” alone does not identify a trained relevance evaluator. |
| AR-02 Platt calibration | Calibration examples and target-label definitions, negative sampling, approved development split, fitting procedure and parameters/artifact. The roadmap permits train/validation calibration but does not prescribe how to isolate calibration from the 56-query primary validation evaluation. No approved calibration artifact was found. |
| AR-02 thresholds and transitions | Numerical GOOD/AMBIGUOUS/BAD boundaries and inclusive/exclusive comparisons; initial source and next-source order; behavior for empty/failed/unsupported source results; precise reevaluation timing and counting of corrective rounds. The high-level transition actions are known, but these decision details are not. |
| AR-03 prompts and roles | Exact action-selection, validator and commentor prompts; whether validator/commentor are separate model calls or part of a shared response; information passed between them; decision precedence and stopping criteria. |
| AR-03 schema and guards | Exact JSON fields beyond the allowed action enum; permitted action arguments; invalid-action response policy; repeated-action handling; whether malformed/validator calls consume an iteration; terminal behavior at T=4. Hard limits and guard requirements are known, but their detailed behavior is not frozen in the available files. |
| AR-03 token/iteration accounting | Completion caps for each controller/validator/commentor role; controller input/evidence budget and accumulation policy; maximum controller calls per iteration and experiment. The final-answer generator's existing caps do not define controller caps. |

These are implementation-relevant omissions, not claims that the separate Phase 1D document necessarily omits them. Providing that document may resolve them directly. No threshold, training label, prompt, token cap or routing rule has been guessed or tuned.

## Next permitted step

Provide the separate Phase 1D document or explicitly freeze the missing settings. Reconcile that specification with the approved roadmap and current request before implementing AR-01/02/03. No controller implementation will proceed until then, per the user's latest instruction.

RQ3_IMPLEMENTATION_STATUS = NOT_STARTED_MISSING_PHASE1D_SPECIFICATION

RQ3_VALIDATION_STATUS = NOT_STARTED

PHASE_9_STATUS = BLOCKED_PENDING_FROZEN_SETTINGS

PHASE_10_READY = NO

**STOP FOR HUMAN REVIEW. DO NOT BEGIN PHASE 10.**
