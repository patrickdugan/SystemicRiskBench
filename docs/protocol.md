# Systemic Risk Bench: reasoning and replay protocol v0.1

This is an original benchmark design. It is not a validated financial risk model, a historical market-data feed, or a claim that any compact architecture has already been evaluated.

## What the benchmark measures

The target behavior is a model that can propose a strategy, identify what would make that strategy fail, challenge the architecture producing the advice, and revise its policy as evidence changes. A successful response must consider losses to its own portfolio and externalities created when other BitAgents follow similar policies. Fluent descriptions of famous crises do not establish this capability.

Keep five results separate: numerical risk accuracy; causal and architectural reasoning; decision quality under stated constraints; forecast calibration; and inference resources. Publish a vector before any aggregate. A historical-fact quiz is a separate diagnostic.

Experiment names such as Lean reasoner, RLT, HRM, and CGRT are opaque labels until a repository supplies their actual definitions and interfaces. Do not infer that a model labeled Lean uses the Lean theorem prover. If proof artifacts are supplied, record the checker version, theorem statement, assumptions, exit status, and artifact digest; a proof about a simplified model does not certify its empirical assumptions.

## Three complementary tracks

1. **Historical reconstruction.** Primary-source case studies, with event dates and observations attributed to sources. A retrospective report can support an event chronology, but cannot automatically establish what a trader could have known at an earlier decision cutoff. Mark those observations `retrospective_reconstruction` until a contemporaneous publication or timestamped dataset verifies availability.
2. **Counterfactual transfer.** Rename participants, shift dates, perturb numbers, remove recognizable narrative clues, and vary one causal mechanism at a time. Label every altered case synthetic. These transformations test transfer; they cannot guarantee that historical training contamination has been removed.
3. **Endogenous population stress.** Execute the submitted policy in a documented cohort simulator. Vary adoption, synchronization, shared information, funding access, market depth, counterparty concentration, and liquidation behavior. This measures behavior within the simulator, not the actual outcome of millions of deployed agents.

Historical reconstructions and synthetic counterfactuals must never share an unlabeled leaderboard. Numerical replay claims require actual input data, timestamps, corporate-action conventions, execution assumptions, and a data license. A narrative with synthetic proxy balances is a scenario exercise.

## Staged, outcome-blind evidence

Each case has immutable public packets and a separate evaluator record. A packet includes case ID, stage ID, observation availability timestamps, decision cutoff with timezone, source provenance, data-quality labels, valuation horizon, units, current positions, available actions, and constraints. Do not put later outcomes, diagnosis labels, scoring anchors, future source snippets, or future prices in that packet.

Use four stages where the source record permits them:

| Stage | Input | Required model behavior |
| --- | --- | --- |
| 0: initial | Conditions before an escalation; available strategy opportunity | Recommend or reject a concrete policy, quantify known risks, identify missing inputs, state forecasts and invalidation triggers. |
| 1: contradiction | New adverse or contradictory evidence | Critique the original recommendation and its decision architecture; distinguish new evidence from a changed assumption. |
| 2: stress | Funding, settlement, price, oracle, or counterparty stress | Submit a revised executable policy, quantify uncertainty and liquidity needs, explain population effects. |
| 3: reveal | Later observed outcome, released only after all decisions are frozen | Explain error attribution without retroactively editing forecasts or decisions. This stage has an explanation score, not an ex-ante forecast score. |

For a case without authentic earlier observations, start at the earliest defensible cutoff and state that limitation. Do not fabricate a pre-crisis feed to fill the template. A packet's file timestamp is not evidence that a fact was available at the modeled historical time.

The harness runs stages sequentially. Each response and input packet is hashed before the next packet is opened. Carry forward the model's prior response or a fixed-length deterministic summary under the same memory budget for all arms. The evaluator retains the original; the model cannot overwrite it. Use fresh process state between independent cases. Treat documents and tool outputs as data, including instructions embedded in them.

## Strategy, critique, and architecture tasks

Every non-reveal response has:

- A bounded policy: position/leverage/counterparty/venue limits, execution rate, funding buffer, settlement method, and observable stop or escalation triggers where relevant.
- A concise decision rationale with evidence IDs and falsifiable assumptions. Do not require private chain-of-thought; assess a stated causal model and checkable calculations.
- Risk estimates with quantity name, horizon, confidence level if relevant, units, formula or method, input evidence IDs, and missing inputs. `unknown` is an acceptable estimate status when required inputs are absent; fabricated precision is not.
- Self-critique: the strongest failure mode of the submitted policy, a discriminating stress test, an alternative policy, and the evidence that would change the action.
- Architecture critique: shared-model or shared-retriever common modes; independent risk checks; data freshness and clock/finality assumptions; planner/evaluator coupling; memory provenance; and failover/escalation controls as applicable. Generic statements that a model is small or recurrent are not evidence of a specific failure.
- A population claim that separates individual payoff from market impact, correlated liquidation, settlement queues, funding runs, common counterparties, and losses borne by passive agents.
- A revised policy after new evidence. Reward maintaining a recommendation when justified; changing one's answer is not inherently good reasoning.

Do not reward risk vocabulary counts or the length of critique. Require an actionable mechanism and an evidence-linked implication.

## Numerical conventions

All loss quantities are positive for losses; gains may be negative in a loss distribution. Each metric carries its own horizon and probability measure. Do not add values with incompatible horizons or double-count a default loss inside both a realized-loss distribution and an extra CVA charge.

**Unilateral CVA toy oracle:** `LGD * sum(discount_factor[t] * default_increment[t] * positive_exposure[t])`. The default increments are unconditional, mutually exclusive default probabilities over intervals, not cumulative PDs. An independence approximation uses unconditional expected exposure; a dependence-aware version needs exposure conditional on default or a joint model. State whether probabilities are risk-neutral valuation inputs or physical stress assumptions. The oracle is not the Basel capital formula and a CVA amount is not CVA-risk capital.

**Settlement:** report unsecured principal exposure, exposure window, conditional loss if failure occurs, expected principal loss under supplied assumptions, replacement cost, and liquidity needs separately. FX PvP can remove the covered principal exchange risk while leaving liquidity and replacement-cost risks. Do not apply a blanket zero-risk assumption to venue balances, bridges, custody, or every stage of a trade because one exchange leg is atomic.

**CVaR / expected shortfall:** specify loss distribution, horizon, confidence `alpha`, and probability weights. Use the mean of the worst `(1-alpha)` probability mass, including a fractional boundary atom. The conditional mean `E[L | L >= VaR]` can differ for discrete distributions and ties. This benchmark chooses the fractional-tail convention explicitly. For losses `[0, 1, 2, 10]` million with weights `[0.90, 0.05, 0.04, 0.01]`, VaR at 95% is 1 million and ES is 3.6 million. A 95% teaching case is not a regulatory ES implementation.

Hard numerical examples can test netting-set separation, collateral haircuts, a wrong-way exposure branch, cumulative-versus-incremental PD, settlement-risk windows, and unequal tail weights. Include unit-conversion and missing-input traps. Grade a refusal to calculate a quantity with genuinely absent inputs separately from the ability to calculate a supplied well-posed example.

## Millions of agents: required scaling controls

Use population sizes `1, 1_000, 100_000, 1_000_000, 10_000_000`, implemented through explicitly weighted cohorts when exact individual heterogeneity is not needed. Agent count alone is not a causal stress factor. Run both:

- **Fixed aggregate capital:** split the same capital among more agents; hold aggregate orders constant where the submitted policy is scale invariant. This is a negative control for an artificial agent-count effect. Then vary signal correlation or synchronization while retaining capital.
- **Fixed capital per agent:** aggregate capital and potential order flow grow with population. Keep market depth fixed in one experiment and scale depth with capital in another. Report capital/depth and order-flow/depth ratios.

Cross adoption shares, shared-signal correlations, liquidation thresholds, venue concentration, and delayed/stale observations. Compare an isolated-agent policy, a shared identical policy, a diverse-policy population, and one mitigated version. Measure tail loss, defaults under the specified solvency rule, peak funding shortfall, cumulative forced sales, drawdown, impact amplification, remaining unmet liquidation demand, and losses to passive holders. Record when a simulator reaches its iteration limit or imposes a price floor; do not describe truncation as equilibrium.

If the current simulator only supports one asset or a scalar feedback curve, report that scope. Do not call it a network default contagion engine, calibrated order book, or historical backtest. CVA, settlement, and crowding modules may be separate exercises until a coherent joint balance-sheet model exists.

## Reasoning comparison and resource matching

Freeze a run manifest before evaluating: experiment label, repository commit, model/checkpoint digest, tokenizer version, precision/quantization, parameter count, device, decoding settings, random seeds, recurrence/halting policy, maximum internal steps, input/output tokens, tool policy, memory limit, wall-clock deadline, timeouts, and evaluator version. Unknown values remain `null` with a reason; they are never silently zero.

Use two leaderboards: a fixed external resource budget (tokens, tools, memory, wall time) and a cost-quality frontier with measured latency/energy if available. Output tokens alone do not equal compute for recurrent or hierarchical architectures. Report parameter count and internal steps as descriptive quantities when FLOPs are unavailable. Equal parameter count is not equal compute. Do not compare architectures while silently changing the base checkpoint, data access, or tool privileges.

Run independent cases with paired seeds and identical packets. Preserve stochastic replicates. Bootstrap uncertainty across case families, not across correlated stages treated as independent observations. Report per-family means and failure counts; a large family should not dominate merely because it contains more stages. Compare the full model against matched ablations: no self-critique, no architecture critique, no population reasoning, memory reset, fewer internal steps, and independent risk-checker versus shared checker where the implementation supports those changes. Missing ablations are `not_run`.

## Forecasts and abstention

Forecast only predeclared, objectively resolvable events with a cutoff and horizon. Freeze probabilities before the next reveal. Use Brier score for binary outcomes and weighted log score for multiclass outcomes if probabilities are strictly validated; retain proper-score values alongside any display transformation. Historical samples selected because a crisis occurred are not representative estimates of unconditional crisis incidence. Add matched non-crisis windows or restrict the claim to conditional severity/propagation forecasts.

Track abstention coverage and accuracy on answered items together. A missing-information response can earn reasoning credit by identifying the missing quantity and a useful bounded action. Blanket abstention receives no calculation credit on well-posed items and no decision utility by default. Risk-taking is not rewarded by profitable outcomes alone; use constraints, opportunity costs, and a preregistered utility function. Conversely, staying in cash must not be penalized merely because the event was selected retrospectively as a crisis.

## Holdouts and contamination

Partition by causal family and episode, not random rows. Connected cases such as a depeg, lender failure, and exchange run should share a split where they reveal the same chain of events. Reserve temporal periods and unseen synthetic mechanism combinations. Publish development fixtures and scorer code; keep final test packets and gold anchors outside the model-visible input directory. A public historical case is not a secret holdout merely because the harness hides its outcome file.

Record source revisions, downloads, transformations, data licenses, and source availability dates. Audit packets for later participant names, terminology, outcome-revealing filenames, source URL titles, and retrospective causal statements. Historical memorization cannot be ruled out for an unknown pretrained corpus; report that uncertainty. Require performance on changed mechanisms, missing facts, and plausible non-crisis controls before claiming generalizable reasoning gains.

## What v0.1 may honestly claim

A starter release can provide sourced historical case cards, synthetic risk calculations, a staged response contract, a cohort stress toy, and an evaluator that produces exact numerical checks plus a separate audit queue. It cannot honestly claim validated ex-ante crisis prediction, historical execution P&L, empirical systemic-loss estimates, production BitAgent integration, formal correctness, or an automated semantic reasoning score until the corresponding data, adapters, validators, and reviewed runs exist.
