# ADR-013: Bellman-Ford and Johnson — declined

**Status:** Decided — **declined**
**Date:** 2026-08-17
**Deciders:** RicheyWorks
**Resolves:** ADR-001 appendix item 4 ("Bellman-Ford and Johnson — Ch. 24,
Ch. 25")

## Question

Real latency graphs are asymmetric and can carry negative edges. Bellman-Ford
handles negatives; Johnson reweights them so Dijkstra can run all-pairs on a
sparse directed graph — the honest `DistanceOracle` for topologies too large
for a V² table. Should either land now?

## What the product actually has

Weights are **costs**, not signed latencies.

- The API hotspot domain is `[1.0, 1000.0]` (`Hotspot`, `TrafficService`,
  living-maze drift). There is no request that can introduce a negative edge.
- `WeightedMazeGrid.setWeight` rejects NaN, infinity, and anything `< 0`.
  Zero is legal in core and unused by the API.
- Every current solver treats the grid as undirected: `d(u,v)` is the entry
  cost of `v`, and the reverse hop is the entry cost of `u`. That is
  already a weak asymmetry, and it is still non-negative.

Bellman-Ford on a graph with no negative edges is Dijkstra with a worse
bound: O(VE) instead of O(E + V log V), and no extra correctness. Shipping
it would be a second shortest-path implementation whose only distinguishing
input cannot be constructed.

Johnson without negatives is identity reweighting, then n Dijkstras.
`DistanceOracle` already does n BFS for the hop-count table and is
**dormant** because a heat map is cheaper as one BFS from the goal
(measured, left unused on purpose). n Dijkstra would be strictly slower
than that unused path.

## Decision

**Decline.** The appendix item asked for algorithms that assume a graph
shape the product refuses to admit. The named trigger is a directed
latency graph with negatives or genuine asymmetry that is not "the cell
you enter". Until that graph exists, Bellman-Ford and Johnson have
nothing to do.

This is the same honesty as ADR-011: do not ship the textbook improvement
for a quantity that is not present.

## Re-fire

Re-open, do not assume, if any of these become true:

- a consumer supplies a directed graph whose reverse hop is not the
  opposite cell's entry cost (WAN / peering latency)
- negative edges are admitted — refunds, incentives, or a signed
  residual — and `WeightedMazeGrid` stops rejecting them
- all-pairs on that graph is measured slower than the product can
  tolerate, *and* the graph is sparse enough that Johnson beats a
  dense table

Until then the appendix item is closed.
