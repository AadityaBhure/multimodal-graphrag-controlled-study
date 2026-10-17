# Language-model backend used for the reported results

All reported RQ1–RQ4 results were produced by one locally served model.

| Item | Value |
|---|---|
| Model | `gpt-oss:20b` (Ollama model ID `f38aa0c53da5`; 20.9 B parameters; MXFP4 quantization) |
| Server | Ollama 0.40.5, native `/api/chat`, context window 16,384 tokens |
| Hardware | NVIDIA GeForce RTX 4060 Laptop GPU (8 GB; model split ≈ 42 % GPU / 58 % CPU) |
| Request settings (all roles) | temperature 0, per-query seed, reasoning (think) level `low`, JSON output mode, completion cap 1,024 tokens (PR-12) |
| Latency recorded | model compute time reported by the server (prompt evaluation + generation; excludes model loading, thermal pauses and HTTP overhead) |
| GPU protection | before a request, at ≥ 80 °C the client pauses 10 minutes and waits until < 70 °C (never counted as latency) |

Frozen plans: `rq1_repair/execution_plan_local.json`, `phase9/execution_plan_local.json`, `rq2_repair/execution_plan_local.json`, `rq4/execution_plan_local.json`. Run outputs use the `_local` suffix. Earlier provider-backed runs (Groq) are archived in the repository and are not reported.

## Recorded notes
* **RQ3 record field.** `scripts/run_phase9.py` writes a hard-coded default `model_ids = ['openai/gpt-oss-120b']` into the RQ3 run configuration, so the RQ3 local records (`phase9/runs_local`) carry that label. The model that produced them is `gpt-oss:20b`, as shown by `phase9/execution_plan_local.json` (`model`) and by every stored request (`artifacts/phase9/llm_stages_local/stages/*`, field `payload.model`). The field is not used by any analysis. RQ1, RQ2 and RQ4 local configs record `gpt-oss:20b`.
* **RQ1 local plan hash.** After RQ1 finished, `research/repair/dispatch.py` gained the uniform local cap (PR-12). RQ1's behaviour is unchanged by it (all RQ1 calls already used 1,024), but `rq1_repair/execution_plan_local.json` no longer matches the current file hash.
