"""Resumable, matched-packet baseline rollouts through signed-in Codex."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import threading
import time

from .cli import digest, historical
from .codex_transport import CodexTransport
from .history import public_packet
from .scoring import read_json, score_numeric
from .suite import quantitative_tasks
from .webhooks import ResultWebhook


def schema_object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def output_schema(packet, track):
    if track == "quant":
        return schema_object({
            "estimates": schema_object({key: {"type": ["number", "null"]}
                                        for key in packet["answer_fields"]}),
            "rationale": {"type": "string"}, "limitations": {"type": "array", "items": {"type": "string"}}})
    text = {"type": "string"}
    texts = {"type": "array", "items": text}
    return schema_object({
        "policy": schema_object({"action": {"type": "string", "enum": ["hold", "reduce", "exit", "hedge", "defer"]},
                                 "conditions": text}),
        "rationale": texts, "risk_estimates": {"type": "array", "items": schema_object({
            "metric": text, "value": {"type": ["number", "null"]}, "units": text,
            "horizon": text, "assumptions": text})},
        "self_critique": text, "architecture_critique": text,
        "population_analysis": schema_object({"fixed_total_capital": text, "fixed_capital_per_agent": text,
                                               "feedback_and_mitigation": text}),
        "revision": schema_object({"action": {"type": "string", "enum": ["initial", "maintain", "revise"]},
                                   "reason": text, "evidence_ids": texts}),
        "missing_inputs": texts, "limitations": texts})


def tasks_for(track, selected_cases=None):
    if track == "quant":
        return [{"case_id": p["id"], "stage_index": 0, "packet": p, "track": track}
                for p in quantitative_tasks()]
    cases = historical()
    if selected_cases:
        known = {c["id"] for c in cases}
        if set(selected_cases) - known:
            raise ValueError("unknown selected case")
        cases = [c for c in cases if c["id"] in selected_cases]
    return [{"case_id": c["id"], "stage_index": stage,
             "packet": public_packet(c, stage, masked=True), "track": track}
            for c in cases for stage in range(len(c["stages"]))]


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def token_totals(receipts):
    keys = ("inputTokens", "cachedInputTokens", "outputTokens", "reasoningOutputTokens", "totalTokens")
    measurements = [r.get("usage", {}).get("last") for r in receipts if r.get("usage")]
    return {key: sum(m.get(key, 0) for m in measurements) if measurements else None for key in keys}


def summarize(receipts, expected_tasks):
    ordered = sorted(receipts, key=lambda r: r["task_index"])
    quant = [{"id": r["case_id"], "estimates": r["response"].get("estimates", {})}
             for r in ordered if r["track"] == "quant" and r["status"] == "ok"]
    numeric = score_numeric(quant) if any(t["track"] == "quant" for t in expected_tasks) else None
    return {"completed_calls": len(ordered), "expected_calls": len(expected_tasks),
            "successful_calls": sum(r["status"] == "ok" for r in ordered),
            "failed_calls": sum(r["status"] != "ok" for r in ordered), "numeric": numeric,
            "token_usage": token_totals(ordered),
            "median_wall_seconds": statistics.median(r["wall_seconds"] for r in ordered) if ordered else None,
            "total_wall_seconds": sum(r["wall_seconds"] for r in ordered),
            "reasoning_score": None, "reasoning_status": "awaiting_two_blind_human_reviews"}


def run_cell(cell, tasks, destination, webhook, timeout, print_lock):
    cell_id = cell["model"] + "--" + cell["effort"]
    cell_dir = destination / "cells" / cell_id
    receipts = []
    prior = {}
    transport = None
    try:
        for index, task in enumerate(tasks):
            case_id, stage = task["case_id"], task["stage_index"]
            packet_hash = digest(task["packet"])
            path = cell_dir / "receipts" / f"{index:03d}.json"
            if path.exists():
                receipt = read_json(path)
                if (receipt["packet_sha256"] != packet_hash or receipt["requested_model"] != cell["model"]
                        or receipt["reasoning_effort"] != cell["effort"]):
                    raise ValueError("resume receipt does not match frozen task/model")
            else:
                attempt_started = time.perf_counter()
                try:
                    if transport is None:
                        transport = CodexTransport(destination / "inference-workspaces" / cell_id, timeout)
                    receipt = transport.infer(task["packet"], prior.get(case_id, []),
                                              cell["model"], cell["effort"], output_schema(task["packet"], task["track"]))
                except (RuntimeError, TimeoutError, OSError, ValueError) as error:
                    receipt = {"status": "transport_error", "response": None, "error": str(error),
                               "wall_seconds": time.perf_counter()-attempt_started,
                               "usage": None, "requested_model": cell["model"],
                               "reasoning_effort": cell["effort"], "resolved_model": None}
                    if transport:
                        transport.close()
                        transport = None
                receipt.update(task_index=index, case_id=case_id, stage_index=stage, track=task["track"],
                               packet_sha256=packet_hash, response_sha256=digest(receipt.get("response")),
                               completed_at=datetime.now(timezone.utc).isoformat())
                save(path, receipt)
            receipts.append(receipt)
            prior.setdefault(case_id, []).append({"stage_index": stage, "response": receipt["response"],
                                                   "status": receipt["status"]})
            event = {"event_id": digest({"cell": cell_id, "task": index, "packet": packet_hash}),
                     "event": "rollout.completed", "cell_id": cell_id, "task_index": index,
                     "status": receipt["status"], "receipt": str(path.relative_to(destination))}
            webhook.emit(event)
            save(cell_dir / "summary.json", summarize(receipts, tasks))
            with print_lock:
                print(f"{cell_id}: {index+1}/{len(tasks)} {case_id}/s{stage} {receipt['status']}", flush=True)
            if len(receipts) >= 3 and all(r["status"] == "transport_error" for r in receipts[-3:]):
                raise RuntimeError("three consecutive transport errors; cell halted")
    finally:
        if transport:
            transport.close()
    return {"cell_id": cell_id, **summarize(receipts, tasks)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Signed-in baseline campaign with result webhooks")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--track", choices=("quant", "history", "all"), default="all")
    parser.add_argument("--cases", help="comma-separated ids for a bounded pilot")
    args = parser.parse_args(argv)
    config = read_json(args.config)
    if config.get("replicates", 1) != 1:
        raise ValueError("Use a separately named output directory for each replicate")
    if type(config.get("workers", 4)) is not int or not 1 <= config.get("workers", 4) <= 16:
        raise ValueError("workers must be an integer in [1,16]")
    destination = Path(args.output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    tasks = []
    if args.track in ("quant", "all"):
        tasks += tasks_for("quant")
    if args.track in ("history", "all"):
        tasks += tasks_for("history", args.cases.split(",") if args.cases else None)
    frozen = {"schema_version": "srb.campaign.v0.2", "config": config, "track": args.track,
              "tasks": tasks, "taskset_sha256": digest(tasks),
              "response_schemas": {t["case_id"]: output_schema(t["packet"], t["track"]) for t in tasks},
              "inference_context": "Codex runtime; ephemeral per call with explicit prior responses",
              "protected_holdout_claim": False, "sampling_seed_control": "not_exposed_by_transport"}
    plan_path = destination / "frozen-plan.json"
    if plan_path.exists() and read_json(plan_path) != frozen:
        raise ValueError("campaign plan changed; use a new output directory")
    save(plan_path, frozen)
    package = Path(__file__).resolve().parent
    provenance = {"source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(package.glob("*.py"))},
                  "base_instructions_sha256": hashlib.sha256(
                      __import__("systemic_risk_bench.codex_transport", fromlist=["BASE_INSTRUCTIONS"])
                      .BASE_INSTRUCTIONS.encode()).hexdigest(),
                  "backend": "signed_in_Codex_app_server",
                  "started_at": datetime.now(timezone.utc).isoformat()}
    provenance_path = destination / "provenance.json"
    if provenance_path.exists():
        original = read_json(provenance_path)
        if original["source_sha256"] != provenance["source_sha256"]:
            raise ValueError("source changed since campaign start; use a new output directory")
    else:
        save(provenance_path, provenance)
    with CodexTransport(destination / "catalog-workspace", config.get("timeout_seconds", 180)) as probe:
        catalog = probe.catalog()
    save(destination / "model-catalog.json", catalog)
    available = {model["model"]: model for model in catalog}
    cells = []
    for model in config["models"]:
        supported = {x["reasoningEffort"] for x in available.get(model, {}).get("supportedReasoningEfforts", [])}
        for effort in config["efforts"]:
            if effort not in supported:
                raise ValueError(f"unavailable model/effort: {model}/{effort}")
            cells.append({"model": model, "effort": effort})
    print(f"Starting {len(cells)} cells x {len(tasks)} tasks = {len(cells)*len(tasks)} rollouts", flush=True)
    results, failures = [], []
    print_lock = threading.Lock()
    save(destination / "status.json", {"state": "running", "expected_cells": len(cells),
         "expected_rollouts": len(cells)*len(tasks), "started_at": provenance["started_at"]})
    with ResultWebhook(destination / "webhook-events") as webhook:
        with ThreadPoolExecutor(max_workers=config.get("workers", 4)) as executor:
            jobs = {executor.submit(run_cell, cell, tasks, destination, webhook,
                                    config.get("timeout_seconds", 180), print_lock): cell for cell in cells}
            for job in as_completed(jobs):
                try:
                    results.append(job.result())
                except Exception as error:
                    failures.append({"cell": jobs[job], "error": str(error)})
                save(destination / "campaign-summary.json", {"cells": results, "failures": failures,
                     "expected_cells": len(cells), "webhooks_received": webhook.received,
                     "frozen_plan_sha256": digest(frozen), "reasoning_scores": "pending_human_audit"})
    save(destination / "status.json", {"state": "complete" if not failures else "finished_with_errors",
         "completed_cells": len(results), "failed_cells": len(failures),
         "completed_at": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"completed_cells": len(results), "failed_cells": failures}, indent=2), flush=True)


if __name__ == "__main__":
    main()
