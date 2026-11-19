# SRB-REV-03: Financial revision panels and forecast coherence

**19 November 2026.** Registration for the source-only work in [issue #6](https://github.com/patrickdugan/SystemicRiskBench/issues/6), continuing [SRB-REV-02](finance-revision.md). The public source law, financial loss schedules and memory codecs stay fixed. Actual BitAgent inference is pending.

## Question and scope

How does retaining the identities of risk records affect a later financial decision after six records are superseded? The count arm carries the sum of twelve old control bits in a declared 4-bit integer. The bitmap arm carries all twelve named bits in a declared 12-bit integer. Each stage requests a posterior over healthy, stressed and crisis regimes, followed by one action from the supplied loss schedule.

The original 48 public roots contain four final policy disagreements between the source-law references. A selected stress panel increases the number of cases where retained information changes the reference action. The natural panel remains available for describing the original issuer sequence. Both panels use invented financial risks and hypothetical read-only decisions.

The source-only registration covers panel selection, forecast/action coherence, missing-response accounting and model-transport receipts. Its deterministic adapter supplies exact arithmetic. Model accuracy and physical memory isolation each require further evidence from the local experiment.

## Frozen panels

[finance-revision-panels.json](../configs/finance-revision-panels.json) contains the roots, the complete selection audit, source hashes and a digest of the manifest. [finance_revision_panels.py](../systemic_risk_bench/finance_revision_panels.py) generates the document and verifies its contents against the current source.

| Panel | Rule | Roots | Purpose |
| --- | --- | ---: | --- |
| `pilot` | First six public roots, indices 0 through 5 | 6 | Check the local transport and measure costs |
| `natural` | First 48 public roots, indices 0 through 47 | 48 | Describe the original source sequence |
| `stress` | First six eligible roots in each financial family, scanning indices 0 through 255 | 18 | Exercise disagreements between memory arms |

Family assignment stays `FAMILIES[index % 3]`, in the order `price_feed`, `collateral`, `counterparty`. For every candidate, the evaluator computes the count and bitmap source-law posteriors, minimizes expected loss under each and compares the resulting final actions. A candidate is eligible when those actions differ. The first six eligible indices in each family are selected; the global execution order is ascending index.

| Family | Eligible among the 256 searched roots | Selected indices |
| --- | ---: | --- |
| Price feed | 10 | 36, 48, 120, 138, 150, 156 |
| Collateral | 6 | 28, 37, 121, 172, 199, 205 |
| Counterparty | 10 | 5, 50, 59, 74, 77, 92 |

The audit contains **18 selected**, **8 eligible after the family quota filled**, and **230 ineligible** roots. Every searched root receives an entry, including its family, reference actions, predicate result and selection decision. The manifest verifies the exact search range and quotas. Insufficient eligible roots cause generation to fail.

The stress panel in global order is:

```text
5, 28, 36, 37, 48, 50, 59, 74, 77, 92, 120, 121, 138, 150, 156, 172, 199, 205
```

Indices 5, 28, 36 and 37 also appear in the natural panel. The pilot is a subset of the natural panel and shares index 5 with the stress panel. These overlaps must accompany any paired report. Combining the panel totals would count some roots more than once.

### What selection permits us to say

The stress panel is conditioned on an evaluator-computed action disagreement. Its inherited count posterior is the posterior under the **original source law**. Knowledge of stress-panel membership changes the available information and the relevant sampling law. The source-law comparator therefore serves as a fixed diagnostic on this selected panel; a Bayes-optimality claim given known panel membership would require a separately derived conditional posterior.

The stress-panel results describe performance on the registered selected roots. Population estimates require independently issued roots and an explicitly defined sampling rule. The deterministic public sequence supports descriptive development results, with uncertainty across independent private roots reserved for a later experiment.

Public root indices, case IDs and the generator also allow fixture reconstruction. Hiding original observations in an update packet establishes the declared interface boundary. A model or adapter with access to the public mapping can recover additional information. Any later memory-capacity claim must account for that access.

## Source-law diagnostics

The following values come from replaying the frozen source law and loss schedules. They contain zero model completions.

| Diagnostic | Natural, 48 roots | Stress, 18 roots |
| --- | ---: | ---: |
| Final reference action disagreements | 4 / 48 | 18 / 18 |
| Count reference action revisions | 13 / 48 | 3 / 18 |
| Bitmap reference action revisions | 17 / 48 | 15 / 18 |
| Mean squared posterior information gap | 0.0359247561 | 0.2683973449 |
| Mean count-policy regret under the full-information reference | 0.0443229960 | 0.5700017726 |
| Full-information final `continue` actions | 23 | 10 |
| Full-information final `de_risk` actions | 18 | 8 |
| Full-information final `halt_and_escalate` actions | 7 | 0 |

The registered stress panel has zero final full-information escalation cases. Escalation coverage is supplied by the natural panel. Altering the stress selector to add escalation cases requires a new panel version and its own audit.

For family $f$, let $L_f(a,z)$ be the fixed loss of action $a$ in regime $z$. The action rule is

$$
a_f(p)=\operatorname*{arg\,min}_{a}\sum_z p_z L_f(a,z),
$$

with ties resolved in the registered action order: `continue`, `de_risk`, `halt_and_escalate`.

Each root contributes its squared posterior gap

$$
G=\sum_z(p^{\mathrm{count}}_z-p^{\mathrm{bitmap}}_z)^2
$$

and the full-information cost of the count reference policy,

$$
I_f=\sum_z p^{\mathrm{bitmap}}_z L_f(a_f(p^{\mathrm{count}}),z)
    -\min_a\sum_z p^{\mathrm{bitmap}}_z L_f(a,z).
$$

This second quantity measures the decision cost associated with the registered information restriction on each root. Its units are the invented loss points in the scenario. The report computes these oracle diagnostics on all registered roots, regardless of model coverage, and supplies the same summaries by financial family.

## Forecast and action scoring

For a model posterior $\hat p$ and reported action $\hat a$, the evaluator records own-forecast excess loss:

$$
C_f(\hat a,\hat p)=\sum_z\hat p_zL_f(\hat a,z)
                    -\min_a\sum_z\hat p_zL_f(a,z).
$$

An action with positive excess loss conflicts with the model's own forecast. The coherence flag requires exact agreement with `optimal_action(forecast, family)`, including its deterministic tie order; it uses no numerical tolerance. An alternate action at an exact tie has zero own-forecast regret and fails that action-rule check. Initial and update stages receive separate coherence fields and counts, so an invalid update leaves a valid initial-stage observation available for inspection.

Reference regret uses the arm's source-law posterior in the same expression. A model can choose a coherent action from an inaccurate posterior, or report an accurate posterior and choose a costly action. Reporting both quantities makes those cases observable. Full-information regret scores the same submitted action against the bitmap reference.

The forecast score is unhalved squared L2 distance to the arm's source-law posterior. The hidden-regime sample Brier score and realized synthetic loss remain available as descriptive secondary quantities. Revisions compare each valid submitted initial action with its valid update action. Reference revision frequencies come from the initial source-law posterior and each arm's final reference.

Every panel report includes its registered root count, scored root count and coverage. A root that fails at either stage receives the fixed **2.0 forecast penalty** and **20.0 policy-regret penalty** in the corresponding coverage-adjusted means. Action accuracy counts a missing or invalid root as incorrect. The same missing policy penalty applies to coverage-adjusted full-information regret. Scored-only means retain an explicit scored denominator.

Coherence rates use the number of valid forecasts and actions at the corresponding stage. Missing responses have their own counts. Incoherence is a decision property that requires a valid forecast/action pair, so a missing reply cannot establish it.

## Reproduce the source-only work

Generate a candidate manifest after a deliberate source change:

```bash
python -m systemic_risk_bench finance-panel --output configs/finance-revision-panels.json
```

Check the committed registration before executing a named panel:

```bash
python -m systemic_risk_bench finance-panel --verify configs/finance-revision-panels.json
python -m unittest discover -s tests -p 'test_finance_revision*.py' -v
python -m unittest discover -s tests -q
```

The manifest records SHA-256 values for the source files that define the fixture, policy and selection. Verification recomputes the complete manifest. Git attributes preserve LF source bytes on Windows and Unix checkouts. A source change requires a deliberate regeneration and review of the registration before another run.

Run the deterministic adapter on both natural-panel memory arms:

```bash
python -m systemic_risk_bench finance-revision --panel natural --manifest configs/finance-revision-panels.json --adapter-argv '["python","-m","examples.finance_revision_fixture_adapter"]' --experiment configs/finance-revision-03-fixture.json --mode count --output artifacts/finance-natural-count.json
python -m systemic_risk_bench finance-revision --panel natural --manifest configs/finance-revision-panels.json --adapter-argv '["python","-m","examples.finance_revision_fixture_adapter"]' --experiment configs/finance-revision-03-fixture.json --mode bitmap --output artifacts/finance-natural-bitmap.json
```

Run the selected stress panel:

```bash
python -m systemic_risk_bench finance-revision --panel stress --manifest configs/finance-revision-panels.json --adapter-argv '["python","-m","examples.finance_revision_fixture_adapter"]' --experiment configs/finance-revision-03-fixture.json --mode count --output artifacts/finance-stress-count.json
python -m systemic_risk_bench finance-revision --panel stress --manifest configs/finance-revision-panels.json --adapter-argv '["python","-m","examples.finance_revision_fixture_adapter"]' --experiment configs/finance-revision-03-fixture.json --mode bitmap --output artifacts/finance-stress-bitmap.json
```

Use `--panel pilot` for the first six roots. Named panels use their manifest-defined root counts; combining them with `--cases` is rejected. Existing `--cases` commands remain available for the legacy development interface.

## Local BitAgent registration and costs

The model target is BitAgent Bonsai-8B served through the local llama.cpp adapter. Before the pilot, freeze the local base-model and LoRA file hashes, the serving executable and launch arguments, both memory arms, the manifest digest, sampling settings and run budgets. The proposed decoding settings are temperature 0, seed 0 and at most 1,024 output tokens per call. The runtime configuration must agree with the registered experiment. Record the prompt-token compliance threshold, per-call timeout and total job limit before execution.

The [v3 pilot template](../configs/finance-revision-bitagent-v3.template.json) carries the expected base and LoRA hashes already listed in the repository's runtime template. Local file verification remains required. Copy it into ignored `artifacts/`, replace its experiment ID and manifest placeholder, and set `status` to `registered` only after review. The runtime config's `max_tokens` must be set to 1024; the older general-purpose runtime template uses 2048. The model CLI requires explicit model registration, including when an older template omits the model marker.

The experiment marks a model campaign with `evaluation_kind="model"`. Its `panel` and `panel_manifest_sha256` bind the root selection. Register `memory_arms=["count","bitmap"]`, `base_sha256`, `checkpoint_sha256` and `model_alias` together with `temperature=0`, `seed=0` and `max_output_tokens_per_call=1024`. The pilot, natural and stress registrations use `preregistered_cases` of 6, 48 and 18 respectively, and `max_calls_per_arm` of 12, 96 and 36. Each model registration also requires `max_wall_seconds_per_arm`; the pilot template sets 600 seconds per arm.

| Phase | Roots per arm | Maximum adapter calls across both arms | Maximum generated tokens at 1,024 per call |
| --- | ---: | ---: | ---: |
| Pilot | 6 | 24 | 24,576 |
| Natural comparison | 48 | 192 | 196,608 |
| Stress diagnostic | 18 | 72 | 73,728 |

These ceilings assume an initial and an update call for every root. A rejected initial response stops that root before its update. Token ceilings describe output only; prompt processing, file verification and server startup add costs. Pilot findings may support transport repairs, followed by a versioned registration before the full comparison. Any model tuning on these public roots must be recorded.

The per-arm wall limit stops further client calls and bounds the time allowed for an adapter subprocess. Roots left incomplete keep their missing-response penalties. Server-side cancellation needs separate process evidence because a persistent server can continue work after its client exits. The optional `max_input_tokens_per_call` threshold is checked against returned usage after inference; an excessive prompt has already consumed compute. The pilot template uses 7,168 input tokens, leaving 1,024 output tokens within the configured 8,192-token context.

The runner measures host wall time around the adapter subprocess. The adapter separately reports request latency and token counts supplied by the inference server. Structured receipts bind those measurements to packet and response digests and include the registered model identity and sampling settings. Costs incurred by rejected or truncated completions remain reportable when the server supplies usage. Missing telemetry stays unknown and reduces measured-cost coverage.

Server token telemetry and runtime identity fields are adapter-reported evidence. Independent verification must establish which artifacts the serving process loaded. Local file checks, an expected server alias and active-adapter metadata support a reproducibility record; they leave the running base model's identity dependent on the deployment evidence.

The legacy field `model_calls_attempted` counts adapter invocations. A deterministic fixture can therefore have a nonzero value in that field. A model-result release requires actual inference receipts, the frozen configuration and a record of the machine used. GitHub-hosted source-only runs exercise fixtures and fake HTTP responses.

## Memory and packet boundaries

Each root starts a fresh adapter process for the initial stage and a second process for the update. The host transfers the validated integer memory. The update packet excludes the earlier observations and response. The transport rejects unknown fields, replayed history and malformed nested records before issuing the model request; response validation enforces the phase-specific field allowlist.

A physical bounded-memory claim requires a separately reset server for every stage, with a deployment boundary that prevents reuse of KV state, files or another channel. Two serving modes are supported:

- **Persistent loopback (`operator_owned_loopback_llama_cpp`):** an operator-started server handles requests with `cache_prompt=false`, leaving an unverified server reset boundary (`model_server_state_reset_verified=false` and `physical_memory_enforced=false`).
- **Ephemeral per-stage server (`ephemeral_per_stage_llama_cpp`, [ephemeral_llamacpp.py](../adapters/ephemeral_llamacpp.py) and [ephemeral template](../configs/finance-revision-bitagent-ephemeral-v3.template.json)):** each stage verifies the pinned `llama-server` executable, base GGUF and LoRA SHA-256 digests, reserves an unused loopback port, boots a fresh `llama-server` process in an empty temporary working directory without slot persistence, binds the child process to a kill-on-close OS job/session so cleanup survives client timeouts, serves at most one completion, and terminates the process and verifies port closure before emitting stage telemetry. Each stage records a unique `server_boot_sha256` alongside startup and shutdown durations. When every attempted stage in a run presents a valid ephemeral receipt with a distinct `server_boot_sha256`, the report sets `model_server_state_reset_verified=true`. Because the Python adapter subprocess itself runs on an unsandboxed host with access to public source code, `physical_memory_enforced=false` and `adapter_process_sandboxed=false` remain false until paired with an OS container/filesystem sandbox and private issuer roots.

## Future typed numeric ledger track

Issue #6 also proposes financial evidence that carries quantities and temporal meaning. That track needs its own schema and registration. A record should identify the instrument or counterparty, amount and unit, valuation currency where applicable, effective-as-of time, observation time, issuer authority, version and superseded record. A correction must carry a typed operation whose scope is explicit.

| Proposed case | Correction | Evaluator requirement |
| --- | --- | --- |
| Price feed | A stale quote is superseded by a quote with a different effective time | Select the authoritative quote for the decision time and preserve its unit |
| Collateral | A valuation or haircut changes | Recompute eligible value using the registered precedence and arithmetic |
| Counterparty | An exposure limit or probability-of-default estimate is withdrawn | Apply the defined missing-value policy and authority rule |

Version precedence must specify how authority, effective time and withdrawal interact. Late arrival alone cannot determine precedence. Register numeric loss functions, rounding rules, conflicting-authority cases and the treatment of unavailable values before model scoring. Synthetic ledger cases should carry their own evidence label, with historical financial data entering through a separate provenance process.
