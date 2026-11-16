import copy
from pathlib import Path
import unittest

from systemic_risk_bench.audit import score_audit, WEIGHTS
from systemic_risk_bench.bitagent import covenant_packet
from systemic_risk_bench.cli import historical
from systemic_risk_bench.history import public_packet, validate_cases
from systemic_risk_bench.scoring import read_json

ROOT = Path(__file__).resolve().parent.parent


class IntegrationTests(unittest.TestCase):
    def test_complete_corpus_and_controls(self):
        cases = historical()
        self.assertEqual(validate_cases(cases), [])
        historical_cases = [c for c in cases if c["provenance"]["mode"] == "retrospective_reconstruction"]
        controls = [c for c in cases if c["provenance"]["mode"] == "synthetic_counterfactual"]
        self.assertEqual(len(historical_cases), 33)
        self.assertEqual(len(controls), 4)
        self.assertEqual(sum(len(c["stages"]) for c in cases), 74)
        for case in cases:
            packet = public_packet(case, 0, masked=True)
            self.assertNotIn("outcome", packet)
            self.assertNotIn("sources", packet)
            self.assertEqual(len(packet["visible_stages"]), 1)
            self.assertEqual(packet["replay_mode"], "narrative_exercise")
            self.assertNotIn("provenance", packet)

    def test_covenant_projection_preserves_units_and_excludes_owner(self):
        fixture = read_json(ROOT / "examples" / "covenant.fixture.json")
        source = copy.deepcopy(fixture)
        packet = covenant_packet(fixture)
        self.assertEqual(packet["max_gross_leverage"], 1.2)
        self.assertEqual(packet["capital"]["capAtoms"], "100000000000")
        self.assertNotIn("owner", packet)
        self.assertTrue(packet["missing_for_cva"])
        self.assertEqual(fixture, source)
        with self.assertRaises(ValueError):
            covenant_packet([])

    def test_audit_requires_two_reviewers_and_retains_disagreement(self):
        review = {"case_id": "c1", "reviewer_id": "A", "ratings": {k: 3 for k in WEIGHTS},
                  "evidence_refs": ["s0.e0"], "rationale": "Independent substantive review"}
        document = {"run_sha256": "fixture", "reviews": [review]}
        with self.assertRaises(ValueError):
            score_audit(document, {"c1": "family1"})
        second = copy.deepcopy(review)
        second["reviewer_id"] = "B"
        document["reviews"].append(second)
        self.assertEqual(score_audit(document, {"c1": "family1"})["family_macro_points"], 60)
        second["ratings"]["self_critique"] = 0
        self.assertEqual(score_audit(document, {"c1": "family1"})["adjudication"], "pending")


if __name__ == "__main__":
    unittest.main()
