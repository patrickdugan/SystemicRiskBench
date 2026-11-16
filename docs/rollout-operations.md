# Signed-plan rollouts and local result webhooks

The baseline transport uses the installed Codex app-server and its existing
ChatGPT sign-in. It does not extract credentials, substitute an API account,
or require a separate API key. Model IDs and supported reasoning levels are
discovered with `model/list`; a missing model/effort pair fails validation.
Provider model fallback is disabled, and requested/resolved model identities
are retained in each receipt.

The first baseline uses GPT-6.1 Sol, GPT-6 Luna, GPT-6 Sol, GPT-5.6 Sol and
GPT-5.6 Luna at low, medium and high effort. The numerical campaign contains
90 calls. The full historical campaign contains 1,110 calls: 15 model/effort
cells times 74 staged packets. All packets are public-development material.

```powershell
python -m systemic_risk_bench.campaign --config configs/signed-plan-baseline.json --track quant --output-dir artifacts/quant-replicate-02
python -m systemic_risk_bench.campaign --config configs/signed-plan-history.json --track history --output-dir artifacts/history-baseline-v1
```

Each call uses a new ephemeral inference session, an empty inference workspace,
read-only permissions, no environment attachments and explicit prior replies
from that case only. The model receives the current public packet and its
earlier responses; evaluator outcomes, source URLs and future stages are not
sent. Base instructions request concise decision rationales, not private
chain-of-thought. Responses use a constrained JSON schema. Tool and external
lookups are disabled in configuration and instructions; recorded tool use
invalidates that call. This is evaluation through the **Codex runtime**, not
a claim to have measured a bare base model without runtime overhead.

The app-server streams completion and token-usage events to the harness. The
harness then posts one signed `rollout.completed` event to its own HTTP receiver
on an ephemeral `127.0.0.1` port. HMAC-SHA256 signs the exact JSON bytes with an
in-memory random secret. The receiver verifies the signature, stores each event
ID once and responds 202. It never binds to a public interface or sends result
webhooks to a third party. This is a local callback pipeline; it is not the
OpenAI Responses API's provider-webhook service.

`frozen-plan.json` fixes packets, schemas and model/effort configuration.
`provenance.json` records source hashes. Completed receipts are saved atomically;
resuming the same directory reuses them and checks packet/model/effort identity.
Code or plan changes require a new campaign directory. Failed receipts are
preserved, not silently retried until a correct answer appears. Three consecutive
transport errors halt a cell. New replicates use distinct output directories;
the backend does not expose a controlled sampling-seed override here.

Useful runtime files inside the selected artifact directory:

- `status.json`: overall running/completion status.
- `cells/<model>--<effort>/summary.json`: current per-cell progress and metrics.
- `cells/<model>--<effort>/receipts/`: responses, digests, model identity, usage and latency.
- `webhook-events/`: authenticated completion receipts, deduplicated by event ID.
- `campaign-summary.json`: completed cells, failures and webhook count.

Read current progress without changing the campaign:

```powershell
python scripts/campaign_status.py artifacts/history-baseline-v1
```

The per-call wall timeout is enforced. Output length is instructed rather than
enforced as an exact token budget. Input, cached-input, output and reasoning-token
counts use provider telemetry when available; they are not independent hardware
meters. Equal effort labels do not establish equal FLOPs, and wall latency
includes networking, provider and runtime overhead. No stochastic confidence
interval is justified from one replicate per cell.

Numerical scoring remains separate from historical reasoning. A full historical
trajectory needs two blind human reviews for the existing audited reasoning
rubric. Automated judges may provide separately labeled triage; their scores
must not be presented as completed independent human reviews.

Official implementation references:
[app-server protocol](https://learn.chatgpt.com/docs/app-server),
[configuration controls](https://learn.chatgpt.com/docs/config-file/config-reference).

The next phase is BitAgent adapter, TRM, RLM, Lean-reasoning and hybrid inference
endpoints under the same packet contract. The initial artifact/endpoint inventory
is in `configs/next-phase-readiness.json`. An architecture label alone is not a
running model: register checkpoint/code digests, adapter activation evidence,
recurrence policy and the actual inference endpoint before scheduling a cell.
