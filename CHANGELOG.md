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