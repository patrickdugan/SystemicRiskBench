"""Reference-only agent adapter for SRB-REV-01; this is NOT an AI model.

Runs as a fresh process per stage and reads strictly the allowed packet.
"""
from __future__ import annotations

import json
import sys

from systemic_risk_bench.agent_revision import (
    bitmap_posterior, count_posterior, initial_posterior
)


def reply(packet: dict) -> dict:
    mode=packet["memory_codec"]
    if mode not in ("bitmap","count"):
        raise ValueError("unsupported declared codec")
    if packet["phase"] == "initial":
        old=packet["old"]
        if len(old)!=12:
            raise ValueError("expected twelve named observations")
        if [x["slot"] for x in old] != list(range(12)):
            raise ValueError("expected canonical slot order")
        count=sum(int(x["match"]) for x in old)
        memory=count if mode=="count" else sum(int(x["match"])<<i for i,x in enumerate(old))
        return {"memory":memory,"posterior":[float(x) for x in initial_posterior(count)]}
    if packet["phase"]=="update":
        memory=packet["memory"]
        changes=packet["corrections"]
        if len(changes)!=6:
            raise ValueError("expected six host-verified corrections")
        if mode=="count":
            posterior=count_posterior(memory,sum(x["new_match"] for x in changes))
        else:
            posterior=bitmap_posterior(
                memory,tuple((x["slot"],x["new_match"]) for x in changes))
        return {"posterior":[float(x) for x in posterior]}
    raise ValueError("unrecognized evaluation phase")


def main() -> int:
    incoming=json.load(sys.stdin)
    packet=incoming["packet"]
    if incoming.get("prior_responses")!=[]:
        raise ValueError("prior responses would leak additional memory")
    json.dump(reply(packet),sys.stdout,allow_nan=False)
    print()
    return 0


if __name__=="__main__":
    raise SystemExit(main())
