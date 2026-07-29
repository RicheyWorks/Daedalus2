<!-- Paste-ready GitHub issue for the LoadBalancerPro tracker.
     TITLE (copy into the title field):
     Give `RoutingStrategy` an optional stateful form
     BODY below the line. Source of truth: docs/upstream-requests-loadbalancerpro.md
     (this file is a verbatim extraction; if they diverge, the source wins). -->

**Problem.** `choose(List<ServerStateVector> servers)` hands the strategy a **fresh list on every
call**. That obliges every strategy to be stateless and at least O(n) per decision, and it makes
incremental data structures impossible — anything that would amortise work across calls has to be
rebuilt from scratch each time.

**This is measured, not theoretical.** Daedalus evaluated backing a tail-latency strategy with an
order-statistic tree (CSRBT's `RankedSet`, which offers O(log n) `select`/`rank`/`percentile`).
Full write-up in `docs/adr/ADR-002-csrbt-rankedset-for-routing.md`. The result, on a simulated
64-server fleet using the real `ServerStateVector` and `ServerScoreCalculator`:

| | ns per decision |
|---|---|
| shipped uniform power-of-two | 46–185 |
| the same policy with a tree rebuilt per call | 5 870–9 131 |

**30×–125× more expensive**, entirely because the tree must be rebuilt. The tree's whole advantage
is incremental maintenance, and the signature denies it.

**Suggested change.** Keep `choose(List)` as-is and add an opt-in interface:

```java
interface StatefulRoutingStrategy extends RoutingStrategy {
    void onServerState(ServerStateVector updated);  // called when a server's metrics change
    RoutingDecision choose();                       // no list — the strategy holds its own view
}
```

The engine can check `instanceof` and use the stateful path when available. Nothing existing
changes.

**Honest caveat, so this is not oversold.** The same evaluation found that the *policy* the tree
would enable — gating to the best quantile — is **worse than what ships today** under realistic
conditions: 29% worse mean latency and 17% worse p99 once the balancer's view of the fleet is even
slightly stale, because concentrating the sample pool on whatever looked best last snapshot causes
herding. This request is about removing an architectural ceiling, **not** about adopting that
policy. Daedalus is not asking for this in order to ship the thing it measured and rejected.

**If declined.** Strategy cost stays O(n) per decision, and fleet size becomes the component's
scaling ceiling. That may well be the right trade for the fleet sizes in scope — it is a
deliberate choice either way, which is the point of raising it.
