"""Per-stage ephemeral llama-server lifecycle, receipt binding, and reset verification."""
from contextlib import redirect_stderr
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import urlparse

from adapters.ephemeral_llamacpp import EphemeralLlamaCppSession, build_server_argv
from adapters.revision_llamacpp import RevisionLlamaCppAdapter
from examples.finance_revision_fixture_adapter import reply
from systemic_risk_bench.agent_revision import fixture
from systemic_risk_bench.finance_revision import packet, run_financial_revision
from systemic_risk_bench.finance_revision_panels import build_manifest
from systemic_risk_bench.revision_receipts import parse_receipt, validate_registered_experiment
from systemic_risk_bench.runner import sha


class FakeEphemeralServer:
    def __init__(self, completion):
        self.content = completion
        self.finish_reason = "stop"
        self.usage = {"prompt_tokens": 31, "completion_tokens": 9, "total_tokens": 40}
        self.requests = []

    def __call__(self, request, timeout=None):
        url = request if isinstance(request, str) else request.full_url
        self.requests.append(url)
        path = urlparse(url).path
        if path == "/health":
            result = {"status": "ok"}
        elif path == "/v1/models":
            result = {"data": [{"id": "bitagent-test"}]}
        elif path == "/lora-adapters":
            result = [{"id": 0, "path": "/tmp/adapter.gguf", "scale": 1.0}]
        elif path == "/v1/chat/completions":
            result = {
                "model": "bitagent-test",
                "usage": self.usage,
                "choices": [{"finish_reason": self.finish_reason,
                             "message": {"content": json.dumps(self.content)}}],
            }
        else:
            raise AssertionError(path)
        return io.BytesIO(json.dumps(result).encode("utf-8"))


class FakeSession:
    counter = 0

    def __init__(self, config, *, verify=True, clock=None, opener=None,
                 reaped=True, port_closed=True):
        FakeSession.counter += 1
        self.config = config
        self.verify = verify
        self.port = 49000 + FakeSession.counter
        self.endpoint = f"http://127.0.0.1:{self.port}/v1"
        self.server_boot_sha256 = hashlib.sha256(
            f"boot-{FakeSession.counter}".encode("ascii")).hexdigest()
        self.startup_seconds = 0.42
        self.shutdown_seconds = None
        self.process_reaped = False
        self.port_closed_verified = False
        self._reaped_target = reaped
        self._port_closed_target = port_closed
        self.entered = False
        self.closed = False

    def __enter__(self):
        self.entered = True
        return self

    def close(self):
        self.closed = True
        self.process_reaped = self._reaped_target
        self.port_closed_verified = self._port_closed_target
        self.shutdown_seconds = 0.05

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def _ephemeral_settings():
    return {
        "server_lifecycle": "ephemeral_per_stage",
        "server_exe": "/local/llama-server",
        "server_sha256": "c" * 64,
        "model_alias": "bitagent-test",
        "gpu_not_before_utc": "2026-11-16T07:35:22+00:00",
        "max_tokens": 96,
        "temperature": 0,
        "seed": 0,
        "base": {"path": "/local/base.gguf", "bytes": 4, "sha256": "a" * 64},
        "adapter": {"path": "/local/adapter.gguf", "bytes": 4,
                    "sha256": "b" * 64, "id": 0, "scale": 1.0},
    }


def _ephemeral_experiment(manifest):
    return {
        "experiment_id": "SRB-REV-03-ephemeral-unit",
        "evaluation_kind": "model",
        "status": "registered",
        "panel": "pilot",
        "panel_manifest_sha256": manifest["manifest_sha256"],
        "preregistered_cases": 6,
        "max_calls_per_arm": 12,
        "max_wall_seconds_per_arm": 60,
        "memory_arms": ["count", "bitmap"],
        "server_sha256": "c" * 64,
        "base_sha256": "a" * 64,
        "checkpoint_sha256": "b" * 64,
        "model_alias": "bitagent-test",
        "max_output_tokens_per_call": 96,
        "temperature": 0,
        "seed": 0,
        "inference_server": "ephemeral_per_stage_llama_cpp",
        "server_reset_between_stages": True,
    }


class EphemeralRevisionServerTests(unittest.TestCase):
    def test_ephemeral_registration_requires_matching_lifecycle_and_server_digest(self):
        manifest = build_manifest()
        supplied = packet(fixture(0), "count", "price_feed", "initial")
        cfg = _ephemeral_settings()
        exp = _ephemeral_experiment(manifest)
        validate_registered_experiment(cfg, exp, supplied, require_model=True)
        for bad_exp in (
            {**exp, "server_reset_between_stages": False},
            {**exp, "server_sha256": "d" * 64},
            {**exp, "inference_server": "operator_owned_loopback_llama_cpp"},
        ):
            with self.subTest(bad_exp=bad_exp), self.assertRaises(ValueError):
                validate_registered_experiment(cfg, bad_exp, supplied, require_model=True)
        with self.assertRaises(ValueError):
            validate_registered_experiment({**cfg, "server_lifecycle": "persistent"},
                                           exp, supplied, require_model=True)

    def test_ephemeral_stage_emits_verified_reset_receipt_and_reaps_before_return(self):
        manifest = build_manifest()
        supplied = packet(fixture(0), "count", "price_feed", "initial")
        expected = reply(supplied)
        server = FakeEphemeralServer(expected)
        sessions = []

        def factory(config, **kwargs):
            sess = FakeSession(config, **kwargs)
            sessions.append(sess)
            return sess

        model = RevisionLlamaCppAdapter(
            _ephemeral_settings(), opener=server, verify=True,
            clock=lambda: datetime(2026, 11, 19, tzinfo=timezone.utc),
            session_factory=factory,
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            response = model.infer_revision(supplied, [], _ephemeral_experiment(manifest))
        self.assertEqual(response, expected)
        self.assertEqual(len(sessions), 1)
        self.assertTrue(sessions[0].closed)
        telemetry, status, error = parse_receipt(stderr.getvalue(), supplied, response, "ok")
        self.assertEqual((status, error), ("valid", None))
        self.assertTrue(telemetry["isolation"]["server_reset_verified"])
        self.assertFalse(telemetry["isolation"]["physical_memory_enforced"])
        self.assertEqual(telemetry["isolation"]["requests_served"], 1)
        self.assertEqual(telemetry["isolation"]["server_boot_sha256"],
                         sessions[0].server_boot_sha256)

    def test_unreaped_ephemeral_server_blocks_ok_response_and_reset_attestation(self):
        manifest = build_manifest()
        supplied = packet(fixture(0), "count", "price_feed", "initial")
        server = FakeEphemeralServer(reply(supplied))

        def broken_factory(config, **kwargs):
            return FakeSession(config, reaped=False, port_closed=False, **kwargs)

        model = RevisionLlamaCppAdapter(
            _ephemeral_settings(), opener=server, verify=True,
            clock=lambda: datetime(2026, 11, 19, tzinfo=timezone.utc),
            session_factory=broken_factory,
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaisesRegex(RuntimeError, "teardown"):
            model.infer_revision(supplied, [], _ephemeral_experiment(manifest))
        telemetry, status, error = parse_receipt(stderr.getvalue(), supplied, None, "adapter_error")
        self.assertEqual((status, error), ("valid", None))
        self.assertEqual(telemetry["status"], "transport_error")
        self.assertFalse(telemetry["isolation"]["server_reset_verified"])

    def test_smuggled_packet_never_spawns_ephemeral_server(self):
        world = fixture(0)
        bad = packet(world, "count", "price_feed", "update", world.old_count)
        bad["hidden_regime"] = world.regime
        spawned = []
        model = RevisionLlamaCppAdapter(
            _ephemeral_settings(), opener=FakeEphemeralServer({}), verify=False,
            clock=lambda: datetime(2026, 11, 19, tzinfo=timezone.utc),
            session_factory=lambda *a, **k: spawned.append(1),
        )
        with self.assertRaises(ValueError):
            model.infer_revision(bad, [])
        self.assertEqual(spawned, [])

    def test_report_certifies_server_reset_only_when_all_stage_boots_are_unique(self):
        manifest = build_manifest()
        exp = _ephemeral_experiment(manifest)

        def make_exec(*, duplicate_boot=False):
            calls = [0]

            def fake_execute(argv, pkt, previous, timeout, experiment):
                calls[0] += 1
                ans = reply(pkt)
                boot_tag = "same-boot" if duplicate_boot else f"boot-{calls[0]}"
                boot_sha = hashlib.sha256(boot_tag.encode("ascii")).hexdigest()
                telemetry_obj = {
                    "schema": "srb.revision_inference_receipt.v1",
                    "packet_sha256": sha(pkt),
                    "response_sha256": sha(ans),
                    "phase": pkt["phase"],
                    "status": "ok",
                    "elapsed_seconds": 0.2,
                    "requested_model": "bitagent-test",
                    "resolved_model": "bitagent-test",
                    "usage": {"input_tokens": 20, "output_tokens": 6, "total_tokens": 26},
                    "sampling": {"temperature": 0, "seed": 0, "max_tokens": 96},
                    "identity": {
                        "base_sha256": "a" * 64,
                        "adapter_sha256": "b" * 64,
                        "adapter_id": 0,
                        "adapter_scale": 1.0,
                        "local_artifacts_verified": True,
                        "verification": "ephemeral_per_stage_server_plus_local_file_and_adapter_hashes",
                    },
                    "isolation": {
                        "server_reset_verified": True,
                        "physical_memory_enforced": False,
                        "server_boot_sha256": boot_sha,
                        "requests_served": 1,
                        "process_reaped": True,
                        "port_closed_verified": True,
                        "startup_seconds": 0.5,
                        "shutdown_seconds": 0.05,
                    },
                    "error_code": None,
                }
                parsed, t_status, err = parse_receipt(
                    "SRB_REVISION_RECEIPT_V1 " + json.dumps(telemetry_obj),
                    pkt, ans, "ok",
                )
                self.assertEqual((t_status, err), ("valid", None))
                return {
                    "status": "ok", "exit_code": 0, "response": ans, "wall_seconds": 0.75,
                    "stdout_sha256": sha(ans), "stderr_tail": "",
                    "input_tokens": 20, "output_tokens": 6,
                    "telemetry_status": "valid", "adapter_telemetry": parsed,
                }
            return fake_execute

        with patch("systemic_risk_bench.finance_revision.execute", side_effect=make_exec()):
            unique_report = run_financial_revision(
                ["test"], exp, mode="count", panel="pilot", manifest=manifest)
        self.assertTrue(unique_report["model_server_state_reset_verified"])
        self.assertFalse(unique_report["physical_memory_enforced"])
        self.assertEqual(unique_report["inference_costs"]["server_reset_verified_calls"], 12)
        self.assertEqual(unique_report["inference_costs"]["unique_server_boots_observed"], 12)
        self.assertAlmostEqual(unique_report["inference_costs"]["server_startup_seconds_observed"], 6.0)

        with patch("systemic_risk_bench.finance_revision.execute",
                   side_effect=make_exec(duplicate_boot=True)):
            reused_report = run_financial_revision(
                ["test"], exp, mode="count", panel="pilot", manifest=manifest)
        self.assertFalse(reused_report["model_server_state_reset_verified"])
        self.assertEqual(reused_report["inference_costs"]["unique_server_boots_observed"], 1)

    def test_ephemeral_session_verifies_files_spawns_and_cleans_up_fake_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {}
            for name, content in (("server", b"srv!"), ("base", b"base"), ("adapter", b"lora")):
                p = root / name
                p.write_bytes(content)
                files[name] = (str(p), len(content), hashlib.sha256(content).hexdigest())
            cfg = copy.deepcopy(_ephemeral_settings())
            cfg["server_exe"], cfg["server_bytes"], cfg["server_sha256"] = files["server"]
            cfg["base"] = {"path": files["base"][0], "bytes": files["base"][1], "sha256": files["base"][2]}
            cfg["adapter"] = {"path": files["adapter"][0], "bytes": files["adapter"][1],
                              "sha256": files["adapter"][2], "id": 0, "scale": 1.0}
            cfg["minimum_free_vram_mib"] = 2600
            argv = build_server_argv(cfg, 18999)
            self.assertIn("--no-webui", argv)
            self.assertNotIn("--slot-save-path", argv)

            class DummyProc:
                pid = 42424
                def __init__(self):
                    self.terminated = False
                def poll(self):
                    return 0 if self.terminated else None
                def terminate(self):
                    self.terminated = True
                def kill(self):
                    self.terminated = True
                def wait(self, timeout=None):
                    self.terminated = True
                    return 0

            proc = DummyProc()
            server = FakeEphemeralServer({})
            with EphemeralLlamaCppSession(
                cfg, verify=True,
                clock=lambda: datetime(2026, 11, 19, tzinfo=timezone.utc),
                opener=server, popen=lambda *a, **k: proc,
                vram_checker=lambda mib: 15000,
            ) as session:
                self.assertIsNotNone(session.server_boot_sha256)
                self.assertGreaterEqual(session.startup_seconds, 0.0)
            self.assertTrue(session.process_reaped)
            self.assertTrue(session.port_closed_verified)


if __name__ == "__main__":
    unittest.main()
