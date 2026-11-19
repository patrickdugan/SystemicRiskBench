"""SRB-REV-02: synthetic financial evidence revisions with observable policy loss.

Builds on SRB-REV-01's independent two-subprocess information contracts.
All prices, controls, costs, and regimes here are invented development fixtures.
An adapter receives no evaluator regime, earlier transcript, or executable authority.
"""
from __future__ import annotations

import math
import time
from fractions import Fraction

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
    if len(posterior) != 3 or any(type(p) not in (float, int, Fraction) or
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
    if phase not in ("initial", "update"):
        raise ValueError("unknown financial response phase")
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


def _model_summary(rows: list[dict]) -> dict:
    """Fixed panel denominators for loss and coverage; valid-pair coherence."""
    cases = len(rows)
    scored = [row for row in rows if row["status"] == "scored"]
    initial_valid = [row for row in rows if row["initial_forecast"] is not None]
    def penalized(key, penalty):
        return math.fsum(row[key] if row["status"] == "scored" else penalty
                         for row in rows) / cases
    def mean_valid(items, key):
        return math.fsum(row[key] for row in items) / len(items) if items else None
    initial_incoherent = sum(not row["initial_action_forecast_coherent"] for row in initial_valid)
    update_incoherent = sum(not row["update_action_forecast_coherent"] for row in scored)
    return {
        "n_cases": cases, "n_scored": len(scored), "coverage": len(scored) / cases,
        "n_initial_valid": len(initial_valid), "initial_coverage": len(initial_valid) / cases,
        "mean_excess_brier_with_missing_penalty": penalized("excess_brier", MISSING_BRIER),
        "mean_sample_brier_with_missing_penalty": penalized("sample_brier", MISSING_BRIER),
        "mean_policy_regret_with_missing_penalty": penalized("policy_regret_vs_matched", MISSING_POLICY_REGRET),
        "mean_policy_regret_vs_full_with_missing_penalty": penalized("policy_regret_vs_full", MISSING_POLICY_REGRET),
        "mean_policy_regret_vs_full_scored": mean_valid(scored, "policy_regret_vs_full"),
        "mean_information_loss_sq_all_cases": mean_valid(rows, "information_loss_sq"),
        "mean_information_constrained_expected_regret": mean_valid(rows, "information_constrained_expected_regret"),
        "action_accuracy_scored": mean_valid(scored, "action_matches_arm_optimum"),
        "action_accuracy_with_missing_penalty": math.fsum(
            row["action_matches_arm_optimum"] for row in scored) / cases,
        "action_revision_rate_scored": mean_valid(scored, "action_revised"),
        "missed_full_escalations_scored": sum(row["missed_full_escalation"] for row in scored),
        "initial_action_forecast_incoherent_count": initial_incoherent,
        "initial_action_forecast_incoherent_rate_valid": initial_incoherent / len(initial_valid) if initial_valid else None,
        "mean_initial_action_forecast_regret_valid": mean_valid(initial_valid, "initial_action_forecast_regret"),
        "update_action_forecast_incoherent_count": update_incoherent,
        "update_action_forecast_incoherent_rate_scored": update_incoherent / len(scored) if scored else None,
        "mean_update_action_forecast_regret_scored": mean_valid(scored, "update_action_forecast_regret"),
    }


def _registered_model_budget(experiment, panel, manifest, mode, cases):
    model = (experiment.get("evaluation_kind") == "model" or
             experiment.get("evaluation") == "model" or
             experiment.get("model_evaluation") is True)
    if not model:
        return None
    if panel == "legacy" or manifest is None:
        raise ValueError("model registration requires a frozen named panel")
    for key, value in (("panel", panel), ("panel_manifest_sha256", manifest["manifest_sha256"])):
        if experiment.get(key) != value:
            raise ValueError("model registration does not bind " + key)
    if (type(experiment.get("preregistered_cases")) is not int or
            experiment["preregistered_cases"] != cases or
            type(experiment.get("max_calls_per_arm")) is not int or
            experiment["max_calls_per_arm"] != 2 * cases):
        raise ValueError("model registration requires exactly two calls per registered root")
    if experiment.get("memory_arms") != list(MODES) or mode not in MODES:
        raise ValueError("model registration must freeze both memory arms in canonical order")
    wall = experiment.get("max_wall_seconds_per_arm")
    if type(wall) not in (int, float) or not math.isfinite(wall) or not 0 < wall <= 86400:
        raise ValueError("model registration requires a finite positive per-arm wall budget")
    return wall


def _cost_summary(receipts: list[dict]) -> dict:
    attempted = [receipt for receipt in receipts if receipt["status"] != "budget_exhausted"]
    valid = [receipt["adapter_telemetry"] for receipt in attempted
             if receipt.get("telemetry_status") == "valid" and receipt.get("adapter_telemetry")]
    inputs = [entry["usage"]["input_tokens"] for entry in valid
              if entry["usage"]["input_tokens"] is not None]
    outputs = [entry["usage"]["output_tokens"] for entry in valid
               if entry["usage"]["output_tokens"] is not None]
    n = len(attempted)
    return {
        "provenance": "host_wall_time_and_adapter_reported_server_counters",
        "independent_runtime_attestation": False,
        "adapter_calls_attempted": n,
        "calls_with_valid_telemetry": len(valid),
        "calls_with_invalid_telemetry": sum(receipt.get("telemetry_status") == "invalid" for receipt in attempted),
        "telemetry_coverage": len(valid) / n if n else 0.0,
        "input_token_coverage": len(inputs) / n if n else 0.0,
        "output_token_coverage": len(outputs) / n if n else 0.0,
        "input_tokens_observed": sum(inputs) if inputs else None,
        "output_tokens_observed": sum(outputs) if outputs else None,
        "input_tokens_all_calls": sum(inputs) if n and len(inputs) == n else None,
        "output_tokens_all_calls": sum(outputs) if n and len(outputs) == n else None,
        "adapter_reported_inference_seconds_observed": math.fsum(entry["elapsed_seconds"] for entry in valid) if valid else None,
        "adapter_reported_inference_seconds_all_calls": math.fsum(entry["elapsed_seconds"] for entry in valid) if n and len(valid) == n else None,
        "failed_calls_with_usage": sum(entry["status"] != "ok" and (
            entry["usage"]["input_tokens"] is not None or entry["usage"]["output_tokens"] is not None) for entry in valid),
    }


def run_financial_revision(adapter_argv: list[str], experiment: dict, *,
                           mode: str, cases: int | None = None, timeout: float = 30,
                           panel: str = "legacy", manifest: dict | None = None) -> dict:
    from .finance_revision_panels import oracle_summary, panel_indices
    if panel == "legacy":
        cases = 18 if cases is None else cases
        if type(cases) is not int or not 1 <= cases <= MAX_CASES:
            raise ValueError("cases out of range")
        if manifest is not None:
            raise ValueError("legacy case selection cannot claim a frozen panel manifest")
        indices = tuple(range(cases))
    else:
        if cases is not None:
            raise ValueError("named panel fixes its cases; omit the cases override")
        indices = panel_indices(panel, manifest)
        cases = len(indices)
    if mode not in MODES:
        raise ValueError("unsupported codec")
    if type(experiment) is not dict or type(experiment.get("experiment_id")) is not str or not experiment["experiment_id"]:
        raise ValueError("nonempty experiment_id required")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError("timeout must be finite positive seconds")
    wall_budget = _registered_model_budget(experiment, panel, manifest, mode, cases)
    started = time.monotonic()
    calls = 0
    def stage(payload):
        nonlocal calls
        remaining = None if wall_budget is None else wall_budget - (time.monotonic() - started)
        if calls >= 2 * cases or (remaining is not None and remaining <= 0):
            return {"status": "budget_exhausted", "wall_seconds": 0.0,
                    "response": None, "input_tokens": None, "output_tokens": None}
        calls += 1
        return execute(adapter_argv, payload, [], timeout if remaining is None else min(timeout, remaining), experiment)
    rows = []
    for index in indices:
        world = fixture(index)
        family = FAMILIES[index % len(FAMILIES)]
        first_packet = packet(world, mode, family, "initial")
        first = stage(first_packet)
        arm_reference = world.exact_count if mode == "count" else world.exact_full
        arm_action = optimal_action(arm_reference, family)
        row = {
            "index": index, "case_id": world.case_id, "family": family, "mode": mode,
            "initial_packet_sha256": canonical_sha(first_packet),
            "initial_receipt": first, "update_receipt": None,
            "status": "initial_invalid", "initial_error": None,
            "initial_forecast": None, "initial_action": None,
            "initial_excess_brier": None, "initial_policy_regret": None,
            "initial_action_forecast_regret": None,
            "initial_action_forecast_coherent": None,
            "update_forecast": None, "update_action": None,
            "excess_brier": None, "sample_brier": None,
            "policy_regret_vs_matched": None, "policy_regret_vs_full": None,
            "update_action_forecast_regret": None,
            "update_action_forecast_coherent": None,
            "realized_loss": None, "information_loss_sq": squared(
                world.exact_count, world.exact_full),
            "optimal_full_action": optimal_action(world.exact_full, family),
            "optimal_arm_action": arm_action,
            "information_constrained_expected_regret": policy_regret(
                arm_action, world.exact_full, family),
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
                    initial_action_forecast_regret=policy_regret(initial_action, initial_forecast, family),
                    initial_action_forecast_coherent=(initial_action == optimal_action(initial_forecast, family)),
                )
                second_packet = packet(world, mode, family, "update", memory)
                second = stage(second_packet)
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
                            update_action_forecast_regret=policy_regret(action, forecast, family),
                            update_action_forecast_coherent=(action == optimal_action(forecast, family)),
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
    family_summaries = {}
    for family in FAMILIES:
        family_rows = [row for row in rows if row["family"] == family]
        if family_rows:
            family_summaries[family] = {
                **oracle_summary([row["index"] for row in family_rows]),
                **_model_summary(family_rows),
            }
    receipts = [row[key] for row in rows for key in ("initial_receipt", "update_receipt")
                if row[key] is not None]
    attempted = [receipt for receipt in receipts if receipt["status"] != "budget_exhausted"]
    return {
        "schema": SCHEMA,
        "report_schema": "srb.finance_revision.report.v2",
        "evidence_class": "public_deterministic_synthetic_financial_development_only",
        "model_evaluation_claim": False, "scientific_confirmation_claim": False,
        "physical_memory_enforced": False, "adapter_process_sandboxed": False,
        "model_server_state_reset_verified": False,
        "authority": "read_only_no_orders_no_signing",
        "experiment": experiment, "experiment_sha256": canonical_sha(experiment),
        "adapter_argv_sha256": canonical_sha(adapter_argv),
        "timeout_seconds_per_call": timeout,
        "panel": panel,
        "panel_manifest_sha256": manifest["manifest_sha256"] if manifest else None,
        "panel_summary": oracle_summary(indices),
        "family_summaries": family_summaries,
        "reference_law": "original_unconditioned_source_law",
        "selection_conditioned_bayes_claim": False,
        "population_estimate_claim": False,
        "coherence_rule": "reported_action_equals_argmin_with_registered_action_order_tie_break",
        "mode": mode, **_model_summary(rows), "n_cases_by_family": {
            family: sum(row["family"] == family for row in rows) for family in FAMILIES},
        "model_calls_attempted": len(attempted),
        "adapter_calls_attempted": len(attempted),
        "model_calls_attempted_field_scope": "legacy_name_counts_adapter_subprocesses_including_fixtures",
        "host_measured_wall_seconds": math.fsum(receipt["wall_seconds"] for receipt in receipts),
        "inference_costs": _cost_summary(receipts),
        "max_wall_seconds_per_arm": wall_budget,
        "n_stages_skipped_for_budget": sum(receipt["status"] == "budget_exhausted" for receipt in receipts),
        "memory_logical_bits": 4 if mode == "count" else 12,
        "missing_brier_penalty": MISSING_BRIER,
        "missing_policy_regret_penalty": MISSING_POLICY_REGRET,
        "prior_responses_suppressed": True,
        "original_history_excluded_from_update": True,
        "hidden_regime_excluded_from_packets": True,
        "reference_is_evaluator_only": True,
        "rows": rows,
    }
