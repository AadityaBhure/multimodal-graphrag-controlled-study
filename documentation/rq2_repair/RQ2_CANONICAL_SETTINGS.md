# RQ2 canonical repair — frozen settings (APPROVED 2026-10-16)

Date: 2026-10-16. Status: approved as proposed by the user on 2026-10-16 (scope option A: primary 24-bundle study only; fusion-isolation study dropped). Authority: Phase 1D §5 (paragraphs 180–299 of `compliance_repair/phase1d_extracted.txt`) > handoff §21 > this document. Only items the specification leaves open are decided here; nothing is tuned on outcomes (no RQ2 canonical output exists).

## Fixed by the specification (implemented as written)
* Cached-evidence invariant: every method receives the byte-identical frozen bundle (`documentation/phase8/bundles`, 24 verified multimodal validation queries: TG/TS/GS/TGS × 2 families × normal/noisy/conflict); no retrieval inside any method.
* CF-B0 / CF-B1: historical implementations reused unchanged (audit found no non-compliance).
* CF-01: resolution order ID → exact normalized alias → global resolver; UNALIGNED groups keyed by evidence_id; group order = max member relevance desc, source coverage desc, canonical entity ID; serialization `[ENTITY id | display_name] [TEXT] [GRAPH] [STRUCTURED] [PROVENANCE]`; retriever order within a group; complete groups first; next group's highest-ranked items only if they fit, `group_truncated=true`; fallback CF-B1 representation if no entity resolves.
* CF-02: structural = Graph + Structured, semantic = Text; dedup by evidence_id/provenance overlap; compact manifest; exactly one selector call returning `{"selected_ids":[...],"reason":"..."}`; ≤ 5 structural; invalid/duplicate IDs removed; one schema repair; fallback = relevance-score top 5 (`selector_fallback='relevance'`); semantic fill in retriever order to K_out = 10; keep all if fewer than 10 exist; budget trimming removes lowest semantic fill first, then lowest-priority structural.
* CF-03: one reasoning call per non-empty source (Text, Graph, Structured order) with only that source's evidence, JSON `{candidate_answer, supporting_evidence_ids, confidence}`, 220-token cap; static NO_EVIDENCE object for empty sources; supporting IDs validated against that source; one fusion call; source failure → ERROR_NO_EVIDENCE for that source only; fusion failure → one exact retry, then `status='error'`.
* Model for all LLM roles: `openai/gpt-oss-120b`, temperature 0, low reasoning effort, per-query seed; final answer uses the shared answer contract (`answer_ids` must be paper IDs grounded in the method's own evidence) and 1,024 cap.

## Open items — proposed frozen values
| # | Item | Proposal | Reason |
|---|---|---|---|
| S1 | Context budget unit | 24,000 characters (MAX_CONTEXT) | Phase 6 froze a 24,000-character cap; RQ1 uses the same equivalence; tokens are measured and reported. |
| S2 | GLOBAL_ENTITY_RESOLVER | Deterministic registry lookup: an ambiguous exact alias is resolved only if exactly one candidate has the evidence item's own entity type (`canonical_entities.entity_type`); otherwise UNALIGNED. No LLM. | Spec forbids free-form LLM entity invention; on the 24 bundles all 372 items already resolve by explicit ID, so this step is expected to be used 0 times (reported). |
| S3 | Entity display_name | `canonical_entities.display_name` (read-only registry) | Needed for the group header; no evidence content added. |
| S4 | CF-02 SELECTOR_INPUT_BUDGET | 5,000 tokens of manifest (o200k_harmony); candidates in input order until the next would exceed it | Keeps the selector request well inside the 8,000 TPM admission limit. |
| S5 | CF-02 manifest line | `ID | source | relevance score | first 200 characters of the item's content (single line) | provenance paper/entity IDs` | "One-line content" per spec. |
| S6 | CF-02 selector cap | 256 completion tokens; repair call 128 | Same caps as the RQ3 controllers. |
| S7 | CF-03 per-source evidence | That source's section exactly as CF-B1 serializes it (8,000 characters per source) | Identical evidence representation across methods. |
| S8 | CF-03 fusion input | The three intermediate objects plus, for each supporting evidence ID, its paper ID; the final `answer_ids` must be paper IDs of supporting evidence | "Final answer can cite only IDs present in intermediate grounded objects." |
| S9 | Prompts | Fixed wording in `research/repair/rq2_canonical/prompts.py`, versioned by hash; frozen before any call | Spec gives roles and constraints, not wording. |
| S10 | Supportability (stratification only, evaluator-side) | FULLY: every gold paper appears as an evidence item's canonical paper in the bundle; PARTIALLY: at least one does; UNSUPPORTABLE: none. Computed once before any call and frozen. | Handoff §21: classify by evidence requirements, not model outcomes; gold is used only for analysis strata, never by a method. |
| S11 | Execution | Same operational stack as RQ1 rev. 4: content+128 admission, successful-call counting, rolling 24 h ledger (190k), query-major provider order, replay-only runner | Proven in RQ1. |
| S12 | Historical CF-02 lexical selector | Kept unchanged as a historical ablation, not re-run | Two-week scope. |

## Expected Groq workload
24 bundles × (CF-B0 1 + CF-B1 1 + CF-01 1 + CF-02 2 + CF-03 up to 4) ≈ 216 calls; estimated 0.8–0.95 M tokens ≈ 4.5–5 days at 190k/day.
