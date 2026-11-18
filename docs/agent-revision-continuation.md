# SRB-REV-01: Testing agent memory under delayed evidence corrections

**19 November 2026.** Public, synthetic, source-only evaluation extension. Mathematical ancestry: [Beyond Bayes BB-CQ-05](https://github.com/patrickdugan/beyond-bayes/pull/24) and [LoopedTransformers LRM-REV-03](https://github.com/MoralityLabAI/LoopedTransformers/pull/209).

## Evaluation question

Can an agent preserve enough of its original evidence to revise its belief when an authoritative tool or verifier later supersedes a named record?

The existing SystemicRiskBench history runner supplies cumulative stage packets and prior agent responses. This supports historical case reconstruction. Its cumulative input does not isolate *retained memory*. This track starts a fresh adapter subprocess at each stage, sends no prior responses, and passes only an explicitly validated bounded integer across the memory boundary. The old evidence is withheld on the second call.

## Source law and memory contracts

The host generates twelve named old binary reports under the original ECA-04 three-regime sensor model, with priors (9/20,7/20,1/5) and match probabilities (19/20,13/20,3/20). Six positions are independently chosen as provisional: their old bits are iid fair noise. Six later replacements are drawn under the true regime. The correction set is hidden at the original-encoding stage. All issuer roots here are public deterministic development fixtures.

| Information arm | Valid initial memory | Logical width | Best possible final reference |
| --- | --- | --- | --- |
| **count** | sum(old) in 0..12 | 4 bits | P(K given old_count, named replacement set and replacement values) |
| **bitmap** | sum(old[slot] times 2^slot) in 0..4095 | 12 bits | P(K given all twelve old values, set and replacements) |

The agent must return exactly a bounded memory integer and a three-class probability forecast on the first call. The harness verifies the memory against the initial visible input. The second call presents that integer and six corrected records with host-simulated versioned HMAC receipts. The expected response is exactly three normalized probabilities. Additional free-form response fields are rejected, preventing use as an *in-band* state side channel.

The host validates every correction receipt before forwarding it. These HMAC keys derive from public fixture seeds and provide only structural testing. They are not evidence of live authentication, provenance guarantees or physical freshness.

The complete old transcript, the private true regime and prior response messages are absent from the update packet. The adapter is nonetheless operator-trusted subprocess code and could retain state via external files or services. This harness therefore flags physical_memory_enforced=false and adapter_process_sandboxed=false. Genuine enforced memory limits need an external isolated, resettable execution environment.

## Proper-score interpretation

The per-case **approximation loss** is squared distance from the information-matched Bayes posterior available to that arm. The **information gap** is the squared distance between the exact count-only posterior and full-history Bayes. In expectation under this exact law, that gap equals the additional unhalved Brier loss incurred through the count restriction. Forecasts on a single root do not establish population effects. Invalid or missing forecasts remain in the denominator with a maximum unhalved Brier loss penalty of two and separately reported coverage.

The mathematical continuation lower bound gives 4096 old histories requiring twelve self-contained fixed bits for arbitrary future named corrections. Retaining the current total separately requires ten additional fixed-width tags in its largest 924-history fiber. This is a logical-state bound for the declared event contract, not a claim about neural hidden-coordinate counts or a universal agent architecture.

## What this contributes to agent evaluations

The correction protocol tests whether an agent's persisted state supports *future evidence changes*. A tool result can be superseded; a citation can be withdrawn; another agent's summary can fail to preserve the fact needed for a downstream update. An agent may score well on its first answer and fail a later same-evidence repair. Bounded-memory testing must explicitly state whether an agent can access an external archive, use its own persistent files, replay the full transcript or rely on a verified old-to-new delta.

This benchmark can become a task family for BitAgent's read-only risk analyses and for multi-agent handoffs in Control-Harness. It executes no trades and authorizes no actions. For a subsequent neural study, use model-root-disjoint training, independent issuer roots, measured memory and tool costs, correction-authority controls, and EvalMath's matched sham and power preflight. Keep the corrected information-matched Bayesian baseline when comparing models.

## Reproduction

From the SystemicRiskBench root, with Python 3.10+:

~~~bash
python -m unittest discover -s tests -p 'test_agent_revision.py' -v
python -m systemic_risk_bench agent-revision --adapter-argv '["python","-m","examples.agent_revision_fixture_adapter"]' --experiment configs/agent-revision-fixture.json --mode count --cases 16 --output artifacts/agent-revision-count.json
python -m systemic_risk_bench agent-revision --adapter-argv '["python","-m","examples.agent_revision_fixture_adapter"]' --experiment configs/agent-revision-fixture.json --mode bitmap --cases 16 --output artifacts/agent-revision-bitmap.json
~~~

The fixture adapter is a deterministic mathematical oracle and makes **zero AI model calls**. The harness invokes it using exactly the same subprocess interface that future models use. Both fixture results are engineering validation, not evidence that an actual LLM has passed the evaluation.
