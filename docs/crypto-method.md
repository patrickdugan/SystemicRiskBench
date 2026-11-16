# Crypto/DeFi historical reasoning case set

Fifteen source-grounded case cards provide 30 staged decisions. Event dates run from MtGox's 2014 failure through Bybit's 2025 compromise; the MtGox retrospective explicitly traces alleged custody theft back to 2011. This covers exchange custody, two flash-crash episodes, smart-contract exploits, liquidation and gas bottlenecks, bridge backing, reflexive stablecoin runs, crypto credit contagion, oracle manipulation, reserve-bank contagion, compiler dependencies, and signing-interface concentration.

`crypto_cases.json` uses `schema_version: srb.history.v0.1`. `build_cases.py` is the editable authoring source and regenerates that JSON without network access or dependencies. Both remain in the requested work directory for integration by the parent task.

## What is historical, and what is synthetic

The cases are **retrospective reconstructions with counterfactual strategies**, not authenticated as-of market-data replays. Sources were searched and opened on 2026-11-16. First-stage portfolio designs and every numerical simulation input are explicitly synthetic. Historical second-stage facts are labeled as reconstructions. Extra stress observations are separately labeled synthetic. The chosen date boundary does not certify when an article or a private fact became publicly available intraday.

Before these cards can support strict foresight scoring, an archive pass must attach publication timestamp, archive snapshot/hash and precise availability to each historical observation. In the meantime they are useful for mechanism reasoning, calibration under partial evidence, strategy revision, architecture critique and systemic counterfactuals.

The late-published sources are deliberately used as evidence for the curator's account, rather than sent to the tested model. The current Maker thread contains edited posts and later replies, and is especially unsuitable for sending wholesale as an as-of observation. The Circle historical blog URL now redirects to the general blog; the still-accessible issuer press release is the cited primary source. Ronin uses a DOJ court filing because the original operator postmortem URL no longer opened reliably; its case anchor is the March 29 public announcement, distinguished from the March 23 underlying theft documented by Treasury's later May 6 statement. The 3AC second-stage cutoff is conservatively July 8, the publication date of supplied first-hand counsel confirmation, rather than the June 27 order date. A visible token or account balance is never substituted for custody ownership or redemption capacity.

## Evidence scope

- Primary operator/protocol material: Ethereum Foundation, GDAX executive Adam White's original operator update, Maker governance, Euler Foundation, Vyper team, Circle and Bybit.
- Primary legal/regulatory material: MtGox trustee plan, DOJ court filings and trial/sentencing report, CFTC complaints and release, SEC release, FBI PSA. Complaints and charging accounts are attributed allegations. The Mango card deliberately avoids asserting a current criminal-case disposition from a stale conviction announcement.
- Primary measured research: Kaiko's own February 2021 order-book analysis and Chicago Fed researchers' own analysis of withdrawal flows. These are retrospective analyses and no raw historical feed is bundled.
- First-hand process account: 3AC liquidators' legal counsel confirms the June 27 liquidation order; it does not establish bilateral recovery rates.

Every source object states the narrow factual claim it supports. Historical sources are paraphrased; benchmark questions and counterfactuals are original scenario design. No forecasts or legal recovery estimates are claimed to have been available before the event.

## Model-visible packet boundary

Export only observations available through the selected stage, the synthetic proxy input block, the questions and a neutral task identifier. Hold back `outcome`, `sources`, source titles/URLs, event title, mechanism tags and curator notes. For identity-masked tracks, replace identifiable venue, protocol and token names consistently and use relative dates; retain a protected private mapping. Masking does not undo pretrained memory, and the numerical stress scenario is intentionally a counterfactual rather than a request to recall the event's exact outcome.

All variants and stages of a historical event belong to the same split. Correlated 2022 crypto credit cases and SVB/USDC should also be grouped by crisis family when measuring held-out generalization. Never train on one naming variant and call another a clean test.

## What to score

Score risk distinctions, input sufficiency, sound arithmetic when inputs permit it, causal paths, usable contingencies, sensitivity to capital scale and synchronization, explicit assumption revision, and independent checks of the proposed reasoning architecture. Do not reward later event identification or guaranteed hindsight profits. Do not score exploit loss, custody shortfall, settlement risk and CVA as interchangeable labels. A depeg can reflect access timing and uncertainty without proving final legal default; a successful chain transfer does not prove wrapped-asset backing; a familiar audit does not prove deployed compiler correctness.

Each card includes a counterfactual mitigation with a cost. Million-agent questions always require both fixed aggregate capital and fixed capital per agent: agent count alone is not an economically meaningful market-impact input.

## Validation performed

- JSON round trip succeeded.
- Fifteen unique case identifiers and 30 ordered staged decisions.
- Every case includes sources, separate outcome/evaluation anchors, explicit synthetic numerical inputs and a counterfactual.
- No raw historical price series, calibrated market-impact model or realized historical PnL is claimed by these artifacts.

## Suggested follow-on coverage

Add 2011 MtGox flash-crash specifics only after locating an authenticated operator archive; the DOJ's 2011 custody-theft account is a different event and should not be conflated with it. Additional candidates include Bitfinex 2016, May 2021 leverage liquidations, Wormhole/Nomad 2022 and later incidents, once equally reliable primary material and time-availability evidence are attached. Historical non-crisis controls, near misses and randomly generated lookalike mechanisms are needed to penalize blanket crisis prediction.
