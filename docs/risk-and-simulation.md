# Risk conventions and simulation limits

All numerical inputs in v0.1 are synthetic, denominated in the question's
currency units, and refer to the explicitly stated horizon. They are exercises,
not estimates for a live counterparty or a regulatory capital implementation.

## Credit valuation adjustment

The benchmark uses **credit valuation adjustment (CVA)**. For a deliberately
independent exposure/default example, unilateral CVA is
`(1-recovery) * sum(discount_i * EE_i * dPD_i)`.
`dPD_i` denotes an unconditional probability mass of first default in a disjoint
interval, not a conditional hazard or a cumulative probability reused each
period. Pricing probabilities and real-world forecasts are distinct inputs.
The term-structure fixture stipulates a common risk-neutral pricing measure.

The wrong-way fixture computes `LGD * E[exposure(state) * PD(default|state)]`
in one period with discount one. It compares that with a product of marginal
expectations and asks why the latter understates the specified dependence.
It is not a full joint default-time model. Collateral, margin periods, netting
enforceability, exposure paths and recovery can all change the result.

The conceptual basis is the BIS description of CVA and counterparty-level
expected losses in [MAR50](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/50/inforce/2023-01-01/published/2020-07-08).
The implemented toy calculation is not the Basel CVA capital calculation.

## Settlement

For an explicitly unprotected pay-away interval, the toy expected principal
loss is `principal * probability_of_failure_in_that_interval * LGD`.
Functioning payment-versus-payment makes this particular principal-loss term
zero. Replacement cost, missing incoming currency, operational disruption and
funding needs remain separate. Gross liquidity need is a stock, not an expected
credit loss. Do not add a CVA valuation adjustment to overlapping realized
default losses without a reconciled accounting convention.

These distinctions follow the BIS [FX settlement guidance](https://www.bis.org/committees/bcbs/basel-consolidated-guidelines/module/rma/20).
The fixture makes no claim that every crypto atomic swap, bridge or exchange
credit constitutes legally effective PvP or final settlement.

## CVaR / expected shortfall

Losses are positive and gains negative. `VaR_alpha` is the left quantile.
`ES_alpha = integral_alpha^1 VaR_u du / (1-alpha)` averages the worst tail
probability mass, including fractional weight at a discrete boundary. It is not
generally `E[L | L >= VaR]` for distributions with atoms. The default example uses
alpha 0.975; its VaR is 20 and ES is 52. Alpha, horizon, weighting and loss sign
must accompany every estimate. Missing or non-unit probability mass is rejected.

[BIS MAR33](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/33/inforce/2023-01-01/published/2020-03-27)
provides context for ES confidence and liquidity-horizon conventions. This
discrete synthetic example does not implement the regulatory horizon framework.

## Population stress probe

Each cohort starts with cash plus a risky position, financed by equity and debt.
An exogenous price shock reduces equity. If risky value exceeds a stipulated
multiple of equity, a cohort sells and repays debt. Aggregate selling produces
permanent exponential price impact against a fixed synthetic depth; the next
round revalues unsold holdings and may trigger further sales. Sales execute at
the pre-impact round price, an explicit simplification that excludes intraround
slippage and order priority. There is one common risky asset and no bilateral
credit network, settlement clock, order book, strategic equilibrium or model
decision inside the simulator.

The conceptual motivation is common-asset fire-sale propagation documented by
the [Bank of England](https://www.bankofengland.co.uk/working-paper/2020/modelling-fire-sale-contagion-across-banks-and-non-banks)
and funding/collateral interactions explored by the
[Office of Financial Research](https://www.financialresearch.gov/working-papers/2014/07/29/an-agent-based-model-for-financial-vulnerability/).
The benchmark's equations and coefficients are original illustrative choices,
not a reproduction or calibration of those papers.

The matrix crosses population counts 1, 1,000, 1,000,000 and 10,000,000 with:

- Fixed capital of 1,000 per agent, so total capital grows with adoption.
- Fixed total equity of 1 billion, a negative control where count alone has no
  effect in this cohort representation.
- A homogeneous leveraged profile and a heterogeneous leverage/reserve/limit
  profile. This bundled contrast does **not** isolate signal correlation or
  asynchronous execution. Both profiles update synchronously by round.

Output distinguishes limited-liability investor loss from residual creditor
shortfall. Their sum is uncapped book-equity loss, which can exceed initial
investor equity. Creditor shortfall is not automatically assigned through a
network, and must not be added again to that same book loss. Loss amplification
uses book loss relative to the exogenous book loss under the stated convention.

Price floors, exponent caps, iteration limits and flow tolerances are explicit.
Floor/cap activation prevents a convergence claim. Even convergence within the
toy model is not evidence of market equilibrium. A million represented agents
means cohort-weighted capital, **zero independent agent decisions**. Submitted
model policies are not executed by this simulator in v0.1; narrative mitigation
proposals require human audit or a future constrained-policy adapter.
