# BitAgent Bonsai-8B signed-plan quantitative baseline (v2)

Completed 19 November 2026 (UTC+8) via pinned `llama-server` (`d5897802f2bc893214fa86abf9b7276bf409f5f661751c4ef0e9981443a005f6`), `Bonsai-8B-Q1_0.gguf` (`284a335aa3fb2ced3b1b01fcb40b08aa783e3b70832767f0dd2e3fdfa134bd54`), and `bitagent-bonsai8b-dagv2-lora-v3-f16.gguf` (`9a11fe2cecf795f53dbea490b9897b28f3d3346a9f69a71ce28bbb195f7de704`, scale `1.0`), `direct_json` track (`temperature=0`, `seed=0`, `max_tokens=2048`).

## Quantitative check results (`6/6` tasks completed, `100%` coverage)

- **Micro accuracy:** `3 / 13` (`23.08%`)
- **Family-macro accuracy:** `25.00%` (`credit: 16.67%`, `crowding: 33.33%`, `settlement: 0.00%`, `tail: 50.00%`)
- **Exact fields:** `q-tail.var = 20`, `q-netting.same_set_exposure = 20`, `q-capacity.million_sell = 300000000`

## Staged history rollout boundary

Completed `4` narrative stages (`control_funding_buffer/s1`, `control_pvp_prefunded/s0`, `control_pvp_prefunded/s1`, `control_orderly_volatility/s1`) before hitting the registered `max_tokens = 2048` truncation gate (`finish_reason: length`) on three consecutive multi-field narrative stages (`12`–`14`), halting cleanly per protocol.
