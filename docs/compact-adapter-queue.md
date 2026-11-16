# Compact-model adapter queue

The signed-plan historical campaign continues independently of the local GPU.
The user's GPU reservation prevents starting the BitAgent server before
**16 November 2026, 15:35:22 Asia/Singapore (07:35:22 UTC)**. This is a minimum
wait, not evidence that the GPU will be free then. The launcher checks available
VRAM and active compute processes afterwards and refuses to take over a port.
It never stops another process.

## BitAgent Bonsai-8B DAG v3

Both artifacts have been verified against the existing BitAgent release lock:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Bonsai-8B-Q1_0.gguf | 1,158,654,496 | `284a335aa3fb2ced3b1b01fcb40b08aa783e3b70832767f0dd2e3fdfa134bd54` |
| bitagent-bonsai8b-dagv2-lora-v3-f16.gguf | 87,329,024 | `9a11fe2cecf795f53dbea490b9897b28f3d3346a9f69a71ce28bbb195f7de704` |

The wrapper requires the registered model alias and exactly one active LoRA at
scale 1.0. It sends that adapter ID/scale explicitly with each completion.
Base-only fallback, unexpected adapters, malformed responses and truncated
completions are failures. It records server token telemetry and leaves unknown
reasoning tokens null. File verification and CPU tests do not establish a live
GPU inference result.

The prepared local campaign takes the exact six numerical packets and 74
historical/control stage packets from the frozen signed-plan plans. It preserves
packet hashes and prior replies within each case, and uses the same response
schemas. Local temperature/seed/output-token settings are recorded; those are
not equivalent to the signed-plan models' reasoning-effort controls.

```powershell
# Prepare without any model or GPU calls.
python scripts/run_local_benchmark.py --config artifacts/bitagent-readiness/local-config.json --baseline-plans artifacts/quant-baseline-v1/frozen-plan.json artifacts/history-baseline-v1/frozen-plan.json --output-dir artifacts/bitagent-dagv3-v1 --prepare-only

# After the reservation, recheck hardware and start an owned hidden server.
pwsh -NoProfile -File scripts/start_local_bitagent.ps1 -Config artifacts/bitagent-readiness/local-config.json -RuntimeDir artifacts/bitagent-server

# Execute only after server health and adapter metadata are verified.
python scripts/run_local_benchmark.py --config artifacts/bitagent-readiness/local-config.json --baseline-plans artifacts/quant-baseline-v1/frozen-plan.json artifacts/history-baseline-v1/frozen-plan.json --output-dir artifacts/bitagent-dagv3-v1
```

For the current reserved GPU, the process-owned waiter combines those last two
steps. It makes no GPU queries until the reservation ends, then retries the idle
GPU preflight without terminating any process:

```powershell
python scripts/launch_when_gpu_available.py --config artifacts/bitagent-readiness/local-config.json --baseline-plans artifacts/quant-baseline-v1/frozen-plan.json artifacts/history-baseline-v1/frozen-plan.json --output-dir artifacts/bitagent-dagv3-v1 --runtime-dir artifacts/bitagent-server
```

Its current state is written to `gpu-wait-status.json` in the output directory.
An append-only `.jsonl` state journal remains available if a Windows reader
temporarily blocks replacement of the status pointer.

The machine-local configuration is generated from verified artifact paths and
kept in ignored artifacts. The committed template contains placeholders. No
wallet authorization, signing, live trading or runtime promotion is performed.

## Located next-phase candidates

These are source/checkpoint registrations, not completed financial benchmark
runs. Current native task interfaces require explicit bridges before their
scores can be compared to free-form model responses.

| Candidate | Located implementation | Current bridge requirement |
| --- | --- | --- |
| ControlTRM | `MoralityLabAI/LoopedTransformers`, commit `254edb4e9a864af06ba656fec3fe54cb49940541`; registered trained proposal checkpoints for seeds 211/223/227 | Replace gym-specific state/action features with a preregistered financial state/action interface. A precomputed toy-task proposal table cannot be reused as financial answers. |
| Lean-trained TRM tactic LM | Same commit, `research/lean_cgrt_hrm400/lcgrt/tactic_lm.py`; a local 1,491,204-parameter checkpoint is identified | Native output is bounded tactic bytes, not the benchmark's JSON response schema. Add a financial proof-obligation track or an explicitly evaluated decoder bridge. |
| RLM | Same commit, `research_gym/benchmarks/rlm_evidence_runtime.py`; official-RLM source identity registered as `72d6940142ddfb84ee6be573dc999a37e633e671`, `rlms==0.1.3` | Point root/child inference at an authorized backend, enforce recursion/tool/token limits, and expose only current-stage evidence. The existing OpenAI-API backend is not automatically a signed-plan backend. |
| Lean / CGRT | Same commit, `research/lean_cgrt_hrm400/lcgrt/search.py`, `certify.py`, `lean_repl.py` and `tactic_lm.py` | Translate supported risk statements into explicit proof obligations, record Lean/toolchain/checker results, and keep empirical financial assumptions outside proof guarantees. |
| TRM/RLM/LDT hybrids | Same commit, `research_gym/benchmarks/rlm_hybrid_runtime.py` | Port typed financial constraints and policy actions; compare trained and proxy arms separately. Root/child calls and deterministic gate work must all be metered. |
| HybridTRMLDT control baseline | `MoralityLabAI/HybridTRMLDT`, commit `1688515d1b29509ea1e0b11b51d93cb2eb9fb4c4`; `research_gym/neural/trm.py` | The existing proposer predicts storyworld actions. Do not label it a financial reasoner before a measured adapter is supplied. |

The located Lean-trained TRM artifact is
`D:/lean_cgrt/runs/rapid/r07_trmXS_sup8_lr0.0005_k2_s97/best.pt`,
SHA-256 `ad753f3eecf56f72e600f5bdce0341cd3dcf2a12f14293edfaa7f5a732eadcc6`.
Its metadata records a TRM encoder with `trm_n=6`, `trm_T=3`, `trm_sup=8` and
Mathlib training. The checksum was independently checked; financial capability
has not been established. The local code defines CGRT as Cross-Generation
Reasoning Tree and describes its current diagnostic limits in its own README.

For every new arm, freeze code/checkpoint hashes, packet transforms, output
decoding, recurrence/halting budgets and failure handling before collecting
results. Keep native proof/control tracks separate from direct narrative
reasoning unless a validated common interface has been demonstrated.
