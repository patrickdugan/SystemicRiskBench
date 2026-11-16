"""Small explicit reference calculators; amounts are in scenario currency units."""

import math


def number(value, name="value", minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        value = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} is outside supported numeric range") from error
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return value


def distribution(values, probabilities):
    if not values or len(values) != len(probabilities):
        raise ValueError("nonempty values and probabilities must have equal length")
    values = [number(x) for x in values]
    probabilities = [number(p, "probability", 0, 1) for p in probabilities]
    if not math.isclose(sum(probabilities), 1, abs_tol=1e-10, rel_tol=0):
        raise ValueError("probabilities must sum to one; they are never silently normalized")
    return [(x, p) for x, p in zip(values, probabilities) if p > 0]


def tail_risk(losses, probabilities, alpha):
    """Left-quantile VaR and integral ES, including fractional boundary mass."""
    alpha = number(alpha, "alpha", 0, 1)
    if not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between zero and one")
    pairs = sorted(distribution(losses, probabilities))
    cumulative = 0.0
    var = pairs[-1][0]
    for loss, probability in pairs:
        cumulative += probability
        if cumulative >= alpha:
            var = loss
            break
    remaining = 1 - alpha
    tail_total = 0.0
    for loss, probability in reversed(pairs):
        taken = min(remaining, probability)
        tail_total += loss * taken
        remaining -= taken
        if remaining <= 1e-14:
            break
    return {"var": var, "expected_shortfall": tail_total / (1 - alpha)}


def unilateral_cva(expected_exposures, default_increments, discounts, recovery):
    """LGD sum D_i EE_i dPD_i. PD increments are unconditional, disjoint masses.

    This factorized toy formula assumes exposure/default independence. Inputs
    labeled pricing use a stipulated risk-neutral measure, not estimated PDs.
    """
    if not expected_exposures or not (
        len(expected_exposures) == len(default_increments) == len(discounts)
    ):
        raise ValueError("CVA arrays must be nonempty and have equal length")
    recovery = number(recovery, "recovery", 0, 1)
    exposures = [number(e, "exposure", 0) for e in expected_exposures]
    increments = [number(p, "default increment", 0, 1) for p in default_increments]
    factors = [number(d, "discount", 0) for d in discounts]
    if sum(increments) > 1 + 1e-12:
        raise ValueError("unconditional default increments cannot exceed one in total")
    return (1 - recovery) * sum(e * p * d for e, p, d in zip(exposures, increments, factors))


def joint_state_credit_loss(exposures, conditional_pd, state_probabilities, recovery):
    """One-period discounted-at-one credit loss with exposure/default dependence."""
    distribution(exposures, state_probabilities)
    if len(conditional_pd) != len(exposures):
        raise ValueError("conditional PD array must match exposures")
    pd = [number(p, "conditional PD", 0, 1) for p in conditional_pd]
    exposure = [number(e, "exposure", 0) for e in exposures]
    recovery = number(recovery, "recovery", 0, 1)
    # Keep zero-probability states aligned with their PDs.
    return (1 - recovery) * sum(e * p * w for e, p, w in zip(exposure, pd, state_probabilities))


def settlement_principal_loss(principal, fail_probability, recovery, pvp):
    if not isinstance(pvp, bool):
        raise ValueError("pvp must be boolean")
    principal = number(principal, "principal", 0)
    fail_probability = number(fail_probability, "fail_probability", 0, 1)
    recovery = number(recovery, "recovery", 0, 1)
    return 0.0 if pvp else principal * fail_probability * (1 - recovery)


def netting_exposure(netting_sets):
    if not netting_sets or any(not positions for positions in netting_sets):
        raise ValueError("need nonempty legally enforceable netting sets")
    return sum(max(0, sum(number(v) for v in positions)) for positions in netting_sets)
