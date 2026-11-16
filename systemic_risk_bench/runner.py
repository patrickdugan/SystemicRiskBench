"""JSON-over-stdin runner. Adapter processes are operator trusted, not sandboxed."""

from datetime import datetime, timezone
import hashlib
import json
import subprocess
import time

from .scoring import loads_json, score_numeric
from .suite import quantitative_tasks


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def execute(adapter_argv, packet, prior_responses, timeout, experiment=None):
    if not isinstance(adapter_argv, list) or not adapter_argv or any(
        not isinstance(arg, str) or not arg for arg in adapter_argv
    ):
        raise ValueError("adapter argv must be a nonempty JSON array of strings")
    request = {"protocol": "srb.adapter.v0.1", "packet": packet,
               "experiment": experiment,
               "prior_responses": prior_responses,
               "instruction": "Return one JSON object on stdout. Give a concise decision "
               "rationale, assumptions, estimates, self/architecture critique and revision "
               "triggers. Cite supplied evidence IDs and identify missing inputs."}
    started = time.perf_counter()
    try:
        result = subprocess.run(adapter_argv, input=json.dumps(request), capture_output=True,
                                text=True, encoding="utf-8", timeout=timeout, shell=False)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "wall_seconds": time.perf_counter()-started,
                "response": None, "input_tokens": None, "output_tokens": None}
    receipt = {"status": "ok" if result.returncode == 0 else "adapter_error",
               "exit_code": result.returncode, "wall_seconds": time.perf_counter()-started,
               "input_tokens": None, "output_tokens": None,
               "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
               "stderr_tail": result.stderr[-2000:], "response": None}
    if result.returncode == 0:
        try:
            response = loads_json(result.stdout)
            if not isinstance(response, dict):
                raise ValueError("adapter response must be an object")
            receipt["response"] = response
        except (ValueError, TypeError) as error:
            receipt.update(status="invalid_json", error=str(error))
    return receipt


def run(adapter_argv, experiment, *, cases=None, masked=False, timeout=60):
    from .history import public_packet
    if not isinstance(experiment, dict) or not isinstance(experiment.get("experiment_id"), str):
        raise ValueError("experiment config requires experiment_id")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 3600:
        raise ValueError("timeout must be in (0,3600]")
    receipts = []
    if cases is None:
        tasks = [(t["id"], 0, t) for t in quantitative_tasks()]
    else:
        tasks = [(c["id"], stage, public_packet(c, stage, masked=masked))
                 for c in cases for stage in range(len(c["stages"]))]
    prior = {}
    for case_id, stage, packet in tasks:
        receipt = execute(adapter_argv, packet, prior.get(case_id, []), timeout, experiment)
        receipt.update(case_id=case_id, stage_index=stage, packet_sha256=sha(packet))
        receipts.append(receipt)
        prior.setdefault(case_id, []).append({"stage_index": stage,
                                               "response": receipt["response"],
                                               "status": receipt["status"]})
    numeric_report = None
    if cases is None:
        numerical = [{"id": r["case_id"], "estimates": r["response"].get("estimates", {})}
                     for r in receipts if r["status"] == "ok"]
        try:
            numeric_report = score_numeric(numerical)
            numeric_report["adapter_responses_scored"] = True
        except ValueError as error:
            numeric_report = {"status": "invalid_response_contract", "error": str(error)}
    return {"schema_version": "srb.run.v0.1", "created_at": datetime.now(timezone.utc).isoformat(),
            "experiment": experiment, "experiment_sha256": sha(experiment),
            "track": "history_reconstruction" if cases is not None else "synthetic_numerical",
            "masked": masked, "adapter_argv": adapter_argv, "timeout_seconds_per_call": timeout,
            "adapter_process_is_not_sandboxed_by_this_harness": True,
            "host_measured_wall_seconds": sum(r["wall_seconds"] for r in receipts),
            "all_other_resources": "unknown unless independently measured and attached",
            "numeric_report": numeric_report, "receipts": receipts,
            "reasoning_score": None, "reasoning_audit_status": "pending"}
