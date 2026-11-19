"""Always publish an SRB-REV-05 PASS/FAIL prompt even after CI setup failure."""
import json
import os
from pathlib import Path

root=Path("artifacts/rev05-ci")
root.mkdir(parents=True,exist_ok=True)
data=root/"observations.json"
prompt=root/"NEXT_PROMPT.md"
if not data.is_file():
    data.write_text(json.dumps({
        "schema":"srb.rev05.cpu_pilot.infrastructure_failure.v1",
        "status":"INFRASTRUCTURE_FAIL",
        "actual_model_inference_observed":False,
        "scientific_confirmation_claim":False,
    },indent=2)+"\n")
if not prompt.is_file():
    prompt.write_text(
        "# SRB-REV-05 next-run prompt\n\n"
        "**INFRASTRUCTURE FAIL.** Model setup/download/boot/transport "
        "did not reach the scored pilot. Examine the failing CI step and "
        "repeat the pinned public two-root registration after repair. "
        "Treat every missing call as infrastructure missingness and "
        "preserve the existing source-law and model SHA-256 contracts.\n")
summary=os.getenv("GITHUB_STEP_SUMMARY")
if summary:
    with open(summary,"a",encoding="utf-8") as f:
        f.write(prompt.read_text(encoding="utf-8"))
        f.write("\nThis is an unsandboxed public development evaluation. "
                "PASS/FAIL gates for model behavior are separate from CI infrastructure.\n")
print("PILOT_RESULT_SUMMARY "+json.dumps(json.loads(data.read_text()).get("gate_results",
    {"infrastructure":"FAIL"})))
print("PROMPT_LOCATION "+str(prompt))
