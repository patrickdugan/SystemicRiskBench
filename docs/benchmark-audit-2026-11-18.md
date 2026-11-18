# Research audit: SystemicRiskBench v0.1 (2026-11-18)

**Scope:** source audit and design recommendations, not a new model evaluation. The findings below describe the repository at the opening of this review. This document travels with the code so a future report can distinguish a harness upgrade from new experimental evidence.

## What already works

- The public historical corpus has 33 retrospective-reconstruction episodes and four explicitly synthetic benign controls, across 74 staged decisions. Public packets are allowlisted and distinguish evaluator-only outcomes from visible information.
- Risk calculators distinguish default increments, wrong-way credit exposure, netting scope, settlement principal risk and fractional-tail expected shortfall.
- The cohort fire-sale simulator separates limited-liability investor losses from creditor shortfall and implements fixed-total-capital headcount invariance as a negative control.
- SRB-EM-01 connects 30 synthetic worlds and 60 genuine paired simulator runs to the pinned EvalMath scorer, with source module hashes and exact cent-quantized scoring inputs.
- The signed-plan arithmetic pilot ran 90 real model calls across 15 model/effort combinations, with a verifiable 13-field reference score for each combination.

These are different types of evidence. The 60 simulator runs are not model calls, the historical cards are not market-tape replays, and the perfect oracle smoke is not a reasoner result.

## Ranked validity risks

| Priority | Risk | Present observation | Practical remedy |
| --- | --- | --- | --- |
| P0 | **Sample size and ceiling** | Six public numerical tasks, 13 fields, only four risk families. Many pilot cells score 13/13. | Treat scores as unit tests, and preregister a genuinely new held-out task-family bank before comparisons. |
| P0 | **Agent action is missing from simulator loop** | SRB-EM-01 evaluates preselected depth interventions; models are not selecting policies and changing order flow. | Wire model-visible observations to constrained actions, execute those actions within the next endogenous step and measure externalities. |
| P0 | **Historical foresight validity** | Narrative retrospective sources lack a complete timestamped as-of archive. | Attach contemporaneous observation timestamps, hashes and accessible information windows. Evaluate later facts only after policy freeze. |
| P1 | **Causal confounding** | The homogeneous/heterogeneous profiles change leverage, reserve and liquidation limit together. Depth is a stipulated action multiplier with fixed cost. | Factor adoption, policy correlation, leverage, reserve, haircut and funding access independently. Price liquidity backstops under stated balance-sheet constraints. |
| P1 | **Independent scoring** | Two attributed human reviewers are required, but independence and the relevance of their evidence refs depend on the operator. Executable-policy constraints have no automated score. | Audit reviewer identity and stage-level evidence refs; grade executable constraints and action regret with deterministic checks. |
| P1 | **Open development set** | Numerical answers are constructed from public task code. Masks may leave narrative identities recoverable. | Freeze separate development and prospective holdout partitions, with protected answers, provenance and release timing. |
| P2 | **Reproducibility coverage** | Previously the CI job was scoped to the EvalMath bridge paths. | Add full Python unit-test, corpus validation and oracle smoke checks on all pull requests. |

## Quantitative interpretation of the pilot

The six numerical questions belong to four groups: credit, settlement, tail and crowding. Three credit questions share a domain and mechanism assumptions. The 13 answer fields are correlated outcomes of those six questions. The 90 calls in the signed-plan pilot include re-use of the same public prompts across models and effort levels.

Even if one model improves in **all four** families, a two-sided exact family-level sign test has a smallest attainable p value of **0.125** (2/2^4), under an independent and exchangeable family-direction null. Those assumptions have not been established by this design. Confidence intervals based on 13 independent answer fields or on 90 independent model calls would seriously overstate precision.

This review adds a descriptive comparison report in `systemic_risk_bench/comparison.py`. It requires the complete six-task pair and identical packet hashes, averages within each family before comparing arms, exposes directional ties and sign-test resolution, and explicitly withholds a confidence interval and model-ranking claim. It does not retroactively strengthen the pilot.

## Next experimental registration: SRB-CF-02

**Scientific question:** does architecture-aware self-critique reduce *realized constrained policy regret and harm to others* when other agents make correlated decisions?

Suggested prospective design, to be frozen before any held-out model run:

1. **Independent causal groups.** Start with a target bank of at least 32 held-out mechanism families spanning funding runs, margin cascades, bank/issuer exposure, liquidity mismatch, custody/settlement, oracle failures and common-model herding. A family is the resampling unit; correlated variants of one underlying crisis remain in its group. Confirm final sample size with a pilot-independent power or precision simulation.
2. **Paired arms.** Same model/checkpoint, budget and observations, with architecture critique enabled versus predeclared ablations. Share the world seed across arms. Separate independent model-training seeds from simulator seeds.
3. **Action space.** Present only an as-of packet and registered feasible actions (size, venue, rate, cash reserve, hedge and backstop budget). Freeze the agent's response before the simulator advances. Record explicit invalid actions and abstentions.
4. **Population treatment.** Fix total capital when testing headcount and signal coordination. Cross independent variations in synchronized arrival, shared model/prompt, funding access and order-book depth. In a separate fixed-per-agent-capital experiment, let aggregate capital grow and report capital/depth explicitly.
5. **Outcomes.** Compute feasible-observation-policy regret, investor loss, creditor loss, funding shortfall, external harm, liquidity use and fractional-tail loss separately. An oracle with privileged state information is an information lower bound, not an achievable policy baseline.
6. **Analysis freeze.** Register primary endpoints, cluster-level effects, incomplete-output policy, multiple-comparison treatment and a family-level uncertainty method. Keep a sealed prospective holdout and make exploratory development results visually distinct.

**Required negative controls:** fixed-capital headcount invariance; zero endogenous impact; independent policies at matched aggregate flow; harmless shocks where a blanket exit incurs cost; and a policy unable to improve the relevant state. Include positive controls where protective action has a mechanically verified effect.

### In-simulator causal identification

A depth tripling action is a useful controlled test. Its economic cost and implementability are currently stipulated. A later version should give liquidity providers capital constraints, order-flow capacity and funding spread. Compare agent interventions against matched random policies and a feasible observation-only oracle. Partition the resulting data by mechanism family, so replicated agents in one world remain a single experimental cluster.

## Historical track and human grading

The corpus can test a model's explicit *mechanism reasoning* today. A prospective as-of trial needs document-availability receipts and a published set of policies that could have been executed at the cutoff. Include calm periods drawn with the same selection process as crisis periods so withdrawal and refusal can receive a real cost.

Human reviews should cite specific stage/response evidence IDs. Adjudicators need calibration cases, disagreement rates by rubric dimension and review blinding to architecture labels. The final grade should retain its components rather than compress a fragile mixture into a leaderboard.

## External motivation and benchmark positioning

Federal Reserve Governor Michael Barr's [16 November 2026 speech](https://www.federalreserve.gov/newsevents/speech/barr20261116a.htm) discusses common AI models and synchronized market responses as potential financial-stability risks. [FinBen (NeurIPS 2024)](https://proceedings.nips.cc/paper_files/paper/2024/hash/adb1d9fa8be4576d28703b396b82ba1b-Abstract-Datasets_and_Benchmarks_Track.html) establishes a broad financial-task benchmark. SystemicRiskBench has a narrower prospective niche: **measure the external harm created when many decision systems act on each other's market conditions**. That claim becomes testable when agent actions causally alter a simulator and independent held-out groups support comparisons.

## Status register

| Artifact | Status |
| --- | --- |
| Public 6-task arithmetic pilot | Executed, descriptive |
| Historical narrative corpus | Published development material |
| SRB-EM-01 depth-intervention replay | Executed synthetic simulation, zero model calls |
| Family-aware pair report | Implemented by this review, no new runs |
| Full general-purpose CI | Added by this review |
| SRB-CF-02 prospective closed-loop agent trial | Proposed, unregistered |
| Historical as-of backtest and independent human reasoning scores | Pending |
