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
python -m systemic_risk_bench run --adapter-argv '["python","examples/fixture_adapter.py"]' --experiment configs/agent-revision-fixture.json --output artifacts/fixture-quant.json
python -m systemic_risk_bench run --adapter-argv '["python","examples/fixture_adapter.py"]' --experiment configs/agent-revision-fixture.json --track history --cases tf_1982_latam --masked --output artifacts/fixture-history.json
python -m systemic_risk_bench compare --runs artifacts/fixture-quant.json artifacts/fixture-quant.json --output artifacts/comparison.json
```

The supplied adapter is an **empty-answer fixture**, not a model or a competitive
baseline. Replace its argv with the actual Lean/RLT/HRM/CGRT inference wrapper.
Numerical replies put exact answer names in `estimates`, e.g.
`{"estimates":{"cva":23400}}`. Missing fields receive zero calculation credit;
duplicates, unknown fields and malformed numbers are rejected.

The runner records packet/config digests, responses, failures and host wall
time. It enforces a per-call wall timeout. Token, tool, memory, recurrence,
FLOP and energy budgets must be enforced and measured by the experiment wrapper;
unknown measurements stay null. The runner does not provide process isolation:
trusted adapter code can read host files. For a defensible blind evaluation,
serve only exported packets to the inference process in an independently
isolated environment with evaluator files inaccessible.

## Agent continuation and evidence-revision evaluation

[SRB-REV-01](docs/agent-revision-continuation.md) adds a **two-process bounded-memory agent eval** inspired by [Beyond Bayes BB-CQ-05](https://github.com/patrickdugan/beyond-bayes/pull/24) and [LoopedTransformers LRM-REV-03](https://github.com/MoralityLabAI/LoopedTransformers/pull/209). The agent receives twelve named evidence reports, compresses them to a declared numeric state, then receives six host-verified corrections in a fresh process. Its previous transcript and replies are withheld from the update packet.

Compare a **4-bit count** contract with a **12-bit named bitmap** using the exact Bayesian reference matching each arm's information. The count-only information loss is recorded separately from model approximation error. A deterministic [fixture adapter](examples/agent_revision_fixture_adapter.py) checks the transport and oracle; it is not an AI agent or a model result. The underlying trusted adapter could use external persistence, so physical memory enforcement and source authenticity require separate isolation.

~~~bash
python -m unittest discover -s tests -p 'test_agent_revision.py' -v
python -m systemic_risk_bench agent-revision --adapter-argv '["python","-m","examples.agent_revision_fixture_adapter"]' --experiment configs/agent-revision-fixture.json --mode count --cases 16 --output artifacts/revision-count.json
python -m systemic_risk_bench agent-revision --adapter-argv '["python","-m","examples.agent_revision_fixture_adapter"]' --experiment configs/agent-revision-fixture.json --mode bitmap --cases 16 --output artifacts/revision-bitmap.json
~~~

## Financial evidence revision and BitAgent model transport

[SRB-REV-02](docs/finance-revision.md) extends bounded-memory correction tasks to
synthetic price-feed, collateral and counterparty decisions. The adapter must
preserve a 4-bit count or 12-bit named bitmap across independent calls, update a
three-regime forecast and choose a registered hypothetical risk action. The
evaluator reports matched-information Brier error, policy regret, actual
synthetic loss and missed escalation checks separately.

```bash
python -m unittest discover -s tests -p 'test_finance_revision.py' -v
python -m systemic_risk_bench finance-revision --adapter-argv '["python","-m","examples.finance_revision_fixture_adapter"]' --experiment configs/finance-revision-fixture.json --mode count --cases 18 --output artifacts/finance-count.json
python -m systemic_risk_bench finance-revision --adapter-argv '["python","-m","examples.finance_revision_fixture_adapter"]' --experiment configs/finance-revision-fixture.json --mode bitmap --cases 18 --output artifacts/finance-bitmap.json
```

The fixture is a deterministic mathematical oracle. The separate
[llama.cpp revision adapter](adapters/revision_llamacpp.py) can send those same
packets to a locally served, artifact-verified BitAgent. CI tests the adapter
using a fake HTTP server and makes no neural calls. Reported two-process
continuation does not certify a physically isolated memory budget or a reset
model server. Financial actions are read-only synthetic choices.

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
