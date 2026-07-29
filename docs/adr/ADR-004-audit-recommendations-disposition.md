# ADR-004: Disposition of the Engine Audit's §2 Recommendations

**Status:** Accepted
**Date:** 2026-07-28
**Deciders:** Richmond (RicheyWorks)
**Source:** `Audit/DAEDALUS_ENGINE_AUDIT_FEEDBACK_RECOMMENDATIONS.md` §2

---

## Context

The engine audit left seven concrete recommendations across three priority tiers. Some are
implemented; the rest deserve a recorded decision rather than an indefinitely-open list —
ADR-002 set the precedent that a reasoned "no" with evidence beats a silent "someday".

## Implemented (2026-07-28)

- **§2.1.1 `MazeVisualizer` interface** — `com.daedalus.visualize.MazeVisualizer`, with
  `AsciiMazeVisualizer` as the reference implementation. `MazeGrid.toString()` now renders
  through it (which also closes §2.3's ASCII-art polish item), and the glyphs come from
  `toTileGrid()`/`TileType`, so terminal, REST, and any future JavaFX/canvas implementation
  share one projection.
- **§2.1.2 Registry observability** — `/actuator/algorithms` (`AlgorithmsEndpoint`), reporting
  live generator/solver counts and descriptors, plugin contributions included. Actuator rather
  than a hand-rolled MBean: one definition serves both the web and JMX transports and inherits
  the per-profile exposure rules (visible in dev, deliberately absent from prod's include
  list). The REST `GET /api/v1/algorithms` remains the product surface; this is the ops one.
- **§2.1.3 Chaos Mode generator** — `ChaosGenerator` (`id: chaos`): splits the grid into 2–3
  bands along the longer dimension, delegates each band to a seeded random pick from
  {backtracker, Prim's, Kruskal's, Sidewinder}, and stitches adjacent bands with exactly one
  door. Trees joined by single edges are a tree, so it keeps the spanning-tree contract and
  sits on the connectivity roster like everyone else — the structural roster guard forced it
  there automatically, which is the guard doing its job. Band doors are guaranteed
  chokepoints: useful stress texture for routing policies.

## Declined or deferred, with reasons

- **§2.2 Octile (and similar) A\* heuristics — declined.** Octile distance models 8-connected
  movement with diagonals; every grid in this engine is 4-connected, where Manhattan is
  already the tight admissible metric. On weighted or braided topologies — the cases that
  matter for load-balancer work — the shipped `LandmarkHeuristic` (ALT) is the measured
  answer (5.79× fewer expansions than plain Dijkstra; 41× on IDA\*). Adding Octile here would
  be a heuristic for a movement model the engine doesn't have.
- **§2.2 Parallel generation — deferred until a consumer exists.** The benchmark harness puts
  every non-pathological generator in the low-millisecond range at 200×200; parallelizing
  would buy microseconds per call at the cost of nondeterminism risk (seed → maze is a
  contract the whole test suite and the replay/leaderboard story lean on). The honest trigger
  for revisiting: a consumer generating mazes at a scale where generation is the measured
  bottleneck — none of the three integration examples is close.
- **§2.2 `MazeReplay` — deferred, design note recorded.** Step-by-step replay requires
  solvers to emit visit sequences, which none do — they return a path and fold everything
  else into `MazeStats`. Retrofitting visit-event capture into ten solvers touches every hot
  loop the ADR-001 work just flattened, so it should be done as an opt-in observer at the
  `Graph` seam (one interception point) rather than per solver — and only when something
  (the web UI is the plausible customer) actually wants to animate solves.
- **§2.3 `@Generated` / JaCoCo exclusions — not applicable.** The build generates no code;
  there is nothing to exclude. The ratchet's existing `api/dto`-style exclusion question was
  settled when thresholds were pinned (ADR-era TESTING.md work).
