# SRB-REV-05 continuation prompt, grounded in CI PASS/FAIL

**Task:** Repair and advance the registered BitAgent financial-revision
experiment in `patrickdugan/SystemicRiskBench`, using the existing
source-frozen benchmark and Lean-compatible regression suite.

## Evidence to preserve

Actual real-model pilot:
[GitHub Actions #44490225970](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44490225970),
[results report](REPORT.md), with complete original unedited
`observations.json` and generated prompt stored in
[artifact #14513409340](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44490225970/artifacts/14513409340).

- **PASS:** 139 repository Python tests; frozen panel digest; correct
  deterministic 4-bit and 12-bit host-visible memory encodings; SHA/size
  verification for official llama.cpp b12248 CPU distribution, Bonsai Q1
  base, and BitAgent LoRA. There were **two actual model-completed
  initial count-stage inference receipts** with measured token counts.
- **FAIL:** all four arm-level decision-coverage gates,
  `0/2` completed cases in every arm. The coverage-lift gate also
  recorded zero assisted gains. Across ten stage attempts, eight hit the
  **150-second CPU timeout**.
- **FAIL:** complete server-reset attestation. Two completed initial calls
  documented clean independent boots; timed-out descendants lacked
  valid teardown receipts, and the CI runner identified surviving
  `llama-server` processes during cleanup.
- **Observed partial model result:** root 0's count-stage integer was
  correctly **6** with and without the codec sidecar. Root 5 count and
  both bitmap roots had no valid initial response within the budget.
  All update calls attempted after valid initial count completions timed
  out. Reported input/output tokens were `918/81` for each of the two
  valid initial completions. Other token costs are unobserved.
- **Interpretation:** missing-penalized regret `20.0` in every arm
  represents the **missing-response penalty**, not evaluated decision
  regret. The experiment cannot identify an effect of host-provided
  memory on risk reasoning until updated actions can be scored.

## Carry out next

**Priority A: timeout-safe cleanup and inference budget.** Find why
`runner.execute` terminating a timed-out Python adapter can leave
its independent `llama-server` process alive. Add a tested
CPU-runner-specific process-group supervisor or descendant cleanup,
without altering source-locked `agent_revision.py`,
`finance_revision.py`, or `finance_revision_panels.py`.
Verify a deliberately hung server is killed, its listening port
closes, and a failure receipt reports the wall timeout without
claiming unmeasured token usage. Promote this only after CI
failure-injection tests pass.

**Priority B: resource-feasible real inference.** First register a
single-root `count` CPU smoke with a bounded stage limit sized
from the observed 141-145-second initial inference and a sufficiently
long update budget. Preserve the 1-bit base and LoRA SHA-256s and
the exact public packet/source hash. Record an explicit fail if
the revised budget still exhausts; do not count initial-only
responses as completed revisions. Use `workflow_dispatch` for
additional real-model runs so ordinary PR and documentation changes
run source-only tests without repeating costly model downloads.

**Priority C: isolate reasoning after update-stage reachability.**
Repeat the two-root, two-codec verified-visible-state ablation after
both direct and assisted packets reach scored update decisions.
Retain the model's raw memory integer, its own initial posterior and
action, and its unmodified updated posterior/action. The sidecar
may replace only the integer derived from the twelve initially
visible old bits. Evaluate policy regret and posterior/decision
coherence with missing cases in the denominator, and compare total
input/output tokens, server startup, failure costs, and wall time.

**Priority D: scientifically meaningful comparison.** Include an
equal-compute model-only arm, a deterministic visible-codec sidecar,
and a local RTX 5080 Q1 run if the hosted CPU proves unsuitable.
Only after those pilots should a separately hashed higher-precision
checkpoint or independent issuer-root panel be introduced.

## Completion gates

The engineering gate requires pinned binary/LoRA verification, a
complete initial/update OS process lifecycle, and accurate failure
receipts. The scientific gate requires at least one updated risk action
and valid posterior per arm before assessing codec lift. Publish
`PASS`, `FAIL`, or `INCONCLUSIVE` for each named gate, with
actual denominators and source-hash links. Report any timeout or
missing response explicitly.

Keep the old source-law panel intact and retain this CI result as
an immutable comparator. All financial decisions remain synthetic,
read-only, and unsuitable for claims of real market performance or
physical memory isolation.
