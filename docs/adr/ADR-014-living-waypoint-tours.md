# ADR-014: Living mazes rescore waypoint tours

**Status:** Decided — **accepted**
**Date:** 2026-08-17
**Deciders:** RicheyWorks
**Composition of:** ADR-007 idea 1 (waypoint tour) and ADR-006 / ADR-008 (living mazes).
Those two shipped independently. A cached Held-Karp cost is a recording of a maze
that may no longer exist.

## Question

`WaypointService` cached the whole `Tour` under `mazeId:k`. Living ticks
`replace` the grid and keep the id. After erosion the optimum can only shrink;
after hardening it can only grow. Scoring a walk against the tree the tour was
first asked about is a lie. Do we freeze the puzzle, refuse the composition, or
rescore?

## Decision

**Freeze the coins, move the score.**

Placement is k-center on the grid the first time a maze is asked for a tour.
That set stays put for the life of the cache entry — a living maze is a hazard,
not a new puzzle mid-walk, and collection tracking keys on `Point` equality.

`tourFor` always runs Held-Karp on the cache's *current* grid plus those frozen
waypoints. The number in `optimalCost` is a fact about the maze under the
player's feet. The UI refetches `/tour` on each living refresh and narrates
when the optimum moves.

What stays the same:

- First placement is still deterministic from the grid at first ask. Two
  players who request a tour before any tick still share an instance.
- A player who first asks *after* ticks have run gets placement on that
  snapshot. That is the same rule as "the maze alone" — the maze is the
  live one.
- Traffic (weight drift) does not change a hop-count tour. No extra listener.
- Ghosts stay recordings of a finished run. They are not a live optimum.

## Why not refuse the composition

Campaign stages already declare `living` and the tour endpoint is public on
every maze. Refusing `/tour` on a live maze would make the late ladder a
404. Rescoring is the smaller close.

## Re-fire

A named "tour hazard" that *moves* waypoints (re-placing after each tick)
would be a different mode. Until someone wants that, placement stays frozen.
