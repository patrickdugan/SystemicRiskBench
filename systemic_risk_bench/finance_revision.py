"""SRB-REV-02: synthetic financial evidence revisions with observable policy loss.

Builds on SRB-REV-01's independent two-subprocess information contracts.
All prices, controls, costs, and regimes here are invented development fixtures.
An adapter receives no evaluator regime, earlier transcript, or executable authority.
"""
from __future__ import annotations

import math

from .agent_revision import (
    MAX_CASES, MODES, fixture, initial_packet, initial_posterior,
    parse_forecast, squared, update_packet, validate_memory,
)
from .runner import execute, sha as canonical_sha

SCHEMA = "srb.finance_revision.v1"
ACTIONS = ("continue", "de_risk", "halt_and_escalate")
REGIMES = ("healthy", "stressed", "crisis")
FAMILIES = ("price_feed", "collateral", "counterparty")
MISSING_BRIER = 2.0
MISSING_POLICY_REGRET = 20.0

# Invented loss units, action-major and regime-ordered. Fixed before scoring.
SCENARIOS = {
    "price_feed": {
        "description": "Synthetic BTC-backed book; twelve provider freshness/deviation checks. A later signed provider revision supersedes six checks.",
        "evidence_kind": "price_feed_integrity_check",
        "loss": {"continue": (0.0, 3.0, 15.0),
                 "de_risk": (0.8, 1.5, 4.0),
                 "halt_and_escalate": (2.5, 2.5, 2.5)},
    },
    "collateral": {
        "description": "Synthetic secured loan book; twelve collateral eligibility and haircut checks. Six valuations are revised.",
        "evidence_kind": "collateral_eligibility_check",
        "loss": {"continue": (0.0, 4.0, 18.0),
                 "de_risk": (1.0, 2.0, 5.0),
                 "halt_and_escalate": (3.0, 3.0, 3.0)},
    },
    "counterparty": {
        "description": "Synthetic derivatives exposure; twelve counterparty solvency and settlement checks. Six assessments are superseded.",
        "evidence_kind": "counterparty_reliability_check",
        "loss": {"continue": (0.0, 4.0, 12.0),
                 "de_risk": (0.6, 1.4, 3.5),
                 "halt_and_escalate": (2.3, 2.3, 2.3)},
    },
}


def expected_loss(action: str, posterior, family: str) -> float:
    if family not in SCENARIOS or action not in ACTIONS:
        raise ValueError("unsupported synthetic family or action")
    if len(posterior) != 3 or any(type(p) not in (float, int) or
                                  not math.isfinite(p) or p < 0 for p in posterior):
        raise ValueError("invalid risk posterior")
    return math.fsum(p * loss for p, loss in
                     zip(posterior, SCENARIOS[family]["loss"][action]))


def optimal_action(posterior, family: str) -> str:
    # ACTIONS gives a reproducible tie break, independent of model text.
    return min(ACTIONS, key=lambda action: expected_loss(action, posterior, family))


def policy_regret(action: str, reference, family: str) -> float:
    return max(0.0, expected_loss(action, reference, family) -
               expected_loss(optimal_action(reference, family), reference, family))


def packet(world, mode: str, family: str, phase: str, memory=None) -> dict:
    if family not in FAMILIES or mode not in MODES:
        raise ValueError("unknown family or memory mode")
    if phase == "initial":
        result = initial_packet(world, mode)
        result["old"] = [{**record, "record_id": f"{family}/{record['slot']:02d}",
                          "version": 0} for record in result["old"]]
        result["reply_contract"] = {
            "memory": "exact declared integer encoding of old controls",
            "posterior": "three probabilities ordered healthy/stressed/crisis",
            "action": list(ACTIONS),
        }
    elif phase == "update":
        result = update_packet(world, mode, memory)
        result["corrections"] = [
            {**event, "record_id": f"{family}/{event['slot']:02d}"}
            for event in result["corrections"]
        ]
        result["reply_contract"] = {
            "posterior": "three probabilities ordered healthy/stressed/crisis",
            "action": list(ACTIONS),
        }
    else:
        raise ValueError("unknown revision phase")
    context = SCENARIOS[family]
    result["schema"] = SCHEMA
    result["finance_context"] = {
        "family": family,
        "description": context["description"],
        "evidence_kind": context["evidence_kind"],
        "match_meaning": "1=control passed, 0=control breached",
        "posterior_order": list(REGIMES),
        "action_loss_units": "synthetic expected-loss points per risk decision",
        "loss_by_action_and_regime": {
            action: list(context["loss"][action]) for action in ACTIONS
        },
        "decision_rule": "minimize posterior expected loss with action order tie break",
        "execution": "hypothetical_read_only_decision",
    }
    return result


def parse_response(response: dict, phase: str, world=None, mode=None):
    expected = {"memory", "posterior", "action"} if phase == "initial" else {
        "posterior", "action"}
    if type(response) is not dict or set(response) != expected:
        raise ValueError("financial response fields must match the phase exactly")
    if type(response["action"]) is not str or response["action"] not in ACTIONS:
        raise ValueError("unregistered financial policy action")
    forecast = parse_forecast(
        {key: response[key] for key in ("posterior", "memory")
         if key in response}, phase)
    memory = None
    if phase == "initial":
        memory = validate_memory(
            {"memory": response["memory"], "posterior": response["posterior"]},
            world, mode)
    return forecast, response["action"], memory


def run_financial_revision(adapter_argv: list[str], experiment: dict, *,
                           mode: str, cases: int = 18, timeout: float = 30) -> dict:
    if type(cases) is not int or not 1 <= cases <= MAX_CASES:
        raise ValueError("cases out of range")
    if mode not in MODES:
        raise ValueError("unsupported codec")
    if type(experiment) is not dict or type(experiment.get("experiment_id")) is not str or not experiment["experiment_id"]:
        raise ValueError("nonempty experiment_id required")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError("timeout must be finite positive seconds")
    rows = []
    for index in range(cases):
        world = fixture(index)
        family = FAMILIES[index % len(FAMILIES)]
        first_packet = packet(world, mode, family, "initial")
        first = execute(adapter_argv, first_packet, [], timeout, experiment)
        row = {
            "index": index, "case_id": world.case_id, "family": family, "mode": mode,
            "initial_packet_sha256": canonical_sha(first_packet),
            "initial_receipt": first, "update_receipt": None,
            "status": "initial_invalid", "initial_error": None,
            "initial_forecast": None, "initial_action": None,
            "initial_excess_brier": None, "initial_policy_regret": None,
            "update_forecast": None, "update_action": None,
            "excess_brier": None, "sample_brier": None,
            "policy_regret_vs_matched": None, "policy_regret_vs_full": None,
            "realized_loss": None, "information_loss_sq": squared(
                world.exact_count, world.exact_full),
            "optimal_full_action": optimal_action(world.exact_full, family),
            "optimal_arm_action": optimal_action(
                world.exact_count if mode == "count" else world.exact_full, family),
        }
        if first["status"] != "ok":
            row["initial_error"] = first["status"]
        else:
            try:
                initial_forecast, initial_action, memory = parse_response(
                    first["response"], "initial", world, mode)
                prior = initial_posterior(world.old_count)
                row.update(
                    initial_forecast=list(initial_forecast), initial_action=initial_action,
                    initial_excess_brier=squared(initial_forecast, prior),
                    initial_policy_regret=policy_regret(initial_action, prior, family),
                )
                second_packet = packet(world, mode, family, "update", memory)
                second = execute(adapter_argv, second_packet, [], timeout, experiment)
                row["update_packet_sha256"] = canonical_sha(second_packet)
                row["update_receipt"] = second
                if second["status"] == "ok":
                    try:
                        forecast, action, _ = parse_response(
                            second["response"], "update")
                        ref = world.exact_count if mode == "count" else world.exact_full
                        row.update(
                            status="scored", update_forecast=list(forecast),
                            update_action=action, input_matched_reference=list(map(float, ref)),
                            excess_brier=squared(forecast, ref),
                            sample_brier=squared(forecast, tuple(
                                int(k == world.regime) for k in range(3))),
                            policy_regret_vs_matched=policy_regret(action, ref, family),
                            policy_regret_vs_full=policy_regret(action, world.exact_full, family),
                            realized_loss=SCENARIOS[family]["loss"][action][world.regime],
                            action_revised=(initial_action != action),
                            action_matches_arm_optimum=(action == optimal_action(ref, family)),
                            missed_full_escalation=(
                                optimal_action(world.exact_full, family) == "halt_and_escalate"
                                and action != "halt_and_escalate"),
                        )
                    except (ValueError, TypeError, KeyError) as error:
                        row.update(status="invalid_forecast_or_action",
                                   update_error=str(error))
                else:
                    row["status"] = "update_" + second["status"]
            except (ValueError, TypeError, KeyError) as error:
                row["initial_error"] = str(error)
        rows.append(row)
    scored = [row for row in rows if row["status"] == "scored"]
    total = lambda key, penalty: sum(
        row[key] if row["status"] == "scored" else penalty for row in rows) / cases
    return {
        "schema": SCHEMA,
        "evidence_class": "public_deterministic_synthetic_financial_development_only",
        "model_evaluation_claim": False, "scientific_confirmation_claim": False,
        "physical_memory_enforced": False, "adapter_process_sandboxed": False,
        "model_server_state_reset_verified": False,
        "authority": "read_only_no_orders_no_signing",
        "experiment": experiment, "experiment_sha256": canonical_sha(experiment),
        "mode": mode, "n_cases": cases, "n_scored": len(scored),
        "coverage": len(scored) / cases, "n_cases_by_family": {
            family: sum(row["family"] == family for row in rows) for family in FAMILIES},
        "model_calls_attempted": sum(
            1 + (row["update_receipt"] is not None) for row in rows),
        "memory_logical_bits": 4 if mode == "count" else 12,
        "missing_brier_penalty": MISSING_BRIER,
        "missing_policy_regret_penalty": MISSING_POLICY_REGRET,
        "mean_excess_brier_with_missing_penalty": total("excess_brier", MISSING_BRIER),
        "mean_policy_regret_with_missing_penalty": total(
            "policy_regret_vs_matched", MISSING_POLICY_REGRET),
        "mean_sample_brier_with_missing_penalty": total(
            "sample_brier", MISSING_BRIER),
        "mean_policy_regret_vs_full_scored": (
            sum(row["policy_regret_vs_full"] for row in scored)/len(scored)
            if scored else None),
        "mean_information_loss_sq_all_cases": sum(
            row["information_loss_sq"] for row in rows)/cases,
        "action_accuracy_scored": (sum(
            row["action_matches_arm_optimum"] for row in scored)/len(scored)
            if scored else None),
        "action_revision_rate_scored": (sum(
            row["action_revised"] for row in scored)/len(scored)
            if scored else None),
        "missed_full_escalations_scored": sum(
            row["missed_full_escalation"] for row in scored),
        "prior_responses_suppressed": True,
        "original_history_excluded_from_update": True,
        "hidden_regime_excluded_from_packets": True,
        "reference_is_evaluator_only": True,
        "rows": rows,
    }
