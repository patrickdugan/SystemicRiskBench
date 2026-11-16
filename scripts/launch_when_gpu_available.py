"""Wait for the user reservation and an idle GPU, then launch owned inference."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
from adapters.llamacpp import LlamaCppAdapter, check_gpu_window
from adapters.storage import save_status as save
from systemic_risk_bench.scoring import read_json


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--baseline-plans", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--runtime-dir", required=True)
    args = parser.parse_args(argv)
    config_path = Path(args.config).resolve()
    config = read_json(config_path)
    directory = Path(args.output_dir).resolve()
    runtime = Path(args.runtime_dir).resolve()
    wait_status = directory/"gpu-wait-status.json"
    cutoff = datetime.fromisoformat(config["gpu_not_before_utc"].replace("Z", "+00:00"))
    while datetime.now(timezone.utc) < cutoff:
        remaining = (cutoff-datetime.now(timezone.utc)).total_seconds()
        save(wait_status, {"state": "user_gpu_reservation", "gpu_not_before_utc": cutoff.isoformat(),
                          "gpu_queries": 0, "model_calls": 0, "remaining_seconds": max(0, remaining)})
        time.sleep(min(30, max(.1, remaining)))
    launcher = APP/"scripts/start_local_bitagent.ps1"
    while True:
        check_gpu_window(config)
        result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(launcher),
                                 "-Config", str(config_path), "-RuntimeDir", str(runtime)],
                                capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            break
        save(wait_status, {"state": "waiting_for_idle_gpu_or_free_port", "last_preflight":
                          (result.stderr or result.stdout)[-1200:], "model_calls": 0,
                          "checked_at": datetime.now(timezone.utc).isoformat()})
        print("GPU/server preflight deferred; no foreign process changed.", flush=True)
        time.sleep(60)
    save(wait_status, {"state": "owned_server_starting", "started_at": datetime.now(timezone.utc).isoformat()})
    deadline = time.monotonic()+180
    last_error = None
    while time.monotonic() < deadline:
        try:
            with urlopen(config["endpoint"].removesuffix("/v1")+"/health", timeout=5) as response:
                if response.status == 200:
                    break
        except OSError as error:
            last_error = str(error)
        time.sleep(2)
    else:
        save(wait_status, {"state": "owned_server_failed_health_check", "error": last_error})
        raise RuntimeError("owned BitAgent server did not become healthy; inspect runtime logs")
    identity = LlamaCppAdapter(config).preflight()
    save(wait_status, {"state": "inference_starting", "runtime_identity": identity,
                      "started_at": datetime.now(timezone.utc).isoformat()})
    command = [sys.executable, str(APP/"scripts/run_local_benchmark.py"), "--config", str(config_path),
               "--baseline-plans", *[str(Path(p).resolve()) for p in args.baseline_plans],
               "--output-dir", str(directory)]
    result = subprocess.run(command, cwd=APP)
    save(wait_status, {"state": "campaign_finished" if result.returncode == 0 else "campaign_failed",
                      "exit_code": result.returncode, "finished_at": datetime.now(timezone.utc).isoformat()})
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
