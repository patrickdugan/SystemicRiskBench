"""Prepare exact pinned Q1 BitAgent CPU model registration for GH Actions.

The CI runner downloads immutable assets, verifies hashes, locates the
distribution llama-server and hashes the binary before launching inference.
No GitHub secret or persistent model path is part of the run artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from adapters.artifacts import verify_file
from systemic_risk_bench.rev05_ci_pilot import validate_registration
from systemic_risk_bench.scoring import read_json


def prepare(spec, manifest, *, server, base, adapter, config_path, experiment_path):
    validate_registration(spec, manifest)
    identity = spec["model"]
    server = Path(server).resolve()
    base = Path(base).resolve()
    adapter = Path(adapter).resolve()
    if not server.is_file():
        raise ValueError("llama-server binary missing")
    verify_file(base, identity["base"]["sha256"], identity["base"]["bytes"])
    verify_file(adapter, identity["adapter"]["sha256"], identity["adapter"]["bytes"])
    server_bytes = server.stat().st_size
    server_sha = hashlib.sha256(server.read_bytes()).hexdigest()
    r = spec["runtime"]
    base_model = {"path":str(base), "bytes":identity["base"]["bytes"],
                  "sha256":identity["base"]["sha256"]}
    lora = {"path":str(adapter), "bytes":identity["adapter"]["bytes"],
            "sha256":identity["adapter"]["sha256"],"id":0,"scale":1.0}
    runtime = {
        "server_exe":str(server), "server_sha256":server_sha,"server_bytes":server_bytes,
        "base":base_model, "adapter":lora,
        "endpoint":"http://127.0.0.1:8873/v1",
        "model_alias":identity["alias"],
        "gpu_not_before_utc":"2026-11-19T00:00:00+00:00",
        "server_lifecycle":"ephemeral_per_stage",
        "context":r["context"],"n_gpu_layers":r["n_gpu_layers"],
        "device":r["device"],"threads":r["threads"],
        "threads_batch":r["threads_batch"],"flash_attn":r["flash_attn"],
        "cache_type_k":r["cache_type_k"],"cache_type_v":r["cache_type_v"],
        "batch_size":r["batch_size"],"ubatch_size":r["ubatch_size"],
        "max_tokens":r["max_tokens"],
        "temperature":r["temperature"],"seed":r["seed"],
        "startup_timeout_seconds":r["startup_timeout_seconds"],
        "timeout_seconds":r["per_stage_timeout_seconds"],
    }
    experiment = {
        "experiment_id":spec["experiment_id"],
        "status":"registered",
        "evaluation_kind":"model",
        "architecture_label":"BitAgent Bonsai 8B Q1 source-pinned CPU ephemeral stage",
        "panel":"ci_pilot_subset_0_5",
        "source_panel":"pilot",
        "panel_manifest_sha256":manifest["manifest_sha256"],
        "root_indices":spec["root_indices"],
        "memory_arms":spec["modes"],
        "preregistered_cases":len(spec["root_indices"]),
        "max_calls_per_arm":2*len(spec["root_indices"]),
        "max_wall_seconds_per_arm":r["max_arm_wall_seconds"],
        "max_input_tokens_per_call":6144,
        "max_output_tokens_per_call":r["max_tokens"],
        "base_sha256":identity["base"]["sha256"],
        "checkpoint_sha256":identity["adapter"]["sha256"],
        "server_sha256":server_sha,
        "model_alias":identity["alias"],
        "inference_server":"ephemeral_per_stage_llama_cpp",
        "temperature":r["temperature"],"seed":r["seed"],
        "agent_action_authorized":False,
        "server_reset_between_stages":True,
        "physical_memory_enforcement":"unverified_unsandboxed_host_ephemeral_server_only",
        "model_weight_source_commit":identity["base"]["url"],
        "lora_source_commit":identity["adapter"]["url"],
        "llama_cpp_release_tag":identity["llama_server"]["tag"],
        "llama_cpp_source_commit":identity["llama_server"]["commit"],
        "llama_cpp_archive_sha256":identity["llama_server"]["archive_sha256"],
    }
    for output, content in ((config_path, runtime),(experiment_path, experiment)):
        dst=Path(output)
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_text(json.dumps(content,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {"server_sha256":server_sha,"server_bytes":server_bytes,
            "base_verified":True,"adapter_verified":True,"registration_written":True}


def main():
    parser=argparse.ArgumentParser()
    for item in ("spec","manifest","server","base","adapter","runtime","experiment"):
        parser.add_argument("--"+item,required=True)
    args=parser.parse_args()
    report=prepare(
        read_json(args.spec),read_json(args.manifest),
        server=args.server,base=args.base,adapter=args.adapter,
        config_path=args.runtime,experiment_path=args.experiment)
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
