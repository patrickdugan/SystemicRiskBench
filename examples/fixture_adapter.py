"""Empty-answer transport fixture. Never label this as a model evaluation."""
import json
import sys

request = json.load(sys.stdin)
print(json.dumps({"estimates": {}, "policy": "defer", "fixture_only": True,
                  "rationale": "Transport fixture; no inference or risk reasoning performed.",
                  "prior_response_count": len(request["prior_responses"])}))
