"""Deterministic teaching calculations for Bagehot-style merchant credit and bank rescue.

Every value is synthetic unless explicitly sourced to Bagehot's 1873 worked
merchant example. Commercial-bank and central-bank equity remain distinct.
"""
from __future__ import annotations

import math


def _number(value, name: str, *, positive=False, nonnegative=False) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real number, not bool")
    if positive and value <= 0:
        raise ValueError(f"{name} must be strictly positive")
    if nonnegative and value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return float(value)


def merchant_equity(
    *, cash_equity, borrower_equity, borrowed, gross_operating_profit,
    funding_rate, target_equity_return
) -> dict:
    """Fixed assets/units, common gross profit and zero frictions other than debt.

    The price-reduction budget presumes unchanged volume and cost per unit.
    Any extra default risk, credit rationing, tax, fees or sales response requires
    an explicitly different model.
    """
    cash = _number(cash_equity, "cash_equity", positive=True)
    equity = _number(borrower_equity, "borrower_equity", positive=True)
    debt = _number(borrowed, "borrowed", nonnegative=True)
    profit = _number(gross_operating_profit, "gross_operating_profit")
    rate = _number(funding_rate, "funding_rate", nonnegative=True)
    target = _number(target_equity_return, "target_equity_return", nonnegative=True)
    if not math.isclose(cash, equity + debt, rel_tol=0, abs_tol=1e-9):
        raise ValueError("merchant example requires the same operating asset capital")
    interest = debt * rate
    return {
        "annual_interest": interest,
        "cash_roe": profit / cash,
        "levered_roe": (profit - interest) / equity,
        "max_price_cut_at_cash_roe": (profit - interest) - target * equity,
        "spread_on_operating_assets": profit / cash - rate,
        "leverage_assets_to_equity": (equity + debt) / equity,
        "debt_to_equity": debt / equity,
        "price_cut_interpretation": "absolute annual operating-surplus budget at fixed volume",
        "assumes_equal_operating_asset_productivity": True,
        "market_equilibrium_claim": False,
    }


def funding_spread_counterfactual(
    *, borrower_equity, borrowed, gross_operating_profit,
    unsubsidized_rate, supported_rate
) -> dict:
    """Invented pricing counterfactual, not evidence that a guarantee lowers rates."""
    e = _number(borrower_equity, "borrower_equity", positive=True)
    d = _number(borrowed, "borrowed", positive=True)
    g = _number(gross_operating_profit, "gross_operating_profit")
    hi = _number(unsubsidized_rate, "unsubsidized_rate", nonnegative=True)
    lo = _number(supported_rate, "supported_rate", nonnegative=True)
    if lo > hi:
        raise ValueError("supported rate must not exceed comparison rate")
    high_roe = (g - hi*d)/e
    low_roe = (g - lo*d)/e
    return {
        "unsubsidized_roe": high_roe,
        "supported_roe": low_roe,
        "annual_interest_saving": (hi-lo)*d,
        "roe_difference": low_roe - high_roe,
        "guarantee_to_rate_effect_is_assumed": True,
        "real_world_pricing_claim": False,
    }


def bank_rescue(
    *, assets, equity, credit_loss, capital_ratio, liquidity_loan,
    central_bank_equity, central_bank_credit_loss
) -> dict:
    """Book-value balance-sheet identity with all assets given risk weight one.

    Lender-of-last-resort loan increases cash and debt one-for-one. A loss
    consumes equity. A separate shareholder/public transfer can restore bank
    equity; any loss borne by the central bank is accounted for at the CB.
    """
    a = _number(assets, "assets", positive=True)
    e = _number(equity, "equity", positive=True)
    loss = _number(credit_loss, "credit_loss", nonnegative=True)
    k = _number(capital_ratio, "capital_ratio", positive=True)
    q = _number(liquidity_loan, "liquidity_loan", nonnegative=True)
    cb_e = _number(central_bank_equity, "central_bank_equity", positive=True)
    cb_loss = _number(central_bank_credit_loss, "central_bank_credit_loss", nonnegative=True)
    if e > a or loss > a or cb_loss > cb_e:
        raise ValueError("inconsistent initial assets/equity or losses")
    if e < k * a:
        raise ValueError("initial bank breaches the stipulated capital constraint")
    after_assets = a - loss
    after_equity = e - loss
    debt = a - e
    bank_injection = max(0.0, e - after_equity)
    # A liquidation at book value repays debt, preserving remaining equity.
    capacity = max(0.0, after_equity / k)
    contraction = max(0.0, after_assets - capacity)
    cb_post = cb_e - cb_loss
    return {
        "initial_bank_debt": debt,
        "post_loss_assets": after_assets,
        "post_loss_equity": after_equity,
        "bank_recap_for_old_equity": bank_injection,
        "max_assets_without_recap": capacity,
        "asset_reduction_required": contraction,
        "equity_after_liquidity_loan": (after_assets + q) - (debt + q),
        "central_bank_equity_after_liquidity_loan_origination": cb_e,
        "central_bank_equity_after_credit_loss": cb_post,
        "central_bank_recap_for_target": cb_loss,
        "public_bank_recapitalization_is_policy_choice": True,
        "commercial_bank_liquidity_is_not_equity": True,
        "cb_recapitalization_is_separate_fiscal_transfer": True,
    }


def repeat_rescue(*, initial_equity, recurring_loss, rounds) -> dict:
    """Conditional recurrence: each period inject exactly the period's loss.

    No endogenous loss probability or re-leveraging decision is assumed.
    """
    e = _number(initial_equity, "initial_equity", positive=True)
    l = _number(recurring_loss, "recurring_loss", nonnegative=True)
    if type(rounds) is not int or not 0 <= rounds <= 1_000_000:
        raise ValueError("rounds must be a bounded nonnegative integer")
    return {
        "restored_equity_after_each_round": e,
        "cumulative_public_transfer_if_publicly_financed": rounds * l,
        "equity_without_injections_before_resolution": e - rounds * l,
        "recurrence_only_assumes_repeat_losses_and_recapitalization": True,
    }
