# Repository integration and next study

Inspected base: BitAgent main at `09fe9239a25618cafece2b89e7f15062842b8e76`.
The benchmark now lives in the standalone patrickdugan/SystemicRiskBench repository. The existing BitAgent checkout supplied its initial source and active baseline jobs. BitAgent-relative paths in the table below refer to that companion repository.

| Existing seam | Current use | Remaining work |
| --- | --- | --- |
| `apps/bitagent-launch-kernel/src/mandates/types.ts` — `StrategyCovenant`, `StrategyProposal`, `StrategyPortfolioState` | Read-only projection of covenant v1 risk, strategy, execution and runtime fields | Export native validated snapshots and retain host verification receipts |
| `src/mandates/benchmark.ts` — `createStrategyBenchmarkScenario` | Reviewed strategy allocation, leverage and candidate-only fixture conventions | Add optional native TypeScript exporter when model runs are wired |
| `src/signals/riskPolicy.ts` — `evaluateSignalRisk` | Identified deterministic per-portfolio order/exposure/drawdown checks as an independent host boundary | Exercise real host constraints against submitted policies; do not credit free-text promises |
| Experiment wrappers | Generic JSON stdin/stdout runner with stage history | Supply actual Lean reasoner/RLT/HRM/CGRT entry points and checkpoint hashes |

The projection preserves tlUSD atom strings and basis-point limits; it performs
no unsupported conversion from token atoms to cash. It omits owner account data
from the review packet. It does not verify native hashes, approve execution,
sign, broadcast or prove the risk assumptions. Those remain responsibilities of
the native deterministic host and wallet boundary.

Suggested preregistered hypotheses:

1. A self-critique pass improves evidence-linked revisions over a matched
   no-critique arm at a fixed external resource budget.
2. Architecture critique detects shared-checker/shared-oracle failures missed by
   a strategy-only critic; reward a concrete discriminating test, not extra prose.
3. Population reasoning transfers to changed counterparties and capacity
   assumptions, including fixed-capital negative controls.
4. Additional recurrence/internal steps help only if numerical, reasoning and
   constraint gains persist under measured compute and paired cases.

Next implementation milestones:

1. Register actual adapters, checkpoints, tokenizer and recurrence controls;
   freeze case/packet digests, budget envelopes and seeds. No acronym expansion
   or theorem-prover guarantee is inferred from an experiment label.
2. Run the public development cases, all four benign controls and numerical
   tasks. Collect paired ablations and two blind human reviews per historical
   case. Attach independently measured resource receipts.
3. Add matched historical non-crisis windows, authenticated availability
   timestamps and licensed prices/order books where numerical backtests are
   intended. Retain event-family grouping and source revision history.
4. Author protected mechanism-changing counterfactuals and isolated inference
   inputs. Connected Terra/Celsius/3AC/FTX cases must stay in one episode-family
   split. The released public cards are development diagnostics.
5. Wire constrained model policies into a richer simulator with separate
   synchronization, liquidity, concentration, funding and settlement controls;
   add passive counterparties, transfer accounting and intervention utility.

The present runner can collect and compare responses today, while these study
milestones stay explicit. It does not claim completed empirical model rankings.
