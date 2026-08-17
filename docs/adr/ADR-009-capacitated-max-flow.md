# ADR-009: Capacitated max-flow — bisection bandwidth without breaking the unit cut

**Status:** Accepted
**Date:** 2026-08-17
**Deciders:** RicheyWorks
**Extends:** ADR-001 appendix item 2. Does not change the product analysis endpoint.

## Context

ADR-001's appendix listed max-flow with real capacities as the next topology primitive
after k-center. `MazeFlow` already ran Edmonds-Karp; every passage was capacity 1, so
`cutSize` was edge connectivity — "how many links to sever". A capacity planner wants
the other reading: how much bandwidth those links carry.

The unit reading is load-bearing. `GET /analysis` and the web UI treat `cutSize` as a
chokepoint *count* ("1 chokepoint"). Changing the default would make a fat uplink look
like four chokepoints. Weights cannot be reused as capacities either: `WeightedMazeGrid`
is latency (cost in `g`); capacity is throughput. Conflating them would make an expensive
cell look like a fat pipe.

Hilbert's live descriptor had the same shape of leftover: the vision table was corrected
in 2026-07-19, `GET /algorithms` still said "best locality of any curve generator".

## Decision

Add `MazeFlow.PassageCapacity` and `minCut(grid, source, sink, capacity)`. The no-arg
overloads stay unit-capacity and keep `cutEdges.size() == cutSize`. Under a real
capacity function, `cutSize` is the flow (bisection bandwidth) and may exceed the
number of cut passages.

Edmonds-Karp pushes the bottleneck of each augmenting path, not one unit per BFS. On
`UNIT` the bottleneck is always 1, so existing cuts are unchanged.

The analysis endpoint stays on the unit overload. A maze has no capacity source of its
own; inventing one would be authorization theater in reverse — a number that looks
like bandwidth and is just a recount of the passages.

## Consequences

- Topology lab reports `uniformCapacity2` next to edge connectivity, so the two readings
  sit side by side.
- Hilbert's descriptor and javadoc match the measured stretch table. The diameter test
  fails if someone carves along the curve (Hamiltonian path) or if the tree ever beats
  Prim's at the same seed — either of those would make the old claim true, and the
  descriptor would have to change with the test.
- ADR-001 appendix item 3 shipped as [ADR-010](ADR-010-bipartite-matching.md) — the
  primitive does not need the LoadBalancerPro seam. Items 4–5 stay held:
  Bellman-Ford/Johnson wait on a directed latency graph that is not a maze;
  incremental SSSP is still "measure first".
