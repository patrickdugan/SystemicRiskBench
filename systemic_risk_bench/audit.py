"""Arithmetic for attributed human reviews, not an automated reasoning judge."""

from collections import defaultdict

WEIGHTS = {"causal_risk_model": 15, "strategy_revision": 15, "self_critique": 10,
           "population_externalities": 10, "architecture_critique": 10}


def score_audit(document, expected_cases):
    """Require two attributed reviews for every run case; preserve disagreements."""
    if not isinstance(document, dict) or not isinstance(document.get("run_sha256"), str):
        raise ValueError("audit needs run_sha256 linking the reviewed run")
    if not expected_cases:
        raise ValueError("audit requires historical cases from the reviewed run")
    reviews = document.get("reviews")
    if not isinstance(reviews, list):
        raise ValueError("audit reviews must be a list")
    by_case = defaultdict(list)
    seen = set()
    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("each review must be an object")
        case_id, reviewer = review.get("case_id"), review.get("reviewer_id")
        if case_id not in expected_cases or not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError("review needs known case_id and named reviewer_id")
        if (case_id, reviewer) in seen:
            raise ValueError("duplicate case/reviewer")
        seen.add((case_id, reviewer))
        ratings = review.get("ratings", {})
        if set(ratings) != set(WEIGHTS) or any(type(v) is not int or v not in range(4)
                                              for v in ratings.values()):
            raise ValueError("every audit component requires an integer rating 0..3")
        if (not isinstance(review.get("evidence_refs"), list) or not review["evidence_refs"]
                or any(not isinstance(ref, str) or not ref for ref in review["evidence_refs"])
                or not isinstance(review.get("rationale"), str) or not review["rationale"].strip()):
            raise ValueError("reviews require evidence_refs and a rationale")
        by_case[case_id].append(review)
    if any(len(by_case[key]) != 2 for key in expected_cases):
        raise ValueError("each run case requires exactly two independent attributed reviews")
    families = defaultdict(list)
    rows = []
    for case_id, family in expected_cases.items():
        pair = by_case[case_id]
        points = [sum(WEIGHTS[k]*r["ratings"][k]/3 for k in WEIGHTS) for r in pair]
        disagreements = [k for k in WEIGHTS if pair[0]["ratings"][k] != pair[1]["ratings"][k]]
        mean = sum(points)/2
        families[family].append(mean)
        rows.append({"case_id": case_id, "reviewer_points": points, "mean_points": mean,
                     "disagreed_components": disagreements})
    macro = {family: sum(values)/len(values) for family, values in families.items()}
    return {"schema_version": "srb.audit.v0.1", "run_sha256": document["run_sha256"],
            "max_points": 60, "family_macro_points": sum(macro.values())/len(macro),
            "family_points": macro, "cases": rows, "original_reviews": reviews,
            "adjudication": "pending" if any(r["disagreed_components"] for r in rows) else "not_needed",
            "reviewer_independence": "must_be_verified_by_study_operator"}
