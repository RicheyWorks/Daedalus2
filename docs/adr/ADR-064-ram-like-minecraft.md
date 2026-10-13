# ADR-064: Keep RAM down the way Minecraft does

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

## Addendum, 2026-10-13 05:0x: rule 5, far isles are cheap

`MeshLod(P, Step)` in the C++ core turns Step x Step columns into one coarse cell. A cell is land when a quarter of
its columns are; its top is the highest top in the cell and its bottom the lowest bottom. The same greedy mesher
then runs over the coarse grid (`MeshGrid`).
- **Claude Island:** 53,579 quads in full, 9,929 at step 4, 3,406 at step 8.
- **Tests:** the outline stays within one cell, and the summit and the deepest rock are kept. `core-test` passes
  25/25, and the full mesh is byte-identical to before.
- **JS port:** `meshLod()` matches C++ for all 14 LOD rows; `reach_parity.mjs` passes 29/29.
- **Web:** `/reach.html` uses `THREE.LOD` per isle: full under 700 m, step 4 under 1.6 km, step 8 beyond. At an
  overview distance the picture is unchanged, and SwiftShader frames went from 5.52 to 6.01 fps, rising to 4.80 →
  6.68 fps with most isles far away.
- **Held:** the same swap for `ADaedalusVoxelIsle` in Unreal, by distance, waits for an editor build.

## Addendum, 2026-10-13: rule 1 for generated plans, and the hottest read

- **`IslandPlan` packs its cubes** like a chunk section: one long per cube (y, z and x in 21 bits each, so the
  numeric order is the generator's ORDER) plus one type byte. `blocks()` is a read-only map view: binary search for
  `get`, entries made as you iterate.
  - A radius-46 land went from 14.5 MB to 2.3 MB retained, from 64 to 10 bytes per cube.
  - The constructor's extra TreeMap copy is gone.
  - Golden digests are unchanged. daedalus-core passes 635 tests with checkstyle and SpotBugs, and the island and
    world server tests are green.
  - The first try unpacked z and y into each other's places, and the equality tests caught it at once.
- **`Chunk.get`** no longer clones `BlockType.values()` on every read: 22 ns down to about 1 to 3 ns per read, and
  0 GCs where there were 23 per 24M reads.

## Numbering and neighbours (2026-10-13)
This was first filed as ADR-062, which blender-team had already taken for the BBA 1 asset LOD manifest. Renumbered to
064; every code comment now says ADR-064. How the three RAM decisions fit:
- **ADR-062 (BBA 1, blender-team):** which LOD of each *asset* to load. Rule 5 for meshes that come from Blender.
- **ADR-063 (DSB 1, disk-saver):** which *islands* are resident under a RAM budget, with hysteresis.
- **ADR-064 (this):** the Minecraft rules themselves, and the voxel side: packed blocks, merged greedy meshes per
  isle, voxel LOD, distance streaming (`DaedalusStreamCore`). `DaedalusStreamer` plans by distance today; the next
  step is to gate its loads through DSB 1's `Pick` so distance and the RAM budget agree (one rule, not two).
- **Done (same day):** `DaedalusStreamCore::Plan` takes `Settings.RamBudgetKiB` and each island's `RamKiB` (DSB 1's
  `ram`), and applies ADR-063's rule: what stays resident counts first, then loads nearest first while they fit; one
  that doesn't fit is skipped, never half-loaded, and a smaller farther one may still fit. Always islands load
  regardless. `daedalus.StreamRamBudgetMiB` (0 = off) turns it on in game; `islands.json` rows may carry `ram_kib`.
  stream_core_test 20/20; 10,000 islands still plan in ~1.4 ms (hash sets, not a scan per step).
- **Chunk palette (rule 1, like a Minecraft chunk section):** `Chunk` stores a palette plus 0, 4 or 8 bits per cube.
  Empty or solid chunks hold no per-cube array (~60 B instead of 4 KiB); terrain chunks with 16 or fewer kinds hold
  2 KiB. Writes widen, `copy()`/load narrow. `occupied()` is O(1) now (it scanned 4,096 bytes on every remove).
  Reads stay lock-free (final fields in the store). Cost: get ~3 ns instead of ~2. ChunkPaletteTest 6/6 checks
  40 random edit runs against a dense model.
- **Realm mesher (web, rule 6's cost):** `realm-mesh.js` copies a chunk plus a 2-cube border into one flat array
  before meshing, so faces and AO corners are array reads instead of ~70 string-keyed Map lookups per cube; colours
  convert once per kind. Same bytes as the old mesher on 60 random chunks (`node tools/realm_mesh_check.mjs`), 2.4x
  faster; World Zero (53 chunks) renders the same in headless Chromium.
- **One request per world, run-length encoded (the wire side of rule 1):** `GET /api/v1/world/{id}/chunks/blocks`
  sends every non-empty chunk as base64 (ordinal, len lo, len hi) triples (`Chunk.runs()` / `Chunk.ofRuns`). World
  Zero: 53 chunks in 1 request and 35 KB, against 54 requests and ~320 KB (23 KB of runs vs 217 KB dense). realm.js
  uses it and falls back to per-chunk on an older server. The per-chunk endpoint stays for other clients.
- **Saved worlds as runs (DAEW version 14):** chunks are written as `Chunk.runs()` triples instead of 4,096 dense
  bytes. World Zero's file: 218 KB -> 25 KB (53 chunks); a 120-chunk test world: 494 KB -> 48 KB. Version 13 and
  older files still load (and re-save as 14, byte-identical to a fresh save); broken runs refuse the file. An older
  server cannot read a version-14 file, so roll servers forward, not back. In RAM the same worlds hold 114 KB and
  258 KB of chunk storage instead of 221 KB and 500 KB (the palette above).
- **Saves redo only dirty chunks (rule 6 for persistence):** every block edit snapshots and saves the world. A
  snapshot copied every chunk (4 KiB each) and the save re-encoded every chunk. Now `Chunk.copy()` shares storage
  copy-on-write, and each store caches its runs until written. A 200-chunk world: edit + save 6.0 -> 1.6 ms (the
  rest is the file write); the cost per edit no longer grows with the number of untouched chunks' cubes.
- **Saves are atomic and buffered:** `WorldStore.save` writes a temp file beside the world and moves it over in one
  step (retrying briefly when Windows holds the file, then falling back to a plain copy), so a crash or full disk
  mid-save leaves the last good world, not a truncated one. A buffered stream cut edit + save to ~1.1 ms on the
  200-chunk world. WorldStoreTest checks a save that dies half way leaves the old bytes and no temp files.
- **Greedy World Package meshes (rule 3 for exported worlds):** `WorldMesher.meshGreedy` and C++
  `MeshChunkGreedy` merge each chunk's visible faces into rectangles per direction and cube type (no per-cube grain,
  which is what made every face unique). Java and C++ match byte for byte (isle8.mesh.txt `greedy` lines, mesh_core_test
  91/91), and MeshFixtureTest checks the quads cover exactly the same unit faces, none twice. Measured: Gallery City
  183k faces -> 51k quads, glb 30.4 MB -> 8.7 MB; Parcels 58k -> 4.9k (9.7 -> 1.0 MB); Bricks 35k -> 436
  (5.8 MB -> 179 KB); World Zero 2.1x.
- **Unreal imports greedy by default:** the package endpoints take `?mesh=greedy` (cached apart from the per-face
  mesh; WorldPackageControllerTest 6/6), and `setup-unreal.ps1 -Mesh greedy` (default) / `import_world_package.fetch`
  ask for it, so an imported Gallery City is 51k quads instead of 183k faces in the editor. `-Mesh faces` keeps the
  old look with per-cube grain; live_parity still checks the per-face mesh against C++.
