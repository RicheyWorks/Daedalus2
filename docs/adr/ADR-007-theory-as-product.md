# ADR-007: Surfacing the theory module as product

**Status:** Accepted (ideas 1–6 and 9 implemented; 7, 8 and 10 queued)
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
anything a user or reviewer can observe. *(Update after ideas 1–6 and 9 shipped: that count is
now one. `DistanceOracle` remains unreferenced, and the postscript on ideas 5 and 6 explains why
that is the right answer rather than a leftover.)* That is the gap worth closing, and it is a much
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

> **Two rows above are wrong as written, and are left standing.** Idea 3's placement framing is
> vacuous on a tree, and idea 6's "revives `DistanceOracle`" is the wrong justification — the
> oracle is slower than a plain sweep for what this needs. Both shipped reframed. The rows stay
> as first written because the postscripts at the end of this document are about those mistakes,
> and editing them away would hide the only interesting part.

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
8. [x] Idea 9 (**Generator invariant fuzzing**) — `GeneratorInvariantFuzzTest`, registry-driven
   so new generators are covered automatically; 506 generations across 11 shapes and 2 seeds
   found **zero** violations, and six deliberate breaks confirm the properties have teeth
9. [x] Idea 3 (**Hardest route**) — `GET /api/v1/maze/{id}/hardest-route`, reporting the
   shortest and longest simple routes, their ratio and the maze's loop count. Reframed after
   measurement (see the postscript): shipped as a *measurement of the current maze*, not as a
   start/goal placement mode, because on a tree those are the same thing
10. [x] Idea 6 (**Distance heat map**) — `GET /api/v1/maze/{id}/distance-field`, one BFS sweep,
    payload-capped; **does not use `DistanceOracle`**, for the measured reason below
11. [x] Idea 5 (**Sanctuary placement**) — `GET /api/v1/maze/{id}/sanctuaries?k=`, k-center via
    `FacilityPlacement`, reporting covering radius, served cells and the worst-served cell
12. [ ] Ideas 7, 8 and 10, in the priority order above

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

## Postscript: what building idea 9 taught

**A green property test is evidence of nothing until it has been seen to fail.** The fuzz swept
506 generations — every registered generator across 11 shapes including 1×1, single rows and
columns, and 16×24 — and reported zero violations. That is the same output a test with an
inverted assertion or an empty loop produces. So the properties were re-verified from the other
side: `mutants/fuzzteeth.py` breaks Binary Tree six ways, one per property, and all six are
caught by the property they were aimed at. Only *then* is "zero violations" a finding rather
than a hope. Recording the negative result plainly is the point — the 23 generators were
previously "presumably fine", and now they are measured.

**The harness taught its own lesson.** The first run was launched under a wrapper that hit a
timeout; the wrapper died, the Python process was orphaned and kept mutating the same source
file, and a second copy started against it. The two interleaved runs printed a confident
"6/6 caught" that was worthless, and left a sabotaged generator in the working tree — which
only surfaced because `git status` was checked afterwards. **A tool that edits source in a loop
needs a lock and a crash-safe restore, not just a `finally`.** The rewritten harness holds a
lock file, keeps a pristine sidecar that the next run restores from, reverts after each
mutation rather than at the end, and reverts on SIGTERM. The result was then re-measured from
a verified-clean tree, which is where the 6/6 in this document comes from.

## Postscript: what building idea 3 taught

**The idea as written in this document was wrong, and measuring it took ten minutes.** Idea 3
proposed placing start and goal "on the longest simple path instead of the extremes". A perfect
maze is a tree; a tree has exactly one simple path between any two cells; so on 22 of the 23
registered generators the longest route between two cells is the *only* route between them, and
the proposed mode would have been a button that changes nothing. Measured on a 15×15
recursive-backtracker maze, extremes placement and "hardest-route placement" agree to the step:
145 and 145.

What survives is the measurement rather than the mode. The gap between shortest and longest is
zero on a tree and large the moment the maze has loops — the same 21×21 maze braided at 0.5
goes from 203/203 to 56/260, a ×4.6 detour; a dungeon measures 40 against 122; and thirty
erosion ticks on a living maze took one instance from ×1.00 to ×2.69 while opening 31 loops.
So the endpoint reports both routes, the ratio, the loop count, and — on a tree — says plainly
that there is only one route and which operations open more. **A feature that is honest about
being inert is better than one that hides it behind a number.**

**Two real defects fell out of building it**, both in `LongestPath`, both invisible until
something asked for large or braided inputs:

1. *It returned "no route" for mazes anyone can walk.* On a 41×41 at braid 0.5 the DFS spent
   its entire two-million-visit budget in the cycle-rich middle and never once reached the goal,
   so the result was `length = -1` and an empty path. The incumbent is now seeded with the BFS
   shortest path: the answer is a real route at worst, and the search spends its budget
   improving rather than hunting for a first success.
2. *It threw `StackOverflowError` on every perfect maze from 200×200 up.* The search recursed,
   and a 512×512 tree — a size the REST surface explicitly accepts — has a unique route tens of
   thousands of cells deep. An `Error`, not an exception, out of a public core API. Braided
   mazes hid it perfectly, because the visit budget ran out at shallow depth before the stack
   did, which is exactly how a bug like this survives a green test suite. The frames now live in
   arrays sized from the grid; a 512×512 perfect maze returns a proven-optimal 74,268-step route
   in 74 ms.

The pattern worth keeping: **the roadmap entry is a hypothesis, not a specification.** Both of
these were found by writing a throwaway probe that printed a table before any feature code
existed.

## Postscript: what building ideas 5 and 6 taught

**`DistanceOracle` should stay dormant, and now there is a number saying why.** Idea 6 was
written as "revives `DistanceOracle`" — the class exists, so surfacing it looked like pure
upside. Measuring first says otherwise. The oracle tabulates all-pairs distances for O(1)
lookups and caps itself at 4,096 cells because the table is `V²` shorts (32 MB at 64×64). A heat
map needs *one* source, not all pairs, and that cap would exclude most mazes this server
generates. Worse, on its own home ground the oracle loses: computing every cell's eccentricity
measured **1,738 ms** via precompute-then-scan against **1,485 ms** for running the same sweeps
directly, at 64×64, with the direct route allocating nothing. It only pays when many *random
pairs* are queried after the table is built, and nothing in this product does that.

So the heat map uses `MazeMetrics.distancesFrom`, and the roadmap's "revives X" column turned out
to be the wrong reason to build the feature — the feature is good, the justification was not.
Six of nine theory classes were dormant when this ADR was written; the right count today is one,
and it stays dormant deliberately rather than by neglect. **"Unused" is a question, not a verdict.**

**The k-center coverage trap did not fire, which is also worth recording.** `FacilityPlacement`
documents a real hazard: on a fragmented graph, `kCenter` improves its radius while leaving most
of the maze unserved. That is why the class ships two variants. Measured on this project's actual
mazes, the hazard is absent — a 21×21 dungeon's 206 habitable cells form one component (the
generator fuzz from idea 9 proves this holds for every registered generator), so `kCenter` serves
all of them at every k, while `kCenterAcrossComponents` pins the radius at 40 and spends extra
facilities "serving" isolated rock nobody can walk to. The dungeon reading is the correct one
here, and `servedCells` is reported anyway so the claim stays checkable if a future generator
changes that.

**The heat map looked broken and was not.** The first render showed no smooth halo around the
goal — bright patches scattered mid-maze, sharp discontinuities everywhere. That reads as a bug.
Checking the numbers instead of the picture: the field is 0 at the goal, and the goal's four
physically-adjacent cells measure 201, 1, 189 and 157. A maze distance field is walking distance,
so touching cells are remote when a wall stands between them — and every abrupt change of shade
marks a wall doing exactly that work. It is the most informative thing the overlay shows. The
legend now says so, and a test pins it, because the next person to look at that picture will
have the same instinct to "fix" it.
