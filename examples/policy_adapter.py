"""Hand-written interface fixture, with zero model calls.

The shock threshold is illustrative. It was not fitted on a protected holdout.
"""
from fractions import Fraction
import json
import sys


request = json.load(sys.stdin)
if request.get("protocol") != "srb.policy.adapter.v1":
    raise ValueError("expected the policy adapter protocol")
packet = request["packet"]
actions = packet["available_actions"]
action = min(actions, key=lambda a: Fraction(a["cost"]))
if Fraction(packet["observation"]["shock"]) >= Fraction(3, 10):
    action = max(actions, key=lambda a: a["depth_multiplier"])
print(json.dumps({"action": action["name"], "rationale": "Hand-written shock-threshold fixture."}))
