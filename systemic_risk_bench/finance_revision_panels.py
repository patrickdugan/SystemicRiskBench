"""SRB-REV-03 source-law panel registration and complete selection audit.

Everything in this module is evaluator-only public development information.
Stress selection conditions on an oracle disagreement. The inherited posterior
is the original source-law comparator, not a posterior conditioned on selection.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from .agent_revision import DOMAIN, MAX_CASES, fixture, initial_posterior, squared
from .finance_revision import ACTIONS, FAMILIES, optimal_action, policy_regret
from .runner import sha

SCHEMA = "srb.finance_revision.panels.v1"
SEARCH_ROOTS = 256
QUOTA_PER_FAMILY = 6
NATURAL_ROOTS = 48
PILOT_ROOTS = 6
SOURCE_PATHS = (
    "systemic_risk_bench/agent_revision.py",
    "systemic_risk_bench/finance_revision.py",
    "systemic_risk_bench/finance_revision_panels.py",
)


def oracle_diagnostic(index: int) -> dict:
    world = fixture(index)
    family = FAMILIES[index % len(FAMILIES)]
    initial = optimal_action(initial_posterior(world.old_count), family)
    count = optimal_action(world.exact_count, family)
    bitmap = optimal_action(world.exact_full, family)
    return {
        "index": index, "case_id": world.case_id, "family": family,
        "initial_action": initial, "count_action": count, "bitmap_action": bitmap,
        "posterior_information_gap": squared(world.exact_count, world.exact_full),
        "count_policy_regret_vs_full": policy_regret(count, world.exact_full, family),
        "predicate_match": count != bitmap,
    }


def oracle_summary(indices) -> dict:
    indices = tuple(indices)
    if (not indices or any(type(i) is not int or not 0 <= i < MAX_CASES for i in indices)
            or list(indices) != sorted(set(indices))):
        raise ValueError("panel indices must be nonempty, unique, ascending source roots")
    rows = [oracle_diagnostic(index) for index in indices]
    n = len(rows)
    disagreements = sum(row["predicate_match"] for row in rows)
    count_revisions = sum(row["initial_action"] != row["count_action"] for row in rows)
    bitmap_revisions = sum(row["initial_action"] != row["bitmap_action"] for row in rows)
    return {
        "n_cases": n,
        "reference_law": "original_unconditioned_source_law",
        "n_oracle_action_disagreements": disagreements,
        "oracle_action_disagreement_rate": disagreements / n,
        "mean_posterior_information_gap": math.fsum(
            row["posterior_information_gap"] for row in rows) / n,
        "count_optimal_action_revisions": count_revisions,
        "count_optimal_action_revision_rate": count_revisions / n,
        "bitmap_optimal_action_revisions": bitmap_revisions,
        "bitmap_optimal_action_revision_rate": bitmap_revisions / n,
        "mean_count_policy_regret_vs_full": math.fsum(
            row["count_policy_regret_vs_full"] for row in rows) / n,
        "mean_bitmap_policy_regret_vs_full": 0.0,
        "count_action_counts": {
            action: sum(row["count_action"] == action for row in rows) for action in ACTIONS},
        "bitmap_action_counts": {
            action: sum(row["bitmap_action"] == action for row in rows) for action in ACTIONS},
    }


def build_manifest() -> dict:
    root = Path(__file__).resolve().parents[1]
    selected_by_family = {family: [] for family in FAMILIES}
    audit = []
    for index in range(SEARCH_ROOTS):
        row = oracle_diagnostic(index)
        chosen = selected_by_family[row["family"]]
        if not row["predicate_match"]:
            decision = "predicate_false"
        elif len(chosen) == QUOTA_PER_FAMILY:
            decision = "quota_full"
        else:
            decision = "selected"
            chosen.append(index)
        audit.append({**row, "selected": decision == "selected", "decision": decision})
    if any(len(indices) != QUOTA_PER_FAMILY for indices in selected_by_family.values()):
        raise ValueError("registered search pool cannot meet each family quota")
    stress = sorted(index for indices in selected_by_family.values() for index in indices)
    indices_by_panel = {
        "pilot": list(range(PILOT_ROOTS)),
        "natural": list(range(NATURAL_ROOTS)),
        "stress": stress,
    }
    manifest = {
        "schema": SCHEMA,
        "experiment_id": "SRB-REV-03",
        "source_domain": DOMAIN,
        "source_sha256": {
            path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in SOURCE_PATHS},
        "selection": {
            "search_roots": SEARCH_ROOTS,
            "search_order": "ascending_index_0_through_255_inclusive",
            "family_assignment": "FAMILIES[index % 3]",
            "quota_per_family": QUOTA_PER_FAMILY,
            "predicate": "source_law_count_final_action != source_law_bitmap_final_action",
            "tie_break_order": list(ACTIONS),
            "complete_search_required": True,
        },
        "evidence_class": "public_deterministic_development_only",
        "reference_law": "original_unconditioned_source_law",
        "selection_conditioned_bayes_claim": False,
        "population_estimate_claim": False,
        "model_evaluation_claim": False,
        "panels": {
            name: {
                "indices": indices,
                "selection_kind": "conditional_oracle_disagreement" if name == "stress" else "source_sequence_prefix",
                "summary": oracle_summary(indices),
            } for name, indices in indices_by_panel.items()
        },
        "selected_by_family": selected_by_family,
        "eligible_by_family": {
            family: sum(row["family"] == family and row["predicate_match"] for row in audit)
            for family in FAMILIES},
        "audit_decision_counts": {
            decision: sum(row["decision"] == decision for row in audit)
            for decision in ("selected", "quota_full", "predicate_false")},
        "natural_stress_overlap": sorted(set(indices_by_panel["natural"]) & set(stress)),
        "audit": audit,
    }
    manifest["manifest_sha256"] = sha(manifest)
    return manifest


def verify_manifest(manifest: dict) -> None:
    if type(manifest) is not dict or type(manifest.get("manifest_sha256")) is not str:
        raise ValueError("panel manifest needs its canonical SHA-256")
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    try:
        if sha(payload) != manifest["manifest_sha256"]:
            raise ValueError("panel manifest content digest mismatch")
        # Rebuilding validates every search decision, quota and source digest.
        # Canonical JSON comparison also distinguishes booleans from integers.
        if sha(manifest) != sha(build_manifest()):
            raise ValueError("panel manifest differs from registered source and selection")
    except (TypeError, OverflowError) as exc:
        raise ValueError("invalid panel manifest") from exc


def panel_indices(name: str, manifest: dict) -> tuple[int, ...]:
    if name not in ("pilot", "natural", "stress"):
        raise ValueError("unknown registered financial panel")
    verify_manifest(manifest)
    return tuple(manifest["panels"][name]["indices"])
