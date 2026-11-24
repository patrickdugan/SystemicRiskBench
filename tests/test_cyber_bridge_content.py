"""CYBER incident narrative: public packet boundary and synthetic capacity oracle."""
import json
import unittest
from fractions import Fraction
from systemic_risk_bench.content_suite import content_case, content_packet
from systemic_risk_bench.cli import historical

CASE = "content_cyber_bridge_2026"


class CyberBridgeTests(unittest.TestCase):
    def test_frozen_baseline_and_stage_boundary(self):
        self.assertEqual(len(historical()), 37)
        case = content_case(CASE)
        self.assertEqual(case["provenance"]["mode"], "retrospective_reconstruction")
        self.assertEqual(len(case["stages"]), 3)
        for index in range(3):
            packet = content_packet(CASE, index)
            self.assertEqual(len(packet["visible_stages"]), index + 1)
            self.assertFalse(packet["clean_holdout_claim"])
            self.assertFalse(packet["authentic_historical_prices"])
            self.assertNotIn("outcome", packet)
            self.assertNotIn("sources", packet)
            self.assertNotIn("numerical_reference", json.dumps(packet))
        early = json.dumps(content_packet(CASE, 0))
        self.assertNotIn("replacement verifier key", early)
        self.assertNotIn("10,000 tokens", early)
        self.assertNotIn("Bitquery", early)
        self.assertNotIn("10,000 tokens", json.dumps(content_packet(CASE, 1)))
        masked = json.dumps(content_packet(CASE, 2, masked=True))
        for name in ("CYBER", "Upbit", "Bithumb", "Bitquery", "Solana", "Ethereum"):
            self.assertNotIn(name, masked)
        self.assertIn("Entity-", masked)

    def test_exact_lockbox_and_capacity_accounting(self):
        reference = content_case(CASE)["outcome"]["numerical_reference"]
        opening = reference["lockbox_opening"]
        outflow = reference["lockbox_outflow"]
        remaining = reference["lockbox_remaining"]
        self.assertEqual(opening - outflow, remaining)
        self.assertEqual(Fraction(outflow, opening) + Fraction(remaining, opening), 1)
        self.assertEqual(reference["blocked_transfer_dependent_matched_volume"], 0)
        for row in reference["fixed_per_agent"]:
            request = 100 * row["agents"]
            filled = min(request, 10_000)
            self.assertEqual(row["requested"], request)
            self.assertEqual(row["max_filled"], filled)
            self.assertEqual(Fraction(str(row["unfilled_fraction"])), Fraction(request - filled, request))
        self.assertEqual(reference["fixed_total_requested"], reference["fixed_total_max_filled"])


if __name__ == "__main__":
    unittest.main()
