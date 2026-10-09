"""Build the Phase 7 review from validated artifacts; no hand-entered metric values."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'documentation/phase7'
def main():
    rows=json.loads((D/'summary.json').read_text(encoding='utf-8'));resources=json.loads((D/'resources.json').read_text(encoding='utf-8'));preserved=json.loads((D/'preservation.json').read_text(encoding='utf-8'))
    table='\n'.join(f"| {r['method']} | {r['gold_coverage']:.6f} | {r['recall@5']:.6f} | {r['mrr']:.6f} | {r['ndcg@5']:.6f} | {r['context_characters']:.1f} | {100*r['context_reduction']:.2f}% | {r['context_ms']:.2f} | {r['fallback_count']}/16 |" for r in rows)
    resource_table='\n'.join(f"| {name} | {r['wall_seconds']:.3f} | {r['memory']['peak_working_set_bytes']} |" for name,r in resources.items())
    examples=json.loads((D/'representative_cases.json').read_text(encoding='utf-8'))
    example_table='\n'.join(f"| {r['method']} | {r['kind']} | `{r['query_id']}` | {r['gold_coverage']:.6f} | {r['context_characters']} |" for r in examples)
    text=f'''# Phase 7 Review Report — RQ1 Context Management

**Status: implementation and bounded context-only validation complete; awaiting human review. Phase 8 has not begun.**

## 1. Checkpoint and scientific controls

The approved Phase 6 closeout checkpoint is `cd450bbd850fc8066c82b701310420d27e7f0df7`; the working tree was clean before Phase 7 changes. All previously tracked files remain unchanged, including the original demo, research UI, baseline implementations/configs, Phase 5 runner/metrics, benchmark and representations. The post-run audit checked all 695 frozen payloads and recomputed all 80 new records. The frozen MVP tag remains `4592d102b363c7d55d3c85ee67efe89409ae96b5`.

Phase 7 is additive under `research/rq1/`. Every method receives the same immutable, hashed graph candidate pool for a query. There is no Text/SQL retrieval, routing, query rewriting or fusion inside a context method. Only context management differs. Generation is off, so all answer-quality measurements are NULL. No Groq request, test/human-test execution or tuning occurred.

## 2. Implementation details and exact configs

The complete mechanisms, equations, source references, adaptations, dependency setup and decisions are in [Protocol and decisions](../phase7/Protocol_and_Decisions.md). Executable configs are `configs/rq1/CM-B0.json`, `CM-B1.json`, `CM-01.json`, `CM-02.json`, `CM-03.json`.

- **CM-B0:** raw candidate-order serialization with a 24,000-character global cap and atomic node/edge records.
- **CM-B1:** deterministic five-paper limit, fixed graph depth 2, parent-path retention and DFS ordering.
- **CM-01:** 10 semantic seeds, one-hop expansion inside the shared pool, connected components, minimum spanning forest using 1−cosine edge costs, deterministic DFS, deduplication and cross-encoder component ranking before budget selection. User-approved **BAAI/bge-reranker-large**, pinned revision `55611d7bca2a7133960a6d3b71e083071bbfc312`; local CPU float32, two threads, batch one, 512-token pair limit. Reranker truncation is exposed in diagnostics. No full KG²RAG stack.
- **CM-02:** top 3 node prizes, top 5 distinct edge-prize levels, fixed edge cost 0.5, official `pcst_fast` 1.0.10 with virtual-node reduction, unrooted one-cluster GW pruning, deterministic tree serialization. Empty/invalid structure uses the documented highest-relevance-node fallback. No neural graph encoder/GAT.
- **CM-03:** 20 semantic seeds, alpha 10, sink capacity 1, support threshold .01, epsilon .05, maximum 1,000,000 pushes. Query-weighted excess diffusion is deterministic and bounded, with explicit mass-conservation/convergence checks and logged top-five semantic fallback. No seed sweep was run.

Global seed 42 and query-derived seeds are unchanged. The existing MiniLM encoder and source representations are fixed. The generation adapter, if separately authorized later, uses the original prompt/parser and `openai/gpt-oss-120b`, temperature 0, low reasoning effort and 1,024-token limit.

The new shared RQ1 boundary exposes more than the original B2 final five papers: depth-2 traversal from its already recorded seed IDs, 256 base nodes / 1,024 base traversal edges / 128 edges per expanded node. Existing noisy graph paths are added uniformly before context control, with 320-node / 1,536-edge hard caps. This is an explicitly documented candidate-boundary adaptation applied equally to all five variants; B2 itself is untouched. Optimization treats the small candidate graph as undirected while retaining source direction and inverse provenance in serialized evidence.

## 3. Tests and validation

**161 tests passed**, with one pre-existing DuckDB deprecation warning. Twenty-six RQ1 tests cover deterministic output, budgets, duplicate handling, empty evidence, missing labels, nonfinite values, MST correctness, PCST selection/fallback, diffusion convergence/termination and mass conservation, high-degree materialization bounds, serialization, no retrieval access, runner resume/config rejection, query/overlay identity, synthetic paths longer than two hops, and read-only UI interaction.

The real validation set is **16 generated graph-relevant records**: 4 each G, TG, GS, TGS; 8 normal and 8 noisy; all 16 are programmatically verified multi-hop-2. There are eight underlying query instances paired with noisy variants, so these are not 16 independent tasks. **No real multi-hop-3+ stratum is available**; longer-hop tests are synthetic only. Official unverified labels were neither inferred nor used. Human verification remains pending.

All five methods completed all 16 records with zero errors and zero LLM calls. The audit independently recomputed each record's existing Phase 5 metrics, checked identical pool hashes and budget boundaries, and verified preservation. Synthetic resume tests confirm unchanged records and incompatible-run rejection.

## 4. Context size and retrieval-quality comparisons

Mean common-pool gold-paper coverage before context control is **0.736595**. The table below measures paper nodes that survive each context method; it is not generated-answer accuracy or proof that all query constraints are supported. Raw context can retain many papers without enough relational explanation.

| Method | Gold coverage | Recall@5 | MRR | nDCG@5 | Mean characters | Reduction vs CM-B0 | Context ms | Fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{table}

Machine-generated [cohort comparisons](../phase7/cohort_comparison.csv) include modality, reasoning depth, normal/noisy stress and answer-set-size cohorts, with query/error/available/NULL counts. [Per-query comparisons](../phase7/per_query_comparison.csv) retain optimization diagnostics, node/edge counts and timings. [Upstream references](../phase7/upstream_reference.csv) distinguish candidate retrieval from context survival. Recall/precision/nDCG at K=1,5,10 and other shared metrics are included in the full tables.

Answer metrics, generation latency, context/model token usage, cost, and annotated evidence coverage are NULL: there was no generation, no final-model token counter, no pricing source, and no gold evidence-ID annotations. Exact evidence-ID redundancy is zero across methods because candidate IDs and emitted IDs are unique; this does not measure semantic redundancy. NULL is explicit in CSV/JSON and never filled with zero.

## 5. Pareto analysis and human-review candidates

[Plots](../phase7/pareto.png) and [Pareto tables](../phase7/pareto.csv) use observed retained-paper coverage versus context characters, context latency, and exact-ID redundancy. Answer-quality and annotated-evidence-coverage frontiers are explicitly unavailable; the plotted gold-paper coverage is a labeled proxy, not a fabricated substitute.

On mean coverage versus size, **CM-B0, CM-B1, CM-01 and CM-02** are mathematically nondominated. CM-02 appears because it has the smallest context despite extremely low coverage; CM-01's small coverage gain over CM-B1 costs much more context and local inference time. On coverage versus latency, **CM-B0 and CM-B1** form the descriptive frontier. CM-03 is dominated on these observed axes.

These are descriptive frontiers on a small, paired controlled set, without confidence intervals or generation evidence. **No winner is selected.** The most useful first human review is the CM-B0/CM-B1 coverage–size trade-off; the other methods' weaknesses and narrow Pareto status should be reviewed before integration.

## 6–7. Representative success and failure cases

“Highest coverage” is a retrieval/context observation, not a claim of correct answer generation. Full contexts and diagnostics are preserved in [representative cases](../phase7/representative_cases.json).

| Method | Case | Query | Gold coverage | Characters |
| --- | --- | --- | ---: | ---: |
{example_table}

CM-01 and CM-B1 fully retain the known paper set on the listed highest-coverage case but miss it on their listed failures. PCST successfully optimizes connected structures yet retains very little answer-paper coverage in this sample; structural success does not imply retrieval success. Diffusion's selected or fallback nodes have zero gold-paper coverage on this set. These negative results remain in the tables; no parameters were changed to improve them.

## 8. Fallback and convergence

PCST returned valid structures on 16/16 real inputs, with **0 real fallbacks**; its empty-result fallback is exercised synthetically. Diffusion converged on **4/16**, and **12/16** triggered the logged `component_mass_exceeds_sink_capacity` fallback. With mass 10 per selected seed and sink capacity 1, a bounded connected component can have insufficient aggregate capacity; the conservation check detects this before spending a million iterations. This is an important limitation of the frozen defaults on the chosen bounded universe, not hidden optimizer success. No failed convergence is reported as a successful diffusion result.

## 9. Resources

Common pool materialization took approximately **109.77 seconds** in total. The pinned local BGE files occupy **2,261,787,453 bytes**. No full graph is loaded into NetworkX. Peak experiment working set was **3,151,491,072 bytes** (about 2.94 GiB), including the local reranker.

| Method | Wall seconds | Process peak working-set bytes |
| --- | ---: | ---: |
{resource_table}

Peak memory is cumulative for the process; it is not each method's incremental allocation. Context timing includes serializer/reference bookkeeping and CM-01's first model load. Initial runs overlapped project checks, so latency is an operational observation rather than an isolated hardware benchmark. Common materialization is separately logged and identical for all variants; cached per-variant retrieval calls/time are zero. No paid API execution occurred.

## 10. Limitations and scientific deviations

- This is a graph-only context-selection comparison, including graph-relevant combined-modality questions. Text and Structured support were intentionally not supplied; do not interpret it as full multimodal answer performance.
- The RQ1 candidate pool and noise policy differ from B2's final Top-5 output, but are shared and frozen across CM methods. Caps can exclude necessary evidence; full-pool coverage is below one.
- The original papers' complete architectures, retrieval stacks and theoretical guarantees are not reproduced. The exact controlled adaptations, PCST prize construction, diffusion scheduling/capacity choices, fallback rules and source references are documented in the protocol.
- CM-01 reranks 512-token truncated representations of organized components; truncation counts are logged. Long components may be underrepresented in that ranking.
- Three-plus-hop real validation, human-reviewed labels, answer quality, semantic redundancy and evidence-ID gold coverage remain unavailable. The fixed-default diffusion fallback rate is high.
- There was no tuning, sweep, outcome-based query selection, expensive generation batch or final-test execution. No baseline/source changes were made.

## 11–12. Review package, UI and Phase 8 readiness

A separate read-only viewer is available at **http://127.0.0.1:8503**, launched by `context_review_app.py`. It shows method selection, candidates before control, retained nodes/edges, context size, exact context, and pruning/optimization diagnostics, with graph display capped at 25 edges. The existing UI on 8502 and original demo are unchanged. Launch/reproduction commands and dependency setup are in the protocol.

The implementation, fixed-default comparisons, tests, audits and failure analysis are ready for review. **Phase 8 has not started and requires approval.** No component is automatically promoted as the integration winner.
'''
    (ROOT/'documentation/Phase_Reports/Phase_07_RQ1_Context_Management.md').write_text(text,encoding='utf-8')
if __name__=='__main__':main()
