"""Telemetry integrity and real-subprocess retention for revision experiments."""
import copy
import json
import sys
import unittest
from unittest.mock import patch

from examples.finance_revision_fixture_adapter import reply
from systemic_risk_bench.agent_revision import fixture
from systemic_risk_bench.finance_revision import packet
from systemic_risk_bench.revision_receipts import (
    PREFIX, SCHEMA, canonical_sha, parse_receipt, validate_registered_experiment,
)
from systemic_risk_bench.runner import execute


def telemetry(for_packet, response):
    return {
        "schema": SCHEMA, "packet_sha256": canonical_sha(for_packet),
        "response_sha256": canonical_sha(response), "phase": for_packet["phase"],
        "status": "ok", "elapsed_seconds": 0.25, "requested_model": "bitagent-test",
        "resolved_model": "bitagent-test",
        "usage": {"input_tokens": 25, "output_tokens": 8, "total_tokens": 33},
        "sampling": {"temperature": 0, "seed": 0, "max_tokens": 96},
        "identity": {"base_sha256": "a" * 64, "adapter_sha256": "b" * 64,
                     "adapter_id": 0, "adapter_scale": 1.0,
                     "local_artifacts_verified": False,
                     "verification": "local_files_plus_server_alias_and_adapter_metadata"},
        "isolation": {"server_reset_verified": False, "physical_memory_enforced": False},
        "error_code": None,
    }


class RevisionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.packet = packet(fixture(0), "count", "price_feed", "initial")
        self.response = reply(self.packet)
        self.receipt = telemetry(self.packet, self.response)

    def parse(self, value, **kwargs):
        return parse_receipt(PREFIX + json.dumps(value), self.packet,
                             kwargs.get("response", self.response),
                             kwargs.get("host_status", "ok"))

    def test_real_subprocess_retains_receipt_before_stderr_truncation(self):
        script = (
            "import json,sys;"
            "request=json.load(sys.stdin);"
            "assert 'rationale' not in request['instruction'];"
            f"receipt=json.loads({json.dumps(json.dumps(self.receipt))});"
            f"response=json.loads({json.dumps(json.dumps(self.response))});"
            f"print({PREFIX!r}+json.dumps(receipt),file=sys.stderr);"
            "print('diagnostic '*500,file=sys.stderr);"
            "print(json.dumps(response))"
        )
        result = execute([sys.executable, "-c", script], self.packet, [], 10)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["telemetry_status"], "valid")
        self.assertEqual(result["input_tokens"], 25)
        self.assertEqual(result["output_tokens"], 8)
        self.assertEqual(result["adapter_telemetry"]["usage"]["total_tokens"], 33)
        self.assertNotIn(PREFIX, result["stderr_tail"])
        self.assertNotIn("diagnostic", json.dumps(result["response"]))

    def test_success_failure_and_unknown_counters_remain_distinct(self):
        receipt, status, error = self.parse(self.receipt)
        self.assertEqual((status, error), ("valid", None))
        self.assertEqual(receipt, self.receipt)
        unknown = copy.deepcopy(self.receipt)
        unknown["usage"] = {key: None for key in unknown["usage"]}
        self.assertEqual(self.parse(unknown)[0]["usage"], unknown["usage"])
        failed = copy.deepcopy(self.receipt)
        failed.update(status="invalid_response", error_code="response_contract",
                      response_sha256=None)
        parsed = self.parse(failed, response=None, host_status="adapter_error")
        self.assertEqual(parsed[1], "valid")
        self.assertEqual(parsed[0]["usage"]["output_tokens"], 8)
        self.assertEqual(self.parse(failed)[1], "invalid")
        self.assertEqual(self.parse(self.receipt, response=None,
                                   host_status="adapter_error")[1], "invalid")

    def test_replay_duplicate_and_extra_field_receipts_are_rejected(self):
        for field, replacement in (("packet_sha256", "c" * 64),
                                   ("response_sha256", "d" * 64),
                                   ("phase", "update")):
            changed = {**self.receipt, field: replacement}
            with self.subTest(field=field):
                self.assertEqual(self.parse(changed)[1], "invalid")
        line = PREFIX + json.dumps(self.receipt)
        self.assertEqual(parse_receipt(line + "\n" + line, self.packet,
                                       self.response, "ok")[1], "invalid")
        changed = {**self.receipt, "local_path": "/private/model.gguf"}
        self.assertEqual(self.parse(changed)[1], "invalid")
        for parent, key, value in (("identity", "path", "/private/model.gguf"),
                                   ("isolation", "server_reset_verified", True)):
            changed = copy.deepcopy(self.receipt)
            changed[parent][key] = value
            self.assertEqual(self.parse(changed)[1], "invalid")

    def test_token_counters_reject_bool_negative_fraction_and_false_total(self):
        for value in (True, -1, 2.5, "8"):
            changed = copy.deepcopy(self.receipt)
            changed["usage"]["output_tokens"] = value
            with self.subTest(value=value):
                self.assertEqual(self.parse(changed)[1], "invalid")
        changed = copy.deepcopy(self.receipt)
        changed["usage"]["total_tokens"] = 34
        self.assertEqual(self.parse(changed)[1], "invalid")
        changed = copy.deepcopy(self.receipt)
        changed["usage"]["total_tokens"] = None
        self.assertEqual(self.parse(changed)[1], "valid")
        changed["usage"].update(total_tokens=2, output_tokens=None)
        self.assertEqual(self.parse(changed)[1], "invalid")
        changed = copy.deepcopy(self.receipt)
        changed["sampling"]["max_tokens"] = 7
        self.assertEqual(self.parse(changed)[1], "invalid")

    def test_missing_and_invalid_telemetry_never_become_zero_cost(self):
        for stderr, expected in (("", "missing"), (PREFIX + "{}", "invalid")):
            with self.subTest(expected=expected):
                process = type("Completed", (), {"stdout": json.dumps(self.response),
                    "stderr": stderr, "returncode": 0})()
                with patch("systemic_risk_bench.runner.subprocess.run", return_value=process):
                    result = execute(["unused"], self.packet, [], 10)
                self.assertEqual(result["telemetry_status"], expected)
                self.assertIsNone(result["input_tokens"])
                self.assertIsNone(result["output_tokens"])
                self.assertIsNone(result["adapter_telemetry"])

    def test_failed_completion_costs_survive_nonzero_adapter_exit(self):
        failed = {**self.receipt, "status": "invalid_response",
                  "error_code": "response_contract", "response_sha256": None}
        process = type("Completed", (), {"stdout": "", "returncode": 1,
            "stderr": PREFIX + json.dumps(failed) + "\ncompletion truncated"})()
        with patch("systemic_risk_bench.runner.subprocess.run", return_value=process):
            result = execute(["unused"], self.packet, [], 10)
        self.assertEqual(result["status"], "adapter_error")
        self.assertEqual(result["telemetry_status"], "valid")
        self.assertEqual(result["output_tokens"], 8)
        self.assertIsNone(result["response"])


class RevisionRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.packet = packet(fixture(0), "count", "price_feed", "initial")
        self.config = {"base": {"sha256": "a" * 64},
                       "adapter": {"sha256": "b" * 64},
                       "model_alias": "bitagent-test", "max_tokens": 96,
                       "temperature": 0, "seed": 0}
        self.experiment = {
            "experiment_id": "SRB-REV-03-local-pilot", "evaluation_kind": "model",
            "base_sha256": "a" * 64, "checkpoint_sha256": "b" * 64,
            "model_alias": "bitagent-test", "max_output_tokens_per_call": 96,
            "temperature": 0, "seed": 0, "memory_arms": ["count", "bitmap"],
            "max_calls_per_arm": 12, "preregistered_cases": 6,
            "inference_server": "operator_owned_loopback_llama_cpp",
        }

    def test_registration_binds_sampling_checkpoint_and_per_arm_budget(self):
        validate_registered_experiment(self.config, self.experiment, self.packet)
        for field, value in (("max_output_tokens_per_call", 1024), ("seed", 1),
                             ("checkpoint_sha256", "c" * 64),
                             ("base_sha256", "d" * 64), ("model_alias", "other"),
                             ("max_calls_per_arm", 11), ("memory_arms", ["count"]),
                             ("status", "template_no_model_calls_run")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_registered_experiment(self.config, {**self.experiment, field: value}, self.packet)
        validate_registered_experiment(self.config, {"experiment_id": "legacy-fixture"}, self.packet)

    def test_production_model_intent_cannot_be_omitted(self):
        for experiment in (None, {"experiment_id": "legacy-fixture"},
                           {key: value for key, value in self.experiment.items()
                            if key != "evaluation_kind"}):
            with self.subTest(experiment=experiment), self.assertRaisesRegex(
                    ValueError, "explicit model registration"):
                validate_registered_experiment(self.config, experiment, self.packet,
                                               require_model=True)


if __name__ == "__main__":
    unittest.main()
