"""Run a pinned local model against exported baseline packets, sequentially."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
from adapters.llamacpp import LlamaCppAdapter, check_gpu_window
from adapters.storage import save_json as save
from systemic_risk_bench.cli import digest
from systemic_risk_bench.scoring import read_json, score_numeric
from systemic_risk_bench.webhooks import ResultWebhook


def summary(receipts, tasks):
    numeric = [{"id": r["case_id"], "estimates": r["response"].get("estimates", {})}
               for r in receipts if r["track"] == "quant" and r["status"] == "ok"]
    numeric_report = score_numeric(numeric) if any(t["track"] == "quant" for t in tasks) else None
    if numeric_report:
        numeric_report.pop("model_evaluation_claim", None)
    usage = [r["usage"] for r in receipts if r.get("usage")]
    return {"completed_calls": len(receipts), "expected_calls": len(tasks),
            "successful_calls": sum(r["status"] == "ok" for r in receipts),
            "failed_calls": sum(r["status"] != "ok" for r in receipts),
            "numeric": numeric_report, "reasoning_score": None,
            "reasoning_status": "requires_independent_audit",
            "token_usage": {key: sum(u[key] for u in usage) if usage and all(u.get(key) is not None for u in usage) else None
                            for key in ("input_tokens", "output_tokens", "total_tokens", "reasoning_tokens")},
            "median_wall_seconds": statistics.median(r["wall_seconds"] for r in receipts) if receipts else None}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--baseline-plans", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--track", choices=("quant", "history", "all"), default="all")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--max-calls", type=int, help="bounded smoke; use a distinct output directory")
    args = parser.parse_args(argv)
    config = read_json(args.config)
    tasks, baseline_digests = [], []
    for filename in args.baseline_plans:
        plan = read_json(filename)
        baseline_digests.append(digest(plan))
        tasks += [t for t in plan["tasks"] if args.track == "all" or t["track"] == args.track]
    identities = [(t["track"], t["case_id"], t["stage_index"]) for t in tasks]
    if not tasks or len(set(identities)) != len(identities):
        raise ValueError("baseline plans must supply distinct selected tasks")
    if args.max_calls is not None:
        if args.max_calls < 1:
            raise ValueError("max-calls must be positive")
        tasks = tasks[:args.max_calls]
    directory = Path(args.output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    frozen = {"schema_version": "srb.local_campaign.v0.1", "config": config,
              "baseline_plan_sha256": baseline_digests, "tasks": tasks,
              "source_sha256": {str(p.relative_to(APP)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [APP/"adapters/llamacpp.py", APP/"adapters/artifacts.py", APP/"adapters/storage.py", Path(__file__).resolve()]},
              "taskset_sha256": digest(tasks), "compute_matched_claim": False}
    path = directory/"frozen-plan.json"
    if path.exists() and read_json(path) != frozen:
        raise ValueError("local campaign plan changed; use a new directory")
    save(path, frozen)
    if args.prepare_only:
        save(directory/"status.json", {"state": "prepared_not_started", "expected_calls": len(tasks),
             "gpu_not_before_utc": config["gpu_not_before_utc"], "model_calls": 0})
        print(f"Prepared {len(tasks)} exact baseline packets; no model/GPU calls.")
        return
    check_gpu_window(config)
    adapter = LlamaCppAdapter(config)
    identity = adapter.preflight()
    save(directory/"runtime-identity.json", identity)
    save(directory/"status.json", {"state": "running", "expected_calls": len(tasks)})
    receipts, prior = [], {}
    with ResultWebhook(directory/"webhook-events") as webhook:
        for index, task in enumerate(tasks):
            target = directory/"receipts"/f"{index:03d}.json"
            packet_hash = digest(task["packet"])
            if target.exists():
                receipt = read_json(target)
                if receipt["packet_sha256"] != packet_hash:
                    raise ValueError("saved local receipt does not match frozen packet")
            else:
                started = time.perf_counter()
                try:
                    receipt = adapter.infer(task["packet"], prior.get(task["case_id"], []), task["track"])
                except (ValueError, OSError, TimeoutError, KeyError) as error:
                    receipt = {"status": "adapter_error", "response": None, "error": str(error),
                               "usage": None, "wall_seconds": time.perf_counter()-started}
                receipt.update(task_index=index, case_id=task["case_id"], stage_index=task["stage_index"],
                               track=task["track"], packet_sha256=packet_hash,
                               completed_at=datetime.now(timezone.utc).isoformat())
                save(target, receipt)
            receipts.append(receipt)
            prior.setdefault(task["case_id"], []).append({"stage_index": task["stage_index"],
                         "response": receipt["response"], "status": receipt["status"]})
            webhook.emit({"event_id": digest({"run": digest(frozen), "task_index": index}),
                          "event": "rollout.completed", "model": config["model_alias"],
                          "task_index": index, "status": receipt["status"]})
            save(directory/"summary.json", summary(receipts, tasks))
            print(f"{index+1}/{len(tasks)} {task['case_id']}/s{task['stage_index']} {receipt['status']}", flush=True)
            if len(receipts) >= 3 and all(r["status"] != "ok" for r in receipts[-3:]):
                save(directory/"status.json", {"state": "halted_after_three_errors", "completed_calls": len(receipts)})
                raise RuntimeError("three consecutive local inference failures; inspect receipts")
    save(directory/"status.json", {"state": "complete", "completed_calls": len(receipts),
         "webhook_receipts": len(list((directory/"webhook-events").glob("*.json")))})


if __name__ == "__main__":
    main()
