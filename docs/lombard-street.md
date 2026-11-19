# SRB-LOMBARD-01: The Merchants of Lombard Street

**Source-based content suite, registered 19 November 2026.**

A standalone primary-source reasoning case, three cumulative stages, thirteen numerical answer fields and a Lean 4 mathematical audit. The nineteenth-century merchant example is taken from Walter Bagehot's *Lombard Street: A Description of the Money Market* (1873), Chapter I. Every bank loss, capital requirement, intervention and recurring crisis scenario is invented for this training/evaluation content.

## Reading and attribution

Bagehot describes the competitive effect of commercial credit through two merchants, one financing a £50,000 enterprise with £50,000 of own capital and the other using £10,000 equity and £40,000 of discounted bills at 5% interest. With £5,000 operating profit, he calculates 10% on the cash merchant's equity and 30% on the borrowing merchant's equity after £2,000 interest. Cheap funding allows the leveraged merchant to accept a lower gross profit while still receiving an acceptable return on his smaller stake. Bagehot also argues that lending enables entry by commercially skilled borrowers who otherwise lack large inherited fortunes.

Primary source: [Walter Bagehot, *Lombard Street*, Project Gutenberg](https://www.gutenberg.org/ebooks/4359), especially Chapter I. The exact title is *Lombard Street: A Description of the Money Market*. "Merchants of Lombard Street" is the exercise name, not the book's title.

In Chapter I the borrowing merchant's higher 30% ROE comes from capital structure and funding cost, **not an established improvement in operating productivity**. Lower prices follow under added assumptions of equal asset use, identical output, unchanged operating unit costs and an accessible loan at the stated rate.

## The competitive-return result

For a cash merchant using assets `A` and a leveraged merchant with own equity `E`, borrowed debt `D`, and the **same** `A = E + D > 0`, let both earn operating gross profit `G` and let the borrowing rate be `r`. Assume `E > 0`, `D > 0`, the same business scale and comparable accounting periods.

```text
unlevered_ROE = G / A
levered_ROE   = (G - r D) / E
difference    = D (G - r A) / (E A)

levered_ROE > unlevered_ROE     iff G/A > r
levered_ROE = unlevered_ROE     iff G/A = r
levered_ROE < unlevered_ROE     iff G/A < r
```

The inequality is an algebraic conditional theorem, not evidence that risk-adjusted equity investors accept the same cost of capital in both structures. For Bagehot's figures, `G=5,000`, `A=50,000`, `E=10,000`, `D=40,000`, `r=0.05`, the leveraged ROE is 0.30 and the cash ROE is 0.10.

If the leveraged merchant has a 10% target on £10,000 own equity, it needs £1,000 after interest. Gross required operating profit is £2,000 interest plus £1,000 equity profit, or £3,000. Relative to £5,000 gross, the annual price-cut **budget** is £2,000 for a fixed number of units and unchanged costs. The original text does not specify number of goods sold, so the exercise does not invent a per-unit price reduction.

A negative-spread control with `G=1,000` gives 2% unlevered ROE and −10% leveraged ROE. A zero-spread control with `G=2,500` yields 5% in both structures. If price competition reduces the gross return below the debt cost, the advantage reverses. Loans may also be rationed, shortened or priced for default risk. These are explicit boundaries of the theorem.

## Two balance sheets and three policy instruments

Synthetic bank, all currency figures **millions of pounds**:

| Book line | Initial | After £30m credit loss | After £30m new equity | After £30m collateralized liquidity loan instead |
| --- | ---: | ---: | ---: | ---: |
| Assets | 500 | 470 | 500 | 500 |
| Liabilities | 450 | 450 | 450 | 480 |
| Equity | 50 | 20 | 50 | 20 |

The equity contribution can come from private shareholders or a public fiscal source. It has exactly the same receiving-bank book-equity effect in this stylized ledger, with different contributors and distributional consequences. The lender-of-last-resort loan raises cash assets and liabilities equally, leaving common equity at £20m.

The bank has a stipulated 10% equity-to-risk-assets floor and starts at the threshold. Before assistance, its post-loss assets are £470m and equity £20m. If remaining assets have risk weight one and can be sold at book value to repay debt, the maximum remaining book is £20m / 0.10 = **£200m**. At least **£270m** in risky asset exposure must be sold/retired or otherwise removed from that book to restore the stipulated ratio without fresh equity. The liquidity loan alone does not replenish the missing £30m equity.

Separate central-bank ledger: originating a secured £30m emergency loan creates a £30m loan asset and corresponding reserve liability, so central-bank equity is unchanged at origination. A later **actual £4m credit loss**, if it occurs, reduces stipulated central-bank equity from £10m to £6m. A **Treasury equity transfer of £4m** restores its former accounting target, *if* that is the selected fiscal policy. A central bank's ability or need to operate with low/negative capital is institution-dependent; this simplified model never assumes automatic Treasury funding.

This separation follows modern lender-of-last-resort analysis, which distinguishes support for solvent but illiquid institutions from support for insolvent ones. Emergency credit is traditionally secured and priced at a high or penalty rate. The Bank of England describes contemporary resolution frameworks in which equity holders and eligible creditors absorb bank failure losses before a public capital contribution. [RBA, Bagehot and the Lender of Last Resort, 150 Years On](https://www.rba.gov.au/speeches/2023/sp-ag-2023-12-14.html); [Bank of England, Approach to Resolution](https://www.bankofengland.co.uk/paper/2023/the-bank-of-englands-approach-to-resolution).

## Conditional repeated recapitalization

Let `E_t` be the commercial bank's equity just before period `t` losses, `L_t` the new recognized loss, and `R_t` net fresh equity contributions after that loss:

```text
E_(t+1) = E_t - L_t + R_t
R_t = L_t  =>  E_(t+1) = E_t
If L_t = 30 and publicly funded R_t = 30 for 3 periods:
  total public transfer = 90
  bank equity after each rescue = 50
If R_t = 0 for 3 periods:
  simple ledger equity = 50 - 90 = -40
```

The no-rescue path is a **counterfactual accounting trajectory** that becomes insolvent after the second £30m loss. Real resolution, creditor haircuts, bankruptcy law and asset sales alter the later path. The three losses are exogenous assumptions. This formal recurrence **does not establish the existence of recurring financial crises**.

A testable dynamic hypothesis would require connecting expected public rescues to ex-ante private funding prices, borrower leverage and risk choices, loss probabilities and subsequent policy responses. For example:

```text
anticipated safety net
    -> reduced private funding risk premium [requires pricing evidence]
    -> larger credit supply and merchant leverage [requires behavioral response]
    -> more fragile balance sheets or correlated positions [requires risk mechanism]
    -> recognized losses and funding run [requires shock realization]
    -> private recap, resolution, collateralized liquidity, or fiscal recap
    -> revision of future rescue expectations [requires equilibrium expectations]
```

A matched control with no credit loss requires zero equity recap. Another control funds a solvent but illiquid bank through a secured loan, with its equity unchanged. Private recapitalization substitutes new investor equity for fiscal cost. These controls distinguish the accounting mechanism from a universal rescue narrative.

The leveraged-ROE expression and competition argument are also discussed alongside the risks of leverage in [RBA, Returns on Equity, Cost of Equity and the Implications for Banks](https://www.rba.gov.au/publications/bulletin/2017/mar/6.html). Higher accounting ROE is not automatically higher risk-adjusted shareholder value.

## Lean 4 proof boundary

The [Lombard/Capital.lean](../Lombard/Capital.lean) module, built with Lean v4.35.0 and mathlib at the matching release, proves:

- Higher leveraged ROE from a strictly positive gross asset/debt spread and the converse negative-spread result.
- Preservation of a stipulated target return by a bounded gross-price cut.
- Bagehot's 10%, 30%, and £2,000 exact rational arithmetic.
- Equality of book equity before and after a pure loan funded by an equal new liability.
- Equity consumption by credit losses and restoration by a separate paid-in contribution.
- The capital-ratio bound on risk assets and loss-induced violation when the initial ratio is binding.
- Separate central-bank credit-loss/recap accounting and an exact repeated-loss matching-transfer recurrence.

Every proposition is conditional on its numerical and accounting assumptions. The proof has no market data, lender behavior, welfare objective, crisis hazard, expectations model, or claim about the historical frequency of rescues. The kernel and axiom report are checked by [SRB-LOMBARD-01 CI](../.github/workflows/lombard-content.yml).

## Export and score

Run from the repository root on Python 3.10+:

```sh
python -m unittest discover -s tests -p 'test_lombard_content.py' -v
python -m systemic_risk_bench content-list
python -m systemic_risk_bench content-packet --case content_bagehot_lombard_merchants --stage 0 --output artifacts/lombard-stage0.json
python -m systemic_risk_bench content-packet --case content_bagehot_lombard_merchants --stage 2 --output artifacts/lombard-stage2.json
python -m systemic_risk_bench content-quant --output artifacts/lombard-questions.json
```

For an agent response adapter, use `content-run` with a registered experiment and `--cases content_bagehot_lombard_merchants`; the runner sends cumulative staged narrative evidence and previous replies and records subprocess results. It **does not** enforce the 4/12-bit memory contract of SRB-REV-02. Numeric responses may be separately scored with `content-score --responses <file> --output <file>`. There are three registered numerical tasks and 13 answer fields; they are intentionally separate from the main benchmark's 6-task, 13-field frozen baseline.

## Evaluation questions for BitAgent and compact reasoners

1. Recognize the exact equality and inequality of merchant ROE under stated borrowing terms, then explain financing advantages without inventing operating efficiencies.
2. Separate solvency, funding liquidity, equity capital and central-bank accounting. Choose between private recap, fiscal recap, collateralized emergency lending, contraction and orderly resolution based on stated facts.
3. Prove the conditional fixed-loss recap recurrence while describing the additional empirical and institutional mechanisms required for an endogenous crisis/recovery cycle.
4. State competing mechanisms for credit growth and bank recap, and include the no-loss and negative-funding-spread controls.
5. If multiple agents pursue the trade, compare fixed total credit with fixed credit per participant, correlated signal exposure and liquidation costs.

The source and synthetic cases are public development material. The rubric still needs independently graded model responses, measured resource budgets, and epistemic/causal audits before claiming model performance.
