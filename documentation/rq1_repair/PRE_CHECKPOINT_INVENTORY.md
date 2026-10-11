# Pre-checkpoint inventory of untracked files

HEAD at inventory time: `34c85038636b1223d1664042e0ce0f0640403dd0` (= PRE_RQ1_RQ2_COMPLIANCE_REPAIR checkpoint). Machine-readable: `pre_checkpoint_inventory.json` (per-file SHA-256).

* Untracked files (after .gitignore): **82**
* To be committed: **80** (71.5 MB)
* Secret-like patterns found in any untracked file: **0**
* Already excluded by `.gitignore` (not inventoried, not committed, not deleted): `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `storage/text/*`, `storage/graph/*`.

## Excluded from the checkpoint (left untracked, not deleted)

| Path | Bytes | Reason |
|---|---:|---|
| `CLAUDE_MASTER_HANDOFF_MULTIMODAL_GRAPHRAG.md` | 53449 | Hand-off briefing for the assistant; not part of the repair implementation; commit left to the user |
| `tmp/pdfs/qafd_equations.png` | 260397 | Transient staging image (tmp/); repository policy keeps staging out of checkpoints |

## Included (grouped)

| Group | Files | Bytes |
|---|---:|---:|
| `documentation/RQ1_RQ2_Compliance_Matrix.md/` | 1 | 31163 |
| `documentation/compliance_repair/` | 6 | 144341 |
| `documentation/rq1_repair/` | 14 | 196438 |
| `documentation/rq1_repair/configs/` | 5 | 10985 |
| `documentation/rq1_repair/inputs/` | 32 | 71031859 |
| `documentation/rq1_repair/provider_preflight/` | 4 | 3368 |
| `requirements-rq-repair.txt` | 1 | 95 |
| `research/repair/` | 8 | 35525 |
| `scripts/audit_rq1_repair_local.py/` | 1 | 3889 |
| `scripts/audit_rq_compliance.py/` | 1 | 23367 |
| `scripts/prepare_rq1_repair.py/` | 1 | 5043 |
| `scripts/report_rq1_repair.py/` | 1 | 5078 |
| `scripts/run_rq1_repair.py/` | 1 | 8069 |
| `tests/test_repair_cm01.py/` | 1 | 5865 |
| `tests/test_repair_dispatch.py/` | 1 | 2725 |
| `tests/test_repair_rq1.py/` | 1 | 6655 |
| `tests/test_repair_statistics.py/` | 1 | 824 |

## Full per-file list

| Path | Type | Category | Bytes | Repair | Commit | SHA-256 |
|---|---|---|---:|:-:|:-:|---|
| `CLAUDE_MASTER_HANDOFF_MULTIMODAL_GRAPHRAG.md` | md | documentation | 53449 | N | N | `0ab9ed5d42a712fc…` |
| `documentation/RQ1_RQ2_Compliance_Matrix.md` | md | documentation | 31163 | Y | Y | `205898cb98d15268…` |
| `documentation/compliance_repair/User_Repair_Instruction.txt` | txt | documentation | 38699 | Y | Y | `f11121e6a783c905…` |
| `documentation/compliance_repair/forensic_preservation.json` | json | runtime-artifact | 555 | Y | Y | `f873181bcc5750df…` |
| `documentation/compliance_repair/historical_trace_summary.json` | json | runtime-artifact | 486 | Y | Y | `cdd2cfde1e36574c…` |
| `documentation/compliance_repair/matrix.json` | json | runtime-artifact | 57963 | Y | Y | `cefc67a59c218732…` |
| `documentation/compliance_repair/phase1d_extracted.txt` | txt | documentation | 44633 | Y | Y | `8d8fe6a6aaadb39a…` |
| `documentation/compliance_repair/rq1_cohort.json` | json | runtime-artifact | 2005 | Y | Y | `6da386c6ce39191c…` |
| `documentation/rq1_repair/CM01_Frozen_Provenance_Adaptation.txt` | txt | documentation | 13380 | Y | Y | `e5d2f9d5ad671a2a…` |
| `documentation/rq1_repair/Implementation_Decisions.md` | md | documentation | 4619 | Y | Y | `1062b38848997889…` |
| `documentation/rq1_repair/RQ1_Execution_Capacity_Blocker.md` | md | documentation | 4568 | Y | Y | `0a0fc2ce4740af61…` |
| `documentation/rq1_repair/adaptation_manifest.json` | json | runtime-artifact | 249 | Y | Y | `a80818e26fd43e88…` |
| `documentation/rq1_repair/capacity_blocker.json` | json | runtime-artifact | 72012 | Y | Y | `de637f98313b2dc1…` |
| `documentation/rq1_repair/configs/CM-01.json` | json | config | 2197 | Y | Y | `023a7f78a9cfd77d…` |
| `documentation/rq1_repair/configs/CM-02.json` | json | config | 2197 | Y | Y | `0a56c548e166fd91…` |
| `documentation/rq1_repair/configs/CM-03.json` | json | config | 2197 | Y | Y | `de250bac72f34f18…` |
| `documentation/rq1_repair/configs/CM-B0.json` | json | config | 2197 | Y | Y | `84db3cb67f8a7c40…` |
| `documentation/rq1_repair/configs/CM-B1.json` | json | config | 2197 | Y | Y | `6c361ef506977831…` |
| `documentation/rq1_repair/execution_plan.json` | json | runtime-artifact | 4457 | Y | Y | `5b76c347c153e4e2…` |
| `documentation/rq1_repair/execution_status.json` | json | runtime-artifact | 222 | Y | Y | `60357a4a388b525f…` |
| `documentation/rq1_repair/implementation_tests.xml` | xml | runtime-artifact | 2630 | Y | Y | `e3c0f96b9ac00b9f…` |
| `documentation/rq1_repair/input_manifest.json` | json | runtime-artifact | 7470 | Y | Y | `973817fd48e131c1…` |
| `documentation/rq1_repair/inputs/037fa2195887b99fb847e07e3703bff13532c5031d508cbb093e4f459cb46c36.json` | json | runtime-artifact | 2280934 | Y | Y | `336a997d9801c0ce…` |
| `documentation/rq1_repair/inputs/09bbc964ae8ba9d3331fd72d9cf03a70060dea2c593c4ab124e71ba0be0be778.json` | json | runtime-artifact | 2243674 | Y | Y | `e9c51fc068dd26aa…` |
| `documentation/rq1_repair/inputs/1e3ba0bc2c56845ad890c80e3b211e83b994dd68b9014294167a195c4ade3c65.json` | json | runtime-artifact | 1387652 | Y | Y | `b9ac1dd6881b0215…` |
| `documentation/rq1_repair/inputs/30a3ed6955609afb006ca3bb840e720174983223a1d62f615038f9e75d7e6a41.json` | json | runtime-artifact | 2496976 | Y | Y | `4a7e1257961cc6eb…` |
| `documentation/rq1_repair/inputs/36e2e96ced2723a75d94cbf3ecaf1757715ee3d00f2cc6d3d735b9ef1a65537d.json` | json | runtime-artifact | 2206570 | Y | Y | `a00500e944381e11…` |
| `documentation/rq1_repair/inputs/375ccc11b7119291edd49c75f157eab17c237c3e86500c69ae0901db46b7f746.json` | json | runtime-artifact | 2517840 | Y | Y | `73949e8388947dc5…` |
| `documentation/rq1_repair/inputs/3b7d695fa721f99855a8fecadd14f428e1576c01a9a400bf12233d5d5e30f8e4.json` | json | runtime-artifact | 2199432 | Y | Y | `0c5358bbad39d9de…` |
| `documentation/rq1_repair/inputs/3e282e70e3fb4271cc030fbb1c326e17ce3d083c31ddfaf50407ebd157b96b6b.json` | json | runtime-artifact | 2273965 | Y | Y | `bd3c31d83833712f…` |
| `documentation/rq1_repair/inputs/4ab20101972585bdaf220981fcc3f3b5d4b0819f24c2433dd043544d3c8e443b.json` | json | runtime-artifact | 2215423 | Y | Y | `70fe11b05b662f57…` |
| `documentation/rq1_repair/inputs/5e4f1a8834419a57554b85eb9b9cb6f60b4e04ca17f2b9e74ed5b0336bf6056a.json` | json | runtime-artifact | 2198034 | Y | Y | `18d3c2e97d27b919…` |
| `documentation/rq1_repair/inputs/60a511856a76d095a7eff591cb2376855eb232ee65e1a61ba6bd263d6fbf0679.json` | json | runtime-artifact | 2273899 | Y | Y | `dca47ecf48e52746…` |
| `documentation/rq1_repair/inputs/6e86b0ff28f3f327aa3364c883e397e3e0b46e3f2dda92c4dfc56fa7c5ce8818.json` | json | runtime-artifact | 2192542 | Y | Y | `c3d17dba7cd27016…` |
| `documentation/rq1_repair/inputs/70422028263d0899cf81c88a80138401fc7893fb135807c5151e652561e8dfea.json` | json | runtime-artifact | 2286981 | Y | Y | `59d8f1509c1462c9…` |
| `documentation/rq1_repair/inputs/86a9e2fbe31e1ebc15e9ace6a43afbed20b3feefd2eba8843c81210db8f5a543.json` | json | runtime-artifact | 1434971 | Y | Y | `ca42942c32d1e619…` |
| `documentation/rq1_repair/inputs/88f07c98961c098584bca2b3269ac3d5c69bc31cccf98676fa06d81e06e6e070.json` | json | runtime-artifact | 2294512 | Y | Y | `cf4497caee23d9f7…` |
| `documentation/rq1_repair/inputs/8a364b6cd518ce796f975bef32b7554ed949123ed8d768e5a58c69cf15efd8df.json` | json | runtime-artifact | 2290932 | Y | Y | `d75462697a07b92e…` |
| `documentation/rq1_repair/inputs/946a1e148df27dd6ce15730fe4ebb95352bf38653854bca606a60dcbaaea26e8.json` | json | runtime-artifact | 2295438 | Y | Y | `6d1e0e1ce85b51a1…` |
| `documentation/rq1_repair/inputs/9b19f582ed1e8446c27cccc823d1ac22986995010cb5959d92d417b709497be9.json` | json | runtime-artifact | 2270287 | Y | Y | `a98d658dc749703e…` |
| `documentation/rq1_repair/inputs/9bec44844d28b624cc49b3d97be3855a0ae0975f59cab4d52be77e428931205a.json` | json | runtime-artifact | 2307112 | Y | Y | `1244fd341283585d…` |
| `documentation/rq1_repair/inputs/a3d95fb5a556b0d15e864627b350ed0352ac095aac61f8b5a0dde3977ea02ac5.json` | json | runtime-artifact | 2180949 | Y | Y | `06d6e6041aaa7084…` |
| `documentation/rq1_repair/inputs/ace6add6e1e0c8b0d2792f247ecad84d4b3a4e8e4b234e6373bfddd2a5c11e63.json` | json | runtime-artifact | 2229855 | Y | Y | `8cfa23de30fcf0be…` |
| `documentation/rq1_repair/inputs/ade01ef25cac40bdb7fafcf90cc12be90b1e3085c116704175b291d16c12730d.json` | json | runtime-artifact | 2319889 | Y | Y | `8a953893763ba1a4…` |
| `documentation/rq1_repair/inputs/b3e7f1f974167f2ac487371a040aa2e2488a33b91fe3c209b49e5fae205e5967.json` | json | runtime-artifact | 2199619 | Y | Y | `40ab927457f0aeb3…` |
| `documentation/rq1_repair/inputs/b94f4fba909ab4a65d07aec1eaf5095fc13b6c97df947a6c2a545bb4d22a12be.json` | json | runtime-artifact | 2497044 | Y | Y | `8b7d130375c13866…` |
| `documentation/rq1_repair/inputs/bc8d2417912556c47221294285110060b212ee2837da3712a27f029cd9a6c474.json` | json | runtime-artifact | 2197849 | Y | Y | `b8ad9a2db61a522f…` |
| `documentation/rq1_repair/inputs/bda703c3758bfb8be5c2263101efef652169e33ab9a74f8a7aca1bf2f1afc203.json` | json | runtime-artifact | 2262023 | Y | Y | `abe6939677de4334…` |
| `documentation/rq1_repair/inputs/c518231389b0e1dac98bba57ca75992d2442202cc799e93731a3f47ce1f61961.json` | json | runtime-artifact | 2250016 | Y | Y | `5eb87f5cd34915b2…` |
| `documentation/rq1_repair/inputs/c93e4f0bce305ed5536d05bc64508a0adaa21a3c373d1daea456d6d3e42305be.json` | json | runtime-artifact | 2224570 | Y | Y | `dd9c6fb7ffded0d6…` |
| `documentation/rq1_repair/inputs/d18198dcc8571f685b525487095bf9ac598f22f69e4e9981f4513d26abe837a7.json` | json | runtime-artifact | 2180022 | Y | Y | `cd2a70be3cb36f17…` |
| `documentation/rq1_repair/inputs/db55fb8c8f5cbeaff120f420beed206036f3ba7a0741039ec227a58217b085a0.json` | json | runtime-artifact | 2286054 | Y | Y | `6621a0c749bc19ff…` |
| `documentation/rq1_repair/inputs/e7ae87c5c397f25c076e6ccb2572875f32d5b0dc5a1b5449b526a00d41887499.json` | json | runtime-artifact | 2249088 | Y | Y | `8ff58142914aaa22…` |
| `documentation/rq1_repair/inputs/f4fd9019d4d09d14711bdc9e51559e7da507b22b67398404f6e532ff373d7eb0.json` | json | runtime-artifact | 2287707 | Y | Y | `2405295810e82b9c…` |
| `documentation/rq1_repair/local_audit_progress.json` | json | runtime-artifact | 27572 | Y | Y | `fcc3fb11b61de25e…` |
| `documentation/rq1_repair/measured_request_capacity.json` | json | runtime-artifact | 17747 | Y | Y | `cf66c1bc4f28f29d…` |
| `documentation/rq1_repair/pre_execution_full_tests.xml` | xml | runtime-artifact | 24120 | Y | Y | `33383938c1d565f4…` |
| `documentation/rq1_repair/pre_execution_preservation.json` | json | runtime-artifact | 1439 | Y | Y | `134e9339937b1f7f…` |
| `documentation/rq1_repair/provider_preflight/chat_completions.json` | json | runtime-artifact | 1001 | Y | Y | `6b5eedbad430f23d…` |
| `documentation/rq1_repair/provider_preflight/diagnostic.json` | json | runtime-artifact | 1922 | Y | Y | `92b7406d936ee86b…` |
| `documentation/rq1_repair/provider_preflight/models_list.json` | json | runtime-artifact | 368 | Y | Y | `457f60298276641f…` |
| `documentation/rq1_repair/provider_preflight/probe_started.json` | json | runtime-artifact | 77 | Y | Y | `48765ba9f0fff127…` |
| `documentation/rq1_repair/request_capacity_preflight.json` | json | runtime-artifact | 15953 | Y | Y | `7e02d8d5f6bd8a68…` |
| `requirements-rq-repair.txt` | txt | config | 95 | Y | Y | `dd5a1324d5434ffd…` |
| `research/repair/__init__.py` | py | source | 86 | Y | Y | `cc74b0e6af5536f1…` |
| `research/repair/dispatch.py` | py | source | 6017 | Y | Y | `c18748aec9fa8766…` |
| `research/repair/rq1_compliance_v1/__init__.py` | py | source | 81 | Y | Y | `219464b40c952424…` |
| `research/repair/rq1_compliance_v1/cm01.py` | py | source | 8444 | Y | Y | `b7ede2c9d20d53f3…` |
| `research/repair/rq1_compliance_v1/cm02.py` | py | source | 4038 | Y | Y | `1fa0e9487f0655c5…` |
| `research/repair/rq1_compliance_v1/cm03.py` | py | source | 8007 | Y | Y | `95c4a8ef31aa3907…` |
| `research/repair/rq1_compliance_v1/context.py` | py | source | 1080 | Y | Y | `8606b2c71083fab7…` |
| `research/repair/rq1_compliance_v1/system.py` | py | source | 7772 | Y | Y | `dfe6d2a3af8f0bac…` |
| `scripts/audit_rq1_repair_local.py` | py | source | 3889 | Y | Y | `3a3161333997fad7…` |
| `scripts/audit_rq_compliance.py` | py | source | 23367 | Y | Y | `a39f6a70bcd44f43…` |
| `scripts/prepare_rq1_repair.py` | py | source | 5043 | Y | Y | `3bebdf1830e48885…` |
| `scripts/report_rq1_repair.py` | py | source | 5078 | Y | Y | `bba4a6162e046062…` |
| `scripts/run_rq1_repair.py` | py | source | 8069 | Y | Y | `4acdabc4425afcf0…` |
| `tests/test_repair_cm01.py` | py | test | 5865 | Y | Y | `075620f77fe95003…` |
| `tests/test_repair_dispatch.py` | py | test | 2725 | Y | Y | `6d3e7c4fd8259c26…` |
| `tests/test_repair_rq1.py` | py | test | 6655 | Y | Y | `509276903f4b6da0…` |
| `tests/test_repair_statistics.py` | py | test | 824 | Y | Y | `e12706d90d75df2c…` |
| `tmp/pdfs/qafd_equations.png` | png | temporary-staging | 260397 | N | N | `451026270f3f580d…` |
