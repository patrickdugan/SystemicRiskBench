"""Run registered SRB-REV-05 CPU pilot and write evidence-based next prompt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import traceback

from systemic_risk_bench.rev05_ci_pilot import (
    next_prompt, run_pilot, validate_registration,
)
from systemic_risk_bench.scoring import read_json


def main() -> int:
    ap=argparse.ArgumentParser()
    for key in ("spec","manifest","experiment","runtime","output","prompt"):
        ap.add_argument("--"+key,required=True)
    args=ap.parse_args()
    output=Path(args.output)
    prompt=Path(args.prompt)
    output.parent.mkdir(parents=True,exist_ok=True)
    prompt.parent.mkdir(parents=True,exist_ok=True)
    try:
        spec=read_json(args.spec)
        manifest=read_json(args.manifest)
        validate_registration(spec,manifest)
        experiment=read_json(args.experiment)
        runtime=read_json(args.runtime)
        if (experiment["experiment_id"]!=spec["experiment_id"] or
                experiment["server_sha256"]!=runtime["server_sha256"] or
                experiment["base_sha256"]!=spec["model"]["base"]["sha256"] or
                experiment["checkpoint_sha256"]!=spec["model"]["adapter"]["sha256"]):
            raise ValueError("runtime identity/registration mismatch")
        cmd=[sys.executable,"-m","adapters.revision_llamacpp","--config",str(Path(args.runtime).resolve())]
        result=run_pilot(spec,manifest,experiment,cmd)
        output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
        text=next_prompt(result)
        prompt.write_text(text,encoding="utf-8")
        print("SRB-REV-05 real CPU experiment completed:")
        for key,value in result["gate_results"].items():
            print(f"GATE {key}: {value}")
        for name,record in result["groups"].items():
            print(f"ARM {name} scored={record['scored']}/{record['cases']} "
                  f"raw_memory_correct={record['raw_model_memory_correct']}/{record['cases']} "
                  f"initial_format_valid={record['initial_response_format_valid']}/{record['cases']} "
                  f"tokens={record['observed_input_tokens']}+{record['observed_output_tokens']} "
                  f"wall_s={record['host_wall_seconds_all_attempts']:.2f} "
                  f"status={record['status_counts']}")
        print(f"OBSERVED_PROMPT_FILE {prompt}")
        print("BEGIN_NEXT_PROMPT")
        print(text)
        print("END_NEXT_PROMPT")
        return 0
    except Exception as exc:
        summary={
            "schema":"srb.rev05.cpu_pilot.infrastructure_failure.v1",
            "status":"INFRASTRUCTURE_FAIL",
            "error_type":type(exc).__name__,
            "error_message":str(exc)[:600],
            "model_inference_observed":False,
            "scientific_confirmation_claim":False,
        }
        output.write_text(json.dumps(summary,indent=2)+"\n")
        next_action=(
            "# SRB-REV-05 next experiment prompt\n\n"
            "**INFRASTRUCTURE FAIL.** Review the pinned llama.cpp CPU runtime, "
            "model/LoRA artifact hashes, Python evaluator exceptions and "
            "stage receipts. Attempt the same two-root registered panel "
            "again after a documented transport fix. Treat any missing "
            "model calls as missing rather than model failure.\n\n"
            f"Error category: \`{type(exc).__name__}\`.\n"
        )
        prompt.write_text(next_action,encoding="utf-8")
        print(json.dumps(summary))
        traceback.print_exc(file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
