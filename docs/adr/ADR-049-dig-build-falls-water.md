# ADR-049: Dig, build, falls hurt, water (the basics)

Status: accepted, 2026-10-12

## Why

Richmond: "add some common sense... be able to explore... dig around like in Minecraft, take waterfalls, falling
hurts. You know the basics." The islands should be places to dig for resources and build.

## Decision

- **The live world is the world you play in.**
  - In Play the Daedalus World actor loads from the server and hides the imported static chunks (`chunk_*`).
    Static meshes can't be dug; the live copy is remeshed from the same cube data (DaedalusMeshCore).
  - The level's World actor now loads on Play (it was off, so it had 0 chunks).
- **Edits:**
  - `SetCube` changes the store, remeshes the chunk and its neighbours at once, and resets the foes' nav cache.
  - It also sends the edit to the server: `PUT /api/v1/world/{id}/block`, or `DELETE` for AIR. The world's
    leases and permissions there decide; a refused edit is undone by the next poll.
  - Reads: `CubeAt`, `CubeCoord`, `CubeCenter` and `CubeTypes`.
- **The pick**, a third tool (Y cycles sword, blaster, pick):
  - Hold attack to mine the cube under the reticle into the bag. Hardness by type, in seconds:
    - leaves and glass 0.15
    - dirt, grass and sand 0.35
    - wood 0.55
    - stone and ore 0.75
    - crystal and obsidian 1.2
    - water, lava, portals, bedrock and clouds can't be mined
  - Aim places the selected cube on the face you look at, never inside yourself. R or D-pad left picks the cube.
  - Survival rules: you place what you mined. `daedalus.Creative 1` lets you place anything.
  - A twelve-edge cursor outlines the target, and the HUD shows the target, mining % and the bag.
- **Common sense:**
  - Falls past about five cubes hurt, at (impact speed − 1300 cm/s) × 0.15.
  - Water breaks a fall. In water you sink slowly and jump swims up, so a waterfall carries you down gently and
    you can swim back up it.
  - Falling off an island into the void is a death.

## Proven live (UE 5.8.3, play scenarios)

- **dig 6/6:** grass under the reticle mined into the bag, the world showed AIR there, a cube placed back filled
  the hole, and the server accepted every edit (7 of 7 over the runs).
- **fall 2/2:** a 2.5 m drop did no damage (impact 915 cm/s); a 15 m fall did 142 (impact 2247 cm/s).
- The first dig runs failed on the test, not the game, three times; each lesson is in AUTOMATION-LESSONS:
  - a struct read back from Python followed the hero's target;
  - a ray aimed into the hole went past reach;
  - a ray aimed at the hole's floor hit the near rim.

## Held

- Water scenario (needs a `FindCube` hook to locate water).
- Collision cooking synchronously on edits: asynchronous cooking leaves an edited chunk without collision for a
  few frames.
- Bigger, deeper lands with ores (next, ADR-050).
- Tools that mine faster, crafting.
