# ADR-025: Creatures on the islands

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks

## Question

The Life panel (ADR-024) lists who lives on an island, but the island in the sky still looks
empty. How do the animals show up in the world without the server streaming positions for
hundreds of individuals?

## Decision

**The server owns the counts, and the client draws them.** No new route and no new frame. The realm
already has every island's ecology (ADR-023), every cube (ADR-018) and the canon (ADR-021), which
is everything it needs to draw.

- **How many.** Each kind gets ⌈log₂(count + 1)⌉ bodies, from 1 to 5, and an island draws at most
  90. A swarm of 300 puffballs reads as a patch, not a carpet, and a pair of red pandas still shows.
- **Where.** One scan per island over the client's own chunks, cached by world revision, finds
  four habitats. Meadow kinds go on open ground (grass, dirt, sand, gravel or stone with air above).
  Pond kinds go on water. Canopy kinds go in the crowns (leaves and blossom). Decomposers go on soil
  as caps. Starborn kinds hang glowing under the island's crystals, where the meteor left them. A
  guild with no habitat on that island falls back to meadow ground.
- **Which spot.** Placement is seeded from the island seed and the kind's key, using mulberry32 and
  FNV-1a, so two browsers draw the same body in the same place. The harness compares body by body.
- **What they look like.** Each body is built from a few voxel boxes. Walkers have a body, head and
  four legs. Fliers have wings that beat. Swimmers are flat, with a tail. Rooted kinds are a cap on a
  stem. Colour comes from a hash of the key and size from the canon (tiny 0.42 cube up to large
  1.4). This is placeholder art: the same scheme can load a per-kind GLB from the Blender connector
  later without changing placement.
- **When.** The realm redraws an island when a landing or a boarding touches it, every fifth day,
  and on load. Each time it skips the redraw if the planned bodies are unchanged.

## What the slice found

- **The determinism check compared the wrong thing.** The first version mapped kind → home, which
  kept only the last body of each kind, so it reported 39 mismatches between two identical pages.
  It now compares body by body (`kind#n`), and all 38 match.
- **Tiny kinds disappear from orbit.** At 0.28 cubes a beetle was a single pixel at fly-to distance,
  so tiny bodies went up to 0.42. Sizes stay ordered, and this is art scale, not ecology.
- On a typical run, Isle 1 at day 31 drew 38 bodies of 9 kinds, with 8 pond bodies, all on water.

## Held

- Per-kind models from Blender (the connector can export a GLB per canon key) — when the canon
  has art.
- Creatures reacting to players or to each other. They wander a small loop around a home spot; any
  behaviour beyond that waits for NPC work (the AI Dungeon Master graft, ADR-018).
