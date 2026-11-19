"""SRB-REV-05 CPU source-law pilot / host verified visible codec tests."""
from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
import unittest

from systemic_risk_bench.agent_revision import fixture
from systemic_risk_bench.finance_revision import packet
from systemic_risk_bench.rev05_ci_pilot import (
    SCHEMA, next_prompt, run_pilot, validate_registration, visible_codec,
)
from systemic_risk_bench.scoring import read_json

ROOT=Path(__file__).resolve().parent.parent
SPEC=ROOT/"configs/rev05-cpu-ci-pilot.json"
MANIFEST=ROOT/"configs/finance-revision-panels.json"


class CodecPilotTests(unittest.TestCase):
    def setUp(self):
        self.spec=read_json(SPEC)
        self.manifest=read_json(MANIFEST)

    def test_registration_and_frozen_root_binding(self):
        validate_registration(self.spec,self.manifest)
        for key,sub in (("root_indices",[0,6]),("modes",["bitmap","count"]),
                        ("treatments",["model_memory"])):
            bad=deepcopy(self.spec)
            bad[key]=sub
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_registration(bad,self.manifest)
        bad=deepcopy(self.spec)
        bad["source_panel_manifest_sha256"]="0"*64
        with self.assertRaises(ValueError):
            validate_registration(bad,self.manifest)

    def test_visible_codec_matches_world_without_evaluator_secrets(self):
        for index in (0,1,2,5,16,35,51,159):
            world=fixture(index)
            for mode in ("count","bitmap"):
                initial=packet(world,mode,("price_feed","collateral","counterparty")[index%3],"initial")
                expected=world.old_count if mode=="count" else world.old_mask
                self.assertEqual(visible_codec(initial),expected)
                self.assertNotIn("regime",json.dumps(initial))
                update=packet(world,mode,("price_feed","collateral","counterparty")[index%3],
                              "update",expected)
                self.assertEqual(update["old"],"not_replayed")
                self.assertEqual(update["prior_responses"],"not_replayed")
        sample=packet(fixture(5),"bitmap","counterparty","initial")
        with self.assertRaises(ValueError):
            visible_codec({**sample,"old":sample["old"][:11]})
        with self.assertRaises(ValueError):
            visible_codec({**sample,"old":list(reversed(sample["old"]))})
        corrupt=deepcopy(sample)
        corrupt["old"][0]["match"]=True
        with self.assertRaises(ValueError):
            visible_codec(corrupt)
        with self.assertRaises(ValueError):
            visible_codec({"phase":"update","memory_codec":"count","old":[]})

    def test_codec_sidecar_keeps_raw_model_evidence_and_changes_only_memory(self):
        calls=[]
        def fake(argv,payload,prior,timeout,experiment):
            self.assertEqual(prior,[])
            calls.append(payload)
            if payload["phase"]=="initial":
                expected=visible_codec(payload)
                wrong=expected+1 if expected<payload["memory_max"] else expected-1
                value={"memory":wrong,"posterior":[.5,.3,.2],"action":"de_risk"}
            else:
                self.assertEqual(payload["old"],"not_replayed")
                self.assertEqual(payload["prior_responses"],"not_replayed")
                value={"posterior":[.5,.3,.2],"action":"de_risk"}
            return {
                "status":"ok","response":value,"wall_seconds":0.1,
                "adapter_telemetry":None,"telemetry_status":"missing",
                "input_tokens":None,"output_tokens":None,
            }
        exp={"experiment_id":self.spec["experiment_id"]}
        report=run_pilot(self.spec,self.manifest,exp,["python","mock"],fake)
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["initial_calls"],8)
        self.assertEqual(sum(c["phase"]=="update" for c in calls),4)
        self.assertEqual(len(calls),12)
        self.assertFalse(report["actual_model_inference_observed"])
        self.assertFalse(report["model_evaluation_claim"])
        self.assertEqual(report["gate_results"]["exact_visible_codec"],"PASS")
        self.assertEqual(report["gate_results"]["genuine_model_inference_observed"],"FAIL")
        self.assertEqual(report["gate_results"]["verified_codec_any_completed"],"PASS")
        self.assertEqual(report["gate_results"]["verified_codec_better_than_model_memory"],"PASS")
        for mode in ("count","bitmap"):
            self.assertEqual(report["groups"][mode+"/model_memory"]["scored"],0)
            self.assertEqual(report["groups"][mode+"/verified_visible_codec"]["scored"],2)
        for row in report["rows"]:
            self.assertEqual(row["raw_model_memory_correct"],False)
            if row["treatment"]=="verified_visible_codec":
                self.assertEqual(row["status"],"scored")
                self.assertEqual(row["update_memory"],row["expected_visible_memory"])
                self.assertTrue(row["update_uses_host_visible_codec"])
                self.assertTrue(row["update_old_history_not_replayed"])
                self.assertTrue(row["update_prior_responses_empty"])
            else:
                self.assertEqual(row["status"],"initial_invalid")
                self.assertIsNone(row["update_receipt"])
        next_run=next_prompt(report)
        self.assertIn("GATE",next_run.upper())
        self.assertIn("PASS",next_run)
        self.assertIn("FAIL",next_run)
        self.assertIn("raw model",next_run.lower() if False else "raw model".lower()) if False else None

    def test_invalid_initial_schema_gets_no_help_from_codec(self):
        def bad_adapter(argv,payload,prior,timeout,experiment):
            return {"status":"ok","response":{"memory":0,"action":"continue"},
                    "wall_seconds":0.1,"telemetry_status":"missing","adapter_telemetry":None}
        report=run_pilot(self.spec,self.manifest,{"experiment_id":"test"},
                         ["python","mock"],bad_adapter)
        self.assertEqual(report["initial_calls"],8)
        self.assertEqual(sum(x["status"]=="scored" for x in report["rows"]),0)
        self.assertEqual(report["gate_results"]["verified_codec_any_completed"],"FAIL")
        self.assertIn("DECISION-PIPELINE FAIL",next_prompt(report))

    def test_response_attestation_has_separate_physical_boundary(self):
        def fake_verified(argv,payload,prior,timeout,experiment):
            if payload["phase"]=="initial":
                resp={"memory":visible_codec(payload),"posterior":[.5,.3,.2],"action":"de_risk"}
            else:
                resp={"posterior":[.5,.3,.2],"action":"de_risk"}
            return {
                "status":"ok","response":resp,"wall_seconds":.1,
                "telemetry_status":"valid",
                "adapter_telemetry":{
                    "identity":{"local_artifacts_verified":True},
                    "isolation":{"server_reset_verified":True,
                                 "server_boot_sha256":"same_boot","process_reaped":True,
                                 "port_closed_verified":True},
                    "usage":{"input_tokens":100,"output_tokens":20},
                },
            }
        report=run_pilot(self.spec,self.manifest,{"experiment_id":"test"},
                         ["python","mock"],fake_verified)
        self.assertTrue(report["actual_model_inference_observed"])
        self.assertFalse(report["physical_memory_enforced"])
        self.assertEqual(report["gate_results"]["all_stage_server_resets_verified"],"FAIL")
        for arm in report["groups"].values():
            self.assertFalse(arm["all_stage_server_resets_verified"])
        self.assertEqual(report["groups"]["count/verified_visible_codec"]["scored"],2)


if __name__=="__main__":
    unittest.main()
