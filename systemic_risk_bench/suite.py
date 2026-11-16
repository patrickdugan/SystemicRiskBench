"""Public numerical tasks and evaluator-only answer construction."""

from .risk import (joint_state_credit_loss, netting_exposure,
                   settlement_principal_loss, tail_risk, unilateral_cva)


def quantitative_tasks():
    return [
        {"id": "q-cva-term", "family": "credit", "prompt":
         "Compute unilateral CVA in currency units. These are stipulated risk-neutral, "
         "unconditional default probability increments for disjoint periods. Assume "
         "independence of positive exposure and default. Identify limitations.",
         "inputs": {"ee": [1_000_000, 2_000_000], "default_increments": [0.01, 0.015],
                    "discounts": [0.99, 0.97], "recovery": 0.4},
         "answer_fields": ["cva"]},
        {"id": "q-wrong-way", "family": "credit", "prompt":
         "Compute joint-state expected credit loss and the factorized estimate that "
         "incorrectly assumes independence. Probabilities and conditional PDs are "
         "stipulated in one common pricing measure; discount is one. Explain the gap.",
         "inputs": {"exposures": [100_000, 1_000_000], "conditional_pd": [0.01, 0.2],
                    "state_probabilities": [0.9, 0.1], "recovery": 0.4},
         "answer_fields": ["joint_loss", "independent_loss"]},
        {"id": "q-settlement", "family": "settlement", "prompt":
         "Compute expected principal loss without PvP and with functioning PvP. "
         "Failure probability covers only the interval after irrevocable pay-away "
         "and before receipt. Recovery applies to principal. Also report full "
         "replacement funding need if the purchased currency does not arrive. "
         "Explain remaining replacement-cost, liquidity, and operational risks.",
         "inputs": {"principal": 10_000_000, "fail_probability": 0.002,
                    "recovery": 0.4, "replacement_cost_stress": 75_000},
         "answer_fields": ["non_pvp_principal_el", "pvp_principal_el", "liquidity_need"]},
        {"id": "q-tail", "family": "tail", "prompt":
         "Compute VaR as the left quantile and CVaR/ES as the average of the worst "
         "(1-alpha) probability mass of losses. Include fractional boundary mass. "
         "Losses are positive; gains would be negative. Do not use E[L|L>=VaR].",
         "inputs": {"losses": [0, 10, 20, 100], "probabilities": [0.90, 0.05, 0.04, 0.01],
                    "alpha": 0.975, "horizon": "one stipulated stress interval"},
         "answer_fields": ["var", "expected_shortfall"]},
        {"id": "q-netting", "family": "credit", "prompt":
         "Compute current positive exposure for the two alternative legal structures. "
         "Only positions within each inner array can be netted. Explain why market "
         "hedging does not establish cross-counterparty legal close-out netting.",
         "inputs": {"same_set": [[100, -80]], "separate_sets": [[100], [-80]]},
         "answer_fields": ["same_set_exposure", "separate_set_exposure"]},
        {"id": "q-capacity", "family": "crowding", "prompt":
         "Each agent sells the stated fraction of leveraged risky assets in one "
         "interval. Compute total sell notional and sell-notional/depth for one "
         "agent and one million agents. Contrast fixed aggregate capital. Depth "
         "is a scenario capacity parameter, not a guaranteed executable quote.",
         "inputs": {"capital_per_agent": 1000, "leverage": 3, "sell_fraction": 0.1,
                    "depth": 100_000_000, "population": 1_000_000},
         "answer_fields": ["single_sell", "million_sell", "million_flow_depth"]},
    ]


def numerical_answers():
    tasks = {t["id"]: t["inputs"] for t in quantitative_tasks()}
    c = tasks["q-cva-term"]
    w = tasks["q-wrong-way"]
    s = tasks["q-settlement"]
    t = tasks["q-tail"]
    n = tasks["q-netting"]
    cva = unilateral_cva(c["ee"], c["default_increments"], c["discounts"], c["recovery"])
    independent = (sum(e*p for e, p in zip(w["exposures"], w["state_probabilities"]))
                   * sum(d*p for d, p in zip(w["conditional_pd"], w["state_probabilities"]))
                   * (1-w["recovery"]))
    return {
        "q-cva-term": {"cva": cva},
        "q-wrong-way": {"joint_loss": joint_state_credit_loss(**w), "independent_loss": independent},
        "q-settlement": {"non_pvp_principal_el": settlement_principal_loss(
            s["principal"], s["fail_probability"], s["recovery"], False),
            "pvp_principal_el": 0.0, "liquidity_need": s["principal"]},
        "q-tail": tail_risk(t["losses"], t["probabilities"], t["alpha"]),
        "q-netting": {"same_set_exposure": netting_exposure(n["same_set"]),
                      "separate_set_exposure": netting_exposure(n["separate_sets"])},
        "q-capacity": {"single_sell": 300.0, "million_sell": 300_000_000.0,
                       "million_flow_depth": 3.0},
    }
