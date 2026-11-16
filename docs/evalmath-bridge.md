# SRB-EM-01: live cohort simulator to EvalMath scoring bridge

**Registration:** 2026-11-16, `configs/evalmath-simulation-v1.json`.
**Source:** `patrickdugan/SystemicRiskBench`, initial simulator from
[commit 75969bc](https://github.com/patrickdugan/SystemicRiskBench/tree/75969bc477fe29d6b31add51244a75c07fc2323d).
**Scorer:** [EvalMath SRB-01, pinned at 1c3e07e](https://github.com/MoralityLabAI/EvalMath/tree/1c3e07ece43cd617b05171d404c53cc8c906dc8c).
**Evidence:** synthetic mechanism calculations, with exact rational scoring
conditional on the exported, quantized simulator outputs. This release runs
no model. It makes no claim about historical stress probabilities or actual
market-maker intervention costs.

The exporter reads the immutable scenario manifest and invokes the existing
`systemic_risk_bench.simulation.simulate` for paired counterfactuals on the
**same** world. Only order-book depth changes between action arms; the exogenous
shock, total capital, leverage/profile, liquidation rule and simulator version
stay fixed. A fixed USD 10,000 cost is assigned to the tripled-depth action
in the declared scoring model. The intervention does not model a real
liquidity facility's financing constraints or availability.

## Registered scenario grid

| Parameter | Registered choices |
| --- | --- |
| Exogenous shock | 4%, 8%, 12%, 30%, 38% |
| Venue depth (USD) | 300,000; 1,000,000; 5,000,000 |
| Portfolio cohort | homogeneous; heterogeneous |
| Capital mode | fixed total, USD 1,000,000 |
| Agents represented | 1,000,000 (0 independent agent model calls) |
| Action A | no liquidity support, baseline depth, cost 0 |
| Action B | triple venue depth, fixed cost USD 10,000 |
| Harm fields | limited-liability investor loss; creditor shortfall |
| Tail statistic | worst 20% of synthetic scenario-mass distribution |
| Catastrophe threshold | USD 300,000 of modeled post-intervention harm |
| Public observation | shock-index only |
| Optional disclosed information | depth tier; cohort profile |
| Scenario masses | 1 each, uncalibrated equal-mass 30-world grid |

There are 30 worlds and 60 underlying simulator calls. The complete
action-by-world loss matrix is *evaluator-only*. It is not a model packet.
The observed shock index deliberately hides depth tier and portfolio profile;
this is a defined partial-observation decision experiment, not evidence that
real-world traders lack these inputs. A query condition grants the model
additional specific information. The bridge does not use the historical
crisis narrative cases because they contain no measured counterfactual
action-by-world post-intervention loss vectors.

## Loss accounting and exactness

In the existing simulator, book-equity loss decomposes into
`limited_liability_investor_loss + creditor_shortfall`. We preserve those
two disjoint components as node losses. Exogenous book loss is a diagnostic;
we never add it to the total. We reject a run that fails the simulator's
convergence flag or whose quantized accounting differs by more than one cent.

The simulator computes IEEE-754 binary64 numbers. Each resulting loss is
serialized as an exact rational number of cents by
`Decimal(str(float_value))` with round-half-even. **Exact arithmetic refers
to the downstream EvalMath scorer on those serialized values.** It does not
upgrade the underlying simulator's numerical accuracy or its calibration.
Published values are conditional on the manifest, source digests, quantization
policy and input law.

The scorer computes the fixed policy floor, observation-constrained policy
floor and full-information oracle, with an exact information-fibre regret
certificate for the two actions. It also computes fractional-tail CVaR
on node harm, plus conditional false-authorization risks for the registered
disclosure queries. Those quantities remain a vector of endpoints.

The `claimed_safe` column is a declared, deliberately misspecified
`exogenous_only_v1` checker: it reports safe iff exogenous book loss is
strictly below the registered catastrophic threshold. The checker overlooks
endogenous market-impact harm, so false authorization can be computed.
It is *not* a human reviewer, a neural grader, or a safety claim by BitAgent.
For the actual evaluator, true harm is defined from the two outcome nodes.
No `selected` field is emitted, since no model has selected a policy.

## Reproduction

From SystemicRiskBench:

```bash
python -m unittest discover -s tests -v
python -m systemic_risk_bench evalmath-export \
  --config configs/evalmath-simulation-v1.json \
  --output artifacts/evalmath_bank.json
```

From a checkout that also has EvalMath at commit `1c3e07ece43cd617b05171d404c53cc8c906dc8c`:

```bash
PYTHONPATH=evalmath/src python evalmath/scripts/score_systemic_risk.py \
  --input artifacts/evalmath_bank.json \
  --output artifacts/evalmath_score.json
```

The [EvalMath bridge workflow](../.github/workflows/evalmath-bridge.yml)
does this cross-repository replay, asserts nonzero observer regret and
strict improvement under depth disclosure, and uploads the export and scored
artifact. Running the two programs on the same source-bound input matters:
the exact math script alone cannot reproduce floating simulator trajectories.

## Limits and next campaign

The actual numeric tasks and recorded historical model responses remain
separate. In particular, 90 model calls on the six numerical tasks do not
represent 90 interventions in this new scenario bank. Joining model choices
requires a separate action-grammar mapping, sealed scenario assignments,
identical visibility/query access, compute budgets and full trace provenance.

Before using the bank as a model evaluation, register the selected model
interface, training/dev/test separation, policy token schema, scenario-group
holdouts, seed schedule, and matched no-information/action baselines.
Compare by grouped scenario seed and report paired differences with
uncertainty across independent groups. The 30 design cells and 60 simulator
calls are a grid of dependent counterfactual outcomes, not independent
financial crisis observations.

The benchmark's fixed-capital versus fixed-per-agent experiments remain
an independent stress track. Current `simulate` changes cohort
composition across the profile switch, so neither that profile contrast nor
the capital mode contrast is a purified synchronization intervention.
