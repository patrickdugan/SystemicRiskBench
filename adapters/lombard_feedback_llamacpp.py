"""Pinned local llama.cpp transport for SRB-LOMBARD-02 finite merchant choices.

Uses the existing verified model/LoRA preflight; no model inference occurs in
repository CI. The remote model server is operator-owned, not a memory sandbox.
"""
import argparse
import json
import sys
import time

from .llamacpp import LlamaCppAdapter, check_gpu_window
from systemic_risk_bench.lombard_feedback import (
    OUTPUTS, SCHEMA, validate_response,
)
from systemic_risk_bench.scoring import loads_json, read_json

SYSTEM = (
    "Solve the supplied public synthetic merchant and bank funding problem. "
    "Use the declared risk-neutral bank financing identity, bank-cost pass-through, "
    "exact merchant default underwriting equation, and enumerate the finite "
    "debt ladder and both projects before choosing the maximum expected terminal "
    "shareholder payoff. All probabilities, guarantees and operating yields are "
    "assumptions. Answer with only one strictly matching JSON object. Do not "
    "access tools, external accounts, files or previous model responses."
)


def schema():
    fields = {
        "project": {"type": "string", "enum": ["prudent", "aggressive"]},
        "borrowed": {"type": "integer", "minimum": 0},
    }
    for field in OUTPUTS:
        if field not in fields:
            fields[field] = {"type": "number"}
    return {"type": "object", "properties": fields,
            "required": list(fields), "additionalProperties": False}


class LombardFeedbackLlamaCppAdapter(LlamaCppAdapter):
    def infer_feedback(self, packet, prior):
        if prior != []:
            raise ValueError("previous model responses must be absent")
        if type(packet) is not dict or packet.get("schema") != SCHEMA:
            raise ValueError("wrong Lombard feedback schema")
        if packet.get("source_class") != "public_synthetic_problem":
            raise ValueError("unexpected source class")
        check_gpu_window(self.config, self.clock() if self.clock else None)
        if self.runtime_identity is None:
            self.preflight()
        request = {
            "model": self.config["model_alias"],
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": json.dumps({"packet": packet},
                                                       sort_keys=True, allow_nan=False)},
            ],
            "response_format": {"type": "json_schema", "schema": schema()},
            "stream": False,
            "temperature": self.config.get("temperature", 0),
            "top_p": 1,
            "seed": self.config.get("seed", 0),
            "max_tokens": self.config.get("max_tokens", 1536),
            "cache_prompt": False,
            "lora": [{"id": self.config["adapter"]["id"],
                      "scale": self.config["adapter"]["scale"]}],
        }
        start = time.perf_counter()
        response = self.request("/v1/chat/completions", request)
        elapsed = time.perf_counter() - start
        choices = response.get("choices", [])
        if type(choices) is not list or len(choices) != 1:
            raise ValueError("expected one completion")
        result = choices[0]
        if result.get("finish_reason") != "stop":
            raise ValueError("interrupted/truncated completion")
        message = result.get("message")
        if type(message) is not dict or message.get("tool_calls"):
            raise ValueError("invalid completion or unexpected tool calls")
        parsed = validate_response(loads_json(message.get("content", "")))
        print(json.dumps({
            "wall_seconds": elapsed,
            "model_alias": self.config["model_alias"],
            "runtime_identity": self.runtime_identity,
            "token_usage": response.get("usage"),
        }), file=sys.stderr)
        return parsed


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local pinned BitAgent credit-feedback adapter")
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    request = loads_json(sys.stdin.read())
    if request.get("protocol") != "srb.adapter.v0.1":
        raise ValueError("unsupported JSON adapter protocol")
    if request.get("prior_responses") != []:
        raise ValueError("previous model responses must be empty")
    response = LombardFeedbackLlamaCppAdapter(
        read_json(args.config)).infer_feedback(
            request["packet"], request["prior_responses"])
    print(json.dumps(response, allow_nan=False))


if __name__ == "__main__":
    main()
