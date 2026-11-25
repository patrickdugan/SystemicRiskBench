"""Policy choice, information constraints and exact loss accounting checks."""
from __future__ import annotations

import copy
from contextlib import redirect_stderr
from fractions import Fraction
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from systemic_risk_bench.cli import main
from systemic_risk_bench.policy import (
    evaluate_choices, execute_policy, public_packets, run_policy,
    validate_policy_config,
)
from systemic_risk_bench.runner import sha


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/policy-simulation-v1.json"
BASELINE = "no_liquidity_support"
SUPPORT = "triple_depth_backstop"


def toy_bank():
    """Unequal world masses and opposite choices under one observation."""
    def world(identifier, mass, visible, base, support):
        return {"id": identifier, "mass": mass, "visible": [visible],
                "queries": [], "outcomes": {
                    BASELINE: {"node_loss": [str(x) for x in base]},
                    SUPPORT: {"node_loss": [str(x) for x in support]},
                }}
    return {
        "actions": [{"name": BASELINE, "cost": "0"},
                    {"name": SUPPORT, "cost": "2"}],
        "baseline": BASELINE, "tail_alpha": "3/4",
        "worlds": [world("calm", 3, 0, (0, 0), (0, 0)),
                   world("crisis", 1, 0, (8, 4), (2, 0)),
                   world("other", 2, 1, (1, 0), (0, 0))],
    }


class PolicyAccountingTests(unittest.TestCase):
    def test_observation_oracle_uses_weighted_groups_and_full_cost(self):
        scores = evaluate_choices(toy_bank(), {0: BASELINE, 1: SUPPORT},
                                  feasible_actions=[BASELINE, SUPPORT])
        selected = scores["selected_policy"]
        self.assertEqual(Fraction(selected["expected_investor_loss"]), Fraction(4, 3))
        self.assertEqual(Fraction(selected["expected_creditor_shortfall"]), Fraction(2, 3))
        self.assertEqual(Fraction(selected["expected_action_cost"]), Fraction(2, 3))
        self.assertEqual(Fraction(selected["expected_total_cost"]), Fraction(8, 3))
        self.assertEqual(Fraction(scores["baseline"]["expected_total_cost"]), Fraction(7, 3))
        self.assertEqual(Fraction(scores["observation_oracle"]["expected_total_cost"]), 2)
        self.assertEqual(Fraction(scores["perfect_information_bound"]["expected_total_cost"]), 1)
        self.assertEqual(Fraction(scores["expected_regret_vs_observation_oracle"]), Fraction(2, 3))
        self.assertEqual(Fraction(scores["information_gap"]), 1)
        signed = [Fraction(row["regret_vs_observation_oracle"])
                  for row in scores["world_results"]]
        self.assertEqual(signed, [Fraction(-2), Fraction(8), Fraction(1)])

    def test_fractional_tail_includes_cost_and_partial_boundary_mass(self):
        scores = evaluate_choices(toy_bank(), {0: BASELINE, 1: SUPPORT},
                                  feasible_actions=[BASELINE, SUPPORT])
        # Six mass units, a 1.5-unit tail: one at $12 and half at $2.
        self.assertEqual(Fraction(scores["selected_policy"]["expected_shortfall_total_cost"]),
                         Fraction(26, 3))
        self.assertEqual(Fraction(scores["selected_policy"]["max_total_cost"]), 12)
        self.assertEqual(Fraction(scores["observation_oracle"]["expected_shortfall_total_cost"]),
                         Fraction(10, 3))
        self.assertEqual(Fraction(scores["perfect_information_bound"]["expected_shortfall_total_cost"]), 3)

    def test_oracle_respects_feasible_actions(self):
        scores = evaluate_choices(toy_bank(), {0: BASELINE, 1: BASELINE},
                                  feasible_actions=[BASELINE])
        expected = Fraction(7, 3)
        for name in ("selected_policy", "baseline", "observation_oracle", "perfect_information_bound"):
            self.assertEqual(Fraction(scores[name]["expected_total_cost"]), expected)
        self.assertEqual(Fraction(scores["expected_regret_vs_observation_oracle"]), 0)
        self.assertEqual(Fraction(scores["information_gap"]), 0)

    def test_incomplete_or_unavailable_choices_are_rejected(self):
        for choices, feasible in (({0: BASELINE}, [BASELINE, SUPPORT]),
                                  ({0: BASELINE, 1: SUPPORT, 2: BASELINE}, [BASELINE, SUPPORT]),
                                  ({0: BASELINE, 1: "invented"}, [BASELINE, SUPPORT]),
                                  ({0: BASELINE, 1: SUPPORT}, [BASELINE])):
            with self.subTest(choices=choices, feasible=feasible), self.assertRaises(ValueError):
                evaluate_choices(toy_bank(), choices, feasible_actions=feasible)


class PolicyHarnessTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_public_packets_are_invariant_to_hidden_state(self):
        original = public_packets(self.config)
        changed = copy.deepcopy(self.config)
        changed["simulation"]["depths"] = ["400000", "7000000"]
        changed["simulation"]["cohort_profiles"] = ["heterogeneous"]
        changed["simulation"]["mass_per_scenario"] = 7
        self.assertEqual(public_packets(changed), original)
        self.assertEqual(len(original), len(self.config["simulation"]["shocks"]))
        encoded = json.dumps(original)
        for forbidden in ("worlds", "outcomes", "queries", "cohort_profiles",
                          "depth_tier", "config_sha256", "node_loss"):
            self.assertNotIn('"' + forbidden + '"', encoded)

    def test_exact_budget_and_cost_contract(self):
        for value in ("-1", "1/1000", True, 10000):
            changed = copy.deepcopy(self.config)
            changed["action_budget"] = value
            with self.subTest(budget=value), self.assertRaises(ValueError):
                validate_policy_config(changed)
        changed = copy.deepcopy(self.config)
        changed["simulation"]["actions"][1]["cost"] = "1/1000"
        with self.assertRaises(ValueError):
            validate_policy_config(changed)

    def test_unrepresentable_simulator_parameters_fail_before_adapters(self):
        invalid = []
        for key, value in (("depths", ["1e-1000"]),
                           ("initial_capital", "1e-1000"),
                           ("initial_capital", "1e309"),
                           ("initial_capital", "1e308"),
                           ("impact", "1e-1000"),
                           ("shocks", ["1e-1000"])):
            changed = copy.deepcopy(self.config)
            changed["simulation"][key] = value
            invalid.append((key, value, changed))
        changed = copy.deepcopy(self.config)
        changed["simulation"]["actions"][1]["depth_multiplier"] = 10 ** 400
        invalid.append(("depth_multiplier", "10**400", changed))
        for key, value, changed in invalid:
            with self.subTest(key=key, value=value), \
                    patch("systemic_risk_bench.policy.execute_policy") as execute, \
                    patch("systemic_risk_bench.policy.build_bank") as build:
                with self.assertRaises(ValueError):
                    run_policy(changed, adapter_argv=["operator-adapter"])
                execute.assert_not_called()
                build.assert_not_called()

    def test_every_choice_is_frozen_before_any_simulation(self):
        from systemic_risk_bench.policy import build_bank
        events = []
        def decide(argv, packet, timeout):
            events.append("choice")
            return {"status": "ok", "response": {"action": BASELINE}, "wall_seconds": 0}
        def simulate_after_freeze(*args, **kwargs):
            self.assertEqual(events, ["choice"] * len(public_packets(self.config)))
            events.append("simulation")
            return build_bank(*args, **kwargs)
        with patch("systemic_risk_bench.policy.execute_policy", side_effect=decide), \
                patch("systemic_risk_bench.policy.build_bank", side_effect=simulate_after_freeze):
            result = run_policy(self.config, adapter_argv=["operator-adapter"])
        self.assertEqual(result["adapter_invocations"], len(public_packets(self.config)))
        self.assertIsNone(result["model_calls"])
        self.assertEqual(events[-1], "simulation")

    def test_invalid_and_unaffordable_actions_have_recorded_baseline_fallback(self):
        changed = copy.deepcopy(self.config)
        changed["action_budget"] = "0"
        responses = [
            {"status": "ok", "response": {"action": SUPPORT}},
            {"status": "ok", "response": {"action": "invented"}},
            {"status": "ok", "response": {"action": BASELINE, "hidden_override": 1}},
            {"status": "ok", "response": {"action": BASELINE, "rationale": 3}},
            {"status": "timeout", "response": None},
        ]
        for response in responses:
            response["wall_seconds"] = 0
        with patch("systemic_risk_bench.policy.execute_policy", side_effect=responses):
            result = run_policy(changed, adapter_argv=["operator-adapter"])
        self.assertEqual([row["status"] for row in result["receipts"]],
                         ["unaffordable_action", "invalid_action", "invalid_response",
                          "invalid_response", "timeout"])
        self.assertTrue(all(row["fallback_used"] for row in result["receipts"]))
        self.assertEqual({row["selected_action"] for row in result["receipts"]}, {BASELINE})
        self.assertEqual(result["scores"]["selected_policy"], result["scores"]["baseline"])

    def test_nonconvergence_preserves_successful_decisions_and_their_freeze(self):
        changed = copy.deepcopy(self.config)
        changed["simulation"]["max_rounds"] = 1
        def decide(argv, packet, timeout):
            return {"status": "ok", "response": {"action": BASELINE}, "wall_seconds": 0}
        with patch("systemic_risk_bench.policy.execute_policy", side_effect=decide) as execute:
            result = run_policy(changed, adapter_argv=["operator-adapter"])
        self.assertEqual(result["run_status"], "evaluation_failed")
        self.assertIsNone(result["scores"])
        self.assertEqual(execute.call_count, len(public_packets(changed)))
        self.assertEqual(len(result["receipts"]), execute.call_count)
        self.assertEqual({row["status"] for row in result["receipts"]}, {"ok"})
        self.assertEqual({row["selected_action"] for row in result["receipts"]}, {BASELINE})
        self.assertTrue(result["decision_freeze"]["completed_before_counterfactual_simulation"])
        frozen = [{key: row[key] for key in ("observation_index", "packet_sha256", "status",
                                            "response", "selected_action", "fallback_used")}
                  for row in result["receipts"]]
        self.assertEqual(result["decision_freeze"]["sha256"], sha(frozen))
        self.assertTrue(result["evaluation_error"]["phase"])
        self.assertEqual(result["evaluation_error"]["type"], "ValueError")
        self.assertIn("nonconverged", result["evaluation_error"]["message"])

    def test_mode_selection_fails_before_adapters_or_simulation(self):
        with patch("systemic_risk_bench.policy.execute_policy") as execute, \
                patch("systemic_risk_bench.policy.build_bank") as build:
            for kwargs in ({}, {"fixture": "baseline", "adapter_argv": ["adapter"]},
                           {"fixture": "unregistered"},
                           {"adapter_argv": ["adapter"], "timeout": float("nan")}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    run_policy(self.config, **kwargs)
        execute.assert_not_called()
        build.assert_not_called()

    def test_zero_impact_makes_blanket_support_costly(self):
        changed = copy.deepcopy(self.config)
        changed["simulation"]["impact"] = "0"
        baseline = run_policy(changed, fixture="baseline")
        support = run_policy(changed, fixture="always_support")
        cost = Fraction(changed["simulation"]["actions"][1]["cost"])
        self.assertEqual(baseline["model_calls"], 0)
        self.assertEqual(support["adapter_invocations"], 0)
        self.assertEqual(Fraction(support["scores"]["selected_policy"]["expected_total_cost"])
                         - Fraction(baseline["scores"]["selected_policy"]["expected_total_cost"]), cost)
        self.assertEqual(Fraction(support["scores"]["expected_regret_vs_observation_oracle"]), cost)

    def test_fixed_capital_headcount_preserves_policy_outcomes(self):
        low = copy.deepcopy(self.config)
        high = copy.deepcopy(self.config)
        low["simulation"]["agents_represented"] = 1
        high["simulation"]["agents_represented"] = 10_000_000
        low_run = run_policy(low, fixture="always_support")
        high_run = run_policy(high, fixture="always_support")
        self.assertEqual(low_run["scores"], high_run["scores"])

    def test_adapter_parser_rejects_duplicate_keys_and_nonfinite_json(self):
        packet = public_packets(self.config)[0]
        for output in ('{"action":"a","action":"b"}',
                       '{"action":NaN}', '{"action":1e999}'):
            argv = [sys.executable, "-c", "print(" + repr(output) + ")"]
            with self.subTest(output=output):
                self.assertEqual(execute_policy(argv, packet, 5)["status"], "invalid_json")

    def test_adapter_exit_failure_and_timeout_keep_failed_receipts(self):
        packet = public_packets(self.config)[0]
        failed = execute_policy([sys.executable, "-c", "raise SystemExit(7)"], packet, 5)
        self.assertEqual(failed["status"], "adapter_error")
        self.assertEqual(failed["exit_code"], 7)
        self.assertIsNone(failed["response"])
        timed_out = execute_policy([sys.executable, "-c", "import time; time.sleep(10)"], packet, .02)
        self.assertEqual(timed_out["status"], "timeout")
        self.assertIsNone(timed_out["response"])

    def test_cli_fixture_round_trip(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "policy.json"
            self.assertEqual(main(["policy-run", "--config", str(CONFIG),
                                   "--fixture", "always_support", "--output", str(output)]), 0)
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["run_status"], "complete")
        self.assertGreater(Fraction(result["scores"]["selected_policy"]["expected_action_cost"]), 0)

    def test_cli_writes_failed_evaluation_before_exiting_nonzero(self):
        changed = copy.deepcopy(self.config)
        changed["simulation"]["max_rounds"] = 1
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "limited-rounds.json"
            config.write_text(json.dumps(changed), encoding="utf-8")
            output = Path(tmp) / "failed-policy.json"
            stderr = io.StringIO()
            with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                main(["policy-run", "--config", str(config), "--fixture", "baseline",
                      "--output", str(output)])
            self.assertEqual(raised.exception.code, 2)
            self.assertTrue(output.is_file())
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["run_status"], "evaluation_failed")
        self.assertIsNone(result["scores"])
        self.assertEqual(len(result["receipts"]), len(public_packets(changed)))
        self.assertTrue(stderr.getvalue().strip())


if __name__ == "__main__":
    unittest.main()
