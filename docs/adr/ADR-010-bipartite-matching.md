# ADR-010: Bipartite b-matching — assign a batch, do not walk a path

**Status:** Accepted
**Date:** 2026-08-17
**Deciders:** RicheyWorks
**Extends:** ADR-001 appendix item 3. Does not add a REST endpoint.

## Context

ADR-001's appendix listed bipartite matching as the next topology primitive after
capacitated max-flow. A* answers "which route"; a load balancer answers "which
server". Those are different questions. Assigning a batch of requests to servers
under per-server capacity is bipartite b-matching, and it is the principled form
of least-connections when you place many requests at once.

The LoadBalancerPro `RoutingStrategy` seam that would host this as a live policy
is still closed (#527). That blocks *integration*, not the algorithm. k-center
and capacitated flow shipped the same way: a core primitive the topology example
can run today, with no pretence that a request is being routed.

Greedy first-fit is the tempting substitute and is wrong. A request that can use
either of two servers will take the only server the next request can use. Max-flow
reassigns. The test that pins this class is written against that fixture, and
compares the result to an in-test first-fit so a rewrite to greedy fails it.

## Decision

Add `BipartiteMatching` in `daedalus-core`. The reduction is the textbook one:
source → request (cap 1), request → eligible server (cap 1), server → sink
(cap = that server's capacity). Edmonds-Karp; BFS follows increasing index, so
the assignment is deterministic.

The maze reading `assignToFacilities` uses hop distance for eligibility — a
request may use a replica only when a route of at most `maxHops` exists. That
composes with `FacilityPlacement` without inventing a new distance.

No REST surface. A maze has no batch of incoming requests; inventing one would
be a number that looks like load-balancing and is just a recount of cells.

## Consequences

- Topology lab section 4 assigns a 4×4 lattice of request sites onto the k-center
  replicas and shows capacity 1 leaving requests unmatched, capacity 4 filling
  every seat.
- ADR-001 appendix item 5 shipped as a decline — [ADR-011](ADR-011-incremental-sssp.md).
  Item 4 stays held: Bellman-Ford/Johnson wait on a directed latency graph that is
  not a maze (current weights are costs ≥ 1, so there is no negative edge to
  justify Bellman-Ford).
