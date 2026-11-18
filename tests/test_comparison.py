"""Comparison of complete numerical pilots: family units and paired-packet checks."""
import hashlib
import unittest

from systemic_risk_bench.comparison import paired_numeric_report
from systemic_risk_bench.suite import numerical_answers, quantitative_tasks


def run_fixture(*, solved):
    answers = numerical_answers()
    receipts = []
    for task in quantitative_tasks():
        identifier = task["id"]
        receipts.append({
            "case_id": identifier,
            "stage_index": 0,
            "packet_sha256": hashlib.sha256(identifier.encode()).hexdigest(),
            "status": "ok",
            "response": {"estimates": answers[identifier] if solved else {}},
        })
    return {"schema_version": "srb.run.v0.1", "track": "synthetic_numerical",
            "experiment": {"experiment_id": "fixture"}, "receipts": receipts}


class PairedComparisonTests(unittest.TestCase):
    def test_perfect_vs_empty_cannot_support_inference_with_four_families(self):
        result = paired_numeric_report(run_fixture(solved=False), run_fixture(solved=True))
        self.assertEqual(result["field_count"], 13)
        self.assertEqual(result["task_count"], 6)
        self.assertEqual(result["family_count"], 4)
        self.assertEqual(result["micro_accuracy_delta_right_minus_left"], 1)
        self.assertEqual(result["family_macro_delta_right_minus_left"], 1)
        self.assertEqual(result["directional_families"]["right_better"], 4)
        self.assertEqual(result["smallest_attainable_two_sided_sign_p"], .125)
        self.assertEqual(result["exploratory_two_sided_family_sign_p"], .125)
        self.assertEqual(result["inferential_status"], "descriptive_pilot_only")
        self.assertFalse(result["model_ranking_supported"])
        self.assertIsNone(result["confidence_interval"])

    def test_identical_runs_have_no_directional_evidence(self):
        fixture = run_fixture(solved=True)
        result = paired_numeric_report(fixture, fixture)
        self.assertEqual(result["directional_families"]["nonzero"], 0)
        self.assertEqual(result["exploratory_two_sided_family_sign_p"], 1)
        self.assertEqual(result["family_macro_delta_right_minus_left"], 0)

    def test_receipt_order_is_immaterial_and_zeros_are_missing(self):
        left = run_fixture(solved=False)
        right = run_fixture(solved=True)
        right["receipts"].reverse()
        result = paired_numeric_report(left, right)
        self.assertEqual(result["family_count"], 4)
        self.assertEqual(result["right_micro_accuracy"], 1)

    def test_unmatched_packets_and_missing_cases_fail_closed(self):
        left, right = run_fixture(solved=False), run_fixture(solved=True)
        right["receipts"][0]["packet_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "identical packet hashes"):
            paired_numeric_report(left, right)
        right = run_fixture(solved=True)
        right["receipts"].pop()
        with self.assertRaisesRegex(ValueError, "every registered"):
            paired_numeric_report(left, right)

    def test_duplicate_or_invalid_response_fails_closed(self):
        left = run_fixture(solved=False)
        for mutation in ("duplicate", "unknown_field", "untrusted_status"):
            right = run_fixture(solved=True)
            if mutation == "duplicate":
                right["receipts"][1]["case_id"] = right["receipts"][0]["case_id"]
            elif mutation == "unknown_field":
                right["receipts"][0]["response"]["estimates"]["bogus"] = 42
            else:
                right["receipts"][0]["status"] = "ok"
                right["receipts"][0]["response"] = None
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                paired_numeric_report(left, right)


if __name__ == "__main__":
    unittest.main()
