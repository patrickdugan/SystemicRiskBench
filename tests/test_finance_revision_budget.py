"""Budget gates and cost denominators using mocked, synthetic adapter calls."""
from copy import deepcopy
import json
import math
import unittest
from unittest.mock import patch

from examples.finance_revision_fixture_adapter import reply as oracle_reply
from systemic_risk_bench.agent_revision import fixture
from systemic_risk_bench.finance_revision import run_financial_revision
from systemic_risk_bench.finance_revision_panels import build_manifest
from systemic_risk_bench.revision_receipts import PREFIX, SCHEMA, parse_receipt
from systemic_risk_bench.runner import sha


def _model_registration(manifest):
    return {
        "experiment_id": "unit-test-registered-pilot", "evaluation_kind": "model",
        "status": "registered", "panel": "pilot",
        "panel_manifest_sha256": manifest["manifest_sha256"],
        "preregistered_cases": 6, "max_calls_per_arm": 12,
        "memory_arms": ["count", "bitmap"], "max_wall_seconds_per_arm": 10,
        "base_sha256": "a" * 64, "checkpoint_sha256": "b" * 64,
        "model_alias": "test", "max_output_tokens_per_call": 1024,
        "temperature": 0, "seed": 0,
        "inference_server": "operator_owned_loopback_llama_cpp",
    }


def _receipt(packet, *, response=None, host_status="ok", telemetry=False,
             input_tokens=None, output_tokens=None, elapsed=0.25):
    if host_status == "ok" and response is None:
        response = oracle_reply(packet)
    result = {
        "status": host_status, "exit_code": 0 if host_status == "ok" else 1,
        "response": response, "wall_seconds": 0.25,
        "stdout_sha256": sha(response), "stderr_tail": "",
        "input_tokens": None, "output_tokens": None,
        "telemetry_status": "missing", "adapter_telemetry": None,
    }
    if telemetry:
        success = host_status == "ok"
        receipt = {
            "schema": SCHEMA, "packet_sha256": sha(packet),
            "response_sha256": sha(response) if success else None,
            "phase": packet["phase"],
            "status": "ok" if success else "invalid_response",
            "elapsed_seconds": elapsed, "requested_model": "test",
            "resolved_model": "test",
            "usage": {
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "total_tokens": (input_tokens + output_tokens
                                 if input_tokens is not None and output_tokens is not None
                                 else None),
            },
            "sampling": {"temperature": 0, "seed": 0, "max_tokens": 1024},
            "identity": {
                "base_sha256": "a" * 64, "adapter_sha256": "b" * 64,
                "adapter_id": 0, "adapter_scale": 1.0,
                "local_artifacts_verified": False,
                "verification": "local_files_plus_server_alias_and_adapter_metadata",
            },
            "isolation": {"server_reset_verified": False, "physical_memory_enforced": False},
            "error_code": None if success else "response_contract",
        }
        parsed, status, error = parse_receipt(
            PREFIX + json.dumps(receipt), packet, response, host_status)
        if status != "valid":
            raise AssertionError(f"test receipt is invalid: {error}")
        result.update(telemetry_status=status, adapter_telemetry=parsed,
                      input_tokens=input_tokens, output_tokens=output_tokens)
    return result


class FinancialRevisionBudgetTests(unittest.TestCase):
    def test_registration_mismatches_stop_before_any_adapter_call(self):
        manifest = build_manifest()
        registered = _model_registration(manifest)
        mutations = (
            ("preregistered_cases", 5), ("preregistered_cases", True),
            ("max_calls_per_arm", True), ("max_calls_per_arm", 11),
            ("max_calls_per_arm", 13),
            ("panel", "natural"), ("panel_manifest_sha256", "0" * 64),
            ("memory_arms", ["count"]), ("memory_arms", ["bitmap", "count"]),
            ("max_wall_seconds_per_arm", 0), ("max_wall_seconds_per_arm", True),
            ("max_wall_seconds_per_arm", math.nan),
            ("max_wall_seconds_per_arm", math.inf),
        )
        with patch("systemic_risk_bench.finance_revision.execute") as execute:
            for key, value in mutations:
                changed = deepcopy(registered)
                changed[key] = value
                with self.subTest(field=key, value=value), self.assertRaises(ValueError):
                    run_financial_revision(["test-only"], changed, mode="count",
                                           panel="pilot", manifest=manifest)
            with self.assertRaises(ValueError):
                run_financial_revision(["test-only"], registered,
                                       mode="count", cases=6)
            execute.assert_not_called()

    def test_deadline_between_stages_retains_all_roots_and_stops_calls(self):
        manifest = build_manifest()
        registered = _model_registration(manifest)
        registered["max_wall_seconds_per_arm"] = 1.0
        clock = [100.0]

        def monotonic():
            value = clock[0]
            clock[0] += 0.25
            return value

        def execute(argv, packet, previous, timeout, experiment):
            self.assertEqual(packet["phase"], "initial")
            self.assertEqual(previous, [])
            self.assertAlmostEqual(timeout, 0.75)
            clock[0] = 102.0
            return _receipt(packet, telemetry=True, input_tokens=10, output_tokens=4)

        with patch("systemic_risk_bench.finance_revision.time.monotonic",
                   side_effect=monotonic), patch(
                       "systemic_risk_bench.finance_revision.execute",
                       side_effect=execute,
                   ) as mocked:
            report = run_financial_revision(["test-only"], registered,
                                            mode="count", panel="pilot", manifest=manifest)
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(report["n_cases"], 6)
        self.assertEqual(len(report["rows"]), 6)
        self.assertEqual(report["n_scored"], 0)
        self.assertEqual(report["n_initial_valid"], 1)
        self.assertEqual(report["coverage"], 0)
        self.assertEqual(report["mean_excess_brier_with_missing_penalty"], 2.0)
        self.assertEqual(report["mean_policy_regret_with_missing_penalty"], 20.0)
        self.assertEqual(report["mean_policy_regret_vs_full_with_missing_penalty"], 20.0)
        self.assertEqual(report["action_accuracy_with_missing_penalty"], 0)
        self.assertEqual(report["adapter_calls_attempted"], 1)
        self.assertEqual(report["model_calls_attempted"], 1)
        self.assertEqual(report["n_stages_skipped_for_budget"], 6)
        self.assertEqual(report["rows"][0]["status"], "update_budget_exhausted")
        self.assertEqual(report["rows"][0]["update_receipt"]["status"], "budget_exhausted")
        for row in report["rows"][1:]:
            self.assertEqual(row["initial_error"], "budget_exhausted")
            self.assertIsNone(row["update_receipt"])
        for family in report["family_summaries"].values():
            self.assertEqual(family["n_cases"], 2)
            self.assertEqual(family["coverage"], 0)
        costs = report["inference_costs"]
        self.assertEqual(costs["adapter_calls_attempted"], 1)
        self.assertEqual(costs["telemetry_coverage"], 1.0)
        self.assertEqual(costs["input_tokens_all_calls"], 10)
        self.assertEqual(costs["output_tokens_all_calls"], 4)
        self.assertIs(report["model_evaluation_claim"], False)

    def test_partial_receipts_preserve_observed_costs_and_unknown_totals(self):
        calls = [0]

        def execute(argv, packet, previous, timeout, experiment):
            index = calls[0]
            calls[0] += 1
            if index == 0:
                return _receipt(packet, telemetry=True, input_tokens=10,
                                output_tokens=2, elapsed=0.25)
            if index == 1:
                return _receipt(packet, telemetry=True, input_tokens=None,
                                output_tokens=3, elapsed=0.5)
            receipt = _receipt(packet)
            if index == 3:
                receipt.update(telemetry_status="invalid", input_tokens=999,
                               output_tokens=999)
            return receipt

        with patch("systemic_risk_bench.finance_revision.execute", side_effect=execute):
            report = run_financial_revision(
                ["test-only"], {"experiment_id": "partial-costs-fixture"},
                mode="bitmap", cases=2)
        self.assertEqual(report["coverage"], 1.0)
        self.assertEqual(report["host_measured_wall_seconds"], 1.0)
        costs = report["inference_costs"]
        self.assertEqual(costs["adapter_calls_attempted"], 4)
        self.assertEqual(costs["calls_with_valid_telemetry"], 2)
        self.assertEqual(costs["calls_with_invalid_telemetry"], 1)
        self.assertEqual(costs["telemetry_coverage"], 0.5)
        self.assertEqual(costs["input_token_coverage"], 0.25)
        self.assertEqual(costs["output_token_coverage"], 0.5)
        self.assertEqual(costs["input_tokens_observed"], 10)
        self.assertEqual(costs["output_tokens_observed"], 5)
        self.assertIsNone(costs["input_tokens_all_calls"])
        self.assertIsNone(costs["output_tokens_all_calls"])
        self.assertEqual(costs["adapter_reported_inference_seconds_observed"], 0.75)
        self.assertIsNone(costs["adapter_reported_inference_seconds_all_calls"])
        self.assertEqual(costs["failed_calls_with_usage"], 0)
        self.assertIs(costs["independent_runtime_attestation"], False)

    def test_zero_counters_and_missing_components_have_distinct_coverage(self):
        def execute(argv, packet, previous, timeout, experiment):
            initial = packet["phase"] == "initial"
            return _receipt(packet, telemetry=True,
                            input_tokens=0 if initial else 7,
                            output_tokens=0 if initial else None,
                            elapsed=0.0 if initial else 0.25)

        with patch("systemic_risk_bench.finance_revision.execute", side_effect=execute):
            report = run_financial_revision(
                ["test-only"], {"experiment_id": "known-zero-costs-fixture"},
                mode="count", cases=1)
        costs = report["inference_costs"]
        self.assertEqual(costs["telemetry_coverage"], 1.0)
        self.assertEqual(costs["input_token_coverage"], 1.0)
        self.assertEqual(costs["output_token_coverage"], 0.5)
        self.assertEqual(costs["input_tokens_observed"], 7)
        self.assertEqual(costs["input_tokens_all_calls"], 7)
        self.assertEqual(costs["output_tokens_observed"], 0)
        self.assertIsNone(costs["output_tokens_all_calls"])
        self.assertEqual(costs["adapter_reported_inference_seconds_all_calls"], 0.25)

    def test_failed_inference_costs_survive_initial_and_update_failures(self):
        failing_id = fixture(0).case_id
        for phase in ("initial", "update"):
            def execute(argv, packet, previous, timeout, experiment):
                failing = packet["case_id"] == failing_id and packet["phase"] == phase
                return _receipt(
                    packet, host_status="adapter_error" if failing else "ok",
                    telemetry=True, input_tokens=17 if failing else 11,
                    output_tokens=7 if failing else 3)

            with self.subTest(phase=phase), patch(
                    "systemic_risk_bench.finance_revision.execute", side_effect=execute):
                report = run_financial_revision(
                    ["test-only"], {"experiment_id": "failed-costs-fixture"},
                    mode="bitmap", cases=2)
            n_calls = 3 if phase == "initial" else 4
            self.assertEqual(report["n_scored"], 1)
            self.assertEqual(report["coverage"], 0.5)
            self.assertEqual(report["mean_policy_regret_with_missing_penalty"], 10.0)
            costs = report["inference_costs"]
            self.assertEqual(costs["adapter_calls_attempted"], n_calls)
            self.assertEqual(costs["calls_with_valid_telemetry"], n_calls)
            self.assertEqual(costs["telemetry_coverage"], 1.0)
            self.assertEqual(costs["failed_calls_with_usage"], 1)
            self.assertEqual(costs["input_tokens_observed"], 17 + 11 * (n_calls - 1))
            self.assertEqual(costs["input_tokens_all_calls"], 17 + 11 * (n_calls - 1))
            self.assertEqual(costs["output_tokens_observed"], 7 + 3 * (n_calls - 1))
            self.assertEqual(costs["output_tokens_all_calls"], 7 + 3 * (n_calls - 1))
            self.assertEqual(costs["adapter_reported_inference_seconds_all_calls"],
                             0.25 * n_calls)

    def test_fixture_calls_without_telemetry_keep_model_costs_unknown(self):
        def execute(argv, packet, previous, timeout, experiment):
            return _receipt(packet)

        with patch("systemic_risk_bench.finance_revision.execute", side_effect=execute):
            report = run_financial_revision(
                ["test-only"], {"experiment_id": "fixture-without-model-telemetry"},
                mode="count", cases=2)
        self.assertIs(report["model_evaluation_claim"], False)
        self.assertIsNone(report["max_wall_seconds_per_arm"])
        costs = report["inference_costs"]
        self.assertEqual(costs["adapter_calls_attempted"], 4)
        self.assertEqual(costs["calls_with_valid_telemetry"], 0)
        self.assertEqual(costs["calls_with_invalid_telemetry"], 0)
        for key in ("telemetry_coverage", "input_token_coverage", "output_token_coverage"):
            self.assertEqual(costs[key], 0.0)
        for key in ("input_tokens_observed", "output_tokens_observed",
                    "input_tokens_all_calls", "output_tokens_all_calls",
                    "adapter_reported_inference_seconds_observed",
                    "adapter_reported_inference_seconds_all_calls"):
            self.assertIsNone(costs[key])
        self.assertEqual(costs["failed_calls_with_usage"], 0)


if __name__ == "__main__":
    unittest.main()
