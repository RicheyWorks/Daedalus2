<!-- Paste-ready GitHub issue for the LoadBalancerPro tracker.
     TITLE (copy into the title field):
     Open `RoutingStrategyId` for externally-contributed strategies
     BODY below the line. Source of truth: docs/upstream-requests-loadbalancerpro.md
     (this file is a verbatim extraction; if they diverge, the source wins). -->

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
