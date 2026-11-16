"""Deterministic cohort fire-sale stress probe, not a calibrated market model."""

import math
from .risk import number


def simulate(*, agents=1_000_000, capital_per_agent=1000, fixed_total_capital=None,
             cohort_profile="homogeneous", shock=0.08, depth=100_000_000, impact=0.08,
             max_rounds=50):
    if isinstance(agents, bool) or not isinstance(agents, int) or agents < 1:
        raise ValueError("agents must be a positive integer")
    if cohort_profile not in ("homogeneous", "heterogeneous"):
        raise ValueError("cohort_profile must be homogeneous or heterogeneous")
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 1:
        raise ValueError("max_rounds must be a positive integer")
    capital_per_agent = number(capital_per_agent, "capital_per_agent", 0)
    total = agents * capital_per_agent if fixed_total_capital is None else number(
        fixed_total_capital, "fixed_total_capital", 0
    )
    if total <= 0:
        raise ValueError("total capital must be positive")
    shock = number(shock, "shock", 0, 0.99)
    depth = number(depth, "depth", 0)
    if depth <= 0:
        raise ValueError("depth must be positive")
    impact = number(impact, "impact", 0)
    # Weighted cohorts preserve a million-agent capital balance without claiming
    # a million independent model calls. Heterogeneity is an explicit ablation.
    specifications = [(1.0, 3.0, 3.2, 0.04)] if cohort_profile == "homogeneous" else [
        (0.35, 3.0, 3.2, 0.03), (0.35, 2.0, 2.8, 0.12), (0.30, 1.0, 1.8, 0.25)
    ]
    cohorts = []
    for weight, leverage, limit, reserve in specifications:
        equity = total * weight
        cash = equity * reserve
        assets = (equity - cash) * leverage
        cohorts.append({"weight": weight, "shares": assets, "cash": cash,
                        "debt": assets - (equity - cash), "limit": limit,
                        "defaulted": False})
    price = 1 - shock
    initial_equity = sum(c["cash"] + c["shares"] * price - c["debt"] for c in cohorts)
    exogenous_loss = total - initial_equity
    trace = []
    converged = False
    floor_hit = False
    impact_cap_hit = False
    for round_index in range(max_rounds):
        orders = []
        for cohort in cohorts:
            risky_value = cohort["shares"] * price
            equity = cohort["cash"] + risky_value - cohort["debt"]
            if equity <= 0:
                cohort["defaulted"] = True
                sell = risky_value
            else:
                # A sale repays debt at the current price. Cash is retained.
                # Mark equity unchanged before next-round price impact.
                sell = min(risky_value, max(0, risky_value - cohort["limit"] * equity))
            orders.append(sell)
        flow = sum(orders)
        if flow <= total * 1e-10:
            converged = True
            break
        for cohort, sale in zip(cohorts, orders):
            cohort["shares"] = max(0, cohort["shares"] - sale / price)
            repayment = min(cohort["debt"], sale)
            cohort["debt"] -= repayment
            cohort["cash"] += sale - repayment
        # Permanent log-price impact per currency of synchronized selling.
        impact_exponent = impact * flow / depth
        impact_cap_hit |= impact_exponent > 700
        price *= math.exp(-min(700, impact_exponent))
        floor_hit |= price < 1e-12
        price = max(1e-12, price)
        trace.append({"round": round_index + 1, "sale_notional": flow, "price": price})
    equities = [c["cash"] + c["shares"] * price - c["debt"] for c in cohorts]
    default_weight = sum(c["weight"] for c, e in zip(cohorts, equities)
                         if c["defaulted"] or e <= 0)
    total_loss = total - sum(equities)
    creditor_shortfall = sum(max(0, -e) for e in equities)
    return {
        "model": "cohort_fire_sale_v0.1", "agents_represented": agents,
        "independent_agent_decisions_simulated": 0, "cohort_count": len(cohorts),
        "capital_mode": "fixed_total" if fixed_total_capital is not None else "fixed_per_agent",
        "total_initial_equity": total, "cohort_profile": cohort_profile,
        "profile_comparison_is_not_isolated_synchronization_ablation": True,
        "final_price": price, "exogenous_book_loss": exogenous_loss,
        "uncapped_book_equity_loss": total_loss,
        "limited_liability_investor_loss": total - sum(max(0, e) for e in equities),
        "creditor_shortfall": creditor_shortfall,
        "endogenous_book_loss": total_loss - exogenous_loss,
        "default_capital_weight": default_weight,
        "book_loss_amplification": total_loss / exogenous_loss if exogenous_loss > 0 else None,
        "rounds": len(trace), "converged": converged and not floor_hit and not impact_cap_hit,
        "flow_tolerance_reached": converged, "price_floor_hit": floor_hit,
        "impact_cap_hit": impact_cap_hit,
        "termination_reason": "numerical_floor_or_cap" if floor_hit or impact_cap_hit
        else "flow_tolerance" if converged else "max_rounds", "trace": trace,
    }


def sweep():
    rows = []
    for agents in (1, 1000, 1_000_000, 10_000_000):
        for fixed in (None, 1_000_000_000):
            for profile in ("heterogeneous", "homogeneous"):
                row = simulate(agents=agents, fixed_total_capital=fixed, cohort_profile=profile)
                row.pop("trace")
                rows.append(row)
    return rows
