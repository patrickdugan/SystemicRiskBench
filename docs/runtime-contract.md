# Runtime and audit contract

`run --adapter-argv` accepts a JSON string containing an executable argv array.
It uses `shell=False`; the operator owns this executable. The adapter reads one
UTF-8 JSON object from stdin and emits exactly one JSON object on stdout.
Duplicate keys, nonfinite numbers and non-object responses are rejected. The
request contains `protocol`, `packet`, `prior_responses`, `experiment` and
`instruction`. `prior_responses` resets between cases and accumulates within a
case, including failed-call status. The wrapper must implement the declared
memory/reset policy itself; external state is not reset by the harness.

Numerical responses supply `estimates` with the exact names in each task's
`answer_fields`. All six tasks and 13 fields stay in the scoring denominator;
unknown tasks/fields are contract failures. Per-task fractions are averaged
within each family, then across families for the macro result. Field-level
micro accuracy and coverage remain visible. Tolerance is absolute `1e-8` or
relative `1e-6`. Quantity conventions are fixed by the public question.

Historical responses should include `policy`, `rationale` linked to evidence
IDs, `risk_estimates`, `forecasts`, `self_critique`, `architecture_critique`,
`population_analysis`, `revision` and `limitations`. The current runner accepts
an object and queues these for audit; it does not enforce the richer proposed
schema or claim that a well-formed response is semantically correct.

`contracts/response.schema.json` documents current object/estimate shape.
`proposed-rich-response.schema.json` and `proposed-run-manifest.schema.json`
are study-design targets and are **not** the runner's current validation schema.
The rich proposal needs adaptation for masked cutoffs before enforcement.

Run outputs use `srb.run.v0.1`; configuration needs an `experiment_id`. Resource
metadata is passed through to the wrapper. Only per-call wall timeout is host
enforced. The host does not trust self-reported token/energy measurements as
independent meters. Nonzero exit, timeout and malformed response are recorded;
adapter error diagnostics are preserved as a bounded stderr tail. Do not print
credentials on stderr or include them in experiment configs.

## Human audit file

The audit command requires a historical run and its canonical JSON digest:
SHA-256 over UTF-8 `json.dumps(run, sort_keys=True, separators=(',', ':'),
allow_nan=False)`. `compare` includes this `run_sha256` for each run. Supply
exactly two distinct reviewers for every case in the selected run:

```json
{
  "run_sha256": "COPY_DIGEST_FROM_COMPARISON",
  "reviews": [
    {
      "case_id": "tf_1982_latam",
      "reviewer_id": "reviewer-A",
      "ratings": {
        "causal_risk_model": 2,
        "strategy_revision": 2,
        "self_critique": 1,
        "population_externalities": 2,
        "architecture_critique": 1
      },
      "evidence_refs": ["stage0:rationale[0]", "s0.e0", "stage1:revision"],
      "rationale": "Illustrative format only; replace with evidence-specific assessment."
    }
  ]
}
```

This example is incomplete until reviewer B is supplied. Scores weight each
0..3 rating by the component's allotted points/3, preserve both reviewers,
average per case and macro-average over families. All disagreement components
remain flagged pending adjudication. The operator verifies reviewer independence
and evidence references; the arithmetic helper cannot establish either itself.
No scoring field is filled from a model's own claimed reasoning quality.

The `calibration` command accepts `{"forecasts":[{"id":"event-1",
"probability":0.2,"outcome":0}]}`. It computes raw mean binary Brier score.
Only the study operator can establish that the probabilities were frozen
before predeclared target outcomes. Absent that evidence, treat the output as
a mathematical diagnostic rather than validated forecasting performance.
