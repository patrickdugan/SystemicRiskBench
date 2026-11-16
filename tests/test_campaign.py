import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from systemic_risk_bench.campaign import output_schema, summarize, tasks_for, token_totals
from systemic_risk_bench.codex_transport import CodexTransport
from systemic_risk_bench.webhooks import ResultWebhook


class WebhookTests(unittest.TestCase):
    def test_signed_delivery_and_duplicate_deduplication(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            with ResultWebhook(directory) as sink:
                event = {"event_id": "a"*64, "event": "rollout.completed"}
                sink.emit(event)
                sink.emit(event)
                self.assertEqual(sink.received, 1)
                self.assertEqual(json.loads((Path(directory)/("a"*64+".json")).read_text()), event)

    def test_unsigned_payload_is_rejected_and_not_written(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            with ResultWebhook(directory) as sink:
                request = Request(sink.url, data=b'{"event_id":"invalid"}', method="POST")
                with self.assertRaises(HTTPError) as error:
                    urlopen(request, timeout=5)
                self.assertEqual(error.exception.code, 401)
                self.assertEqual(list(Path(directory).glob("*.json")), [])


class CampaignTests(unittest.TestCase):
    def test_frozen_history_contains_only_visible_packets(self):
        tasks = tasks_for("history", ["tf_1982_latam"])
        self.assertEqual(len(tasks), 2)
        self.assertEqual(len(tasks[0]["packet"]["visible_stages"]), 1)
        self.assertEqual(len(tasks[1]["packet"]["visible_stages"]), 2)
        for task in tasks:
            self.assertNotIn("outcome", task["packet"])
            self.assertNotIn("sources", task["packet"])

    def test_quant_schema_has_question_fields_without_answers(self):
        task = tasks_for("quant")[0]
        schema = output_schema(task["packet"], "quant")
        self.assertEqual(schema["properties"]["estimates"]["required"], ["cva"])
        self.assertNotIn("23400", json.dumps(schema))

    def test_usage_adds_last_turn_not_cumulative_total(self):
        receipts = [{"usage": {"last": {"totalTokens": 5}, "total": {"totalTokens": 20}}},
                    {"usage": {"last": {"totalTokens": 7}, "total": {"totalTokens": 40}}}]
        self.assertEqual(token_totals(receipts)["totalTokens"], 12)

    def test_incomplete_task_denominator_and_unaudited_reasoning(self):
        tasks = tasks_for("quant")
        receipt = {"task_index": 0, "track": "quant", "case_id": "q-cva-term", "status": "ok",
                   "response": {"estimates": {"cva": 23400}}, "wall_seconds": 1, "usage": None}
        result = summarize([receipt], tasks)
        self.assertEqual(result["expected_calls"], 6)
        self.assertAlmostEqual(result["numeric"]["numeric_micro_accuracy"], 1/13)
        self.assertIsNone(result["reasoning_score"])


class FakeTransport(CodexTransport):
    def __init__(self, text):
        self.cwd = str(Path(__file__).parent.resolve())
        self.timeout = 1
        self.text = text
        self.sent = []
        self.events = [
            {"method": "thread/tokenUsage/updated", "params": {"threadId": "test-thread", "tokenUsage": {"last": {"totalTokens": 8}}}},
            {"method": "item/completed", "params": {"threadId": "test-thread", "item": {"type": "agentMessage", "text": text}}},
            {"method": "turn/completed", "params": {"threadId": "test-thread", "turn": {"id": "test-turn", "status": "completed"}}}]

    def request(self, method, params, timeout=None):
        self.sent.append((method, params))
        if method == "thread/start":
            return {"thread": {"id": "test-thread"}, "model": params["model"], "instructionSources": []}
        return {"turn": {"id": "test-turn"}}

    def receive(self, deadline):
        return self.events.pop(0)


class TransportTests(unittest.TestCase):
    def test_explicit_effort_ephemeral_no_fallback_and_prior_history(self):
        transport = FakeTransport('{"estimates":{"cva":23400}}')
        result = transport.infer({"question": "visible"}, [{"response": "previous"}], "gpt-6.1-sol", "high", {})
        self.assertEqual(result["status"], "ok")
        start = transport.sent[0][1]
        self.assertTrue(start["ephemeral"])
        self.assertFalse(start["allowProviderModelFallback"])
        self.assertEqual(start["environments"], [])
        self.assertEqual(transport.sent[1][1]["effort"], "high")
        self.assertIn("previous", transport.sent[1][1]["input"][0]["text"])

    def test_duplicate_model_json_is_not_accepted(self):
        result = FakeTransport('{"a":1,"a":2}').infer({}, [], "m", "low", {})
        self.assertEqual(result["status"], "model_error")


if __name__ == "__main__":
    unittest.main()
