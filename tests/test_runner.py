import json
from pathlib import Path
import sys
import tempfile
import unittest

from systemic_risk_bench.runner import execute, run
from systemic_risk_bench.scoring import read_json


class RunnerTests(unittest.TestCase):
    def test_adapter_gets_only_supplied_packet_and_prior(self):
        code = "import json,sys;r=json.load(sys.stdin);print(json.dumps({'received':r}))"
        receipt = execute([sys.executable, "-c", code], {"visible": "yes"}, [{"previous": 1}], 10)
        self.assertEqual(receipt["status"], "ok")
        received = receipt["response"]["received"]
        self.assertEqual(received["packet"], {"visible": "yes"})
        self.assertEqual(received["prior_responses"], [{"previous": 1}])
        self.assertNotIn("outcome", received)
        self.assertIsNone(receipt["input_tokens"])

    def test_non_json_non_object_error_and_timeout(self):
        for code in ("print('oops')", "print('[]')", "print('NaN')",
                     "print('{\"a\":1,\"a\":2}')", "print('{\"a\":1e999}')"):
            result = execute([sys.executable, "-c", code], {}, [], 10)
            self.assertEqual(result["status"], "invalid_json")
        result = execute([sys.executable, "-c", "raise SystemExit(3)"], {}, [], 10)
        self.assertEqual(result["status"], "adapter_error")
        result = execute([sys.executable, "-c", "import time;time.sleep(2)"], {}, [], .1)
        self.assertEqual(result["status"], "timeout")

    def test_empty_estimates_baseline_has_zero_score(self):
        result = run([sys.executable, "-c", "print('{}')"], {"experiment_id": "fixture"})
        self.assertEqual(len(result["receipts"]), 6)
        self.assertEqual(result["numeric_report"]["numeric_micro_accuracy"], 0)
        self.assertIsNone(result["reasoning_score"])

    def test_strict_json_duplicate_and_nonfinite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            target = Path(directory)/"input.json"
            for value in ('{"a":1,"a":2}', '{"a":NaN}'):
                target.write_text(value, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_json(target)


if __name__ == "__main__":
    unittest.main()
