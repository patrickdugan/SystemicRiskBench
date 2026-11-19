# SRB-REV-05 CI execution record

Public development experiment. Registered roots `[0, 5]`, with 4-bit count and
12-bit bitmap, each run in direct model-memory and verified-visible-codec arms.
Pinned source panel SHA-256:
`81232c2f28c1e57b0fd8c1d8cc478ec3983c73f08be2e51076acb8e5995a0f0a`.

## Verified engineering PASS / FAIL events

| Check | Observed result | Evidence |
| --- | --- | --- |
| Initial focused source tests | **FAIL**, two mistaken test assertions; fixed before real inference | [run 44489891465](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44489891465) |
| CPU server archive downloaded and SHA verified | **PASS** | [run 44489997337](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44489997337) |
| Bonsai Q1 base SHA/size and BitAgent LoRA SHA/size | **PASS** | [run 44489997337](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44489997337) |
| First model registration import | **FAIL**, standalone script lacked repository import path; fixed with `PYTHONPATH=.` | [run 44489997337](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44489997337) |
| Frozen financial panel and deterministic codec | **PASS**, 5 focused tests | [run 44490225970](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44490225970) |
| Full Python repository regression | **PASS**, 139 tests | [run 44490225970](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44490225970) |

At the time of this execution note, the actual BitAgent CPU job in
[run 44490225970](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44490225970)
has reached its staged inference step. Model pass/fail and individual response
receipts are pending completion of that job.

## Promotion rule for observed model outcome

The CI job writes `artifacts/rev05-ci/observations.json` and
`artifacts/rev05-ci/NEXT_PROMPT.md`, and uploads both as
`srb-rev05-real-bitagent-cpu-pilot`. Preserve exact observed status, model
output, token usage and missing-response penalties when promoting them into
a versioned result. An infrastructure error is explicitly classified and
must not be turned into a scientific model-competence failure.

The generated prompt must state each actual gate's **PASS** or **FAIL**
without carrying input answers, hidden regimes, or unobserved performance
claims. The source-law panel is public development material and model memory
is only bounded by the protocol, with `physical_memory_enforced=false`.

## Scientific questions still awaiting model receipts

- Initial bounded integer encoding correctness, separated from JSON schema
  and normalized-posterior validity.
- Whether host verification of the original **visible** old bits permits
  more complete update-stage reasoning under otherwise identical packet
  construction.
- Update action agreement with the model's own forecast and the correct
  source-law Bayes decision, with exact missing-case denominator.
- CPU-stage startup, inference, termination and token cost, including failed
  calls and any timeout.

The next-run prompt is a generated outcome artifact, rather than a
researcher-supplied claim of a successful model run.
