# SRB-REV-02: Financial policy revision after superseded evidence

**19 November 2026.** Development-stage extension of [SRB-REV-01](agent-revision-continuation.md). The evaluator uses invented financial scenarios, deterministic public issuer roots, the exact fixed three-regime Bayes law and two-process state transfer.

## Registered question

After a named risk record is superseded, does the agent update its **observable policy action** using only the state it retained? Compare an exact 4-bit count summary to a 12-bit named bitmap, separately measuring belief approximation error and decision regret. The report records missing responses in the denominator. Each root receives a distinct initial and update adapter subprocess, with no `prior_responses` replay.

The benchmark models three **synthetic** risks in equal rotation:

- **Price feed:** BTC collateral marks summarized as twelve provider freshness and deviation control bits. The host supersedes six provider checks.
- **Collateral:** secured-loan collateral eligibility and haircut checks, later revised.
- **Counterparty:** hypothetical derivatives exposure with twelve reliability and settlement checks.

The publicly visible control bit means `1 = check passed` and `0 = check breached`. Six positions were provisional fair-noise observations, chosen behind the initial-stage information boundary; their revised values follow the synthetic three-regime sensor model. All records, costs and probabilities are invented. There are no market forecasts, live feeds, orders, wallet actions or brokerage authorization.

## Exact information and policies

The initial model reply has **exactly** `memory`, `posterior`, and `action`. The host validates the numeric memory encoding against the old observations. At the update stage the only allowed reply fields are `posterior` and `action`. The packet withholds old reports and prior responses and includes six versioned host-verified correction receipts. These are development HMACs with reproducible source-derived keys; they provide structural checks only.

The actions are `continue`, `de_risk`, and `halt_and_escalate`. The evaluator chooses the Bayes-optimal action by minimizing expected loss under the **information-matched** posterior. At ties the action tuple order is fixed. Its invented cost schedules are part of the public `SCENARIOS` constant in [finance_revision.py](../systemic_risk_bench/finance_revision.py):

| Scenario | Action | Healthy | Stressed | Crisis |
| --- | --- | ---: | ---: | ---: |
| Price feed | continue | 0 | 3 | 15 |
| Price feed | de_risk | 0.8 | 1.5 | 4 |
| Price feed | halt_and_escalate | 2.5 | 2.5 | 2.5 |
| Collateral | continue | 0 | 4 | 18 |
| Collateral | de_risk | 1 | 2 | 5 |
| Collateral | halt_and_escalate | 3 | 3 | 3 |
| Counterparty | continue | 0 | 4 | 12 |
| Counterparty | de_risk | 0.6 | 1.4 | 3.5 |
| Counterparty | halt_and_escalate | 2.3 | 2.3 | 2.3 |

The **belief approximation** metric is unhalved squared L2 distance to that arm's conditional Bayes posterior. The **memory information gap** is the squared distance between the count-conditional and complete-bitmap posterior, scored host-side for every root. **Policy regret** is the expected loss of the chosen action under the arm's matched posterior minus the minimum available expected loss. We also record the action's full-information regret and realized loss under the hidden synthetic regime, with no inference that these scores estimate real-world return distributions.

A missing initial response, invalid memory, malformed forecast, invalid action or missing update is charged the fixed maximum unhalved Brier penalty **2.0** and a registered policy-regret penalty **20.0**. Coverage is reported alongside scores. This policy penalty exceeds the largest possible regret across the fixed schedules, and is an evaluator convention.

Use whole issuer roots, balancing all three risk families. The same roots and policy schedules are used for count and bitmap runs. Report individual family results and uncertainty across roots for any later model comparison. Synthetic stress cases are deliberately distribution-controlled; they do not measure financial-crisis prevalence.

## Reference-only reproduction

```bash
python -m unittest discover -s tests -p 'test_finance_revision.py' -v
python -m unittest discover -s tests -q
python -m systemic_risk_bench finance-revision --adapter-argv '["python","-m","examples.finance_revision_fixture_adapter"]' --experiment configs/finance-revision-fixture.json --mode count --cases 18 --output artifacts/finance-count.json
python -m systemic_risk_bench finance-revision --adapter-argv '["python","-m","examples.finance_revision_fixture_adapter"]' --experiment configs/finance-revision-fixture.json --mode bitmap --cases 18 --output artifacts/finance-bitmap.json
```

These commands invoke a deterministic oracle, which reads the public packet and performs exact math in ordinary Python. Its perfect scoring validates plumbing and policy arithmetic. It supplies **zero neural evidence**.

## Connecting an actual local BitAgent

The model adapter at [adapters/revision_llamacpp.py](../adapters/revision_llamacpp.py) talks only to a local loopback llama.cpp endpoint. It reuses the existing verified base/LoRA checksum and active-adapter preflight, sampling configuration and GPU gate from [adapters/llamacpp.py](../adapters/llamacpp.py). The runtime must already be started by the operator using the checked local launcher. The adapter requires a single completion, rejects truncation and tool calls, and constrains the response to JSON. Each call is a fresh user message.

The [SRB-REV-03 protocol](finance-revision-stress.md) supplies the current model registration. Replace `configs/local-bitagent.template.json` placeholders in a **machine-local** file under ignored `artifacts/` and set its `max_tokens` to 1024. Preserve the measured base and LoRA SHA-256 values and local paths. Make a separate experiment file from [finance-revision-bitagent-v3.template.json](../configs/finance-revision-bitagent-v3.template.json), registering the checkpoint, local server, named panel, manifest digest, seed and budgets before any run. The production model adapter requires explicit model registration and rejects unfilled templates.

Example for the first six public development roots after the server is independently launched:

```powershell
python -m systemic_risk_bench finance-revision --panel pilot --manifest configs/finance-revision-panels.json --adapter-argv '["python","-m","adapters.revision_llamacpp","--config","artifacts/bitagent-readiness/local-config.json"]' --experiment artifacts/finance-revision-bitagent.json --mode count --timeout 300 --output artifacts/finance-bitagent-count-6.json
python -m systemic_risk_bench finance-revision --panel pilot --manifest configs/finance-revision-panels.json --adapter-argv '["python","-m","adapters.revision_llamacpp","--config","artifacts/bitagent-readiness/local-config.json"]' --experiment artifacts/finance-revision-bitagent.json --mode bitmap --timeout 300 --output artifacts/finance-bitagent-bitmap-6.json
```

The proposed development campaign is 48 roots per arm (16 of each family) after a CPU transport preflight and six-root local pilot. This needs 96 model completions per arm if all 48 cases succeed. The repository does not ship the actual weights or model-serving environment, and GitHub-hosted CI only tests the deterministic fixture and a fake HTTP transport.

The evaluator records SHA-256 packet digests, host wall time and adapter receipts. The local adapter emits structured server telemetry to stderr; the runner validates it before truncating the diagnostic suffix. Token costs retain their measured coverage, and unsuccessful completions retain usage when supplied by the server. For report release, scrub local paths and model-serving metadata.

**Important memory boundary:** the original history is absent from the second JSON packet, and the client disables prompt caching. The persistent llama.cpp server may still retain KV caches or other out-of-band state. This source-only harness cannot certify a physical 4-bit or 12-bit memory limit. The flags `physical_memory_enforced=false` and `model_server_state_reset_verified=false` remain in the output even if a model returns accurate answers. A stronger study will run a resettable isolated model server per phase, then train or test on independently seeded private issuer roots and independently verify model identity and resource receipts.

This study scores decisions as hypothetical read-only choices. No benchmark output is sufficient to authorize real trading.
