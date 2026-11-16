"""Read live campaign progress without starting models or contacting the provider."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
args = parser.parse_args()
root = args.directory.resolve()
plan = json.loads((root / "frozen-plan.json").read_text(encoding="utf-8"))
rows = []
for summary_path in sorted(root.glob("cells/*/summary.json")):
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows.append({"cell": summary_path.parent.name, "completed": summary["completed_calls"],
                 "expected": summary["expected_calls"], "failed": summary["failed_calls"],
                 "tokens": summary["token_usage"]["totalTokens"]})
config = plan["config"]
expected_cells = len(config["models"]) * len(config["efforts"])
print(json.dumps({"campaign": config["campaign_id"], "expected_cells": expected_cells,
                  "cells_started": len(rows), "cells_complete": sum(r["completed"] == r["expected"] for r in rows),
                  "rollouts_complete": sum(r["completed"] for r in rows),
                  "rollouts_expected": expected_cells * len(plan["tasks"]),
                  "failed_calls": sum(r["failed"] for r in rows),
                  "webhook_receipts": len(list((root/"webhook-events").glob("*.json"))),
                  "rows": rows}, indent=2))
