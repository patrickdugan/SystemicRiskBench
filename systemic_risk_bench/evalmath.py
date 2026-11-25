"""Export source-bound simulator counterfactuals for EvalMath SRB-01.

Evaluator-only export. The historical episodes are deliberately excluded:
their narratives lack complete action-by-world counterfactual loss vectors.
Simulator values are binary64; deterministic cent quantization creates an
exact rational *scoring input*, not an exact solution to the market model.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path

from .scoring import read_json
from .simulation import simulate

SCHEMA = "SRB-EvalMath-01"
CONFIG_SCHEMA = "srb.evalmath.simulation_config.v1"
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "configs/evalmath-simulation-v1.json"


def exact(value, label: str, *, positive: bool = False) -> Fraction:
    if type(value) is not str:
        raise ValueError(f"{label} must be an exact rational string")
    try:
        x = Fraction(value)
    except (ValueError, TypeError, ZeroDivisionError) as error:
        raise ValueError(f"{label} must be a rational string") from error
    try:
        finite = math.isfinite(float(x))
    except OverflowError:
        finite = False
    if x < 0 or (positive and x == 0) or not finite:
        raise ValueError(f"{label} must be finite and {'positive' if positive else 'nonnegative'}")
    return x


def cents(value: float) -> int:
    """Quantize an already computed finite simulator float to integer cents."""
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("finite numeric simulator loss required")
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def money(cents_value: int) -> str:
    """Canonical exact rational USD amount."""
    return str(Fraction(cents_value, 100))


def validate_config(doc: dict) -> None:
    if not isinstance(doc, dict) or doc.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError(f"expected {CONFIG_SCHEMA}")
    if (type(doc.get("agents_represented")) is not int or doc["agents_represented"] < 1
            or type(doc.get("max_rounds")) is not int or doc["max_rounds"] < 1
            or type(doc.get("mass_per_scenario")) is not int or doc["mass_per_scenario"] < 1):
        raise ValueError("agents, rounds and scenario mass must be positive integers")
    exact(doc.get("initial_capital"), "initial_capital", positive=True)
    exact(doc.get("impact"), "impact")
    threshold = exact(doc.get("harm_threshold"), "harm_threshold", positive=True)
    alpha = exact(doc.get("tail_alpha"), "tail_alpha")
    if alpha >= 1:
        raise ValueError("tail_alpha must be less than 1")
    for name in ("shocks", "depths", "cohort_profiles"):
        if (not isinstance(doc.get(name), list) or not doc[name]
                or any(type(value) is not str for value in doc[name])
                or len(set(doc[name])) != len(doc[name])):
            raise ValueError(f"{name} must contain distinct choices")
    shocks = [exact(shock, "shock") for shock in doc["shocks"]]
    depths = [exact(depth, "depth", positive=True) for depth in doc["depths"]]
    for name, values in (("shocks", shocks), ("depths", depths)):
        if len(set(values)) != len(values):
            raise ValueError(f"{name} must contain distinct rational values")
    for shock in shocks:
        if shock >= Fraction(99, 100):
            raise ValueError("shock must be below 0.99")
    if any(p not in ("homogeneous", "heterogeneous") for p in doc["cohort_profiles"]):
        raise ValueError("unknown simulator cohort profile")
    actions = doc.get("actions")
    if not isinstance(actions, list) or len(actions) != 2 or any(not isinstance(a, dict) for a in actions):
        raise ValueError("register exactly two liquidity actions for the binary certificate")
    names = [a.get("name") for a in actions]
    if any(not isinstance(n, str) or not n for n in names) or len(set(names)) != 2:
        raise ValueError("action names must be unique strings")
    if doc.get("baseline") != names[0] or actions[0].get("depth_multiplier") != 1:
        raise ValueError("first action must be the baseline with multiplier one")
    for a in actions:
        if type(a.get("depth_multiplier")) is not int or a["depth_multiplier"] < 1:
            raise ValueError("depth_multiplier must be a positive integer")
        exact(a.get("cost"), "action cost")
    if doc.get("observation") != "shock_index_only" or doc.get("query_names") != ["depth_tier", "cohort_profile"]:
        raise ValueError("observation and query vocabulary must be registered")
    if doc.get("claimed_safe_checker") != "exogenous_only_v1":
        raise ValueError("only the registered exogenous-only heuristic is implemented")
    if doc.get("quantization") != "Decimal(str(float_value)) nearest cent, ROUND_HALF_EVEN":
        raise ValueError("quantization policy is part of the scoring contract")
    if (threshold * 100).denominator != 1:
        raise ValueError("harm threshold must be denominated in whole cents")


def build_bank(config: dict, *, config_sha256: str | None = None) -> dict:
    validate_config(config)
    baseline_name = config["baseline"]
    threshold_cents = int(exact(config["harm_threshold"], "harm_threshold") * 100)
    total = float(exact(config["initial_capital"], "initial_capital", positive=True))
    impact = float(exact(config["impact"], "impact"))
    worlds = []
    n_runs = 0
    for shock_i, shock in enumerate(config["shocks"]):
        for depth_i, depth in enumerate(config["depths"]):
            for profile_i, profile in enumerate(config["cohort_profiles"]):
                outcomes = {}
                exogenous = []
                for action in config["actions"]:
                    result = simulate(
                        agents=config["agents_represented"],
                        fixed_total_capital=total,
                        cohort_profile=profile,
                        shock=float(exact(shock, "shock")),
                        depth=float(exact(depth, "depth", positive=True)) * action["depth_multiplier"],
                        impact=impact,
                        max_rounds=config["max_rounds"],
                    )
                    n_runs += 1
                    if not result["converged"] or result["termination_reason"] != "flow_tolerance":
                        raise ValueError("nonconverged simulator outcome: registration must be amended")
                    investor = cents(result["limited_liability_investor_loss"])
                    creditor = cents(result["creditor_shortfall"])
                    book = cents(result["uncapped_book_equity_loss"])
                    if investor < 0 or creditor < 0 or abs(investor + creditor - book) > 1:
                        raise ValueError("negative loss or accounting mismatch exceeds one cent")
                    exogenous.append(cents(result["exogenous_book_loss"]))
                    outcomes[action["name"]] = {
                        "node_loss": [money(investor), money(creditor)],
                        "claimed_safe": False,
                    }
                if len(set(exogenous)) != 1:
                    raise ValueError("depth-only intervention changed the exogenous shock loss")
                safe = exogenous[0] < threshold_cents
                for outcome in outcomes.values():
                    outcome["claimed_safe"] = safe
                worlds.append({
                    "id": f"shock{shock_i}_depth{depth_i}_profile{profile_i}",
                    "mass": config["mass_per_scenario"],
                    "visible": [shock_i],
                    "queries": [depth_i, profile_i],
                    "outcomes": outcomes,
                })
    repo_root = Path(__file__).resolve().parents[1]
    return {
        "schema": SCHEMA,
        "nodes": ["limited_liability_investor_loss", "creditor_shortfall"],
        "actions": [{"name": a["name"], "cost": a["cost"]} for a in config["actions"]],
        "baseline": baseline_name,
        "query_names": config["query_names"],
        "harm_threshold": config["harm_threshold"],
        "tail_alpha": config["tail_alpha"],
        "worlds": worlds,
        "source": {
            "repo": "patrickdugan/SystemicRiskBench",
            "experiment_id": config["experiment_id"],
            "simulator": "cohort_fire_sale_v0.1",
            "simulator_module_sha256": sha256((repo_root / "systemic_risk_bench/simulation.py").read_bytes()).hexdigest(),
            "exporter_module_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "config_sha256": config_sha256,
            "model_calls": 0,
            "counterfactual_evidence": "same simulator, paired depth-only intervention; USD losses rounded to cents",
            "scenario_mass": "equal mass per grid cell; illustrative, not estimated probabilities",
            "loss_accounting": "investor limited-liability loss plus creditor shortfall; no double counting",
            "claimed_safe_checker": "toy exogenous-book-loss-only heuristic, no model or human grader",
            "visibility": "shock index visible; depth and cohort profile query-gated",
            "quantization": config["quantization"],
            "historical_cases_included": False,
            "simulations": n_runs,
        },
    }


def export_bank(config_path: str | Path = DEFAULT_CONFIG) -> dict:
    raw = Path(config_path).read_bytes()
    # Same duplicate-key/nonfinite loader as the main benchmark.
    doc = read_json(config_path)
    return build_bank(doc, config_sha256=sha256(raw).hexdigest())
