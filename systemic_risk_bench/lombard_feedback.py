"""SRB-LOMBARD-02: source-free synthetic credit-pricing comparative statics.

The experiment assumes a bank-creditor rescue guarantee and explicitly passes
some change in bank funding costs to merchants. It does not infer bailout
probabilities from Bagehot (1873), nor treat a central-bank emergency loan as
an equity transfer. All values are registered illustrative parameters.
"""
from __future__ import annotations

import math
from typing import Any

from .runner import execute, sha as canonical_sha

SCHEMA = "srb.lombard_feedback.v1"
PROJECTS = ("prudent", "aggressive")
REQUIRED_CONFIG = {
    "experiment_id", "merchant_equity", "max_merchant_debt", "debt_step",
    "risk_free_rate", "bank_default_probability", "bank_recovery",
    "bank_default_feedback", "bank_equity_fraction", "pass_through",
    "merchant_recovery", "origination_margin", "guarantee_grid",
    "projects",
}
P_FIELDS = {"name", "success_return_on_assets", "curvature", "base_failure_probability",
            "failure_slope_per_debt_to_equity"}
OUTPUTS = (
    "project", "borrowed", "bank_default_probability", "merchant_failure_probability",
    "unbacked_bank_funding_rate", "backed_bank_funding_rate",
    "merchant_loan_rate", "merchant_expected_equity_profit",
    "expected_treasury_bank_debt_guarantee",
)
MAX_CASES = 128


def _num(value, label: str, lo: float | None = None, hi: float | None = None) -> float:
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite real number")
    value = float(value)
    if lo is not None and value < lo or hi is not None and value > hi:
        raise ValueError(f"{label} outside registered bounds")
    return value


def validate_config(config: dict[str, Any]) -> dict:
    if type(config) is not dict or set(config) != REQUIRED_CONFIG:
        raise ValueError("feedback config requires exact registered fields")
    if not isinstance(config["experiment_id"], str) or not config["experiment_id"]:
        raise ValueError("experiment_id required")
    for field in ("max_merchant_debt", "debt_step"):
        if type(config[field]) is not int or config[field] <= 0:
            raise ValueError(f"{field} must be a positive integer")
    if config["max_merchant_debt"] % config["debt_step"] != 0:
        raise ValueError("the debt ladder must exactly cover the maximum")
    if config["max_merchant_debt"] // config["debt_step"] > 50:
        raise ValueError("too many candidate debt states")
    e = _num(config["merchant_equity"], "merchant_equity", 1)
    limits = {
        "risk_free_rate": (0, 0.5),
        "bank_default_probability": (0, 0.8),
        "bank_recovery": (0, 1),
        "bank_default_feedback": (0, 1),
        "bank_equity_fraction": (0, 1),
        "pass_through": (0, 1),
        "merchant_recovery": (0, 1),
        "origination_margin": (0, 0.5),
    }
    for field, (lo, hi) in limits.items():
        _num(config[field], field, lo, hi)
    if type(config["guarantee_grid"]) is not list or not config["guarantee_grid"]:
        raise ValueError("nonempty registered guarantee grid required")
    if len(config["guarantee_grid"]) > MAX_CASES:
        raise ValueError("grid too long")
    values = [_num(g, "guarantee", 0, 1) for g in config["guarantee_grid"]]
    if len(set(values)) != len(values) or values != sorted(values):
        raise ValueError("coverage grid must be unique and increasing")
    projects = config["projects"]
    if type(projects) is not list or len(projects) != 2:
        raise ValueError("exactly two project classes required")
    if {p.get("name") for p in projects if type(p) is dict} != set(PROJECTS):
        raise ValueError("projects must be prudent and aggressive")
    for project in projects:
        if type(project) is not dict or set(project) != P_FIELDS:
            raise ValueError("project fields malformed")
        _num(project["success_return_on_assets"], "success_return_on_assets", 0, 1)
        _num(project["curvature"], "curvature", 0, 0.1)
        _num(project["base_failure_probability"], "base_failure_probability", 0, 0.9)
        _num(project["failure_slope_per_debt_to_equity"], "failure_slope", 0, 0.2)
        top_failure = (project["base_failure_probability"] +
                       project["failure_slope_per_debt_to_equity"] *
                       config["max_merchant_debt"] / e)
        if top_failure >= 1:
            raise ValueError("merchant failure probability reaches one")
        top_bank_failure = config["bank_default_probability"] + (
            config["bank_default_feedback"] * top_failure *
            config["max_merchant_debt"] / e)
        if top_bank_failure >= 1:
            raise ValueError("bank failure probability reaches one")
    return config


def exact_funding_rate(*, risk_free: float, default_probability: float,
                       recovery: float, guarantee: float) -> float:
    """Risk-neutral gross promised bank-debt rate with loss-cover guarantee.

    (1+r) [1 - PD*(1-recovery)*(1-guarantee)] = 1+risk_free.
    The government pays only the promised debt shortfall at bank default.
    """
    rf = _num(risk_free, "risk_free", 0, 0.5)
    pd = _num(default_probability, "PD", 0, 0.99)
    rec = _num(recovery, "recovery", 0, 1)
    g = _num(guarantee, "guarantee", 0, 1)
    denominator = 1.0 - pd * (1 - rec) * (1 - g)
    if denominator <= 0:
        raise ValueError("invalid bank funding denominator")
    return (1 + rf) / denominator - 1


def quote(config: dict, project: dict, debt: int, guarantee: float,
          *, pass_through: float | None = None,
          feedback: float | None = None) -> dict:
    e = float(config["merchant_equity"])
    if type(debt) is not int or not 0 <= debt <= config["max_merchant_debt"] or (
        debt % config["debt_step"]):
        raise ValueError("debt must be on registered ladder")
    if project not in config["projects"]:
        raise ValueError("unregistered merchant project")
    g = _num(guarantee, "guarantee", 0, 1)
    alpha = float(config["pass_through"]) if pass_through is None else _num(
        pass_through, "pass_through", 0, 1)
    sensitivity = float(config["bank_default_feedback"]) if feedback is None else _num(
        feedback, "bank_default_feedback", 0, 1)
    debt_equity = debt / e
    p_merch = (project["base_failure_probability"] +
               project["failure_slope_per_debt_to_equity"] * debt_equity)
    p_bank = config["bank_default_probability"] + sensitivity * p_merch * debt_equity
    if not 0 <= p_merch < 1 or not 0 <= p_bank < 1:
        raise ValueError("invalid project/portfolio failure probability")
    params = dict(risk_free=config["risk_free_rate"], default_probability=p_bank,
                  recovery=config["bank_recovery"])
    unbacked = exact_funding_rate(**params, guarantee=0.0)
    backed = exact_funding_rate(**params, guarantee=g)
    passed = unbacked - alpha * (unbacked - backed)
    merchant_den = 1 - p_merch * (1 - config["merchant_recovery"])
    if merchant_den <= 0:
        raise ValueError("merchant creditor promised-repayment denominator zero")
    loan_rate = (1 + passed + config["origination_margin"]) / merchant_den - 1
    promised = debt * (1 + loan_rate)
    gross_success = ((e + debt) * (1 + project["success_return_on_assets"]) -
                     project["curvature"] * debt * debt / e)
    # This exact credit underwriting model presumes good-state full repayment.
    if gross_success < promised:
        raise ValueError("loan cannot be fully repaid in stipulated success state")
    success_equity = gross_success - promised
    expected_terminal_equity = (1 - p_merch) * success_equity
    expected_equity_profit = expected_terminal_equity - e
    bank_debt_principal = debt * (1 - config["bank_equity_fraction"])
    public_exposure = p_bank * g * (1 - config["bank_recovery"]) * (
        1 + backed) * bank_debt_principal
    realized_bad_state_bank_debt_shortfall = (
        1 - config["bank_recovery"]) * (1 + backed) * bank_debt_principal
    return {
        "project": project["name"], "borrowed": debt,
        "merchant_assets": e + debt,
        "merchant_failure_probability": p_merch,
        "bank_default_probability": p_bank,
        "unbacked_bank_funding_rate": unbacked,
        "backed_bank_funding_rate": backed,
        "merchant_loan_rate": loan_rate,
        "merchant_loan_face": promised,
        "merchant_success_equity": success_equity,
        "merchant_expected_equity_profit": expected_equity_profit,
        "merchant_expected_roe": expected_equity_profit / e,
        "bank_debt_principal": bank_debt_principal,
        "bad_state_unpaid_bank_debt": realized_bad_state_bank_debt_shortfall,
        "expected_treasury_bank_debt_guarantee": public_exposure,
        "bank_funding_saving_on_debt": (unbacked - backed) * bank_debt_principal,
        "passed_bank_funding_saving_on_merchant_debt": (
            alpha * (unbacked - backed) * debt),
        "merchant_credit_expected_loss_face": (
            p_merch * (1 - config["merchant_recovery"]) * promised),
    }


def best_choice(config: dict, guarantee: float, *, pass_through=None, feedback=None) -> dict:
    """Enumerate an informed representative merchant's finite feasible ladder.

    Each proposed portfolio is quoted for its own PD. This is a finite
    comparative-static exercise, not a price-taking general equilibrium.
    """
    choices = []
    rejected = 0
    for project in config["projects"]:
        for debt in range(0, config["max_merchant_debt"]+1, config["debt_step"]):
            try:
                choices.append(quote(config, project, debt, guarantee,
                                     pass_through=pass_through, feedback=feedback))
            except ValueError as error:
                if "success state" in str(error):
                    rejected += 1
                else:
                    raise
    if not choices:
        raise ValueError("no viable merchant plans")
    # Tie breaks: smaller debt, then prudent over aggressive.
    winner = min(choices, key=lambda row: (
        -row["merchant_expected_equity_profit"], row["borrowed"],
        PROJECTS.index(row["project"])))
    return {**winner, "candidate_plans_checked": len(choices),
            "candidate_plans_rejected": rejected}


def population_controls(choice: dict, counts=(1, 1000, 1_000_000)) -> list[dict]:
    """Freeze the chosen per-merchant risk quote across aggregation choices.

    Holding TOTAL credit constant must leave total risk-priced guarantee cost
    unchanged. Fixed credit per agent scales aggregate exposure instead.
    Neither rule simulates correlated runs, market depth, or price impact.
    """
    if not isinstance(choice, dict):
        raise ValueError("choice must be an oracle quote")
    unit_debt = choice["borrowed"]
    unit_cost = choice["expected_treasury_bank_debt_guarantee"]
    result = []
    for n in counts:
        if type(n) is not int or n < 1:
            raise ValueError("cohort count must be a positive integer")
        result.append({
            "agents": n,
            "fixed_total_debt": unit_debt,
            "fixed_total_treasury_expected": unit_cost,
            "fixed_per_agent_debt_total": n * unit_debt,
            "fixed_per_agent_treasury_expected": n * unit_cost,
            "bank_pd_held_constant": True,
            "no_market_depth_or_agent_interactions": True,
        })
    return result


def analysis(config: dict) -> dict:
    validate_config(config)
    rows = []
    for g in config["guarantee_grid"]:
        full = best_choice(config, g)
        no_pass = best_choice(config, g, pass_through=0.0)
        no_bank_pd = best_choice(config, g, feedback=0.0)
        fixed_base_pd_zero = {
            **config, "bank_default_probability": 0.0,
            "bank_default_feedback": 0.0,
        }
        no_default = best_choice(fixed_base_pd_zero, g)
        # On-bank-debt fiscal guarantee is distinct from discretionary new
        # bank equity injections and central bank recapitalization.
        rows.append({
            "guarantee": g,
            "baseline": full,
            "population_controls": population_controls(full),
            "no_pass_through": no_pass,
            "no_bank_default_feedback": no_bank_pd,
            "zero_bank_default_probability": no_default,
        })
    return {
        "schema": SCHEMA, "experiment_id": config["experiment_id"],
        "source_class": "synthetic_law_evaluator_fixture",
        "model_evaluation_claim": False, "empirical_identification_claim": False,
        "general_equilibrium_claim": False,
        "policy": "anticipated_Treasury_guarantee_on_bank_funding_debt",
        "no_bank_equity_recap_or_central_bank_credit_in_this_model": True,
        "bank_liability_guarantee_vs_equity_transfer_kept_distinct": True,
        "config_sha256": canonical_sha(config), "n_cases": len(rows),
        "rows": rows,
        "negative_controls": [
            "zero_guarantee", "zero_pass_through",
            "zero_bank_default_probability", "fixed_bank_pd_feedback",
        ],
    }


def public_cases(config: dict) -> list[dict]:
    validate_config(config)
    base = {
        key: value for key, value in config.items() if key != "experiment_id"
    }
    return [
        {"schema": SCHEMA, "id": f"lombard-guarantee-{i:03d}", "index": i,
         "guarantee": guarantee, "source_class": "public_synthetic_problem",
         "experiment_id": config["experiment_id"],
         "config_sha256": canonical_sha(config), "parameters": base,
         "instructions": (
             "Enumerate all eligible debt and project choices. Use exact bank "
             "funding-price parity, assume the configured pass-through, then price "
             "the merchant debt's expected shortfall and maximize expected terminal "
             "equity value. Return only project, borrowed, funding and merchant rates, "
             "failure probabilities, merchant expected profit and expected Treasury "
             "bank-debt guarantee cost. These are invented inputs. No trading or "
             "government action is authorized."),
         "response_fields": list(OUTPUTS)}
        for i, guarantee in enumerate(config["guarantee_grid"])
    ]


def validate_response(value: dict) -> dict:
    if type(value) is not dict or set(value) != set(OUTPUTS):
        raise ValueError("feedback adapter response has missing or extra fields")
    if value["project"] not in PROJECTS or type(value["project"]) is not str:
        raise ValueError("unknown project")
    if type(value["borrowed"]) is not int or value["borrowed"] < 0:
        raise ValueError("borrowed must be a nonnegative integer")
    for key in OUTPUTS:
        if key in ("project", "borrowed"):
            continue
        if key in ("bank_default_probability", "merchant_failure_probability"):
            _num(value[key], key, 0, 1)
        elif key == "expected_treasury_bank_debt_guarantee":
            _num(value[key], key, 0)
        elif key in ("unbacked_bank_funding_rate", "backed_bank_funding_rate",
                     "merchant_loan_rate"):
            _num(value[key], key, -0.999999)
        else:
            _num(value[key], key)
    return value


def score_responses(config: dict, responses: list[dict]) -> dict:
    oracle = analysis(config)
    if type(responses) is not list:
        raise ValueError("responses must be an array")
    indexed = {}
    for row in responses:
        if type(row) is not dict or set(row) != {"id", "response"}:
            raise ValueError("response list entries require id and response")
        key = row["id"]
        if type(key) is not str or key in indexed:
            raise ValueError("duplicate or invalid response id")
        indexed[key] = row["response"]
    public = public_cases(config)
    if set(indexed) - {case["id"] for case in public}:
        raise ValueError("unregistered response id")
    scored = []
    for item, baseline in zip(public, oracle["rows"]):
        key = item["id"]
        reference = baseline["baseline"]
        entry = indexed.get(key)
        try:
            actual = validate_response(entry)
        except (ValueError, TypeError):
            actual = None
        checks = {}
        for field in OUTPUTS:
            truth = reference[field]
            if actual is None:
                passed = False
            elif field in ("project", "borrowed"):
                passed = actual[field] == truth
            else:
                passed = math.isclose(actual[field], truth, rel_tol=1e-7,
                                      abs_tol=1e-7)
            checks[field] = passed
        scored.append({
            "id": key, "status": "scored" if actual is not None else "invalid_or_missing",
            "field_checks": checks, "field_accuracy": sum(checks.values()) / len(OUTPUTS),
            "correct_policy": checks["project"] and checks["borrowed"],
        })
    return {
        "schema": "srb.lombard_feedback.score.v1",
        "experiment_id": config["experiment_id"],
        "config_sha256": oracle["config_sha256"], "model_evaluation_claim": False,
        "n_cases": len(scored),
        "coverage": sum(s["status"] == "scored" for s in scored)/len(scored),
        "field_accuracy_including_missing": sum(sum(s["field_checks"].values())
            for s in scored)/(len(scored)*len(OUTPUTS)),
        "policy_accuracy_including_missing": sum(s["correct_policy"]
            for s in scored)/len(scored),
        "rows": scored,
    }


def run_adapter(config: dict, adapter_argv: list[str], experiment: dict,
                *, timeout: float = 30) -> dict:
    """Real subprocesses, model identity and isolation remain adapter concerns."""
    cases = public_cases(config)
    if type(experiment) is not dict or type(experiment.get("experiment_id")) is not str:
        raise ValueError("experiment registration needs experiment_id")
    responses = []
    receipts = []
    for case in cases:
        receipt = execute(adapter_argv, case, [], timeout, experiment)
        receipts.append({"id": case["id"], "packet_sha256": canonical_sha(case),
                         "receipt": receipt})
        responses.append({"id": case["id"], "response":
                          receipt["response"] if receipt["status"] == "ok" else None})
    return {
        "schema": "srb.lombard_feedback.run.v1",
        "source_class": "public_development_synthetic",
        "model_evaluation_claim": False,
        "physical_memory_enforced": False,
        "adapter_process_sandboxed": False,
        "experiment": experiment,
        "input_sha256": canonical_sha(config),
        "score": score_responses(config, responses),
        "subprocess_calls_attempted": len(cases),
        "all_model_identity_and_resource_telemetry_requires_independent_audit": True,
        "receipts": receipts,
    }
