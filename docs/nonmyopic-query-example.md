# Choosing which risk report to request

**Status:** L1 public development example. This document specifies an exact
sanity test for planning information queries. Its outcomes are derived from the
eight stipulated worlds below. Model performance remains unmeasured.

## Funding and settlement setup

An agent must decide whether to proceed with a transfer or pause it and keep
liquidity in reserve. One of two conditions determines whether proceeding is
appropriate during the stated horizon. A regime report identifies the binding
condition; the agent can also request separate reports about funding and
settlement.

The hidden world consists of three independent, uniformly distributed bits:

| Bit | Report | Meaning |
| --- | --- | --- |
| A | Binding regime | `0`: the funding condition determines the required action; `1`: the settlement condition determines it. |
| B | Funding condition | `0`: clear; `1`: blocked. This condition determines the action when `A = 0`. |
| C | Settlement condition | `0`: clear; `1`: blocked. This condition determines the action when `A = 1`. |

All eight combinations have mass `1/8`. The agent receives this prior, the
report definitions and the action rule. It can request any previously unread
report for a fee of **1** currency unit, with a maximum of **two reports**.
Reports return their bit exactly. The next request may depend on an earlier
answer, and the agent may stop before using its whole allowance.

Let action `0` mean proceed and action `1` mean pause. The required action is

$$
T(A,B,C)=
\begin{cases}
B & A=0,\\
C & A=1.
\end{cases}
$$

A correct action has decision loss `0`. A wrong action has decision loss
`20`: proceeding through the binding obstacle incurs a stipulated failed
transfer loss, while pausing a clear transfer forfeits contract value of the
same amount. This symmetric loss makes a blanket pause costly. These amounts
define the example's objective within a single currency and horizon.

For a policy `pi`, let `N_pi(w)` count the reports it requests in world `w` and
let `a_pi(w)` be its final action. Its expected total cost is

$$
J(\pi)=\frac{1}{8}\sum_{w\in\{0,1\}^3}
\left(20\,\mathbf{1}\{a_\pi(w)\ne T(w)\}+N_\pi(w)\right).
$$

The budget requires `N_pi(w) <= 2` on every reachable branch. Fees enter the
objective once per requested report.

## World table

| A | B | C | Required action T | Binding report after reading A |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | B |
| 0 | 0 | 1 | 0 | B |
| 0 | 1 | 0 | 1 | B |
| 0 | 1 | 1 | 1 | B |
| 1 | 0 | 0 | 0 | C |
| 1 | 0 | 1 | 1 | C |
| 1 | 1 | 0 | 0 | C |
| 1 | 1 | 1 | 1 | C |

## Cost without queries and the information bound

Each final action is correct in four worlds. Acting immediately therefore has
expected cost `20 * 4/8 = 10`. Randomizing the action leaves that expectation
unchanged.

A comparator given all hidden bits for free selects `T` in every world and
has cost **0**. That comparator defines the perfect-information lower bound.
The agent's feasible comparator must pay for reports and obey the query
budget.

## Why the regime report has zero immediate decision value

After observing `A = 0`, the unknown funding bit is still uniform. Observing
`A = 1` leaves the relevant settlement bit uniform. Either branch has a
minimum expected decision loss of `10` if the agent acts immediately.

Reading A therefore reduces immediate expected decision loss by **0**. Its
fee raises total cost to `11` when no further report is requested. The report
becomes useful by identifying which subsequent observation matters.

Reading B alone has a different effect. Conditional on its value `b`, the
required action equals `b` with probability `3/4`: the funding regime has
probability `1/2`, and the settlement regime contributes another `1/4` when C
happens to equal `b`. Choosing action B has expected decision loss
`20 * 1/4 = 5`. Including its fee gives **6**. The same calculation applies
to reading C alone.

A greedy policy that measures each query by its immediate reduction in
expected decision loss, net of its fee, chooses B or C. Their immediate net
benefit is `4`; A's is `-1`.

## Why the greedy policy stops at cost 6

Suppose the first report was B. Its answer leaves expected decision loss `5`.
Reading A as the second report would resolve the funding-regime branch. The
settlement-regime branch would still have an unknown C, producing expected
decision loss `10` in that branch. Averaging gives

$$
\tfrac12\cdot0+\tfrac12\cdot10=5.
$$

Reading C instead has the same expected value. When B and C agree, the action
is known; when they differ, A remains unknown. Those events each have
probability `1/2`, so the expected decision loss is again `5`.

Neither possible second report lowers expected decision loss after a first
query of B. Paying for one would raise total expected cost from `6` to `7`.
The greedy policy stops after its first report at cost **6**. Starting with C
gives the same result by symmetry.

## The optimal policy under the two-query budget

Request A first. If its answer is `0`, request B; otherwise request C. Return
the second answer as the action.

```python
regime = observe("A")
condition = observe("B" if regime == 0 else "C")
return condition
```

This policy selects the correct action in all eight worlds. It spends two
units on reports and has expected total cost **2**.

Optimality follows by enumerating the possible first decisions. Stopping
immediately costs `10`. A first query of B or C has best achievable cost `6`,
as derived above. A first query of A permits the cost-2 policy. Its relevant
second query removes all decision loss; stopping after A costs `11`, while
querying the irrelevant condition costs `12`. A randomized first choice
forms a weighted average of these costs and cannot improve on `2`.

| Policy or comparator | Expected decision loss | Expected query fees | Expected total cost |
| --- | ---: | ---: | ---: |
| Free perfect information | 0 | 0 | 0 |
| Best action without a query | 10 | 0 | 10 |
| Query A, then act immediately | 10 | 1 | 11 |
| Greedy immediate-value query policy | 5 | 1 | 6 |
| Optimal adaptive policy with budget 2 | 0 | 2 | 2 |

With a query budget of zero, the feasible optimum is `10`. Allowing one
query reduces it to `6`; allowing two reduces it to `2`.

The greedy policy's regret relative to the feasible optimum is `6 - 2 = 4`.
The feasible optimum's gap to the perfect-information bound is `2`, entirely
due to report fees in this example. Keeping those quantities separate lets
the evaluator identify the cost of a planning error.

## Development checks and extension

An exact evaluator can enumerate policy trees or use dynamic programming over
the worlds consistent with the query history. A submitted tree passes this
example when every branch respects the budget and the exact expected total
cost is `2`. Evaluation should replay all eight worlds, including branches
that a single sampled interaction would leave unexplored.

Tests should check the zero-, one- and two-query optima above, retain query
fees in both policies and comparators, and reject requests beyond the budget.
Renaming reports or swapping the bit labels should preserve the underlying
decision problem after the corresponding transformation of the rule.

The reusable skill is choosing an observation for the future queries it
enables. A larger task can compose selectors recursively so that an early
report identifies a relevant subgraph of funding and settlement dependencies.
Learning that composition from sparse demonstrations, then producing a valid
policy under a measured resource budget, supplies a further task to calibrate.

This supplied selector rule is a public L1 sanity test. Difficulty on a
frontier-oriented suite requires measured results on a frozen collection of
held-out tasks. All relabelings and numerical variants from this generator
belong to one source group. They add regression coverage while the count of
independent candidate groups stays at one.
