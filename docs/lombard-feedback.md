# SRB-LOMBARD-02: Expected guarantees, credit access and bank risk

Registered synthetic mechanism experiment, 19 November 2026. This builds on
[SRB-LOMBARD-01](lombard-street.md) and its historical primary-source case. It
uses a modern bank-funding guarantee hypothesis to make the proposed rescue and
merchant-credit connection a falsifiable *within-model* calculation.

## Historical and empirical provenance

Bagehot's 1873 [*Lombard Street*](https://www.gutenberg.org/cache/epub/4359/pg4359-images.html),
Chapter I, establishes the printed merchant-credit example with £50,000 of
operating capital financed by either £50,000 own equity or £10,000 equity plus
£40,000 borrowed through discounts at 5% interest. His competitive point is
that access to borrowing can permit lower prices while retaining adequate
accounting return on the smaller equity stake.

The modern funding-support hypothesis comes from the IMF's
[2014 Global Financial Stability Report, Chapter 3](https://www.imf.org/external/pubs/ft/gfsr/2014/01/)
and the BIS discussion of
[bailouts and bail-in](https://www.bis.org/speeches/20141202-bailouts-bail-and-financial-stability).
Both discuss implicit financial support as a possible source of lower funding
costs and weaker creditor discipline. The IMF's
[International Evidence on Government Support and Risk Taking](https://www.elibrary.imf.org/view/journals/001/2013/094/article-A001-en.xml)
notes the opposing charter-value mechanism, through which support can
encourage safer behavior. A
[2025 Bank of England staff working paper](https://www.bankofengland.co.uk/working-paper/2025/the-implicit-subsidy-to-the-indian-banking-system),
revised August 2026, discusses subsidy estimation using debt/CDS and
equity-implied risks. These sources motivate the research question. **No
numerical data from them enter the experiment**.

## Registered mechanism and units

Let `E` be merchant equity, `D` merchant loan principal, `g` anticipated
coverage of a bank **funding-creditor** claim shortfall, and `alpha` the fraction
of the bank funding saving passed to its merchant borrowers. The benchmark
uses one-period gross promised rates and recovery fractions. All its
probabilities are expressly stipulated risk-neutral underwriting inputs.

```text
Bank p_B(j,D) = p_B0 + sensitivity * p_M(j,D) * (D/E)
Merchant p_M(j,D) = p_M0(j) + slope(j) * (D/E)

r_B(g,j,D) = (1+r_f)/(1-p_B(j,D)*(1-R_B)*(1-g)) - 1

r_pass(j,D,g) = r_B(0,j,D) - alpha*(r_B(0,j,D)-r_B(g,j,D))

r_M(j,D,g) = (1+r_pass+origination_margin)/
             (1-p_M(j,D)*(1-R_M)) - 1

success_asset_value = (E+D)*(1+success_ROA(j)) - curvature(j)*D²/E
success_equity = success_asset_value - D*(1+r_M)

expected_equity_profit = (1-p_M)*success_equity - E

bank_funding_principal = (1-bank_equity_fraction)*D
expected_Treasury_bank_debt_guarantee =
  p_B*g*(1-R_B)*(1+r_B(g))*bank_funding_principal
```

Each project/debt candidate must support complete merchant-loan repayment
in the success state. The recovered amount in merchant failure is a fraction
of promised merchant debt; merchant shareholders receive zero equity in that
state. The backstop itself covers a fraction of bank funding creditors'
shortfall in the **different bank failure event**. The two failure
probabilities and their conditional recovery conventions are modeled
separately. Neither is an empirically estimated risk-neutral intensity.

The representative merchant selects the project and borrowing amount
maximizing expected terminal equity profit. A tie goes to the lower loan
principal and then to the prudent project. The full finite ladder of £0 to
£40,000 in £5,000 increments is enumerated for both project classes. This
is a proposed-portfolio quoted-choice experiment. Its bank PD may depend
on the contemplated loan portfolio; no claim of atomistic price-taking or
general-equilibrium uniqueness follows.

**What the bailout means here:** `g` is a promised share of bank debt
loss absorbed by the Treasury after bank default. A collateralized central-bank
liquidity advance, a share subscription to recapitalize a commercial bank, and
a Treasury transfer to replenish central-bank equity are modeled separately
in [SRB-LOMBARD-01](lombard-street.md). This experiment only prices the
hypothetical bank debt guarantee and its contingent cost.

## Frozen source-law panels

[Primary registration](../configs/lombard-feedback-v1.json) has an invented
2.5% risk-free rate, 8% initial bank failure probability, 35% bank creditor
recovery, 80% pass-through of the funding saving, and a 10% bank equity funding
fraction. Merchant project risks, terminal values, and margins are committed
with the config. Guarantee coverage runs `0, 0.25, 0.5, 0.75, 1`.

A third [roughly 60-basis-point illustrative scale](../configs/lombard-feedback-60bp-scale.json)
sets bank PD to 0.9% and freezes its leverage feedback at zero. With 35%
bank-creditor loss-given-default and the same 2.5% risk-free rate, fully
protected funding is about 60 basis points cheaper than the unbacked rate.
The magnitude is chosen to resemble the order of scale of the
[IMF's 2012 historical structural-support estimate](https://www.elibrary.imf.org/view/journals/001/2012/128/article-A001-en.xml)
of approximately 60 basis points near end-2007. The benchmark does not
use the IMF's bank sample, estimation methodology or actual loan contract
observations; 0.9% is solely a fabricated risk-neutral probability chosen to
create a similar price gap. This scenario probes whether the large-stress
result persists with a smaller price advantage.

The [risk-mix ambiguity control](../configs/lombard-feedback-charter-control.json)
changes only the prudent project's success return. Its purpose is to
test whether risk-taking necessarily rises with government support.
Both panels are completely public and have zero empirical calibration.

Controls are built into each reported coverage arm:

- **Zero pass-through** (`alpha=0`) should eliminate the borrowing-rate subsidy to merchants, holding the candidate bank PD function fixed.
- **Zero bank default probability and no bank-PD feedback** should eliminate any funding guarantee premium.
- **Zero bank-PD feedback** isolates the effect of a constant bank failure risk from the chosen credit size.
- **Fixed aggregate credit** keeps the expected guaranteed bank funding debt exposure constant across larger represented agent counts.
- **Fixed credit per agent** scales aggregate credit and its expected guarantee cost proportionally to population if bank PD and risk pricing are held fixed.

The alternative project calibration is a separate stress test for risk-type
switching. The direction of project risk is always an outcome to report.
Population controls are accounting scaling identities with a frozen quote,
rather than a simulation of a million interacting financial agents.

## Lean 4 proof boundary

[Lombard/Funding.lean](../Lombard/Funding.lean) formalizes the
risk-neutral creditor parity identity, nonincreasing bank funding rates as
guarantee coverage grows at fixed hazard, lower merchant base funding costs
with larger pass-through and the zero-pass-through control. It includes a
conditional monotonic link from larger debt/equity to bank PD under the chosen
linear exposure formula. The Treasury guarantee theorem applies at a **fixed
promised claim face**; the simulated face and default probabilities change
under altered leverage, so its whole-policy fiscal cost requires the Python
experiment. All these theorems are checked using the pinned Lean 4.35.0
toolchain and mathlib, with the axiom report in CI.

The Lean propositions verify the algebra of the stipulated mechanism. They
do not establish the existence of a government guarantee, characterize its
welfare, prove that actual banks choose the model's parameters or
demonstrate endogenous crisis frequencies.

## Run source-only tests

```sh
python -m unittest discover -s tests -p 'test_lombard_feedback.py' -v
python -m unittest discover -s tests -q
python -m systemic_risk_bench lombard-feedback-export --config configs/lombard-feedback-v1.json --output artifacts/lombard-feedback-tasks.json
python -m systemic_risk_bench lombard-feedback-oracle --config configs/lombard-feedback-v1.json --output artifacts/lombard-feedback-evaluator.json
python -m systemic_risk_bench lombard-feedback-run --config configs/lombard-feedback-v1.json --experiment configs/finance-revision-fixture.json --adapter-argv '["python","-m","examples.lombard_feedback_reference_adapter"]' --output artifacts/lombard-feedback-fixture-run.json
```

The oracle is an exact deterministic program, never a language model. The
reference adapter verifies real process transport and exact scoring on
publicly solvable cases. Missing or malformed responses remain in the score
denominator. The model's output contract contains exactly nine fields:
project type, chosen debt, bank and merchant failure probabilities,
backed/unbacked bank rates, the merchant rate, expected merchant-equity
profit, and the expected Treasury guarantee payment. Generated fixture
artifacts and all answers are evaluator-side.

## Local BitAgent or another reasoner

The independent [llama.cpp adapter](../adapters/lombard_feedback_llamacpp.py)
reuses the existing artifact-hash and active-LoRA preflight and the existing
GPU reservation gate. The operator must start an owned local server and
provide a previously verified machine-local config. For example:

```powershell
python -m systemic_risk_bench lombard-feedback-run --config configs/lombard-feedback-v1.json --experiment artifacts/lombard-feedback-bitagent.json --adapter-argv '["python","-m","adapters.lombard_feedback_llamacpp","--config","artifacts/bitagent-readiness/local-config.json"]' --timeout 300 --output artifacts/lombard-feedback-bitagent-run.json
```

Generate the experiment JSON from
[the BitAgent registration template](../configs/lombard-feedback-bitagent.template.json).
Each case starts a new JSON adapter process, sends no previous response,
suppresses chat prompt caching and requires one strict JSON response.
An independently reset local model server would be needed to establish
physical isolation. The current runner correctly reports
`physical_memory_enforced=false`. Capture actual model hashes and measured
tokens/latency before comparing BitAgent with larger models.

## Empirical extension and identification

A credible real-world funding-subsidy estimate needs a panel of bank
debt spreads or CDS claims, support probability proxies such as
support-sensitive credit rating notches, and independent indicators of
default risk, maturity, collateral, liquidity and issuer characteristics.
Loan pricing to merchants is a second panel, requiring matched borrowers,
loan types and origination dates to estimate pass-through. Merchant leverage,
interest coverage, output prices and loan-level defaults provide downstream
outcomes.

A preregistered design should exploit discrete changes in credible public
support expectations or resolution regimes and evaluate pre-trends,
contemporaneous capital requirements, banks' funding mixes, size selection and
credit-quality sorting. The parameter `alpha` should be estimated from
borrower contract differences with fixed effects and sensitivity bounds.
Bailout expectations can be endogenous to risk; reverse causation and
simultaneous balance-sheet repair are major identification concerns.
Estimate confidence intervals over banks, issuer cohorts and shocks,
keeping correlated crisis episodes together.

A bank's expected support need not determine its credit decisions:
higher franchise value can induce conservatism, private bail-in can alter
funding discipline, and equity-price reactions can be driven by dilution or
resolution priority. The synthetic charter-value control exists to require
model evaluations to acknowledge these possibilities.

### Interpretive status

This is a registered source-law diagnostic on five guarantee levels and two
competing project schedules. It supplies algebraic and executable baselines
and an agent-scoring interface. No historical funding spread is measured,
no causal subsidy coefficient has been estimated, and no live lending or
financial authorization is performed.
