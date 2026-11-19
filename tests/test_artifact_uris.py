"""Artifact URI audit regression tests, using synthetic temporary files."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_artifact_uris import audit


class ArtifactAuditTests(unittest.TestCase):
    def test_checked_in_artifacts_match_immutable_index(self):
        result = audit()
        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["n_verified"], 28)
        self.assertEqual(result["bytes_verified"], 1_382_582)
        self.assertEqual(result["n_pinned_external_weights"], 2)

    def fixture(self, directory: Path):
        content = b'{"fixture": true}\n'
        target = directory / "results" / "fixture.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        commit = "a" * 40
        item = {
            "path": "results/fixture.json",
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "blob_uri": f"https://github.com/patrickdugan/SystemicRiskBench/blob/{commit}/results/fixture.json",
            "raw_uri": f"https://raw.githubusercontent.com/patrickdugan/SystemicRiskBench/{commit}/results/fixture.json",
        }
        doc = {
            "schema": "srb.artifact_uri_index.v1",
            "repository": "https://github.com/patrickdugan/SystemicRiskBench",
            "artifact_commit": commit,
            "uri_policy": "immutable_commit_pinned_reports_and_datasets",
            "storage_tier": "git_repository_under_100mb",
            "total_indexed_bytes": len(content),
            "artifacts": [item],
            "external_pinned_weights_huggingface": [{
                "bytes": 1024, "sha256": "b" * 64,
                "uri": "https://huggingface.co/company/model/resolve/" + "c"*40 + "/weight.gguf",
            }],
        }
        manifest = directory / "results/artifact-uris.json"
        manifest.write_text(json.dumps(doc, indent=2) + "\n")
        return doc, target, manifest

    def test_mutated_bytes_and_mutable_url_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc, target, manifest = self.fixture(root)
            self.assertEqual(audit(root)["status"], "passed")
            target.write_bytes(b'{"fixture": false}\n')
            self.assertEqual(audit(root)["status"], "failed")
            target.write_bytes(b'{"fixture": true}\n')
            doc["artifacts"][0]["raw_uri"] = doc["artifacts"][0]["raw_uri"].replace(
                "a"*40, "main")
            manifest.write_text(json.dumps(doc))
            self.assertEqual(audit(root)["status"], "failed")

    def test_user_local_file_paths_or_secrets_are_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc, target, manifest = self.fixture(root)
            data = b'{"local": "file:///C:/Users/private/some.log"}\n'
            target.write_bytes(data)
            doc["artifacts"][0]["bytes"] = len(data)
            doc["artifacts"][0]["sha256"] = hashlib.sha256(data).hexdigest()
            doc["total_indexed_bytes"] = len(data)
            manifest.write_text(json.dumps(doc))
            issues = audit(root)["issues"]
            self.assertTrue(any("sensitive marker" in item for item in issues))

    def test_traversal_duplicate_and_model_pin_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc, target, manifest = self.fixture(root)
            doc["artifacts"] = [copy.deepcopy(doc["artifacts"][0])] * 2
            manifest.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):
                audit(root)
            doc["artifacts"] = [copy.deepcopy(doc["artifacts"][0])]
            doc["artifacts"][0]["path"] = "../fixture.json"
            manifest.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):
                audit(root)
            doc, target, manifest = self.fixture(root)
            doc["external_pinned_weights_huggingface"][0]["uri"] = (
                "https://huggingface.co/company/model/resolve/main/weight.gguf"
            )
            manifest.write_text(json.dumps(doc))
            self.assertEqual(audit(root)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
