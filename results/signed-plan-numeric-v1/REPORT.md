# Signed-plan numerical baseline v1

Completed 16 November 2026 (Asia/Singapore). 90 actual model calls; 90 signed local result webhooks; 15 completed model/effort cells.

Each cell answers the same six public numerical tasks (13 numeric fields), once. This is a small exploratory arithmetic diagnostic; no audited reasoning ranking is claimed.

| Model | Effort | Correct fields | Family macro | Median wall s | Reasoning tokens |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-5.6-luna | high | 13/13 | 100.0% | 12.27 | 1,746 |
| gpt-5.6-luna | low | 11/13 | 91.7% | 8.83 | 1,033 |
| gpt-5.6-luna | medium | 11/13 | 91.7% | 12.98 | 1,985 |
| gpt-5.6-sol | high | 13/13 | 100.0% | 8.33 | 588 |
| gpt-5.6-sol | low | 13/13 | 100.0% | 7.32 | 476 |
| gpt-5.6-sol | medium | 13/13 | 100.0% | 9.07 | 410 |
| gpt-6-luna | high | 13/13 | 100.0% | 9.38 | 1,199 |
| gpt-6-luna | low | 10/13 | 83.3% | 6.39 | 0 |
| gpt-6-luna | medium | 10/13 | 83.3% | 7.02 | 0 |
| gpt-6-sol | high | 13/13 | 100.0% | 9.72 | 697 |
| gpt-6-sol | low | 11/13 | 91.7% | 6.76 | 74 |
| gpt-6-sol | medium | 13/13 | 100.0% | 8.35 | 621 |
| gpt-6.1-sol | high | 13/13 | 100.0% | 14.68 | 1,330 |
| gpt-6.1-sol | low | 13/13 | 100.0% | 11.20 | 492 |
| gpt-6.1-sol | medium | 13/13 | 100.0% | 12.61 | 966 |

All 90 calls completed without recorded tool use. Exact model resolution is retained in the response file. Wall latency includes the Codex runtime and provider overhead; these runs are not a hardware-matched speed contest.

## Observed numerical errors

- **gpt-5.6-luna--low**: `q-wrong-way.joint_loss` returned 19140 (reference 12540); `q-wrong-way.independent_loss` returned 19140 (reference 3306).
- **gpt-5.6-luna--medium**: `q-wrong-way.joint_loss` returned 2699.4 (reference 12540); `q-wrong-way.independent_loss` returned 555.06 (reference 3306).
- **gpt-6-luna--low**: `q-cva-term.cva` returned 25185.0 (reference 23400); `q-wrong-way.joint_loss` returned 12600 (reference 12540); `q-wrong-way.independent_loss` returned 54600 (reference 3306).
- **gpt-6-luna--medium**: `q-cva-term.cva` returned 33765 (reference 23400); `q-wrong-way.joint_loss` returned 143000 (reference 12540); `q-wrong-way.independent_loss` returned 140400 (reference 3306).
- **gpt-6-sol--low**: `q-wrong-way.joint_loss` returned 12600 (reference 12540); `q-wrong-way.independent_loss` returned 6690 (reference 3306).

Full staged historical/benign-control rollouts are a separate campaign. They require two blind human reviews per case for a reasoning score. Actual BitAgent/TRM/RLM/Lean/hybrid adapters are the following phase; endpoint and checkpoint identity must be established first.

## Reproduce

```powershell
python -m systemic_risk_bench.campaign --config configs/signed-plan-baseline.json --track quant --output-dir artifacts/quant-replicate-02
```

Use the same source, packets and schemas. The engine does not expose a sampling-seed override. Do not treat one perfect cell on 13 fields as evidence of general crisis reasoning.
