"""Freeze a visible-information policy, then execute its liquidity intervention.

This public development probe has one policy decision before the cascade.
The observation oracle is an ex-post finite-grid comparator optimized for mean
cost. Model-call counts and protected holdouts require separate evidence.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import subprocess
import time

from .evalmath import build_bank, exact, validate_config
from .runner import sha
from .scoring import loads_json

CONFIG_SCHEMA = "srb.policy.config.v1"


def _runtime_number(value, label, *, positive=False):
    try:
        converted = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{label} exceeds the simulator's binary64 range") from error
    if not math.isfinite(converted) or (value != 0 and converted == 0) or (positive and converted <= 0):
        raise ValueError(f"{label} cannot be represented in the simulator's binary64 range")
    return converted


def validate_policy_config(config):
    if not isinstance(config, dict) or config.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError(f"expected {CONFIG_SCHEMA}")
    if not isinstance(config.get("experiment_id"), str) or not config["experiment_id"].strip():
        raise ValueError("policy config requires experiment_id")
    simulation = config.get("simulation")
    validate_config(simulation)
    if simulation.get("experiment_id") != config["experiment_id"]:
        raise ValueError("policy and simulation experiment IDs must agree")
    budget = exact(config.get("action_budget"), "action_budget")
    if (budget * 100).denominator != 1:
        raise ValueError("action_budget must be denominated in whole cents")
    for action in simulation["actions"]:
        cost = exact(action["cost"], "action cost")
        if (cost * 100).denominator != 1:
            raise ValueError("action costs must be denominated in whole cents")
    if exact(simulation["actions"][0]["cost"], "baseline cost") != 0:
        raise ValueError("fallback baseline must have zero cost")
    # Check numeric conversion without computing outcomes or consuming adapter calls.
    capital = _runtime_number(exact(simulation["initial_capital"], "initial capital"),
                              "initial capital", positive=True)
    _runtime_number(capital * 3, "maximum initial asset value", positive=True)
    _runtime_number(exact(simulation["impact"], "impact"), "impact")
    for shock in simulation["shocks"]:
        _runtime_number(exact(shock, "shock"), "shock")
    for depth in simulation["depths"]:
        base = _runtime_number(exact(depth, "depth"), "depth", positive=True)
        for action in simulation["actions"]:
            multiplier = _runtime_number(action["depth_multiplier"], "depth multiplier", positive=True)
            _runtime_number(base * multiplier, "effective depth", positive=True)


def public_packets(config):
    """Return only information supplied to the policy, one packet per shock."""
    validate_policy_config(config)
    sim = config["simulation"]
    budget = exact(config["action_budget"], "action_budget")
    actions = [{"name": a["name"], "depth_multiplier": a["depth_multiplier"],
                "cost": str(exact(a["cost"], "action cost"))}
               for a in sim["actions"] if exact(a["cost"], "action cost") <= budget]
    return [{
        "schema_version": "srb.policy.packet.v1",
        "observation": {"shock": str(exact(shock, "shock"))},
        "initial_capital": str(exact(sim["initial_capital"], "initial_capital")),
        "action_budget": str(budget),
        "available_actions": deepcopy(actions),
        "action_effect": "Depth multiplier applies before all liquidation rounds.",
        "objective": "Minimize limited-liability investor loss plus creditor shortfall "
                     "plus the action cost paid once by an external sponsor.",
        "response_contract": {"required": {"action": "an available action name"},
                              "optional": {"rationale": "string"}},
    } for shock in sim["shocks"]]


def execute_policy(adapter_argv, packet, timeout):
    """Run an operator-trusted process with the public packet on stdin."""
    request = {"protocol": "srb.policy.adapter.v1", "packet": packet,
               "instruction": "Choose one available action within the budget. Return "
                              "one JSON object with action and optional rationale on stdout."}
    started = time.perf_counter()
    common = {"request_sha256": sha(request), "response": None}
    try:
        result = subprocess.run(adapter_argv, input=json.dumps(request, allow_nan=False),
                                capture_output=True, text=True, encoding="utf-8",
                                timeout=timeout, shell=False)
    except subprocess.TimeoutExpired:
        return {**common, "status": "timeout", "wall_seconds": time.perf_counter() - started}
    except (OSError, UnicodeError) as error:
        return {**common, "status": "adapter_error", "error": str(error),
                "wall_seconds": time.perf_counter() - started}
    receipt = {**common, "status": "ok" if result.returncode == 0 else "adapter_error",
               "exit_code": result.returncode, "wall_seconds": time.perf_counter() - started,
               "stdout_sha256": sha256(result.stdout.encode()).hexdigest(),
               "stderr_tail": result.stderr[-2000:]}
    if result.returncode == 0:
        try:
            receipt["response"] = loads_json(result.stdout)
        except (ValueError, TypeError) as error:
            receipt.update(status="invalid_json", error=str(error))
    return receipt


def _resolve_response(receipt, config):
    baseline = config["simulation"]["baseline"]
    actions = {a["name"]: a for a in config["simulation"]["actions"]}
    if receipt["status"] == "ok":
        response = receipt.get("response")
        if (not isinstance(response, dict) or set(response) - {"action", "rationale"}
                or not isinstance(response.get("action"), str)
                or ("rationale" in response and not isinstance(response["rationale"], str))):
            receipt.update(status="invalid_response", error="expected action and optional string rationale")
        elif response["action"] not in actions:
            receipt.update(status="invalid_action", error="action was not registered")
        elif exact(actions[response["action"]]["cost"], "action cost") > exact(
                config["action_budget"], "action_budget"):
            receipt.update(status="unaffordable_action", error="action exceeds the available budget")
    receipt["fallback_used"] = receipt["status"] != "ok"
    receipt["selected_action"] = baseline if receipt["fallback_used"] else receipt["response"]["action"]
    return receipt


def _stats(rows, alpha):
    mass = sum(row["mass"] for row in rows)
    def mean(key):
        return str(sum(row["mass"] * row[key] for row in rows) / mass)
    remaining = tail_mass = mass * (1 - alpha)
    tail_sum = Fraction(0)
    for row in sorted(rows, key=lambda r: r["total"], reverse=True):
        taken = min(remaining, row["mass"])
        tail_sum += taken * row["total"]
        remaining -= taken
        if remaining == 0:
            break
    return {"expected_investor_loss": mean("investor"),
            "expected_creditor_shortfall": mean("creditor"),
            "expected_action_cost": mean("cost"),
            "expected_total_cost": mean("total"),
            "expected_shortfall_total_cost": str(tail_sum / tail_mass),
            "max_total_cost": str(max(row["total"] for row in rows))}


def evaluate_choices(bank, choices, *, feasible_actions):
    """Compare a frozen policy with mean-optimal policies on the same grid.

Only the aggregate observation-oracle regret must be nonnegative. Its
world-level differences remain signed because the oracle shares a choice
across hidden states.
"""
    if not isinstance(choices, dict) or any(type(k) is not int for k in choices):
        raise ValueError("choices must map integer observation indices to action names")
    registered = {a["name"]: exact(a["cost"], "action cost") for a in bank["actions"]}
    if (not isinstance(feasible_actions, list) or not feasible_actions
            or any(not isinstance(a, str) or a not in registered for a in feasible_actions)
            or len(set(feasible_actions)) != len(feasible_actions)
            or bank["baseline"] not in feasible_actions):
        raise ValueError("feasible actions must be distinct registered actions including the baseline")
    groups = {}
    costs = {}
    for world in bank["worlds"]:
        visible = world["visible"]
        if (not isinstance(visible, list) or len(visible) != 1 or type(visible[0]) is not int
                or type(world["mass"]) is not int or world["mass"] <= 0):
            raise ValueError("worlds require a single integer observation and positive integer mass")
        if world["id"] in costs:
            raise ValueError("duplicate world id")
        groups.setdefault(visible[0], []).append(world)
        costs[world["id"]] = {}
        for name in feasible_actions:
            losses = world["outcomes"][name]["node_loss"]
            if len(losses) != 2:
                raise ValueError("policy scoring requires investor and creditor loss nodes")
            investor, creditor = (exact(v, "node loss") for v in losses)
            costs[world["id"]][name] = {
                "mass": Fraction(world["mass"]), "investor": investor, "creditor": creditor,
                "cost": registered[name], "total": investor + creditor + registered[name]}
    if (not groups or set(choices) != set(groups)
            or any(not isinstance(a, str) or a not in feasible_actions for a in choices.values())):
        raise ValueError("choose one feasible action for every observed group")
    alpha = exact(bank["tail_alpha"], "tail_alpha")
    if alpha >= 1:
        raise ValueError("tail_alpha must be below one")
    # Stable ties follow registered action order, never world order.
    allowed = [name for name in registered if name in feasible_actions]
    oracle = {group: min(allowed, key=lambda name: sum(
        w["mass"] * costs[w["id"]][name]["total"] for w in worlds))
        for group, worlds in groups.items()}
    selected, baseline, observed, privileged, details = [], [], [], [], []
    for world in bank["worlds"]:
        group = world["visible"][0]
        outcomes = costs[world["id"]]
        full_action = min(allowed, key=lambda name: outcomes[name]["total"])
        action = choices[group]
        current, reference = outcomes[action], outcomes[oracle[group]]
        selected.append(current)
        baseline.append(outcomes[bank["baseline"]])
        observed.append(reference)
        privileged.append(outcomes[full_action])
        details.append({
            "world_id": world["id"], "observation_index": group, "mass": world["mass"],
            "selected_action": action, "investor_loss": str(current["investor"]),
            "creditor_shortfall": str(current["creditor"]), "action_cost": str(current["cost"]),
            "total_cost": str(current["total"]),
            "baseline_total_cost": str(outcomes[bank["baseline"]]["total"]),
            "observation_oracle_action": oracle[group],
            "observation_oracle_total_cost": str(reference["total"]),
            "perfect_information_action": full_action,
            "perfect_information_total_cost": str(outcomes[full_action]["total"]),
            "regret_vs_observation_oracle": str(current["total"] - reference["total"]),
        })
    report = {"selected_policy": _stats(selected, alpha), "baseline": _stats(baseline, alpha),
              "observation_oracle": _stats(observed, alpha),
              "perfect_information_bound": _stats(privileged, alpha)}
    mean = lambda key: Fraction(report[key]["expected_total_cost"])
    report.update(
        expected_regret_vs_observation_oracle=str(mean("selected_policy") - mean("observation_oracle")),
        expected_total_cost_change_vs_baseline=str(mean("selected_policy") - mean("baseline")),
        information_gap=str(mean("observation_oracle") - mean("perfect_information_bound")),
        oracle_objective="mass-weighted mean total cost; tail statistics are descriptive",
        observation_oracle_status="ex_post_optimum_on_public_grid_with_stipulated_masses",
        world_results=details,
    )
    return report


def run_policy(config, *, fixture=None, adapter_argv=None, timeout=60):
    """Collect all decisions before simulating and scoring any counterfactual."""
    config = deepcopy(config)
    packets = public_packets(config)
    if (fixture is None) == (adapter_argv is None):
        raise ValueError("choose exactly one fixture or adapter argv")
    if fixture is not None and fixture not in ("baseline", "always_support"):
        raise ValueError("fixture must be baseline or always_support")
    if adapter_argv is not None and (not isinstance(adapter_argv, list) or not adapter_argv
            or any(not isinstance(arg, str) or not arg for arg in adapter_argv)):
        raise ValueError("adapter argv must be a nonempty JSON array of strings")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError("timeout must be finite and in (0,3600]")
    receipts = []
    sim = config["simulation"]
    for index, packet in enumerate(packets):
        if fixture is not None:
            action = sim["baseline"] if fixture == "baseline" else sim["actions"][1]["name"]
            receipt = {"status": "ok", "response": {"action": action}, "wall_seconds": 0.0}
        else:
            receipt = execute_policy(adapter_argv, deepcopy(packet), timeout)
        receipt = _resolve_response(receipt, config)
        receipt.update(observation_index=index, packet=packet, packet_sha256=sha(packet))
        receipts.append(receipt)
    frozen = [{key: r[key] for key in ("observation_index", "packet_sha256", "status", "response",
                                       "selected_action", "fallback_used")} for r in receipts]
    decision_sha = sha(frozen)
    choices = {r["observation_index"]: r["selected_action"] for r in receipts}
    # No evaluator outcomes exist in this run until every response is frozen.
    bank, scores, evaluation_error = None, None, None
    phase = "simulation"
    try:
        bank = build_bank(sim, config_sha256=sha(sim))
        phase = "scoring"
        allowed = [a["name"] for a in packets[0]["available_actions"]]
        scores = evaluate_choices(bank, choices, feasible_actions=allowed)
    except (ValueError, ArithmeticError) as error:
        # Retain potentially costly adapter responses even when a cascade fails.
        evaluation_error = {"phase": phase, "type": type(error).__name__, "message": str(error)}
    root = Path(__file__).resolve().parent
    return {
        "schema_version": "srb.policy.run.v1", "experiment_id": config["experiment_id"],
        "run_status": "complete" if evaluation_error is None else "evaluation_failed",
        "evaluation_error": evaluation_error,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_kind": "fixture" if fixture is not None else "adapter",
        "evidence_status": "public_development", "fixture": fixture,
        "adapter_argv": adapter_argv, "timeout_seconds_per_call": timeout,
        "model_calls": 0 if fixture is not None else None,
        "model_call_count_status": "known_fixture_zero" if fixture is not None else "unmeasured",
        "adapter_invocations": 0 if fixture is not None else len(receipts),
        "policy_decisions": len(receipts), "failed_decisions": sum(r["fallback_used"] for r in receipts),
        "decision_freeze": {"sha256": decision_sha, "completed_before_counterfactual_simulation": True},
        "config": config, "config_sha256": sha(config), "receipts": receipts, "scores": scores,
        "counterfactual_bank": bank, "counterfactual_bank_sha256": sha(bank) if bank is not None else None,
        "runtime": {"python_version": platform.python_version(),
                    "python_implementation": platform.python_implementation(),
                    "platform": platform.platform()},
        "source_sha256": {name: sha256((root / name).read_bytes()).hexdigest()
                          for name in ("policy.py", "evalmath.py", "simulation.py", "risk.py",
                                       "runner.py", "scoring.py")},
        "limits": {
            "policy_horizon": "one pre-cascade liquidity choice; cohort liquidation rules remain fixed",
            "mechanisms": "one public fire-sale mechanism; grid cells are correlated variants",
            "action_cost": "stipulated external sponsor cost, charged once; funding capacity unmodeled",
            "external_harm": "creditor shortfall only; other counterparties and welfare unmodeled",
            "probabilities": "illustrative scenario masses; no market-frequency calibration",
            "adapter_is_operator_trusted_and_unsandboxed": True,
            "holdout_status": "public development inputs; no protected holdout",
            "model_ranking_supported": False,
        },
    }
