"""SRB-REV-02 public synthetic source-only and local transport tests."""
from datetime import datetime, timezone
import io
import json
import math
import sys
import unittest
from urllib.parse import urlparse

from adapters.revision_llamacpp import RevisionLlamaCppAdapter
from examples.finance_revision_fixture_adapter import reply as reference_reply
from systemic_risk_bench.agent_revision import fixture
from systemic_risk_bench.finance_revision import (
    ACTIONS, FAMILIES, SCENARIOS, SCHEMA, expected_loss, optimal_action,
    packet, parse_response, policy_regret, run_financial_revision,
)


class FakeServer:
    def __init__(self):
        self.requests = []
        self.completion = None
        self.finish = "stop"
        self.tool_calls = None

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        path = urlparse(request.full_url).path
        if path == "/v1/models":
            data = {"data": [{"id": "bitagent-test"}]}
        elif path == "/lora-adapters":
            data = [{"id": 0, "path": "bitagent.gguf", "scale": 1.0}]
        elif path == "/v1/chat/completions":
            data = {"model": "bitagent-test", "usage": {
                "prompt_tokens": 25, "completion_tokens": 8},
                "choices": [{"finish_reason": self.finish, "message": {
                    "content": json.dumps(self.completion),
                    "tool_calls": self.tool_calls}}]}
        else:
            raise AssertionError(path)
        return io.BytesIO(json.dumps(data).encode())


def config():
    return {"endpoint": "http://127.0.0.1:8873/v1",
            "model_alias": "bitagent-test",
            "gpu_not_before_utc": "2026-11-16T07:35:22+00:00",
            "timeout_seconds": 10, "max_tokens": 1024,
            "base": {"path": "base.gguf", "bytes": 4, "sha256": "base-digest"},
            "adapter": {"path": "bitagent.gguf", "bytes": 4,
                        "sha256": "adapter-digest", "id": 0, "scale": 1.0}}


def adapter(server):
    return RevisionLlamaCppAdapter(
        config(), opener=server, verify=False,
        clock=lambda: datetime(2026, 11, 19, tzinfo=timezone.utc))


class FinanceRevisionTests(unittest.TestCase):
    def test_packets_exclude_evaluator_regime_and_history(self):
        for index in range(18):
            world = fixture(index)
            family = FAMILIES[index % 3]
            for mode in ("count", "bitmap"):
                first = packet(world, mode, family, "initial")
                state = world.old_count if mode == "count" else world.old_mask
                later = packet(world, mode, family, "update", state)
                self.assertEqual(first["schema"], SCHEMA)
                self.assertEqual(first["phase"], "initial")
                self.assertEqual(later["schema"], SCHEMA)
                self.assertEqual(later["old"], "not_replayed")
                self.assertEqual(later["prior_responses"], "not_replayed")
                self.assertEqual(len(later["corrections"]), 6)
                self.assertNotIn("corrections", first)
                self.assertNotIn("regime", json.dumps(first))
                self.assertNotIn("regime", json.dumps(later))
                self.assertNotIn(world.host_key.hex(), json.dumps(later))
                self.assertEqual(
                    [record["record_id"] for record in first["old"]],
                    [f"{family}/{i:02d}" for i in range(12)])
                for item in later["corrections"]:
                    self.assertEqual(item["record_id"], f"{family}/{item['slot']:02d}")
                    self.assertEqual(item["new_version"], 1)
                self.assertEqual(later["finance_context"]["execution"],
                                 "hypothetical_read_only_decision")

    def test_policy_losses_and_regret(self):
        for family in FAMILIES:
            self.assertEqual(optimal_action((1.0, 0, 0), family), "continue")
            self.assertEqual(optimal_action((0, 1.0, 0), family), "de_risk")
            self.assertEqual(optimal_action((0, 0, 1.0), family),
                             "halt_and_escalate")
            for distribution in ((1.0, 0, 0), (0.15, 0.45, 0.4), (0, 0, 1.0)):
                minimum = min(expected_loss(action, distribution, family)
                              for action in ACTIONS)
                self.assertAlmostEqual(
                    expected_loss(optimal_action(distribution, family),
                                  distribution, family), minimum)
                for action in ACTIONS:
                    self.assertGreaterEqual(
                        policy_regret(action, distribution, family), 0)
            self.assertEqual(set(SCENARIOS[family]["loss"]), set(ACTIONS))

    def test_reference_subprocess_count_and_bitmap(self):
        command = [sys.executable, "-m", "examples.finance_revision_fixture_adapter"]
        for mode in ("count", "bitmap"):
            result = run_financial_revision(
                command, {"experiment_id": "oracle-transport-only"},
                mode=mode, cases=12, timeout=10)
            self.assertEqual(result["coverage"], 1.0)
            self.assertEqual(result["n_scored"], 12)
            self.assertEqual(result["model_calls_attempted"], 24)
            self.assertEqual(result["memory_logical_bits"],
                             4 if mode == "count" else 12)
            self.assertEqual(result["n_cases_by_family"],
                             {family: 4 for family in FAMILIES})
            self.assertLess(result["mean_excess_brier_with_missing_penalty"], 1e-20)
            self.assertLess(result["mean_policy_regret_with_missing_penalty"], 1e-12)
            self.assertEqual(result["action_accuracy_scored"], 1.0)
            self.assertFalse(result["model_evaluation_claim"])
            self.assertFalse(result["physical_memory_enforced"])
            self.assertFalse(result["model_server_state_reset_verified"])
            for row in result["rows"]:
                self.assertEqual(row["status"], "scored")
                self.assertAlmostEqual(row["policy_regret_vs_matched"], 0.0)
                self.assertEqual(row["initial_receipt"]["status"], "ok")
                self.assertEqual(row["update_receipt"]["status"], "ok")

    def test_invalid_initial_and_update_remain_in_denominator(self):
        invalid = run_financial_revision(
            [sys.executable, "-c", "print('{}')"],
            {"experiment_id": "invalid"}, mode="count", cases=2)
        self.assertEqual(invalid["coverage"], 0)
        self.assertEqual(invalid["mean_excess_brier_with_missing_penalty"], 2.0)
        self.assertEqual(invalid["mean_policy_regret_with_missing_penalty"], 20)
        self.assertEqual(invalid["model_calls_attempted"], 2)
        script = (
            "import json,sys;"
            "from examples.finance_revision_fixture_adapter import reply;"
            "p=json.load(sys.stdin)['packet'];"
            "x=reply(p) if p['phase']=='initial' else "
            "{'posterior':[0.0,0.0,1.0],'action':'trade_now'};"
            "print(json.dumps(x))"
        )
        rejected = run_financial_revision(
            [sys.executable, "-c", script],
            {"experiment_id": "bad-action"}, mode="bitmap", cases=1)
        self.assertEqual(rejected["coverage"], 0)
        self.assertEqual(rejected["model_calls_attempted"], 2)
        self.assertEqual(rejected["rows"][0]["status"], "invalid_forecast_or_action")

    def test_response_rejects_side_channels_and_invalid_action(self):
        world = fixture(0)
        initial = reference_reply(packet(world, "bitmap", "price_feed", "initial"))
        self.assertEqual(parse_response(initial, "initial", world, "bitmap")[2],
                         world.old_mask)
        for bad in (
            {**initial, "reasoning": "hidden history"},
            {**initial, "action": "execute_trade"},
            {**initial, "memory": True},
            {**initial, "posterior": [math.nan, 0, 1]},
        ):
            with self.assertRaises((ValueError, TypeError, KeyError)):
                parse_response(bad, "initial", world, "bitmap")
        with self.assertRaises(ValueError):
            parse_response({"posterior": [1, 0, 0], "action": "halt_and_escalate",
                            "memory": 0}, "update")


class LocalRevisionModelTransportTests(unittest.TestCase):
    def test_financial_update_is_single_turn_and_model_schema(self):
        world = fixture(0)
        initial = packet(world, "bitmap", "price_feed", "initial")
        update = packet(world, "bitmap", "price_feed", "update", world.old_mask)
        server = FakeServer()
        server.completion = reference_reply(initial)
        live = adapter(server)
        self.assertEqual(live.infer_revision(initial, [])["memory"], world.old_mask)
        server.completion = reference_reply(update)
        self.assertEqual(live.infer_revision(update, [])["action"],
                         optimal_action(world.exact_full, "price_feed"))
        request = json.loads(server.requests[-1].data)
        self.assertEqual(len(request["messages"]), 2)
        supplied = json.loads(request["messages"][1]["content"])
        self.assertEqual(supplied, {"packet": update})
        self.assertNotIn("old", json.dumps(supplied).replace('"old": "not_replayed"', ""))
        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertEqual(set(request["response_format"]["schema"]["required"]),
                         {"posterior", "action"})
        self.assertFalse(request["cache_prompt"])
        self.assertEqual(request["lora"], [{"id": 0, "scale": 1.0}])
        self.assertNotIn("tools", request)
        with self.assertRaises(ValueError):
            live.infer_revision(update, [{"history": "smuggled"}])
        poisoned = dict(update)
        poisoned["old"] = [{"slot": 0, "match": 1}]
        with self.assertRaises(ValueError):
            live.infer_revision(poisoned, [])

    def test_truncation_tool_call_and_invalid_response_fail_closed(self):
        world = fixture(0)
        first = packet(world, "count", "collateral", "initial")
        server = FakeServer()
        live = adapter(server)
        server.completion = reference_reply(first)
        server.finish = "length"
        with self.assertRaisesRegex(ValueError, "truncated"):
            live.infer_revision(first, [])
        server.finish = "stop"
        server.tool_calls = [{"id": "unwanted"}]
        with self.assertRaisesRegex(ValueError, "tool calls"):
            live.infer_revision(first, [])
        server.tool_calls = None
        server.completion = {**reference_reply(first), "extra_state": "smuggled"}
        with self.assertRaises(ValueError):
            live.infer_revision(first, [])

    def test_remote_transport_is_rejected(self):
        settings = config()
        settings["endpoint"] = "https://untrusted.invalid/v1"
        with self.assertRaises(ValueError):
            RevisionLlamaCppAdapter(settings, verify=False)


if __name__ == "__main__":
    unittest.main()
