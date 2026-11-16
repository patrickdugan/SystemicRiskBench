"""Contract and leakage-boundary tests for the narrative historical exporter."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from systemic_risk_bench.history import load_cases, public_packet, validate_cases


def sample_case():
    return {
        "id": "example-1987-credit",
        "title": "Example Bank funding episode",
        "family": "funding_runs",
        "event_date": "1987-10-19",
        "entities": [{"name": "Example Bank", "aliases": ["Example"]}, "OTHER EXCHANGE"],
        "provenance": {"mode": "retrospective_reconstruction", "secret_note": "PRIVATE_PROVENANCE"},
        "stages": [
            {"id": "early-1987-10-18", "cutoff": "1987-10-18T12:00:00Z", "observations": ["Example Bank needs funding.", "Market depth is unknown; see https://example.org/source."], "questions": ["Should Example reduce exposure?"], "evaluation_anchors": ["PRIVATE_STAGE_ANCHOR"]},
            {"id": "late-1987-10-19", "cutoff": "1987-10-19T12:00:00+00:00", "observations": ["OTHER EXCHANGE observes FUTURE_SIGNAL."], "questions": ["How should Example Bank revise its policy?"]},
        ],
        "outcome": {"summary": "PRIVATE_OUTCOME", "mechanisms": ["PRIVATE_MECHANISM"], "evaluation_anchors": ["PRIVATE_GOLD"]},
        "sources": [{"url": "https://example.org/source", "title": "PRIVATE_SOURCE_TITLE"}],
        "evaluation_anchors": ["PRIVATE_TOP_LEVEL_ANCHOR"],
    }


class HistoricalPacketTests(unittest.TestCase):
    def test_schema_and_load_multiple_files(self):
        first = sample_case()
        second = sample_case()
        second["id"] = "second-case"
        self.assertEqual(validate_cases([first, second]), [])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            paths = []
            for index, case in enumerate((first, second)):
                path = Path(directory) / f"cases-{index}.json"
                path.write_text(json.dumps({"schema_version": "0.1.0", "cases": [case]}), encoding="utf-8")
                paths.append(path)
            self.assertEqual([case["id"] for case in load_cases(paths)], [first["id"], second["id"]])

    def test_public_packet_excludes_gold_sources_and_future_stages(self):
        packet = public_packet(sample_case(), 0)
        serialized = json.dumps(packet)
        self.assertNotIn("PRIVATE_", serialized)
        self.assertNotIn("FUTURE_SIGNAL", serialized)
        self.assertNotIn("https://", serialized)
        self.assertNotIn("1987-10-19", serialized)
        self.assertNotIn("event_date", packet)
        self.assertEqual(len(packet["visible_stages"]), 1)
        self.assertIn("Example Bank needs funding", serialized)

    def test_cumulative_visible_stages_without_mutation(self):
        case = sample_case()
        original = copy.deepcopy(case)
        packet = public_packet(case, 1)
        self.assertEqual(len(packet["visible_stages"]), 2)
        self.assertIn("FUTURE_SIGNAL", json.dumps(packet))
        self.assertEqual(packet["visible_stages"][1]["observations"][0]["evidence_id"], "s1.e0")
        self.assertEqual(case, original)

    def test_masked_packet_removes_metadata_dates_names_and_original_ids(self):
        case = sample_case()
        packet = public_packet(case, 1, masked=True)
        serialized = json.dumps(packet)
        for identifying_text in ("Example", "OTHER EXCHANGE", "1987", "early-", "late-"):
            self.assertNotIn(identifying_text, serialized)
        self.assertTrue(packet["case_id"].startswith("case-"))
        self.assertNotIn("title", packet)
        self.assertFalse(packet["masking"]["complete"])
        self.assertFalse(packet["clean_holdout_claim"])
        self.assertIn("Entity-01", serialized)
        self.assertIn("Entity-02", serialized)
        self.assertEqual(public_packet(case, 1, masked=True), packet)

    def test_masking_warns_when_no_entity_list_exists(self):
        case = sample_case()
        del case["entities"]
        packet = public_packet(case, 0, masked=True)
        self.assertIn("Example Bank", json.dumps(packet))
        self.assertIn("incomplete", packet["masking"]["warning"])

    def test_reject_invalid_stage_indices(self):
        for index in (-1, 2):
            with self.assertRaises(IndexError):
                public_packet(sample_case(), index)
        for index in (True, 0.5, "0"):
            with self.assertRaises(TypeError):
                public_packet(sample_case(), index)

    def test_chronology_and_duplicate_ids_rejected(self):
        case = sample_case()
        case["stages"][1]["cutoff"] = "1987-10-17"
        self.assertTrue(any("earlier" in error for error in validate_cases([case])))
        with self.assertRaises(ValueError):
            public_packet(case, 0)
        errors = validate_cases([sample_case(), sample_case()])
        self.assertTrue(any("duplicate case id" in error for error in errors))

    def test_overlapping_entity_alias_is_rejected(self):
        case = sample_case()
        case["entities"] = ["Example", {"name": "Example Bank", "aliases": ["Example"]}]
        with self.assertRaises(ValueError):
            public_packet(case, 0, masked=True)

    def test_invalid_collections_fail_with_actionable_error(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"schema_version":"0.1.0","cases":{}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cases must be a list"):
                load_cases([path])
            path.write_text("not JSON", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Cannot load"):
                load_cases([path])


if __name__ == "__main__":
    unittest.main()
