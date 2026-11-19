"""Verify the public SRB artifact URI catalog against committed source bytes.

No remote downloads, local model files, tokens, or machine secrets are used.
Intentionally avoids printing file contents or possible secret values.
Run: python scripts/audit_artifact_uris.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
INDEX = Path("results/artifact-uris.json")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SENSITIVE_PATHS = {
    "win_user_directory": re.compile(
        rb"(?i)\b[A-Z]:\\{1,4}(?:Users|OneDrive|Documents|Desktop)\\{1,4}"
    ),
    "file_scheme": re.compile(rb"(?i)file:///(?:[A-Z]:/|home/|Users/)", re.I),
    "unix_user_directory": re.compile(
        rb"(?i)/(?:home/(?:runner|patri|patrick|oai)|Users/(?:patri|patrick)|mnt/data)/"
    ),
    "credential_assignment": re.compile(
        rb'(?i)"(?:api_?key|access_?token|secret|password|private_?key)"\s*:\s*"[^"]{12,}"'
    ),
}


def audit(root: Path = ROOT, index_path: Path = INDEX) -> dict:
    """Validate every indexed byte stream and URI against an immutable Git SHA."""
    root = root.resolve()
    manifest = json.loads((root / index_path).read_text(encoding="utf-8"))
    if manifest.get("schema") != "srb.artifact_uri_index.v1":
        raise ValueError("unexpected artifact URI index schema")
    if manifest.get("repository") != "https://github.com/patrickdugan/SystemicRiskBench":
        raise ValueError("repository identity mismatch")
    commit = manifest.get("artifact_commit")
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise ValueError("missing full immutable artifact commit SHA")
    if manifest.get("uri_policy") != "immutable_commit_pinned_reports_and_datasets":
        raise ValueError("artifact URI pinning policy unspecified")
    items = manifest.get("artifacts")
    if not isinstance(items, list) or not items:
        raise ValueError("artifact entries missing")
    if manifest.get("storage_tier") != "git_repository_under_100mb":
        raise ValueError("unexpected artifact storage tier")
    if len(items) != len({row.get("path") for row in items if isinstance(row, dict)}):
        raise ValueError("duplicate artifact paths")
    scanned_bytes = 0
    violations = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("invalid artifact entry")
        path = item.get("path")
        if not isinstance(path, str):
            raise ValueError("artifact path must be a string")
        rel = PurePosixPath(path)
        if rel.is_absolute() or ".." in rel.parts or "\\" in path or str(rel) != path:
            raise ValueError(f"unsafe artifact path: {path}")
        candidate = (root / path).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise ValueError(f"missing artifact or symlink escaped tree: {path}")
        expected_blob = f"https://github.com/patrickdugan/SystemicRiskBench/blob/{commit}/{path}"
        expected_raw = f"https://raw.githubusercontent.com/patrickdugan/SystemicRiskBench/{commit}/{path}"
        if item.get("blob_uri") != expected_blob or item.get("raw_uri") != expected_raw:
            violations.append(f"{path}: URI is not pinned to the expected immutable content")
        data = candidate.read_bytes()
        scanned_bytes += len(data)
        if type(item.get("bytes")) is not int or len(data) != item["bytes"]:
            violations.append(f"{path}: size mismatch")
        declared = item.get("sha256")
        if not isinstance(declared, str) or not HEX64.fullmatch(declared):
            violations.append(f"{path}: invalid SHA-256 registration")
        elif hashlib.sha256(data).hexdigest() != declared:
            violations.append(f"{path}: SHA-256 mismatch")
        for label, pattern in SENSITIVE_PATHS.items():
            if pattern.search(data):
                violations.append(f"{path}: matched sensitive marker {label}")
    if type(manifest.get("total_indexed_bytes")) is not int:
        raise ValueError("total_indexed_bytes must be an integer")
    if scanned_bytes != manifest["total_indexed_bytes"]:
        violations.append("total indexed byte count mismatch")
    if scanned_bytes > 100_000_000:
        violations.append("indexed Git artifacts exceed 100 MB threshold")
    weights = manifest.get("external_pinned_weights_huggingface")
    if not isinstance(weights, list) or not weights:
        violations.append("model weights registration missing")
    else:
        for weight in weights:
            if not isinstance(weight, dict):
                violations.append("invalid external model weight entry")
                continue
            if type(weight.get("bytes")) is not int or weight["bytes"] <= 0:
                violations.append("invalid external model weight size")
            digest = weight.get("sha256")
            if not isinstance(digest, str) or not HEX64.fullmatch(digest):
                violations.append("invalid external model weight digest")
            url = weight.get("uri", "")
            if (not isinstance(url, str) or
                not re.fullmatch(r"https://huggingface\.co/[^\s]+/resolve/[0-9a-f]{40}/[^\s]+", url)):
                violations.append("external model URI lacks a commit pin")
    report = {
        "schema": "srb.artifact_uri_audit.v1",
        "status": "passed" if not violations else "failed",
        "artifact_commit": commit,
        "n_verified": len(items),
        "bytes_verified": scanned_bytes,
        "n_pinned_external_weights": len(weights) if isinstance(weights, list) else 0,
        "issues": violations,
    }
    return report


def main() -> int:
    try:
        report = audit()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
