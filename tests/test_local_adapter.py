from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
from unittest.mock import patch
import os
from urllib.parse import urlparse

from adapters.artifacts import verify_file
from adapters.storage import save_json, save_status
from adapters.llamacpp import LlamaCppAdapter, check_gpu_window, validate_shape
from systemic_risk_bench.campaign import output_schema
from systemic_risk_bench.suite import quantitative_tasks


def config():
    return {"endpoint": "http://127.0.0.1:8873/v1", "model_alias": "bitagent-test",
            "gpu_not_before_utc": "2026-11-16T07:35:22+00:00", "max_tokens": 2048,
            "base": {"path": "base.gguf", "bytes": 4, "sha256": "base-digest"},
            "adapter": {"path": "bitagent.gguf", "bytes": 4, "sha256": "adapter-digest", "id": 0, "scale": 1.0}}


class FakeServer:
    def __init__(self):
        self.requests = []
        self.adapters = [{"id": 0, "path": "bitagent.gguf", "scale": 1.0}]
        self.completion = {"model": "bitagent-test", "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"estimates": {"cva": 23400}, "rationale": "fixture", "limitations": []})}}],
                           "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}}

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        path = urlparse(request.full_url).path
        if path == "/v1/models":
            result = {"data": [{"id": "bitagent-test"}]}
        elif path == "/lora-adapters":
            result = self.adapters
        elif path == "/v1/chat/completions":
            result = self.completion
        else:
            raise AssertionError(path)
        return io.BytesIO(json.dumps(result).encode())


class LocalAdapterTests(unittest.TestCase):
    def test_gpu_gate_blocks_inference_before_any_http_call(self):
        server = FakeServer()
        adapter = LlamaCppAdapter(config(), opener=server, verify=False,
                                 clock=lambda: datetime(2026, 11, 16, 7, 0, tzinfo=timezone.utc))
        with self.assertRaisesRegex(ValueError, "GPU reservation"):
            adapter.infer(quantitative_tasks()[0], [], "quant")
        self.assertEqual(server.requests, [])

    def test_future_window_and_missing_timezone_are_rejected(self):
        settings = config()
        with self.assertRaises(ValueError):
            check_gpu_window(settings, datetime(2026, 11, 16, 7, 0, tzinfo=timezone.utc))
        settings["gpu_not_before_utc"] = "2099-01-01T00:00:00"
        with self.assertRaises(ValueError):
            check_gpu_window(settings)

    def test_pinned_lora_identity_and_same_packet_are_preserved(self):
        server = FakeServer()
        adapter = LlamaCppAdapter(config(), opener=server, verify=False,
                                 clock=lambda: datetime(2026, 11, 16, 8, 0, tzinfo=timezone.utc))
        packet = quantitative_tasks()[0]
        result = adapter.infer(packet, [{"response": "earlier"}], "quant")
        body = json.loads(server.requests[-1].data)
        supplied = json.loads(body["messages"][1]["content"])
        self.assertEqual(supplied["packet"], packet)
        self.assertEqual(supplied["prior_responses"], [{"response": "earlier"}])
        self.assertEqual(body["lora"], [{"id": 0, "scale": 1.0}])
        self.assertEqual(result["response"]["estimates"]["cva"], 23400)
        self.assertIsNone(result["usage"]["reasoning_tokens"])

    def test_base_only_wrong_scale_or_extra_adapter_cannot_pass(self):
        for adapters in ([], [{"id": 0, "path": "bitagent.gguf", "scale": 0}],
                         [{"id": 0, "path": "wrong.gguf", "scale": 1}],
                         [{"id": 0, "path": "bitagent.gguf", "scale": 1}, {"id": 1, "path": "other.gguf", "scale": 1}]):
            server = FakeServer()
            server.adapters = adapters
            with self.subTest(adapters=adapters), self.assertRaises(ValueError):
                LlamaCppAdapter(config(), opener=server, verify=False).preflight()

    def test_remote_host_is_not_accepted_as_local(self):
        settings = config()
        settings["endpoint"] = "https://example.com/v1"
        with self.assertRaises(ValueError):
            LlamaCppAdapter(settings, verify=False)

    def test_truncation_and_unknown_schema_fields_are_failures(self):
        packet = quantitative_tasks()[0]
        schema = output_schema(packet, "quant")
        with self.assertRaises(ValueError):
            validate_shape({"estimates": {"cva": True}, "rationale": "x", "limitations": []}, schema)
        with self.assertRaises(ValueError):
            validate_shape({"estimates": {"cva": 3}, "rationale": "x", "limitations": [], "future_gold": 1}, schema)
        server = FakeServer()
        server.completion["choices"][0]["finish_reason"] = "length"
        adapter = LlamaCppAdapter(config(), opener=server, verify=False,
                                 clock=lambda: datetime(2026, 11, 16, 8, 0, tzinfo=timezone.utc))
        with self.assertRaisesRegex(ValueError, "finish"):
            adapter.infer(packet, [], "quant")

    def test_file_hash_and_size_mismatch_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory)/"artifact.gguf"
            path.write_bytes(b"test")
            digest = hashlib.sha256(b"test").hexdigest()
            self.assertTrue(verify_file(path, digest, 4)["verified"])
            with self.assertRaises(ValueError):
                verify_file(path, digest, 5)
            with self.assertRaises(ValueError):
                verify_file(path, "wrong", 4)

    def test_transient_windows_file_locks_are_retried(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            target = Path(directory)/"status.json"
            original_replace = os.replace
            calls = []
            def locked_twice(source, destination):
                calls.append(1)
                if len(calls) < 3:
                    raise PermissionError("simulated Windows reader lock")
                return original_replace(source, destination)
            with patch("adapters.storage.os.replace", side_effect=locked_twice):
                save_json(target, {"state": "ready"}, delay=0)
            self.assertEqual(json.loads(target.read_text())["state"], "ready")
            self.assertEqual(len(calls), 3)

    def test_status_journal_survives_a_blocked_pointer(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            target = Path(directory)/"gpu-status.json"
            with patch("adapters.storage.save_json", side_effect=PermissionError("locked")):
                self.assertFalse(save_status(target, {"state": "waiting"}))
            journal = target.with_suffix(".jsonl")
            self.assertEqual(json.loads(journal.read_text())["state"], "waiting")

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell launcher check requires pwsh")
    def test_launcher_honors_reservation_before_hardware_or_process_access(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            settings = Path(directory)/"future-config.json"
            settings.write_text(json.dumps({"gpu_not_before_utc": "2099-01-01T00:00:00Z"}), encoding="utf-8")
            runtime = Path(directory)/"must-not-be-created"
            launcher = Path(__file__).resolve().parent.parent/"scripts/start_local_bitagent.ps1"
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(launcher),
                                     "-Config", str(settings), "-RuntimeDir", str(runtime)],
                                    capture_output=True, text=True, timeout=45)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("GPU reservation", result.stderr)
            self.assertFalse(runtime.exists())


if __name__ == "__main__":
    unittest.main()
