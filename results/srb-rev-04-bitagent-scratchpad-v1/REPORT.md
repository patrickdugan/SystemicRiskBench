# SRB-REV-04: Bounded intra-stage scratchpad BitAgent Bonsai-8B results (v1)

Completed 19 November 2026 (UTC+8). Pre-registered at commit `eab92b0` against the identical frozen panel manifest `81232c2f28c1e57b0fd8c1d8cc478ec3983c73f08be2e51076acb8e5995a0f0a` ([finance-revision-panels.json](../../configs/finance-revision-panels.json)) used in [SRB-REV-03](../srb-rev-03-bitagent-ephemeral-v2/REPORT.md).

## Model, serving isolation, and intervention

- **Checkpoint identity:** Identical to SRB-REV-03 — `Bonsai-8B-Q1_0.gguf` (`284a335aa3fb2ced3b1b01fcb40b08aa783e3b70832767f0dd2e3fdfa134bd54`) + `bitagent-bonsai8b-dagv2-lora-v3-f16.gguf` (`9a11fe2cecf795f53dbea490b9897b28f3d3346a9f69a71ce28bbb195f7de704`, scale `1.0`) served via pinned `llama-server` (`d5897802f2bc893214fa86abf9b7276bf409f5f661751c4ef0e9981443a005f6`).
- **Intervention (`bounded_scratchpad`, [revision_scratchpad_llamacpp.py](../../adapters/revision_scratchpad_llamacpp.py)):** Within each stage's fresh `ephemeral_per_stage_llama_cpp` server, Pass 1 allows up to `1,792` tokens of plain-text step-by-step derivation (`temperature=0`, `seed=0`), and Pass 2 commits up to `256` tokens constrained by `_response_schema(packet)` (`max_output_tokens_per_call=2048`). No output post-processing or renormalization is performed by the adapter.
- **Inter-stage memory boundary:** Each stage's ephemeral `llama-server` is terminated and reaped and its port verified closed before the stage exits (`requests_served=2`). Zero scratchpad text or KV-cache state survives to `update`; only the host-validated 4-bit (`count`) or 12-bit (`bitmap`) integer crosses stages. Across all six runs, **168 / 168 attempted stages** produced valid receipts with **168 globally distinct `server_boot_sha256` digests** (`model_server_state_reset_verified=true` on all six reports; `physical_memory_enforced=false` and `adapter_process_sandboxed=false` preserved).

## Panel outcomes (`SRB-REV-04` vs. `SRB-REV-03`)

Note: `pilot` (`0..5`), `stress` (`18` disagreement roots), and `natural` (`0..47`) overlap on shared public roots; do not pool denominators across panels.

| Panel | Arm | SRB-REV-03 Scored | SRB-REV-04 Scored (Coverage) | Excess Brier (w/ 2.0 pen.) | Matched Regret (w/ 20.0 pen.) | Full-Info Regret (w/ 20.0 pen.) | Scored Full-Info Regret | Action Acc. (Scored) | Own-Forecast Coherent (Init / Upd) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `pilot` | `count` (4b) | 1 / 6 (16.7%) | **1 / 6 (16.7%)** | 1.682331 | 16.898517 | 16.998475 | 1.990851 | 0.0% | 0/1 / 0/1 |
| `pilot` | `bitmap` (12b) | 0 / 6 (0.0%) | **0 / 6 (0.0%)** | 2.000000 | 20.000000 | 20.000000 | n/a | n/a | n/a / n/a |
| `stress` | `count` (4b) | 0 / 18 (0.0%) | **4 / 18 (22.2%)** | **1.586815** | **15.747576** | **15.811759** | 1.152918 | 25.0% | **2/4 / 2/4 (50.0%)** |
| `stress` | `bitmap` (12b) | 0 / 18 (0.0%) | **0 / 18 (0.0%)** | 2.000000 | 20.000000 | 20.000000 | n/a | n/a | n/a / n/a |
| `natural` | `count` (4b) | 2 / 48 (4.2%) | **16 / 48 (33.3%)** | **1.486886** | **13.647570** | **13.670669** | 1.012008 | 25.0% | **10/16 (62.5%) / 6/16 (37.5%)** |
| `natural` | `bitmap` (12b) | 0 / 48 (0.0%) | **3 / 48 (6.2%)** | **1.923331** | **18.791639** | **18.791639** | **0.666229** | **66.7%** | **2/3 (66.7%) / 2/3 (66.7%)** |

## Measured compute and latency receipts (`SRB-REV-04`)

| Panel | Arm | Stage Calls | Unique Server Boots | Input Tokens | Output Tokens | Failed Calls w/ Usage | Server Inference (s) | Ephemeral Boot (s) | Ephemeral Stop (s) | Host Wall (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `pilot` | `count` | 7 | 7 | 25,467 | 9,136 | 2 | 157.85 | 25.01 | 3.25 | 204.14 |
| `pilot` | `bitmap` | 6 | 6 | 22,165 | 8,528 | 3 | 139.77 | 16.78 | 3.04 | 173.16 |
| `stress` | `count` | 22 | 22 | 79,135 | 27,309 | 6 | 491.48 | 82.89 | 13.22 | 649.88 |
| `stress` | `bitmap` | 18 | 18 | 62,913 | 21,944 | 5 | 385.24 | 66.47 | 10.76 | 511.46 |
| `natural` | `count` | 64 | 64 | 228,029 | 75,034 | 13 | 1,305.96 | 214.39 | 33.14 | 1,711.48 |
| `natural` | `bitmap` | 51 | 51 | 180,709 | 63,134 | 15 | 1,123.51 | 170.83 | 26.27 | 1,503.28 |
| **Total** | **Both** | **168** | **168** | **598,418** | **205,085** | **44** | **3,603.81** | **576.37** | **89.68** | **4,753.40** |

## Principal findings

1. **8x `natural` coverage and substantial coherence gains from intra-stage derivation:** Allowing a stage-local derivation before JSON commit lifted `natural` `count` coverage from `2/48` (`4.2%`) to `16/48` (`33.3%`, with `16/16` update completion among initial-valid roots), lifted `stress` `count` coverage from `0/18` to `4/18` (`22.2%`), unlocked `3/48` (`6.25%`) fully scored 12-bit `bitmap` roots on `natural` (`indices 9, 31, 35`, achieving `0.0` full-info regret on `root 9` `continue -> de_risk` and `root 35` `de_risk -> halt_and_escalate`), and raised own-forecast coherence from `0%` in SRB-REV-03 to `62.5%` initial / `37.5%` update on `natural` `count` (`66.7%` / `66.7%` on `natural` `bitmap`; `50.0%` / `50.0%` on `stress` `count`).
2. **Empirical codec reversal (serialization reliability vs. theoretical information capacity):** Under exact Bayes arithmetic, 12-bit `bitmap` strictly dominates 4-bit `count` (`0.000` vs. `0.0443` expected full-info regret on `natural`; `0.000` vs. `0.5700` on `stress`). For the 1-bit neural agent without an external arithmetic verifier, computing $\sum_{s=0}^{11}\mathrm{old}[s]\cdot 2^s$ fails far more often than summing twelve bits, so **4-bit `count` empirically beats 12-bit `bitmap` on coverage-adjusted full-information regret** on both `natural` (`13.671` vs. `18.792`) and `stress` (`15.812` vs. `20.000`), even though conditional on surviving initial encoding (`n=3`), `bitmap` achieves lower scored full-information regret (`0.666` vs. `1.012`).
