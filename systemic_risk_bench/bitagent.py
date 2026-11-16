"""Read-only projection of actual BitAgent strategy covenant v1 fields."""

from .risk import number


def covenant_packet(covenant):
    if not isinstance(covenant, dict) or covenant.get("schema") != "bitagent_strategy_covenant_v1":
        raise ValueError("expected BitAgent StrategyCovenant v1")
    risk = covenant["risk"]
    maximum_leverage = number(risk["maxGrossLeverageBps"], "maxGrossLeverageBps", 0)/10000
    cap = covenant["capital"]
    if cap["asset"] != "tlUSD" or not isinstance(cap["capAtoms"], str) or not cap["capAtoms"].isdigit():
        raise ValueError("capital must be tlUSD with integer-string capAtoms")
    execution = covenant["execution"]
    return {
        "schema_version": "srb.bitagent_projection.v0.1",
        "source_schema": covenant["schema"], "source_covenant_hash": covenant["covenantHash"],
        "authority": "benchmark_read_only", "max_gross_leverage": maximum_leverage,
        "capital": {"asset": cap["asset"], "capAtoms": cap["capAtoms"],
                    "currency_conversion": "not_assumed"},
        "strategies": [{key: s[key] for key in
                        ("strategyId", "strategyVersion", "weightBps", "adapterHash")}
                       for s in covenant["strategies"]],
        "risk_limits": dict(risk),
        "execution": {key: execution[key] for key in
                      ("instruments", "permittedActions", "orderTtlMs", "maxMarketAgeMs",
                       "oraclePolicy", "counterpartyPolicy")},
        "runtime_hashes": dict(covenant["runtime"]),
        "missing_for_cva": ["exposure term structures", "netting enforceability",
                            "collateral and close-out terms", "pricing PD term structure",
                            "recovery and discount curves", "exposure/default dependence"],
        "missing_for_settlement": ["pay-away and final receipt timing", "PvP/DvP applicability",
                                   "settlement rail/finality assumptions", "failure-window probability"],
        "questions": ["Would this covenant remain individually and systemically resilient "
                      "if one million agents used the same strategies and verifier?",
                      "Which risk cannot be computed from these fields, and what new input is needed?",
                      "What objective or shared oracle assumptions need an independent test?"],
        "caveat": "Projection only. Original host validates hashes and authorizes candidates; "
                  "this benchmark neither verifies nor approves the covenant.",
    }
