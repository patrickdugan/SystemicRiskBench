"""Offline commands. Public packet creation never includes answer keys."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from . import __version__
from .scoring import brier, read_json, score_numeric
from .simulation import sweep
from .suite import numerical_answers, quantitative_tasks

ROOT = Path(__file__).resolve().parent


def write(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def historical():
    from .history import load_cases
    return load_cases(sorted((ROOT / "data" / "history").glob("*.json")))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Systemic Risk Bench v" + __version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="validate historical cards and reference checks")
    commands.add_parser("list", help="list historical case ids; evaluator/curator view")
    export = commands.add_parser("packet", help="export one stage without later outcomes")
    export.add_argument("--case", required=True)
    export.add_argument("--stage", required=True, type=int, help="zero-based stage index")
    export.add_argument("--masked", action="store_true")
    export.add_argument("--output", required=True)
    quant = commands.add_parser("quant", help="export public numerical questions")
    quant.add_argument("--output", required=True)
    numeric = commands.add_parser("score", help="score numerical responses")
    numeric.add_argument("--responses", required=True)
    numeric.add_argument("--output", required=True)
    stress = commands.add_parser("stress", help="cohort stress matrix, zero model calls")
    stress.add_argument("--output", required=True)
    em = commands.add_parser("evalmath-export", help="export evaluator-only paired simulator counterfactuals")
    em.add_argument("--config", required=True)
    em.add_argument("--output", required=True)
    demo = commands.add_parser("smoke", help="reference fixtures only; never a model result")
    demo.add_argument("--output-dir", required=True)
    forecast = commands.add_parser("calibration", help="score resolved frozen binary forecasts")
    forecast.add_argument("--input", required=True)
    forecast.add_argument("--output", required=True)
    runner = commands.add_parser("run", help="invoke operator-provided JSON stdin/stdout adapter")
    runner.add_argument("--adapter-argv", required=True, help="JSON array, no shell expansion")
    runner.add_argument("--experiment", required=True)
    runner.add_argument("--track", choices=("quant", "history"), default="quant")
    runner.add_argument("--cases", help="comma-separated historical ids; required for history")
    runner.add_argument("--masked", action="store_true")
    runner.add_argument("--timeout", type=float, default=60)
    runner.add_argument("--output", required=True)
    revise = commands.add_parser("agent-revision", help="bounded-memory delayed-evidence agent eval")
    revise.add_argument("--adapter-argv", required=True, help="JSON array, no shell expansion")
    revise.add_argument("--experiment", required=True, help="experiment JSON with experiment_id")
    revise.add_argument("--mode", choices=("count","bitmap"), required=True)
    revise.add_argument("--cases", type=int, default=16, help="public development issuer roots")
    revise.add_argument("--timeout", type=float, default=30)
    revise.add_argument("--output", required=True)
    bridge = commands.add_parser("bitagent-packet", help="read-only covenant v1 risk projection")
    bridge.add_argument("--input", required=True)
    bridge.add_argument("--output", required=True)
    audit = commands.add_parser("audit", help="score two attributed human reviews per historical case")
    audit.add_argument("--run", required=True)
    audit.add_argument("--reviews", required=True)
    audit.add_argument("--output", required=True)
    compare = commands.add_parser("compare", help="compare matching run receipts; no invented reasoning scores")
    compare.add_argument("--runs", nargs="+", required=True)
    compare.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            from .history import validate_cases
            cases = historical()
            result = validate_cases(cases)
            if result:
                raise ValueError("; ".join(result))
            reference = score_numeric([{"id": key, "estimates": values}
                                       for key, values in numerical_answers().items()])
            print(json.dumps({"case_count": len(cases), "history_errors": result, "reference_numeric_accuracy":
                              reference["numeric_micro_accuracy"]}, indent=2))
        elif args.command == "list":
            print(json.dumps([{k: case[k] for k in ("id", "title", "event_date", "family")}
                              for case in historical()], indent=2))
        elif args.command == "packet":
            from .history import public_packet
            cases = {c["id"]: c for c in historical()}
            if args.case not in cases:
                raise ValueError("unknown case id")
            packet = public_packet(cases[args.case], args.stage, masked=args.masked)
            packet["packet_sha256"] = digest(packet)
            write(args.output, packet)
        elif args.command == "quant":
            write(args.output, {"schema_version": "srb.quant.v0.1", "tasks": quantitative_tasks()})
        elif args.command == "score":
            document = read_json(args.responses)
            write(args.output, score_numeric(document["responses"]))
        elif args.command == "stress":
            write(args.output, {"model_calls": 0, "calibration": "synthetic_illustrative",
                                "results": sweep()})
        elif args.command == "evalmath-export":
            from .evalmath import export_bank
            write(args.output, export_bank(args.config))
        elif args.command == "agent-revision":
            from .agent_revision import run_agent_revision
            write(args.output, run_agent_revision(
                json.loads(args.adapter_argv), read_json(args.experiment),
                mode=args.mode, cases=args.cases, timeout=args.timeout))
        elif args.command == "calibration":
            write(args.output, brier(read_json(args.input)["forecasts"]))
        elif args.command == "bitagent-packet":
            from .bitagent import covenant_packet
            write(args.output, covenant_packet(read_json(args.input)))
        elif args.command == "audit":
            from .audit import score_audit
            recorded = read_json(args.run)
            reviews = read_json(args.reviews)
            if reviews.get("run_sha256") != digest(recorded):
                raise ValueError("reviews do not match run content digest")
            known = {c["id"]: c["family"] for c in historical()}
            ids = {r["case_id"] for r in recorded["receipts"]}
            if recorded.get("track") != "history_reconstruction" or not ids <= set(known):
                raise ValueError("audit requires a recognized historical run")
            write(args.output, score_audit(reviews, {key: known[key] for key in sorted(ids)}))
        elif args.command == "compare":
            rows = []
            packet_sets = []
            for path in args.runs:
                recorded = read_json(path)
                receipts = recorded["receipts"]
                packet_sets.append([(r["case_id"], r["stage_index"], r["packet_sha256"])
                                    for r in receipts])
                numeric = recorded.get("numeric_report") or {}
                rows.append({"experiment": recorded["experiment"]["experiment_id"],
                             "run_sha256": digest(recorded), "track": recorded["track"],
                             "numeric_family_macro_accuracy": numeric.get("numeric_family_macro_accuracy"),
                             "wall_seconds": recorded["host_measured_wall_seconds"],
                             "failed_calls": sum(r["status"] != "ok" for r in receipts),
                             "reasoning_score": None, "reasoning_audit": "separate_audit_artifact"})
            write(args.output, {"rows": rows, "identical_packets": all(
                p == packet_sets[0] for p in packet_sets), "compute_matched_claim": False,
                "note": "Compare only matched packets/budgets; unknown resource measurements "
                        "and unresolved human audits prevent a reasoning leaderboard claim."})
        elif args.command == "run":
            from .runner import run
            selected = None
            if args.track == "history":
                if not args.cases:
                    raise ValueError("history run requires explicit --cases ids")
                ids = args.cases.split(",")
                if len(set(ids)) != len(ids):
                    raise ValueError("duplicate case selection")
                by_id = {c["id"]: c for c in historical()}
                if set(ids) - set(by_id):
                    raise ValueError("unknown historical case id")
                selected = [by_id[key] for key in ids]
            write(args.output, run(json.loads(args.adapter_argv), read_json(args.experiment),
                                   cases=selected, masked=args.masked, timeout=args.timeout))
        elif args.command == "smoke":
            destination = Path(args.output_dir)
            responses = [{"id": key, "estimates": values}
                         for key, values in numerical_answers().items()]
            report = score_numeric(responses)
            report.update({"run_kind": "reference_fixture_smoke", "model_calls": 0,
                           "not_an_experiment_result": True})
            write(destination / "reference-smoke.json", report)
            write(destination / "cohort-stress.json", {
                "model_calls": 0, "calibration": "synthetic_illustrative", "results": sweep()})
            write(destination / "reference-responses.json", {"responses": responses,
                  "fixture_only_do_not_treat_as_model_output": True})
            print(f"Reference smoke written to {destination}; zero model calls.")
    except (ValueError, KeyError, TypeError, IndexError, OSError) as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
