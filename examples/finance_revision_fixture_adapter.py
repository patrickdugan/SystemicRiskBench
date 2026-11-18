"""Deterministic mathematical oracle for SRB-REV-02, never a model result."""
import json
import sys

from systemic_risk_bench.agent_revision import (
    bitmap_posterior, count_posterior, initial_posterior,
)
from systemic_risk_bench.finance_revision import SCHEMA, optimal_action


def reply(packet):
    if packet.get("schema") != SCHEMA:
        raise ValueError("wrong financial revision track")
    mode = packet["memory_codec"]
    if mode not in ("count", "bitmap"):
        raise ValueError("unknown memory codec")
    family = packet["finance_context"]["family"]
    if packet["phase"] == "initial":
        old = packet["old"]
        if len(old) != 12 or [x["slot"] for x in old] != list(range(12)):
            raise ValueError("wrong old-report format")
        count = sum(int(x["match"]) for x in old)
        memory = count if mode == "count" else sum(
            int(x["match"]) << x["slot"] for x in old)
        p = initial_posterior(count)
        return {"memory": memory, "posterior": list(map(float, p)),
                "action": optimal_action(p, family)}
    if packet["phase"] == "update":
        if packet["old"] != "not_replayed" or packet["prior_responses"] != "not_replayed":
            raise ValueError("earlier evidence must be suppressed")
        memory = packet["memory"]
        events = packet["corrections"]
        if len(events) != 6:
            raise ValueError("wrong correction count")
        if mode == "count":
            p = count_posterior(memory, sum(event["new_match"] for event in events))
        else:
            p = bitmap_posterior(
                memory, tuple((event["slot"], event["new_match"]) for event in events))
        return {"posterior": list(map(float, p)),
                "action": optimal_action(p, family)}
    raise ValueError("unknown phase")


def main():
    request = json.load(sys.stdin)
    if request.get("prior_responses") != []:
        raise ValueError("prior response leakage")
    json.dump(reply(request["packet"]), sys.stdout, allow_nan=False)
    print()


if __name__ == "__main__":
    main()
