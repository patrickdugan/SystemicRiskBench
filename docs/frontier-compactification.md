# SRB-HARD-01: frontier reasoning and compact skill acquisition

## Target and present status

SystemicRiskBench should measure whether an agent can learn an unfamiliar
financial mechanism, assemble an executable policy and preserve that competence
when its inference resources shrink. Opus 4.5 and stronger reference systems
anchor the intended solvability range. INTELLECT-3 is an open-weight reference
candidate. BitAgent, augmented with learned recurrent skills and verified
reasoning, is the compact system whose progress the benchmark should expose.

The user's phrase "ARC 2.5 level" describes the desired challenge. Calibration
will use actual SRB episodes and measured resource budgets. ARC-AGI-2 supplies
useful design principles: infer contextual rules, combine them in unfamiliar
ways and report the cost of solving tasks. Its official task distributions and
scores remain specific to ARC. [ARC-AGI-2 design](https://arcprize.org/arc-agi/2)

**Status: design proposal, awaiting difficulty calibration.** The existing six
arithmetic tasks, historical cards and SRB-CF-02-DEV policy harness provide
development infrastructure. The hard task bank and protected test set still
need construction. This document records the target and admission criteria;
it reports zero new model evaluations.

## Difficulty tiers

| Tier | Task | Evidence it should produce |
| --- | --- | --- |
| L0: prerequisites | Existing calculators, action contracts, accounting and simulator controls | Correct units, valid actions and reproducible scoring |
| L1: mechanism learning | Infer a short rule from examples; choose a useful query; repair an assumption after new evidence | Transfer to new values and symbols with a witnessed feasible solution |
| L2: systemic composition | Combine several mechanisms through a staged policy whose actions change later observations and constraints | Held-out policy success under the declared information, action and query limits |
| L3: skill acquisition | Learn on a public curriculum, freeze a skill bundle, then compose skills on reserved task groups | Improvement per training cost, retained earlier competence and deployment efficiency |

The main hard score comes from L2. L3 measures the learning program that builds
the deployed solver. More difficult future releases can add longer causal
dependencies after the first version has a measured difficulty distribution.

## What makes an episode difficult

A task presents a small institution graph, a typed balance sheet and a few
observed transitions. It supplies the relevant vocabulary and primitive laws.
Some combinations or context-dependent rules must be inferred from the
demonstrations. The agent can request observations at stated costs and must
commit before the next state appears.

Every scored L2 episode should require a decision-changing interaction among
mechanisms. Its companion cases change one causal assumption while preserving
plausible surface cues. A correct policy must respond to that change. Name
permutations and extra decimal places serve as robustness checks.

Candidate domains for the first bank:

| Domain | Rule interaction to learn | Executable consequence |
| --- | --- | --- |
| Funding and maturity | Cash arrival time interacts with payment priority and an expiring credit line | A solvent portfolio can miss an earlier cash obligation |
| Collateral and wrong-way risk | Borrowing capacity falls when the pledged issuer weakens | A nominal hedge can consume the buffer needed to survive stress |
| Settlement and netting | Legal netting scope interacts with sequence and delivery conditions | The order of otherwise similar transactions changes required liquidity |
| Crowding and market impact | The same local exit rule changes prices as adoption grows | A policy must throttle or coordinate execution under a shared capital budget |
| Counterparty networks | Guarantee direction, seniority and recovery interact across a graph | Protecting one node can move losses onto another creditor |
| Oracles and timing | Observation age interacts with collateral updates and settlement finality | A useful-looking signal can be irrelevant to the current decision cutoff |
| Information acquisition | A query reveals which later signal matters | A query with zero immediate value can enable a valuable later query |
| Constraint repair | A discovered exception invalidates one premise of a proposed policy | The agent must repair the policy and its proof obligations before committing |

These are domain labels. Independence is determined by generator ancestry and
shared causal construction. A hundred parameter draws from one generator
remain correlated variants of that construction.

An example L2 episode could combine collateral eligibility, a funding deadline,
conditional settlement and price impact. The agent observes several small
transactions, infers the collateral rule, purchases a discriminating observation,
then orders a hedge and funding action while preserving cash for settlement.
Its transfer twin changes settlement precedence, making the earlier policy
fail. The scorer accepts every policy satisfying the same outcome criteria.

The [nonmyopic query example](nonmyopic-query-example.md) gives a fully worked
L1 case. It isolates one capability the hard tier will compose with financial
state transitions. Its small size makes exhaustive checking possible.

## Same information for agent and reference solver

Let h contain the released history, remaining budget and the agent's earlier
actions. For a finite task, the oracle evaluates policies over h. It cannot
choose a different action for two hidden worlds that generate the same h.
When queries are available, their price, latency and effect on later feasible
actions enter the state transition.

For a task with terminal actions and optional queries, the reference recurrence
is

$$
V(h)=\min\left\{\min_a\mathbb E[L(w,a)\mid h],\;
\min_q\left[c_q+\sum_z P(z\mid h,q)V(h,q,z)\right]\right\}.
$$

The oracle's prior over mechanisms must also be part of the task's public
rules, or derivable from the same demonstrations. A policy that is measurable
in public observations can still exploit privileged knowledge of the true
transition law. Record both sources of information in the oracle contract.

Cases with unresolved ambiguity need a declared robust objective or a score
bound. An unattainable clairvoyant optimum is reported as an information bound.
Task admission requires a witnessed policy feasible under the actual query
budget. Its program must fit the declared grammar, output-size and execution
limits. An offline solver can spend additional computation to establish the
optimum; that search cost is recorded separately from the witness's deployment
cost. A lower bound with no feasible witness remains a bound. Query selection
and early commitment become part of reasoning quality.

## Outcomes and a proposed pass rule

Use complete policies as the scoring unit. Evaluate a frozen contingent policy
over the registered world bank or a prospectively sampled distribution. A lucky
single-world outcome cannot establish success for a policy with poor expected
performance. The sequence runner must share frozen decisions across identical
observable histories.

The primary objective charges realized investor loss, creditor loss, execution
costs and opportunity costs according to one published accounting model.
Evidence queries also carry their declared costs. Report tail loss and losses
to passive parties separately. Submitting an executable action that violates
a constraint established by the public contract or known state makes that
episode unsuccessful at the commit boundary, including when a gate blocks it.
Rejected internal candidates and failed proof-search attempts are recorded as
search work. An allowed probe that
discovers unknown eligibility has its own modeled result and cost.

For episodes with positive baseline headroom, define

$$
r(\pi)=\frac{J(\pi)-J^*_{\mathrm{information,budget}}}
{J(\pi_0)-J^*_{\mathrm{information,budget}}}.
$$

Here pi_0 is a preregistered admissible baseline, selected from the cheap-policy
controls using calibration data and fixed before test. The draft episode success
criterion is valid execution with r <= 0.10, plus any required certificate.
The denominator is checked before task admission. Set a minimum headroom per
task scale before selection; cases below it use an absolute-regret criterion
so a rounding cent cannot determine the normalized score. Calm controls with
zero headroom retain their own reported stratum and a frozen absolute cost
tolerance. Always publish absolute regret as well. Simulation failures are recorded as infrastructure
failures with preserved decisions and a frozen rerun policy.

The proposed hard pass is at least 70% macro success across eligible L2 source
groups, with at least 50% within each domain. Zero- and tiny-headroom controls
are excluded from that hard score and domain floors. They have a separate
proposed 90% success gate under their frozen absolute-regret tolerances. Those
values are design candidates for calibration. A run also reports attempted constraint violations and false
certificate acceptances. A release-level safety qualification requires zero
observed violations in the evaluated set; its uncertainty remains visible.

## Calibration with frontier references

Freeze a pilot protocol before reference inference. Use public training
material and a separate calibration bank. Select the final difficulty mixture
there, then freeze the test protocol and generate the protected holdout.
Changing difficulty after final test feedback creates a new benchmark version.

| Candidate | Role | Current SRB-HARD-01 status |
| --- | --- | --- |
| Claude Opus 4.5, exact dated model ID | Named solvability anchor | Not run |
| A pinned stronger frontier model | Tests ceiling and breadth of the task bank | Not run |
| INTELLECT-3, pinned weights and tokenizer | Open-weight reasoning reference | Not run |
| BitAgent Bonsai-8B base plus registered adapter | Compact deployment baseline | Hard-track bridge pending |
| Deterministic and greedy policies | Detect shortcut solutions and quantify avoidable loss | Per-task implementations pending |

The draft calibration target puts the named frontier anchor at 70-85% L2
success under its declared reference budget. A stronger model may exceed that
range. INTELLECT-3's performance is a measurement target. Its developer describes
106B total parameters and 12B active parameters; report both alongside resident
memory when comparing it with BitAgent. [Model card](https://huggingface.co/PrimeIntellect/INTELLECT-3)

Opus 4.5's dated API identity is `claude-opus-4-5-20251101`. Its launch evaluations
used task-dependent thinking and context budgets. The SRB run must therefore
record its own effort setting and limits. Published benchmark scores cannot
substitute for this calibration. [Developer announcement](https://www.anthropic.com/news/claude-opus-4-5)

Inspect the full distribution, including task failures and solver costs. If a
few easy groups support a high average while another domain is inaccessible,
revise the calibration bank's task construction. Keep that revision history.
Script-only, nearest-demonstration and greedy-query baselines test whether the
selected tasks require the intended reasoning. An unexpectedly strong BitAgent
score is evidence to investigate and reproduce.

## Compactification and skill assembly

The compact target is a deployed BitAgent system with a semantic proposer,
learned reusable skills and a deterministic execution boundary. Its Lean
component checks explicitly stated obligations. Training data and deployment
cost are counted for every component of that system.

The [implementation mapping](compact-skill-integration.md) identifies current
native interfaces and the financial bridges they need. A proposed skill has
typed inputs, preconditions, an action or proof-search procedure, an output
contract and a resource limit. Its registry records training-group ancestry,
weights or source hashes, verifier identity and measured failure behavior.

Useful skills include cash-flow scheduling, legal netting, collateral capacity,
query selection and invariant repair. Train them on public primitives, freeze
their implementation, then require combinations absent from training.
Transfer twins alter a rule so a cached plan needs revision. A specialist is
successful when it changes held-out policy outcomes under matched resources.

Lean obligations can establish conservation of balances, the order of permitted
transfers or bounds under supplied haircut assumptions. The host constructs
the theorem statement from the actual action and state. The submitted proof
must close that statement under an explicit axiom allowlist. Tests include
invalid assumptions and false conclusions. Economic realism remains an
empirical property of the environment.

Keep separate arms for plain BitAgent, deterministic tools, a fixed skill router,
a learned recurrent router, and the full learned router with Lean search.
Frontier models receive the same tool interfaces in matched-tool comparisons.
Lean automation alone and a flat model with extra equivalent compute establish
whether the learned search or recurrence improves outcomes. Scratch reasoning
contents are unnecessary; concise rationales and executable receipts suffice.

## Resource and learning protocols

The proposed matched profile uses a 12,000-token live context and 48,000
cumulative input-plus-generated tokens per episode across every root, critic
and child invocation. It allows eight model invocations, 24 environment/tool
calls, 60 aggregate CPU seconds of proof checking and a 600-second wall limit.
The eight-call limit covers token-generating root and child models. Typed
learned-skill invocations have a separate cap of 32, with 256 recurrent steps
and 32 Lean attempts across the episode. Their time and memory are also metered.
These are pilot defaults. Record hidden reasoning usage when the provider
exposes it; an unknown measurement prevents a verified compute-matching claim.

A separately labeled frontier-capacity profile permits 64,000 live context
tokens, 256,000 cumulative tokens, 32 model invocations, 128 tool calls,
300 proof CPU seconds and 1,800 wall seconds. It permits 128 learned-skill
invocations, 1,024 recurrent steps and 128 Lean attempts. Solvability calibration uses this
profile if the matched profile creates an inference-capacity bottleneck. Scores
from the two profiles remain separate. BitAgent's deployment target is measured
on its actual device, with peak VRAM and host memory recorded.

For recurrent components, record total internal steps and all evaluated
candidates, including failed repairs. Deployment size includes resident expert
weights, cached programs and the skill library. Report pretraining separately
from benchmark-specific teacher generation, training and adaptation costs.

L3 has two protocols. In frozen transfer, training ends before the test set is
opened. In the acquisition track, a bounded support phase may add or train
skills; the resulting bundle is frozen before a fresh query phase. Test labels
never enter support training. Re-test prior skills after acquisition and report
forgetting alongside new competence. Reset working memory between unrelated
groups, and declare which durable skill state is allowed to persist.

## Split design and release gates

Keep each generator lineage and its semantic twins in one partition. Split on
causal programs and institution-graph structure, then vary names and numbers
within that structure. Check for equivalent programs after renaming and graph
isomorphism. A secret seed applied to a public template supplies fresh numbers;
new mechanism compositions need their own transfer evaluation.

The provisional final bank target is at least 32 source groups with four
eligible hard episodes and at least one control per group across the eight
domains. Final size follows a
pilot-independent precision calculation. These counts describe planned work.
Shared ancestry can reduce the effective number of independent groups.
Aggregate seeds and variants inside each source group before uncertainty
analysis, and report the broader domain dependence.

Before a hard release, require independently replayed transitions, feasible
reference policies, passed information-boundary checks, reviewed human
solutions, complete frontier calibration and a frozen holdout procedure.
Two independent solvers should reconstruct each task's valid policy using the
allowed information. Include calm cases and action-neutral controls with the
same selection rules as stressed cases.

The first implementation milestone is one staged two-mechanism family, together
with its causal twin, a budgeted observation-policy solver and typed proof
obligations. Only after that interface survives independent replay should the
bank expand across domains and connect trained compact components.
