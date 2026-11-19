"""Unit tests for the two-pass stage-isolated bounded-scratchpad adapter (SRB-REV-04)."""
from contextlib import redirect_stderr
from datetime import datetime, timezone
import hashlib
import io
import json
import unittest
from urllib.parse import urlparse

from adapters.revision_scratchpad_llamacpp import ScratchpadRevisionLlamaCppAdapter
from examples.finance_revision_fixture_adapter import reply
from systemic_risk_bench.agent_revision import fixture
from systemic_risk_bench.finance_revision import packet
from systemic_risk_bench.finance_revision_panels import build_manifest
from systemic_risk_bench.revision_receipts import parse_receipt


class TwoPassFakeServer:
    def __init__(self, final_obj):
        self.final_obj = final_obj
        self.chat_calls = []

    def __call__(self, request, timeout=None):
        url = request if isinstance(request, str) else request.full_url
        path = urlparse(url).path
        if path == "/health":
            result = {"status": "ok"}
        elif path == "/v1/models":
            result = {"data": [{"id": "bitagent-test"}]}
        elif path == "/lora-adapters":
            result = [{"id": 0, "path": "/tmp/adapter.gguf", "scale": 1.0}]
        elif path == "/v1/chat/completions":
            body = json.loads(request.data.decode("utf-8"))
            self.chat_calls.append(body)
            if len(self.chat_calls) == 1:
                result = {
                    "model": "bitagent-test",
                    "usage": {"prompt_tokens": 900, "completion_tokens": 300, "total_tokens": 1200},
                    "choices": [{"finish_reason": "stop",
                                 "message": {"content": "Step 1: sum bits..."}}],
                }
            else:
                result = {
                    "model": "bitagent-test",
                    "usage": {"prompt_tokens": 1250, "completion_tokens": 40, "total_tokens": 1290},
                    "choices": [{"finish_reason": "stop",
                                 "message": {"content": json.dumps(self.final_obj)}}],
                }
        else:
            raise AssertionError(path)
        return io.BytesIO(json.dumps(result).encode("utf-8"))


class DummySession:
    seq = 0

    def __init__(self, config, **kwargs):
        DummySession.seq += 1
        self.port = 51000 + DummySession.seq
        self.server_boot_sha256 = hashlib.sha256(f"srb04-{DummySession.seq}".encode()).hexdigest()
        self.startup_seconds = 0.3
        self.shutdown_seconds = None
        self.process_reaped = False
        self.port_closed_verified = False

    def __enter__(self):
        return self

    def close(self):
        self.process_reaped = True
        self.port_closed_verified = True
        self.shutdown_seconds = 0.04


def _cfg():
    return {
        "server_lifecycle": "ephemeral_per_stage",
        "server_exe": "/local/llama-server",
        "server_sha256": "c" * 64,
        "model_alias": "bitagent-test",
        "gpu_not_before_utc": "2026-11-16T07:35:22+00:00",
        "max_tokens": 2048,
        "max_scratchpad_tokens": 1792,
        "max_commit_tokens": 256,
        "temperature": 0,
        "seed": 0,
        "base": {"path": "/local/base.gguf", "bytes": 4, "sha256": "a" * 64},
        "adapter": {"path": "/local/adapter.gguf", "bytes": 4,
                    "sha256": "b" * 64, "id": 0, "scale": 1.0},
    }


def _exp(manifest):
    return {
        "experiment_id": "SRB-REV-04-scratchpad-unit",
        "evaluation_kind": "model",
        "status": "registered",
        "panel": "pilot",
        "panel_manifest_sha256": manifest["manifest_sha256"],
        "preregistered_cases": 6,
        "max_calls_per_arm": 12,
        "max_wall_seconds_per_arm": 120,
        "memory_arms": ["count", "bitmap"],
        "server_sha256": "c" * 64,
        "base_sha256": "a" * 64,
        "checkpoint_sha256": "b" * 64,
        "model_alias": "bitagent-test",
        "max_output_tokens_per_call": 2048,
        "temperature": 0,
        "seed": 0,
        "inference_server": "ephemeral_per_stage_llama_cpp",
        "server_reset_between_stages": True,
    }


class ScratchpadRevisionTests(unittest.TestCase):
    def test_two_pass_scratchpad_sums_tokens_strips_cot_and_reaps_server(self):
        manifest = build_manifest()
        pkt = packet(fixture(0), "bitmap", "price_feed", "initial")
        expected = reply(pkt)
        srv = TwoPassFakeServer(expected)
        model = ScratchpadRevisionLlamaCppAdapter(
            _cfg(), opener=srv, verify=True,
            clock=lambda: datetime(2026, 11, 19, tzinfo=timezone.utc),
            session_factory=DummySession,
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            ans = model.infer_revision(pkt, [], _exp(manifest))
        self.assertEqual(ans, expected)
        self.assertNotIn("Step 1", json.dumps(ans))
        self.assertEqual(len(srv.chat_calls), 2)
        self.assertNotIn("response_format", srv.chat_calls[0])
        self.assertEqual(srv.chat_calls[1]["response_format"]["type"], "json_schema")
        telemetry, status, err = parse_receipt(stderr.getvalue(), pkt, ans, "ok")
        self.assertEqual((status, err), ("valid", None))
        self.assertEqual(telemetry["usage"], {
            "input_tokens": 2150, "output_tokens": 340, "total_tokens": 2490,
        })
        self.assertEqual(telemetry["isolation"]["requests_served"], 2)
        self.assertTrue(telemetry["isolation"]["server_reset_verified"])


if __name__ == "__main__":
    unittest.main()
