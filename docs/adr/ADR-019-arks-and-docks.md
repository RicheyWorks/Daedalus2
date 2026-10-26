# ADR-019: Arks and docks

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks
**Prompted by:** "this floating island idea with flying boats like in final fantasy will be legit" —
"we call the ships arks" — "they transport animals to other islands to populate them after the great
explosion of a meteor hit and busted everything up into islands."

## The story this serves

A meteor struck and shattered the world. What is left is a lane of floating islands, barren of
animal life. **Arks** carry creatures from island to island to repopulate them. That makes the ark
the world's colonisation vector: in island-biogeography terms, the immigration rate of an island is
mostly set by ark traffic, not wind. ADR-020+ build the ecology on that premise.

## Decision

**Every island grows a pier.** `IslandGenerator.dock()` lays a plank path from the dry rim column
nearest x = 0 on the +Z side (the side facing the world origin) and runs it `PIER_LENGTH = 7` cubes
past the rim on log posts, with two mooring bollards at the tip. Trees and boulders keep a clearance
from it (`nearReserved`). The tip is a trait (`dockX/Y/Z`), so it is derived from the seed like
everything else — not stored. Seed 11's golden digest moved on purpose (`ed45f7d3…` → `bcd94a28…`).

**Every island launches one ark.** `ArkOps.launch(slot, traits)` → `Ark(id = ark-<slot>, name,
homeSlot, slot, berth)`. The name is `ArkNames.of(seed)` — a colour or quality plus a sky creature,
original pairings, 256 combinations. The berth is the open cube above the pier tip: where a
passenger steps off. Until voyages exist (ADR-020) an ark is derived from the lane, never stored.

**`GET /world/{id}/arks`** (public) lists them; `IslandRow` gains the pier tip in world coordinates.
README table, prod matcher and `ProdAuthPostureTest` changed together.

**The realm moors the Blender model.** `/models/ark.glb` is the ark built in Blender through the
connector and exported with its vertex colours (`COLOR_0` verified in the file). It is served as a
static file with its own prod-posture row. Each ark gets a clone at 0.6 scale, a name label and a
slow bob.

## What it found

- The first mooring laid the hull along the pier, bow outward. At 23 cubes the hull reached back
  through the rim into the island — the harness screenshot showed a balloon inside the trees. Arks now
  moor side-on across the pier tip, `ARK_STANDOFF = 9` cubes out.
- The footprint test's reach had to grow: a rim can sit 22% past the radius and the pier runs beyond
  it. Reach is now `ceil(1.22 · radius) + PIER_LENGTH + 2`, still under half the 96-cube lane spacing.

## Verified

Core: island + ark tests (pier tip is a plank with open air above, bollards, no trunk on the pier,
for five seeds; names stable and spread). Server: `everyIslandLaunchesAnArkMooredAtItsPier` checks
id, name, state and that the berth stands on a real WOOD plank in the world. Browser harness: both
pages moor the same named ark with its model loaded, the berth is AIR over WOOD, screenshot
`realm_ark.png`.

## Held

- Voyages: arks moving between islands (ADR-020).
- Ark state persistence: arises with voyages, not before.
