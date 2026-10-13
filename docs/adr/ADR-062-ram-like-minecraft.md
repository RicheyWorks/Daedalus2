# ADR-062: Keep RAM down the way Minecraft does

**Status:** accepted, 2026-10-13. **Author:** unreal-team (Claude). **Asked by:** Richey. "Figure out how Minecraft
deals with RAM with all its blocks. Wherever a different language optimizes better, we use it."

## How Minecraft does it

1. **A block is a number, not an object.** Each 16x16x16 section is a small palette plus packed indices: 4 to 8
   bits per block, and one value for a uniform section. Air sections aren't stored at all.
2. **Only nearby chunks are in RAM** (view distance). Chunks load and unload as you move, and unloaded ones live
   compressed on disk (region files).
3. **One mesh per section, visible faces only.** Faces between two solid blocks are never built. Mods such as
   Sodium also merge faces (greedy meshing).
4. **Nothing is an entity unless it has to be.** Blocks have no per-block object, physics body or tick. Only the few
   block entities (chests, furnaces) do.
5. **Far terrain is cheap.** Vanilla simply doesn't draw beyond view distance; mods like Distant Horizons use LOD
   meshes.
6. **Rebuild only what changed.** Placing a block re-meshes one section, on a worker thread.

## Where we stand (measured 2026-10-13)

| Rule | Ours | Verdict |
|---|---|---|
| 1. Block = number | Java `Chunk`: 16^3 `byte[]`, air chunks omitted. A radius-46 land (225,885 blocks) is 130 chunks, 0.5 MB. No chunk is uniform, and there are at most 9 kinds per chunk, so a palette would save little. | Already Minecraft-grade. The generator's `IslandPlan` uses 64 B per block (14.5 MB for that land), but only briefly; fix only if generation spikes matter. |
| 2. Load by distance | **Every island sublevel is loaded all the time** (several are AlwaysLoaded). The editor sits at **13.2 GB private** on a 31.7 GB PC. | **The big gap.** Fixed by `UDaedalusStreamer` (below). |
| 3. One mesh per chunk, faces only | World chunks: `DaedalusMeshCore` (C++), culled, about 156k triangles for World Zero. Voxel isles were one HISM instance per visible cube (Claude Island alone 117,627), each with its own physics body. | Isles now use a merged greedy mesh (ADR-058 addendum, `DaedalusVoxelIsleCore::Mesh`): 53,579 quads, one body. Not yet compiled in the editor. |
| 4. No per-block objects | Isles: the per-cube physics bodies above. Rock under an isle now has no collision (`bRockCollision=false`). | Fixed by the merged mesh. |
| 5. Far = cheap | Nothing yet. | Next: an HLOD/proxy mesh per island beyond unload distance. |
| 6. Rebuild what changed | World actor re-meshes per chunk on live block frames. | OK. |

Content on disk is 2.2 GB, of which `Daedalus/Art` is 1.6 GB in 22,185 files (about 4.3k meshes plus materials).
With every island loaded, every island's art is in RAM. That makes rule 2 the lever.

## Decision

- **`UDaedalusStreamer` (C++):** Minecraft's view distance for islands.
  - The decision logic is `DaedalusStreamCore.h`: plain C++, 15/15 under ASan, and 10,000 islands plan in about
    1.7 ms.
  - Islands load within 1.5 km of their edge and unload past 2.5 km. The gap is hysteresis, so islands don't
    flicker in and out.
  - Unloads run first, so RAM is freed before anything new loads. Loads go nearest first, one per half second.
    Islands marked always stay loaded.
  - The list of islands is `Saved/Daedalus/islands.json`, written in the editor by `daedalus_islands.py` from each
    sublevel's actor bounds.
  - It is opt-in per bot: only `/Game/Claude/` is listed by default, so no bot's island starts streaming without
    its owner. A sublevel must be Dynamic, not AlwaysLoaded, for this to work, and the script reports which ones
    are not.
- **Language rule (Richey):** whatever runs inside Unreal's frame or memory budget is C++. The cores are plain C++
  so they're testable and portable: mesh, isle, tactics, orrery and stream. Java keeps persistent state, simulation
  and strategy, and gets byte-for-byte parity ports where the server needs the same answer. Today that means:
  - voxel meshing for Unreal: C++, already done;
  - isle shape: C++ for Unreal, plus Java and JS parity ports for the server and web;
  - tactics: Unreal executes in C++, and the Java director decides;
  - storage: Java `Chunk` stays, since it is already 1 byte per block.
  Nothing is moved to C++ without a measurement showing it is a bottleneck.

## Held

- **Compile and measure in the editor:** the streamer and merged mesh need an editor build, then the working set
  measured with and without them. Trigger: the next editor turn after the Unreal break.
- **Editor RAM during turns:** each bot should keep only its own island loaded in the editor (the Levels panel's
  Unload). The safe scripted way to do that in UE 5.8 Python is still to be found in an editor slot.
  `FocusSet()` already says which islands to keep.
- **Rule 5:** an island proxy or HLOD mesh for far distances.

## Addendum, 2026-10-13 04:4x: rule 3 in the browser

`/reach.html` now draws each isle as merged surface quads, via `reach-core.js` `mesh()`, a port of the C++ `Mesh()`.
Before, it drew one instanced cube per visible block.
- **Parity:** `core-test` writes `voxel_mesh_parity.txt`, and `tools/reach_parity.mjs` matches all 7 isles, quad
  for quad (FNV hash).
- **Triangles:** 195,246 cubes × 12 = 2.34M became 98,992 quads × 2 = 198k, 12× fewer, and the page looks the
  same.
- **Speed:** with headless Chromium on SwiftShader, the same view ran at 0.29 fps before and 4.42 fps after, 15×
  faster. Ready time went from 2.0 s to 2.6 s, because meshing happens once on load.
- **JS heap:** about the same (27 to 30 MB), since cube instances and quads cost similar bytes. The win is GPU work
  per frame. This is the same change ADR-058 made for Unreal, which still waits on an editor build.
