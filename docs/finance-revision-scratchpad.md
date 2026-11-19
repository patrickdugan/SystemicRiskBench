# SRB-REV-04: Bounded intra-stage scratchpad vs. direct JSON on frozen financial panels

**19 November 2026.** Comparator registration continuing [SRB-REV-03](finance-revision-stress.md). Uses the identical frozen panel manifest `81232c2f28c1e57b0fd8c1d8cc478ec3983c73f08be2e51076acb8e5995a0f0a` ([finance-revision-panels.json](../configs/finance-revision-panels.json)), loss schedules, Bayesian reference law, and pinned BitAgent Bonsai-8B checkpoint.

## Motivation

In SRB-REV-03 ([REPORT.md](../results/srb-rev-03-bitagent-ephemeral-v2/REPORT.md)), `direct_json` generation (`max_tokens=1024`, no chain-of-thought, GBNF JSON-schema starting at token 0) achieved `0/48` valid 12-bit `bitmap` encodings and `2/48` scored 4-bit `count` cases on `natural` (`0/18` in both arms on `stress`), because a 1-bit transformer without intermediate tokens cannot evaluate $\sum_{s=0}^{11}\mathrm{old}[s]\cdot 2^s$ or normalize a 12-observation Bayesian posterior in a single forward pass.

## Registered intervention (`bounded_scratchpad`)

[revision_scratchpad_llamacpp.py](../adapters/revision_scratchpad_llamacpp.py) introduces a two-pass **intra-stage** scratchpad within the same stage-isolated `ephemeral_per_stage_llama_cpp` server lifecycle:

1. **Pass 1 (bounded derivation, `max_scratchpad_tokens=1792`, `temperature=0`, `seed=0`):** The model derives the integer memory (at `initial`), the 3-regime Bayesian posterior, and action expected losses in plain text.
2. **Pass 2 (JSON-schema commit, `max_commit_tokens=256`, `temperature=0`, `seed=0`):** On the same ephemeral server (`requests_served=2`), the model commits only the phase-specific JSON object constrained by `_response_schema(packet)`. The adapter performs **no post-processing, rounding, or renormalization** on model outputs.
3. **Inter-stage memory boundary preserved:** The ephemeral `llama-server` process is terminated and reaped and its port verified closed before Stage 1 returns (`model_server_state_reset_verified=true`). Zero scratchpad text or KV-cache state crosses to Stage 2; only the host-validated 4-bit or 12-bit integer `memory` is supplied in the `update` packet.
4. **Cost accounting:** `SRB_REVISION_RECEIPT_V1` sums Pass 1 + Pass 2 prompt and completion tokens under `max_output_tokens_per_call=2048` and `max_input_tokens_per_call=6144`.
