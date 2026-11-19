# SRB-LOMBARD-02: Finite credit-pricing feedback audit

**Status:** source-only experiment, deterministic synthetic input laws.
**Registered:** 19 November 2026.
**Source-only CI evidence:** [GitHub Actions run #44453510940](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44453510940), including a full 93-test Python regression and Lean/mathlib check.

## Purpose and empirical boundary

Walter Bagehot's [*Lombard Street*](https://www.gutenberg.org/cache/epub/4359/pg4359-images.html) (1873) shows how cheaper credit can produce superior accounting ROE and a price-undercutting margin for an entrepreneur with modest equity. Modern studies document the possibility of **implicit bank funding subsidies** when public support is expected. Relevant context appears in the [IMF April 2014 GFSR](https://www.imf.org/external/pubs/ft/gfsr/2014/01/) and its [2013 cross-country bank risk study](https://www.elibrary.imf.org/view/journals/001/2013/094/article-A001-en.xml).

The exact experiment here is an **invented one-period mechanism model**. It
assumes pricing-measure and physical default probabilities coincide; a real
fiscal loss estimate would require physical probabilities with a separately
calibrated market-risk-premium model. Its empirical task is to isolate the causal arrows that would require data before claiming an observed subsidy or recurring central-bank rescue cycle. No bank issuance tape, merchant loan file, official intervention sample or external market prices have been used.

## Registered one-period source-law findings

All amounts are in synthetic GBP units per representative merchant. The Treasury expectation refers only to an assumed guarantee of bank funding-creditor shortfall, conditional on bank default; it is independent of any public bank-equity injection or central bank balance-sheet recapitalization.

### Main feedback calibration

| Coverage g | Chosen project | Merchant debt | Merchant failure PD | Bank failure PD | Merchant loan rate | Expected Treasury guarantee |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0% | prudent | 10,000 | 2.50% | 8.450% | 11.039% | 0 |
| 25% | prudent | 10,000 | 2.50% | 8.450% | 9.773% | 132.113 |
| 50% | prudent | 15,000 | 3.25% | 8.878% | 9.357% | 411.099 |
| 75% | prudent | 15,000 | 3.25% | 8.878% | 8.090% | 607.622 |
| 100% | prudent | 20,000 | 4.00% | 9.440% | 7.567% | 1,132.092 |

The chosen debt and both default PDs rise under the registered risk law. This follows from a fully transparent finite project-choice optimization over a stipulated bank-default feedback formula, not a fitted behavioral response.

### Risk-type ambiguity calibration

| Coverage g | Chosen project | Merchant debt | Merchant failure PD | Expected Treasury guarantee |
| ---: | --- | ---: | ---: | ---: |
| 0% | aggressive | 5,000 | 6.60% | 0 |
| 25% | aggressive | 5,000 | 6.60% | 67.231 |
| 50% | aggressive | 10,000 | 7.70% | 290.258 |
| 75% | prudent | 15,000 | 3.25% | 607.622 |
| 100% | prudent | 20,000 | 4.00% | 1,132.092 |

A small change to the assumed prudent project's terminal success value changes the risk-mix outcome. Higher support increases chosen debt in this panel, while the selected project ultimately becomes safer. This is a falsification control for an unrestricted claim that guarantees must increase project risk.

### A lower roughly 60bp pricing-scale sensitivity

The third control sets bank default PD to **0.9%** and freezes default-feedback at zero; its full-support funding advantage is approximately **60.3 basis points**. This scale was chosen as an illustration, loosely comparable to the order of magnitude of a historical structural subsidy estimate in [IMF Working Paper 12/128](https://www.elibrary.imf.org/view/journals/001/2012/128/article-A001-en.xml). No IMF parameter is directly transferred into our simulator.

| Coverage g | Chosen debt | Merchant failure PD | Selected merchant loan rate | Expected Treasury guarantee |
| ---: | ---: | ---: | ---: | ---: |
| 0% | 20,000 | 4.00% | 6.807% | 0 |
| 25% | 25,000 | 4.75% | 7.305% | 33.878 |
| 50% | 25,000 | 4.75% | 7.180% | 67.656 |
| 75% | 25,000 | 4.75% | 7.055% | 101.335 |
| 100% | 25,000 | 4.75% | 6.930% | 134.916 |

**Selection effect:** the chosen merchant loan rate rises between 0% and 25% guarantee coverage, because the model switches from £20,000 to £25,000 borrowing and merchant risk increases. The fixed-project and fixed-debt underwriting rate falls monotonically with coverage, as the Lean theorem predicts. A borrower-weighted observed interest rate could move differently from the rate offered for a matched risk type.

## Score and exact-law verification

The deterministic reference adapter receives only public packets and computes exact model responses. Its five cases per panel are mathematical transport fixtures. It makes **zero LLM calls** and reports its own outputs with a `model_evaluation_claim=false` flag.

The [Python evaluator](../../systemic_risk_bench/lombard_feedback.py) constructs all candidate portfolios, checks that successful project values cover promised merchant debt, prices both types of default claims, computes separate bank and merchant probabilities, and selects the highest expected terminal shareholder profit. The output includes explicit beneficiary and public-budget components.

The [Lean kernel file](../../Lombard/Funding.lean) proves bank-creditor break-even parity, the nonincreasing bank debt rate under higher guarantee coverage at fixed risk, pass-through inequalities, the zero-default/zero-pass-through controls, and conditional Treasury exposure monotonicity at fixed claim face. The loan-size optimization and fiscal cost with endogenous loan face are computed by the Python model. The proofs rely only on their explicit assumptions.

The old 1873 merchant figures and the earlier conditional bank/common-equity restoration proofs remain in [SRB-LOMBARD-01](../../docs/lombard-street.md). The Treasury bank-debt guarantee here is a different fiscal instrument from a central bank liquidity loan, a bank equity recap, or a Treasury contribution to the central bank's own accounting equity.

## Registered negative controls

The source-only CI also exercises zero bank PD, zero credit pass-through, bank PD independent of merchant leverage, and paired aggregate exposure scaling. At a fixed bank quote, increasing the represented number of agents leaves **fixed-total-credit** guarantee cost unchanged. With fixed credit per agent and frozen risk parameters, aggregate expected guarantee cost scales linearly with represented borrowers. Neither test models strategic herd behavior, endogenous prices from millions of agents or market-clearing credit supply.

The two project calibrations and 60bp scenario must remain distinct reports in future comparisons. The register includes all their parameters and SHA-256 digests:

| Config | SHA-256 |
| --- | --- |
| `lombard-feedback-v1.json` | `d19eef913cfbeb3f1fa89762c2403bd31e9a3d58923726ab3ad5c51f676967e9` |
| `lombard-feedback-charter-control.json` | `3ddbf091b8cd5bafcbc4a35f80659e7c769c5dcc8ab2703ae47c4cce7fe71c54` |
| `lombard-feedback-60bp-scale.json` | `10c5fc4f92d6485b35427b21b600ef210b0f0faad003ee141336565407481c81` |

These digests identify the canonical JSON config values used by the Python evaluator. The GitHub Actions job publishes evaluator-only result artifacts with corresponding packet digests and real subprocess fixture receipts.

## Causal inference work required

A real estimate of `alpha`, the bank's funding-cost pass-through to merchant borrowers, needs matched loans, borrower risk and bank funding issuance terms measured at identical maturities. An identified change in anticipated bank creditor protection could provide a treatment variation; event windows and difference-in-differences require credible parallel trends and controls for concurrent capital requirements, liquidity rules, lender concentration, and borrower selection. Bank-specific CDS versus equity-implied default evidence and support-rating uplifts may give separate proxies for anticipated protection.

The downstream credit/leverage result should be compared under debt-capacity constraints, borrower price elasticity, risk correlation, loan loss and funding-deposit feedback. Its fiscal conclusion must distinguish actual guarantee payments, net fiscal recoveries, new bank equity capital, central-bank credit impairment and Treasury recapitalization of the central bank. These are different accounting objects. The finite source-law result has no estimate of their historical frequency.

## Reproduction

```sh
python -m unittest discover -s tests -p 'test_lombard_feedback.py' -v
python -m unittest discover -s tests -q
python -m systemic_risk_bench lombard-feedback-oracle --config configs/lombard-feedback-v1.json --output artifacts/lombard-feedback-main.json
python -m systemic_risk_bench lombard-feedback-oracle --config configs/lombard-feedback-charter-control.json --output artifacts/lombard-feedback-charter.json
python -m systemic_risk_bench lombard-feedback-oracle --config configs/lombard-feedback-60bp-scale.json --output artifacts/lombard-feedback-60bp.json
lake build Lombard
```

A pinned local BitAgent adapter is available at
[adapters/lombard_feedback_llamacpp.py](../../adapters/lombard_feedback_llamacpp.py).
Model identity, measured tokens, runtime budgets, and fresh genuine model responses
are required for the first agent-behavior evaluation. All figures above are
deterministic fixture results.
