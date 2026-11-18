# Compact skills for systemic policy reasoning

**Design status, 18 November 2026:** proposed financial interfaces. This document
maps inspected native implementations to a harder systemic-risk track. It records
no new model inference or trained financial skill. Opus 4.5 and INTELLECT-3 are
prospective comparison arms; passing thresholds require calibration and a frozen
evaluation protocol before a held-out comparison.

## Source identities and present capabilities

The existing [architecture queue](../configs/architecture-queue.json) registers
LoopedTransformers commit `254edb4e9a864af06ba656fec3fe54cb49940541`.
GitHub returned `No commit found for the ref` when that pin was requested in this
session. For design reading, the files below were inspected at the accessible
commit `90d9fa1b9fbd1b388693e294674c30bed0099946`. This separate source snapshot
does not replace the queue's checkpoint identities or establish reproducibility
of the unavailable revision. The Windows checkpoint files remain outside this
checkout; their recorded verification status comes from the existing queue.

| Component | Inspected implementation | Financial integration required |
| --- | --- | --- |
| Bonsai-8B Q1 with DAG v3 LoRA | [SRB adapter](../adapters/llamacpp.py) and [artifact queue](compact-adapter-queue.md) require the registered base and one active LoRA | A typed financial proposal decoder, current-stage evidence references and an executed policy interface |
| ControlTRM | [48-dimensional recurrent proposer][control-trm] maps supplied features to action, confidence and provenance outputs | Train a financial router from public features; log actual checkpoint inference and recurrence visits |
| TRM/LDT conductor | [Runtime][hybrid-runtime] supports proposal, verification and commit receipts | Replace native task tables and action vocabulary with the financial interface below |
| Lean tactic model | [Byte-level tactic LM][tactic-lm] reads 384 goal bytes and emits up to 96 tactic bytes | Financial obligations with preserved Lean state, an explicit projection receipt and a compatible tactic evaluator |
| CGRT search | [Lean-backed search][lean-search] controls expansion, branching and learned branch scores | Bind financial obligations to the appropriate graph-policy model; the byte tactic LM has a different interface |
| Control-Harness | [Attested controller][control-code] at `74f0e097c7818c790bf41b9260f6478973dc3c1d` handles registry identity and archive decisions | Financial authority scopes, evidence freshness and resource enforcement around policy execution |

The [HybridTRMLDT proposer][story-trm] at its existing queue pin
`1688515d1b29509ea1e0b11b51d93cb2eb9fb4c4` was also readable. Its features describe
story trust, evidence, heat and scene; its actions include `befriend` and `defuse`.
Those weights provide a native control baseline pending a measured financial bridge.

ControlTRM initializes its hidden state from zero on each forward call. Its
recurrence performs repeated computation on the supplied features. Carrying a
learned skill state between decisions needs an added interface and training test.

### Native shortcuts that need explicit controls

`run_local_architecture` consumes `trained_row["ranked_actions"]` from a proposal
table. A financial run must compute its own proposals from the current packet.
The native `ldt_action` ranks supplied `ldt_scores` within `exact_allowed`, while
the [task definition][hybrid-tasks] also carries utilities and the optimal action.
Some native public scores are constructed from task utilities. Importing these
tables into a financial agent would contaminate the competence measurement.

The financial gate may derive admissibility from released constraints. Future
losses, hidden state and optimal-policy labels belong to the evaluator. A gate
that repairs a proposal must expose both the original proposal and the executed
fallback, so repaired performance can be attributed to the gate. Internal
candidate rejection is search work; an inadmissible commit attempt is a
constraint failure even when the gate blocks execution.

## Proposed division of work

Bonsai interprets evidence and emits a bounded policy program plus explicit
assumptions. A learned TRM router selects a skill and its recurrence budget from
that typed state. Candidate skills cover exposure aggregation, collateral and
funding arithmetic, dependency tracing, or bounded liquidation scheduling.
The LDT component can rank candidate refinements; a deterministic checker
derives admissibility from the public constraint specification.

Lean checks the obligations generated from each candidate. Control-Harness then
checks authority and resource receipts before allowing the simulator to execute
the exact action bytes covered by the certificate. Prices and newly released
evidence produce the next observation and can invalidate earlier certificates.
The financial simulator supplies realized outcomes for evaluation after each
decision is frozen.

These roles are a proposed interface contract:

| Interface | Required payload and receipt |
| --- | --- |
| `propose(packet, budget)` | Evidence IDs, typed quantities with units, assumptions, bounded policy AST and candidate action hash |
| `route(state, skill_catalog, budget)` | Skill ID/version, input hash, checkpoint hash, recurrence visits, halt decision and returned-state hash |
| `check(candidate, public_state)` | Deterministic admissibility result and constraint IDs; utility and hidden-world outcomes stay outside this response |
| `prove(obligation)` | Exact statement and assumptions, Lean/Mathlib versions, proof artifact, kernel result, axiom inventory and cost receipt |
| `commit(action, certificate)` | Matching action, packet, state and authority hashes; stage/expiry check; explicit refusal or execution receipt |

A certificate covers the theorem that the trusted compiler produced. Testing
the compiler's translation from units, cash flows and action semantics is part
of the benchmark. Empirical assumptions about depth or funding stay explicit.

## Lean interface and proof controls

The current tactic model keeps the **last 384 UTF-8 bytes** of a goal. Preserve
the complete goal and context inside Lean, and record the exact bytes supplied
to the model along with a truncation flag. Decompose larger obligations into
named lemmas through a checked transformation; the model's short view cannot
replace the original statement. The 96-byte output limit also needs a distinct
`unsupported_or_exhausted` result when the proposed tactic cannot fit.

[`certify.py`][fragment-cert] accepts only `apply h/r...` and `constructor` in its
propositional fragment. The separate [Mathlib evaluator][mathlib-eval] tests
candidate tactics at their source state, requires goal closure and kernel
acceptance, and checks axioms against its declared standard set. A financial
arithmetic bridge should use that stronger replay pattern with an explicitly
approved theory. Reusing the fragment certifier requires expressing the claim
within its actual fragment.

Report tactic-model-only closure, automation-only closure and their interleaved
policy at the same Lean-call budget. CGRT comparisons need `best`, `cgrt` and
`cgrt_shuf`, with matching context counts and expansion costs. A completed
certificate establishes the stated invariant; competence is measured through
the policy's utility and generalization on the financial task.

## Budgeted arms

Set **12,000 tokens per program context** as a hard ceiling including system
instructions, evidence, tool returns, retained history and reserved output.
Meter each program separately and also enforce an episode-wide cap. The
proposed matched profile permits eight semantic-model invocations and 48,000 total
input-plus-output tokens, with one child active at a time. Every child consumes
the same episode budget. Freeze tokenizer versions and report native counts.
Use identical packet bytes across arms and disclose any model-specific projection.

Use the [design manifest](../configs/frontier-hard-v1.design.json) as the budget
source: 24 environment/tool calls, 32 learned-skill invocations, 256 recurrent
steps, 32 Lean attempts, 60 proof CPU seconds and a 600-second episode deadline.
These are proposed development settings to freeze after a resource smoke. Count recurrence visits,
CPU/GPU time, peak memory and tool latency independently. Provider-internal
compute remains unknown when telemetry is unavailable.

| Arm | Purpose |
| --- | --- |
| Scripted solver with the shared tools | Expose how much competence the supplied mechanics and deterministic algorithms already provide |
| Opus 4.5 / INTELLECT-3 semantic controller with shared tools | Establish difficulty and a measured quality/cost target on identical observations |
| Bonsai semantic controller with shared tools | Establish the compact model's starting competence |
| Bonsai plus frozen learned router/skills | Measure additional competence from the compact skill library |
| Full compact system with Lean and authority gate | Measure executed utility, certificate coverage and enforcement together |
| Matched ablations | Replace learned routing with fixed or shuffled routing; reset recurrent state; vary visits over 1, 2, 4 and 8; remove learned tactics while retaining automation |

Run gate ablations in an isolated simulator and retain pre-gate proposal scores.
Compare competence at matched total cost, including verification and fallbacks.
Record refusal opportunity cost and useful-action coverage so universal refusal
cannot supply a competitive policy score. All arms receive the same authorized
tools and observation access; tool availability is a separate experimental factor.

## Skill retention and composition

Freeze skill weights and the catalog before evaluation. Hold out generator
families, institution names and parameter regimes. Test new compositions of
previously learned primitives, longer dependency chains and changed timing of
funding or collateral events. Reordered descriptions and renamed nodes preserve
the intended mechanics and test reliance on incidental labels.

After learning each added skill, replay an immutable earlier-skill test set and
report forgetting alongside the new-skill gain. Compare frozen skills, rehearsal
and joint retraining at recorded training budgets. Evaluation episodes start
from fresh memory; within-episode recurrent memory gets a matched reset control.
Audit the router's chosen skill, skill execution and final policy separately.
Source-disjoint holdouts must precede claims about transfer.

## Finite next increment

Build a public development slice with a typed policy grammar and two staged
financial mechanisms, each containing useful-action and refusal-cost cases.
Add the deterministic solver and independent transition tests before attaching
models. Export exact arithmetic obligations for the permitted actions, then
connect the Bonsai proposal adapter and the Lean replay adapter under the shared
budget ledger. Train one small router on development traces and compare it with
fixed routing on reserved generator seeds. This increment establishes end-to-end
execution and skill attribution; a later family-level holdout establishes the
hard benchmark's difficulty and compactification target.

[control-trm]: https://github.com/MoralityLabAI/LoopedTransformers/blob/90d9fa1b9fbd1b388693e294674c30bed0099946/research_gym/neural/control_trm.py
[hybrid-runtime]: https://github.com/MoralityLabAI/LoopedTransformers/blob/90d9fa1b9fbd1b388693e294674c30bed0099946/research_gym/benchmarks/rlm_hybrid_runtime.py
[hybrid-tasks]: https://github.com/MoralityLabAI/LoopedTransformers/blob/90d9fa1b9fbd1b388693e294674c30bed0099946/research_gym/benchmarks/rlm_hybrid_neighborhood.py
[tactic-lm]: https://github.com/MoralityLabAI/LoopedTransformers/blob/90d9fa1b9fbd1b388693e294674c30bed0099946/research/lean_cgrt_hrm400/lcgrt/tactic_lm.py
[lean-search]: https://github.com/MoralityLabAI/LoopedTransformers/blob/90d9fa1b9fbd1b388693e294674c30bed0099946/research/lean_cgrt_hrm400/lcgrt/search.py
[fragment-cert]: https://github.com/MoralityLabAI/LoopedTransformers/blob/90d9fa1b9fbd1b388693e294674c30bed0099946/research/lean_cgrt_hrm400/lcgrt/certify.py
[mathlib-eval]: https://github.com/MoralityLabAI/LoopedTransformers/blob/90d9fa1b9fbd1b388693e294674c30bed0099946/research/lean_cgrt_hrm400/lcgrt/mathlib_eval.py
[control-code]: https://github.com/MoralityLabAI/Control-Harness/blob/74f0e097c7818c790bf41b9260f6478973dc3c1d/src/evals/oracle_control_harness.py
[story-trm]: https://github.com/MoralityLabAI/HybridTRMLDT/blob/1688515d1b29509ea1e0b11b51d93cb2eb9fb4c4/research_gym/neural/trm.py
