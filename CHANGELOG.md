# Changelog

All notable changes to Daedalus are documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Versions before
`1.0.0` (the multi-module split + first audit pass) live in git history
under the `_migration/` portfolios.

## [Unreleased] — 2026-07-18

**Features, security + infrastructure.** Repo is live at `RicheyWorks/Daedalus2`
and CI is green. The `ComplexityAnalyzer` surface lands empirical,
regression-friendly complexity tracking for the generators; per-key rate
limiting closes the shared-bucket gap on the write endpoints; the rest is
housekeeping on the things that make the repo behave.

### Added

- **`MazeMetrics.largestComponentCell`, and the corner assumption it removes —
  found by building the ai-dungeon-master example.** Four call sites seeded
  themselves at `new Point(0, 0)`: `MazeMetrics.diameter`,
  `FacilityPlacement.kCenter` / `kCenterAcrossComponents`, and
  `LandmarkHeuristic.precompute` (twice). That is safe for a maze generator —
  every cell is carved, so the top-left is always in the single component — and
  silently wrong for anything sparser.

  A BSP dungeon has **solid rock in its corners**. Running the new
  `examples/dungeon-layout` against a 33² dungeon, the first output was:

  ```
  exact diameter   99 steps
  fast estimate     0 steps        <- measured a one-cell component
  rooms served      1 of 529 floor cells
  entrance (0,0)   boss (0,0)      <- same square of rock
  ```

  `diameter` seeded at an isolated rock cell, returned 0, and
  `placeStartAndGoalAtExtremes` therefore put the entrance and the boss room in
  the same place. `FacilityPlacement` collapsed the same way. After seeding from
  the largest connected component instead — one extra O(V + E) flood fill, so
  `diameter` stays linear — the same level reports diameter 99 (agreeing with
  `exactDiameter`), a hardest route 2.5× the direct one, and **529 of 529 floor
  cells served**.

  On a fully carved maze `largestComponentCell` returns `(0, 0)`, so nothing
  changes for existing callers. This is the same defect class as the Trémaux and
  ALT bugs: an assumption about graph shape that every maze fixture satisfies.

- **`FacilityPlacement.kCenterAcrossComponents` — k-center that survives a
  partitioned graph.** Found by auditing `theory` for a second shape assumption:
  not loops this time but **disconnection**, which the vision docs' own
  chaos-engineering pitch creates ("inject 15% node failure").

  Nothing in `theory` throws on a fragmented graph — `DistanceOracle` reports
  `UNREACHABLE`, `WaypointTour` reports `feasible=false`, `MazeFlow` correctly
  gives edge connectivity 0 across a cut. But `kCenter`'s greedy scores an
  unreachable cell as `-1` and compares with `>`, so it can never leave the
  component it started in. Measured on a 16×16 tree severed along one column
  (16 cut edges in a spanning tree ⇒ 17 components):

  | k | `kCenter` radius / served | `kCenterAcrossComponents` radius / served |
  |---|---|---|
  | 1 | 82 / 114 of 256 | 82 / 114 of 256 |
  | 2 | 44 / 114 | 82 / 126 |
  | 3 | 25 / 114 | 82 / 169 |
  | 8 | 12 / 114 | 82 / 212 |
  | 12 | **7** / 114 | 82 / 254 |

  Adding facilities drives the covering radius steadily down — 82 to 7, a
  placement that looks better and better — while coverage never moves off
  **114 of 256 cells**. Every extra facility refines service inside the one
  component the greedy can see; the other 142 cells are no closer to anything.
  Nothing lies; `servedCells` is in the result. But a quality metric that
  *improves* while more than half the graph stays unreachable is worth naming
  explicitly.

  **Both behaviours are kept, because both have a real consumer.** For a dungeon
  — placing treasure, save points or boss rooms — unreachable cells are solid
  rock, genuinely not places, and `kCenter` is correct. For a partitioned
  network, every fragment still holds real nodes, and `kCenterAcrossComponents`
  is. The new variant ranks unreachable cells as infinitely badly served, which
  is simply what the k-center objective says: the cost of a placement is the
  distance from the worst-served node, and for an unreachable node that is
  infinite. The 2-approximation still holds per component; across components no
  ratio is claimed, since with fewer facilities than components the objective is
  unbounded. On a connected grid the two are asserted to agree exactly, so the
  generalisation cannot disturb the ordinary case.

- **`MazeMetrics.exactDiameter` — the true diameter, for when the estimate
  isn't good enough.** Came out of auditing the `theory` package for the same
  defect class that bit the solvers: code that is only correct on a tree. The
  two prime suspects both turned out to be **already honest** —
  `MazeMetrics.diameter` documents itself as "exact for perfect (tree) mazes; a
  lower-bound heuristic if the maze has cycles", and `LongestPath` names its own
  NP-hardness and states outright that "the problem only becomes hard once the
  maze is braided". No bug to fix.

  What neither did was *quantify* the caveat, which is what a caller actually
  needs. Measured over 15 mazes at 20² per setting, double-BFS against the true
  diameter:

  | braid factor | mean error | worst error |
  |---|---|---|
  | 0.0 (perfect) | 0.0% | 0.0% |
  | 0.1 | 0.5% | 9.6% |
  | 0.3 | 0.6% | 8.4% |
  | 0.5 | 1.4% | **20.0%** |
  | 0.7 | 3.4% | 9.5% |
  | 1.0 | 2.5% | 13.6% |

  Tight on average, but **up to 20% low on an individual looped maze**. The
  two-sweep argument needs the farthest cell from an arbitrary source to be an
  endpoint of some diameter, and one cycle breaks that — a shortcut can land the
  first sweep somewhere lying on no diameter at all.

  That distinction is use-case dependent, so both are now available and the
  javadoc says which to reach for. Ranking generators or placing a start and
  goal far apart: keep the O(V + E) estimate — `placeStartAndGoalAtExtremes`
  deliberately still uses it. Capacity or latency planning over a braided
  topology, where the diameter *is* the worst-case route length: use
  `exactDiameter` and pay the O(V²).

  Tested against an independent brute-force implementation at four braid
  factors, plus a directional assertion that the fast estimate is **never an
  over-estimate** — that direction is the one that matters, since an
  over-estimate would understate worst-case route length in planning use.

- **Generator shape sweep — every generator against awkward grid shapes.**
  Third shape assumption audited today, after loops and disconnection: **grid
  shape itself**. Every generator fixture in the repo used a square grid, yet
  several generators carry an implicit assumption about dimensions — the
  space-filling curves want a power of two, `EllersGenerator` works a row at a
  time, `DungeonGenerator` needs room to split BSP leaves.

  `GeneratorConnectivityTest` already covered this for `HilbertCurveGenerator`
  specifically, since that is where the forest bug was found. It now sweeps all
  21 spanning-tree generators across eight shapes: `1×1`, `1×10`, `10×1`, `2×3`,
  `7×13` (both prime), `33×17`, `5×64` (extreme aspect ratio) and `20×20`
  (square but not a power of two). `DungeonGenerator` gets its own case at the
  same shapes, asserting the property that survives its contract — rock is meant
  to be unreachable, but the **carved** space must be a single connected level,
  or the layout contains rooms the player can never enter.

  **The audit found nothing**: 22 generators × 9 shapes, zero violations. Worth
  having anyway — it converts "the square-grid tests happen to pass" into an
  enforced property, and a generator that quietly dropped the last column of a
  lopsided grid, or divided by zero on a single row, would now fail loudly.

- **`SolverBraidedMazePropertyTest` — every solver, over mazes with loops.**
  Closes the gap that let two separate correctness bugs ship behind a green
  suite this month: **every solver fixture in the repository was a perfect
  maze**. A perfect maze is a spanning tree, which makes it a uniquely
  forgiving subject — exactly one route exists between any pair of cells, so a
  solver can be badly wrong and still look right. `LandmarkHeuristic` was
  inadmissible yet A* still returned the optimal path (there was only one to
  return); `TremauxSolver` could not solve a looped maze at all and no fixture
  contained a loop.

  The test sweeps 10 solvers × 4 generators × 5 seeds × 4 braid factors and
  asserts three properties: every returned path is a legal traversal (starts at
  the start, ends at the goal, never crosses a wall), every *complete* solver
  finds a route wherever BFS does, and every *optimal* solver still returns a
  shortest one once route choice actually exists. Runs in ~1.2 s.

  **The audit behind it found no further defects** — nine of ten solvers are
  correct at every braid factor, and the tenth, `wall-follower`, fails only
  where its own javadoc says it will (wall following is provably complete only
  on simply-connected mazes; it gives up via an iteration cap rather than
  hanging, and never returns a wrong path). Its exclusion is scoped to
  completeness alone — it is still held to the legality contract, and a separate
  case pins the guarantee it *does* make. Asserting that it fails on loops would
  forbid anyone from later improving it.

  Verified to have teeth rather than assumed: replaying the pre-fix
  `TremauxSolver` against this exact matrix fails **21 of 80** cases. There is
  also a tripwire asserting the solver list is complete, since silently omitting
  a new solver is precisely how Trémaux went untested.

- **`ApplicationSmokeTest` — the first test that boots the whole application.**
  Until now every server test was a slice (`@WebMvcTest` for controllers,
  `ApplicationContextRunner` for `RedisConfig`), which left a blind spot: no
  test ever assembled the full context, and nothing whatsoever exercised what
  the starters contribute for free. The springdoc **2.6.0 → 3.0.3** major bump
  went through a fully green 267-test suite without a single assertion touching
  `/v3/api-docs`. This adds one `@SpringBootTest(webEnvironment = RANDOM_PORT)`
  covering the joins: the context loads with the engine registries wired across
  the module boundary, `/actuator/health` is `UP`, `/v3/api-docs` serves a
  document whose `paths` cover the contract endpoints, and `/swagger-ui` is
  served. Path coverage is asserted as a *subset* (`containsAll`), not an exact
  count — adding an endpoint shouldn't fail the test, but silently losing one
  should.

  It paid for itself on the first run by failing on the 503 health bug recorded
  under **Fixed** below — a defect no slice test could have observed, and one
  that had been latent in the default profile.

  Implementation note for anyone extending it: this uses Spring Framework 7's
  `RestTestClient`, because **Boot 4 removed `TestRestTemplate`** from
  `spring-boot-test`. `WebTestClient` is the usual alternative but pulls in
  `spring-webflux`, which this module deliberately does not depend on.

- **`theory.ComplexityAnalyzer` — empirical complexity harness.** Revives the
  long-stubbed `com.daedalus.theory.ComplexityAnalyzer` (last seen in the v1.x
  portfolio) against the current engine API. Runs every registered generator
  at a fixed seed across configurable square sizes (default 32²/64²/128²),
  capturing the work each reports through `MazeStats` (cells visited, peak
  frontier, backtracks, path length) plus a wall-clock timing. `analyzeAll()`
  sweeps a `GeneratorRegistry` and returns a stably-sorted `Report` (a
  generator that throws is recorded as `success=false` rather than sinking the
  sweep). `Report.toCsv()` / `toJson()` emit only the deterministic,
  seed-stable columns — no wall-clock — so the report is a committable golden
  file for regression detection; timing stays on each `Measurement` for live
  inspection. Hand-rolled CSV/JSON, so daedalus-core gains no new dependency.
  Covered by 10 tests (determinism, no-stats and throwing-generator paths,
  a sweep over all 20 built-in generators, and the serialized shape). Clears
  the item from `BACKLOG.md` "New surfaces".
- **`theory.GrowthEstimator` — empirical Big-O labelling.** Turns a
  `ComplexityAnalyzer` sweep into a growth verdict per generator: fits each
  `metric(n)` against candidate classes (`O(1)` … `O(n^2)`) by
  least-squares-through-origin plus R² model selection, and reports the
  log-log power-law exponent alongside. Deterministic (rides the seed-stable
  counters); metrics that stay at zero or fewer than two distinct sizes return
  `UNKNOWN` rather than a fabricated class. Covered by 8 tests over synthetic
  known-growth data plus a live sweep. Implements idea **T1** from
  `AUDIT_CLRS_IDEAS_2026-07-18.md`.
- **`theory.MazeMetrics` — diameter & auto start/goal placement.** Double-BFS
  over the passage graph (CLRS Ch. 22) finds the maze's two farthest-apart
  cells — exact for perfect (tree) mazes, a lower-bound heuristic when the maze
  has cycles — and `placeStartAndGoalAtExtremes` drops the start and goal there
  for a maximal-challenge layout. Also exposes `farthestFrom` and
  `distancesFrom` (BFS distance field, `-1` for unreachable) for heat-maps.
  Deterministic (row-major tie-break on the farthest cell). Implements idea
  **T3** from the CLRS audit; 6 tests over hand-built mazes and a real
  perfect maze.
- **`theory.MazeFlow` — min-cut chokepoints & edge connectivity.** Edmonds-Karp
  max-flow (CLRS Ch. 26) over unit-capacity passages: the minimum start→goal
  cut is the fewest passages that would seal the goal off, and the cut edge set
  is exactly those bottleneck passages. Equivalently the start↔goal edge
  connectivity — `1` for a perfect maze (single route), `≥2` once braided.
  `minCutStartToGoal` / `edgeConnectivity` convenience; deterministic.
  Implements idea **X1** from the CLRS audit; 6 tests (perfect vs. braided,
  cut-edges-actually-disconnect, determinism).
- **`solver.solvers.DialSolver` — bucket-queue (Dial's) shortest path.** Dijkstra
  with a bucket priority queue keyed by integer distance (CLRS Ch. 24, and the
  bounded-key idea of Ch. 20): `O(C·V + E)` instead of `O((V + E) log V)`,
  near-linear on a grid. Reads the same `weightOf` hook as `DijkstraSolver` and
  returns an identical optimal path on uniform and integer-weighted mazes; it
  refuses fractional weights (bucketing is ill-defined — use Dijkstra there).
  Registered in `AlgorithmConfig` as solver id `dial`. Implements idea **S1**
  from the CLRS audit; 7 tests (matches Dijkstra on uniform + integer-weighted
  grids, detours around costly cells, rejects fractional weights, determinism).
- **`theory.LongestPath` — hardest route (longest simple path).** Budget-bounded
  DFS backtracking for the longest simple start→goal path: exact for small mazes,
  an honest lower bound (`exact=false`) when the budget is hit — never a wrong or
  non-simple path. The class javadoc documents why this is NP-hard (Hamiltonian
  path reduces to it, CLRS Ch. 34) and why no polynomial exact algorithm is
  attempted (Ch. 35). Trivial on perfect mazes (unique path), interesting once
  braided. `hardestRoute(grid)` convenience. Implements idea **T2** — the last of
  the CLRS-audit top five; 5 tests (braided longest > shortest, perfect == unique
  path, inexact-under-budget, determinism).
- **`engine.Braider` — dead-end braiding.** Seeded, deterministic post-process
  that opens one wall on a configurable fraction of dead ends, turning any
  generator's perfect maze (a spanning tree) into a braided one with real loops
  and route choice. This is the keystone for the structural metrics: min-cut
  (`MazeFlow`) is always 1 on a tree and longest-path (`LongestPath`) always
  equals shortest, so both only become meaningful once braided. Implements idea
  **G4**; 6 tests (full braid leaves zero dead ends, edge count exceeds `V-1` so
  cycles exist, exact fractional targeting, determinism, no-op at factor 0).
- **`solver.LandmarkHeuristic` — ALT (A\*, landmarks, triangle inequality).** BFS
  distance fields from a few greedily-spread landmarks give the bound
  `h(a,b) = max_L |d(L,b) - d(L,a)|`, admissible by the triangle inequality (the
  same potential-function reasoning as Johnson's reweighting, CLRS Ch. 25).
  Unlike Manhattan — which measures straight-line distance and is oblivious to
  walls — these distances are measured through the actual passages, so the bound
  reflects the detours a solver really has to make. Plugs straight into
  `AStarSolver`'s existing heuristic constructor. **Measured: ~55% fewer A\*
  expansions than Manhattan** (58,799 → 26,167 cells across 45 mazes at 25², 40²
  and 60²). Unit-cost grids only — hop counts would over-estimate on a
  `WeightedMazeGrid` and break optimality, which the javadoc states plainly.
  Implements idea **S2**; 5 tests (admissibility checked on *every* cell,
  optimality vs BFS, the aggregate expansion win, deterministic landmark choice).
- **`engine.generators.WeightedPrimsGenerator` — Prim's as an actual MST.**
  Weights every wall up front and always carves the cheapest frontier wall via a
  priority queue (CLRS Ch. 23), where the existing `PrimsGenerator` pulls a
  *uniformly random* frontier wall — a different algorithm with a different bias,
  so the two yield different mazes from the same seed. Registered as generator id
  `weighted-prims` (the built-in roster is now 21).
  **Correction to the original idea:** it proposed weight *variance* as a texture
  knob, but that cannot work — an MST depends only on the relative *order* of edge
  weights, and any strictly monotone reweighting (scaling, powers, variance
  changes) leaves the order, and hence the tree, identical. i.i.d. weights from
  any continuous distribution give the same family of mazes. What genuinely
  changes texture is breaking isotropy, so the knob shipped is a
  `horizontalBias` subtracted from east–west walls, which stretches the maze into
  long horizontal corridors. Implements idea **G1**; 5 tests (spanning-tree
  property, determinism, differs from random-frontier Prim's on the same seed,
  the bias measurably increases east–west passages, stats populated).
- **`theory.MazeFlow.vertexDisjointPaths` — route redundancy via Menger.** Counts
  the routes between two cells that share no intermediate cell, using the
  vertex-splitting reduction to max flow (CLRS Ch. 26): every cell becomes
  `v_in → v_out` joined by a capacity-1 arc, so no single cell can carry two
  routes. By Menger's theorem that count is also the fewest intermediate cells
  you'd have to block to sever the two. It is always `<=` the edge connectivity
  from X1 — blocking cells is at least as powerful as blocking passages — and is
  exactly `1` on any perfect maze, since a tree has one route; `Braider` is what
  creates genuine alternatives. Implements idea **X2**; 8 tests, including the
  vertex `<=` edge invariant checked across 15 braided mazes.
- **`theory.WaypointTour` — optimal "collect all the coins" routes.** Shortest
  route from a start cell visiting every waypoint, solved exactly by the
  Held–Karp dynamic program (CLRS Ch. 15's subset DP applied to the TSP-path
  variant of Ch. 34). Visiting waypoints nearest-first is *not* optimal — picking
  the order is the hard part — so the DP keys on *(set already collected, cell
  you're standing on)* instead of the full ordering, trading factorial time for
  `O(2^k · k²)`. That's exponential in the waypoint count but independent of maze
  size, which is exactly the right shape for a game mode: a handful of coins in a
  large maze. Waypoints are capped at 16 with a clear error beyond that, and the
  chosen order is stitched back into a real cell path. Also adds
  `MazeMetrics.shortestPath`. Implements idea **T5**; 7 tests, the key one
  cross-checking the DP against brute-force enumeration of every visiting order.
- **`util.TileGridCodec` — run-length wire encoding for tile grids.** Encodes the
  rendered `char[][]` the REST/STOMP surfaces ship as `<rows>x<cols>:` plus
  row-major runs. Since no `TileType` glyph is a digit, a count-prefixed run
  parses with no separators or escapes, and a run of one is written as the bare
  glyph so the encoding can never expand the payload. Runs cross row boundaries,
  which is where the border and corridor stretches collapse.
  **Measured saving: 36–38%** (encoded is 62–64% of raw, stable from 16² to
  128²). Implements idea **X3**; 7 tests covering round-trip on real mazes, every
  glyph, malformed input and ragged grids.
  **Worth knowing before using it:** a rendered maze alternates cell/wall at
  nearly every column, which is close to the worst case for run-length coding, so
  36% is about all it can give. The far bigger win is not compressing this grid
  but *not sending it* — the rendered grid is `(2r+1) x (2c+1)`, roughly four
  times the cell count, while the maze itself is two wall bits per cell. Measured
  side by side at 64² and 128², sending cell bits is **~16× smaller** than the
  rendered glyph grid. This codec is the drop-in that needs no API change; the
  16× needs a client-side renderer.
- **`examples/loadbalancer-topology` — the integration made runnable (ADR-001, item 5).**
  A standalone module (not a reactor child, matching `examples/biome-plugin`) that
  demonstrates the three LoadBalancerPro integrations needing no changes to either
  project: generate a topology, measure its capacity with min-cut, and place replicas with
  k-center — plus latency-aware routing done the corrected way, with load in the edge cost
  and an admissible heuristic. A fifth section builds a spine-and-leaf `CsrGraph`, a
  degree-3 topology no `MazeGrid` could express, to show the seam taking a real network
  shape. Seven tests pin the claims, because an example that only prints is documentation
  that can rot.
  **It also surfaced a defect the vision documents miss:** `HilbertCurveGenerator`'s raw
  output is **not connected**. At 32² the edge connectivity from `(0,0)` to `(31,31)`
  measures **0** — no route exists — with 396 dead ends. Since both the vision document and
  the integration guide recommend Hilbert as *the* topology generator and then route across
  it with A\*, anyone following that advice gets an empty path back, silently, in the same
  way the heuristic bug was silent. Measured across braid factors: `0.0` → connectivity 0,
  `0.6` → 1, `1.0` → 2. The example therefore braids fully and says why, and a test pins
  the raw generator's disconnectedness so the finding cannot quietly regress.
- **`theory.FacilityPlacement` — k-center placement (ADR-001 appendix, item 1).** Where to
  put `k` edge caches / replicas / rack anchors so the worst-served node is as close as
  possible, by the farthest-first greedy (CLRS Ch. 35): take any node, then repeatedly add
  the node currently worst served. That is a **2-approximation**, and since no polynomial
  algorithm can guarantee better than 2 unless P = NP (Ch. 34), the simple algorithm also
  carries the best available guarantee. The greedy step turns out to be
  `MazeMetrics.farthestFrom` generalised to a set — the same rule `LandmarkHeuristic`
  already uses to spread landmarks, which is not a coincidence: both want points far from
  each other and from everything else.
  Also exposes `coveringRadius(grid, facilities)` for scoring a placement you already have.
  Unreachable cells (a dungeon's solid rock) are simply unserved rather than distorting the
  radius. 8 tests, the load-bearing one **verifying the 2-approximation against brute-force
  enumeration of every k-subset** on small mazes — the guarantee is checked, not asserted.
- **`com.daedalus.graph` — the graph seam (ADR-001, phase 1).** `Graph` is the abstraction
  that lets Daedalus route over any topology rather than only a rectangular maze:
  dense integer node ids, and adjacency delivered into a **caller-owned buffer**
  (`neighbors(node, int[] out)`) so a search loop allocates nothing. Two
  implementations ship: `MazeGraph`, a zero-cost **live view** over `MazeGrid` that
  reads wall flags directly, and `CsrGraph`, a compressed-sparse-row snapshot built
  from caller-supplied edges — the entry point for a service mesh or rack layout that
  was never a maze, with in-place `setEdgeWeight` so live latency/load can move
  without rebuilding the structure.
  `BfsSolver` is retargeted onto it as the proving spike, and the seam paid for
  itself immediately: **2.39–2.75× faster** (58–64% less time over 12 mazes at 80²)
  against a faithful copy of the previous implementation. That beats even D2's
  1.42–1.72×, because BFS shed the per-node `ArrayList` from `openNeighbors` on top of
  the hashing. Every existing test passed **unchanged**, including the cross-solver
  agreement checks that compare bidirectional and A\* against BFS — which is the
  evidence the retarget is behaviour-preserving.
  **Phase 2** moved `DijkstraSolver` and `AStarSolver` onto the same seam, removing the
  last per-expansion `List` from their loops. Benchmarking that change was
  **inconclusive** — 1.44×, 1.21×, then 0.86× across reps, i.e. inside the noise — and it
  is recorded as such rather than dressed up. The reason is that D2 already took the big
  win here by removing the hash collections; what remains is priority-queue work plus the
  `Point` that `MazeGraph.edgeWeight` still allocates, so the list was a small share of
  the total. **This phase is justified by architecture, not performance**: one adjacency
  contract across every solver, and the ability to run them on a topology that was never a
  maze. A node-indexed weight accessor would remove the last allocation and is the obvious
  next measurement.
  **`DialSolver`** followed, and is worth recording as a worked example of predicting
  wrong. It was the last `HashMap<Point,…>` solver, so a BFS-sized win was predicted. The
  first retarget delivered **1.14× / 1.28× / 1.00×** — barely anything. The cause was in
  the new code, not the old: buckets were still a `Map<Integer, IntBucket>`, so every
  relaxation did a `computeIfAbsent` on a **boxed distance key** and put hashing straight
  back on the hottest path — the exact cost the seam exists to remove. Indexing buckets by
  distance directly (a plain `IntBucket[]`, grown on demand) delivered
  **1.94× / 2.36× / 1.99×**, the win originally predicted. Behaviour is unchanged
  throughout: `dial` still returns paths identical to `dijkstra`, and still rejects
  fractional weights.
  **`theory.MazeMetrics`** moved onto the seam last, chosen by measurement rather than by
  working down the solver list: it is the one class on everything's hot path, because
  `DistanceOracle.precompute` runs a BFS *per cell* and `LandmarkHeuristic` and
  `WaypointTour` sit on it too. Removing the per-cell neighbour list there compounds
  across all of them — `DistanceOracle.precompute` on a 48² maze (2,304 BFS runs) went
  from ~239 ms to ~146 ms, a steady **1.59–1.73×**. The remaining six solvers all still
  use `HashMap`/`HashSet` and are candidates on the same evidence, but each should be
  measured rather than assumed, since Dijkstra and A\* showed the seam pays nothing where
  hashing was already gone.
  **`theory.MazeFlow`** followed, picked by the same rule and giving the largest win yet:
  **2.46× / 3.21× / 5.59×** on eight braided 64² mazes. It was the heaviest hasher left — a
  `Map<Long, Integer>` residual table keyed by packed `(from, to)` pairs, boxing a `Long` on
  every residual lookup, and max-flow performs one per edge per BFS. That is now a
  compressed-sparse-row residual network (`offsets` / `targets` / `twin` / `capacity` arrays)
  with an `int[]` BFS queue, so the inner loop boxes nothing. Cut sizes and cut edges are
  unchanged — both `MazeFlow` suites pass untouched, including the test that verifies removing
  the reported edges genuinely severs source from sink. This matters beyond microbenchmarks:
  min-cut is what capacity analysis calls in the LoadBalancer example, so it is on the
  ecosystem's hot path rather than the maze game's.
  `vertexDisjointPaths` followed in the same file, replacing its
  `List<List<Integer>>` adjacency and `Map<Long, Integer>` residual with an arc-indexed
  split graph — every arc paired with a zero-capacity reverse twin, grouped by tail, which
  is the textbook max-flow representation in flat arrays. **2.02× / 3.04× / 3.74×**, with
  the vertex `<=` edge invariant and every other assertion unchanged. `MazeFlow` now holds
  no hash structures at all, and the dead `key()`, list-based `addArc` and
  `findAugmentingPath` helpers are gone with their imports.
- **`engine.generators.DungeonGenerator` — rooms and corridors (C3).** Binary
  space partitioning: split the grid recursively, carve a room in every leaf,
  then join sibling regions with L-shaped corridors on the way back up. The
  recursion order is what guarantees connectivity — each subtree is joined to its
  sibling exactly once. Registered as generator id `dungeon` (the roster is now
  22).
  This is the first generator here that is **deliberately not a perfect maze**,
  and it inverts all three of the usual properties: rooms are open areas (interior
  cells open on all four sides), rooms are dense blocks of cycles so routes are
  never unique, and the rock between rooms is never carved and stays unreachable.
  Callers that assume full reachability must not use it — the `MazeGenerator`
  contract allows this explicitly ("unless their theoretical contract says
  otherwise"). A pleasant side effect: the structural metrics that need `Braider`
  to become interesting on a maze — `MazeFlow`'s min-cut, `LongestPath` — are
  non-trivial here for free. 8 tests covering room openness (measured against a
  perfect maze of the same size), loop presence, unreachable rock, connectivity
  of everything carved, and statelessness across reuse.
- **`theory.DistanceOracle` — all-pairs distances, O(1) queries.** BFS from every
  cell tabulated into a flat `short[]`, so any later "how far is A from B" — a
  leaderboard scoring against the optimal route, arbitrary start/goal queries,
  ranking cells by eccentricity — is a single array read (CLRS Ch. 25, unweighted
  special case). Also exposes `eccentricity` and `diameter`.
  The binding constraint is memory, not time: the table is `V²`, and `V` is
  itself quadratic in the maze's edge length, so 32² needs 2 MB, 64² needs 32 MB
  and 128² would need 512 MB. Rather than quietly exhaust the heap it caps at
  4,096 cells and throws with a pointer to `MazeMetrics.distancesFrom` (one BFS,
  one row of this table) for larger mazes. Implements idea **S4**; 8 tests,
  including an exhaustive every-pair check against BFS and a diameter
  cross-validation against `MazeMetrics`, which derives the same number by
  double-BFS instead of exhaustive scan.

### Changed

- **ADR-002 — CSRBT `RankedSet` behind `TailLatencyPowerOfTwoStrategy`:
  evaluated and declined** (ADR-001 item 7). Measured against the real classes
  from both sibling projects — `ServerStateVector` / `ServerScoreCalculator`
  from LoadBalancerPro 2.4.2, `OrderedSet` / `RedBlackStrategy` from csrbt-core
  0.1.0 — over a simulated 64-server fleet. Harness committed at
  `docs/evaluations/CsrbtRoutingEval.java`.

  Reading the strategy first changed the question. It samples exactly **two**
  servers at random and takes the better one; its only O(n) step is a boolean
  health filter, and `ServerStateVector` already carries per-server `p95`/`p99`.
  **There is no order statistic in it to accelerate**, so adopting a ranked
  structure necessarily means changing the *policy* — to "gate to the best q%
  of the fleet, then power-of-two inside that pool".

  The decisive variable turned out to be **how stale the balancer's view is**,
  which is also the entire reason power-of-two-choices exists. Benchmarking
  against a perfectly fresh view measures a system nobody runs:

  | view refreshed every 25 requests | mean ms | p99 ms | max in-flight | ns/decision |
  |---|---|---|---|---|
  | **uniform po2 (shipped)** | **6.03** | **19.13** | **5** | **48** |
  | greedy least-score | 33.77 | 52.77 | 19 | 200 |
  | RankedSet-gated po2 | 7.86 | 22.32 | 13 | 5 870 |
  | quickselect-gated po2 | 7.78 | 21.52 | 10 | 417 |

  Three findings, any one sufficient to decline. The gating policy **herds** —
  29% worse mean, 17% worse p99, double the peak in-flight — because
  concentrating the sample pool on whatever looked best in the last snapshot
  sends every request to the same place; greedy, the limiting case, is 9× worse.
  Where gating *did* win (fresh view only), an O(n) quickselect matched the tree
  at **1/9th the cost**, so the gain came from the policy, not the structure.
  And `RoutingStrategy.choose(List<ServerStateVector>)` hands over a **fresh
  list per call**, so an order-statistic tree — whose whole advantage is
  incremental maintenance — must be rebuilt every time: **5.8–9.1 µs per
  decision against 46–185 ns**, 30–125× more expensive, on the per-request hot
  path.

  That last point is a fact about the call shape rather than about CSRBT, and it
  produced a concrete upstream request (ADR-001 item 6, request 3): give
  `RoutingStrategy` an optional stateful form, since the current signature
  obliges every strategy to be stateless and O(n) per decision.

- **`DeadEndFillingSolver` moved onto the graph seam — the last solver where it
  pays (ADR-001 item 3).** Both phases retargeted: the cascade's `HashSet` of
  filled cells and `ArrayDeque` frontier, and phase two's BFS maps.
  **Measured 1.60–2.75× faster** over 12 mazes at 80².

  One deliberate simplification. The old cascade could enqueue the same cell
  several times and discarded the duplicates at poll time, which meant no exact
  capacity bound existed. Enqueueing each cell at most once is equivalent — a
  cell is filled the first time it is polled and never unfilled, so later
  enqueues were always no-ops — and it makes V an exact bound rather than a
  guess. That is the kind of "obviously equivalent" reasoning worth distrusting,
  so it was checked: **1024 A/B cases identical** on path, `cellsVisited` and
  `cellsExplored`.

  The nested neighbour scan needs **two** adjacency buffers, not one — the inner
  loop counting a neighbour's surviving exits would otherwise clobber the outer
  loop's contents mid-scan. Sharing one buffer compiles and passes casually
  written tests; it silently corrupts the cascade.

- **`BidirectionalSolver` and `DfsSolver` moved onto the graph seam (ADR-001
  item 3).** These were the two largest remaining holdouts — bidirectional
  carried **seven** hashed-`Point` collections (two parent maps, two seen sets,
  two `ArrayDeque` frontiers, plus a `LinkedList` for reconstruction), DFS
  carried three. Both now run on `MazeGraph` adjacency into a reused buffer,
  with `int[]` parent arrays, `boolean[]` seen flags and `int[]` frontier
  storage sized at exactly V (each node is enqueued at most once, so that bound
  is exact rather than a guess).

  | | before | after | speedup |
  |---|---|---|---|
  | `bidirectional` | 11.97–13.14 ms | 4.88–5.86 ms | **2.12–2.69×** |
  | `dfs` | 10.71–11.20 ms | 3.46–3.51 ms | **3.09–3.19×** |

  Measured over 12 mazes at 80², mean of 5 reps after warm-up. Both land in the
  band BFS got (2.39–2.75×), which is the fourth consecutive confirmation of the
  rule this phase established: **the seam pays exactly where hashing survived,
  and nowhere else.** Every solver that had already been moved onto cell-id
  arrays showed no further gain; every one still hashing `Point` gained 2–3×.

  Equivalence was verified rather than argued: **1024 A/B cases each**, across
  four generators × eight seeds × four braid factors × two sizes × four random
  start/goal pairs, comparing path *and* stats (`cellsExplored`, `cellsVisited`)
  against a verbatim copy of the previous implementation. All 2048 identical.
  Random start/goal pairs matter for bidirectional specifically — its
  smaller-frontier balancing rule is only exercised when the two searches are
  unbalanced, which corner-to-corner runs never do.

- **`TremauxSolver` moved onto the graph seam; edge marks are a flat `byte[]`
  (ADR-001 item 3).** Diagnosed before being touched, which changed the fix.
  Trémaux was among the slowest solvers, and the intuitive read — "it's a walk,
  walks are long" — is wrong: it takes **1.04 × V steps against BFS's
  1.00 × V**, essentially identical work. The whole gap was **cost per step**,
  so no algorithmic tuning would have moved it.

  The culprit was the mark table. Marks lived in a `Map<Edge, Integer>` where
  `Edge` was a record wrapping two `Point` records, so every lookup allocated a
  composite key — and lookups ran once per neighbour **and again inside a
  `Comparator` during a per-step `sort`**, so each step allocated edge keys
  O(d log d) times plus a comparator, a neighbour `List`, and boxed `Integer`
  values, all to choose between at most four options.

  Marks are now `byte[V * 4]` addressed by `cell * 4 + direction`, with both
  halves of a passage incremented together so the pair acts as one undirected
  mark. Neighbours come from `MazeGraph` into a reused buffer, and the sort is
  replaced by a linear min-scan. **Measured 3.3–6.8× faster** over 12 mazes at
  80², which puts Trémaux at roughly BFS's cost (0.8–1.45×) instead of several
  times it. Selection is provably equivalent — `MazeGraph` yields neighbours in
  the same `Direction` order and the old sort was *stable*, so "first minimum
  wins" reproduces the previous choice exactly.

- **`MazeGrid.weightOf(Point)` is now `final`** — closing a silent-failure hazard
  the coordinate-indexed accessor introduced. Once the graph seam started asking
  for weights by `(row, col)`, a subclass overriding the older `Point` form
  would still compile but be **bypassed entirely**: its costs would vanish and
  A\* would quietly optimise the wrong thing. Sealing the delegate turns that
  into a compile error naming the method to override instead. Nothing in the
  repo was affected — only `WeightedMazeGrid` overrode it, and that had already
  moved — but `daedalus-plugin-runtime` loads third-party jars that may subclass
  `MazeGrid`, so the failure mode was reachable from outside.

- **`MazeGrid.weightOf(int row, int col)` — coordinate-indexed entry cost.**
  The graph seam addresses nodes by dense integer id, so
  `MazeGraph.edgeWeight(int, int)` was building a `Point` on every edge
  relaxation purely to hand it to `weightOf(Point)`, which immediately unwrapped
  it again — one allocation per relaxation, in the hottest loop the engine has.
  Subclasses now override the `(row, col)` form and `weightOf(Point)` delegates
  to it, so there is a single implementation point and both forms cannot drift.
  This is ADR-001 item 4's "add `EdgeWeightedGraph`" resolved without adding a
  type: `Graph.edgeWeight` was already node-indexed, so a parallel interface
  would have been ceremony around a one-method change.

- **Spring Boot 3.3.1 → 4.1.0 (with Framework 7).** The server, plugin runtime
  and desktop modules now build on the Boot 4 line. Four coordinate changes and
  a single import were the entire migration:

  | | before | after |
  |---|---|---|
  | `spring-boot-starter-parent` | 3.3.1 | **4.1.0** |
  | `resilience4j.version` | 2.2.0 | **2.4.0** |
  | resilience4j artifact | `resilience4j-spring-boot3` | **`resilience4j-spring-boot4`** |
  | `springdoc.version` | 2.6.0 | **3.0.3** |

  The lone source change is in `RedisConfigConditionalTest`: Boot 4 split the
  monolithic `spring-boot-autoconfigure` jar into per-technology modules, which
  both moved *and* renamed the class —
  `org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration`
  became `org.springframework.boot.data.redis.autoconfigure.DataRedisAutoConfiguration`
  (now in `spring-boot-data-redis`). Nothing in `src/main` needed touching in
  any module.

  **Verified, not assumed.** The migration was first run in a throwaway copy of
  the tree. The initial `mvn test` reported **28 errors** — a mix of
  `NoSuchMethodError` on `MockHttpServletRequestBuilder.contentType(String)` and
  `IncompatibleClassChangeError: HttpHeaders does not implement MultiValueMap`.
  Every one of those was an artifact of Maven's *incremental* compilation
  leaving Boot 3 test bytecode on disk to run against Boot 4 jars; return types
  and interface sets are part of a JVM method signature, so stale classes fail
  exactly this way. A `clean` rebuild reduced 28 errors to **one** — the Redis
  import above. The lesson generalises: when a dependency bump produces
  `NoSuchMethodError` for a method that plainly still exists in source, rebuild
  clean before reading it as an API break.

  After the fix, the full reactor is green on Boot 4: **267 tests, 0 failures,
  0 errors, 0 Checkstyle violations, 0 SpotBugs findings** (core 183,
  plugin-api 7, plugin-runtime 16, server 57, desktop 4). The per-key rate
  limiter and its 429 path pass unchanged, so `RequestNotPermitted` handling
  survived both the Boot and the Resilience4j bump.

  **springdoc's major bump was checked at runtime, not by test.** Nothing in
  the suite exercises `/v3/api-docs`, so the packaged jar was booted and probed
  directly: it starts clean, `/v3/api-docs` returns **HTTP 200** with all **10**
  paths documented, and `/swagger-ui/index.html` returns 200. One behavioural
  change worth knowing about downstream: springdoc 3 emits **OpenAPI 3.1.0**
  where 2.x emitted 3.0.x. Nothing in this repo consumes the spec —
  `Code/daedalus-api-dtos.ts` is hand-written against the Java records rather
  than generated — but external clients running codegen against the published
  document will see the version change.

- **Solvers index state by cell id instead of hashing `Point` (D2).**
  `DijkstraSolver` and `AStarSolver` now hold distance / parent / closed state in
  flat arrays addressed through the new `solver.GridIndex` (`row * cols + col`),
  replacing `HashMap<Point,…>` / `HashSet<Point>`. **Measured 1.42–1.72× faster**
  (29–42% less time) over 12 mazes at 80², A/B'd against a faithful copy of the
  previous implementation with identical stats bookkeeping. Behaviour is
  unchanged by construction — queue ordering, neighbour iteration and
  tie-breaking are all identical — and the full suite passes untouched, including
  the assertions that `dial` equals `dijkstra`, that weighted routing picks exact
  known paths, and that A\* matches BFS. This is the item the D3 benchmark
  redirected effort toward.

### Fixed

- **`TremauxSolver` was missing Trémaux's third rule and could not solve mazes
  with loops.** The implementation carried only "never enter a twice-marked
  passage" and "prefer the least-marked passage". The rule it lacked — **on
  re-entering a junction you have already stood on, having arrived along a
  previously unmarked passage, turn straight back** — is the one that retires
  that passage and guarantees a retreat route stays open. Without it the walk
  strands itself: it reaches a cell whose every passage is already twice-marked
  while the goal sits unvisited elsewhere. The old code read that state as
  "unreachable" and returned an empty path, under a comment asserting it was
  *"impossible on connected maze"*.

  It was not impossible. Measured at 20² over 40 seeds per setting:

  | braid factor | mazes failed (old) | mazes failed (fixed) |
  |---|---|---|
  | 0.0 (perfect) | 0 / 40 | 0 / 40 |
  | 0.25 | **19 / 40** | 0 / 40 |
  | 0.5 | **20 / 40** | 0 / 40 |
  | 1.0 | **10 / 40** | 0 / 40 |

  BFS finds a path on every one of those grids, so the mazes were plainly
  solvable. Only perfect mazes were ever safe — a spanning tree has no loop to
  strand you — and **every fixture in the suite was a perfect maze**, which is
  why 183 passing tests never saw it. `TremauxSolver` had no test of its own at
  all until now; the new `TremauxSolverTest` braids deliberately and asserts the
  walk is a legal traversal (starts at start, ends at goal, never crosses a
  wall) across four generators and four braid factors.

  Perfect-maze behaviour is unchanged: 64/64 A/B fixtures produce a walk
  identical to the previous implementation's, since a tree never triggers the
  restored rule.

- **`LandmarkHeuristic` was inadmissible on weighted grids, so A* returned
  suboptimal routes (ADR-001 item 4).** The heuristic stored BFS **hop counts**
  regardless of the grid's costs. Hop counts bound cost from below only while
  every edge costs at least one hop's worth, so the class documented a "keep
  weights `>= 1.0`" rule — which `WeightedMazeGrid.setWeight` never enforced
  (it accepts any non-negative value). Violate it and A* still returns a path;
  it just isn't the cheapest one.

  Measured on twelve fully-braided 24² mazes with weights drawn from
  `[0.05, 0.35]`:

  | | before | after |
  |---|---|---|
  | cells where `h` exceeded true cost | **575 / 576** | **0 / 576** |
  | worst over-estimate (true distance ≈ 32) | **132.1** | 0 |
  | seeds where A* beat by Dijkstra on cost | **12 / 12** | **0 / 12** |
  | worst excess cost | **+36%** | 0 |

  **Why the suite never caught it:** every existing fixture was a *perfect*
  maze. A spanning tree has exactly one route between any pair of cells, so
  every heuristic — admissible or not — returns it. The defect only becomes
  reachable once the topology has redundancy, which is why these tests braid
  the maze first, and why it matters: braided multi-path meshes are precisely
  what the LoadBalancer integration guide tells users to build.

  `precompute` now chooses its metric from the grid rather than assuming.
  Uniform-cost grids keep the BFS fields (O(V + E) per landmark). Any grid
  carrying a non-`1.0` weight gets Dijkstra fields **in both directions** — and
  the second sweep is not redundancy. `MazeGrid` charges the weight of the cell
  being *entered*, so `d(a,b) − d(b,a) = w(b) − w(a)`: the graph is directed
  even though its passages are not, and the familiar symmetric
  `|d(L,b) − d(L,a)|` bound quietly assumes otherwise. Weighted mode uses the
  directed pair `d(L,t) − d(L,s)` and `d(s,L) − d(t,L)`, each of which follows
  from the triangle inequality without a symmetry assumption.
  `MazeMetricsWeightedDistanceTest` asserts the two sweeps genuinely disagree,
  so nobody deletes one as duplication.

  The fix is also a win, not just a tax: on 64² braided weighted topologies A\*
  with the corrected heuristic uses **5.79× fewer expansions and searches 1.9×
  faster** than plain Dijkstra. Precompute costs ≈ 8 ms per topology against
  ≈ 2 ms for a single Dijkstra solve, so it repays after roughly four queries —
  the normal case, since a topology is routed over many times between updates.
  No API change; existing callers get the correction for free.

- **The server reported itself unhealthy (`/actuator/health` → 503) whenever
  Redis was disabled — which is the default.** `spring-boot-starter-data-redis`
  is unconditionally on the classpath, so Boot's `DataRedisAutoConfiguration`
  contributes a `RedisConnectionFactory` even when `daedalus.redis.enabled` is
  `false` and `RedisConfig` is correctly gated off. The health
  auto-configuration then registered an indicator against that factory, its
  `PING` failed, and the failure propagated to the **aggregate** status:

  ```
  "redis": { "status": "DOWN",
             "details": { "error": "...Unable to connect to Redis" } }
  ```

  Everything else — `diskSpace`, `ping`, `livenessState`, `readinessState`,
  `ssl` — was `UP`, and `LeaderboardService` was logging *"in-memory backend
  (Redis disabled or unavailable)"*, i.e. the application was working exactly
  as designed. But `dev` is the default profile and sets
  `daedalus.redis.enabled: false`, so **anyone who cloned the repo and ran it
  had an app that answered its own health check with 503** — precisely the
  signal a load balancer or Kubernetes readiness probe uses to pull an instance
  out of rotation.

  Fixed in `application.yml` by binding the stock indicator to the same flag
  that gates the config:

  ```yaml
  management:
    health:
      redis:
        enabled: ${daedalus.redis.enabled:false}
  ```

  Note this is a *binding*, not a blanket disable — with
  `daedalus.redis.enabled=true` (the prod default) the indicator returns and
  Redis is monitored as before. `RedisHealthBindingTest` pins that direction
  specifically, because the tempting "simplification" to a literal `false`
  would silently blind production monitoring. It also closes the first half of
  the standing BACKLOG item for custom `HealthIndicator`s, with no custom code:
  Boot's indicator was already correct, it was merely registered
  unconditionally.

- **`HilbertCurveGenerator` emitted a forest, not a maze.** Found by auditing all 22
  generators for the spanning-tree contract after the LoadBalancer example produced an
  impossible result. At 32² it yielded **953 edges for 1024 cells — 71 disconnected
  components — with only 66 cells reachable from the origin**. Two causes, both silent: the
  hand-rolled recursive quadrant split did not compose into a real Hilbert curve, so
  consecutive cells were sometimes not adjacent; and when a cell arrived with no visited
  neighbour the code did `if (!candidates.isEmpty())` and simply **skipped carving it**,
  orphaning the cell without any error. The traversal is now the canonical `d2xy` Hilbert
  mapping (guaranteeing adjacency on power-of-two grids), and cells that cannot attach
  immediately are deferred to a repair pass instead of dropped. This mattered beyond
  aesthetics: both vision documents name Hilbert as *the* topology generator for
  LoadBalancer work, so anyone following that advice was routing over a disconnected graph
  and getting empty paths back with no error.
- **The "Hilbert has the best locality" recommendation is measurably false.** Having fixed
  Hilbert's connectivity, the obvious next question was whether it is actually the curve it
  claims to be — connectivity and fidelity are different properties. Measuring **stretch**
  (maze distance ÷ straight-line distance, 20,000 random pairs at 32²) inverts the vision
  document's comparison table:

  | generator | mean stretch | p95 | max | diameter |
  |---|---|---|---|---|
  | **prims** | **2.48** | 5.50 | 57 | 110 |
  | archimedes-spiral | 2.50 | 5.60 | 59 | 95 |
  | gauss | 2.60 | 6.33 | 69 | 123 |
  | morton-curve | 3.06 | 7.50 | 77 | 123 |
  | **hilbert-curve** | **4.62** | 11.00 | 115 | **235** |
  | recursive-backtracker | 9.31 | 25.40 | 289 | 436 |

  Hilbert scores **worse than Morton**, the reverse of the documented ranking, with more than
  double Prim's diameter. The cause is a conflation: the Hilbert *curve* does have excellent
  locality, but `HilbertCurveGenerator` walks the grid in curve order and then attaches each
  cell to a **random visited neighbour** — so the spanning tree is not the curve and inherits
  none of its locality. The vision document and the example now carry the measured table and
  recommend `prims` or `archimedes-spiral` for topology work.
  **The obvious fix was then tested and is worse.** Carving strictly *along* the curve — the
  maximally curve-faithful generator — measures **16.69** mean stretch with a diameter of
  1023, i.e. **3.6× worse than today's version and 6.7× worse than Prim's**. A space-filling
  curve carved end to end is a Hamiltonian *path*, and a path is the spanning tree with the
  worst possible diameter: two cells touching in 2-D can be a thousand steps apart along the
  snake. The relationship is therefore inverted from the intuition — greater curve fidelity
  makes maze locality *worse*, because curve locality is about ordering while maze locality is
  about tree diameter. What actually predicts it is **bushiness**, which the generator
  descriptors already record ("bushy texture; many short branches" for Prim's; long winding
  corridors for the worst performer). Topology generators should be chosen on that axis rather
  than on mathematical pedigree.
- **Connectivity is now verified for every generator.** `PerfectMazePropertyTest` covered
  8 of 22, which is how the above hid. `GeneratorConnectivityTest` asserts the full
  spanning-tree contract (reachable everywhere, exactly `V-1` edges) across all 21
  generators that claim it, plus Hilbert specifically on non-power-of-two and rectangular
  grids where the enclosing-square filter can break curve adjacency. `DungeonGenerator` is
  excluded by contract and keeps its own connectivity test.

### Verified

- **Uniform-spanning-tree cover times measured (G2 + T4).** Aldous-Broder and
  Wilson's sample the *same* distribution — a uniform spanning tree — so they
  differ only in cost, and the audit wanted that shown empirically. At first it
  couldn't be: both generators counted only cells *added to the maze*, which is
  exactly `n` for both, so `MazeStats` was blind to the random walking that
  actually dominates them. Both now count walk steps into `cellsExplored`, and
  the picture is stark (averaged over 7 seeds):

  | cells | Aldous-Broder steps | Wilson's steps | ratio | AB per cell | W per cell |
  |------:|--------------------:|---------------:|------:|------------:|-----------:|
  | 256   | 4,938   | 1,204  | 4.1x | 19.3 | 4.7 |
  | 1,024 | 27,492  | 6,925  | 4.0x | 26.8 | 6.8 |
  | 4,096 | 144,699 | 27,671 | 5.2x | 35.3 | 6.8 |

  Wilson's cost *per cell* stays flat (~5–7) while Aldous-Broder's climbs
  steadily (19 → 35) — the signature of blind cover-time walking versus
  loop-erased hitting-time walking — and the gap widens with size, as theory
  predicts. Locked in `RandomWalkCoverTimeTest`.
- **`GrowthEstimator` caveat found and documented.** Classifying those same
  random-walk series exposed a real limitation in the T1 tool: fitted from a
  *single seed*, Aldous-Broder's label swung between `O(n)` and `O(n^2)` across
  seeds and Wilson's once came back `UNKNOWN`, despite their true behaviour being
  stable and clearly separated once averaged. The javadoc now warns to average a
  randomized metric over several seeds before fitting.
- **DSU certified near-constant amortized (D1).** `util/DSU` already carried both
  optimizations — union by rank *and* two-pass path compression — so no
  production change was needed. Added structural guards that behaviour alone
  can't provide: if someone simplified `find` into a plain root walk, every
  correctness test would still pass while the structure silently degraded from
  inverse-Ackermann to `O(n)`. The new tests read `parent` directly to assert the
  path really is rewritten, and that rank ordering survives (CLRS Ch. 21 + 17).
- **Reservoir-sampled frontier declined (G3).** The idea was to cut frontier
  memory, so the frontier was measured first — using the `maxFrontierSize` the
  generators already record. Randomized Prim's peaks at 561 walls on a 64² maze
  and only 4,866 on a 512² one: **1.9% of cells, about 0.22 MB**, and the share
  *falls* as mazes grow, because the frontier tracks the perimeter of the grown
  region rather than its area. There is no pressure to relieve. Independently,
  the technique doesn't fit: Algorithm R samples one pass over a stream, whereas
  Prim's frontier is live mutable state that must persist across steps, so using
  a reservoir would mean rescanning the grid every step — O(n²) instead of the
  current O(frontier). Noted the real lever if it ever matters: encode each wall
  as one `int` rather than a two-`Point` object, ~10× smaller, no algorithm change.
- **Consistent hashing declined (X4).** The maze cache is a single-process
  bounded map; Redis is wired for the leaderboard, not for sharding mazes. A hash
  ring would be distribution infrastructure for a system that isn't distributed —
  and if it ever becomes one, Redis Cluster already shards by hash slot with
  minimal reshuffling, so doing it in the application would duplicate the
  datastore's mechanism and add a second thing to get wrong.
- **Parallelism trio measured; C1 and C2 declined, C3 reframed.** Generation was
  timed before any thread pool was written: 1.96 ms at 64², 5.01 ms at 128²,
  18.3 ms at 256², 106 ms at 512² (Borůvka). At the sizes this project actually
  serves — ≤128² — generation is **2–5 ms**, which fork/join setup would simply
  consume. The decisive objection is not speed but the contract: `MazeGenerator`
  promises *"same seed ⇒ same maze"*, and `ComplexityAnalyzer`, `GrowthEstimator`
  and much of the suite depend on that determinism; parallel rounds would put it
  at risk to save milliseconds. **C2** falls harder still — after D2 a full
  Dijkstra over an 80² maze runs in under a millisecond, so there is nothing to
  parallelise. **C3** was reframed rather than dropped: its speed rationale dies
  with C1, but quadrant generation with doorways punched through the seams is how
  rooms-and-corridors dungeon layouts get built, and that's a real gap — every
  current generator makes uniform perfect mazes. It belongs in the backlog as a
  single-threaded feature, judged on the layouts it produces.
- **`DeadEndFillingSolver`: a `Stream` removed from the cascade's inner loop.** Profiling put
  this solver second-worst at 14.66 ms, and the cause was not hashing. Its cascade counted a
  neighbour's surviving exits with
  `openNeighbors(n).stream().filter(...).count()` — a full stream pipeline built once per
  neighbour of every filled cell, which on a recursive-backtracker maze (almost entirely dead
  ends) is the hottest line in the solver. Replaced with a plain counting loop.
  Measured on the cascade phase in isolation, with both variants asserted to fill an identical
  set of cells: **1.13× / 1.24× / 2.77×**. The spread is wide because stream pipelines are
  exactly the shape JIT behaviour varies most on, so the honest reading is "consistently
  faster, magnitude unstable" rather than a headline multiple. Worth recording that the first
  attempt at this benchmark was **invalid** — it compared the legacy cascade alone against the
  full new solver including its BFS phase, which measures nothing; the numbers above come from
  the corrected like-for-like version.
- **Solver costs profiled before optimising, which redirected the work entirely (ADR-001).**
  With six solvers still using `HashMap`/`HashSet`, the plan was to move them onto the graph
  seam. Timing them first over 12 mazes at 80² changed the answer:

  | solver | time | | solver | time |
  |---|---:|---|---|---:|
  | wall-follower | 2.55 ms | | bidirectional | 6.94 ms |
  | bfs | 2.70 ms | | dead-end-filling | 14.66 ms |
  | dial | 4.83 ms | | tremaux | 20.01 ms |
  | dfs | 5.26 ms | | **ida-star** | **875.91 ms** |

  **IDA\* costs ~300× BFS and 44× the next-worst solver.** De-hashing it would have been
  rearranging deck chairs: the cost is inherent to iterative deepening, which re-searches from
  scratch each pass under a slightly larger f-bound — with unit costs the bound rises by 1 per
  pass, so a maze with a path hundreds of steps long is re-explored hundreds of times.
  The fix turned out to be a heuristic already built for another purpose. Swapping Manhattan
  for `LandmarkHeuristic` (ALT): **342.7 ms → 8.4 ms, a 41× speedup**. The same swap saves A\*
  only ~55% of expansions; IDA\* gains far more because re-expansion multiplies every saving.
  No code changed — `IDAStarSolver` already accepts a heuristic. Its javadoc now carries the
  measurements and says plainly when to use it: ALT when a maze is solved repeatedly, A\*/BFS
  for one-shot queries (ALT's precompute costs about as much as just solving the maze), and
  IDA\* itself only when `O(d)` memory is the actual constraint. It is a memory-optimised
  algorithm, not a time-optimised one, and the default heuristic makes that trade steeply.
- **d-ary heap benchmarked and declined (D3).** A 4-ary heap was measured against
  `java.util.PriorityQueue` inside a real Dijkstra loop (12 mazes at 80², warmed
  up, three reps) and came in at −1.5% / −8.5% / −1.8% — inside the noise, with a
  d=2 control swinging 11.8ms→22.7ms across reps. The heap simply isn't the
  bottleneck: the loop is dominated by `HashMap`/`HashSet` lookups on `Point`
  keys. No code was shipped rather than add a placebo optimization. The follow-up
  measurement is the useful part — swapping those maps for flat arrays indexed by
  `row * cols + col` ran **1.47–2.00× faster** on the identical workload, so idea
  **D2** was upgraded to High impact and is now the top performance item.
- **Bidirectional termination audited (S3).** `BidirectionalSolver` stops at the
  first frontier touch, and textbooks warn that this can return a path one step
  longer than optimal. Rather than assume it, the concern was measured: across
  **4,320** randomized braided mazes (sizes 6–20, three braid factors, random
  start/goal pairs) it never disagreed with BFS on path length, so the solver was
  left alone and the termination rule documented instead. A braided-maze sweep
  now lives in the suite as a regression guard — worth noting the previous tests
  could never have caught this, since a perfect maze has only one route.

### Security (2026-07-19)

- **STOMP `CONNECT` frames are now authenticated.** HTTP security guarded the
  `/ws/**` upgrade under `prod`, but nothing inspected STOMP frames, so the
  messaging layer had **no notion of who was connected**. Two consequences: a
  deployment exposing the endpoint without that HTTP rule — a misconfigured
  profile, or a proxy terminating the upgrade — had no second line of defence,
  and there was no principal on which any per-destination rule could ever be
  built. `StompAuthChannelInterceptor` validates the bearer token from the
  `CONNECT` frame's native headers and attaches a `Principal` carrying the JWT
  subject, sharing `JwtTokenService`'s decoder so issuance and verification
  cannot drift.

  Required under `prod`, advisory elsewhere — matching how `SecurityConfig` and
  `ProdSecurityConfig` already split the HTTP surface, so a dev or embedded
  desktop client still connects without minting a token. **A token that is
  present but invalid is refused in every profile**, including the permissive
  ones: "no credentials" and "bad credentials" are different situations, and
  only the first is something a relaxed profile should wave through.

  **Scope, stated plainly: this is authentication, not authorization.** A client
  can still subscribe to another user's frames. The broker's destinations are
  not scoped to an owner, and nothing in the domain records which subject owns a
  session, so "may this principal subscribe here?" is not yet answerable —
  closing that needs session ownership modelled first. The BACKLOG entry has
  been rewritten to say so rather than marked done.

  Per-frame validation was deliberately omitted: the principal is established
  once at `CONNECT` and carried on the session, so re-decoding the token on
  every `SEND` would cost thousands of verifications for no extra guarantee.
  The trade-off is that a connection outlives its token's expiry.

- **Per-key rate-limiter buckets are now bounded — and bounding them carefully.**
  The interceptor created a Resilience4j instance per distinct caller key and
  never evicted it, so anyone able to mint keys — forged subjects, or forged
  source IPs when `daedalus.ratelimit.trust-forwarded-header` is on — could grow
  the `RateLimiterRegistry` without limit. Buckets now live in a Caffeine cache
  capped by `daedalus.ratelimit.max-keys` (default 10 000) and expiring on
  `daedalus.ratelimit.idle-ttl` (default 10 minutes).

  **The obvious implementation would have been a bypass.** Evicting a bucket a
  caller has already drained hands them a full budget the moment they return, so
  a naive LRU turns "cycle keys fast" into "no rate limit at all" — trading a
  memory-exhaustion bug for an authentication-adjacent one. Each bucket's
  effective TTL is therefore raised to at least its own `limitRefreshPeriod`:
  past that point it would have refilled anyway, so discarding it is
  unobservable. That requires a per-entry Caffeine `Expiry` rather than a
  cache-wide `expireAfterAccess`, since base limiters configure different refresh
  periods (`mazeGenerate` and `authLogin` do not agree). Size-based eviction
  keeps the property too — Caffeine evicts approximately LRU, so a key flood
  discards the attacker's own idle entries rather than an active caller's
  drained bucket.

  Bucket creation also moved off `RateLimiterRegistry.rateLimiter(name, config)`
  to standalone `RateLimiter.of(...)`, because the registry retains every
  instance it creates — which is the leak being closed.

  Two things caught during the work, both by tests that already existed for
  other reasons. Widening `RateLimitProperties` broke four call sites at compile
  time (good — loud). Adding a convenience constructor then gave the record two
  constructors, and Spring's binder will not choose between them: it looks for a
  no-arg constructor, fails, and **the entire application context stops
  starting**. `ApplicationSmokeTest` — added earlier the same day precisely
  because no test booted the real context — turned that into a clear failure
  instead of a broken deployment. Fixed with an explicit `@ConstructorBinding`.

### Security

- **Per-key rate limiting on the throttled endpoints.** The three limiters
  (`mazeGenerate`, `mazeSolve`, `authLogin`) were global — a single
  Resilience4j bucket shared across every caller, so one noisy client could
  spend everyone else's quota (and one IP could burn the whole `authLogin`
  brute-force budget). Replaced the method-scoped `@RateLimiter` annotations
  with `@PerKeyRateLimit(...)` plus a `PerKeyRateLimitInterceptor` that
  resolves a caller key — authenticated subject (`Authentication.getName()`),
  else client IP — and throttles each key against its own bucket, cloned from
  the named instance's config in the `RateLimiterRegistry`. The YAML
  instances now serve as per-caller *templates*. `X-Forwarded-For` is trusted
  only when `daedalus.ratelimit.trust-forwarded-header` is set (off by
  default; on in `application-prod.yml`, which runs behind an ingress) so a
  direct client can't spoof the header to mint a fresh bucket per forged IP.
  The `429` wire contract is unchanged: `ApiExceptionHandler` collapses the
  composite instance name (`mazeGenerate::ip:…`) back to the base
  `mazeGenerate` for the body's `limiter` property, so no caller IP or subject
  leaks into the response, and `Retry-After` still resolves from the base
  instance's refresh period. New code lives under
  `com.daedalus.server.ratelimit` (`PerKeyRateLimit`, `RateLimitNaming`,
  `RateLimitKeyResolver`, `PerKeyRateLimitInterceptor`) plus
  `RateLimitProperties` / `RateLimitWebConfig` in `…server.config`; covered by
  18 new tests (naming round-trip, key resolution, per-key bucket isolation,
  and an end-to-end MockMvc 429 path). Clears the "per-key rate limiting" item
  from `BACKLOG.md`.

### Infrastructure

- **CI fixed and verified green.** Run #1 failed because `ci.yml` ran
  `mvn clean verify`, which never installs reactor artifacts into `~/.m2`,
  so the standalone `examples/biome-plugin` build couldn't resolve
  `daedalus-plugin-api:1.0.0-SNAPSHOT`. Switched the reactor step to
  `clean install` (commit `2519a1f`, 2026-07-02); also bumped actions for
  the Node 24 cutover (`checkout@v6`, `setup-java@v5`, `upload-artifact@v7`)
  and fixed the README badge URL. Run #2 (2026-07-03) passed — 56s total,
  reactor + biome-plugin both green.
- **`.gitattributes` added.** `* text=auto` with explicit `eol=crlf` for
  `*.bat`/`*.cmd`, `eol=lf` for `*.sh`, and `binary` for PDFs, images, and
  archives. Ends the CRLF churn that made untouched files (`.gitignore`,
  `_migration/migrate.bat`) show up as fully-rewritten phantom diffs on
  Windows. Tree renormalized with `git add --renormalize .`.
- **`.gitignore` cleaned.** Removed two literal `ECHO is on.` lines — an
  artifact of the batch script that originally generated the file (`echo`
  with no argument prints its own status instead of a blank line).
- **Coverage.** JaCoCo agent + per-module report wired into the reactor at
  `verify`. CI regenerates `.github/badges/jacoco.svg` on pushes to main
  (cicirello/jacoco-badge-generator) and commits it back `[skip ci]`; README
  shows the badge next to CI status.
- **Static analysis gates.** Checkstyle (minimal hygiene ruleset,
  `config/checkstyle.xml`, runs at `validate`) and SpotBugs (medium threshold,
  runs at `verify`) now fail the build. First run over the codebase surfaced
  and fixed four real issues: an unused import in `JwtTokenService`, a dead
  local (`ideal`) in `GameSessionService.complete`, a swallowed exception on
  classloader close in `PluginManager.shutdownAll` (now debug-logged), and a
  missing null guard on Micrometer’s `@Nullable Timer.record` return in
  `MazeGenerationService.generate`. Intentional-design findings
  (EI_EXPOSE_REP on events/DTOs/DI, CT_CONSTRUCTOR_THROW, MS_EXPOSE_REP on
  the static context accessors) are excluded with per-block justifications
  in `config/spotbugs-exclude.xml`.
- **Dependabot.** Weekly update PRs for the Maven reactor, the standalone
  biome-plugin pom, and the GitHub Actions used by the workflows; minor/patch
  bumps grouped into a single PR.
- **Issue & PR templates.** Bug report and feature request forms
  (`.github/ISSUE_TEMPLATE/`) plus a PR checklist template.
- **Container image.** Multi-stage `Dockerfile` (Maven build layer → slim
  Temurin 21 JRE, non-root user) for `daedalus-server`; the release workflow
  gained a job that publishes `ghcr.io/richeyworks/daedalus2:{version,latest}`
  on every `v*` tag.
- **CHANGELOG de-binarified.** The 2026-05-05 entry documenting OneDrive
  null-byte corruption contained a literal `\0` character, which made grep
  and diff tools treat this whole file as binary. Replaced with the escaped
  text form.

## [Unreleased] — 2026-05-11

**Reference plugin + CI + core consolidation.** Four BACKLOG items closed
in this pass: the worked example plugin (`BiomeGeneratorPlugin`), GitHub
Actions CI, the Lightning policy decision, and the final newest-pick
generator (Recursive Backtracker) folded onto the shared Growing-Tree
engine. The example plugin lives in `examples/biome-plugin/` (deliberately
not part of the main reactor so `mvn clean verify` at the root keeps its
current scope) and demonstrates every interesting touchpoint of the SPI:
manifest declaration, algorithm registration, programmatic event
subscription, and stop-time disarm. The core changes finish what the
2026-05-07 Growing-Tree unification started — every member of the
newest / oldest / random / norm / state-machine family now plugs into
`GrowingTreeEngine` through a `GrowingTreePolicy`, with no bespoke loops
left in the catalog.

### Added

- **`examples/biome-plugin/`** — reference plugin module. Registers two
  themed generators (`forest-biome`, `desert-biome`) against
  `GeneratorRegistry` and subscribes to `MazeGeneratedEvent` to log a
  one-line summary per generation. Both generators are written from
  scratch against the public SPI — no reach-ins to package-private engine
  internals — so the example doubles as a from-zero tutorial for plugin
  authors.

  - `ForestBiomeGenerator` — recursive backtracker with a weighted
    vertical-first carve order. With probability 0.7 the two vertical
    directions occupy slots 0–1 of the per-cell try-order; with the
    complementary probability the two horizontal directions take those
    slots. Within-pair order is uniformly random on each side. Long
    trunks, short side branches. Perfect maze (single component, no
    cycles); seed-deterministic.
  - `DesertBiomeGenerator` — Sidewinder variant with a 1/3 run-close
    probability (vs. Sidewinder's 1/2). Longer horizontal corridors.
    Perfect maze; seed-deterministic.
  - `BiomeGeneratorPlugin` — extends `AbstractPlugin`. Subscribes to
    `MazeGeneratedEvent` by looking up Spring's well-known
    `ApplicationEventMulticaster` bean and calling
    `addApplicationListener(...)` on it. Plugin instances are loaded via
    `ServiceLoader` (not by the Spring bean factory), so `@EventListener`
    annotations on plugin classes are silently ignored; programmatic
    registration is the supported path. The listener unwraps
    `PayloadApplicationEvent` manually — `PluginEvent` is a Daedalus-domain
    POJO that doesn't extend `ApplicationEvent`, so Spring wraps it on
    publish; `@EventListener` does this automatically via its method-adapter
    layer, but a raw `ApplicationListener` doesn't. An `AtomicBoolean armed`
    flag is flipped to false in `stop()` to neutralise the listener; Spring's
    `removeApplicationListener` would also work, but the flag keeps the
    lifecycle methods one line each without retaining the listener reference
    as plugin state.
  - `BiomeGeneratorsTest` — perfect-maze invariant + seed-determinism +
    descriptor smoke tests for both generators.
  - `META-INF/services/com.daedalus.plugin.MazePlugin` — ServiceLoader
    entry so the plugin is discovered by the host's `PluginManager`.
  - `examples/biome-plugin/README.md` — build / run instructions plus
    the why-not-`@EventListener` explanation.

- **`examples/run-with-biome.sh`** — one-shot demo script. Installs
  `daedalus-plugin-api` into the local Maven repo, builds the plugin
  JAR, stages it in a `mktemp -d` plugin directory, then boots
  `daedalus-server` with `daedalus.plugins.directory` pointed at that
  directory. Forwards any extra arguments as Spring Boot run arguments.

- **`.github/workflows/ci.yml`** — `mvn -B verify` on push/PR for
  `main`. Java 21 Temurin via `actions/setup-java@v4` with built-in
  Maven cache. Locale + timezone forced to `en_US.UTF-8 / UTC` so any
  format-sensitive test is deterministic across runners. Builds the
  reference plugin in a follow-on step so the example doesn't silently
  rot. Concurrency group cancels in-flight runs on rapid pushes.

- **`.github/workflows/release.yml`** — tag-driven release pipeline.
  Triggers on `v*` tags; builds the reactor (`-DskipTests` since CI
  already validated the tip), builds the example plugin, extracts the
  matching CHANGELOG section as release notes, and publishes a GitHub
  Release with the server's `-exec.jar` and the plugin JAR attached.
  `softprops/action-gh-release@v2` handles the upload. Tags with
  `-rc` / `-beta` / `-alpha` suffixes are marked prerelease.

- **`GrowingTreePolicies.newestWithNormJump(double pJump)`** — new
  composed policy: mostly pick the newest cell (RB-style long corridors),
  with probability `pJump` jump to the active cell with the largest
  quadratic norm (a fork toward the high-norm corner). Endpoints
  short-circuit to the underlying singletons — `pJump = 0.0` returns
  `newest()`, `pJump = 1.0` returns `quadraticNorm()` — so the seed
  consumption pattern at the endpoints matches the underlying policy
  byte-for-byte. Used by `LightningGenerator` (see below); also generally
  available to plugin authors who want the same texture.

- **`GrowingTreePoliciesTest`** — five new unit tests covering
  `newestWithNormJump`: equivalence to `newest()` at `pJump=0.0`,
  equivalence to `quadraticNorm()` at `pJump=1.0`, seed determinism in
  the mixed regime, branch-coverage at `pJump=0.5` (both component
  policies fire over a small sample), and bounds-rejection for NaN /
  out-of-range probabilities.

### Changed

- **`LightningGenerator`** — given a genuinely different selection policy
  to restore its visual identity. The 2026-05-07 unification collapsed
  Lightning onto Gauss (both delegated to `quadraticNorm()`); per the
  BACKLOG resolution, Lightning now uses
  `GrowingTreePolicies.newestWithNormJump(0.15)` — mostly RB-like long
  corridors with a 15% chance per turn of forking toward the highest-norm
  active cell. Produces a jagged "lightning bolt with branches" texture
  distinct from every other generator in the catalog. **Seed-mapping
  change:** the `seed → maze` mapping for id `"lightning"` changed in
  this pass; pinned seeds from before 2026-05-11 will resolve to
  different mazes. The displayName drops the "(Fast)" qualifier since the
  hand-tuned fast path is long gone.

- **`RecursiveBacktrackerGenerator`** — folded onto `GrowingTreeEngine`
  via `GrowingTreePolicies.newest()`. The pre-refactor implementation
  maintained its own stack-of-cells DFS with a Fisher–Yates shuffle of
  `Direction.values()` and an in-order scan for the first unvisited
  neighbour; the engine's slow-path enumeration uses
  `Collections.shuffle` on a `List<Direction>`. For size-4 lists
  `Collections.shuffle` takes the fast path and emits exactly the same
  Fisher–Yates sequence (`nextInt(4), nextInt(3), nextInt(2)`).
  **Seed-mapping: preserved.** The original BACKLOG note had worried
  about a different `Random` consumption pattern; a side-by-side audit
  of the pre- and post-refactor code confirmed identical bit consumption
  end-to-end (same start-cell call, same shuffle output, the `newest()`
  policy consumes zero bits). Clients with pinned RB seeds resolve to
  the same maze before and after this refactor. The equivalence is
  locked by the new
  `RecursiveBacktrackerEngineEquivalenceTest` (parameterised over five
  `(rows, cols, seed)` combinations including tall, wide, and non-square
  grids). This was the last newest-pick generator carrying its own loop
  — the entire Growing-Tree family now lives behind one engine.

- **`README.md`** — adds a CI badge, points the "Writing a plugin"
  section at `examples/biome-plugin/`, and lists `examples/` in the
  workspace-layout overview.
- **`BACKLOG.md`** — removes the closed "Reference plugin:
  `BiomeGeneratorPlugin`" item and rewrites the stretch-goal
  "GitHub Actions CI" entry to reflect that the CI + release pieces
  are now done; only the optional coverage-upload step remains. The
  entire "Refactoring (core)" section is dropped — both items
  (Lightning's fate and RB on `GrowingTreeEngine`) shipped in this
  pass and the section had no other entries.

---

## [Unreleased] — 2026-05-07

**Four BACKLOG items closed in one pass:** DSU extraction, Growing-Tree policy
unification, REST input validation, and per-method rate limiting on write
endpoints. All four were called out in `BACKLOG.md` (server hardening + core
refactor sections); each now has a real implementation plus tests, and the
matching backlog entries have been removed.

**Desktop visualizer is now actually runnable.** The `daedalus-desktop`
module shipped with `DaedalusLauncher` + `DaedalusPrimaryStage` referencing
a `/ui/main.fxml` and a `Theme` SPI that had no implementations and no
resources directory — the app would have crashed on startup with
`NullPointerException: main.fxml missing from /resources/ui`. This
release fills in the missing pieces so
`mvn -pl daedalus-desktop javafx:run -am` opens a window and draws mazes:

- **`/ui/main.fxml`** — `BorderPane` with a top toolbar (generator
  picker, rows / cols spinners, seed field, Generate button), a center
  `Pane` holding the rendering `Canvas`, and a bottom status bar.
  Controller wired via Spring's bean factory.
- **`/ui/cosmic.css`** — paired stylesheet for the Cosmic theme.
- **`MainController` (`@Component`)** — populates the generator
  and solver dropdowns from the live `GeneratorRegistry` and
  `SolverRegistry`, runs generations and solves through
  `MazeGenerationService` / `MazeSolverService` (so plugin events and
  metrics fire exactly as they do for the REST surface), renders the
  resulting `MazeGrid` via `toTileGrid()` onto the canvas with
  theme-driven colors, and re-renders on window resize. Three layers
  on every paint: tile grid (passages / walls / start / goal); solve
  path overlay in `theme.path()` (drawn under endpoint markers so
  start and goal stay visible, with connector tiles between
  consecutive path cells so the trace renders continuously rather than
  as dots); and finally the movable player marker as a circle in
  `theme.player()`. Reset puts the player back at start without
  re-running the generator. Arrow keys and WASD walk the player
  through open walls (closed walls silently block); reaching the goal
  flips the marker to `theme.path()` color and announces the win in
  the status bar.
- **`CosmicTheme` (`@Component implements Theme`)** — first concrete
  theme: dark navy + cyan + magenta palette; matches the
  `daedalus.ui.theme: cosmic` default in `application.yml`.

Note: `DaedalusLauncher` boots the full Spring context including the
embedded servlet container, so running the desktop client also exposes
the REST API on port 8080. Useful for debugging; potentially noisy if
something else is bound to that port.

### Added

- **`com.daedalus.util.DSU` — shared union-find utility.** Single
  implementation with both standard optimizations (path-compressing two-pass
  `find`, union-by-rank with `byte[]` ranks) over a fixed `int[]` keyspace.
  Maze generators that work in 2-D coordinates flatten via
  `r * cols + c`. Replaces the inline `HashMap<Point, Point>` DSUs that
  used to live in `KruskalsGenerator` and `BoruvkasGenerator` — same
  asymptotic complexity, no more boxing on the hot inner loop. The API
  also surfaces `sizeOf(int)`, `largestComponent()`, and
  `isFullyConnected()`; the first two are backed by an `int[]
  componentSize` array maintained at the root on every union plus a
  running `largestSize` max, so both queries stay O(1). `DSUTest` (unit
  + randomized stress against an oracle, cross-checking connectivity *and*
  size bookkeeping) locks in the invariants.

- **Kruskal's now early-exits when the spanning tree is complete.**
  `KruskalsGenerator` checks `dsu.isFullyConnected()` at the top of the
  edge-iteration loop and breaks when true, sparing the shuffle's
  cycle-creating tail (~half of the original edge list on a typical
  maze). Output is bit-for-bit identical for the same seed — the skipped
  edges were all guaranteed-no-op `union` calls; we just stop visiting
  them.

- **`GrowingTreePolicy` SPI + `GrowingTreeEngine` shared loop.** The
  Growing-Tree family (`GrowingTreeGenerator`, `LightningGenerator`,
  `GaussGenerator`, `TuringGenerator`) used to repeat the same
  frontier-list / pick-cell / carve-or-drop skeleton four times with only
  the cell-selection rule differing. Extracted: each generator now passes
  a one-method `GrowingTreePolicy` lambda (or stateful object, in
  Turing's case) into `GrowingTreeEngine.run(...)`. Existing public
  generator classes are kept as thin adapters for backward compatibility
  — callers that hold `new GaussGenerator()` references compile and
  behave identically. Named factories live in `GrowingTreePolicies`
  (`newest`, `oldest`, `random`, `middle`, `mixed(double)`,
  `quadraticNorm`, `turingMachine`); the four registered generators
  consume them instead of inlining lambdas, and the stateful
  Turing-machine policy was moved out of `TuringGenerator`'s private
  inner class into the shared bucket. `GrowingTreePoliciesTest` pins
  each factory's contract directly (synthetic active lists + fixed-seed
  `Random`).

- **`OldestPickGenerator` (id `oldest-pick`).** New built-in: a
  Growing-Tree variant that always expands the head of the active list,
  giving BFS-shaped wave-front growth — short branches, "expanding ring"
  texture, the visual opposite of Recursive Backtracker's long winding
  rivers. Existence as a five-line class plus one line in
  `AlgorithmConfig.builtInGenerators()` is the demonstration that the
  engine + policy extraction pays off. Covered by
  `PerfectMazePropertyTest`.

- **REST input validation on every write endpoint.** `GenerateRequest`,
  `MoveRequest`, and `LoginRequest` carry `jakarta.validation`
  annotations (`@NotBlank`, `@Pattern` for IDs, `@Min`/`@Max` for grid
  dimensions, `@Size` for usernames/passwords). `MazeController` is
  `@Validated` (enables param-level constraints on path / query) and
  every body parameter is `@Valid`. `ApiExceptionHandler` translates
  `MethodArgumentNotValidException` and `ConstraintViolationException`
  into RFC 7807 `ProblemDetail` 400 responses with a sorted
  `fieldErrors` map keyed by the offending field — replaces the
  previous "malformed payload returns 500" behavior that was called out
  in the audit. New: `MazeControllerValidationTest` (boundary cases per
  field) and `AuthControllerValidationTest` (login DTO).

- **`@AlgorithmId` composite constraint.** New annotation in
  `com.daedalus.api.validation` that bundles
  `@NotBlank + @Pattern("^[a-z0-9][a-z0-9-]{0,63}$")` with
  `@ReportAsSingleViolation`. Single source of truth for the algorithm
  / solver id regex; `GenerateRequest.generatorId` and
  `MazeController.solve`'s `solverId` path variable both wear it now,
  replacing the duplicated `@NotBlank @Pattern(...)` blocks. The
  composite's message is preserved verbatim from the prior
  `@Pattern` message so existing test assertions still hold.

- **`@NonNegativeCoordinate` constraint on `MoveRequest.to`.** Closes
  the documented validation gap where a request body with a negative
  `row` or `col` slipped past the API surface and silently flipped
  `GameSessionService#tryMove` to `false` (returning `200 OK`
  body=`false` instead of a structured 400). The validator lives in
  `daedalus-server`'s validation package and reaches into `Point` via
  its public accessors, so `daedalus-core` stays framework-free per its
  existing rationale. Upper-bound and adjacency checks remain owned by
  `tryMove` (which has access to the grid dimensions and current
  position); validation only catches the structurally impossible. New
  test cases in `MazeControllerValidationTest` cover null `to`,
  negative `row`, and negative `col`.

- **Resilience4j rate limiting on the three write endpoints.** Three
  named `@RateLimiter` instances configured in `application.yml`:
  `mazeGenerate` (30/min), `mazeSolve` (60/min — solving is cheaper),
  and `authLogin` (10/min — brute-force guard). `application-test.yml`
  overrides with very generous limits so MockMvc tests don't trip over
  themselves; `application-prod.yml` tightens `authLogin` further. All
  three configured `timeout-duration: 0` — fail fast with
  `RequestNotPermitted` rather than queueing.
  `ApiExceptionHandler#onRateLimited` maps the exception to a
  `429 Too Many Requests` with a `Retry-After` header carrying the
  limiter's actual `limit-refresh-period` (rounded up to whole seconds,
  floored at 1 per RFC 9110) and a problem-detail body whose `limiter`
  property names which instance was exhausted, so clients can
  differentiate "your generate quota is gone" from "your solve quota is
  gone" without us baking business meaning into HTTP.
  `ApiExceptionHandler` now takes an optional `RateLimiterRegistry` via
  an `@Autowired` constructor (Resilience4j Spring Boot autowires it
  from YAML); tests using the no-arg constructor see the previous
  1-second floor as the fallback. New:
  `ApiExceptionHandlerRateLimitTest` — five unit tests against the
  handler in isolation, including the registry-aware path
  (verifies `Retry-After: 60` for a 1-minute refresh, `Retry-After: 1`
  for a 250 ms refresh and for unregistered limiter names).

### Changed

- **`LightningGenerator`'s seed → maze mapping is no longer bit-for-bit
  identical to its pre-refactor output.** Pre-refactor Lightning used a
  faster array-based shuffle that filtered out-of-bounds neighbors
  *before* shuffling — that consumed `Random` differently than the other
  three Growing-Tree variants. The unified `GrowingTreeEngine` uses the
  slow path (shuffle all four directions, then iterate and bounds-check)
  so that `GrowingTreeGenerator`, `GaussGenerator`, and
  `TuringGenerator` all stay bit-for-bit identical to their previous
  output. Lightning was the odd one out, and unification + reproducibility
  across the family was preferred over Lightning's marginal allocation
  savings. Anyone pinning a Lightning seed should regenerate.

### Caveats

- **Rate limits are global, not per-IP / per-subject.** Resilience4j's
  `@RateLimiter` annotation is method-scoped — a single bucket shared by
  all callers. A new BACKLOG entry has been kept ("Per-key rate
  limiting") to track the upgrade to a `RateLimiterRegistry` plus
  `HandlerInterceptor` keyed off the request principal / IP.

## [Unreleased] — 2026-05-06

**Cost-aware routing landed.** New `WeightedMazeGrid` adds per-cell entry
costs, and `DijkstraSolver` / `AStarSolver` now read those costs through
a polymorphic `MazeGrid#weightOf(Point)` hook (default `1.0`). Plain
`MazeGrid` instances are unchanged behaviourally, so existing solver
callers and the perfect-maze property test keep working untouched. Two
new core test files (`WeightedMazeGridTest`, `WeightedRoutingTest`) lock
in defaults / validation and prove that on a two-corridor maze the
solvers detour around a heavily-weighted cell and stay on the short
corridor when the penalty is modest.

This is the LoadBalancer-Lab integration angle from the Vision docs:
load on a node = cost to route through it. The same pattern works for
latency, terrain cost, swamp tiles, etc. Edge cost from `u` to `v` is
defined as `weightOf(v)`; the start cell is never charged because the
solver begins there rather than entering it.

**Multi-JAR discovery test restored and broadened.** `PluginManagerJar
DiscoveryTest` had a 4th test method (`discover_withMu...`) that lost
its body — the file was truncated at line 199 and broke the reactor.
Reconstructed as `discover_withMultipleJars_isolatesEachInItsOwnClass
loader`, plus a new `OtherSamplePlugin` test fixture so two genuinely
different plugins can coexist in the registry. Test asserts both jars
reach the registry under distinct ids, that `externalLoaders` holds
two distinct `URLClassLoader` instances, and that each loader's URL
list points at exactly one of the two jars we wrote (not collapsed
into a single loader). The "plugin.getClass().getClassLoader() is the
URLClassLoader" assertion is intentionally absent — Maven Surefire's
parent-first delegation lets the parent CL define the class because
the test fixtures are on the test classpath, so we probe the invariant
through `getURLs()` instead.

**Plugin-runtime audit gaps closed.** Three more tests added to
`PluginManagerJarDiscoveryTest`:

- `discover_ignoresNonJarFiles_butStillLoadsJarsBesideThem` — drops a
  real plugin JAR alongside `.txt` / `.yml` / `.zip` files plus a
  jar-named subdirectory; only the JAR is processed.
- `discover_jarWithNoServiceFile_tracksLoaderButRegistersNothing` —
  documents that a JAR with a class file but no `META-INF/services`
  entry produces zero plugins yet still has its `URLClassLoader`
  tracked, so `shutdownAll()` can release the file handle on Windows.
- `discover_corruptJar_publishesPluginFailedEvent_discoverPhase` —
  builds a JAR whose service file names a missing class and asserts
  the failure surfaces as a `PluginFailedEvent.Phase.DISCOVER`.

### Fixed

- **`PluginManager.loadJar()` now catches `Throwable`, not just
  `Exception`.** The original `catch (Exception e)` couldn't catch
  `ServiceConfigurationError` (which extends `Error`), so the most
  common discovery failures — service file naming a missing class,
  wrong type, plugin constructor throwing — would crash `discover()`
  outright instead of publishing a `PluginFailedEvent.Phase.DISCOVER`.
  The event-publication branch was effectively unreachable. Widening
  the catch to `Throwable` aligns this method with how `bootAll()` and
  `shutdownAll()` already treat lifecycle failures (each catches
  `Throwable`) and makes the "operators see plugin failures via
  `/topic/plugins/failures`" guarantee actually hold for discovery.

- **OneDrive sync corruption — 10 server-module files repaired.**
  A reactor build surfaced compile errors in six files with the
  unmistakable pattern of an interrupted OneDrive sync: trailing null
  bytes (`\0`) on some, mid-method truncation on others. A full
  sweep then found four more in the same state that the compiler
  hadn't reached yet because the build aborted early.

  **Cleanly recovered (trailing nulls only — surviving content is
  byte-identical to the pre-corruption file):**
  - `daedalus-server/.../config/OpenApiConfig.java`
  - `daedalus-server/.../controller/MazeWebSocketController.java`
  - `daedalus-server/.../test/.../MazeWebSocketControllerPluginFailedTest.java`

  **Reconstructed (truncation, but the missing tail was small or
  obvious from surrounding context):**
  - `daedalus-server/.../controller/MazeController.java` — initial
    pass added only the missing closing brace because the surviving
    tail looked clean; a follow-up build error revealed two more
    methods had been silently lost: the `GET /api/v1/leaderboard`
    endpoint (present in the class Javadoc but not the body) and a
    private `toResponse(UUID, String, int, int, long, MazeGrid)`
    helper called by both `generate` and `get`. Both now restored;
    the helper flattens `MazeGrid#toTileGrid()` (which returns
    `TileType[][]`) into the `char[][]` shape `GenerateResponse`
    expects. Lesson: corruption-tail detection that relies on "ends
    with `}`" misses the case where the last surviving content was
    itself a method-end brace inside a longer file.
  - `daedalus-server/.../controller/PluginController.java` — last
    `.toList()` of the existing stream pipeline plus the `/describe`
    endpoint (signature documented in README's REST table)
  - `daedalus-server/.../test/.../MazeControllerGeneratorIdTest.java`
    — the last few `jsonPath` assertions on `$.cols` and `$.seed`
  - `daedalus-server/.../test/.../JwtTokenServiceTest.java` — the
    body of `issuedToken_expiresAtMatchesTtl` (TTL math against
    `IssuedToken#expiresAt`)
  - `daedalus-server/.../DaedalusApp.java` — the small
    `SpringApplicationBuilder` shim subclass

  **Reconstructed with reasonable confidence but worth a second pair
  of eyes** (the surviving header + Javadoc described the intent
  clearly, but a meaningful chunk of body had to be rebuilt):
  - `daedalus-server/.../config/ProdSecurityConfig.java` — last few
    `requestMatchers` for protected write endpoints + plugin
    introspection + `/ws/**` + `/v3/api-docs/**` deny + `.anyRequest()
    .authenticated()` + `.oauth2ResourceServer(...jwt)` wiring
  - `daedalus-server/.../config/SecurityConfig.java` — entire
    `@Bean SecurityFilterChain` body (CSRF off, stateless sessions,
    `permitAll` on every documented path glob)

  **Backups of the corrupted originals** are at
  `/tmp/server-backup/` in the build sandbox; if the reconstruction
  diverges from the user's intent, the surviving prefixes can be
  diffed against the rebuilt files to find disagreement.

  **Root cause** is OneDrive's "Files On-Demand" feature lazily
  hydrating cloud-only files: when an editor or compiler reads a file
  that hasn't fully synced down, OneDrive sometimes returns the
  cached-locally portion plus null padding instead of waiting for
  hydration. The fix on the user's side is either pinning the project
  folder ("Always keep on this device") or moving the working copy
  off OneDrive entirely.

## [Unreleased] — 2026-05-05

Reactor green: `mvn clean verify` passes 25 / 25 tests across all six modules
in 16 s. The four findings from the May 3 audit are confirmed applied; the
follow-ups it called out as "non-blocking" are now also done.

Two further changes landed later in the day, after the build was verified:
**OpenAPI / Swagger UI polish** and a **profile-aware Security split**. Both
are additive — the dev / test posture is unchanged, only the prod posture
gets meaningfully more restrictive, and there's a new test that locks in
which `SecurityFilterChain` bean activates per profile.

A subsequent pass added **JWT-based auth** to the prod posture — single ops
user with bcrypt-hashed password from env vars, `POST /api/v1/auth/login`
issues a self-signed HS256 JWT, write endpoints + `/ws/**` + plugin
introspection require the token, reads stay public. Two new test classes
(`JwtTokenServiceTest`, `AuthControllerTest`) lock in issue/decode round-trip
and the login contract.

### Added

- **`com.daedalus.api.dto` package** with 10 record-based DTOs extracted from
  controller inner classes — `GenerateRequest`/`Response`, `MoveRequest`,
  `SessionResponse`, `SolveResponse`, `GeneratedFrame`, `SolvedFrame`,
  `MoveFrame`, `PluginFailedFrame`, `PluginInfo`. Every record has Javadoc
  describing its endpoint or STOMP topic.
- **OpenAPI / Swagger UI polish.** New `OpenApiConfig` populates the doc-level
  `Info` (title, description, version, contact, license placeholder), declares
  the dev server URL, and pre-registers three tags (`Mazes`, `Plugins`,
  `Leaderboard`) for stable ordering in Swagger UI. `MazeController`,
  `PluginController`, and the leaderboard endpoint carry `@Tag` and
  `@Operation` summaries so the rendered UI explains each route. Spec is
  served at `/v3/api-docs` (JSON), `/v3/api-docs.yaml`, and `/swagger-ui.html`
  in dev / non-prod profiles.
- **`ProdSecurityConfig`** — new `@Profile("prod")` filter chain:
  `/actuator/health`, `/actuator/info`, `/actuator/prometheus` stay public
  (matching `application-prod.yml`'s exposure list); every other
  `/actuator/**` path requires authentication; `/v3/api-docs/**` and
  `/swagger-ui/**` are explicitly denied; `/api/**` and `/ws/**` remain
  permitted with TODOs for wiring real auth (OAuth2 / JWT / mTLS) before
  any non-trusted-network deployment.
- **`SecurityConfigProfileTest`** — locks in the `@Profile` split so the
  dev and prod chains can never both activate (which would crash boot).
- **JWT auth (prod)** — `JwtAuthProperties`, `AdminCredentialsProperties`,
  `JwtTokenService` (HS256, self-signed via `NimbusJwtEncoder` / `Decoder`),
  `LoginRequest`/`LoginResponse` DTOs, `AuthController` with
  `POST /api/v1/auth/login`. Dependency added: `spring-boot-starter-oauth2-
  resource-server` (brings in `nimbus-jose-jwt`). Config bound from
  `daedalus.security.jwt.*` and `daedalus.security.admin.*`; prod requires
  `DAEDALUS_JWT_SECRET` + `DAEDALUS_ADMIN_PASSWORD_BCRYPT` env vars. Dev
  defaults are baked into `application.yml` so login works out-of-box during
  development (admin / admin).
- **`JwtTokenServiceTest`** (4 cases) — round-trip claims, foreign-secret
  rejection, short-secret refusal at construction time, TTL math.
- **`AuthControllerTest`** (4 cases) — 200 + token on success; identical
  401 / no body on wrong password, unknown user, and unconfigured admin
  (no leakage of which check failed).
- **API versioning** on the REST surface: `MazeController` now mounts at
  `/api/v1`, `PluginController` at `/api/v1/plugins`. Class Javadoc, the one
  test that hits the endpoint, and its docstring all updated.
- **Desktop module tests** (`daedalus-desktop`, previously had none):
  - `ThemeManagerTest` — 3 cases covering the constructor's default-resolution
    branches (named-default present, named-default missing → fall back to first,
    empty theme list → no NPE).
  - `DaedalusLauncherTest` — 1 case locking in the static-lifecycle null-safety
    contract.
- **`@AfterEach closeManager()`** in `PluginManagerJarDiscoveryTest` — releases
  every `URLClassLoader` opened by `discover()` so JUnit's `@TempDir` cleanup
  can delete the test JARs on Windows.

### Changed

- **Controllers stripped of inner records.** `MazeController` 135→128 lines,
  `MazeWebSocketController` 68→63 lines, `PluginController` 40→37 lines.
  Routing/handler logic unchanged.
- **`SecurityConfig` is now `@Profile("!prod")`.** Behaviour for dev / test /
  the JavaFX desktop client is unchanged: every endpoint is `permitAll()`,
  Swagger UI works, actuator is open. Each `requestMatcher` is now explicitly
  declared and commented so the intent is obvious. `PasswordEncoder` moved
  to its own `PasswordEncoderConfig` class so the bean stays available
  regardless of which profile is active.
- **`AUDIT_RECOMMENDATIONS_2026-05-05.md`** rewritten from a backlog into a
  verification log. All audit items, including the five "non-blocking"
  follow-ups, now have date-stamped completion notes.
- **Workspace root** trimmed from 11 entries to 9: only `.idea/`, `_migration/`,
  the five Maven modules, `pom.xml`, `README.md`, `AUDIT_RECOMMENDATIONS_*.md`,
  and this file.

### Fixed

- **Spring Boot multi-module artifact collision.** `daedalus-server`'s
  `spring-boot-maven-plugin` now uses `<classifier>exec</classifier>` so the
  thin JAR remains the main Maven artifact (downstream modules like
  `daedalus-desktop` can compile against it) and the executable fat JAR is
  published as `daedalus-server-<version>-exec.jar`. Run with
  `java -jar daedalus-server-<version>-exec.jar`.
- **`PluginManagerJarDiscoveryTest` Windows file-locks.** Three tests called
  `discover()` (which opens a `URLClassLoader` per JAR) but never invoked
  `shutdownAll()`. The new `@AfterEach` closes the loaders before `@TempDir`
  cleans up. Net effect: `mvn clean verify` now goes green on Windows.

### Licensed

- **MIT License** — added `LICENSE` at project root. Copyright 2026 Richmond.
  README updated to point at it; `OpenApiConfig` swagger metadata switched
  from "Unlicensed (no license file in repo yet)" to MIT.
- **SPDX-License-Identifier headers** — `// SPDX-License-Identifier: MIT`
  added as line 1 of every Java source file (109 across the five modules)
  plus the two files under `Code/`. Total: 111 files. Lets automated
  license-scanners (FOSSA, ScanCode, REUSE) detect the license per-file
  without having to read the root `LICENSE`.

### Removed

- Three superseded audit zips from project root: `daedalus-complete-audit-
  2026-05-03.zip` (duplicate of `(1)` archive), `daedalus-full-audit-
  2026-05-03.zip`, `daedalus-server-audit-2026-05-03.zip`.
- Empty `src/` skeleton (23 leftover directories from the multi-module split
  that `migrate.bat` should have removed).
- Two 0-byte stub files in root: `com.daedalus.desktop`, `com.daedalus.server`.
- `migrate.bat` and `MIGRATION.md` from the active root (archived to
  `_migration/`; migration is complete).

### Verified (no changes needed)

- All four audit patches (`M