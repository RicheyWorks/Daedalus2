# ADR-008: Living mazes v2 — hardening without stranding anyone

**Status:** Accepted
**Date:** 2026-08-17
**Deciders:** RicheyWorks
**Supersedes / extends:** ADR-006 (living mazes). Fires the re-fire trigger recorded there.

## Context

ADR-006 shipped living mazes as *erosion*: each tick only opens walls. That is safe by
construction — reachability can only grow — and it was the right v1 because closing a wall
needs a connectivity proof per closure. The ADR named the trigger: *if Option 3 (traffic)
or Option 7 (fog-of-war) is built, revisit closing with a cut-vertex check.*

Both shipped on 2026-07-30. Fog-of-war walks already see the live grid, so a maze that can
get *harder* mid-walk is the composition that ADR-006 called the killer version. The
trigger has fired.

The ADR's wording is slightly wrong, and is left standing. Closing a wall removes an
**edge**, not a vertex. The certificate is a cut-edge / bridge, not a cut-vertex. A
cut-vertex check would be the proof for deleting a *cell*. Using the wrong object would
have looked rigorous and protected the wrong operation.

A second trap: "close every current non-bridge" is not safe as a *batch*. Two parallel
paths are each a non-bridge; closing both disconnects the rooms. The simultaneously-safe
set is the complement of a spanning forest — every extra can come off at once and the
forest still joins every habitable cell.

## Decision

Add `Sealer` in `daedalus-core` as Braider's inverse. Each living tick may close a
fraction of the maze's non-forest passages. Default `daedalus.living.seal-factor` is
**0**, so `POST /live` without `?seal=` is byte-identical to v1. Hardening is opt-in per
request (`?seal=` in `[0, 1]`) or via the process-wide knob.

The forest is a BFS over the habitable graph (degree &gt; 0) in `MazeGrid.openNeighbors`
order, so it is deterministic without a seed. The seed only shuffles *which* extras close
first. Rock (dungeon stone) is skipped, the same way habitability already works for
crossbreeding and k-center.

## Options considered

### Option A: Close one wall per tick after a per-edge bridge test

Safe. Slow to watch. A 21×21 braid can have dozens of extras; one per 2 s tick takes a
minute to become a tree again. Rejected as the only mode; the forest complement lets a
tick close many extras safely.

### Option B: Tarjan bridges, close a fraction of current non-bridges

Looks like the textbook answer. Unsafe as a batch (the two-path case). Would need a
recompute after every single close, which is Option A with extra ceremony.

### Option C: Spanning-forest complement (CHOSEN)

One BFS, then a shuffle of the extras. Closing any subset leaves the forest. On a perfect
maze the extra set is empty — a no-op, stated plainly, the same honesty ADR-007's
hardest-route endpoint learned on trees.

## Consequences

- `MazeMutatedEvent` / `MutationFrame` grow an additive `wallsClosed` field. The
  seven-argument event constructor still compiles (closes 0).
- Campaign stages that declare `living` keep v1 behaviour: they call `/live` without
  `seal`. A stage that wants hardening passes the query param.
- A maze that is already a tree and is asked only to harden settles on tick one, same as
  a fully-braided maze asked only to erode.

## Action items

1. [x] `MazeGrid.seal` — the inverse of `carve`, both sides of the wall
2. [x] `Sealer` + tests with teeth (tree is a no-op; full seal returns a tree; two
       parallel paths keep exactly one; components unchanged across seeds)
3. [x] `LivingMazeService` applies sealing when the run's factor is positive; v1
       constructors stay erosion-only
4. [x] `POST /live?seal=` validated to `[0, 1]`; default factor 0 in `application.yml`
5. [x] UI: Harden checkbox; mutation log names walls closed
6. [x] ADR-006 action 16 records the trigger as fired
7. [x] Campaign composition (2026-08-17) — the finale declares {@code hardening}; the
       client folds it into the existing {@code /live} call as {@code ?seal=0.08}. A
       second start would join the v1 run and drop the factor.
