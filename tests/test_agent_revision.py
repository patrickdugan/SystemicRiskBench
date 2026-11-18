"""SRB-REV-01: explicit agent memory, correction provenance and Bayes tests.

Only public deterministic development fixtures are opened.
"""
from dataclasses import replace
from fractions import Fraction as Q
from itertools import product
from hashlib import sha256
import json
import math
import sys
import unittest

from systemic_risk_bench.agent_revision import (
    J, N, MATCH, PRIORS, count_posterior, fixture, initial_packet,
    initial_posterior, bitmap_posterior, run_agent_revision, parse_forecast,
    signed_events, update_packet, valid_posterior, validate_memory, verify_events
)


def independent_old_count_oracle(m, q):
    """Literal original 2^12 old-vector likelihood, with specific final bits.

    This never calls the analytic coarse scorer or binomial combinatorics.
    The replacement vector's binomial multiplicity cancels in normalization.
    """
    weights=[]
    for prior,t in zip(PRIORS,MATCH):
        mass=Q(0)
        for old in product((0,1),repeat=N):
            if sum(old)!=m:
                continue
            w=prior
            for i,b in enumerate(old):
                p=Q(1,2) if i<J else t
                w*=p if b else 1-p
            w*=t**q * (1-t)**(J-q)
            mass+=w
        weights.append(mass)
    z=sum(weights,Q(0))
    return tuple(a/z for a in weights)


class AgentRevisionTests(unittest.TestCase):
    def test_fixture_is_deterministic_and_private(self):
        ids=set()
        for index in range(32):
            w=fixture(index)
            self.assertEqual(w,fixture(index))
            self.assertNotIn(w.case_id,ids)
            ids.add(w.case_id)
            self.assertEqual(len(w.old),12)
            self.assertEqual(len(w.slots),6)
            self.assertEqual(tuple(sorted(w.slots)),w.slots)
            self.assertEqual(len(set(w.slots)),6)
            self.assertEqual(len(w.replacements),6)
            for mode in ("count","bitmap"):
                a=initial_packet(w,mode)
                b=update_packet(w,mode,w.old_count if mode=="count" else w.old_mask)
                self.assertNotIn("regime",json.dumps(a))
                self.assertNotIn("regime",json.dumps(b))
                self.assertNotIn(w.host_key.hex(),json.dumps(a)+json.dumps(b))
                self.assertNotIn("corrections",a)
                self.assertEqual(a["correction_schedule"],"hidden_until_update")
                self.assertEqual(b["old"],"not_replayed")
                self.assertNotIn("original_history",b)
                self.assertEqual(len(b["corrections"]),6)
        for bad in (-1,256,True):
            with self.assertRaises(ValueError):
                fixture(bad)

    def test_host_signatures_detect_tampering(self):
        w=fixture(0)
        signed=signed_events(w)
        self.assertTrue(verify_events(w,signed))
        altered=[dict(s) for s in signed]
        altered[0]["new_match"]=1-altered[0]["new_match"]
        self.assertFalse(verify_events(w,altered))
        altered=[dict(s) for s in signed]
        altered[0]["synthetic_receipt_hmac"]="0"*64
        self.assertFalse(verify_events(w,altered))
        altered=[dict(s) for s in signed]
        altered[0]["new_version"]=2
        self.assertFalse(verify_events(w,altered))
        altered=[dict(s) for s in signed]
        altered[1],altered[0]=altered[0],altered[1]
        self.assertFalse(verify_events(w,altered))

    def test_analytic_count_matches_independent_raw_history(self):
        for m,q in ((0,0),(1,6),(3,1),(6,3),(8,2),(10,5),(12,6)):
            self.assertEqual(count_posterior(m,q),
                             independent_old_count_oracle(m,q))
        for m in range(13):
            self.assertEqual(sum(initial_posterior(m),Q(0)),Q(1))
        self.assertNotEqual(count_posterior(6,3),valid_posterior(6))
        with self.assertRaises(ValueError):
            count_posterior(12,7)

    def test_bitmap_replay_tracks_exact_final_bayes(self):
        for i in range(48):
            w=fixture(i)
            corrections=tuple(zip(w.slots,w.replacements))
            self.assertEqual(bitmap_posterior(w.old_mask,corrections),w.exact_full)
            self.assertEqual(count_posterior(w.old_count,sum(w.replacements)),
                             w.exact_count)
            self.assertGreaterEqual(sum((a-b)**2 for a,b in
                                        zip(w.exact_count,w.exact_full)),Q(0))
        for invalid in (
            ((0,0),)*6,
            ((-1,0),)*6,
            ((0,True),)*6,
        ):
            with self.assertRaises(ValueError):
                bitmap_posterior(0,invalid)

    def test_declared_state_and_forecast_validation(self):
        w=fixture(0)
        full=[float(x) for x in initial_posterior(w.old_count)]
        self.assertEqual(validate_memory({"memory":w.old_count,"posterior":full},
                                         w,"count"),w.old_count)
        self.assertEqual(validate_memory({"memory":w.old_mask,"posterior":full},
                                         w,"bitmap"),w.old_mask)
        for bad in (True, -1, 4096, "6"):
            with self.assertRaises(ValueError):
                validate_memory({"memory":bad,"posterior":full},w,"bitmap")
        if w.old_count!=0:
            with self.assertRaises(ValueError):
                validate_memory({"memory":0,"posterior":full},w,"count")
        for payload in (
            {"posterior":[0.5,0.5,0.5]},
            {"posterior":[True,0,0]},
            {"posterior":[float("nan"),0.5,0.5]},
            {"posterior":[0.6,0.4,0],"freeform_history":"smuggle"},
            {"posterior":[0.5,0.5]},
        ):
            with self.assertRaises(ValueError):
                parse_forecast(payload,"update")

    def test_reference_adapter_in_two_real_subprocesses(self):
        adapter=[sys.executable,"-m","examples.agent_revision_fixture_adapter"]
        for mode in ("count","bitmap"):
            result=run_agent_revision(adapter,{"experiment_id":"reference-only"},mode=mode,
                                      cases=10,timeout=10)
            self.assertEqual(result["coverage"],1)
            self.assertEqual(result["n_scored"],10)
            self.assertEqual(result["model_calls_attempted"],20)
            self.assertTrue(result["prior_responses_suppressed"])
            self.assertTrue(result["initial_old_history_excluded_from_update_packets"])
            self.assertEqual(result["memory_logical_bits"],4 if mode=="count" else 12)
            self.assertLess(result["mean_excess_brier_with_missing_penalty"],1e-22)
            for row in result["rows"]:
                self.assertEqual(row["status"],"scored")
                self.assertEqual(row["initial_receipt"]["status"],"ok")
                self.assertEqual(row["update_receipt"]["status"],"ok")
                self.assertIsNone(row["initial_error"])

    def test_missing_or_invalid_adapter_is_in_denominator(self):
        invalid=[sys.executable,"-c","print('{}')"]
        result=run_agent_revision(invalid,{"experiment_id":"bad"},mode="count",cases=2)
        self.assertEqual(result["coverage"],0)
        self.assertEqual(result["n_scored"],0)
        self.assertEqual(result["mean_excess_brier_with_missing_penalty"],2)
        self.assertEqual(result["model_calls_attempted"],2)
        self.assertTrue(all(x["status"]=="initial_invalid" for x in result["rows"]))

    def test_no_false_science_claims_or_sandbox_assertions(self):
        result=run_agent_revision([sys.executable,"-c","print('{}')"],
                                  {"experiment_id":"no-sandbox"},mode="bitmap",cases=1)
        self.assertFalse(result["scientific_confirmation_claim"])
        self.assertFalse(result["physical_memory_enforced"])
        self.assertFalse(result["adapter_process_sandboxed"])
        self.assertEqual(result["authority"],"read_only_no_execution")


if __name__=="__main__":
    unittest.main()
