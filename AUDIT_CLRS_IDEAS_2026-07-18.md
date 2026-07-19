# Daedalus — CLRS Idea Audit (hit-list)

**Framing**: an ideation pass, not a code review — mining *Introduction to
Algorithms* (Cormen, Leiserson, Rivest, Stein) for interesting, buildable
directions across the engine. Chapter numbers reference **CLRS 3rd ed.**; each
result is also named so it survives edition renumbering.
**Scope**: generators, solvers, core data structures, concurrency, theory, and
the maze-as-a-service surface.
**Grounding**: the current code — 20 generators (`AlgorithmConfig`), 9 solvers
(`solver/solvers/`), `util/DSU.java`, `WeightedMazeGrid`, `MazeStats`, the
maze cache, and the `theory.ComplexityAnalyzer` that landed 2026-07-18.
**Status**: nothing here is committed or scheduled — it's a menu.

---

## TL;DR

Twenty ideas, each anchored to a CLRS chapter and mapped to a real file.
The cheapest high-payoff move is **T1** (auto Big-O labelling — a ~40-line
extension of the analyzer shipped today). The most *interesting* is **X1**
(max-flow / min-cut as a maze difficulty metric — a genuinely novel feature
straight out of Ch. 26). See **Top 5 to build first** at the end.

Read each entry as: **`ID · title`** — `CLRS ref · Impact · Effort` — then the
hook, the code it touches, and the payoff.

---

## 1. Generators

**G1 · Weighted Prim with a real priority queue** — `Ch. 23 (MST/Prim) + Ch. 6/19 (heaps) · Impact Med · Effort Med`
`PrimsGenerator` grows an *unweighted* frontier today. Give the grid edges
random weights and pull the minimum with a d-ary heap: Prim's now produces a
tunable texture (low-variance weights → lattice-like; high-variance → long
winding rivers). The weight store already exists in `WeightedMazeGrid`.

**G2 · Uniform spanning trees, measured** — `Ch. 5 (randomized analysis) · Impact Med · Effort Low`
Wilson's (loop-erased random walk) and Aldous-Broder both sample a *uniform*
spanning tree, but Wilson's is asymptotically faster. Run both through the new
`ComplexityAnalyzer` and let the CSV show Aldous-Broder's cover-time blow-up
against Wilson's as n grows — theory you can now demonstrate empirically.

**G3 · Reservoir-sampled frontier** — `Ch. 5 (reservoir sampling) · Impact Med · Effort Med`
For mazes too large to hold the whole frontier set, keep a running uniform
sample (Algorithm R) and carve from it: O(1) extra memory per step. Turns
frontier-based generators into streaming ones for 512²+ grids.

**G4 · Randomized-weight Kruskal + braiding** — `Ch. 23 (Kruskal) + Ch. 21 (disjoint sets) · Impact Low · Effort Low`
`KruskalsGenerator` + `DSU` are already here. Sort a *randomly weighted* edge
list for a free family of textures, then add a "braid factor" that re-admits
k% of the rejected edges to introduce loops (imperfect mazes on demand).

## 2. Solvers

**S1 · Dial's algorithm (bucket-queue Dijkstra)** — `Ch. 24 (SSSP) + Ch. 20 (bounded-key structures) · Impact Med · Effort Med`
**Shipped 2026-07-18 as `solver.solvers.DialSolver` (id `dial`).** Maze edge
weights are small bounded integers, so a bucket/radix priority queue (Dial)
beats a comparison heap: near-linear shortest paths. Drop-in behind
`DijkstraSolver` for `WeightedMazeGrid`, and a clean before/after for the
analyzer to quantify.

**S2 · Landmark (ALT) heuristic for A\*** — `Ch. 25 (Johnson reweighting — same triangle-inequality idea) · Impact High · Effort Med`
Precompute BFS distance trees from a handful of "landmark" cells (corners);
at query time, max over landmarks gives an admissible lower bound far tighter
than Manhattan → dramatically fewer expansions in `AStarSolver` on large mazes.
The precompute is exactly Johnson's "reweight by a potential" trick.

**S3 · Correct bidirectional stopping rule** — `Ch. 24 · Impact Med · Effort Low`
Audit `BidirectionalSolver` for the textbook bug: terminate when the sum of the
two frontier minima exceeds the best meeting-path found — *not* on first
touch, which can miss the optimal path. Pure correctness, near-zero cost.

**S4 · Distance oracle for stored mazes** — `Ch. 25 (all-pairs shortest paths) · Impact Med · Effort Med`
Precompute all-pairs distances once per stored maze (unweighted ⇒ BFS from
every cell, O(V·E)); afterwards any start/goal query — and the leaderboard's
"optimal time" baseline — is O(1). Johnson's makes the weighted version cheap.

## 3. Core data structures

**D1 · Certify the DSU is α(n)** — `Ch. 21 (disjoint sets) + Ch. 17 (amortized) · Impact Low · Effort Low`
Confirm `util/DSU.java` uses union-by-rank *and* path compression (or
path-halving) and add the inverse-Ackermann note. Both Kruskal and Borůvka
ride on it, so this is a load-bearing few lines with an outsized story.

**D2 · Bitset maze grid** — `Ch. 11 flavor + bit tricks · Impact Med · Effort Med`
Pack the four wall bits per cell into a `long[]`; neighbor scans and flood-fill
become word-parallel and cache-friendly, a measurable gen/solve win at 128²+.
Enables SWAR tricks (population counts for dead-end detection, etc.).

**D3 · d-ary heap tuned to grid degree** — `Ch. 6 (heaps) · Impact Low · Effort Low`
A 4-ary heap matches the grid's branching factor and shortens sift-down chains
versus a binary heap in Dijkstra/A*. Small, self-contained, and easy to A/B
with the analyzer.

## 4. Concurrency & parallelism

**C1 · Parallel Borůvka** — `Ch. 23 (MST) + Ch. 27 (multithreaded) · Impact Med · Effort Med`
Borůvka's rounds are embarrassingly parallel — each component finds its
cheapest outgoing edge independently. Parallelize `BoruvkasGenerator` with
fork/join for the flagship "parallel MST" demo the audits keep gesturing at.

**C2 · Parallel BFS frontier** — `Ch. 27 · Impact Med · Effort Med`
Expand each BFS layer in parallel for solving huge mazes; stays deterministic
if the next frontier is sorted before dedup. Pairs naturally with D2's bitsets.

**C3 · Divide-and-conquer tiled generation** — `Ch. 4 flavor + Ch. 27 · Impact Med · Effort High`
Generate quadrants concurrently, then carve doorways on the seams. Doubles as
the "procedural dungeon" backlog item and scales generation across cores.

## 5. Theory & analysis

**T1 · Auto Big-O labelling in `ComplexityAnalyzer`** — `Ch. 3 (growth of functions) · Impact High · Effort Low`
**Shipped 2026-07-18 as `theory.GrowthEstimator`.** The analyzer already emits
deterministic `visited(n)` per size; the estimator fits those points against
{1, log n, √n, n, n log n, n²} by least-squares + R² model selection and reports
each generator's empirical growth class plus a log-log exponent.

**T2 · "Hardest maze" = longest simple path is NP-hard** — `Ch. 34 (NP-completeness) + Ch. 35 (approximation) · Impact Med · Effort Med`
**Shipped 2026-07-18 as `theory.LongestPath`.** Finding the longest simple path
(the "hardest" route) reduces from Hamiltonian path — genuinely NP-hard. Document it honestly, then ship a
heuristic "make this harder" mode. Portfolio-grade: shows you know where the
tractability cliff is.

**T3 · Diameter → auto start/goal placement** — `Ch. 22 (BFS) · Impact Med · Effort Low`
**Shipped 2026-07-18 as `theory.MazeMetrics`.** Double-BFS finds the two
farthest-apart cells (the maze's diameter — exact for perfect mazes);
`placeStartAndGoalAtExtremes` drops start and goal there for a
guaranteed-maximal challenge.

**T4 · Random-walk cover/mixing time** — `Ch. 5 (probabilistic analysis) · Impact Low · Effort Low`
Frame a pure random-walk solver and Aldous-Broder generation as Markov-chain
cover time; the expected-step formulas explain the very curves T1 will plot.
Theory that pays for itself in narrative.

**T5 · Held–Karp for "collect all the coins"** — `Ch. 15 (DP) + Ch. 34 (TSP) · Impact Med · Effort Med`
Shortest tour visiting k waypoints via the O(2^k·k²) DP → a game mode with an
optimal-score oracle. Bounded k keeps it tractable and shows off DP over
subsets.

## 6. Distributed / maze-as-a-service

**X1 · Min-cut chokepoints** — `Ch. 26 (max-flow / max-flow–min-cut theorem) · Impact High · Effort Med`
**Shipped 2026-07-18 as `theory.MazeFlow`.** Model passages as unit-capacity
edges; the minimum start→goal cut is the fewest walls that would seal the exit. That single number is both a
**difficulty metric** and a **level-design tool** ("where's the bottleneck?").
Novel, visual, and a direct application of the chapter's headline theorem.

**X2 · Vertex-disjoint paths = robustness** — `Ch. 26 (Menger via max-flow) · Impact Med · Effort Med`
The count of vertex-disjoint start→goal routes measures redundancy and powers
non-colliding multiplayer routing (a backlog stretch goal). Same max-flow
machinery as X1, split-vertex trick for the vertex version.

**X3 · Compact maze wire-encoding** — `Ch. 32 (string algorithms / RLE) · Impact Low · Effort Low`
Run-length + delta encode the `char[][]` tile grid for REST/STOMP payloads,
and you get maze "diffs" for frame streaming almost for free. Shrinks the
generation/solve frame traffic the WebSocket layer pushes.

**X4 · Consistent hashing for the maze cache** — `Ch. 11 (hashing) · Impact Low · Effort Med`
If the cache goes multi-node (Redis is already wired for the leaderboard),
consistent hashing spreads stored mazes with minimal reshuffling when nodes
join or leave. Standard, but the right tool if scale-out ever happens.

---

## Top 5 to build first

Ranked by payoff-to-effort, biased toward what the current code makes cheap.
**All five shipped 2026-07-18** — see the per-idea "Shipped" notes above.

| # | Idea | Why now | CLRS |
|---|------|---------|------|
| 1 | **T1 — auto Big-O labelling** *(shipped)* | done — `theory.GrowthEstimator` turns raw counts into an at-a-glance growth class | Ch. 3 |
| 2 | **T3 — diameter start/goal** *(shipped)* | done — `theory.MazeMetrics`, one double-BFS; immediate, visible gameplay/UX win | Ch. 22 |
| 3 | **X1 — min-cut difficulty metric** *(shipped)* | done — `theory.MazeFlow`, novel feature + flagship theorem; reuses the grid graph you already build | Ch. 26 |
| 4 | **S1 — Dial's bucket-queue Dijkstra** *(shipped)* | done — `solver.solvers.DialSolver` (id `dial`); classic optimization on `WeightedMazeGrid` | Ch. 24 |
| 5 | **T2 — longest-path/NP-hardness writeup** *(shipped)* | done — `theory.LongestPath`, budget-bounded exact/heuristic longest simple path | Ch. 34/35 |

## Traps & non-starters

- **Fibonacci heaps as a default (Ch. 19).** The O(1) amortized decrease-key is
  a theoretical trophy; on the grid sizes you'll actually run, its constants
  lose to a d-ary or pairing heap. Cite it, benchmark it, but don't ship it as
  the production queue — CLRS itself flags the constant-factor caveat.
- **van Emde Boas trees (Ch. 20).** Gorgeous O(log log u), but the space and
  constants only pay off at huge key universes. For bounded maze weights,
  **Dial's buckets (S1)** are the pragmatic win — same idea, none of the
  overhead.
- **All-pairs precompute (S4) memory is O(V²).** Fine for a stored 64² maze,
  ruinous at 512². Gate it behind a size cap.
- **Don't parallelize inherently sequential generators.** Recursive
  backtracker is a DFS — its state is a stack, not independent subproblems.
  Spend concurrency on the ones with real independence: Borůvka (C1), tiled
  generation (C3), layer-parallel BFS (C2).

## Appendix — CLRS chapters referenced

| Ch. (3e) | Topic | Used by |
|----------|-------|---------|
| 3 | Growth of functions | T1 |
| 5 | Probabilistic analysis & randomized algorithms | G2, G3, T4 |
| 6 | Heapsort / binary heaps | G1, D3 |
| 11 | Hash tables | D2, X4 |
| 15 | Dynamic programming | T5 |
| 17 | Amortized analysis | D1 |
| 19 | Fibonacci heaps | G1 (and Traps) |
| 20 | van Emde Boas / bounded-key structures | S1 (and Traps) |
| 21 | Disjoint sets (union-find) | G4, D1 |
| 22 | Elementary graph algorithms (BFS/DFS) | S4, T3 |
| 23 | Minimum spanning trees (Kruskal, Prim, Borůvka) | G1, G4, C1 |
| 24 | Single-source shortest paths (Dijkstra, Bellman-Ford) | S1, S3 |
| 25 | All-pairs shortest paths (Johnson, Floyd-Warshall) | S2, S4 |
| 26 | Maximum flow (max-flow–min-cut, Menger) | X1, X2 |
| 27 | Multithreaded algorithms | C1, C2, C3 |
| 32 | String matching / encoding | X3 |
| 34 | NP-completeness | T2, T5 |
| 35 | Approximation algorithms | T2 |
