"""Conceptual primary-source content track, independent from historical crisis totals.

Contents use the existing public_packet allowlist and require explicit source
annotations. Models get staged content without evaluator-only claims.
"""
from pathlib import Path

from .history import load_cases, public_packet

CONTENT_DIR = Path(__file__).resolve().parent / "data" / "content"


def content_cases() -> list[dict]:
    return load_cases(sorted(CONTENT_DIR.glob("*.json")))


def content_case(case_id: str) -> dict:
    matches = [case for case in content_cases() if case["id"] == case_id]
    if len(matches) != 1:
        raise ValueError("unknown content-suite case id")
    return matches[0]


def content_packet(case_id: str, stage: int, masked: bool = False) -> dict:
    return public_packet(content_case(case_id), stage, masked=masked)
