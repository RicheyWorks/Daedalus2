# ADR-054: The world dresser puts the shipped art library into the live world

Status: accepted, 2026-10-12

## Why

Richmond: "the building in unreal needs to advance significantly. We have deployment dates to hit." The art queue
had shipped about a thousand meshes into `/Game/Daedalus/Art`, but none of them stood in the world.

## Decision

`ADaedalusDresser` (C++) is spawned by the hero, one per level. Once the live cubes stop streaming in, it dresses
them:
- **Plants.** Every grass, dirt, sand, stone and gravel top with two cubes of air above it can grow something:
  - trees 2.5%, shrubs 3%, flowers 5%, grass 8%, mushrooms 1%, herbs 1.5% (scaled by `Density`);
  - species by ground: sand gets palms, Joshua trees, saguaro, tumbleweed and desert rose; stone gets pines,
    spruce, larch, edelweiss and moss; grass gets the rest; water plants wait for water;
  - one species per 6x6 cell, so plants cluster the way real ones do;
  - trees at least 3 cubes apart;
  - random yaw, scale 0.85–1.2 and jitter.
- **A starter town** on the flattest grass within 20 cubes of the PlayerStart: a well, the news board, a shop,
  three cottages, benches, four lanterns, mailboxes and flower pots. The plants keep a 9-cube margin clear around
  it.
- **The library is found by name** in the asset registry (`Prop_Tree_<Species>_<Stage>`, `Bld_*`…). Every asset the
  queue ships joins the world on the next `Dress()` with no code change.
- **Performance:** one hierarchical instanced mesh per mesh, so 2,100 instances cost 125 components. Trees and
  buildings collide; small plants don't. Deterministic per `Seed`.

## Proven (live, UE 5.8.3, scenario `dress` 5/5)

`placed=2100 meshes=125 trees=160 plants=1922 town=18 library=1003`, with the town on the legendary land near the
start. The screenshot (`bot-team\shots\dressed_town.png`) shows forested, flowering islands and the town.

## Found on the way

The art queue's import left material instances dirty. Closing the editor for a build then raised "Save Content?",
and the rebuild stalled. The import now saves its folder; e2e is 20/20 and a mutant was caught.

## Held

- Plants on dug cubes keep floating until the next `Dress()`. Next: re-dress the edited chunk only.
- Packaging: add `/Game/Daedalus/Art` to "Additional Asset Directories to Cook" before the first packaged build.
- Water plants, once water surfaces are tracked.
