# SRB-CF-02-DEV: execute a policy before the cascade

The policy harness lets an adapter choose a budgeted liquidity action from a
public observation. It freezes that choice before the simulator computes the
cascade. The selected action changes venue depth, which changes the price
impact of subsequent liquidation orders.

`configs/policy-simulation-v1.json` defines a public development exercise.
SRB-CF-02 remains a proposed prospective study in the
[research audit](benchmark-audit-2026-11-18.md). This implementation supplies
an executable interface and reference checks for that future work.

## Run the fixtures

From the repository root, with Python 3.10 or later:

```bash
python -m systemic_risk_bench policy-run \
  --config configs/policy-simulation-v1.json \
  --fixture baseline \
  --output artifacts/policy-baseline.json

python -m systemic_risk_bench policy-run \
  --config configs/policy-simulation-v1.json \
  --fixture always_support \
  --output artifacts/policy-support.json
```

Both fixtures execute deterministic Python policies and make zero model calls.
The baseline chooses `no_liquidity_support`; `always_support` chooses
`triple_depth_backstop` under the default budget. Fixture results establish
the behavior of the harness and its stipulated interventions.

The committed [development fixture report](../results/policy-development-v1/REPORT.md)
includes complete receipts for both built-in policies and the example adapter.

## What the agent sees and controls

The default manifest preserves the SRB-EM-01 grid:

| Setting | Value |
| --- | --- |
| Visible shock | 4%, 8%, 12%, 30% or 38% |
| Hidden depth | USD 300,000; 1,000,000 or 5,000,000 |
| Hidden cohort profile | Homogeneous or heterogeneous |
| Total initial portfolio capital | USD 1,000,000 |
| No-support action | Depth multiplier 1; cost USD 0 |
| Backstop action | Depth multiplier 3; cost USD 10,000 |
| Action budget | USD 10,000 per decision |
| Scenario mass | Equal mass for each of the 30 grid cells |
| Tail level | Worst 20% of scenario mass |

Public packets expose the shock as an exact rational string, initial capital,
the action budget and the available actions with their costs and depth
multipliers. Depth, cohort identity and counterfactual outcomes stay in the
evaluator's state. There is one choice for each distinct public packet, so
the default run freezes five decisions. That choice applies to every hidden
world sharing the observation.

All adapter calls finish before the evaluator runs the counterfactual bank.
The bank executes both depth actions in each world, producing 60 simulator
outcomes. These outcomes support paired evaluation of the selected policy.
Each simulated cascade keeps the existing liquidation rule throughout its
rounds; the adapter has one decision before that cascade begins.

The backstop cost is charged to an external sponsor in the scoring objective.
Scoring records that expense separately from the simulator's cohort balance
sheets. The budget limits the admissible action on each decision. Financing
the sponsor and replenishing its budget require a richer economic model.

## Attach an adapter

```bash
python -m systemic_risk_bench policy-run \
  --config configs/policy-simulation-v1.json \
  --adapter-argv '["python", "my_policy_adapter.py"]' \
  --timeout 60 \
  --output artifacts/policy-adapter.json
```

To check the subprocess interface with the supplied example:

```bash
python -m systemic_risk_bench policy-run \
  --config configs/policy-simulation-v1.json \
  --adapter-argv '["python", "examples/policy_adapter.py"]' \
  --output artifacts/policy-threshold-fixture.json
```

That example uses a hand-written rule: select the strongest affordable depth
action when the observed shock is at least 30%, and choose the cheapest action
otherwise. It contains no model inference. The generic adapter runner still
reports its model-call count as null because it cannot infer the behavior
of an arbitrary subprocess from its response.

Each process receives one JSON request through stdin with protocol
`srb.policy.adapter.v1`, a `packet` and an instruction. Write exactly one JSON
object to stdout. The response selects an action by name:

```json
{
  "action": "triple_depth_backstop",
  "rationale": "The observed shock warrants spending the available backstop budget."
}
```

`rationale` is optional and must be a string when supplied. The harness grades
the executed action; reviewing the rationale remains a separate task.
Unexpected response fields, invalid JSON and unavailable actions produce
explicit failed receipts. A timeout or adapter failure also invokes the
baseline fallback. Every affected world remains in the denominator, and
the report marks the fallback so readers can separate policy choices from
execution failures.

The report records `adapter_invocations`. An adapter may invoke a model
several times or use deterministic code, so `model_calls` remains null for
adapter runs. The built-in fixtures report zero model calls. Token and
compute budgets belong to the inference wrapper and need their own measurement.

## Read the score

In a `srb.policy.run.v1` report, `scores` contains the policy comparison. Each decision has a
receipt with its response, status and `packet_sha256`; `selected_action`
records the executed choice, while `fallback_used` identifies a failure
handled by the baseline. The run's `evidence_status` is `public_development`.

A completed evaluation has `run_status: "complete"`. If a cascade fails to
converge or scoring fails, the CLI saves the frozen receipts with
`run_status: "evaluation_failed"`, an `evaluation_error` and `scores: null`,
then exits with status 2. This keeps collected decisions available for audit.
Unusable numeric configurations are rejected before any adapter call.

For a world and action, total cost is the sum of limited-liability investor
loss, creditor shortfall and the stipulated action cost. Investor loss and
creditor shortfall form disjoint components in this simulator's accounting.
Exogenous shock loss is already included in those outcomes.

| Reported policy | How its action is chosen |
| --- | --- |
| Selected policy | The frozen adapter or fixture response for the public packet, including declared fallbacks |
| Baseline | No liquidity support in every world |
| Observation oracle | The feasible action with the lowest mean total cost across worlds sharing the same public observation |
| Perfect-information bound | The feasible action with the lowest total cost in each fully observed world |

The observation oracle uses the evaluator's counterfactual matrix to fit the
best action for each observation under the declared scenario masses. Its
decisions obey the same visibility restriction as the selected policy. It is
a benchmark computed on this development grid; learning that policy from
separate data remains future work.

Expected regret compares mean total cost with the observation oracle. Its
aggregate value is nonnegative for admissible policies on the same bank.
A world-level difference can be negative because the observation oracle
optimizes over a group of hidden worlds. The information gap measures how
much lower the mean cost could become with full state access.

Each policy also receives a fractional-tail expected-shortfall score for
total cost, including intervention costs. When the tail boundary cuts through
a world's mass, the score includes only the required fraction of that mass.
The oracle minimizes mean cost, so another policy can have a better tail
score. A tail-optimal oracle would require a separate objective and analysis.

The exporter rounds finite simulator losses to cents with its declared
round-half-even rule. Scoring then uses exact rational arithmetic. This
preserves exact comparisons on the exported values; simulator trajectories
still use binary64 arithmetic.

## Evidence and study boundaries

The report binds configuration, public packets, frozen decisions and the
counterfactual bank to content hashes, and records source hashes and Python
runtime details for replay. Configuration hashes use canonical JSON content.
Keep the complete report when comparing runs. Those hashes make changes
detectable when checked against a trusted copy. The public development
manifest remains available to anyone running an adapter.

Adapter processes run with the operator's host access. Packet allowlisting
controls the request payload; a protected evaluation needs process isolation
and inaccessible evaluator files.

The 30 worlds share one fire-sale simulator and a small parameter grid.
Independent mechanism groups remain a study-design requirement. Population
size describes weighted capital cohorts, while model decisions occur once per observation.
Changes in the two cohort profiles jointly alter leverage and reserve policy,
so their contrast cannot isolate coordination.

This harness measures the consequences of choosing a stipulated backstop.
Order placement by model-controlled investors, repeated decisions during the
cascade and funding constraints remain extensions. A prospective SRB-CF-02
trial also needs a frozen model protocol, held-out scenario groups and a
justified sample size before collecting model outcomes.
