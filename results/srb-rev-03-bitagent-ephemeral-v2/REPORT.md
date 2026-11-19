# SRB-REV-03: Stage-isolated BitAgent Bonsai-8B financial revision results (v2)

Completed 19 November 2026 (UTC+8). Pre-registered at commit `9ba9700` against frozen panel manifest `81232c2f28c1e57b0fd8c1d8cc478ec3983c73f08be2e51076acb8e5995a0f0a` ([finance-revision-panels.json](../../configs/finance-revision-panels.json)).

## Model, serving isolation, and scope

- **Checkpoint identity:** `Bonsai-8B-Q1_0.gguf` (`284a335aa3fb2ced3b1b01fcb40b08aa783e3b70832767f0dd2e3fdfa134bd54`) + `bitagent-bonsai8b-dagv2-lora-v3-f16.gguf` (`9a11fe2cecf795f53dbea490b9897b28f3d3346a9f69a71ce28bbb195f7de704`, scale `1.0`) served via pinned `llama-server` (`d5897802f2bc893214fa86abf9b7276bf409f5f661751c4ef0e9981443a005f6`).
- **Response track & decoding:** `direct_json` (no chain-of-thought, tools, or scratchpad), `temperature=0`, `seed=0`, `max_tokens=1024`, OpenAI `response_format.json_schema` grammar active.
- **Stage-isolated server reset (`ephemeral_per_stage_llama_cpp`):** Every stage invocation booted a fresh `llama-server` OS process on an unused loopback port in an empty temporary working directory without slot persistence, bound to a kill-on-close OS job, served exactly one request (`cache_prompt=false`), and verified process exit and port closure before emitting `SRB_REVISION_RECEIPT_V1`. Across the six v2 runs, **148 / 148 attempted stages** produced valid receipts with **148 globally distinct `server_boot_sha256` digests** (`model_server_state_reset_verified=true` on all six reports).
- **Epistemic boundary:** Because the Python adapter subprocess runs on an unsandboxed host and the public development issuer sequence is deterministic, `physical_memory_enforced=false`, `adapter_process_sandboxed=false`, `selection_conditioned_bayes_claim=false`, and `population_estimate_claim=false` remain false. All actions are hypothetical read-only choices.

## Pilot v1 transport repair audit

Under initial pre-registration `1291dc7`, the six-root pilot (`pilot-v1`, 12 calls across `count` and `bitmap`) revealed that OpenAI `/v1/chat/completions` in `llama-server` requires `response_format.json_schema.schema` rather than top-level `response_format.schema`. Without the nested key, `llama-server` left JSON-schema GBNF inactive (`0/6` valid initial responses per arm). Per protocol ([finance-revision-stress.md](../../docs/finance-revision-stress.md)), only `pilot` roots `0..5` were touched during diagnosis; the wire-format repair was committed and re-registered as `-v2` (`9ba9700`) before executing `pilot-v2`, `stress-v2`, and `natural-v2`.

## Panel outcomes (`v2`)

Note: `pilot` (`0..5`) is a prefix of `natural` (`0..47`) and shares root `5` with `stress`; `natural` and `stress` share roots `5, 28, 36, 37`. Do not pool panel denominators.

| Panel | Arm | Cases | Initial valid | Scored (coverage) | Excess Brier (w/ 2.0 pen.) | Matched regret (w/ 20.0 pen.) | Full-info regret (w/ 20.0 pen.) | Scored full-info regret | Action acc. (w/ pen.) | Own-forecast incoherent (init / upd) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `pilot` | `count` (4b) | 6 | 1 | 1 (16.7%) | 1.710806 | 16.666667 | 16.666667 | 0.000000 | 16.7% | 1/1 / 1/1 |
| `pilot` | `bitmap` (12b) | 6 | 0 | 0 (0.0%) | 2.000000 | 20.000000 | 20.000000 | n/a | 0.0% | n/a / n/a |
| `stress` | `count` (4b) | 18 | 0 | 0 (0.0%) | 2.000000 | 20.000000 | 20.000000 | n/a | 0.0% | n/a / n/a |
| `stress` | `bitmap` (12b) | 18 | 0 | 0 (0.0%) | 2.000000 | 20.000000 | 20.000000 | n/a | 0.0% | n/a / n/a |
| `natural` | `count` (4b) | 48 | 3 | 2 (4.2%) | 1.929344 | 19.188307 | 19.193014 | 0.632325 | 2.1% | 3/3 / 2/2 |
| `natural` | `bitmap` (12b) | 48 | 0 | 0 (0.0%) | 2.000000 | 20.000000 | 20.000000 | n/a | 0.0% | n/a / n/a |

## Measured compute and latency receipts (`v2`)

| Panel | Arm | Calls | Unique server boots | Input tokens | Output tokens | Failed calls w/ usage | Server inference (s) | Ephemeral boot (s) | Ephemeral stop (s) | Host wall (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `pilot` | `count` | 7 | 7 | 6,660 | 361 | 2 | 17.95 | 21.63 | 3.80 | 59.12 |
| `pilot` | `bitmap` | 6 | 6 | 5,536 | 392 | 2 | 15.98 | 18.37 | 2.84 | 50.81 |
| `stress` | `count` | 18 | 18 | 16,475 | 885 | 6 | 43.02 | 49.42 | 7.82 | 137.45 |
| `stress` | `bitmap` | 18 | 18 | 16,619 | 1,114 | 6 | 52.70 | 66.72 | 9.16 | 176.25 |
| `natural` | `count` | 51 | 51 | 47,428 | 2,579 | 17 | 123.40 | 136.68 | 22.76 | 388.81 |
| `natural` | `bitmap` | 48 | 48 | 44,319 | 3,064 | 15 | 136.31 | 159.07 | 24.35 | 437.21 |
| **Total (`v2`)** | **Both** | **148** | **148** | **137,037** | **8,395** | **48** | **389.36** | **451.89** | **70.73** | **1,249.65** |

## Failure modes and coherence diagnostics

1. **Single-pass bitwise memory bottleneck (`direct_json`, no CoT):** Under JSON-schema grammar without chain-of-thought or REPL scratchpad, the 1-bit `Bonsai-8B-Q1_0` + `dagv3` LoRA model cannot evaluate `sum(old[slot] << slot)` across twelve records in one forward pass. On `natural` (`bitmap`), its 33 normalized initial completions collapsed to `{1999: 27, 0: 4, 1023: 2}`, achieving `0/48` valid 12-bit state encodings (`0/18` on `stress`). On `natural` (`count`), its 32 normalized initial completions concentrated on `{12: 19, 6: 11, 0: 1, 11: 1}`, matching `world.old_count` on 3/48 roots (`indices 0, 15, 39`; `index 15` subsequently failed update-stage posterior normalization, leaving 2/48 fully scored roots).
2. **Scenario-specific simplex normalization errors:** Across `natural` (`count` + `bitmap`), 31/32 `collateral` initial calls (`16/16` count, `15/16` bitmap) and `12/12` `stress` `collateral` calls failed `parse_forecast`'s `1e-6` simplex-sum check (`output_tokens=32`), whereas `64/64` `natural` and `24/24` `stress` initial calls on `price_feed` and `counterparty` emitted `[0.3333333333333333, 0.3333333333333333, 0.3333333333333333]`.
3. **Action/forecast coherence separates lucky zero-regret actions from coherent Bayes decisions:** On both scored `natural` `count` roots (`index 0` and `index 39`, both `price_feed`), the model reported a flat `[1/3, 1/3, 1/3]` posterior at both stages while switching action from `halt_and_escalate` (`initial`) to `continue` (`update`). On `index 0`, `continue` matched the Bayes-optimal action (`policy_regret_vs_matched = 0.0`, `policy_regret_vs_full = 0.0`), which under SRB-REV-02's reference regret alone appears optimal; SRB-REV-03's coherence check flags both stages as incoherent against the model's own `[1/3, 1/3, 1/3]` forecast (`de_risk` expected loss `2.10` vs `halt_and_escalate` `2.50` at initial, own-forecast regret `0.40`; `continue` `6.00` vs `de_risk` `2.10` at update, own-forecast regret `3.90`). On `index 39`, the same `continue` choice incurred `1.038735` matched regret (`1.264649` full-information regret).
