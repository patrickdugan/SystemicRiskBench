import math
import unittest

from systemic_risk_bench.risk import (
    joint_state_credit_loss, netting_exposure, settlement_principal_loss,
    tail_risk, unilateral_cva,
)
from systemic_risk_bench.scoring import brier, score_numeric
from systemic_risk_bench.simulation import simulate
from systemic_risk_bench.suite import numerical_answers


class RiskTests(unittest.TestCase):
    def test_known_cva_and_zero_recovery_loss(self):
        self.assertAlmostEqual(unilateral_cva([1e6, 2e6], [.01, .015], [.99, .97], .4), 23400)
        self.assertEqual(unilateral_cva([1e6], [.2], [1], 1), 0)

    def test_wrong_way_joint_is_not_product_of_marginals(self):
        self.assertAlmostEqual(joint_state_credit_loss([1e5, 1e6], [.01, .2], [.9, .1], .4), 12540)
        self.assertAlmostEqual(numerical_answers()["q-wrong-way"]["independent_loss"], 3306)

    def test_es_fractional_boundary_and_ties(self):
        result = tail_risk([0, 10, 20, 100], [.9, .05, .04, .01], .975)
        self.assertEqual(result["var"], 20)
        self.assertAlmostEqual(result["expected_shortfall"], 52)
        self.assertEqual(tail_risk([3, 3, 3], [.2, .3, .5], .95)["expected_shortfall"], 3)
        self.assertEqual(tail_risk([-10, -5], [.5, .5], .9)["expected_shortfall"], -5)
        self.assertEqual(tail_risk([0, 1], [.5, .5], .5000000000005)["var"], 1)

    def test_zero_probability_extreme_does_not_change_tail(self):
        self.assertEqual(tail_risk([1e9, 10], [0, 1], .99)["expected_shortfall"], 10)

    def test_pvp_only_eliminates_principal_loss_in_this_calculator(self):
        self.assertEqual(settlement_principal_loss(1e7, .002, .4, False), 12000)
        self.assertEqual(settlement_principal_loss(1e7, .002, .4, True), 0)

    def test_legal_scope_of_netting(self):
        self.assertEqual(netting_exposure([[100, -80]]), 20)
        self.assertEqual(netting_exposure([[100], [-80]]), 100)

    def test_invalid_inputs_are_rejected(self):
        for invalid in (float("nan"), float("inf"), True, "0.1"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                unilateral_cva([invalid], [.1], [1], .4)
        with self.assertRaises(ValueError):
            tail_risk([1, 2], [.2, .2], .95)
        with self.assertRaises(ValueError):
            unilateral_cva([1, 2], [.6, .6], [1, 1], .4)
        with self.assertRaises(ValueError):
            unilateral_cva([1, 2], [.1], [1], .4)


class ScoringTests(unittest.TestCase):
    def test_missing_tasks_stay_in_denominator(self):
        report = score_numeric([{"id": "q-cva-term", "estimates": {"cva": 23400}}])
        self.assertEqual(len(report["checks"]), 13)
        self.assertAlmostEqual(report["numeric_micro_accuracy"], 1/13)
        self.assertIsNone(report["reasoning_score"])

    def test_duplicate_and_unknown_ids_cannot_inflate_score(self):
        response = {"id": "q-cva-term", "estimates": {"cva": 23400}}
        with self.assertRaises(ValueError):
            score_numeric([response, response])
        with self.assertRaises(ValueError):
            score_numeric([{"id": "made_up", "estimates": {}}])

    def test_boolean_not_numeric_and_empty_is_zero(self):
        self.assertEqual(score_numeric([])["numeric_micro_accuracy"], 0)
        response = {"id": "q-settlement", "estimates": {"pvp_principal_el": False}}
        self.assertEqual(score_numeric([response])["numeric_micro_accuracy"], 0)

    def test_brier_known_values_and_probability_validation(self):
        report = brier([{"id": "a", "probability": .8, "outcome": 1},
                        {"id": "b", "probability": .2, "outcome": 0}])
        self.assertAlmostEqual(report["brier_score"], .04)
        with self.assertRaises(ValueError):
            brier([{"id": "a", "probability": 1.2, "outcome": 1}])


class SimulationTests(unittest.TestCase):
    def test_fixed_aggregate_capital_does_not_depend_on_agent_count(self):
        a = simulate(agents=1, fixed_total_capital=1e9)
        b = simulate(agents=10_000_000, fixed_total_capital=1e9)
        for field in ("final_price", "uncapped_book_equity_loss", "default_capital_weight", "trace"):
            self.assertEqual(a[field], b[field])

    def test_no_impact_is_negative_control(self):
        result = simulate(impact=0)
        self.assertAlmostEqual(result["endogenous_book_loss"], 0, places=5)
        self.assertAlmostEqual(result["final_price"], .92)
        self.assertTrue(result["converged"])

    def test_no_shock_produces_no_sales(self):
        result = simulate(shock=0)
        self.assertEqual(result["rounds"], 0)
        self.assertEqual(result["uncapped_book_equity_loss"], 0)

    def test_larger_population_with_added_capital_increases_pressure(self):
        small = simulate(agents=1)
        large = simulate(agents=1_000_000)
        self.assertLess(large["final_price"], small["final_price"])
        self.assertEqual(large["independent_agent_decisions_simulated"], 0)

    def test_truncation_is_reported(self):
        result = simulate(max_rounds=1)
        self.assertFalse(result["converged"])
        self.assertTrue(math.isfinite(result["final_price"]))

    def test_investor_loss_and_creditor_shortfall_are_separate(self):
        result = simulate()
        self.assertLessEqual(result["limited_liability_investor_loss"], 1e9)
        self.assertAlmostEqual(result["uncapped_book_equity_loss"],
                               result["limited_liability_investor_loss"] + result["creditor_shortfall"])

    def test_numerical_floor_is_not_claimed_as_convergence(self):
        result = simulate(impact=1e6)
        self.assertTrue(result["price_floor_hit"])
        self.assertTrue(result["impact_cap_hit"])
        self.assertFalse(result["converged"])


if __name__ == "__main__":
    unittest.main()
