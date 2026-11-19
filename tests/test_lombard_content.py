"""Tests for source-grounded Bagehot content and conditional rescue arithmetic."""
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from systemic_risk_bench.content_suite import (
    content_case, content_cases, content_packet,
)
from systemic_risk_bench.content_math import (
    content_numeric_answers, content_quantitative_tasks, score_content_numeric,
)
from systemic_risk_bench.lombard import (
    bank_rescue, merchant_equity, repeat_rescue, funding_spread_counterfactual,
)
from systemic_risk_bench.suite import quantitative_tasks, numerical_answers

CASE_ID = "content_bagehot_lombard_merchants"


class LombardContentTests(unittest.TestCase):
    def test_is_separate_from_33_historical_episodes_and_numeric_baseline(self):
        from systemic_risk_bench.cli import historical
        self.assertEqual(len(historical()), 37)  # 33 histories + four benign controls.
        self.assertEqual(len(content_cases()), 2)
        self.assertEqual(content_cases()[0]["id"], CASE_ID)
        self.assertEqual(len(quantitative_tasks()), 6)
        self.assertEqual(sum(len(fields) for fields in numerical_answers().values()), 13)

    def test_source_scope_fiction_and_staged_packet_leakage(self):
        case = content_case(CASE_ID)
        self.assertEqual(case["provenance"]["mode"], "synthetic_counterfactual")
        self.assertFalse(case["provenance"]["historical_market_data"])
        self.assertIn("1873", case["provenance"]["primary_text"])
        self.assertEqual(len(case["stages"]), 3)
        self.assertTrue(any("gutenberg.org" in x["url"] for x in case["sources"]))
        early = content_packet(CASE_ID, 0)
        late = content_packet(CASE_ID, 2)
        self.assertEqual(len(early["visible_stages"]), 1)
        self.assertEqual(len(late["visible_stages"]), 3)
        early_text = json.dumps(early)
        self.assertNotIn("GBP 500 million", early_text)
        self.assertNotIn("GBP 4 million", early_text)
        self.assertNotIn("outcome", early)
        self.assertNotIn("sources", early)
        self.assertNotIn("evaluation_anchors", early)
        self.assertNotIn("source URLs", early_text)  # No raw source URLs enter packet.
        self.assertFalse(early["clean_holdout_claim"])
        self.assertEqual(early["replay_mode"], "narrative_exercise")
        with self.assertRaises(ValueError):
            content_case("unknown_case")

    def test_metadata_masking_protection(self):
        raw = json.dumps(content_packet(CASE_ID, 2, masked=True))
        for name in ("Walter Bagehot", "Bank of England", "Treasury"):
            self.assertNotIn(name, raw)
        self.assertIn("Entity-01", raw)
        self.assertTrue(content_packet(CASE_ID, 0, masked=True)["case_id"].startswith("case-"))

    def test_original_merchant_math_and_spread_reversal(self):
        inputs = content_quantitative_tasks()[0]["inputs"]
        actual = merchant_equity(**inputs)
        self.assertEqual(actual["annual_interest"], 2000)
        self.assertEqual(actual["cash_roe"], 0.10)
        self.assertEqual(actual["levered_roe"], 0.30)
        self.assertEqual(actual["max_price_cut_at_cash_roe"], 2000)
        self.assertEqual(actual["leverage_assets_to_equity"], 5)
        self.assertEqual(actual["debt_to_equity"], 4)
        negative_spread = merchant_equity(**{**inputs, "gross_operating_profit": 1000})
        self.assertLess(negative_spread["levered_roe"], negative_spread["cash_roe"])
        at_zero_spread = merchant_equity(**{**inputs, "gross_operating_profit": 2500})
        self.assertAlmostEqual(at_zero_spread["cash_roe"], at_zero_spread["levered_roe"])
        with self.assertRaises(ValueError):
            merchant_equity(**{**inputs, "cash_equity": True})
        with self.assertRaises(ValueError):
            merchant_equity(**{**inputs, "cash_equity": 40000})
        conditional = funding_spread_counterfactual(
            borrower_equity=10000, borrowed=40000,
            gross_operating_profit=5000, unsubsidized_rate=.11, supported_rate=.05)
        self.assertAlmostEqual(conditional["unsubsidized_roe"], .06)
        self.assertAlmostEqual(conditional["supported_roe"], .30)
        self.assertAlmostEqual(conditional["annual_interest_saving"], 2400)
        self.assertAlmostEqual(conditional["roe_difference"], .24)
        with self.assertRaises(ValueError):
            funding_spread_counterfactual(
                borrower_equity=10000, borrowed=40000,
                gross_operating_profit=5000, unsubsidized_rate=.05, supported_rate=.11)

    def test_bank_vs_central_bank_ledger_and_no_loss_control(self):
        inputs = content_quantitative_tasks()[1]["inputs"]
        answer = bank_rescue(**inputs)
        for field, expected in {
            "initial_bank_debt": 450, "post_loss_assets": 470,
            "post_loss_equity": 20, "bank_recap_for_old_equity": 30,
            "max_assets_without_recap": 200, "asset_reduction_required": 270,
            "equity_after_liquidity_loan": 20,
            "central_bank_equity_after_liquidity_loan_origination": 10,
            "central_bank_equity_after_credit_loss": 6,
            "central_bank_recap_for_target": 4,
        }.items():
            self.assertAlmostEqual(answer[field], expected)
        safe = bank_rescue(**{**inputs, "credit_loss": 0,
                              "central_bank_credit_loss": 0})
        self.assertEqual(safe["bank_recap_for_old_equity"], 0)
        self.assertEqual(safe["central_bank_recap_for_target"], 0)
        self.assertEqual(safe["equity_after_liquidity_loan"], 50)
        with self.assertRaises(ValueError):
            bank_rescue(**{**inputs, "capital_ratio": 0.2})
        with self.assertRaises(ValueError):
            bank_rescue(**{**inputs, "credit_loss": math.nan})

    def test_conditional_repeat_rescue_is_not_crisis_prediction(self):
        answer = repeat_rescue(initial_equity=50, recurring_loss=30, rounds=3)
        self.assertEqual(answer["restored_equity_after_each_round"], 50)
        self.assertEqual(answer["cumulative_public_transfer_if_publicly_financed"], 90)
        self.assertEqual(answer["equity_without_injections_before_resolution"], -40)
        self.assertTrue(answer["recurrence_only_assumes_repeat_losses_and_recapitalization"])
        self.assertEqual(repeat_rescue(initial_equity=50, recurring_loss=0,
                                      rounds=3)["cumulative_public_transfer_if_publicly_financed"], 0)
        with self.assertRaises(ValueError):
            repeat_rescue(initial_equity=50, recurring_loss=30, rounds=True)

    def test_content_numeric_scores_keep_invalid_in_denominator(self):
        questions = content_quantitative_tasks()
        self.assertEqual(len(questions), 4)
        self.assertEqual(sum(len(q["answer_fields"]) for q in questions), 17)
        gold = content_numeric_answers()
        rows = [{"id": task["id"], "estimates": gold[task["id"]]} for task in questions]
        report = score_content_numeric(rows)
        self.assertEqual(report["n_fields"], 17)
        self.assertEqual(report["micro_accuracy"], 1.0)
        self.assertFalse(report["model_evaluation_claim"])
        missing = score_content_numeric(rows[:1])
        self.assertEqual(missing["n_covered_fields"], 4)
        self.assertEqual(missing["micro_accuracy"], 4/17)
        with self.assertRaises(ValueError):
            score_content_numeric(rows + [rows[0]])
        with self.assertRaises(ValueError):
            score_content_numeric([{"id": rows[0]["id"],
                                     "estimates": {"unknown": 1}}])
        invalid = score_content_numeric([
            {"id": rows[0]["id"], "estimates": {"annual_interest": True,
                                                "cash_roe": float("nan")}}])
        self.assertEqual(invalid["n_covered_fields"], 0)

    def test_cli_export_and_actual_subprocess_content_track(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            env = base / "packet.json"
            run = base / "run.json"
            q = base / "tasks.json"
            cmd = [sys.executable, "-m", "systemic_risk_bench"]
            subprocess.run(cmd + ["content-packet", "--case", CASE_ID,
                                  "--stage", "0", "--output", str(env)],
                           check=True, capture_output=True, timeout=25)
            packet = json.loads(env.read_text())
            self.assertEqual(packet["stage_index"], 0)
            self.assertIn("packet_sha256", packet)
            subprocess.run(cmd + ["content-quant", "--output", str(q)],
                           check=True, capture_output=True, timeout=25)
            questions = json.loads(q.read_text())
            self.assertFalse(questions["gold_answers_present"])
            self.assertNotIn("expected", json.dumps(questions))
            exp = base / "experiment.json"
            exp.write_text(json.dumps({"experiment_id": "lombard-fixture-only"}))
            subprocess.run(cmd + [
                "content-run", "--adapter-argv",
                json.dumps([sys.executable, "-m", "examples.fixture_adapter"]),
                "--experiment", str(exp), "--cases", CASE_ID,
                "--output", str(run),
            ], check=True, capture_output=True, timeout=30)
            output = json.loads(run.read_text())
            self.assertEqual(output["track"], "content_theory")
            self.assertEqual(len(output["receipts"]), 3)
            self.assertTrue(output["adapter_process_is_not_sandboxed_by_this_harness"])
            self.assertTrue(all(row["status"] == "ok" for row in output["receipts"]))


if __name__ == "__main__":
    unittest.main()
