# SRB-CF-02-DEV fixture results

Executed on 18 November 2026 with CPython 3.12.14. The public development
grid contains 30 worlds, combining five shocks with three depths and two
cohort profiles. Each run froze five policy decisions before computing its
60 counterfactual simulation outcomes. All 15 decisions across the fixture
runs completed successfully.

These runs made **zero model calls**. The built-in baseline and always-support
fixtures record that count directly. The supplied threshold adapter uses
hand-written Python and launches five subprocesses. Its report retains
`model_calls: null`, because the generic runner cannot establish model use
inside an arbitrary adapter. The inspected source establishes zero inference
for this particular fixture, as recorded in [summary.json](summary.json).

## Costs on the declared grid

Total cost adds limited-liability investor loss, creditor shortfall and the
action cost charged to an external sponsor. The table rounds exact rational
results to cents for display. Scenario masses are equal and illustrative.
ES at 80% averages total cost over the worst 20% of scenario mass, including
the required fraction when a world straddles the tail boundary.

| Policy | Mean total cost (USD) | Mean action cost (USD) | ES at 80% (USD) |
| --- | ---: | ---: | ---: |
| Baseline: no support | 501,679.12 | 0.00 | 1,015,030.10 |
| Always support | 461,699.78 | 10,000.00 | 1,002,872.77 |
| Threshold fixture: support at shocks of at least 30% | 494,915.56 | 4,000.00 | 1,002,872.77 |
| Observation oracle | 459,699.78 | 8,000.00 | 1,002,872.77 |
| Perfect-information bound | 457,473.27 | 4,666.67 | 997,431.57 |

The observation oracle selects support at shocks of 8%, 12%, 30% and 38%.
It leaves the 4% shock unsupported. Always supporting therefore incurs
USD 2,000 more mean cost than this comparator, through spending on the
lowest-shock group. The threshold fixture leaves support unused at 8% and
12%, producing mean regret of USD 35,215.79 against the same comparator.

Full state access lowers the optimum mean cost by another USD 2,226.50.
That information gap follows from permitting different actions for hidden
depths and cohort profiles. The observation oracle must choose one action
for every world sharing a visible shock. It is fitted after observing the
counterfactual matrix and minimizes mean cost on this public grid. Its tail
score describes the resulting policy; tail optimization would require a
separate objective.

Losses can exceed the USD 1,000,000 initial portfolio equity because total
cost includes creditor shortfall and the sponsor's expense. The JSON reports
preserve the investor and creditor components separately.

## Receipts and replay

| Artifact | Contents |
| --- | --- |
| [summary.json](summary.json) | Exact rational scores, selected actions, source hashes and canonical report hashes |
| [baseline.json](baseline.json) | Five frozen no-support decisions and their complete evaluator bank |
| [always-support.json](always-support.json) | Five frozen support decisions and their complete evaluator bank |
| [threshold-fixture.json](threshold-fixture.json) | Five subprocess receipts, responses and the complete evaluator bank |

Each report includes packet hashes, the decision digest computed before
simulation, the configuration and the source digests used for the run.
The source hashes in the summary match the committed module contents used
to generate these artifacts. Report hashes use canonical JSON with sorted
keys and compact separators, so whitespace in the published file is excluded.

From the repository root:

```bash
python -m systemic_risk_bench policy-run \
  --config configs/policy-simulation-v1.json \
  --fixture baseline \
  --output artifacts/policy-baseline.json

python -m systemic_risk_bench policy-run \
  --config configs/policy-simulation-v1.json \
  --fixture always_support \
  --output artifacts/policy-support.json

python -m systemic_risk_bench policy-run \
  --config configs/policy-simulation-v1.json \
  --adapter-argv '["python", "examples/policy_adapter.py"]' \
  --output artifacts/policy-threshold-fixture.json
```

Run timestamps and measured subprocess time change on replay. The source-bound
policy scores and selected actions can be compared through the report fields.
The [policy harness guide](../../docs/policy-simulation.md) explains the action
contract, failed-decision receipts and scoring conventions.

## Scope of the evidence

The threshold rule is an illustrative interface fixture with an explicit
30% cutoff. Its source contains no fitting routine. All results concern one
fire-sale mechanism and correlated variations of its parameters. Repeating
the grid under another fixture preserves those same worlds.

Depth multiplication and its price are stipulated. The sponsor's cost enters
scoring separately from portfolio balance sheets, while its financing and
funding capacity remain unmodeled. The existing simulator supplies the
liquidation rule throughout each cascade; a policy chooses one intervention
before it begins. Model-controlled investor orders and decisions during the
cascade require further implementation.

SRB-CF-02 remains a proposed prospective study. These receipts establish
execution and exact scoring for the public development harness. A model
comparison will need its own frozen protocol and held-out mechanism groups.
