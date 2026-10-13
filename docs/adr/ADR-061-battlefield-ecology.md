# ADR-061: Reactive Battlefield Ecology

Status: Accepted (Java core). Owner: pythagoras. Branch: `pythagoras/battlefield-ecology`.

## Context
The Adaptive Combat Director (NEXT-PHASE-COMBAT-AI) needs terrain that answers back: cover and concealment that change
when a fight burns or blasts them, and recover between encounters. `world/ecology` (ADR-021..023) models species and
communities and is left untouched; this is a separate cell grid for combat.

## Decision
Package `com.daedalus.world.battlefield`:
- `Vegetation`: BARE, MEADOW, SCRUB, PINE, OAK, WETLAND, each with cover, concealment, flammability, burn ticks and
  years to the next succession stage (meadow -> scrub -> pine -> oak).
- `BattlefieldEcology`: w x h grid in centimetres. `apply(IGNITE|BLAST|DOUSE, x, y, r)`, `tick()` (4-neighbour fire
  spread with wind; a cell's total chance to light a neighbour equals its flammability, spread over its burn time;
  wetland never burns), `grow(years)`, and queries `coverAt`, `burningAt`, `concealmentBetween` (canopy and smoke along
  a sight line), `bestCover(unit, threat, radius)` (avoids fire).
- Determinism: every draw is SplitMix64(seed, tick, cell), so the same seed plus the same events replay bit-for-bit.
- Java decides at ~1 s timescale, never on the frame path (as ADR-060).

## Contracts (versioned plain text, all-or-nothing, errors name the line: `DBE line N: reason`)
DBE 1 snapshot (Java -> Unreal):
```
DBE 1
grid <w> <h> <cellCm> <originX> <originY> <seed>
tick <n>
row <j> <one code per cell: . m s p o w>
fire <i> <j> <ticksLeft>
```
DBE-E 1 events (Unreal -> Java), at most 256 per batch: `event <IGNITE|BLAST|DOUSE> <x> <y> <z> <radiusCm>`.

## Integration
Unreal (unreal-team) forwards explosions and incendiaries as DBE-E events beside DTE 1, and renders DBE 1 rows as
foliage density, scorch decals and fire/smoke. The director calls `bestCover` when choosing DTO 1 move orders.

## Status
Java core and tests done; the in-game demo requires the Unreal hook above (not built here; no editor use in this phase).
