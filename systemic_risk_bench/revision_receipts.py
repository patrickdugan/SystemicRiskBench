"""Bound, allowlisted telemetry for the local revision adapter.

The JSON response remains the only channel available to the next benchmark
stage. Telemetry is host-side, adapter-reported evidence; a valid receipt does
not attest a sandbox, a server reset, or the running server's model bytes.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

from .scoring import loads_json

PREFIX = "SRB_REVISION_RECEIPT_V1 "
SCHEMA = "srb.revision_inference_receipt.v1"
PACKET_SCHEMAS = {"srb.agent_revision.v1", "srb.finance_revision.v1"}
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = {
    "schema", "packet_sha256", "response_sha256", "phase", "status",
    "elapsed_seconds", "requested_model", "resolved_model", "usage",
    "sampling", "identity", "isolation", "error_code",
}


def canonical_sha(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest()


def _object(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"{label} fields do not match the receipt contract")


def _number(value, label, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{label} must be finite and at least {minimum}")


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer at least {minimum}")


def _digest(value, label):
    if type(value) is not str or not _DIGEST.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def validate_usage(usage):
    """Preserve unknown counters and reject invented or malformed counters."""
    _object(usage, {"input_tokens", "output_tokens", "total_tokens"}, "usage")
    for key, value in usage.items():
        if value is not None:
            _integer(value, key)
    if all(value is not None for value in usage.values()):
        if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
            raise ValueError("total token counter disagrees with its components")
    if usage["total_tokens"] is not None:
        known = sum(usage[key] or 0 for key in ("input_tokens", "output_tokens"))
        if usage["total_tokens"] < known:
            raise ValueError("total token counter is below the known component sum")
    return usage


def parse_receipt(stderr, packet, response, host_status):
    """Return (telemetry, status, error) after binding one complete stderr line.

    The caller must supply the complete stderr stream, before truncating its
    human-readable suffix. Duplicate receipts are invalid even if identical.
    """
    lines = [line[len(PREFIX):] for line in stderr.splitlines()
             if line.startswith(PREFIX)]
    if not lines:
        return None, "missing", None
    try:
        if len(lines) != 1:
            raise ValueError("exactly one revision receipt is required")
        value = loads_json(lines[0])
        _object(value, _FIELDS, "receipt")
        if value["schema"] != SCHEMA:
            raise ValueError("unsupported revision receipt schema")
        if packet.get("schema") not in PACKET_SCHEMAS:
            raise ValueError("telemetry requires a registered revision packet")
        if value["packet_sha256"] != canonical_sha(packet):
            raise ValueError("receipt packet digest does not match this invocation")
        if value["phase"] != packet.get("phase"):
            raise ValueError("receipt phase does not match this invocation")
        if value["status"] not in {
                "ok", "invalid_response", "transport_error", "budget_exceeded"}:
            raise ValueError("unknown adapter receipt status")
        if value["status"] == "ok":
            if host_status != "ok" or response is None:
                raise ValueError("successful telemetry requires a valid host response")
            if value["response_sha256"] != canonical_sha(response):
                raise ValueError("receipt response digest does not match stdout")
            if value["error_code"] is not None:
                raise ValueError("successful receipt cannot contain an error code")
        else:
            if host_status == "ok" or response is not None:
                raise ValueError("failed telemetry cannot accompany a successful response")
            if value["response_sha256"] is not None:
                raise ValueError("failed telemetry must omit the response digest")
            expected_error = {"invalid_response": "response_contract",
                              "transport_error": "http_or_decode",
                              "budget_exceeded": "token_budget"}[value["status"]]
            if value["error_code"] != expected_error:
                raise ValueError("adapter error code differs from the failure status")
        _number(value["elapsed_seconds"], "elapsed_seconds")
        if type(value["requested_model"]) is not str or not value["requested_model"]:
            raise ValueError("requested model is required")
        if value["resolved_model"] is not None and (
                type(value["resolved_model"]) is not str or not value["resolved_model"]):
            raise ValueError("resolved model must be a nonempty string or null")
        validate_usage(value["usage"])
        sampling = value["sampling"]
        _object(sampling, {"temperature", "seed", "max_tokens"}, "sampling")
        _number(sampling["temperature"], "temperature")
        _integer(sampling["seed"], "seed")
        _integer(sampling["max_tokens"], "max_tokens", 1)
        if (value["status"] == "ok" and value["usage"]["output_tokens"] is not None and
                value["usage"]["output_tokens"] > sampling["max_tokens"]):
            raise ValueError("successful receipt exceeds its output token budget")
        identity = value["identity"]
        _object(identity, {"base_sha256", "adapter_sha256", "adapter_id",
                           "adapter_scale", "local_artifacts_verified",
                           "verification"}, "identity")
        for key in ("base_sha256", "adapter_sha256"):
            _digest(identity[key], key)
        _integer(identity["adapter_id"], "adapter_id")
        _number(identity["adapter_scale"], "adapter_scale")
        if type(identity["local_artifacts_verified"]) is not bool:
            raise ValueError("local artifact verification must be a boolean")
        isolation = value["isolation"]
        if type(isolation) is not dict or type(isolation.get("server_reset_verified")) is not bool:
            raise ValueError("isolation server_reset_verified must be a boolean")
        if isolation.get("physical_memory_enforced") is not False:
            raise ValueError("unsandboxed host adapter cannot attest physical_memory_enforced")
        if isolation["server_reset_verified"] is False:
            if identity["verification"] != "local_files_plus_server_alias_and_adapter_metadata":
                raise ValueError("unsupported model identity verification claim")
            _object(isolation, {"server_reset_verified", "physical_memory_enforced"},
                    "isolation")
        else:
            if identity["local_artifacts_verified"] is not True:
                raise ValueError("server_reset_verified requires verified local artifacts")
            if identity["verification"] != "ephemeral_per_stage_server_plus_local_file_and_adapter_hashes":
                raise ValueError("server_reset_verified requires ephemeral per-stage verification")
            _object(isolation, {
                "server_reset_verified", "physical_memory_enforced",
                "server_boot_sha256", "requests_served", "process_reaped",
                "port_closed_verified", "startup_seconds", "shutdown_seconds",
            }, "isolation")
            _digest(isolation["server_boot_sha256"], "server_boot_sha256")
            if type(isolation["requests_served"]) is not int or isolation["requests_served"] not in (0, 1):
                raise ValueError("ephemeral stage server may serve at most one request")
            if value["status"] == "ok" and isolation["requests_served"] != 1:
                raise ValueError("successful ephemeral receipt must record exactly one request")
            if isolation["process_reaped"] is not True or isolation["port_closed_verified"] is not True:
                raise ValueError("server_reset_verified requires reaped process and closed port")
            _number(isolation["startup_seconds"], "startup_seconds")
            _number(isolation["shutdown_seconds"], "shutdown_seconds")
        return value, "valid", None
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        return None, "invalid", str(error)


def validate_registered_experiment(config, experiment, packet, *, require_model=False):
    """Bind explicit model registrations to the actual per-call runtime config.

    Legacy source fixtures have no model registration and retain their existing
    behavior. The evaluator owns campaign call-count enforcement; this function
    validates the declared envelope and checks the active packet's memory arm.
    """
    if experiment is None:
        if require_model:
            raise ValueError("local model inference requires explicit model registration")
        return
    if type(experiment) is not dict:
        raise ValueError("experiment must be an object")
    model = (experiment.get("evaluation_kind") == "model" or
             experiment.get("evaluation") == "model" or
             experiment.get("model_evaluation") is True)
    if not model:
        if require_model:
            raise ValueError("local model inference requires explicit model registration")
        return
    if not experiment.get("experiment_id") or "template" in str(
            experiment.get("status", "")).lower():
        raise ValueError("model experiment must be registered before inference")
    pairs = {
        "base_sha256": config["base"]["sha256"],
        "checkpoint_sha256": config["adapter"]["sha256"],
        "model_alias": config["model_alias"],
        "max_output_tokens_per_call": config.get("max_tokens", 1024),
        "temperature": config.get("temperature", 0),
        "seed": config.get("seed", 0),
    }
    _integer(pairs["max_output_tokens_per_call"], "runtime max_tokens", 1)
    _number(pairs["temperature"], "runtime temperature")
    _integer(pairs["seed"], "runtime seed")
    for field, actual in pairs.items():
        if field not in experiment or experiment[field] != actual:
            raise ValueError(f"registered {field} differs from the runtime config")
    for field in ("base_sha256", "checkpoint_sha256"):
        _digest(experiment[field], field)
    _integer(experiment["max_output_tokens_per_call"], "max_output_tokens_per_call", 1)
    _number(experiment["temperature"], "temperature")
    _integer(experiment["seed"], "seed")
    _integer(experiment.get("preregistered_cases"), "preregistered_cases", 1)
    _integer(experiment.get("max_calls_per_arm"), "max_calls_per_arm", 1)
    if experiment["max_calls_per_arm"] < 2 * experiment["preregistered_cases"]:
        raise ValueError("registered call budget cannot cover both stages")
    if "max_input_tokens_per_call" in experiment:
        _integer(experiment["max_input_tokens_per_call"], "max_input_tokens_per_call", 1)
    if experiment.get("memory_arms") != ["count", "bitmap"]:
        raise ValueError("model experiment must register the paired memory arms")
    if packet.get("memory_codec") not in experiment["memory_arms"]:
        raise ValueError("packet memory codec is outside the registered experiment")
    server_kind = experiment.get("inference_server")
    lifecycle = config.get("server_lifecycle", "persistent")
    if server_kind == "operator_owned_loopback_llama_cpp":
        if experiment.get("server_reset_between_stages", False) is not False:
            raise ValueError("persistent loopback server cannot claim server_reset_between_stages")
        if lifecycle != "persistent":
            raise ValueError("runtime server_lifecycle differs from registered inference_server")
    elif server_kind == "ephemeral_per_stage_llama_cpp":
        if experiment.get("server_reset_between_stages") is not True:
            raise ValueError("ephemeral per-stage server must register server_reset_between_stages=true")
        if lifecycle != "ephemeral_per_stage":
            raise ValueError("runtime server_lifecycle must be ephemeral_per_stage")
        _digest(experiment.get("server_sha256"), "server_sha256")
        if config.get("server_sha256") != experiment["server_sha256"]:
            raise ValueError("registered server_sha256 differs from the runtime config")
    else:
        raise ValueError("model experiment must register the local inference server")
