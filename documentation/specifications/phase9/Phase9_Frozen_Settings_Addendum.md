# Phase 9 Frozen Settings Addendum

Status: Frozen before Phase 9 controller implementation.
Purpose: Fill only the settings left unspecified by `Phase1D_Exact_Implementation_Specifications_9_Methods.docx`.
The Phase 1D document remains authoritative wherever it is explicit. This addendum must not modify Phase 7/8 or any frozen retriever.

## 1. Shared deterministic rule router (AR-B1 and shared use by AR-01/AR-02)

Normalize the raw query with Unicode NFKC, lowercase, and collapsed whitespace.

Source cue rules:

### Text cues
Match Text if the normalized query contains any of:
`abstract`, `title`, `text`, `content`, `phrase`, `wording`, `mention`, `mentions`, `mentioned`, `contain`, `contains`, `containing`.

### Graph cues
Match Graph if the query contains any of:
`author`, `authors`, `authored`, `written by`, `writes`, `affiliat`, `institution`, `university`, `cites`, `cited by`, `references`, `referenced by`, `topic`, `field of study`.

Exception: `citation count`, numeric citation comparisons, or phrases such as `at least N citations`, `more than N citations`, `less than N citations` are Structured cues, not Graph cues.

### Structured cues
Match Structured if the query contains a structured field/cue:
`year`, `publication year`, `date`, `rank`, `paper rank`, `citation count`, numeric `citations`, `journal`, `conference`, `venue`, `document type`, `doctype`, `before`, `after`, `between`, `at least`, `at most`, `more than`, `less than`, `greater than`, `fewer than`, `>=`, `<=`, `>`, `<`.

Router output is the set of matched sources in fixed priority:
`Text -> Graph -> Structured`.

If no cue matches, return `Text` only.

AR-B1 retrieves every source returned by this rule router, once, in that fixed order, then stops.
The rule table is frozen before Phase 9 results and must not be tuned afterward.

## 2. AR-01 Adaptive-RAG-inspired router

### 2.1 Label construction

Use only Phase 9 training material. Do not use the 56-query primary Phase 9 validation cohort, official validation, test, or human-test for classifier training or model selection.

Eligible labeling pool:
- official training split;
- generated training split.

Create a deterministic train/development partition using SHA-256 of `query_id`:
- 90% train;
- 10% development.
The partition is made before model training and persisted.

Oracle route labels:
- `A = NO_RETRIEVAL`
- `B = SINGLE_STEP`
- `C = MULTI_STEP`

For a query with an explicitly empty/unanswerable gold set, A is successful.
For an answerable query, A is unsuccessful.

B:
- use the shared rule router;
- call only its first source;
- successful iff `gold_paper_coverage == 1.0`.

C label oracle:
- retrieve up to three distinct sources;
- start with the shared rule-router order;
- after matched sources are exhausted, append unseen sources in fixed `Text -> Graph -> Structured` order;
- use the raw query unchanged for this offline label-oracle retrieval;
- successful iff accumulated `gold_paper_coverage == 1.0`.

Assign the cheapest successful route in order `A < B < C`.
If none succeeds, label C.
This deterministic retrieval-only labeling oracle is used only to create classifier labels; it is not the AR-01 inference controller.

### 2.2 T5 training

Model: `t5-base`.
Resolve once from Hugging Face, record and pin the exact revision/commit used.

Input: raw question.
Target: exactly one token/string from `A`, `B`, `C`.

Training:
- tokenizer/model from the same pinned revision;
- max source length: 256 tokens;
- max target length: 2 tokens;
- optimizer: AdamW;
- learning rate: `3e-5`;
- weight decay: `0.01`;
- seed: `42`;
- maximum epochs: `10`;
- select checkpoint with minimum development loss;
- early-stopping patience: `2` completed epochs without development-loss improvement;
- no label smoothing;
- no oversampling or synthetic class balancing;
- log class counts and imbalance.

Confidence at inference is the normalized probability over the first decoded class token A/B/C when available.

### 2.3 AR-01 inference details

A:
- zero retrieval calls.

B:
- call only the first source from the shared rule router.

C:
- maximum three retrieval calls;
- initial retrieval uses the raw query and first unqueried source from the shared router;
- after each retrieval except the last, call the fixed controller LLM to return strict JSON:
  `{"sufficient": boolean, "next_subquery": string, "reason": string}`
- controller model: `openai/gpt-oss-120b`;
- temperature `0`;
- reasoning effort `low`;
- completion cap `128`;
- evidence input is the fixed source-separated accumulated context under the common 24,000-character budget;
- if `sufficient=true`, stop early;
- otherwise route `next_subquery` with the same shared rule router and choose its first unqueried source;
- if no routed source is unqueried, choose the first unqueried source in `Text -> Graph -> Structured`;
- if controller JSON fails after the project's single deterministic schema-repair attempt, keep the original query as the next subquery and choose the next unqueried source;
- never exceed three retrieval calls.

## 3. AR-02 CRAG-inspired evaluator

### 3.1 Cross-encoder

Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`.
Resolve once, record, and pin its exact model revision.
Run locally with deterministic inference.
Score `(raw_query, EvidenceItem.content)`.
Use the model's standard pair truncation with a maximum pair length of 512 tokens.
Do not add source-specific learned transformations.

### 3.2 Platt calibration

Use only the 10% Phase 9 development partition created from the training pool above.
Do not use the 56-query primary validation cohort, official validation, test, or human-test.

Collect evidence from the unchanged B1/B2/B3 retrievers using their frozen settings.

Per evidence item target:
- `1` if its canonical paper IDs or provenance paper IDs intersect the query gold paper set;
- `0` otherwise.

Use all collected labeled evidence items; no post-hoc negative sampling.
Queries with an empty gold set are excluded from Platt fitting.

Fit a one-dimensional logistic regression mapping raw cross-encoder score to relevance probability:
- solver `lbfgs`;
- `C=1.0`;
- `class_weight="balanced"`;
- `max_iter=1000`;
- seed/random_state `42`.

Persist coefficient, intercept, training counts, model revision, data fingerprint, and calibration artifact hash.

### 3.3 GOOD / AMBIGUOUS / BAD threshold fitting

Create query-level accumulated-evidence states on the same development partition in the shared router order.

Ground-truth retrieval-quality state:
- GOOD: `gold_paper_coverage == 1.0`
- BAD: `gold_paper_coverage == 0.0`
- AMBIGUOUS: `0.0 < gold_paper_coverage < 1.0`

Exclude explicitly empty/unanswerable gold queries from threshold fitting.

Search only the frozen Phase 1D grid:
- LOWER in `{0.20,0.25,0.30,0.35,0.40}`
- UPPER in `{0.60,0.65,0.70,0.75,0.80}`
- require `LOWER < UPPER`.

Prediction rule remains the Phase 1D rule:
- if `max(p) >= UPPER`: GOOD
- elif every `p <= LOWER`: BAD
- else: AMBIGUOUS
- empty evidence: BAD.

Select the pair with highest macro-F1.
Tie-break in this exact order:
1. lower total classification error;
2. wider `UPPER-LOWER` margin;
3. lower LOWER;
4. lower UPPER.

Freeze and persist the selected thresholds before the 56-query primary Phase 9 validation run.

### 3.4 AR-02 source progression

Initial source: first source from the shared rule router.

AMBIGUOUS:
- retrieve the highest-priority unqueried source from the shared router;
- if none remains in the routed set, use the first unqueried source in `Text -> Graph -> Structured`.

BAD:
- retrieve all remaining unqueried project sources using the frozen retrievers;
- deterministic dispatch/log order is `Text -> Graph -> Structured`;
- parallel physical execution is optional, but logical call order and evidence merge order must remain deterministic.

Re-evaluate after each correction round.
Maximum two correction rounds beyond the initial retrieval.
Evaluator execution failure -> AMBIGUOUS, as already frozen in Phase 1D.
Structured unsupported/empty result is a valid empty retrieval, not an evaluator failure.

## 4. AR-03 AGENT-G-inspired prompts, schemas and limits

All controller/critic roles use:
- model `openai/gpt-oss-120b`;
- temperature `0`;
- reasoning effort `low`.

The candidate-answer Generator uses the already frozen shared final-answer prompt/parser and its existing 1,024 completion-token cap.

### 4.1 Agent prompt

System intent:
"You are a retrieval controller. Do not answer the user's question. Choose exactly one retrieval action or STOP using only the query, previous feedback, and currently retrieved evidence. Prefer the smallest next action that can resolve missing evidence. Do not invent evidence, gold labels, entities, relations, SQL, or facts. Never repeat an action that previously returned no new evidence unless the feedback explicitly requires it. Return JSON only matching AgentAction."

AgentAction schema is exactly the Phase 1D schema:
`iteration`, `source`, `retrieval_query`, `domain`, `entities`, `relations`, `structured_intent`, `reason_code`, `stop_reason`.

Completion cap: `256`.

### 4.2 Validator prompt

System intent:
"You are an evidence-grounding validator. You do not have access to benchmark gold answers. Decide only whether the candidate answer fully addresses the query and every material claim/constraint is supported by the retrieved evidence. Reject answers that use the wrong entity/relation/source, rely on missing evidence, contain unsupported claims, or depend on a structured-query failure. Return JSON only."

Schema:
`{"accept": boolean, "error_type": enum, "unsupported_claims": [string]}`

Allowed `error_type`:
`none`, `wrong_source`, `wrong_entity`, `wrong_relation`, `insufficient_evidence`, `unsupported_answer`, `structured_query_error`.

Completion cap: `256`.

### 4.3 Commentor prompt

System intent:
"You are a corrective retrieval critic. Using only the query, last AgentAction, and validator result, provide concise guidance for the next retrieval action. Do not answer the query and do not introduce new factual evidence."

Schema:
`{"feedback": string, "recommended_source": "text"|"graph"|"structured"|"none", "reason": string}`

Completion cap: `128`.

### 4.4 Schema repair

One deterministic repair call is allowed for malformed Agent, Validator, or Commentor JSON.

Repair system intent:
"Rewrite the supplied output into valid JSON matching the required schema exactly. Preserve its intended decision; do not add factual content."

Completion cap: `128`.

A successful repair does not consume an additional retrieval iteration.
If repair fails:
- the current retrieval iteration is counted;
- use the shared rule router to select the first unqueried source;
- execute at most one source tool in that iteration;
- record `schema_repair_failed=true`.

### 4.5 Evidence/control budget

Evidence memory is cumulative, but model-facing evidence uses the fixed Phase 9 source-separated serialization and the common 24,000-character context cap.
No RQ1 pruning or RQ2 fusion is allowed.

Agent sees:
- original query;
- previous feedback;
- fixed serialized accumulated evidence.

Validator sees:
- original query;
- candidate answer;
- same fixed serialized accumulated evidence.

Commentor sees only:
- original query;
- last AgentAction;
- validator result.

### 4.6 Loop normalization and termination

Normalize an action for repeat detection as:
`(source, normalized retrieval_query, sorted entities, sorted relations, normalized structured_intent)`.

Normalization: Unicode NFKC, lowercase, trim, collapse whitespace.

If the same normalized action is produced twice with no new evidence:
- force feedback: `Previous action produced no new evidence. Choose a different source/action.`

If the same normalized action is produced once more without new evidence:
- terminate with `INSUFFICIENT_EVIDENCE`.

Maximum retrieval iterations: `T=4`.

If iteration 4 ends with a rejected candidate, return `INSUFFICIENT_EVIDENCE`; do not return an unsupported partial answer.

Commentor is not called after an accepted candidate or after terminal iteration 4.

### 4.7 LLM-call accounting

Per retrieval iteration:
- Agent: one call, plus at most one repair;
- Candidate Generator: one call;
- Validator: one call, plus at most one repair;
- Commentor: one call only after rejection and only if another iteration is possible, plus at most one repair.

Do not silently retry provider failures.
Provider-rate-limit pauses/resume use the existing durable dispatch policy and do not change experiment identity or scientific settings.
All calls, repairs, tokens, finish reasons and errors are logged.

## 5. Scientific boundary

This addendum fills previously unspecified implementation details only.
It must not:
- change B1/B2/B3 retrievers;
- expose evaluator modality/gold labels to controllers;
- use official validation/test/human-test for training or calibration;
- tune settings after viewing the 56-query Phase 9 primary validation outcomes;
- modify Phase 7/8;
- begin Phase 10.

Any deviation from this addendum requires explicit human approval before implementation.
