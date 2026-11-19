"""Public Lombard Street content-suite numerical tasks, separate from fixed SRB v0.1 numbers.

The first example uses Bagehot's printed figures. The bank and central-bank
ledger is expressly synthetic. Reference answers are available only to scorer.
"""
from __future__ import annotations

import math

from .lombard import bank_rescue, merchant_equity, repeat_rescue, funding_spread_counterfactual
from .scoring import finite


def content_quantitative_tasks() -> list[dict]:
    return [
        {
            "id": "content-lombard-merchants",
            "family": "credit_competition",
            "source_status": "Bagehot_1873_primary_source_figures_with_added_fixed_volume_model",
            "prompt": "Two merchants operate with equal GBP 50,000 capital. An unlevered merchant "
                      "has GBP 50,000 equity; a competitor uses GBP 10,000 equity plus "
                      "GBP 40,000 bills discounted at 5%. Each earns GBP 5,000 annual "
                      "operating profit before debt service. At identical units, fixed "
                      "nonfinancing costs and 10% target equity return, calculate interest, "
                      "both ROEs and maximum annual total price-cut budget. Quantities "
                      "are in pounds and ratios are decimals.",
            "inputs": {
                "cash_equity": 50000, "borrower_equity": 10000,
                "borrowed": 40000, "gross_operating_profit": 5000,
                "funding_rate": 0.05, "target_equity_return": 0.10
            },
            "answer_fields": ["annual_interest", "cash_roe", "levered_roe",
                              "max_price_cut_at_cash_roe"],
        },
        {
            "id": "content-lombard-bank-rescue",
            "family": "bank_solvency_and_liquidity",
            "source_status": "invented_development_example_not_historical_bank_data",
            "prompt": "A synthetic bank holds GBP 500m assets, GBP 450m liabilities and "
                      "GBP 50m equity, and suffers GBP 30m credit losses. Minimum common "
                      "equity/risk assets is 10%; all noncash assets have unit risk weight. "
                      "A lender of last resort alternatively lends GBP 30m cash while creating "
                      "an equal bank debt. A separate central bank has GBP 10m equity and "
                      "subsequently incurs a GBP 4m credit loss. Find post-loss bank equity, "
                      "recapitalization required to reach GBP 50m, no-recapitalization "
                      "risk-asset capacity and asset/paydown contraction at book value, "
                      "bank equity after the liquidity loan, and fiscal recapitalization "
                      "if the central bank returns to GBP 10m equity. Bank figures in "
                      "millions of GBP.",
            "inputs": {
                "assets": 500, "equity": 50, "credit_loss": 30,
                "capital_ratio": 0.10, "liquidity_loan": 30,
                "central_bank_equity": 10, "central_bank_credit_loss": 4
            },
            "answer_fields": [
                "post_loss_equity", "bank_recap_for_old_equity",
                "max_assets_without_recap", "asset_reduction_required",
                "equity_after_liquidity_loan", "central_bank_recap_for_target",
            ],
        },
        {
            "id": "content-lombard-pricing-counterfactual",
            "family": "guarantee_pricing_hypothesis",
            "source_status": "invented_rate_sensitivity_control_no_empirical_guarantee_effect",
            "prompt": "Invented merchant term sheets: GBP 10,000 equity, GBP 40,000 "
                      "debt, GBP 5,000 annual gross operating profit. An "
                      "unsubsidized risk-pricing scenario sets borrowing at 11% "
                      "and an anticipated-support scenario sets borrowing at 5%. "
                      "Compute each ROE, yearly interest saving and difference "
                      "in ROE as a decimal. The rate reduction is a premise, "
                      "not an observed central-bank subsidy.",
            "inputs": {
                "borrower_equity": 10000, "borrowed": 40000,
                "gross_operating_profit": 5000,
                "unsubsidized_rate": 0.11, "supported_rate": 0.05
            },
            "answer_fields": [
                "unsubsidized_roe", "supported_roe",
                "annual_interest_saving", "roe_difference",
            ],
        },
        {
            "id": "content-lombard-repeat-rescue",
            "family": "conditional_public_recapitalization",
            "source_status": "invented_repeat_loss_and_policy_assumption",
            "prompt": "The synthetic bank starts with GBP 50m equity. Assume it loses "
                      "GBP 30m each period for exactly 3 periods. Under a rule that "
                      "transfers exactly that period's loss from public funds, compute "
                      "total transfers and final restored equity. Separately compute "
                      "the pre-resolution book-equity arithmetic if the losses occur "
                      "with no injections. This stipulated recurrence does not predict "
                      "crises, rescue probabilities or regulatory interventions.",
            "inputs": {"initial_equity": 50, "recurring_loss": 30, "rounds": 3},
            "answer_fields": [
                "restored_equity_after_each_round",
                "cumulative_public_transfer_if_publicly_financed",
                "equity_without_injections_before_resolution",
            ],
        },
    ]


def content_numeric_answers() -> dict[str, dict[str, float]]:
    tasks = {item["id"]: item["inputs"] for item in content_quantitative_tasks()}
    merchant = merchant_equity(**tasks["content-lombard-merchants"])
    bank = bank_rescue(**tasks["content-lombard-bank-rescue"])
    recurring = repeat_rescue(**tasks["content-lombard-repeat-rescue"])
    pricing = funding_spread_counterfactual(**tasks["content-lombard-pricing-counterfactual"])
    values = {
        "content-lombard-merchants": merchant,
        "content-lombard-bank-rescue": bank,
        "content-lombard-repeat-rescue": recurring,
        "content-lombard-pricing-counterfactual": pricing,
    }
    return {
        task["id"]: {field: values[task["id"]][field] for field in task["answer_fields"]}
        for task in content_quantitative_tasks()
    }


def score_content_numeric(responses: list[dict]) -> dict:
    """All declared fields count, even absent or invalid answers."""
    if type(responses) is not list:
        raise ValueError("responses must be an array")
    answers = content_numeric_answers()
    matched = {}
    for row in responses:
        if type(row) is not dict or type(row.get("id")) is not str:
            raise ValueError("responses need string ids")
        identifier = row["id"]
        if identifier not in answers or identifier in matched:
            raise ValueError("unknown or duplicate content task")
        if type(row.get("estimates")) is not dict or set(row["estimates"]) - set(answers[identifier]):
            raise ValueError("unknown content estimate or estimates are not an object")
        matched[identifier] = row["estimates"]
    results = []
    per_family = {}
    for task in content_quantitative_tasks():
        identifier = task["id"]
        observed = matched.get(identifier, {})
        correct = 0
        for field, expected in answers[identifier].items():
            value = observed.get(field)
            passed = bool(finite(value) and math.isclose(
                float(value), float(expected), rel_tol=1e-9, abs_tol=1e-9))
            correct += int(passed)
            results.append({
                "task_id": identifier, "family": task["family"], "field": field,
                "expected": expected, "actual": value if finite(value) else None,
                "status": "correct" if passed else "wrong" if finite(value)
                          else "missing_or_invalid",
            })
        per_family[task["family"]] = correct / len(answers[identifier])
    return {
        "schema": "srb.content.numeric.v1",
        "mode": "development_source_and_synthetic_mixed",
        "model_evaluation_claim": False,
        "n_tasks": len(answers),
        "n_fields": len(results),
        "n_covered_fields": sum(x["actual"] is not None for x in results),
        "micro_accuracy": sum(x["status"] == "correct" for x in results)/len(results),
        "family_accuracy": per_family,
        "checks": results,
    }
