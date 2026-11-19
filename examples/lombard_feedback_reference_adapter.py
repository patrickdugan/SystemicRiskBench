"""SRB-LOMBARD-02 deterministic exact-math fixture; zero AI model calls."""
import json
import sys

from systemic_risk_bench.lombard_feedback import (
    OUTPUTS, best_choice, validate_config,
)


def reply(packet):
    if packet.get("schema") != "srb.lombard_feedback.v1":
        raise ValueError("unsupported packet")
    config = dict(packet["parameters"], experiment_id=packet["experiment_id"])
    validate_config(config)
    winner = best_choice(config, packet["guarantee"])
    return {name: winner[name] for name in OUTPUTS}


def main():
    incoming = json.load(sys.stdin)
    if incoming.get("prior_responses") != []:
        raise ValueError("old transcript leak")
    json.dump(reply(incoming["packet"]), sys.stdout, allow_nan=False)
    print()


if __name__ == "__main__":
    main()
