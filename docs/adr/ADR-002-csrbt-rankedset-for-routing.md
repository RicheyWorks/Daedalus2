# ADR-002 — CSRBT `RankedSet` behind `TailLatencyPowerOfTwoStrategy`

**Status:** Decided — **declined**, with a follow-up request against LoadBalancerPro
**Date:** 2026-07-19
**Resolves:** ADR-001 action item 7 ("evaluate CSRBT `RankedSet` behind
`TailLatencyPowerOfTwoStrategy` — measure before adopting, per this ecosystem's habit")

---

## Question

CSRBT's `RankedSet<K>` offers order statistics — `select(i)`, `rank(k)`, `percentile(pct)`,
`rangeCount(lo, hi)` — in O(log n). LoadBalancerPro routes with
`TailLatencyPowerOfTwoStrategy`. The obvious-sounding move is to put the tree behind the
strategy so it can reason about where a server sits in the fleet's latency distribution rather
than looking at two servers in isolation.

Should we?

## What the strategy actually does today

Reading it first turned out to matter, because it changes the question.

```java
List<ServerStateVector> eligible = servers.stream().filter(...healthy...).toList();  // O(n)
List<ServerStateVector> candidates = sampleCandidates(eligible);                     // exactly 2
ServerStateVector chosen = min(candidates, by score);                                // O(1)
```

**There is no order statistic anywhere in it.** Power-of-two-choices samples two servers
uniformly at random and takes the better one. The only O(n) step is a boolean health filter,
which a ranked structure cannot help with. `ServerStateVector` already carries
`p95LatencyMillis` and `p99LatencyMillis` per server, so per-server percentiles are free
too — the tree would only add *cross-fleet* ranking, which the algorithm never asks for.

So adopting `RankedSet` cannot be a drop-in optimisation. It necessarily means **changing the
policy** to something that consumes a rank — the natural candidate being "gate to the best
_q_% of the fleet by score, then power-of-two inside that pool". That is what was measured.

## Method

A discrete-event fleet simulation, using the **real** classes from both ecosystems rather than
stand-ins: `ServerStateVector` and `ServerScoreCalculator` from LoadBalancerPro 2.4.2, and
`OrderedSet` + `RedBlackStrategy` from csrbt-core 0.1.0.

- 64 heterogeneous servers (capacity 4–32), 40 000 requests, one arrival per tick.
- A request occupies its server for a service time inversely proportional to capacity; the
  latency it observes also pays for whatever was already in flight there.
- Offered load set so the fleet runs with genuine contention rather than an idle queue.
- First 2 000 requests discarded as warm-up. Latency figures are deterministic and reproduced
  exactly across runs; `ns/decision` carries normal JIT noise.

**The variable that decides the whole question is view staleness.** A real balancer routes on
a picture that is already out of date — metrics are scraped on an interval, and multiple
balancer replicas act on the same stale snapshot. That delay is the entire reason
power-of-two-choices exists. A benchmark that hands the strategy a perfectly fresh view is
measuring a system nobody runs, and it will flatter greedy selection. So staleness is swept.

Four strategies:

| | policy | selection cost |
|---|---|---|
| `uniform po2` | the shipped strategy | O(n) health filter |
| `greedy` | always the lowest score | O(n) |
| `RankedSet-gated po2` | best 20% by score, then po2 inside | build tree + `percentile(20)` |
| `quickselect-gated po2` | **same policy**, threshold via Hoare partial select | O(n) average |

The fourth exists to separate two claims that are easy to conflate: *is gating a better
policy* and *is a tree the right way to compute the gate*.

## Results

**Fresh view — refreshed every request (unrealistic):**

| strategy | mean ms | p99 ms | max in-flight | ns/decision |
|---|---|---|---|---|
| uniform po2 (shipped) | 5.54 | 14.35 | 4 | 185 |
| greedy least-score | 4.21 | 6.15 | 2 | 315 |
| **RankedSet-gated po2** | **3.66** | **5.55** | 2 | 9 131 |
| quickselect-gated po2 | 3.82 | 6.15 | 2 | 1 002 |

**Stale view — refreshed every 25 requests (realistic):**

| strategy | mean ms | p99 ms | max in-flight | ns/decision |
|---|---|---|---|---|
| **uniform po2 (shipped)** | **6.03** | **19.13** | **5** | **48** |
| greedy least-score | 33.77 | 52.77 | 19 | 200 |
| RankedSet-gated po2 | 7.86 | 22.32 | 13 | 5 870 |
| quickselect-gated po2 | 7.78 | 21.52 | 10 | 417 |

**Very stale view — refreshed every 100 requests:**

| strategy | mean ms | p99 ms | max in-flight | ns/decision |
|---|---|---|---|---|
| **uniform po2 (shipped)** | **6.25** | **19.13** | **5** | **46** |
| greedy least-score | 54.68 | 204.47 | 19 | 210 |
| RankedSet-gated po2 | 9.22 | 24.11 | 10 | 5 844 |
| quickselect-gated po2 | 9.24 | 24.11 | 10 | 368 |

## Decision — decline

Three independent reasons, any one of which is sufficient.

**1. The policy change makes routing worse under the conditions that actually hold.** Gating to
the best quantile beats uniform sampling only when the view is perfectly fresh. At realistic
staleness it is **29% worse on mean latency and 17% worse at p99**, and its peak in-flight
count doubles (10–13 against 5) — the signature of herding. Concentrating the sample pool on
whichever servers *looked* best in the last snapshot sends everyone to the same place, which
is exactly the failure mode uniform sampling is designed to avoid. Greedy selection, the
limiting case of the same idea, degrades catastrophically: **9× mean and 10× p99**.

**2. Where gating did win, the tree was not the reason.** Quickselect matched it — 3.82 vs 3.66
mean on a fresh view, and identical p99 (24.11) once stale — at **1/9th to 1/16th the cost**.
The gain, such as it is, comes from the policy, and the cheap O(n) selection captures it. There
is no measured benefit attributable to the order-statistic tree.

**3. The interface forecloses the tree's actual advantage.** `RoutingStrategy.choose` takes
`List<ServerStateVector>` — a **fresh list on every call**. An order-statistic tree earns its
keep through *incremental maintenance*: O(log n) per update, amortised over many queries.
Handed a new list each time, it must be rebuilt from scratch, so every call pays O(n log n)
plus per-node allocation and CSRBT's per-operation read lock, against the O(n) scan it is
replacing. Measured: **5.8–9.1 µs per decision versus 46–185 ns for the shipped strategy — 30×
to 125× more expensive**, on the per-request hot path.

Reason 3 is the important one, and it is **not a criticism of CSRBT**. The tree is doing what
it is designed to do; the call shape simply denies it the only regime where it wins. No
order-statistic structure — CSRBT's or anyone else's — can pay for itself behind this
signature.

## What would change the answer

The evaluation produces a concrete API request, which is added to ADR-001 item 6:

> **Request 3 — give `RoutingStrategy` an optional stateful form.** Alongside
> `choose(List<ServerStateVector>)`, expose a lifecycle a strategy can use to maintain
> its own index:
>
> ```java
> interface StatefulRoutingStrategy extends RoutingStrategy {
>     void onServerState(ServerStateVector updated);   // called when a server's metrics change
>     RoutingDecision choose();                        // no list — the strategy holds its own view
> }
> ```
>
> This is what makes incremental structures viable at all. Without it, every strategy is
> obliged to be stateless and O(n) per decision, and the fleet size at which that stops being
> acceptable is the ceiling on the whole component.

Even with that interface, note that finding 1 stands on its own: **quantile gating is a worse
policy than uniform sampling under stale state**, regardless of how cheaply the quantile is
computed. A stateful interface would make the tree affordable; it would not make the policy
correct. Any future revisit should re-measure the policy question first, and only then ask what
data structure serves it.

## Reproducing

The harness is committed at `docs/evaluations/CsrbtRoutingEval.java`. It is deliberately not
part of the Maven reactor — it needs jars from two sibling projects, so wiring it into the
build would couple this repo's CI to their local state. Run it directly:

```bash
# from a scratch directory
unzip -q /path/to/LoadBalancerPro/target/LoadBalancerPro-2.4.2.jar 'BOOT-INF/classes/*' -d lbpc
mv lbpc/BOOT-INF/classes/* lbpc/
cp /path/to/CSRBT/csrbt-core/build/libs/csrbt-core-0.1.0.jar csrbt.jar
# csrbt-core needs a log4j2 API on the classpath
javac -cp "lbpc:csrbt.jar" -d . CsrbtRoutingEval.java
java  -cp "lbpc:csrbt.jar:log4j-api.jar:." CsrbtRoutingEval
```

Latency columns are deterministic and should reproduce exactly; `ns/decision` will vary.
