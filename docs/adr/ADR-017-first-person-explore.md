# ADR-017: First-person explore — extrude the grid, VR as a plugin

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** RicheyWorks
**Prompted by:** first-person / gamepad / headset viewing, and the dungeon-AI
layout already produced by `DungeonGenerator` + `DungeonLayoutLab`

## Question

The 2D well (web canvas and the JavaFX desktop) already paints the same
thin-wall `toTileGrid()` projection. A first-person walk, Xbox pads, and
headsets were requested as a new host — not another control on the 960px
toolbar. Where does that host live, and what is a legal step in 3D?

## Decision

**Extrude the existing `rows × cols` cell graph.** v1 is corridors from
`MazeGrid`, not a volumetric `x,y,z` grid. A true 3-axis maze would rewrite
every generator and solver; that is a later ADR.

**New reactor module `daedalus-explore`.** Depends on `daedalus-core` and
`daedalus-plugin-api`. It does not sit inside `daedalus-desktop` — JavaFX 3D
cannot attach a real headset. The 2D well is unchanged.

**Walk legality is `openNeighbors`.** Free-walk + capsule collision against
closed wall tiles. When the cell underfoot changes, the step must be a
member of `grid.openNeighbors(from)` — the same rule as `DesktopWalk` and
`AgentWalkService`. No diagonals, no flying camera.

**Mesh source of truth is `toTileGrid()`.** Uncarved dungeon rock is solid.
Interior room posts that the projection already opens stay floor. World
mapping: cell `(r,c)` → `(c · cellSize, eyeY, r · cellSize)`, Y-up, north is −Z.

**VR is a plugin.** The host talks to `XrRuntime`. OpenXR (and later
vendor runtimes) ship as example JARs, not compile-time natives of
`daedalus-explore`. Zero XR JARs is a valid desktop first-person.

**CI stays headless.** Mesh, collision, cell-step, fog, living rebuild,
input mapping, and story export run in `mvn verify`. GLFW and OpenXR
sessions are launch-only (`DAEDALUS_EXPLORE=1`). Same spirit as ADR-003:
the window is a thin shell.

## Consequences

- A living tick (`Braider` / `Sealer`) rebuilds the mesh from the new
  snapshot; a just-closed wall cannot be crossed.
- Fog follows ADR-006: stood-on cells and their touching wall tiles.
- `DungeonLayoutLab` locations (entrance, vaults, boss) become in-world
  markers; story JSON is the handshake for ai-dungeon-master.
- Gamepad and keyboard produce the same `ExploreInput.Intent`.
