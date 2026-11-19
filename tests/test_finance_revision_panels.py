"""Independent selection and scoring checks for the SRB-REV-03 public panels."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as Q
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from systemic_risk_bench.agent_revision import fixture
from systemic_risk_bench.finance_revision import run_financial_revision
from systemic_risk_bench.finance_revision_panels import (
    build_manifest, panel_indices, verify_manifest,
)
from systemic_risk_bench.runner import sha


# These values were independently replayed from the registered source law before
# the panel implementation. Keep them fixed if a later experiment changes policy.
FAMILIES = ("price_feed", "collateral", "counterparty")
ACTIONS = ("continue", "de_risk", "halt_and_escalate")
STRESS_ROOTS = (5, 28, 36, 37, 48, 50, 59, 74, 77, 92, 120, 121,
                138, 150, 156, 172, 199, 205)
ELIGIBLE_ROOTS = {
    "price_feed": (36, 48, 120, 138, 150, 156, 174, 189, 225, 231),
    "collateral": (28, 37, 121, 172, 199, 205),
    "counterparty": (5, 50, 59, 74, 77, 92, 98, 188, 191, 248),
}
GOLDEN_SUMMARIES = {
    "natural": {
        "n_cases": 48,
        "n_oracle_action_disagreements": 4,
        "mean_posterior_information_gap": 0.03592475610670176,
        "count_optimal_action_revisions": 13,
        "bitmap_optimal_action_revisions": 17,
        "mean_count_policy_regret_vs_full": 0.04432299604127768,
    },
    "stress": {
        "n_cases": 18,
        "n_oracle_action_disagreements": 18,
        "mean_posterior_information_gap": 0.2683973449271681,
        "count_optimal_action_revisions": 3,
        "bitmap_optimal_action_revisions": 15,
        "mean_count_policy_regret_vs_full": 0.5700017725664852,
    },
}
GOLDEN_STRESS_FAMILIES = {
    "price_feed": (0.14825172634865752, 0.38168554547458444),
    "collateral": (0.48817613254793407, 0.8882960396217742),
    "counterparty": (0.16876417588491274, 0.44002373260309713),
}
PRIORS = (Q(9, 20), Q(7, 20), Q(1, 5))
PASS_PROBABILITIES = (Q(19, 20), Q(13, 20), Q(3, 20))
LOSSES = {
    "price_feed": ((Q(0), Q(3), Q(15)),
                   (Q(4, 5), Q(3, 2), Q(4)),
                   (Q(5, 2), Q(5, 2), Q(5, 2))),
    "collateral": ((Q(0), Q(4), Q(18)),
                   (Q(1), Q(2), Q(5)),
                   (Q(3), Q(3), Q(3))),
    "counterparty": ((Q(0), Q(4), Q(12)),
                     (Q(3, 5), Q(7, 5), Q(7, 2)),
                     (Q(23, 10), Q(23, 10), Q(23, 10))),
}


@lru_cache(maxsize=None)
def _old_count_distribution(probability):
    """Multiply the 12 Bernoulli polynomials, avoiding production binomials."""
    coefficients = [Q(1)]
    for p in [probability] * 6 + [Q(1, 2)] * 6:
        updated = [Q(0)] * (len(coefficients) + 1)
        for count, mass in enumerate(coefficients):
            updated[count] += mass * (1 - p)
            updated[count + 1] += mass * p
        coefficients = updated
    return tuple(coefficients)


@lru_cache(maxsize=None)
def _source_posterior(old_count, new_count=None, full_count=None):
    weights = []
    for prior, p in zip(PRIORS, PASS_PROBABILITIES):
        if full_count is not None:
            likelihood = p ** full_count * (1 - p) ** (12 - full_count)
        else:
            likelihood = _old_count_distribution(p)[old_count]
            if new_count is not None:
                # The probability of the observed six-position replacement
                # string suffices; its common binomial coefficient cancels.
                likelihood *= p ** new_count * (1 - p) ** (6 - new_count)
        weights.append(prior * likelihood)
    return tuple(w / sum(weights) for w in weights)


def _loss(action, posterior, family):
    return sum(p * loss for p, loss in
               zip(posterior, LOSSES[family][ACTIONS.index(action)]))


def _best(posterior, family):
    return min(ACTIONS, key=lambda action: _loss(action, posterior, family))


def _world_references(index):
    world = fixture(index)
    return (
        _source_posterior(world.old_count),
        _source_posterior(world.old_count, sum(world.replacements)),
        _source_posterior(None, full_count=world.accepted_count),
    )


def _oracle_response(packet):
    """Read only the supplied packet; use independent rational source math."""
    family = packet["finance_context"]["family"]
    if packet["phase"] == "initial":
        old = packet["old"]
        count = sum(record["match"] for record in old)
        memory = count if packet["memory_codec"] == "count" else sum(
            record["match"] * 2 ** record["slot"] for record in old)
        posterior = _source_posterior(count)
        response = {"memory": memory}
    else:
        memory = packet["memory"]
        events = packet["corrections"]
        if packet["memory_codec"] == "count":
            posterior = _source_posterior(
                memory, sum(event["new_match"] for event in events))
        else:
            bits = [(memory // (2 ** slot)) % 2 for slot in range(12)]
            for event in events:
                bits[event["slot"]] = event["new_match"]
            posterior = _source_posterior(None, full_count=sum(bits))
        response = {}
    response.update(posterior=list(map(float, posterior)),
                    action=_best(posterior, family))
    return response


def _receipt(response, status="ok"):
    return {
        "status": status, "exit_code": 0 if status == "ok" else 1,
        "response": response, "wall_seconds": 0.125,
        "input_tokens": None, "output_tokens": None,
        "stdout_sha256": sha(response), "stderr_tail": "",
    }


def _execute_oracle(argv, packet, prior_responses, timeout, experiment):
    if prior_responses != []:
        raise AssertionError("the update call replayed previous responses")
    for forbidden in ("panel", "manifest", "panel_summary", "exact_count",
                      "exact_full", "optimal_arm_action", "regime"):
        if forbidden in packet:
            raise AssertionError(f"evaluator field reached adapter: {forbidden}")
    return _receipt(_oracle_response(packet))


def _rehash(manifest):
    manifest["manifest_sha256"] = sha({
        key: value for key, value in manifest.items()
        if key != "manifest_sha256"
    })


class FinancialPanelManifestTests(unittest.TestCase):
    def test_frozen_selection_and_every_search_decision(self):
        manifest = build_manifest()
        self.assertIsNone(verify_manifest(manifest))
        self.assertEqual(panel_indices("pilot", manifest), tuple(range(6)))
        self.assertEqual(panel_indices("natural", manifest), tuple(range(48)))
        self.assertEqual(panel_indices("stress", manifest), STRESS_ROOTS)
        self.assertEqual(manifest["panels"]["stress"]["indices"],
                         list(STRESS_ROOTS))
        audit = manifest["audit"]
        self.assertEqual(len(audit), 256)
        self.assertEqual([row["index"] for row in audit], list(range(256)))
        eligible_by_family = {family: [] for family in FAMILIES}
        for index, row in enumerate(audit):
            family = FAMILIES[index % 3]
            _, count, bitmap = _world_references(index)
            eligible = _best(count, family) != _best(bitmap, family)
            selected = index in STRESS_ROOTS
            self.assertEqual(row["family"], family)
            self.assertIs(row["predicate_match"], eligible)
            self.assertIs(row["selected"], selected)
            self.assertEqual(row["decision"], "selected" if selected else
                             "quota_full" if eligible else "predicate_false")
            if eligible:
                eligible_by_family[family].append(index)
        self.assertEqual(eligible_by_family,
                         {key: list(value) for key, value in ELIGIBLE_ROOTS.items()})
        self.assertEqual(Counter(row["decision"] for row in audit),
                         {"selected": 18, "quota_full": 8, "predicate_false": 230})
        self.assertEqual(set(panel_indices("natural", manifest)) &
                         set(STRESS_ROOTS), {5, 28, 36, 37})

    def test_manifest_hashes_match_bytes_and_canonical_contents(self):
        manifest = build_manifest()
        source_hashes = manifest["source_sha256"]
        self.assertIsInstance(source_hashes, dict)
        self.assertTrue(source_hashes)
        root = Path(__file__).resolve().parents[1]
        for path, digest in source_hashes.items():
            self.assertEqual(digest, hashlib.sha256((root / path).read_bytes()).hexdigest())
        expected = sha({key: value for key, value in manifest.items()
                        if key != "manifest_sha256"})
        self.assertEqual(manifest["manifest_sha256"], expected)
        self.assertIsNone(verify_manifest(json.loads(json.dumps(manifest))))

    def test_edited_and_rehashed_manifests_are_rejected(self):
        original = build_manifest()
        mutations = []
        changed = deepcopy(original)
        changed["panels"]["stress"]["indices"][0] = 98
        mutations.append(("eligible root outside the frozen quota", changed))
        changed = deepcopy(original)
        changed["panels"]["natural"]["indices"][1] = 0
        mutations.append(("duplicated root", changed))
        changed = deepcopy(original)
        changed["audit"][5]["selected"] = False
        mutations.append(("selection audit mismatch", changed))
        changed = deepcopy(original)
        changed["audit"][0]["predicate_match"] = True
        mutations.append(("forged acceptance predicate", changed))
        changed = deepcopy(original)
        changed["audit"].pop()
        mutations.append(("truncated rejection audit", changed))
        changed = deepcopy(original)
        changed["audit"][1]["index"] = True
        mutations.append(("boolean root index", changed))
        changed = deepcopy(original)
        first_path = next(iter(changed["source_sha256"]))
        changed["source_sha256"][first_path] = "0" * 64
        mutations.append(("forged source hash", changed))
        for name, changed in mutations:
            with self.subTest(edit=name, rehashed=False):
                with self.assertRaises(ValueError):
                    verify_manifest(changed)
            _rehash(changed)
            with self.subTest(edit=name, rehashed=True):
                with self.assertRaises(ValueError):
                    verify_manifest(changed)
                with self.assertRaises(ValueError):
                    panel_indices("stress", changed)

    def test_named_panels_cannot_be_silently_truncated(self):
        manifest = build_manifest()
        with patch("systemic_risk_bench.finance_revision.execute") as execute:
            for name in ("pilot", "natural", "stress"):
                with self.subTest(panel=name), self.assertRaises(ValueError):
                    run_financial_revision(
                        ["test-only"], {"experiment_id": "invalid-truncation"},
                        mode="count", panel=name, cases=1, manifest=manifest)
            with self.assertRaises(ValueError):
                panel_indices("unknown", manifest)
            execute.assert_not_called()


class FinancialPanelScoringTests(unittest.TestCase):
    def test_independent_reference_replay_and_registered_oracle_metrics(self):
        manifest = build_manifest()
        for name in ("natural", "stress"):
            for mode in ("count", "bitmap"):
                with self.subTest(panel=name, mode=mode), patch(
                    "systemic_risk_bench.finance_revision.execute",
                    side_effect=_execute_oracle,
                ):
                    report = run_financial_revision(
                        ["test-only"], {"experiment_id": "independent-source-law"},
                        mode=mode, panel=name, manifest=manifest)
                    self.assertEqual(report["panel"], name)
                    expected = GOLDEN_SUMMARIES[name]
                    for key, value in expected.items():
                        self.assertAlmostEqual(report["panel_summary"][key], value,
                                               places=12, msg=key)
                    self.assertEqual(report["coverage"], 1.0)
                    self.assertEqual(report["n_scored"], expected["n_cases"])
                    self.assertEqual(report["action_accuracy_with_missing_penalty"], 1.0)
                    self.assertAlmostEqual(
                        report["mean_policy_regret_with_missing_penalty"], 0.0,
                        places=12)
                    full_regret = (expected["mean_count_policy_regret_vs_full"]
                                   if mode == "count" else 0.0)
                    self.assertAlmostEqual(
                        report["mean_policy_regret_vs_full_with_missing_penalty"],
                        full_regret, places=12)
                    self.assertEqual(report["initial_action_forecast_incoherent_count"], 0)
                    self.assertEqual(report["update_action_forecast_incoherent_count"], 0)
                    for flag in ("model_evaluation_claim", "scientific_confirmation_claim",
                                 "physical_memory_enforced", "model_server_state_reset_verified"):
                        self.assertIs(report[flag], False)
                    for row in report["rows"]:
                        for phase in ("initial", "update"):
                            self.assertIs(row[f"{phase}_action_forecast_coherent"], True)
                            self.assertAlmostEqual(
                                row[f"{phase}_action_forecast_regret"], 0.0, places=12)
                    for family, family_report in report["family_summaries"].items():
                        self.assertEqual(family_report["n_cases"], expected["n_cases"] // 3)
                        self.assertEqual(family_report["coverage"], 1.0)
                        if name == "stress":
                            gap, regret = GOLDEN_STRESS_FAMILIES[family]
                            self.assertEqual(family_report["n_oracle_action_disagreements"], 6)
                            self.assertEqual(family_report["count_optimal_action_revisions"], 1)
                            self.assertEqual(family_report["bitmap_optimal_action_revisions"], 5)
                            self.assertAlmostEqual(
                                family_report["mean_posterior_information_gap"], gap,
                                places=12)
                            self.assertAlmostEqual(
                                family_report["mean_count_policy_regret_vs_full"], regret,
                                places=12)

    def test_inaccurate_forecast_can_be_coherent(self):
        def reply(argv, packet, prior_responses, timeout, experiment):
            response = _oracle_response(packet)
            response.update(posterior=[0.0, 0.0, 1.0], action="halt_and_escalate")
            return _receipt(response)

        with patch("systemic_risk_bench.finance_revision.execute", side_effect=reply):
            report = run_financial_revision(
                ["test-only"], {"experiment_id": "coherent-wrong-forecast"},
                mode="bitmap", cases=1)
        row = report["rows"][0]
        self.assertEqual(row["status"], "scored")
        self.assertGreater(row["initial_excess_brier"], 0)
        self.assertGreater(row["excess_brier"], 0)
        self.assertGreater(row["initial_policy_regret"], 0)
        self.assertGreater(row["policy_regret_vs_matched"], 0)
        for phase in ("initial", "update"):
            self.assertIs(row[f"{phase}_action_forecast_coherent"], True)
            self.assertEqual(row[f"{phase}_action_forecast_regret"], 0.0)
            self.assertEqual(report[f"{phase}_action_forecast_incoherent_count"], 0)

    def test_accurate_forecast_with_expensive_action_is_incoherent(self):
        def reply(argv, packet, prior_responses, timeout, experiment):
            response = _oracle_response(packet)
            response["action"] = max(
                ACTIONS, key=lambda a: _loss(
                    a, response["posterior"], packet["finance_context"]["family"]))
            return _receipt(response)

        with patch("systemic_risk_bench.finance_revision.execute", side_effect=reply):
            report = run_financial_revision(
                ["test-only"], {"experiment_id": "incoherent-correct-forecast"},
                mode="bitmap", cases=1)
        row = report["rows"][0]
        self.assertEqual(row["status"], "scored")
        self.assertLess(row["initial_excess_brier"], 1e-20)
        self.assertLess(row["excess_brier"], 1e-20)
        for phase in ("initial", "update"):
            self.assertIs(row[f"{phase}_action_forecast_coherent"], False)
            self.assertGreater(row[f"{phase}_action_forecast_regret"], 0)
            self.assertEqual(report[f"{phase}_action_forecast_incoherent_count"], 1)
        self.assertAlmostEqual(row["initial_action_forecast_regret"],
                               row["initial_policy_regret"], places=12)
        self.assertAlmostEqual(row["update_action_forecast_regret"],
                               row["policy_regret_vs_matched"], places=12)

    def test_initial_and_update_failures_keep_full_panel_denominators(self):
        manifest = build_manifest()
        for name in ("natural", "stress"):
            indices = panel_indices(name, manifest)
            missing_index = indices[0]
            missing_id = fixture(missing_index).case_id
            missing_family = FAMILIES[missing_index % 3]
            for mode in ("count", "bitmap"):
                _, count, bitmap = _world_references(missing_index)
                missing_regret = (_loss(_best(count, missing_family), bitmap, missing_family)
                                  - _loss(_best(bitmap, missing_family), bitmap, missing_family)
                                  if mode == "count" else Q(0))
                for phase in ("initial", "update"):
                    def reply(argv, packet, prior_responses, timeout, experiment):
                        if packet["case_id"] == missing_id and packet["phase"] == phase:
                            return (_receipt(None, status="timeout") if phase == "initial"
                                    else _receipt({}))
                        return _execute_oracle(argv, packet, prior_responses, timeout, experiment)

                    with self.subTest(panel=name, mode=mode, phase=phase), patch(
                        "systemic_risk_bench.finance_revision.execute", side_effect=reply,
                    ):
                        report = run_financial_revision(
                            ["test-only"], {"experiment_id": "one-missing-root"},
                            mode=mode, panel=name, manifest=manifest)
                        n = len(indices)
                        baseline = (GOLDEN_SUMMARIES[name]["mean_count_policy_regret_vs_full"]
                                    if mode == "count" else 0.0)
                        self.assertEqual(report["n_cases"], n)
                        self.assertEqual(report["n_scored"], n - 1)
                        self.assertEqual(report["coverage"], (n - 1) / n)
                        self.assertEqual(report["action_accuracy_with_missing_penalty"],
                                         (n - 1) / n)
                        self.assertAlmostEqual(report["mean_policy_regret_with_missing_penalty"],
                                               20.0 / n, places=12)
                        self.assertAlmostEqual(report["mean_excess_brier_with_missing_penalty"],
                                               2.0 / n, places=12)
                        self.assertAlmostEqual(
                            report["mean_policy_regret_vs_full_with_missing_penalty"],
                            (baseline * n - float(missing_regret) + 20.0) / n, places=12)
                        self.assertAlmostEqual(
                            report["panel_summary"]["mean_count_policy_regret_vs_full"],
                            GOLDEN_SUMMARIES[name]["mean_count_policy_regret_vs_full"],
                            places=12)
                        family_n = n // 3
                        self.assertEqual(
                            report["family_summaries"][missing_family]["coverage"],
                            (family_n - 1) / family_n)
                        self.assertEqual(report["model_calls_attempted"],
                                         2 * n - (phase == "initial"))


if __name__ == "__main__":
    unittest.main()
