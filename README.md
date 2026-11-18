# Systemic Risk Bench

Version 0.1.0 — a standalone research benchmark for BitAgent and compact
reasoners on financial strategy, self-critique, architecture critique and
population externalities. Lean reasoner, RLT, HRM and CGRT are experiment labels;
this release does not guess their definitions or claim to have evaluated them.

The central question: **does an agent recognize when a strategy that looks good
for one portfolio becomes fragile when millions of agents herd capital into it?**

The first corpus contains **33 historical episodes / 66 staged decisions**:
18 traditional-finance cases and 15 crypto/DeFi cases. Four separately labeled
synthetic benign controls add eight decisions. Six numerical tasks supply 13
independently tested answer fields. A cohort stress matrix represents populations
from one to ten million agents without executing millions of model calls.

**Evidence map (v0.1):**

| Track | Available result | Interpretation |
| --- | --- | --- |
| Historical mechanisms | 33 retrospective episodes plus four synthetic benign controls; 74 staged decisions | Public development cases, without an as-of price-tape backtest or independent reasoning grade |
| Quantitative reasoning | Six questions, 13 scored fields, four causal families | Small arithmetic pilot; many model/effort cells already reach the ceiling |
| Cohort population stress | Weighted synthetic cohorts representing up to ten million agents | Mechanistic stress simulation, zero independent agent calls |
| EvalMath SRB-EM-01 | 30 worlds, 60 paired simulation outcomes | Exact scoring *after* cent quantization of deterministic simulator outputs; no model policy rollout |

The [18 November research audit](docs/benchmark-audit-2026-11-18.md) prioritizes policy-in-the-loop population experiments, held-out causal families, historical as-of receipts and trustworthy uncertainty estimates. [Core validation](.github/workflows/tests.yml) runs tests and corpus/reference checks on every pull request.

## Run locally

Python 3.10+; no runtime dependencies, API keys or model downloads. From this directory:

```powershell
python -m unittest discover -s tests -v
python -m systemic_risk_bench validate
python -m systemic_risk_bench smoke --output-dir artifacts/reference
python -m systemic_risk_bench list
python -m systemic_risk_bench packet --case tf_1982_latam --stage 0 --masked --output artifacts/packet.json
python -m systemic_risk_bench quant --output artifacts/quant.json
python -m systemic_risk_bench stress --output artifacts/stress.json
```

The committed [reference smoke](examples/reference-smoke.json) uses oracle
fixtures and makes **zero model calls**. Its perfect arithmetic score is a
harness check. It is not a reasoner result. Generated run artifacts go in the
ignored `artifacts/` directory.

## What a model must do

At the first stage, recommend a bounded policy, identify missing information,
quantify supported risk and state what would falsify the recommendation. At the
next stage, receive new evidence and revise or defend the policy with explicit
reasons. Every case asks the model to challenge its own strategy and the
architecture producing it: objective misspecification, short memory, shared
signals, stale oracles, correlated critics, verifier assumptions and execution
or settlement boundaries.

Population analysis must distinguish fixed total capital from fixed capital per
agent, capacity from executable liquidity, private risk reduction from losses
imposed on others, and solvency from funding access. A proof or deterministic
verifier can establish a stated invariant while leaving empirical liquidity and
legal assumptions unresolved.

The [case catalog](docs/case-catalog.md) links the primary sources. Traditional
finance covers sovereign debt, bank runs, portfolio insurance, currency crises,
LTCM, quant deleveraging, Lehman/AIG, euro stress, the 2010 flash crash, CHF,
volatility products, March 2020, Archegos, LDI and SVB. Crypto covers Mt. Gox,
the DAO, exchange flash crashes, Maker liquidations, bridge/security failures,
UST, Celsius, 3AC, Mango, FTX, USDC, Euler, Curve/Vyper and Bybit.

These are **narrative historical reconstructions**, with clearly labeled
synthetic role observations. The corpus has no historical order-book tape or
execution-P&L backtest. Each case stores source scope, chronology cautions,
later outcomes and evaluation anchors separately from the public stage packet.
Public export uses an allowlist and never includes those evaluator fields or
future stages. Masking drops identifying metadata and substitutes explicitly
listed entities; narrative identification and pretraining contamination remain
possible. All committed cards are public development material, not hidden tests.

## Connect an experiment

Write an adapter executable that reads one JSON request from stdin and writes
one JSON response to stdout. Diagnostics belong on stderr. The request includes
`packet`, `prior_responses`, `experiment` metadata and protocol instructions.
Each stage starts a new process; prior replies preserve the decision history.
The adapter is responsible for inference, checkpoint loading and memory policy.

```powershell
python -m systemic_risk_bench run --adapter-argv '["python","examples/fixture_adapter.py"]' --experiment configs/experiment.template.json --output artifacts/fixture-quant.json
python -m systemic_risk_bench run --adapter-argv '["python","examples/fixture_adapter.py"]' --experiment configs/experiment.template.json --track history --cases tf_1982_latam --masked --output artifacts/fixture-history.json
python -m systemic_risk_bench compare --runs artifacts/fixture-quant.json artifacts/fixture-quant.json --output artifacts/comparison.json
```

The supplied adapter is an **empty-answer fixture**, not a model or a competitive
baseline. Replace its argv with the actual Lean/RLT/HRM/CGRT inference wrapper.
Numerical replies put exact answer names in `estimates`, e.g.
`{"estimates":{"cva":23400}}`. Missing fields receive zero calculation credit;
duplicates, unknown fields and malformed numbers are rejected.

For exactly two complete numerical runs on the same packet hashes, `compare`
also emits a `paired_numeric` diagnostic. It reports the difference in
accuracy within each of the four risk families and the discrete resolution
of an exploratory family-level sign test. Even a win in all four families
has a best possible two-sided p value of 0.125; the output explicitly
withholds model-ranking and confidence-interval claims. Unmatched runs
receive a `not_applicable` diagnostic.

The runner records packet/config digests, responses, failures and host wall
time. It enforces a per-call wall timeout. Token, tool, memory, recurrence,
FLOP and energy budgets must be enforced and measured by the experiment wrapper;
unknown measurements stay null. The runner does not provide process isolation:
trusted adapter code can read host files. For a defensible blind evaluation,
serve only exported packets to the inference process in an independently
isolated environment with evaluator files inaccessible.

## Compare reasoning

Publish a vector: numerical family accuracy, human-audited reasoning,
constraint compliance, forecast calibration, latency and resources. The current
scorer automatically measures numerical accuracy; it does not pretend to judge
causal reasoning from keywords. [The audit rubric](contracts/rubric.json) allocates
60 reasoning points across causal understanding, strategy revision, self-critique,
population effects and architecture critique. Two reviewers, blinded to
experiment label, must cite response/evidence references. Disagreements stay
visible until adjudicated.

```powershell
python -m systemic_risk_bench audit --run artifacts/fixture-history.json --reviews artifacts/reviews.json --output artifacts/audit.json
```

Reviews bind to the canonical JSON SHA-256 of the run. See
[the runtime contract](docs/runtime-contract.md) for their format. No combined
100-point leaderboard is emitted while executable-policy constraints and
forecast targets remain unevaluated. Binary Brier scoring is available through
`calibration`; freeze forecast targets, horizons, probabilities and missing-data
penalties before revealing outcomes. A crisis-selected sample cannot establish
unconditional crisis incidence. The four synthetic benign controls test
indiscriminate withdrawal, but do not substitute for matched historical calm
windows.

Use identical packets, paired seeds and checkpoint/tool budgets. Hold out whole
episodes and causal families; group connected 2022 crypto failures together.
Report uncertainty across families rather than treating stages as independent
replicates. Compare no-critique, no-architecture-critique, no-population-reasoning,
memory-reset and internal-step ablations where the actual models support them.
See [the full protocol](docs/protocol.md).

## EvalMath causal-risk replay (synthetic simulator)

The [SRB-EM-01 live bridge](docs/evalmath-bridge.md) exports 30 registered
scenario worlds and 60 paired depth-intervention simulations, with investor
losses and creditor shortfall separately accounted for. It connects the
existing cohort fire-sale simulator to
[EvalMath SRB-01](https://github.com/MoralityLabAI/EvalMath/pull/38),
which scores observable-policy regret, counterfactual loss, exact
fractional-tail harm and the effect of score disclosure on a registered
synthetic exogenous-only safety checker.

```powershell
python -m systemic_risk_bench evalmath-export --config configs/evalmath-simulation-v1.json --output artifacts/evalmath_bank.json
```

The exporter is evaluator-only and contains privileged counterfactual
outcomes. It has no model calls, calibrated market frequencies, or historical
replay claims. The cross-repository CI pins the EvalMath scorer at an exact
commit and archives both the input bank and exact score output.

## Risk and BitAgent integration

[Risk conventions](docs/risk-and-simulation.md) distinguish unilateral CVA,
wrong-way credit loss, legal netting, settlement principal/liquidity exposure,
VaR and fractional-tail CVaR/ES. The fire-sale simulator is deliberately
synthetic and reports capital assumptions, numerical termination, investor
losses and creditor shortfall separately.

`bitagent-packet` projects a native `bitagent_strategy_covenant_v1` JSON object
into a read-only risk review packet. It uses the existing mandate types and
does not assume that a leverage limit provides exposure/default curves needed
for CVA. [Repository seams and next milestones](docs/integration.md) describe
the remaining model and executable-policy wiring.

The [first signed-plan numerical baseline](results/signed-plan-numeric-v1/REPORT.md)
contains 90 actual model calls across five models and three reasoning levels.
[Rollout operations](docs/rollout-operations.md) explain the local result webhooks,
historical campaign, resource telemetry and reproducibility limits.

Compact-architecture adapters, independent human reviews, protected test cases
and calibrated historical data remain separate study milestones. Numerical
accuracy is reported independently of crisis-reasoning quality.

The [compact-adapter queue](docs/compact-adapter-queue.md) registers verified
BitAgent/ControlTRM artifacts and the located RLM, Lean/CGRT and hybrid entry
points. The BitAgent HTTP wrapper and owned-server launcher enforce the user's
GPU reservation before inference; prepared packets are not counted as model runs.

See [repository migration and active jobs](docs/repository-migration.md) for the
existing campaign locations while the standalone checkout takes over new work.
