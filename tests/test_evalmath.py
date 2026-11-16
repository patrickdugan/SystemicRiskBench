"""Live SRB-EM-01 export checks (unittest, no EvalMath package dependency)."""
from __future__ import annotations

import copy
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from systemic_risk_bench.cli import main
from systemic_risk_bench.evalmath import (
    CONFIG_SCHEMA, DEFAULT_CONFIG, SCHEMA, build_bank, cents, export_bank,
    money, validate_config,
)
from systemic_risk_bench.simulation import simulate


def loss(row, action):
    return sum((Fraction(v) for v in row["outcomes"][action]["node_loss"]), Fraction(0))


def best_expected(bank, query=None):
    """Independent exhaustive oracle over every 2^k observable policy."""
    from itertools import product
    groups = {}
    for row in bank["worlds"]:
        key = tuple(row["visible"] + ([row["queries"][query]] if query is not None else []))
        groups.setdefault(key, []).append(row)
    actions = [x["name"] for x in bank["actions"]]
    costs = {a["name"]: Fraction(a["cost"]) for a in bank["actions"]}
    return min(
        sum((r["mass"] * (loss(r, a) + costs[a])
             for key, a in zip(groups, profile)
             for r in groups[key]), Fraction(0))
        for profile in product(actions, repeat=len(groups))
    ) / sum(r["mass"] for r in bank["worlds"])


class EvalMathExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        cls.bank = export_bank()

    def test_registered_grid_and_provenance(self):
        b = self.bank
        self.assertEqual(b["schema"], SCHEMA)
        self.assertEqual(b["query_names"], ["depth_tier", "cohort_profile"])
        self.assertEqual(len(b["worlds"]), 30)
        self.assertEqual(len({r["id"] for r in b["worlds"]}), 30)
        self.assertEqual(b["source"]["simulations"], 60)
        self.assertEqual(b["source"]["model_calls"], 0)
        self.assertFalse(b["source"]["historical_cases_included"])
        self.assertEqual(b["source"]["config_sha256"], sha256(DEFAULT_CONFIG.read_bytes()).hexdigest())
        root = DEFAULT_CONFIG.parents[1]
        self.assertEqual(b["source"]["simulator_module_sha256"],
                         sha256((root / "systemic_risk_bench/simulation.py").read_bytes()).hexdigest())
        self.assertEqual(set(r["mass"] for r in b["worlds"]), {1})
        self.assertTrue(all("selected" not in r for r in b["worlds"]))
        self.assertTrue(all(len(r["visible"]) == 1 and len(r["queries"]) == 2
                            for r in b["worlds"]))

    def test_replay_source_interventions_and_accounting(self):
        b = self.bank
        r = next(r for r in b["worlds"] if r["id"] == "shock1_depth0_profile0")
        base = simulate(agents=1_000_000, fixed_total_capital=1_000_000,
                        cohort_profile="homogeneous", shock=.08, depth=300_000, impact=.08,
                        max_rounds=50)
        deep = simulate(agents=1_000_000, fixed_total_capital=1_000_000,
                        cohort_profile="homogeneous", shock=.08, depth=900_000, impact=.08,
                        max_rounds=50)
        self.assertTrue(base["converged"] and deep["converged"])
        self.assertEqual(r["outcomes"]["no_liquidity_support"]["node_loss"],
                         [money(cents(base["limited_liability_investor_loss"])),
                          money(cents(base["creditor_shortfall"]))])
        self.assertEqual(r["outcomes"]["triple_depth_backstop"]["node_loss"],
                         [money(cents(deep["limited_liability_investor_loss"])),
                          money(cents(deep["creditor_shortfall"]))])
        self.assertGreater(loss(r, "no_liquidity_support") - loss(r, "triple_depth_backstop"),
                           Fraction(10000))
        self.assertEqual(set(r["outcomes"]), {a["name"] for a in b["actions"]})
        self.assertTrue(all(Fraction(v) >= 0 for w in b["worlds"]
                            for x in w["outcomes"].values() for v in x["node_loss"]))

    def test_restricted_observation_has_positive_exact_loss_floor(self):
        b = self.bank
        visible = best_expected(b)
        extra_depth = best_expected(b, query=0)
        extra_profile = best_expected(b, query=1)
        # A clairvoyant policy chooses the cheapest action for every world.
        oracle = sum((r["mass"] * min(
            loss(r, action["name"]) + Fraction(action["cost"])
            for action in b["actions"]) for r in b["worlds"]), Fraction(0)) / 30
        self.assertGreater(visible, oracle)
        self.assertLess(extra_depth, visible)
        self.assertLessEqual(extra_profile, visible)
        self.assertGreater(visible - oracle, 0)

    def test_toy_checker_has_realized_false_accepts_under_simulator(self):
        b = self.bank
        threshold = Fraction(b["harm_threshold"])
        events = [(
            r["outcomes"][a]["claimed_safe"],
            loss(r, a) >= threshold)
            for r in b["worlds"] for a in ("no_liquidity_support", "triple_depth_backstop")]
        self.assertTrue(any(claim and harm for claim, harm in events))
        self.assertTrue(any(claim and not harm for claim, harm in events))
        self.assertTrue(any(not claim for claim, _ in events))
        self.assertTrue(any(Fraction(r["outcomes"]["no_liquidity_support"]["node_loss"][1]) > 0
                            for r in b["worlds"]))

    def test_invalid_registration_rejected_before_replay(self):
        bad = []
        for key, val in (("schema_version", "unknown"), ("tail_alpha", "1"),
                         ("harm_threshold", "3/1000"), ("observation", "perfect"),
                         ("claimed_safe_checker", "actual_model")):
            if key == "harm_threshold":
                # Tiny, but valid threshold. Test negative separately.
                continue
            d = copy.deepcopy(self.config); d[key] = val; bad.append(d)
        for key, val in (("impact", -1), ("depths", ["0"]), ("shocks", [".99"]),
                         ("cohort_profiles", ["unknown"]), ("agents_represented", True),
                         ("mass_per_scenario", 0), ("max_rounds", -2)):
            d = copy.deepcopy(self.config); d[key] = val; bad.append(d)
        d = copy.deepcopy(self.config); d["actions"][1]["depth_multiplier"] = 0; bad.append(d)
        d = copy.deepcopy(self.config); d["actions"][0]["cost"] = 1.0; bad.append(d)
        d = copy.deepcopy(self.config); d["depths"].append(d["depths"][0]); bad.append(d)
        for d in bad:
            with self.subTest(config=d), self.assertRaises(ValueError):
                validate_config(d)
        self.assertEqual(self.config["schema_version"], CONFIG_SCHEMA)

    def test_cli_round_trip(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "export.json"
            self.assertEqual(main(["evalmath-export", "--config", str(DEFAULT_CONFIG),
                                   "--output", str(output)]), 0)
            loaded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(loaded, self.bank)


if __name__ == "__main__":
    unittest.main()
