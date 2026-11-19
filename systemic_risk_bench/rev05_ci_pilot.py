"""SRB-REV-05 live BitAgent CPU pilot: visible-state codec ablation.

The original SRB-REV-03 source functions and frozen panel manifest are untouched.
This evaluator uses only a subset of public registered roots (0,5), measuring
raw model memory separately from a declared host-computed visible-state codec.
The intervention changes only the integer passed between stages, never the
model's initial posterior/action, hidden regime, or corrected observations.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

from .agent_revision import fixture, initial_posterior, parse_forecast, squared
from .finance_revision import (
    ACTIONS, FAMILIES, MISSING_BRIER, MISSING_POLICY_REGRET,
    optimal_action, packet, parse_response, policy_regret,
)
from .revision_receipts import canonical_sha
from .runner import execute

SCHEMA = "srb.rev05.cpu_pilot.run.v1"
MODES = ("count", "bitmap")
TREATMENTS = ("model_memory", "verified_visible_codec")
REPORT_GATE_KEYS = (
    "exact_visible_codec", "genuine_model_inference_observed",
    "verified_codec_any_completed", "verified_codec_better_than_model_memory",
)


def visible_codec(packet_initial: dict) -> int:
    """Derive retained state exclusively from initially visible records."""
    if packet_initial.get("phase") != "initial" or packet_initial.get("memory_codec") not in MODES:
        raise ValueError("visible codec only accepts registered initial packets")
    old = packet_initial.get("old")
    if type(old) is not list or len(old) != 12:
        raise ValueError("visible codec requires 12 old records")
    value = 0
    for expected, record in enumerate(old):
        if (type(record) is not dict or type(record.get("slot")) is not int
                or record["slot"] != expected or type(record.get("match")) is not int
                or record["match"] not in (0, 1)):
            raise ValueError("malformed or permuted old record")
        if packet_initial["memory_codec"] == "count":
            value += record["match"]
        else:
            value |= record["match"] << expected
    if value > packet_initial.get("memory_max", -1):
        raise ValueError("encoded value exceeds fixed memory bound")
    return value


def validate_registration(spec: dict, manifest: dict) -> None:
    if type(spec) is not dict or spec.get("schema") != "srb.rev05.cpu_pilot.v1":
        raise ValueError("wrong pilot specification")
    if spec.get("source_panel_manifest_sha256") != manifest.get("manifest_sha256"):
        raise ValueError("source panel manifest digest differs from registration")
    registered = spec.get("root_indices")
    if (type(registered) is not list or registered != [0, 5] or
            any(type(i) is not int for i in registered) or
            any(i not in manifest["panels"]["pilot"]["indices"] for i in registered)):
        raise ValueError("pilot roots must be registered [0,5] from frozen pilot")
    if spec.get("modes") != list(MODES) or spec.get("treatments") != list(TREATMENTS):
        raise ValueError("registered model, codec and comparator arms differ")
    if spec.get("source_class") != "public_deterministic_development_pilot":
        raise ValueError("not the registered public development split")
    model = spec.get("model", {})
    for key in ("base", "adapter"):
        identity = model.get(key, {})
        if (type(identity.get("sha256")) is not str or
            len(identity["sha256"]) != 64 or type(identity.get("bytes")) is not int):
            raise ValueError(f"pinned {key} identity missing")
    run = spec.get("runtime", {})
    if (run.get("n_gpu_layers") != 0 or run.get("device") != "none" or
            run.get("flash_attn") != "off"):
        raise ValueError("this registered CI runner is CPU only")
    if (type(run.get("per_stage_timeout_seconds")) not in (float, int) or
            not 0 < run["per_stage_timeout_seconds"] <= 360):
        raise ValueError("missing bounded per-stage timeout")


def _isolation_audit(receipt: dict) -> dict:
    data = receipt.get("adapter_telemetry") or {}
    isolation = data.get("isolation") or {}
    return {
        "inference_receipt_valid": receipt.get("telemetry_status") == "valid",
        "server_reaped_and_port_closed": (
            isolation.get("process_reaped") is True and
            isolation.get("port_closed_verified") is True),
        "server_reset_verified": isolation.get("server_reset_verified") is True,
        "boot_sha256": isolation.get("server_boot_sha256"),
        "input_tokens": data.get("usage", {}).get("input_tokens"),
        "output_tokens": data.get("usage", {}).get("output_tokens"),
    }


def _sanitized_receipt(receipt: dict) -> dict:
    """Remove stderr paths and preserve hashed response plus audit telemetry."""
    value = {k: v for k, v in receipt.items() if k not in (
        "stderr_tail", "stdout_text", "adapter_argv")}
    return value


def _initial_model_output(response: dict, max_memory: int):
    if type(response) is not dict or set(response) != {"memory", "posterior", "action"}:
        raise ValueError("initial model JSON must include exact three fields")
    forecast = parse_forecast({
        "posterior": response["posterior"],
        "memory": response["memory"]}, "initial")
    memory = response["memory"]
    if type(memory) is not int or not 0 <= memory <= max_memory:
        raise ValueError("initial model memory value violates bounded codec")
    action = response["action"]
    if type(action) is not str or action not in ACTIONS:
        raise ValueError("initial model policy action is invalid")
    return forecast, memory, action


def _per_arm_summary(rows: list[dict]) -> dict:
    attempted = len(rows)
    initial_valid = [row for row in rows if row["initial_response_format_valid"]]
    scored = [row for row in rows if row["status"] == "scored"]
    initial_attempts = [row["initial_receipt"] for row in rows]
    receipts = initial_attempts + [
        row["update_receipt"] for row in rows if row["update_receipt"] is not None]
    all_iso = [_isolation_audit(receipt) for receipt in receipts]
    all_valid = [x for x in all_iso if x["inference_receipt_valid"]]
    input_values = [x["input_tokens"] for x in all_valid if type(x["input_tokens"]) is int]
    output_values = [x["output_tokens"] for x in all_valid if type(x["output_tokens"]) is int]
    boot_ids = [x["boot_sha256"] for x in all_iso if x["boot_sha256"]]
    if attempted == 0:
        raise ValueError("pilot arm must have registered roots")
    return {
        "cases": attempted,
        "raw_model_memory_correct": sum(x["raw_model_memory_correct"] is True for x in rows),
        "initial_response_format_valid": len(initial_valid),
        "update_attempts": len(receipts)-attempted,
        "scored": len(scored),
        "coverage": len(scored)/attempted,
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "initial_error_counts": dict(Counter(row["initial_error"] for row in rows
                                             if row["initial_error"])),
        "full_information_regret_with_missing_penalty": sum(
            row["policy_regret_vs_full"] if row["status"]=="scored"
            else MISSING_POLICY_REGRET for row in rows)/attempted,
        "matched_regret_with_missing_penalty": sum(
            row["policy_regret_vs_matched"] if row["status"]=="scored"
            else MISSING_POLICY_REGRET for row in rows)/attempted,
        "posterior_excess_brier_with_missing_penalty": sum(
            row["excess_brier"] if row["status"]=="scored"
            else MISSING_BRIER for row in rows)/attempted,
        "update_own_forecast_coherent": sum(
            row["update_coherent"] is True for row in scored),
        "update_model_action_matches_bayes": sum(
            row["bayes_correct"] is True for row in scored),
        "host_wall_seconds_all_attempts": math.fsum(
            receipt.get("wall_seconds", 0) for receipt in receipts),
        "stage_calls_attempted": len(receipts),
        "inference_receipt_valid_calls": len(all_valid),
        "server_reset_verified_calls": sum(x["server_reset_verified"] for x in all_iso),
        "unique_server_boots": len(set(boot_ids)),
        "all_stage_server_resets_verified": (
            len(boot_ids) == len(receipts) and len(set(boot_ids)) == len(receipts)
            and all(x["server_reaped_and_port_closed"] for x in all_iso)),
        "observed_input_tokens": sum(input_values),
        "observed_output_tokens": sum(output_values),
        "input_token_coverage": len(input_values)/len(receipts),
        "output_token_coverage": len(output_values)/len(receipts),
    }


def run_pilot(spec: dict, manifest: dict, experiment: dict, adapter_argv: list[str],
              executor=execute, monotonic=time.monotonic) -> dict:
    validate_registration(spec, manifest)
    started = monotonic()
    timeout = float(spec["runtime"]["per_stage_timeout_seconds"])
    per_arm_wall = float(spec["runtime"]["max_arm_wall_seconds"])
    groups: dict[str, dict] = {}
    rows = []
    for mode in MODES:
        for treatment in TREATMENTS:
            arm_start = monotonic()
            for index in spec["root_indices"]:
                world = fixture(index)
                family = FAMILIES[index % 3]
                initial = packet(world, mode, family, "initial")
                expected = visible_codec(initial)
                if expected != (world.old_count if mode == "count" else world.old_mask):
                    raise AssertionError("visible codec differs from independently computed fixture")
                if monotonic() - arm_start >= per_arm_wall:
                    first = {"status": "budget_exhausted", "wall_seconds":0,
                             "response":None, "input_tokens":None,
                             "output_tokens":None}
                else:
                    first = executor(adapter_argv, initial, [], timeout, experiment)
                row = {
                    "index": index, "case_id": world.case_id, "family":family,
                    "mode": mode, "treatment":treatment,
                    "initial_packet_sha256":canonical_sha(initial),
                    "expected_visible_memory":expected,
                    "raw_model_memory":None,
                    "raw_model_memory_correct":None,
                    "initial_response_format_valid":False,
                    "initial_forecast":None, "initial_action":None,
                    "initial_receipt":_sanitized_receipt(first),
                    "update_receipt":None, "status":"initial_invalid",
                    "initial_error":None, "update_error":None,
                    "update_packet_sha256":None,
                    "update_memory":None, "update_uses_host_visible_codec":False,
                    "update_old_history_not_replayed":None,
                    "update_prior_responses_empty":None,
                    "update_forecast":None, "update_action":None,
                    "update_coherent":None, "bayes_correct":None,
                    "excess_brier":None, "policy_regret_vs_full":None,
                    "policy_regret_vs_matched":None,
                }
                if first["status"] != "ok":
                    row["initial_error"] = first["status"]
                    rows.append(row)
                    continue
                try:
                    forecast, raw_memory, action = _initial_model_output(
                        first["response"], initial["memory_max"])
                    row["initial_response_format_valid"] = True
                    row["raw_model_memory"] = raw_memory
                    row["raw_model_memory_correct"] = raw_memory == expected
                    row["initial_forecast"] = list(forecast)
                    row["initial_action"] = action
                    row["initial_own_forecast_coherent"] = (
                        action == optimal_action(forecast, family))
                    prior = initial_posterior(world.old_count)
                    row["initial_excess_brier"] = squared(forecast, prior)
                    if treatment == "model_memory" and raw_memory != expected:
                        raise ValueError("raw_model_memory_incorrect")
                    memory_for_update = expected if treatment == "verified_visible_codec" else raw_memory
                    row["update_memory"] = memory_for_update
                    row["update_uses_host_visible_codec"] = treatment == "verified_visible_codec"
                    update = packet(world, mode, family, "update", memory_for_update)
                    row["update_packet_sha256"] = canonical_sha(update)
                    row["update_old_history_not_replayed"] = update["old"] == "not_replayed"
                    row["update_prior_responses_empty"] = update["prior_responses"] == "not_replayed"
                    if monotonic() - arm_start >= per_arm_wall:
                        second = {"status": "budget_exhausted", "wall_seconds":0,
                                  "response":None, "input_tokens":None,
                                  "output_tokens":None}
                    else:
                        second = executor(adapter_argv, update, [], timeout, experiment)
                    row["update_receipt"] = _sanitized_receipt(second)
                    if second["status"] != "ok":
                        row["status"] = "update_" + second["status"]
                        row["update_error"] = second["status"]
                        rows.append(row)
                        continue
                    update_forecast, update_action, _ = parse_response(
                        second["response"], "update")
                    ref = world.exact_count if mode == "count" else world.exact_full
                    row["status"] = "scored"
                    row["update_forecast"] = list(update_forecast)
                    row["update_action"] = update_action
                    row["excess_brier"] = squared(update_forecast, ref)
                    row["policy_regret_vs_full"] = policy_regret(
                        update_action, world.exact_full, family)
                    row["policy_regret_vs_matched"] = policy_regret(
                        update_action, ref, family)
                    row["update_coherent"] = update_action == optimal_action(
                        update_forecast, family)
                    row["bayes_correct"] = update_action == optimal_action(ref, family)
                except (ValueError, TypeError, KeyError) as error:
                    if row["update_receipt"] is None:
                        row["initial_error"] = str(error)
                    else:
                        row["status"] = "update_invalid_response"
                        row["update_error"] = str(error)
                rows.append(row)
            name = mode + "/" + treatment
            chosen = [r for r in rows if r["mode"] == mode and r["treatment"] == treatment]
            groups[name] = _per_arm_summary(chosen)
    seen_initial = len(rows)
    receipts = [receipt for row in rows for receipt in
                (row["initial_receipt"],row["update_receipt"]) if receipt is not None]
    real = any(
        (r.get("adapter_telemetry") or {}).get("identity", {}).get(
            "local_artifacts_verified") is True and
        (r.get("adapter_telemetry") or {}).get("isolation", {}).get(
            "requests_served") in (1, 2) and
        type((r.get("adapter_telemetry") or {}).get("usage", {}).get(
            "output_tokens")) is int and
        (r.get("adapter_telemetry") or {})["usage"]["output_tokens"] > 0
        for r in receipts)
    gates = {
        "exact_visible_codec": "PASS",
        "genuine_model_inference_observed": "PASS" if real else "FAIL",
        "verified_codec_any_completed": "PASS" if sum(
            groups[f"{mode}/verified_visible_codec"]["scored"] for mode in MODES) > 0 else "FAIL",
        "verified_codec_better_than_model_memory": "PASS" if any(
            groups[f"{mode}/verified_visible_codec"]["scored"] >
            groups[f"{mode}/model_memory"]["scored"] for mode in MODES) else "FAIL",
    }
    # All end-to-end stage receipts, including failures, require unique boots
    # for a strong reset claim. Ordinary model correctness is a separate gate.
    gates["all_stage_server_resets_verified"] = (
        "PASS" if all(group["all_stage_server_resets_verified"] for group in groups.values())
        else "FAIL"
    )
    return {
        "schema":SCHEMA, "experiment_id":spec["experiment_id"],
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_class":"public_deterministic_development_pilot",
        "actual_model_inference_observed":real,
        "scientific_confirmation_claim":False, "physical_memory_enforced":False,
        "adapter_process_sandboxed":False, "unconditional_memory_claim":False,
        "model_evaluation_claim":False, "model_inference_observed_is_not_scientific_confirmation":True,
        "intervention":"host_verified_visible_integer_only",
        "prompt_or_posteriors_not_host_corrected":True,
        "source_manifest_sha256":manifest["manifest_sha256"],
        "registration_sha256":canonical_sha(spec),
        "experiment_sha256":canonical_sha(experiment),
        "roots":spec["root_indices"],"logical_bits":{"count":4,"bitmap":12},
        "expected_initial_calls":len(spec["root_indices"])*len(MODES)*len(TREATMENTS),
        "initial_calls":seen_initial, "wall_seconds":monotonic()-started,
        "gate_results":gates, "groups":groups, "rows":rows,
    }


def next_prompt(report: dict) -> str:
    """Write PASS/FAIL promotion instructions from the observed receipts."""
    gates = report["gate_results"]
    groups = report["groups"]
    rows = report["rows"]
    timed_out = sum(
        int(row["initial_receipt"]["status"] == "timeout") +
        int(row["update_receipt"] is not None and
            row["update_receipt"]["status"] == "timeout")
        for row in rows
    )
    calls = sum(g["stage_calls_attempted"] for g in groups.values())
    known = sum(g["inference_receipt_valid_calls"] for g in groups.values())
    raw_valid = sum(g["raw_model_memory_correct"] for g in groups.values())
    scored = sum(g["scored"] for g in groups.values())
    lines = [
        "# SRB-REV-05 next-run prompt: promoted observed CI PASS/FAIL",
        "",
        f"Experiment: \`{report['experiment_id']}\`.",
        f"Frozen registration: \`{report['registration_sha256']}\`.",
        f"Frozen issuer panel: \`{report['source_manifest_sha256']}\`.",
        "",
        "## Observed gate outcomes",
        "",
        "| Prespecified gate | Outcome |",
        "| --- | --- |",
    ]
    lines.extend(f"| {key} | **{status}** |" for key, status in gates.items())
    lines.extend([
        "",
        f"**Observed stage calls:** {calls}, of which {timed_out} timed out "
        f"and {known} supplied validated usage receipts. "
        f"Correct model-origin memory: {raw_valid} of {len(rows)} "
        f"initial attempts. Fully scored: {scored} of {len(rows)}.",
        "",
        "| Mode / treatment | Raw correct | Scored | Timeouts | Observed input/output tokens |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for name, g in groups.items():
        members = [x for x in rows if x["mode"]+"/"+x["treatment"] == name]
        count_timeout = sum(
            (row["initial_receipt"]["status"] == "timeout") +
            bool(row["update_receipt"] is not None and
                 row["update_receipt"]["status"] == "timeout")
            for row in members)
        lines.append(f"| {name} | {g['raw_model_memory_correct']}/{g['cases']} | "
                     f"{g['scored']}/{g['cases']} | {count_timeout} | "
                     f"{g['observed_input_tokens']}/{g['observed_output_tokens']} |")
    lines.extend(["", "## Next execution prompt", ""])
    if gates["genuine_model_inference_observed"] != "PASS":
        lines.append("**INFRASTRUCTURE FAIL:** Verify the pinned CPU model, LoRA, "
                     "release hash, server preflight and strict JSON transport. "
                     "Until a positive-token completion receipt exists, mark all "
                     "model competence as unknown.")
    elif timed_out:
        lines.append(
            f"**CPU STAGE TIMEOUT FAIL ({timed_out}/{calls}):** "
            "The registered 150-second stage ceiling censored the main "
            "model comparison. First implement timeout-safe process-tree "
            "termination and confirm that every timed-out inference server "
            "and its port are reaped. Keep completed responses, failed-call "
            "costs and observed usage in separate categories. "
            "Then rerun a smaller resource-feasible registered CPU subset "
            "with a generous declared timeout, or use the pinned local GPU "
            "for the full paired study. Recompare direct and host-coded "
            "memory only after both reach update-stage scoring.")
        if any(row["raw_model_memory_correct"] for row in rows):
            lines.append(
                "At least one raw model-generated memory integer was already "
                "correct; host verification cannot demonstrate a lift on "
                "a root whose initial memory was correct and whose later "
                "inference timed out.")
    elif gates["verified_codec_any_completed"] != "PASS":
        lines.append("**DECISION-PIPELINE FAIL:** Inference finished within "
                     "the registered stage ceilings, but the assisted arm "
                     "still scored zero. Inspect posterior normalization "
                     "and action-choice consistency before changing memory.")
    elif gates["verified_codec_better_than_model_memory"] != "PASS":
        lines.append("**CODEC-LIFT FAIL:** Under completed paired inference, "
                     "source-visible integer verification did not improve "
                     "coverage. Test fresh issuer roots and compute-matched "
                     "artifacts before drawing broad conclusions.")
    else:
        lines.append("**CODEC-LIFT PASS (development only):** Register a "
                     "larger fresh-root and compute-matched confirmation "
                     "with the same checkpoint. Host-computed state is a "
                     "tool intervention rather than learned BitAgent memory.")
    if gates["all_stage_server_resets_verified"] != "PASS":
        lines.append(
            "**RESET-AUDIT FAIL:** Preserve successful per-stage reaping "
            "evidence separately from timed-out calls without receipts. "
            "Investigate any orphaned llama-server processes and certify "
            "full process-group cleanup before making a server isolation claim.")
    lines.extend([
        "",
        "Maintain the frozen source-law cases and original hashes. "
        "Measure per-stage first-token and completion latency, retain all "
        "failed calls in denominators, and preserve the model's raw "
        "posterior, action and uncorrected memory alongside any host "
        "intervention. Public deterministic issuer roots do not provide "
        "independent scientific confirmation. Financial actions are "
        "synthetic, read-only, and physically unsandboxed at the adapter.",
        "",
    ])
    return "\n".join(lines)
