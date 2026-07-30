# ADR-007: Surfacing the theory module as product

**Status:** Accepted (idea 1 implemented; 2–10 queued)
**Date:** 2026-07-30
**Deciders:** Richmond
**Supersedes / extends:** ADR-006 (living mazes roadmap, complete)

## Context

ADR-006's ten ideas are all shipped. Looking for what to build next, the honest question was
not "what feature would be fun" but "what does this codebase already contain that nobody can
see". The audit answers that unambiguously.

The `daedalus-core` `theory` package is the project's actual differentiator — it is not a maze
game with some graph code attached, it is a graph-theory library with a maze game attached.
Counting references from the server and desktop modules:

| Theory class | What it computes | Reachable by a user? |
|---|---|---|
| `MazeMetrics` | BFS fields, diameter, extremes placement | yes (3 refs) |
| `MazeFlow` | max-flow min-cut, edge connectivity | yes (2 refs) |
| `DifficultyGrader` | composite playability score | yes (1 ref) |
| `WaypointTour` | **exact Held-Karp TSP over waypoints** | **no (0)** |
| `LongestPath` | **longest simple path (hardest route)** | **no (0)** |
| `FacilityPlacement` | **k-center facility placement** | **no (0)** |
| `DistanceOracle` | **all-pairs distance precomputation** | **no (0)** |
| `ComplexityAnalyzer` | **empirical algorithm measurement** | **no (0)** |
| `GrowthEstimator` | **growth-curve fitting with R²** | **no (0)** |

Six of nine classes — including an exact exponential-time TSP solver and an empirical
complexity classifier — are fully built, documented, and tested, and contribute nothing to
anything a user or reviewer can observe. That is the gap worth closing, and it is a much
better generator of ideas than brainstorming features from nothing.

**Constraints.** Anything added must hold the standards this codebase already enforces:
bounded stores and bounded compute per request, deterministic where the project promises
determinism, verified by tests with demonstrated teeth, and rate-limited on the existing
budgets. Compute-heavy theory (Held-Karp is `O(2^k · k²)`, longest-simple-path is
NP-hard) must carry explicit, documented caps rather than hoping inputs stay small.

## Decision

Adopt a second roadmap of ten ideas, all of which surface dormant analytical capability as
product. Implement idea 1 (**Waypoint Tour mode**) now; queue the rest in priority order, the
same way ADR-006 was executed batch by batch.

## The ten ideas

| # | Idea | Revives | Why it is interesting | Cost |
|---|---|---|---|---|
| 1 | **Waypoint Tour mode** — collect scattered waypoints then reach the goal; the server knows the provably optimal collection order and scores you against it | `WaypointTour` | Turns an exact exponential algorithm into a game mechanic. "You walked 87 steps; optimal is 64" is a hook no maze app has | M |
| 2 | **Complexity Lab** — run a generator across sizes live, fit the growth curve, report empirical `O(·)` with R² | `ComplexityAnalyzer`, `GrowthEstimator` | Measuring algorithmic complexity *as a product feature*, live, rather than asserting it in a comment | M |
| 3 | **Hardest-route mode** — place start/goal on the longest simple path instead of the extremes | `LongestPath` | The extremes are the farthest apart; the longest *simple path* is the cruellest walk. Different, and provably so | S |
| 4 | **Maze fingerprint + generator classifier** — a structural signature (degree histogram, dead-end density, branchiness, cut profile) that identifies which generator produced an unlabelled maze | — | "Guess the algorithm from the shape alone", with measured accuracy. Also gives dedup and find-similar for free | M |
| 5 | **Sanctuary placement** — k-center safe points minimising worst-case distance from anywhere | `FacilityPlacement` | Optimal checkpoint placement is a real optimisation problem with an obvious game reading | S |
| 6 | **Distance heat-map overlay** — shade every cell by its distance from the goal | `DistanceOracle` | Makes the BFS field visible; instantly explains why a maze feels hard | S |
| 7 | **Adversarial seed search** — find the maze that maximises solver A's disadvantage against B | `DifficultyGrader` | "Find me the maze that makes A\* look stupid" — search over the existing deterministic seed space | M |
| 8 | **Heuristic misleadingness** — measure where A\*'s heuristic lies most, and overlay it | — | Explains *why* a solver lost the arena, in structural terms rather than vibes | M |
| 9 | **Generator invariant fuzzing** — property-test every registered generator (perfect ⇒ spanning tree, sparse ⇒ connected habitable set) across sizes and seeds | — | Turns 23 generators from "presumably fine" into a proven set; would have caught the crossbreeding rock bug | S |
| 10 | **Solver tournament with confidence intervals** — rank all solvers over many mazes, reporting variance rather than a single race | — | The arena races once; a tournament says which solver is *actually* better, with statistics | M |

## Options considered for idea 1

### Option A: Waypoints as a maze property (server-generated, deterministic)

| Dimension | Assessment |
|---|---|
| Complexity | Medium — waypoints derive from the maze seed; tour computed on demand |
| Cost | Held-Karp bounded at 16 waypoints; product default 5 |
| Scalability | Fine — tour is computed once per request and cached with the maze |
| Team familiarity | High — mirrors how hotspots and daily mazes already work |

**Pros:** deterministic, so every player gets the same puzzle and the leaderboard/ghost
machinery applies unchanged; the optimal tour is a server-side fact, not a client claim;
composes with the existing session model.
**Cons:** waypoints must be stored with the maze; one more field on the maze response.

### Option B: Waypoints chosen client-side per session

| Dimension | Assessment |
|---|---|
| Complexity | Low — no server change beyond a tour endpoint |
| Cost | Same tour cost |
| Scalability | Fine |
| Team familiarity | High |

**Pros:** trivially simple; no maze-model change.
**Cons:** every player gets a different puzzle, which destroys shared leaderboards, ghosts and
the daily challenge for this mode; the client could also lie about which waypoints it visited.
A scoring comparison against "optimal" is meaningless if the client picks the instance.

### Option C: Waypoints as a plugin

| Dimension | Assessment |
|---|---|
| Complexity | High — needs new SPI hooks for per-maze state and session rules |
| Cost | Highest |
| Scalability | Fine |
| Team familiarity | Medium |

**Pros:** keeps the core lean; proves the plugin SPI can carry a real feature.
**Cons:** the SPI has no concept of session-scoped progress; building that machinery to host
one mode is backwards. Worth revisiting when a second such mode exists.

## Trade-off analysis

The deciding factor is **who owns the instance**. The whole appeal of this mode is comparing a
human's route against a provably optimal one, and that comparison only means something if the
instance is fixed and server-owned — otherwise "optimal" is a number computed over waypoints
the client invented, and two players' scores are not comparable. Option B is cheaper in exactly
the way that removes the point of the feature. Option C solves a problem nobody has yet.

Option A also inherits every piece of ADR-006's machinery for free: because waypoints derive
deterministically from the maze seed, the daily challenge, per-maze leaderboards, ghosts and
campaign stages all work in waypoint mode without a line of new code in any of them.

**Decision: Option A.**

## Consequences

**Easier:** the theory module gains a product surface, so future analytical work has somewhere
obvious to land; scoring against a proven optimum becomes a reusable pattern (idea 3 and idea 5
both want it).

**Harder:** the maze response grows a field, and every renderer must tolerate its absence;
Held-Karp's cost has to stay visibly bounded, which means the waypoint count is a hard cap
rather than a suggestion.

**To revisit:** if a second mode needs session-scoped rules, build the plugin SPI support then
(Option C) rather than accreting modes into the core.

## Action items

1. [x] `WaypointService`: deterministic waypoint placement from the maze seed, bounded count
2. [x] Optimal tour computed via `WaypointTour`, exposed on a rate-limited endpoint
3. [x] Session tracking of collected waypoints; completion requires all of them
4. [x] UI: waypoints drawn, collection feedback, score against optimal on completion
5. [x] Tests with demonstrated teeth, plus end-to-end sweep coverage
6. [x] Idea 2 (**Complexity Lab**) — `GET /api/v1/complexity`, log-log plot in the UI, fits
   pinned against known algorithm behaviour (Prim's perimeter frontier, Aldous-Broder's
   cover-time overdraw) rather than merely asserting the endpoint responds
7. [x] Idea 4 (**Maze fingerprint + generator classifier**) — `MazeFingerprint` +
   `GeneratorClassifier` in core, `GET /api/v1/maze/{id}/fingerprint`, accuracy measured on
   held-out seeds (58.9% exact vs 4.3% chance; 87.4% by algorithm family) with calibrated
   confidence (~89% accurate above 0.25, ~45% below)
8. [ ] Ideas 3, 5–10, in the priority order above

## Postscript: what building idea 2 taught

The first version fitted `cellsVisited`, the obvious "work done" metric, and reported O(n) at
R² = 1.000 for every one of the 23 generators. That is not a finding, it is an identity: a
spanning-tree generator carves each cell exactly once, so the metric *is* `n`. A lab whose
headline chart says the same thing about every subject is decoration. The discriminating
metrics turned out to be `cellsExplored` and `maxFrontierSize`, and only once those were
plotted did the feature justify itself — Prim's frontier is a perimeter, Aldous-Broder pays
cover time. **Measuring the wrong quantity produces perfect-looking numbers**, which is a more
dangerous failure than noisy ones.

## Postscript: what building idea 4 taught

Two things, both about how to read a number.

**A "wrong" answer can be the correct one.** The classifier's exact accuracy is 58.9%, which
sounds mediocre until you look at what it gets wrong: Aldous-Broder confused with Wilson's,
Kruskal's with weighted Prim's, the backtracker with hunt-and-kill. Those are not near-misses,
they are algorithms that produce the same texture — and in the first case provably so, since
both sample the uniform spanning tree distribution. Scoring by algorithm *family* gives 87.4%.
The honest report is both numbers plus the reason for the gap, not the flattering one.

**A feature that does not help is not free.** A row-scan-bias component was added on the
reasonable theory that row-sweeping generators leave a signature in row-to-row variance. It
moved exact accuracy by nothing and family accuracy by 0.8 points — about three samples out of
414, indistinguishable from noise — so it was removed. Keeping it would have meant carrying
code and a docstring justifying a benefit that was never measured.
