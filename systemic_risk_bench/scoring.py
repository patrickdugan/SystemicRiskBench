"""Strict numerical scoring; semantic reasoning is separately reviewed by humans."""

import json
import math
from collections import defaultdict
from .suite import numerical_answers, quantitative_tasks


def loads_json(value):
    def reject(value):
        raise ValueError(f"non-finite JSON constant: {value}")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def finite_float(raw):
        parsed = float(raw)
        if not math.isfinite(parsed):
            raise ValueError("non-finite JSON number")
        return parsed
    return json.loads(value, parse_constant=reject, object_pairs_hook=unique, parse_float=finite_float)


def read_json(path):
    with open(path, encoding="utf-8-sig") as handle:
        return loads_json(handle.read())


def finite(value):
    try:
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value))
    except OverflowError:
        return False


def score_numeric(responses):
    """All known tasks stay in the denominator, including missing responses."""
    if not isinstance(responses, list):
        raise ValueError("responses must be a list")
    answers = numerical_answers()
    index = {}
    for row in responses:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError("each response requires a string id")
        if row["id"] in index:
            raise ValueError(f"duplicate response id: {row['id']}")
        if row["id"] not in answers:
            raise ValueError(f"unknown quantitative response id: {row['id']}")
        if not isinstance(row.get("estimates", {}), dict):
            raise ValueError("estimates must be an object")
        index[row["id"]] = row
    checks = []
    families = defaultdict(list)
    answered = 0
    for task in quantitative_tasks():
        identifier = task["id"]
        estimates = index.get(identifier, {}).get("estimates", {})
        task_checks = []
        unknown = set(estimates) - set(answers[identifier])
        if unknown:
            raise ValueError(f"unknown estimate fields for {identifier}: {sorted(unknown)}")
        for name, expected in answers[identifier].items():
            actual = estimates.get(name)
            valid = finite(actual)
            answered += int(valid)
            passed = valid and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-8)
            item = {"id": identifier, "field": name, "expected": expected,
                    "actual": actual, "passed": passed,
                    "status": "correct" if passed else "wrong" if valid else "missing_or_invalid"}
            checks.append(item)
            task_checks.append(int(passed))
        families[task["family"]].append(sum(task_checks) / len(task_checks))
    family_scores = {key: sum(values)/len(values) for key, values in sorted(families.items())}
    return {"schema_version": "srb.numeric_report.v0.1", "checks": checks,
            "numeric_micro_accuracy": sum(c["passed"] for c in checks)/len(checks),
            "numeric_family_macro_accuracy": sum(family_scores.values())/len(family_scores),
            "family_accuracy": family_scores, "coverage": answered/len(checks),
            "reasoning_score": None, "reasoning_status": "requires_independent_human_audit",
            "model_evaluation_claim": False}


def brier(forecasts):
    """Score already-frozen binary forecasts; benchmark selection is not prevalence."""
    if not forecasts:
        raise ValueError("need forecasts")
    losses = []
    ids = set()
    for row in forecasts:
        if row.get("id") in ids or not isinstance(row.get("id"), str):
            raise ValueError("forecasts require unique string ids")
        ids.add(row["id"])
        p, outcome = row.get("probability"), row.get("outcome")
        if not finite(p) or not 0 <= p <= 1 or type(outcome) is not int or outcome not in (0, 1):
            raise ValueError("binary forecast requires probability in [0,1] and integer outcome 0/1")
        losses.append((p-outcome)**2)
    return {"brier_score": sum(losses)/len(losses), "n": len(losses),
            "requires_preregistered_event_cutoff_horizon_and_frozen_forecast": True}
