# SRB-REV-05: Hosted CPU BitAgent pilot, observed run

**Run:** [GitHub Actions #44490225970](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44490225970)
**Actual model artifact:** [raw CI observations and generated prompt (artifact #14513409340)](https://github.com/patrickdugan/SystemicRiskBench/actions/runs/44490225970/artifacts/14513409340)
**Date:** 19 November 2026. **Status:** engineering workflow success, scientific test **FAIL / timeout-censored**.

The experiment was preregistered in `configs/rev05-cpu-ci-pilot.json`
with public source roots `[0,5]`, memory modes `count` (4 logical bits)
and `bitmap` (12 logical bits), and treatment arms
`model_memory` and `verified_visible_codec`.
The original source panel manifest SHA-256 was
`81232c2f28c1e57b0fd8c1d8cc478ec3983c73f08be2e51076acb8e5995a0f0a`.
The registered pilot config SHA-256 was
`1b9946b7f1cf4583371690cec46921543e5ba715dd9035a9d040fada2e2e4b99`.

## Recorded PASS/FAIL, respecting inference missingness

| Check | Outcome | Exact meaning |
| --- | --- | --- |
| Source-law and deterministic codec tests | **PASS** | 139 complete Python regression tests and five focused codec tests passed |
| Official llama.cpp CPU binary integrity | **PASS** | b12248 archive SHA-256 verified |
| Actual Q1 model and LoRA integrity | **PASS** | SHA-256 and byte sizes of the two pinned HF downloads verified |
| Host visible-memory encoding | **PASS** | Both codecs agree with the independent source fixture on the chosen roots |
| Real BitAgent inference occurred | **PASS** | Two initial count-model completions yielded valid independent inference and usage receipts |
| Completed full initial-update decisions | **FAIL: 0/8 cases** | Every arm scored 0 of two roots |
| Verified-codec gain in scored coverage | **FAIL: 0 cases gained** | No assisted arm reached a scored update; this comparison is timeout-censored |
| Complete stage-reset evidence | **FAIL** | Two successful calls had verified OS reset, eight timed-out calls lacked validated teardown receipts |

All source-law cases are public deterministic development examples. Nothing
above measures an independently held-out model generalization result.
The actual policy-regret values for successfully updated cases remain
undefined because zero updates completed.

## Four-arm model result

| Mode and treatment | Valid model-generated initial memory | Completed updates | Stage calls attempted | Stage timeouts | Reported input/output tokens* | Host wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Count, model memory | 1/2 | 0/2 | 3 | 2 | 918 / 81 | 441.46 |
| Count, host-verified visible codec | 1/2 | 0/2 | 3 | 2 | 918 / 81 | 445.72 |
| Bitmap, model memory | 0/2 | 0/2 | 2 | 2 | 0 / 0 | 300.22 |
| Bitmap, host-verified visible codec | 0/2 | 0/2 | 2 | 2 | 0 / 0 | 300.22 |
| **Total** | **2/8** | **0/8** | **10** | **8** | **1,836 / 162** | **1,487.62** |

*Token totals are **observed only on the two completed initial calls**.
Timed-out inference still consumed resources; its token and inference
timing are unmeasured by the existing receipt contract. The zero observed
tokens on bitmap arms mean no valid usage receipts, not free computation.

### Which stages completed?

For public root 0 on `count`, the model returned the correct integer
memory **6** at the initial phase under both treatments. The initial calls
took **141.25 s** (model-memory arm) and **145.50 s** (verified-codec arm).
Both update calls then reached the registered **150-second** stage timeout
without a completed response.

For public root 5 on `count`, the expected initial memory was **8**;
its initial calls timed out in both treatments, leaving model-generated
memory unobserved. The bitmap initial records expected integer encodings
**2643** (root 0) and **1662** (root 5), but all four bitmap initial
calls also timed out. The registered benchmark therefore provides no
model-memory encoding result for these bitmap cases under this CPU limit.

The host verification did not change root 0's integer because the
model had already encoded it correctly. With no completed update in
either treatment, the pilot cannot identify a cognitive improvement from
the sidecar. The fixed missing-case penalty of `20.0` produces the reported
full-information regret value in all arms, but **that number is a
coverage penalty, not measured decision error on a scored case**.

### Server lifetime caveat

The two completed initial calls reported distinct verified process boots
and clean shutdowns. The eight timed-out adapter calls produced no valid
model telemetry or post-teardown receipts. The Actions job cleanup log
also identified orphaned `llama-server` processes, consistent with the
outer subprocess timeout terminating its adapter while a descendant
server remained alive.

The benchmark's `all_stage_server_resets_verified=FAIL` is therefore
important: proof of server teardown is incomplete. The adapter subprocess
was unsandboxed throughout, so `physical_memory_enforced=false` remains
the correct claim.

## Interpretation for the next research experiment

This CPU pilot **does establish that official GitHub-hosted CPU inference
is possible** with the pinned Bonsai Q1 and LoRA checkpoints. Its small
read-only arithmetic validator works, and the original count-mode
initial packet can produce a correct memory integer.

The scientific decision-completion gate failed under the chosen timeout.
The result does not distinguish CPU latency, language-model Bayesian
reasoning, or helpfulness of deterministic state encoding, because every
update-stage contrast was censored. The prior local GPU REV-03/04 results
remain the more informative measures of arithmetic and decision quality.

The [promoted next-run prompt](NEXT_PROMPT.md) therefore begins with
**CPU TIMEOUT / RESET AUDIT FAIL**. It calls for timeout-safe
process-tree teardown and a resource-feasible staged inference protocol
before any larger public or held-out root sweep.

The original generated `NEXT_PROMPT.md` and complete JSON receipts are
preserved in the Actions artifact. The committed prompt is a reviewed
interpretation of those actual PASS/FAIL outcomes, explicitly prioritizing
timeout-censored computation over speculative model reasoning failure.
