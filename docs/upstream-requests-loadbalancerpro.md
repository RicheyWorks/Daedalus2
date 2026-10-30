# Upstream requests against LoadBalancerPro

Three API changes Daedalus needs from LoadBalancerPro, resolving **ADR-001 action item 6**.
Each is written to be pasted into the LoadBalancerPro issue tracker as-is.

They are ordered by how much they unblock: (1) and (2) block integration outright, (3) is what
makes a whole class of optimisation possible and came out of a measurement rather than a guess.

Nothing here requires Daedalus to change. Each request states the workaround if it is declined.

---

## Issue 1 — Open `RoutingStrategyId` for externally-contributed strategies

**Problem.** `RoutingStrategyId` is a closed enum:

```java
public enum RoutingStrategyId {
    TAIL_LATENCY_POWER_OF_TWO, WEIGHTED_LEAST_LOAD,
    WEIGHTED_LEAST_CONNECTIONS, WEIGHTED_ROUND_ROBIN, ROUND_ROBIN;
}
```

`RoutingStrategy.id()` returns it, so **no external project can implement `RoutingStrategy`
without patching this enum**. Daedalus can generate topologies and compute routes, but cannot
present the result as a strategy LoadBalancerPro will accept.

**Suggested change.** Keep the enum for the built-ins and let the interface carry a wider type —
e.g. `id()` returns a `String` (or a small `StrategyId` value type wrapping one), with the enum
providing the canonical names. `fromName` already normalises hyphens and case, so string handling
is largely in place.

**Compatibility.** Existing switches over the enum keep working if the enum stays; only the
`RoutingStrategy.id()` return type widens.

**If declined.** External strategies stay impossible and Daedalus can only supply routing
*advice* out-of-band, not a pluggable strategy. Worth saying explicitly in the README so nobody
else attempts it.

---

## Issue 2 — Add `topologyNodeId` to `ServerStateVector`

**Problem.** `ServerStateVector` describes a server (`serverId`, in-flight count, weight, p95/p99
latency, error rate) but carries **no notion of where that server sits in a topology**. Daedalus
reasons about graphs whose nodes are servers; without a join key, there is nothing to map a graph
node onto a `ServerStateVector` and back.

**Suggested change.** Add an optional field, e.g. `Optional<String> topologyNodeId` (or a plain
nullable `String`), defaulted so existing constructors keep compiling. It needs no meaning inside
LoadBalancerPro — it is an opaque handle owned by whatever produced the topology.

**Why not reuse `serverId`.** They are different identities. `serverId` names a *process*;
`topologyNodeId` names a *position*. A server can be replaced without moving, and a node can be
re-homed without the server changing. Conflating them breaks as soon as either happens.

**If declined.** Callers must maintain an external `Map<String, String>` alongside every routing
call, which is exactly the kind of side-table that goes stale silently.

---

## Issue 3 — Give `RoutingStrategy` an optional stateful form

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
