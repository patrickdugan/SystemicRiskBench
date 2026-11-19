"""Packet smuggling, registered budgets, and model-failure cost accounting."""
from contextlib import redirect_stderr
import copy
from datetime import datetime, timezone
import io
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlparse

from adapters.revision_llamacpp import RevisionLlamaCppAdapter, main, validate_revision_packet
from examples.finance_revision_fixture_adapter import reply
from systemic_risk_bench.agent_revision import fixture, initial_packet, update_packet
from systemic_risk_bench.finance_revision import FAMILIES, packet
from systemic_risk_bench.revision_receipts import parse_receipt


class Server:
    def __init__(self, completion):
        self.requests = []
        self.content = completion
        self.finish_reason = "stop"
        self.usage = {"prompt_tokens": 25, "completion_tokens": 8, "total_tokens": 33}
        self.raise_http = False

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        path = urlparse(request.full_url).path
        if path == "/v1/models":
            result = {"data": [{"id": "bitagent-test"}]}
        elif path == "/lora-adapters":
            result = [{"id": 0, "path": "/local/private/adapter.gguf", "scale": 1.0}]
        elif path == "/v1/chat/completions":
            if self.raise_http:
                raise OSError("synthetic HTTP failure")
            result = {"model": "bitagent-test", "usage": self.usage,
                      "choices": [{"finish_reason": self.finish_reason,
                                   "message": {"content": json.dumps(self.content)}}]}
        else:
            raise AssertionError(path)
        return io.BytesIO(json.dumps(result).encode())


def settings():
    return {"endpoint": "http://127.0.0.1:8873/v1", "model_alias": "bitagent-test",
            "gpu_not_before_utc": "2026-11-16T07:35:22+00:00", "max_tokens": 96,
            "temperature": 0, "seed": 0,
            "base": {"path": "/local/private/base.gguf", "bytes": 4, "sha256": "a" * 64},
            "adapter": {"path": "/local/private/adapter.gguf", "bytes": 4,
                        "sha256": "b" * 64, "id": 0, "scale": 1.0}}


def adapter(server):
    return RevisionLlamaCppAdapter(settings(), opener=server, verify=False,
        clock=lambda: datetime(2026, 11, 19, tzinfo=timezone.utc))


class RevisionTransportTests(unittest.TestCase):
    def test_generated_base_and_financial_packets_satisfy_closed_contract(self):
        for index, family in enumerate(FAMILIES):
            world = fixture(index)
            for mode in ("count", "bitmap"):
                memory = world.old_count if mode == "count" else world.old_mask
                for supplied in (initial_packet(world, mode), update_packet(world, mode, memory),
                                 packet(world, mode, family, "initial"),
                                 packet(world, mode, family, "update", memory)):
                    validate_revision_packet(supplied)

    def test_hidden_history_and_nested_smuggling_fail_before_http(self):
        world = fixture(0)
        original = packet(world, "bitmap", "price_feed", "update", world.old_mask)
        mutations = []
        bad = copy.deepcopy(original)
        bad["hidden_regime"] = 0
        mutations.append(bad)
        for field in ("likelihood", "finance_context", "reply_contract"):
            bad = copy.deepcopy(original)
            bad[field]["earlier_history"] = list(world.old)
            mutations.append(bad)
        bad = copy.deepcopy(original)
        bad["corrections"][0]["old_match"] = world.old[world.slots[0]]
        mutations.append(bad)
        bad = copy.deepcopy(original)
        bad["finance_context"]["description"] += " earlier answer: halt"
        mutations.append(bad)
        bad = copy.deepcopy(original)
        bad["likelihood"]["priors"][0][0] = True
        mutations.append(bad)
        bad = copy.deepcopy(original)
        bad["memory"] = True
        mutations.append(bad)
        bad = copy.deepcopy(original)
        bad["corrections"][1] = copy.deepcopy(bad["corrections"][0])
        mutations.append(bad)
        initial = packet(world, "bitmap", "price_feed", "initial")
        initial["old"][0]["hidden_state"] = list(world.replacements)
        mutations.append(initial)
        for supplied in mutations:
            server = Server({})
            with self.subTest(supplied=supplied), self.assertRaises(ValueError):
                adapter(server).infer_revision(supplied, [])
            self.assertEqual(server.requests, [])

    def test_success_receipt_binds_forecast_without_disclosing_local_paths(self):
        supplied = packet(fixture(0), "count", "price_feed", "initial")
        server = Server(reply(supplied))
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            response = adapter(server).infer_revision(supplied, [])
        telemetry, status, error = parse_receipt(stderr.getvalue(), supplied, response, "ok")
        self.assertEqual((status, error), ("valid", None))
        self.assertEqual(telemetry["usage"], {"input_tokens": 25, "output_tokens": 8, "total_tokens": 33})
        self.assertFalse(telemetry["identity"]["local_artifacts_verified"])
        self.assertNotIn("/local/private", stderr.getvalue())
        self.assertFalse(telemetry["isolation"]["server_reset_verified"])
        payload = json.loads(server.requests[-1].data)
        self.assertEqual(json.loads(payload["messages"][1]["content"]), {"packet": supplied})
        self.assertFalse(payload["cache_prompt"])

    def test_invalid_model_outputs_preserve_costs(self):
        supplied = packet(fixture(0), "count", "price_feed", "initial")
        valid = reply(supplied)
        for result, finish in ((valid, "length"), ({**valid, "memory": 13}, "stop"),
                               ({**valid, "action": "send_order"}, "stop"),
                               ({**valid, "extra_history": "retained"}, "stop")):
            server = Server(result)
            server.finish_reason = finish
            stderr = io.StringIO()
            with self.subTest(result=result, finish=finish), redirect_stderr(stderr), self.assertRaises(ValueError):
                adapter(server).infer_revision(supplied, [])
            telemetry, status, error = parse_receipt(stderr.getvalue(), supplied, None, "adapter_error")
            self.assertEqual((status, error), ("valid", None))
            self.assertEqual(telemetry["status"], "invalid_response")
            self.assertEqual(telemetry["usage"]["output_tokens"], 8)

    def test_transport_failure_records_unknown_usage_and_elapsed_time(self):
        supplied = packet(fixture(0), "count", "price_feed", "initial")
        server = Server({})
        server.raise_http = True
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(OSError):
            adapter(server).infer_revision(supplied, [])
        telemetry, status, _ = parse_receipt(stderr.getvalue(), supplied, None, "adapter_error")
        self.assertEqual(status, "valid")
        self.assertEqual(telemetry["status"], "transport_error")
        self.assertIsNone(telemetry["usage"]["output_tokens"])
        self.assertGreaterEqual(telemetry["elapsed_seconds"], 0)

    def test_model_registration_mismatch_blocks_all_http(self):
        supplied = packet(fixture(0), "count", "price_feed", "initial")
        experiment = {"evaluation_kind": "model", "experiment_id": "pilot",
                      "base_sha256": "a" * 64, "checkpoint_sha256": "b" * 64,
                      "model_alias": "bitagent-test", "max_output_tokens_per_call": 1024,
                      "temperature": 0, "seed": 0}
        server = Server(reply(supplied))
        with self.assertRaisesRegex(ValueError, "max_output_tokens"):
            adapter(server).infer_revision(supplied, [], experiment)
        self.assertEqual(server.requests, [])

    def test_production_cli_rejects_omitted_model_intent_before_adapter_creation(self):
        supplied = packet(fixture(0), "count", "price_feed", "initial")
        request = {"protocol": "srb.adapter.v0.1", "packet": supplied,
                   "prior_responses": [], "experiment": {
                       "experiment_id": "unregistered-model",
                       "status": "template_no_model_calls_run",
                       "checkpoint_sha256": "REPLACE_WITH_LOCAL_DIGEST"}}
        with patch("sys.stdin", io.StringIO(json.dumps(request))), patch(
                "adapters.revision_llamacpp.read_json", return_value={}), patch(
                "adapters.revision_llamacpp.RevisionLlamaCppAdapter") as model:
            with self.assertRaisesRegex(ValueError, "explicit model registration"):
                main(["--config", "test-only.json"])
            model.assert_not_called()

    def test_budget_exceedance_preserves_measured_cost(self):
        supplied = packet(fixture(0), "count", "price_feed", "initial")
        server = Server(reply(supplied))
        server.usage = {"prompt_tokens": 25, "completion_tokens": 97, "total_tokens": 122}
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaisesRegex(ValueError, "budget"):
            adapter(server).infer_revision(supplied, [])
        telemetry, status, _ = parse_receipt(stderr.getvalue(), supplied, None, "adapter_error")
        self.assertEqual(status, "valid")
        self.assertEqual(telemetry["status"], "budget_exceeded")
        self.assertEqual(telemetry["usage"]["output_tokens"], 97)


if __name__ == "__main__":
    unittest.main()
