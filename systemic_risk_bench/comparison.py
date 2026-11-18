"""Paired diagnostics for SRB's small, public numerical pilot.

The independent descriptive unit is a risk family, not a question, answer
field, stage, model token, or repeated evaluation of the same public fixture.
A sign test is reported as a resolution diagnostic; causal exchangeability
and preregistration are needed before its p value supports inference.
"""

from collections import defaultdict
import hashlib
import json
from math import comb

from .scoring import score_numeric
from .suite import quantitative_tasks


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def _normalize(run):
    if not isinstance(run, dict) or run.get("track") != "synthetic_numerical":
        raise ValueError("paired numerical comparison requires synthetic_numerical runs")
    receipts = run.get("receipts")
    if not isinstance(receipts, list):
        raise ValueError("run receipts must be a list")
    expected = {task["id"] for task in quantitative_tasks()}
    packets = {}
    responses = []
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError("each receipt must be an object")
        identifier = receipt.get("case_id")
        if identifier not in expected or identifier in packets or receipt.get("stage_index") != 0:
            raise ValueError("numerical receipts must have unique known case ids at stage zero")
        packet_hash = receipt.get("packet_sha256")
        if not isinstance(packet_hash, str) or len(packet_hash) != 64 or any(
            character not in "0123456789abcdef" for character in packet_hash
        ):
            raise ValueError("each receipt needs a lowercase SHA-256 packet digest")
        packets[identifier] = packet_hash
        if receipt.get("status") == "ok":
            response = receipt.get("response")
            if not isinstance(response, dict):
                raise ValueError("ok receipts must contain an object response")
            responses.append({"id": identifier, "estimates": response.get("estimates", {})})
    if set(packets) != expected:
        raise ValueError("paired comparison requires every registered numerical task")
    return packets, score_numeric(responses)


def _sign_test(wins, losses):
    """Two-sided exact sign-test resolution; ties have no directional information."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(comb(n, k) for k in range(min(wins, losses) + 1))
    return min(1.0, 2 * tail / (2 ** n))


def paired_numeric_report(left, right):
    """Compare two complete runs on byte-identical public packets.

    All results are descriptive because the current pilot has four risk
    families and a public, reusable task set. The exact sign-test p value
    measures discrete resolution under a hypothetical independent-family null.
    """
    left_packets, left_score = _normalize(left)
    right_packets, right_score = _normalize(right)
    if left_packets != right_packets:
        raise ValueError("paired numerical inference requires identical packet hashes")
    left_checks = {(c["id"], c["field"]): c["passed"] for c in left_score["checks"]}
    right_checks = {(c["id"], c["field"]): c["passed"] for c in right_score["checks"]}
    task_fields = {t["id"]: t["answer_fields"] for t in quantitative_tasks()}
    by_family = defaultdict(list)
    for task in quantitative_tasks():
        fields = task_fields[task["id"]]
        delta = (sum(int(right_checks[(task["id"], field)]) for field in fields)
                 - sum(int(left_checks[(task["id"], field)]) for field in fields)) / len(fields)
        by_family[task["family"]].append(delta)
    family_deltas = {name: sum(values) / len(values)
                     for name, values in sorted(by_family.items())}
    wins = sum(delta > 0 for delta in family_deltas.values())
    losses = sum(delta < 0 for delta in family_deltas.values())
    ties = len(family_deltas) - wins - losses
    effective_n = wins + losses
    return {
        "schema_version": "srb.paired_numeric.v0.1",
        "left_run_sha256": _digest(left),
        "right_run_sha256": _digest(right),
        "packet_match": "identical_hashes_all_six_tasks",
        "independent_descriptive_unit": "risk_family",
        "field_count": len(left_checks),
        "task_count": len(task_fields),
        "family_count": len(family_deltas),
        "left_micro_accuracy": left_score["numeric_micro_accuracy"],
        "right_micro_accuracy": right_score["numeric_micro_accuracy"],
        "micro_accuracy_delta_right_minus_left": (right_score["numeric_micro_accuracy"]
                                                  - left_score["numeric_micro_accuracy"]),
        "left_family_macro_accuracy": left_score["numeric_family_macro_accuracy"],
        "right_family_macro_accuracy": right_score["numeric_family_macro_accuracy"],
        "family_macro_delta_right_minus_left": (right_score["numeric_family_macro_accuracy"]
                                                 - left_score["numeric_family_macro_accuracy"]),
        "family_deltas_right_minus_left": family_deltas,
        "directional_families": {"right_better": wins, "left_better": losses,
                                  "tied": ties, "nonzero": effective_n},
        "exploratory_two_sided_family_sign_p": _sign_test(wins, losses),
        "smallest_attainable_two_sided_sign_p": (min(1.0, 2 / (2 ** effective_n))
                                                  if effective_n else 1.0),
        "confidence_interval": None,
        "inferential_status": "descriptive_pilot_only",
        "reasoning_quality_evaluated": False,
        "model_ranking_supported": False,
        "notes": [
            "The six public questions share only four causal families; 13 answer fields are not independent samples.",
            "The exploratory sign-test p assumes independent, exchangeable family directions under its null; this design does not certify those assumptions.",
            "Repeated public prompts, changed seeds and more simulated agents do not create new independent causal families.",
            "For inferential claims, preregister new held-out causal families, independent evaluation units, a target effect and a power or precision plan.",
        ],
    }
