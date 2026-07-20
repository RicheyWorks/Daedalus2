# ADR-001: Make Daedalus a Graph Engine, Not a Maze Engine

**Status:** Proposed
**Date:** 2026-07-19
**Deciders:** Richmond (RicheyWorks)
**Consumers in scope:** CSRBT, LoadBalancerPro, future embedders

---

## Context

`Vision/daedalus-vision-document.md` states the thesis plainly: Daedalus is "not a maze
game", it is "a general-purpose network topology and intelligent routing engine", with
load balancing as the highest-priority use case. The code does not yet match that claim,
and the gap is structural rather than cosmetic.

The requirement is that Daedalus be consumable in **four modes at once** — embedded jar,
network service, plugin host, and live routing data plane. Those four pull in different
directions, and only one seam satisfies all of them.

### What the code actually says

This ADR is written after reading the consumer repositories, not from the vision docs.
Five findings drive everything below.

**1. The core is grid-shaped, not graph-shaped.**
`MazeGrid` hardcodes 4-neighbour adjacency over a dense rectangle; `Point(row, col)` is
the node identity; `openNeighbors` is the adjacency function. Every solver and every
`theory` class is written against that. A data-centre topology is none of those things:
arbitrary degree, arbitrary node identity, no rectangle.

**2. LoadBalancerPro's routing seam is *selection*, not *routing*.**

```java
public interface RoutingStrategy {
    RoutingStrategyId id();
    RoutingDecision choose(List<ServerStateVector> servers);
}
```

It receives a **flat list of candidate servers** and returns **one of them**. There is no
graph, no source node, no destination, no hops. All five shipped strategies
(`RoundRobin`, `WeightedLeastLoad`, `WeightedLeastConnections`, `WeightedRoundRobin`,
`TailLatencyPowerOfTwo`) are selection policies over a set.

This makes the vision document's central claim — "use A\*, Bidirectional, or Dead-End
Filling solvers as advanced load balancing strategies (far smarter than round-robin)" — a
**category error as stated**. A\* answers *"what is the best path from A to B?"*.
`choose` asks *"which of these N endpoints should serve this request?"*. You cannot drop a
pathfinder into a selector: there is no graph to search and no destination to search
toward. Pretending otherwise would produce an adapter that fabricates a topology per
request and returns the first hop of a route nobody asked for.

**3. `RoutingStrategyId` is a closed enum.** Five constants. A Daedalus-backed strategy
cannot even be *named* without editing LoadBalancerPro. The seam is pluggable in shape but
sealed in practice — unlike Daedalus's own `GeneratorRegistry`/`SolverRegistry` or CSRBT's
`TreeStrategy`, both of which are open interfaces with runtime registration.

**4. `ServerStateVector` has no topology coordinate.** It carries `serverId`, health,
in-flight count, capacity, weight, `averageLatencyMillis`, `p95LatencyMillis`,
`p99LatencyMillis`, error rate, queue depth, network-awareness and latency-window signals.
Rich telemetry — but nothing that says *where a server sits in a topology*. Any
topology-aware decision needs that field or a side index.

**5. The published integration guide contains a correctness bug.**
`Vision/02-LoadBalancer-Integration-Guide.md` recommends `HilbertLoadBalancer`, whose
`dynamicHeuristic` folds node load into A\*'s **heuristic**:

```java
return distance + (load * 2.0);   // h(n) is no longer a lower bound
```

A\* is optimal only when `h` never over-estimates the true remaining cost. Adding load to
`h` destroys admissibility, so A\* silently starts returning non-optimal routes — the
failure is invisible because it still returns *a* path. Load is a property of traversal
and belongs in the edge **cost** (`g`), which `WeightedMazeGrid` already models correctly.
The way to make `h` *better* rather than *wrong* is a tighter admissible bound —
`LandmarkHeuristic` (ALT), which measured 55% fewer expansions than Manhattan. This guide
should be corrected before anyone builds on it.

### What CSRBT is, and why it is a different shape

CSRBT is a **Composable Self-Balancing Tree Engine**: `OrderedSet<K>` over pluggable
`TreeStrategy` implementations (Red-Black, AVL, Splay, Hybrid, weight-balanced,
B+tree), morphing at runtime behind a health gate, with a control plane
(`WorkloadMonitor`, `StrategyScorer`, `StrategyMorphTarget`) that picks strategies from
observed workload.

It is **not** a graph engine and Daedalus should not try to consume it as one. The genuine
overlap is `RankedSet<K>` — `select(rank)`, `rank(key)`, `percentile(pct)`, `median()`,
`countInRange`, `rangeQuery` in O(log n). Those are precisely the primitives a load
balancer needs over live telemetry, and `ServerStateVector` already carries
`p95LatencyMillis` / `p99LatencyMillis` as *precomputed scalars*. The three projects are
complementary brains, not layers:

| Project | Owns | Primitive |
|---|---|---|
| **CSRBT** | ordered state, adaptively indexed | `select` / `rank` / `percentile` |
| **Daedalus** | topology and traversal | generate / route / measure |
| **LoadBalancerPro** | the live decision and its evidence | `choose(...)` |

The `AlgorithmConfig` comment ("mirrors the CSRBT pattern of swappable algorithms") is
already an acknowledgement that all three share one architectural idea: **an open strategy
registry plus a control plane that selects among strategies**. That shared pattern, not a
shared data structure, is the real ecosystem tie.

---

## Decision

Introduce a **`Graph` SPI in `daedalus-core`** as the single seam all four consumption
modes are built on, and be explicit about which load-balancing questions Daedalus can
actually answer today.

Concretely:

1. **`com.daedalus.graph.Graph`** — nodes as dense `int` ids, `degree(v)`, `neighbor(v,i)`,
   `weight(u,v)`, `nodeCount()`. `MazeGrid` gets a `Graph` view; solvers and `theory`
   classes are retargeted at `Graph`. **The D2 refactor already did the hard half of this**
   — solver state moved onto `row * cols + col` integer ids behind `GridIndex`, so the
   internals are already node-id-shaped rather than `Point`-shaped.

2. **Keep `daedalus-core` framework-free.** Service mode (`daedalus-server`) and plugin
   mode (`daedalus-plugin-runtime`) become thin adapters over the same SPI. This is
   already true and must survive the refactor — it is what makes embedded mode possible
   at all.

3. **Integrate with LoadBalancerPro where the shapes genuinely match**, and do not force
   the mismatch. Three integrations are real today; one is not:

   | Integration | Shape | Status |
   |---|---|---|
   | Topology generation for `lab/` experiments | offline, batch | **Ready now** — no interface change |
   | Capacity analysis (min-cut = bisection bandwidth) | offline, batch | **Ready now** — `MazeFlow` exists |
   | Placement (which racks/AZs host replicas) | offline, batch | Needs k-center (below) |
   | Per-request `RoutingStrategy` | online, selection | **Blocked** — see below |

4. **Unblock per-request integration properly**, by asking LoadBalancerPro for two
   changes rather than smuggling a pathfinder into a selector:
   - open `RoutingStrategyId` (string id + registry, as CSRBT and Daedalus both do), and
   - add an optional `topologyNodeId` to `ServerStateVector`.

   With those, a genuinely topology-aware *selection* strategy becomes expressible:
   "among healthy servers, choose the one minimising `α · distance(ingress, server) +
   β · load`", where `distance` is an O(1) `DistanceOracle` lookup. That is a selection
   policy informed by topology — the correct shape — not a path search wearing a costume.

---

## Options Considered

### Option A — Adapter-only (status quo, what the guide does)

Consumers depend on `daedalus-core` and treat `MazeGrid` as a topology, `Point` as a node.

| Dimension | Assessment |
|---|---|
| Complexity | Low |
| Cost | Near zero now, compounding later |
| Scalability | Poor — grid-only, dense rectangle |
| Team familiarity | Highest (it is today's code) |

**Pros:** nothing to build; works for the lab's grid-shaped experiments.
**Cons:** every consumer re-implements the same adapter; topologies are forced into a
rectangle; node identity is a `(row, col)` pair that means nothing to a service mesh; the
mismatch is pushed onto every consumer forever.

### Option B — Extract a `Graph` SPI, keep `MazeGrid` as one implementation (recommended)

| Dimension | Assessment |
|---|---|
| Complexity | Medium — touches 10 solvers + `theory` |
| Cost | One focused refactor, well-fenced by tests |
| Scalability | Good — arbitrary graphs, arbitrary degree |
| Team familiarity | High — mirrors the existing registry/SPI idiom |

**Pros:** one seam serves all four modes; consumers bring their own graph; mazes become a
*use case* of the engine rather than its identity, which is exactly the vision's claim;
D2 already moved the internals to integer node ids.
**Cons:** a real refactor with real regression risk; `weightOf(Point)` must generalise to
edge weights; some maze-specific optimisations (the `boolean[][] visited` layer) do not
survive generalisation unchanged.

### Option C — Rewrite core against an existing graph library (JGraphT et al.)

| Dimension | Assessment |
|---|---|
| Complexity | High |
| Cost | High, plus a permanent dependency |
| Scalability | Good |
| Team familiarity | Low |

**Pros:** free breadth of algorithms; someone else maintains the graph plumbing.
**Cons:** **breaks the single most valuable property of this codebase** — `daedalus-core`
has zero framework dependencies, which is what makes it embeddable in CSRBT,
LoadBalancerPro and a JavaFX desktop app alike. It also discards the hand-tuned,
measured work (D2's 1.42–1.72×, ALT's 55%) in favour of generic implementations. Rejected.

---

## Trade-off Analysis

The decisive axis is **who absorbs the impedance mismatch**. Option A pushes it onto every
consumer, permanently and repeatedly. Option C absorbs it by importing someone else's
model and losing the zero-dependency property. Option B absorbs it once, inside the engine,
which is the only place it can be paid for a single time.

The refactor risk in Option B is real but unusually well-fenced: the suite already pins
cross-implementation agreement (`dial` equals `dijkstra`, A\* matches BFS, `LongestPath`
matches Dijkstra, `DistanceOracle`'s diameter matches `MazeMetrics`'s double-BFS). Those
are exactly the invariants a storage/representation refactor would break, and D2 already
demonstrated the pattern working: internals were swapped with **zero test changes**.

On the LoadBalancerPro side, the honest trade-off is accepting that **Daedalus does not
have a per-request routing story today** and saying so, rather than shipping an adapter
that appears to work. The offline integrations (topology, capacity, placement) are real,
valuable, and unblocked — that is where the first release should land.

---

## Consequences

**Easier**
- Consumers supply their own topology; no grid coercion.
- One implementation of each algorithm serves mazes, meshes and lab experiments.
- The four consumption modes stop being four different integration stories.
- `theory` (min-cut, diameter, oracle, tours) becomes usable on real networks, which is
  where those algorithms were always aimed.

**Harder**
- Two node identities during migration (`Point` and `int`) until `MazeGrid` is fully behind
  the SPI. This must be time-boxed, not left to drift.
- Weighted edges generalise past `weightOf(Point)` (per-cell entry cost), so
  `WeightedMazeGrid` needs a companion edge-weighted implementation.
- `LandmarkHeuristic` is unit-cost-only by construction; on weighted topologies its
  precompute must switch from BFS to Dijkstra or it stops being admissible.

**To revisit**
- Whether `daedalus-server` should expose gRPC alongside REST for the data-plane mode
  (REST framing cost matters at per-request rates; batch/offline use does not care).
- Whether the plugin runtime should host *consumer* strategies (LoadBalancerPro routing
  policies as JARs) or stay Daedalus-only. Hosting foreign strategies makes the classloader
  isolation a security boundary, which it currently is not.

---

## Action Items

1. [x] **Correct `Vision/02-LoadBalancer-Integration-Guide.md`** — done 2026-07-19. The
       `dynamicHeuristic` example is replaced with load-in-`g` via `WeightedMazeGrid` plus
       an admissible `LandmarkHeuristic`, and the section carries an explicit correction
       notice. Note the two compose only because costs are kept `>= 1.0`, which keeps the
       unit-cost landmark bound a valid lower bound.
2. [x] Define `com.daedalus.graph.Graph` + `MazeGrid` adapter; retarget one solver
       (`BfsSolver`) as a spike — done 2026-07-19. `Graph`, `MazeGraph` (live view) and
       `CsrGraph` (CSR snapshot, updatable weights) shipped with 7 tests; `BfsSolver`
       retargeted. **Measured 2.39–2.75× faster** than the previous implementation, and
       the whole suite passed unchanged. The spike settles the design question: the seam
       is not an abstraction tax, it is faster than what it replaced.
3. [~] Retarget remaining solvers and `theory` classes; delete the maze-specific paths.
       `DijkstraSolver` and `AStarSolver` moved onto the seam 2026-07-19 (all tests
       unchanged). Measured effect was **inconclusive** (1.44× / 1.21× / 0.86× — noise),
       because D2 had already taken the win here; recorded honestly, and the phase stands
       on the architectural argument instead. `DialSolver` followed. The follow-up — give
       `Graph` a node-indexed weight accessor so `edgeWeight` stops allocating a `Point` —
       **was done as part of item 4**.

       `TremauxSolver` moved 2026-07-19, and "the seam pays exactly where hashing survived"
       held again — but the diagnosis mattered more than the move. Measuring first showed
       Trémaux takes **1.04 × V steps to BFS's 1.00 × V**, so the gap was entirely per-step
       cost, not walk length: marks lived in a `Map<Edge, Integer>` whose key was a record
       wrapping two `Point` records, looked up once per neighbour *and again inside a
       comparator during a per-step sort*. Flat `byte[V * 4]` marks plus a linear min-scan
       gave **3.3–6.8× faster**, landing Trémaux at roughly BFS's cost.

       The rewrite also surfaced a **correctness bug older than this seam work**: the solver
       implemented only two of Trémaux's three rules and so could not solve mazes containing
       loops, failing 19/40, 20/40 and 10/40 mazes at braid factors 0.25, 0.5 and 1.0. Fixed,
       and `TremauxSolverTest` now exists — it did not before, which is why nothing caught it.

       `BidirectionalSolver` (7 hashed collections) and `DfsSolver` (3) followed on the same
       day: **2.12–2.69×** and **3.09–3.19×** respectively, both landing in BFS's band. Each
       was proved equivalent over 1024 A/B cases — four generators × eight seeds × four braid
       factors × two sizes × four random start/goal pairs, comparing path *and* stats against
       a verbatim copy of the old code. Random endpoints matter for bidirectional: its
       smaller-frontier balancing rule only engages when the two searches are unbalanced,
       which corner-to-corner fixtures never make happen.

       **Four consecutive confirmations now** that the seam pays exactly where hashing
       survived and nowhere else — BFS 2.39–2.75×, Dial, bidirectional 2.12–2.69×, DFS
       3.09–3.19×, against no measurable gain for the solvers D2 had already put on cell-id
       arrays. That is a strong enough regularity to plan against rather than re-measure each
       time.

       `DeadEndFillingSolver` followed (**1.60–2.75×**, 1024 A/B cases identical), which
       **completes the solver retarget wherever the seam can pay**. Two solvers still hold
       hashed collections and are deliberately left alone:

       - `IDAStarSolver` is the most expensive solver in absolute terms, but the seam is not
         its lever. Its cost is re-expansion inherent to iterative deepening — each pass
         re-searches under a slightly larger f-bound — which a tighter heuristic addresses
         (ALT measured **41×** there) and data structures do not. Retargeting it would buy a
         constant factor on a quantity that is multiplied by the wrong thing.
       - `WallFollowerSolver`'s single hash set is stats bookkeeping, not algorithm state.
         The algorithm is O(1) memory by design; replacing the set with a `boolean[]` would
         add O(V) allocation to make the *reporting* marginally cheaper.

       `LongestPath` followed — the last hot hashed structure anywhere in the engine. Its
       backtracking DFS probed a `HashSet<Point>` once per neighbour of every visited node,
       up to the two-million-visit budget per call; flat `boolean[]` membership and an `int[]`
       path stack gave **3.56–3.76×** on braided 14² mazes, with 192 A/B cases identical.

       **Item 3 is now complete.** Six consecutive confirmations of the rule, and no
       counter-example: BFS 2.39–2.75×, bidirectional 2.12–2.69×, DFS 3.09–3.19×, Trémaux
       3.3–6.8×, dead-end filling 1.60–2.75×, longest-path 3.56–3.76× — against no measurable
       gain anywhere D2 had already moved to cell-id arrays. What remains hashed is
       deliberate: `IDAStarSolver` (its cost is re-expansion, which a tighter heuristic fixes
       and data structures do not), `WallFollowerSolver` (stats bookkeeping on an O(1)-memory
       algorithm) and `WaypointTour` (a one-off dedupe of at most 16 waypoints).
4. [x] Add `EdgeWeightedGraph` and move `LandmarkHeuristic` precompute to Dijkstra — done
       2026-07-19, and it turned out to be a **correctness** item, not the performance
       item it was filed as. No `EdgeWeightedGraph` type was needed: `Graph.edgeWeight`
       was already node-indexed, so the fix was to give `MazeGrid` a
       `weightOf(int row, int col)` accessor and override *that* in `WeightedMazeGrid`,
       which removes the `Point` allocation `MazeGraph.edgeWeight` was making on every
       relaxation. Adding a parallel interface would have been ceremony around a
       one-method change.

       The Dijkstra half exposed a live bug. `LandmarkHeuristic` stored BFS hop counts
       unconditionally, guarded only by a prose rule ("keep weights `>= 1.0`") that
       `WeightedMazeGrid.setWeight` never enforced. Below 1.0 the heuristic is
       inadmissible and A* silently returns suboptimal routes: measured on twelve braided
       24² topologies with weights in `[0.05, 0.35]`, **inadmissible in 575 of 576 cells**
       and **suboptimal on 12 of 12 seeds, by up to 36%**. Perfect mazes hid it completely
       — a spanning tree has one route per pair, so any heuristic finds it — meaning the
       bug was only reachable through braided topologies, i.e. the load-balancer case.

       `precompute` now selects its metric from the grid. Weighted grids get Dijkstra
       fields **in both directions**, because charging the entry cost of a cell makes the
       graph directed (`d(a,b) − d(b,a) = w(b) − w(a)`) and the symmetric
       `|d(L,b) − d(L,a)|` bound is therefore invalid; the directed pair
       `d(L,t) − d(L,s)` and `d(s,L) − d(t,L)` is used instead. Uniform grids keep the
       cheaper BFS path. Result: 0/576 violations, 0/12 suboptimal, and on 64² braided
       weighted topologies **5.79× fewer expansions / 1.9× faster** than plain Dijkstra
       (precompute ≈ 8 ms vs ≈ 2 ms for one solve, so it amortises after ~4 queries).
       15 new tests.
5. [x] Ship the three offline LoadBalancerPro integrations (topology, min-cut capacity,
       placement) as an `examples/loadbalancer-topology` module — done 2026-07-19, runnable
       via `mvn -f examples/loadbalancer-topology/pom.xml exec:java`, with 7 tests pinning
       its claims. Building it exposed a further defect worth its own follow-up:
       **`HilbertCurveGenerator` produces a disconnected topology** (edge connectivity 0
       corner-to-corner at 32², 396 dead ends), which invalidates the "generate a Hilbert
       topology and route across it" advice in both vision documents unless the output is
       braided first.
6. [~] Raise **three** requests against LoadBalancerPro (was two; the third came out of
       item 7's measurements):
       1. Open `RoutingStrategyId` — it is a closed enum
          (`TAIL_LATENCY_POWER_OF_TWO`, `WEIGHTED_LEAST_LOAD`, `WEIGHTED_LEAST_CONNECTIONS`,
          `WEIGHTED_ROUND_ROBIN`, `ROUND_ROBIN`), so no external project can contribute a
          strategy without patching the enum.
       2. Add `topologyNodeId` to `ServerStateVector` — without it there is no join key
          between a server and the graph node representing it, so Daedalus cannot route
          over a topology whose nodes are LoadBalancerPro servers.
       3. **New:** give `RoutingStrategy` an optional stateful form.
          `choose(List<ServerStateVector>)` hands over a fresh list per call, which obliges
          every strategy to be stateless and O(n) per decision and makes incremental data
          structures impossible to amortise. See ADR-002 for the measurement that produced
          this.

       All three are now written out as ready-to-file issue text in
       [`docs/upstream-requests-loadbalancerpro.md`](../upstream-requests-loadbalancerpro.md),
       each stating the problem, a suggested change that keeps existing callers compiling, and
       what happens if it is declined. Request 3 carries the ADR-002 measurement and an explicit
       caveat that Daedalus is **not** asking for the policy that evaluation rejected — only for
       the architectural ceiling to be removed.

       Still to do: paste them into the LoadBalancerPro tracker.
7. [x] Evaluate CSRBT `RankedSet` behind `TailLatencyPowerOfTwoStrategy` — done 2026-07-19,
       **declined**. Full write-up in
       [ADR-002](ADR-002-csrbt-rankedset-for-routing.md); measured with the real classes
       from both projects (LoadBalancerPro 2.4.2, csrbt-core 0.1.0), harness committed at
       `docs/evaluations/CsrbtRoutingEval.java`.

       Reading the strategy first changed the question: it samples exactly two servers at
       random and takes the better one, so **there is no order statistic in it to
       accelerate** — its only O(n) step is a boolean health filter, and per-server
       percentiles already ship on `ServerStateVector`. Adopting `RankedSet` therefore
       requires changing the *policy*, to "gate to the best q% then power-of-two inside".

       That policy is worse. It wins only against a perfectly fresh view of the fleet;
       at realistic staleness it is **29% worse on mean latency, 17% worse at p99, with
       double the peak in-flight count** — it herds, which is the exact failure uniform
       sampling exists to prevent. And where it did win, the tree was not the cause: an
       O(n) quickselect matched it at **1/9th–1/16th the cost**. Finally the interface
       forecloses the tree's real advantage — a fresh `List` per call means rebuilding
       every time, costing **5.8–9.1 µs per decision against 46–185 ns** for the shipped
       strategy. That last point is a fact about the call shape, not about CSRBT, and it
       is what produced request 3 above.

---

## Appendix — CLRS primitives that serve this direction

The existing `theory` package was built for mazes. These are the additions that pay off
specifically for topology and load balancing, in priority order.

**1. k-center placement — Ch. 35 (approximation), Ch. 34 (NP-completeness).**
"Where do we put N replicas / edge caches / AZ anchors so the worst-served node is as close
as possible?" is metric k-center: NP-hard, with a clean greedy **2-approximation** (repeatedly
place the next centre at the point farthest from all existing centres) and a matching
hardness bound at 2 unless P=NP. Daedalus already has every ingredient —
`MazeMetrics.farthestFrom` is literally the greedy step, and `LandmarkHeuristic` already
uses this exact selection rule to place landmarks. This directly serves the vision's "CDN
edge placement" and "rack & AZ placement" use cases.

**2. Max-flow with real capacities — Ch. 26.**
`MazeFlow` currently models unit-capacity passages. Generalising to integer capacities turns
min-cut into **bisection bandwidth** — the actual throughput ceiling between two halves of a
topology, and the number a capacity planner wants. Same machinery, strictly more useful.

**3. Bipartite matching — Ch. 26 via max-flow.**
The one classical algorithm whose shape *does* match `RoutingStrategy`: assigning a batch of
requests to servers under per-server capacity is bipartite b-matching. Unlike A\*, this
answers a selection question, and it is the principled version of "least connections" when
you are placing many requests at once rather than one at a time.

**4. Bellman-Ford and Johnson — Ch. 24, Ch. 25.**
Real latency graphs are **asymmetric** (`d(u,v) ≠ d(v,u)`), which every current solver
assumes away. Johnson's reweighting also makes all-pairs tractable on sparse directed
graphs — the honest version of `DistanceOracle` for topologies too large for its V² table.

**5. Incremental shortest paths — Ch. 24, extended.**
The live-routing mode implies weights that change continuously. Recomputing Dijkstra per
update is the naive answer; incremental/dynamic SSSP (D\*Lite-style) repairs only the
affected subtree. This is the single largest algorithmic gap between "batch topology tool"
and "data plane", and should be measured before it is assumed necessary.

**6. Order statistics — CSRBT, not CLRS Ch. 9.**
Selecting the p95 server does not need a new selection algorithm; CSRBT already maintains
`percentile`/`rank`/`select` in O(log n) under live updates. This is where the ecosystems
compose rather than duplicate.
