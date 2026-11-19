# Systemic Risk Bench historical case catalog

33 retrospective reconstruction cases: 18 traditional-finance cases and 15 crypto/DeFi cases, with 66 staged decisions. These are source-grounded reasoning cases with synthetic roles/stresses, not authenticated point-in-time market tapes or realized PnL backtests. Outcome/source metadata remains evaluator-only.

Dates identify case anchors. `month_marker`, `year_marker` or `period_marker` entries are not exact onset dates; `announcement_day` marks public disclosure. All cases use `retrospective_reconstruction` provenance; historical pretraining knowledge remains a confound after identity masking.

| ID | Case | Event anchor | Family | Stages | Primary/institutional sources |
|---|---|---|---|---:|---|
| `tf_1980s_thrift` | 1980s savings-and-loan duration mismatch and forbearance | 1980-01-01 (year_marker) | `bank_duration_and_forbearance` | 2 | [Savings and Loan Crisis](https://www.federalreservehistory.org/essays/savings-and-loan-crisis) |
| `tf_1982_latam` | 1982 Latin American sovereign debt and bank funding | 1982-08-01 (month_marker) | `sovereign_external_funding` | 2 | [Latin American Debt Crisis of the 1980s](https://www.federalreservehistory.org/essays/latin-american-debt-crisis) |
| `tf_1984_continental` | 1984 Continental Illinois electronic funding run | 1984-05-07 (day) | `bank_wholesale_funding_run` | 2 | [Continental Illinois: A Bank That Was Too Big to Fail](https://www.federalreservehistory.org/essays/continental-illinois) |
| `tf_1987_black_monday` | 1987 crash and dynamic portfolio insurance | 1987-10-19 (day) | `market_microstructure_feedback` | 2 | [Stock Market Crash of 1987](https://www.federalreservehistory.org/essays/stock-market-crash-of-1987) |
| `tf_1992_erm` | 1992 sterling ERM exit | 1992-09-16 (day) | `currency_regime_break` | 2 | [Operation of monetary policy: July to September 1992](https://www.bankofengland.co.uk/quarterly-bulletin/1992/q4/operation-of-monetary-policy) |
| `tf_1994_mexico` | 1994-95 Mexican peso and dollar-indexed debt crisis | 1994-12-20 (day) | `currency_and_sovereign_rollover` | 2 | [Drawing Lessons from the Mexican Crisis](https://www.imf.org/en/news/articles/2015/09/28/04/53/spmds9508) |
| `tf_1997_asia` | 1997 Asian crisis and foreign-currency funding | 1997-07-02 (day) | `currency_funding_contagion` | 2 | [The Asian Crisis: Capital Markets Dynamics and Spillover](https://www.imf.org/external/pubs/ft/icm/icm98/pdf/file02.pdf) |
| `tf_1998_ltcm` | 1998 Russia shock and LTCM convergence trade | 1998-09-02 (day) | `leveraged_convergence_and_counterparty` | 2 | [Near Failure of Long-Term Capital Management](https://www.federalreservehistory.org/essays/ltcm-near-failure) |
| `tf_2007_quant` | August 2007 quantitative equity crowding | 2007-08-06 (day) | `crowded_factor_deleveraging` | 2 | [What Happened to the Quants in August 2007? Evidence from Factors and Transactions Data](https://web.mit.edu/~alo/www/Papers/august07b_2.pdf) |
| `tf_2008_lehman_aig` | September 2008 Lehman, AIG and money-market contagion | 2008-09-15 (day) | `counterparty_funding_network` | 2 | [Crisis and Response: An FDIC History, 2008-2013, Overview](https://www.fdic.gov/bank/historical/crisis/overview.pdf); [Actions Related to AIG](https://www.newyorkfed.org/aboutthefed/aig) |
| `tf_2010_euro` | Euro-area sovereign-bank feedback and fragmentation | 2010-01-01 (year_marker) | `sovereign_bank_doom_loop` | 2 | [Deleveraging and monetary policy](https://www.ecb.europa.eu/press/key/date/2012/html/sp121126_1.pl.html) |
| `tf_2010_flash` | May 6, 2010 flash crash and volume-linked execution | 2010-05-06 (day) | `flash_crash_microstructure` | 2 | [Findings Regarding the Market Events of May 6, 2010](https://www.sec.gov/files/marketevents-report.pdf) |
| `crypto_mtgox_2014` | Mt. Gox: custody shortfall and withdrawal failure | 2014-02-28 | `custody_exchange_run` | 2 | [MtGox trustee: Draft Amended Rehabilitation Plan, September 29, 2022](https://www.mtgox.com/d/04y7ivbnz5gw.pdf); [DOJ: Russian Nationals Charged With Hacking One Cryptocurrency Exchange and Illicitly Operating Another](https://www.justice.gov/archives/opa/pr/russian-nationals-charged-hacking-one-cryptocurrency-exchange-and-illicitly-operating-another) |
| `tf_2015_chf` | January 2015 Swiss franc minimum-rate discontinuation | 2015-01-15 (day) | `currency_policy_gap` | 2 | [Swiss National Bank discontinues minimum exchange rate and lowers interest rate to -0.75%](https://www.snb.ch/en/publications/communication/press-releases/2015/pre_20150115); [SNB monetary policy after the discontinuation of the minimum exchange rate](https://www.snb.ch/en/publications/communication/speeches/2015/ref_20150424_tjn) |
| `crypto_dao_2016` | The DAO: contract exploit, governance response and replay risk | 2016-06-17 | `smart_contract_governance` | 2 | [Ethereum Foundation: Critical Update Re DAO Vulnerability](https://blog.ethereum.org/en/2016/06/17/critical-update-re-dao-vulnerability); [Ethereum Foundation: Hard Fork Completed](https://blog.ethereum.org/en/2016/07/20/hard-fork-completed) |
| `crypto_gdax_flash_2017` | GDAX ETH/USD: thin-book stop and margin cascade | 2017-06-21 | `venue_flash_crash` | 2 | [GDAX executive Adam White: ETH-USD Trading Update 3](https://medium.com/@AdamLWhite/eth-usd-trading-update-3-69e623335e00) |
| `tf_2018_volatility` | February 2018 short-volatility and ETP rebalancing | 2018-02-05 (day) | `volatility_feedback_and_product_structure` | 2 | [The equity market turbulence of 5 February: the role of exchange-traded volatility products](https://www.bis.org/publications/equity-market-turbulence-5-february-role-exchange-traded-volatility-products) |
| `tf_2020_dash_for_cash` | March 2020 dash for cash and Treasury-market dysfunction | 2020-03-01 (month_marker) | `safe_asset_liquidity_and_margin` | 2 | [Holistic Review of the March Market Turmoil](https://www.fsb.org/2020/11/holistic-review-of-the-march-market-turmoil/) |
| `crypto_maker_black_thursday_2020` | Maker Black Thursday: collateral auctions under network congestion | 2020-03-12 | `collateral_liquidation_infrastructure` | 2 | [Maker governance: Black Thursday Response Thread](https://forum.skyeco.com/t/black-thursday-response-thread/1433); [Maker governance: Liquidation report and Black Thursday Compensation Analysis](https://forum.skyeco.com/t/maker-mcd-ethereum-system-liquidation-report-and-black-thursday-compensation-analysis/2243) |
| `crypto_february_flash_2021` | February 2021 crypto selloff: venue depth and liquidity withdrawal | 2021-02-22 | `venue_flash_crash` | 2 | [Kaiko Research: February 2021 Monthly Market Report](https://static1.squarespace.com/static/6019ac844f9ea403da8bd8e4/t/604fd47c45ebf53bd2ec6827/1615844478058/Kaiko-Research-February-Market-Report.pdf) |
| `tf_2021_archegos` | March 2021 Archegos and concentrated synthetic equity exposures | 2021-03-01 (month_marker) | `opaque_prime_broker_counterparty` | 2 | [FINMA concludes Archegos proceedings against Credit Suisse](https://www.finma.ch/en/news/2023/07/20230724-mm-archegos/) |
| `crypto_ronin_bridge_2022` | Ronin bridge: validator-key concentration and wrapped-asset backing | 2022-03-29 (announcement_day) | `bridge_signer_failure` | 2 | [DOJ court filing: Ronin bridge compromise account in Tornado Cash prosecution](https://www.justice.gov/usao-sdny/file/1311391/dl?inline=); [US Treasury: First-Ever Sanctions on a Virtual Currency Mixer](https://home.treasury.gov/news/press-releases/jy0768) |
| `crypto_terra_ust_2022` | Terra UST/LUNA: endogenous collateral and redemption feedback | 2022-05-09 | `stablecoin_reflexive_run` | 2 | [SEC: Terraform and Do Kwon charged with defrauding investors](https://www.sec.gov/newsroom/press-releases/2023-32) |
| `crypto_celsius_2022` | Celsius: yield-account withdrawal freeze and maturity mismatch | 2022-06-12 | `custody_exchange_run` | 2 | [CFTC: Mashinsky and Celsius charged with fraud and material misrepresentations](https://www.cftc.gov/PressRoom/PressReleases/8749-23); [Chicago Fed Letter 479: A Retrospective on the Crypto Runs of 2022](https://www.chicagofed.org/publications/chicago-fed-letter/2023/479) |
| `crypto_three_arrows_2022` | Three Arrows Capital: shared borrower and hidden leverage | 2022-06-27 | `counterparty_network_contagion` | 2 | [Ogier: Counsel to Three Arrows Capital joint liquidators](https://www.ogier.com/news-and-insights/cases/cross-border-ogier-team-advises-joint-liquidators-appointed-over-cryptocurrency-hedge-fund-three-arrows-capital-limited/) |
| `tf_2022_ldi` | September 2022 UK gilt and LDI collateral spiral | 2022-09-23 (day) | `liability_hedge_liquidity_spiral` | 2 | [Financial stability buy/sell tools: a gilt market case study](https://www.bankofengland.co.uk/quarterly-bulletin/2023/2023/financial-stability-buy-sell-tools-a-gilt-market-case-study) |
| `crypto_mango_2022` | Mango Markets: thin reference market and collateral manipulation | 2022-10-11 | `oracle_collateral_manipulation` | 2 | [CFTC v Avraham Eisenberg: January 2023 complaint](https://www.cftc.gov/media/8046/enfeisenbergcomplaint010923/download) |
| `crypto_ftx_2022` | FTX: affiliated trading firm, customer claims and withdrawal run | 2022-11-11 | `custody_exchange_run` | 2 | [DOJ: Samuel Bankman-Fried Sentenced To 25 Years In Prison](https://www.justice.gov/usao-sdny/pr/samuel-bankman-fried-sentenced-25-years-prison); [Chicago Fed Letter 479: A Retrospective on the Crypto Runs of 2022](https://www.chicagofed.org/publications/chicago-fed-letter/2023/479) |
| `tf_2023_svb` | March 2023 Silicon Valley Bank duration and fast deposit run | 2023-03-08 (day) | `bank_duration_and_digital_run` | 2 | [Review of the Federal Reserve's Supervision and Regulation of Silicon Valley Bank: Executive Summary](https://www.federalreserve.gov/publications/2023-April-SVB-Executive-Summary.htm) |
| `crypto_usdc_svb_2023` | USDC/SVB: reserve-bank concentration and weekend redemption friction | 2023-03-11 | `stablecoin_bank_contagion` | 2 | [Circle: $3.3 Billion of USDC Reserve Risk Removed, Dollar De-peg Closes](https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes) |
| `crypto_euler_2023` | Euler: contract vulnerability and uncertain recoveries | 2023-03-13 | `smart_contract_governance` | 2 | [Euler Foundation: Special Announcement](https://forum.euler.finance/t/special-announcement/900) |
| `crypto_curve_vyper_2023` | Curve/Vyper: shared compiler failure across apparently different pools | 2023-07-30 | `shared_code_dependency` | 2 | [Vyper team: Nonreentrancy Lock Vulnerability Technical Post-Mortem](https://hackmd.io/@vyperlang/HJUgNMhs2) |
| `crypto_bybit_2025` | Bybit: signing interface compromise and correlated custody withdrawals | 2025-02-21 | `custody_supply_chain` | 2 | [Bybit: Security Incident Timeline and FAQs](https://www.bybit.com/en/learn/this-week-in-bybit/bybit-security-incident-timeline); [FBI PSA I-022625: North Korea Responsible for Bybit Hack](https://www.fbi.gov/investigate/cyber/alerts/2025/north-korea-responsible-for-1-5-billion-bybit-hack) |

Sources support curator reconstructions at the scope recorded in each JSON card. Complaints and indictments are attributed allegations; source publication dates do not certify a fact was publicly available at an earlier model decision cutoff. See the source JSON and crypto audit for chronology qualifications.


## Separate synthetic benign controls

- `control_funding_buffer` — Adequate liquidity through a funding stress (2 stages; fictional dates; no historical source claim).
- `control_pvp_prefunded` — Functioning PvP with prefunded replacement liquidity (2 stages; fictional dates; no historical source claim).
- `control_orderly_volatility` — Orderly volatility with adequate collateral (2 stages; fictional dates; no historical source claim).
- `control_redeemable_basis` — Temporary stablecoin basis with redemption access confirmed (2 stages; fictional dates; no historical source claim).

## Separate source-grounded content suite

- `content_bagehot_lombard_merchants` — Walter Bagehot, *Lombard Street*
  (1873), Chapter I: merchant return on equity under borrowing; competitive
  pricing and cash-financed competitor; synthetic bank losses, emergency
  liquidity, privately or publicly funded recapitalization and Treasury/central
  bank accounting; three staged teaching decisions.
  Source and formal protocol: [Merchants of Lombard Street](lombard-street.md).
  This case is stored in `systemic_risk_bench/data/content/` and is excluded
  from the frozen historical crisis case and numerical baseline counts.

- `content_bagehot_guarantee_feedback` — a modern source-motivated staged
  extension of Bagehot's merchant argument to contingent guarantees of bank
  funding creditors, bank-to-merchant interest pass-through, portfolio-risk
  feedback and expected fiscal exposures. Separate from all historical
  source-grounded crisis episodes. See [SRB-LOMBARD-02](lombard-feedback.md).
