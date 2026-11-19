"""Source-only finite-choice and independent protocol tests for SRB-LOMBARD-02."""
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import urlparse

from adapters.lombard_feedback_llamacpp import (
    LombardFeedbackLlamaCppAdapter, schema,
)
from examples.lombard_feedback_reference_adapter import reply as oracle_reply
from systemic_risk_bench.content_suite import content_case, content_packet
from systemic_risk_bench.lombard_feedback import (
    OUTPUTS, SCHEMA, analysis, best_choice, exact_funding_rate, public_cases,
    quote, run_adapter, score_responses, validate_config, validate_response,
)
from systemic_risk_bench.scoring import read_json

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs/lombard-feedback-v1.json"
ALT = ROOT / "configs/lombard-feedback-charter-control.json"
SCALE = ROOT / "configs/lombard-feedback-60bp-scale.json"


def cfg(path=CONFIG):
    return read_json(path)


class FakeServer:
    def __init__(self, result=None):
        self.requests = []
        self.answer = result
        self.finish = "stop"
        self.tool_calls = None

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        path = urlparse(request.full_url).path
        if path == "/v1/models":
            output = {"data": [{"id": "bitagent-test"}]}
        elif path == "/lora-adapters":
            output = [{"id": 0, "path": "adapter.gguf", "scale": 1.0}]
        elif path == "/v1/chat/completions":
            output = {"model": "bitagent-test", "choices": [{
                "finish_reason": self.finish,
                "message": {"content": json.dumps(self.answer),
                            "tool_calls": self.tool_calls},
            }], "usage": {"prompt_tokens": 91, "completion_tokens": 11}}
        else:
            raise AssertionError(path)
        return io.BytesIO(json.dumps(output).encode())


def local_adapter(server):
    local = {"endpoint": "http://127.0.0.1:8873/v1",
             "model_alias": "bitagent-test",
             "gpu_not_before_utc": "2026-11-16T07:35:22+00:00",
             "base": {"path": "base.gguf", "bytes": 4, "sha256": "base"},
             "adapter": {"path": "adapter.gguf", "bytes": 4,
                         "sha256": "adapter", "id": 0, "scale": 1},
             "timeout_seconds": 10}
    return LombardFeedbackLlamaCppAdapter(
        local, opener=server, verify=False,
        clock=lambda: datetime(2026, 11, 19, tzinfo=timezone.utc))


class FundingFeedbackTests(unittest.TestCase):
    def test_fair_bank_debt_pricing_and_guarantee_monotonic(self):
        for pd in (0, .02, .08, .3):
            rates = [exact_funding_rate(
                risk_free=.025, default_probability=pd, recovery=.35, guarantee=g)
                for g in (0, .2, .5, .8, 1)]
            self.assertEqual(rates, sorted(rates, reverse=True))
            for g, rate in zip((0, .2, .5, .8, 1), rates):
                expected_payment = (1+rate)*(1-pd*(1-.35)*(1-g))
                self.assertAlmostEqual(expected_payment, 1.025, places=12)
        for value in (True, -1, math.nan, 2):
            with self.assertRaises(ValueError):
                exact_funding_rate(risk_free=.025, default_probability=.08,
                                   recovery=.35, guarantee=value)

    def test_registered_protocol_completeness_and_bad_parameters(self):
        config = cfg()
        self.assertEqual(validate_config(config), config)
        self.assertEqual(len(public_cases(config)), 5)
        for bad, value in (
            ("pass_through", True), ("pass_through", 1.2),
            ("bank_default_probability", -0.1), ("debt_step", False),
            ("max_merchant_debt", 12345), ("guarantee_grid", [.5, 0]),
            ("guarantee_grid", [0, 0]), ("risk_free_rate", math.inf)):
            copy = deepcopy(config)
            copy[bad] = value
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_config(copy)
        copy = deepcopy(config)
        copy["projects"][0]["failure_slope_per_debt_to_equity"] = .3
        with self.assertRaises(ValueError):
            validate_config(copy)

    def test_lender_and_merchant_expected_cashflow_identities(self):
        c = cfg()
        for g in c["guarantee_grid"]:
            for project in c["projects"]:
                for d in range(0, 40001, 5000):
                    row = quote(c, project, d, g)
                    bank_den = 1-row["bank_default_probability"]*(
                        1-c["bank_recovery"])*(1-g)
                    self.assertAlmostEqual(
                        (1+row["backed_bank_funding_rate"])*bank_den,
                        1+c["risk_free_rate"], places=12)
                    credit_den = 1-row["merchant_failure_probability"]*(
                        1-c["merchant_recovery"])
                    expected_bank_return = (1+row["merchant_loan_rate"])*credit_den
                    passbank = row["unbacked_bank_funding_rate"] - c["pass_through"]*(
                        row["unbacked_bank_funding_rate"]-row["backed_bank_funding_rate"])
                    self.assertAlmostEqual(
                        expected_bank_return, 1+passbank+c["origination_margin"],
                        places=12)
                    self.assertAlmostEqual(row["merchant_expected_equity_profit"],
                        (1-row["merchant_failure_probability"])*
                        row["merchant_success_equity"]-c["merchant_equity"], places=8)
                    self.assertGreaterEqual(row["merchant_success_equity"], 0)
                    if g == 0:
                        self.assertEqual(row["expected_treasury_bank_debt_guarantee"], 0)

    def test_main_comparative_statics_and_controls(self):
        c = cfg()
        report = analysis(c)
        self.assertEqual(report["n_cases"], 5)
        self.assertFalse(report["empirical_identification_claim"])
        self.assertTrue(report["physical_and_pricing_default_probabilities_assumed_equal"])
        self.assertFalse(report["physical_measure_calibration_claim"])
        self.assertFalse(report["general_equilibrium_claim"])
        self.assertTrue(report["no_bank_equity_recap_or_central_bank_credit_in_this_model"])
        rows = report["rows"]
        self.assertEqual([r["guarantee"] for r in rows], c["guarantee_grid"])
        self.assertEqual(rows[0]["baseline"]["expected_treasury_bank_debt_guarantee"], 0)
        self.assertLess(rows[0]["baseline"]["borrowed"], rows[-1]["baseline"]["borrowed"])
        self.assertLess(rows[0]["baseline"]["merchant_failure_probability"],
                        rows[-1]["baseline"]["merchant_failure_probability"])
        self.assertLess(rows[-1]["baseline"]["backed_bank_funding_rate"],
                        rows[-1]["baseline"]["unbacked_bank_funding_rate"])
        for row in rows:
            self.assertEqual(
                (row["no_pass_through"]["project"], row["no_pass_through"]["borrowed"]),
                (rows[0]["no_pass_through"]["project"],
                 rows[0]["no_pass_through"]["borrowed"]))
            self.assertEqual(
                (row["zero_bank_default_probability"]["project"],
                 row["zero_bank_default_probability"]["borrowed"]),
                (rows[0]["zero_bank_default_probability"]["project"],
                 rows[0]["zero_bank_default_probability"]["borrowed"]))
        self.assertGreater(
            rows[-1]["baseline"]["expected_treasury_bank_debt_guarantee"], 0)

    def test_risk_mix_response_direction_is_fixture_dependent(self):
        c = cfg(ALT)
        report = analysis(c)
        start = report["rows"][0]["baseline"]
        end = report["rows"][-1]["baseline"]
        self.assertLess(start["borrowed"], end["borrowed"])
        self.assertNotEqual(start["project"], end["project"])
        # This alternative is deliberately capable of greater credit use
        # and lower project-default risk at the new optimum.
        self.assertGreater(start["merchant_failure_probability"],
                           end["merchant_failure_probability"])

    def test_illustrative_60bp_funding_scale_changes_less_credit(self):
        scaled = analysis(cfg(SCALE))
        start = scaled["rows"][0]["baseline"]
        end = scaled["rows"][-1]["baseline"]
        delta_rate = start["unbacked_bank_funding_rate"] - end["backed_bank_funding_rate"]
        self.assertGreater(delta_rate, .005)
        self.assertLess(delta_rate, .007)
        self.assertEqual(start["project"], "prudent")
        self.assertEqual(end["project"], "prudent")
        self.assertEqual(start["borrowed"], 20000)
        self.assertEqual(end["borrowed"], 25000)
        self.assertEqual(start["expected_treasury_bank_debt_guarantee"], 0)
        self.assertGreater(end["expected_treasury_bank_debt_guarantee"], 0)
        self.assertFalse(scaled["empirical_identification_claim"])
        # Fixed-project, fixed-debt quote falls with stronger guaranteed funding.
        project = next(p for p in cfg(SCALE)["projects"] if p["name"] == "prudent")
        fixed_rates = [quote(cfg(SCALE), project, 20000, g)["merchant_loan_rate"]
                       for g in cfg(SCALE)["guarantee_grid"]]
        self.assertEqual(fixed_rates, sorted(fixed_rates, reverse=True))
        # Chosen loan rate may rise when support induces a debt-ladder jump.
        at_quarter = scaled["rows"][1]["baseline"]
        self.assertGreater(at_quarter["merchant_loan_rate"], start["merchant_loan_rate"])
        self.assertGreater(at_quarter["borrowed"], start["borrowed"])

    def test_source_only_packets_and_content_case_leakage(self):
        c = cfg()
        q = public_cases(c)
        oracle = analysis(c)
        first = q[0]
        self.assertEqual(first["schema"], SCHEMA)
        self.assertEqual(first["guarantee"], 0)
        self.assertEqual(first["source_class"], "public_synthetic_problem")
        self.assertEqual(first["response_fields"], list(OUTPUTS))
        serialized = json.dumps(first)
        self.assertNotIn("baseline", serialized)
        self.assertNotIn("oracle", serialized)
        self.assertNotIn("merchant_expected_equity_profit", first)
        self.assertNotIn("n_cases", first)
        self.assertNotIn(oracle["config_sha256"][:0] + '"rows":', serialized)
        case = content_case("content_bagehot_guarantee_feedback")
        self.assertEqual(case["provenance"]["mode"], "synthetic_counterfactual")
        self.assertEqual(len(case["stages"]), 3)
        initial = json.dumps(content_packet(case["id"], 0))
        self.assertNotIn("outcome", content_packet(case["id"], 0))
        self.assertNotIn("2013/094", initial)

    def test_reference_adapter_subprocess_and_scoring_failures(self):
        c = cfg()
        cmd = [sys.executable, "-m", "examples.lombard_feedback_reference_adapter"]
        receipt = run_adapter(c, cmd, {"experiment_id": "registered-source-only"},
                              timeout=10)
        scored = receipt["score"]
        self.assertEqual(len(receipt["receipts"]), 5)
        self.assertEqual(scored["coverage"], 1)
        self.assertEqual(scored["field_accuracy_including_missing"], 1)
        self.assertEqual(scored["policy_accuracy_including_missing"], 1)
        self.assertFalse(receipt["model_evaluation_claim"])
        self.assertFalse(receipt["physical_memory_enforced"])
        self.assertEqual(oracle_reply(public_cases(c)[0])["borrowed"],
                         analysis(c)["rows"][0]["baseline"]["borrowed"])
        only_first = [{"id": public_cases(c)[0]["id"],
                       "response": oracle_reply(public_cases(c)[0])}]
        missing = score_responses(c, only_first)
        self.assertEqual(missing["coverage"], 1/5)
        self.assertEqual(missing["field_accuracy_including_missing"], 1/5)
        with self.assertRaises(ValueError):
            score_responses(c, only_first + only_first)
        with self.assertRaises(ValueError):
            score_responses(c, [{"id": "unknown", "response": None}])
        with self.assertRaises(ValueError):
            validate_response({"project": "prudent"})
        for field, value in (("merchant_failure_probability", 2),
                             ("bank_default_probability", -1),
                             ("expected_treasury_bank_debt_guarantee", -100)):
            candidate = dict(oracle_reply(public_cases(c)[0]), **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_response(candidate)
        failed = run_adapter(
            c, [sys.executable, "-c", "print('{}')"],
            {"experiment_id": "invalid-adapter"}, timeout=10)
        self.assertEqual(failed["subprocess_calls_attempted"], 5)
        self.assertEqual(failed["score"]["coverage"], 0)
        self.assertEqual(failed["score"]["field_accuracy_including_missing"], 0)

    def test_source_only_report_deterministic(self):
        c = cfg()
        self.assertEqual(analysis(c), analysis(deepcopy(c)))
        for g, row in zip(c["guarantee_grid"], analysis(c)["rows"]):
            self.assertEqual(row["baseline"]["borrowed"] % c["debt_step"], 0)
            self.assertEqual(best_choice(c, g)["borrowed"], row["baseline"]["borrowed"])


class LocalLombardTransportTests(unittest.TestCase):
    def test_model_request_is_single_packet_verified_local_identity(self):
        packet = public_cases(cfg())[0]
        server = FakeServer(oracle_reply(packet))
        model = local_adapter(server)
        result = model.infer_feedback(packet, [])
        self.assertEqual(set(result), set(OUTPUTS))
        payload = json.loads(server.requests[-1].data)
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(json.loads(payload["messages"][1]["content"]), {"packet": packet})
        self.assertFalse(payload["cache_prompt"])
        self.assertEqual(payload["lora"], [{"id": 0, "scale": 1}])
        self.assertEqual(set(payload["response_format"]["schema"]["required"]), set(OUTPUTS))
        self.assertNotIn("tools", payload)
        with self.assertRaises(ValueError):
            model.infer_feedback(packet, [{"old": "smuggled"}])
        with self.assertRaises(ValueError):
            model.infer_feedback({**packet, "source_class": "hidden_gold"}, [])

    def test_invalid_action_truncation_tool_call_and_side_channel(self):
        packet = public_cases(cfg())[1]
        server = FakeServer(oracle_reply(packet))
        model = local_adapter(server)
        server.finish = "length"
        with self.assertRaisesRegex(ValueError, "truncated"):
            model.infer_feedback(packet, [])
        server.finish = "stop"
        server.tool_calls = [{"id": "unwanted"}]
        with self.assertRaisesRegex(ValueError, "tool calls"):
            model.infer_feedback(packet, [])
        server.tool_calls = None
        server.answer = {**server.answer, "scratchpad": "secret"}
        with self.assertRaises(ValueError):
            model.infer_feedback(packet, [])


if __name__ == "__main__":
    unittest.main()
