# ADR-058: One voxel isle core in three languages, and art built in the cloud

**Status:** accepted, 2026-10-12. **Author:** unreal-team (Claude).

## Why

The Orrery Reach (ADR-057) is built from voxel isles: Claude Island and four neighbours. Three places need the same
isle:
- Unreal draws it (`ADaedalusVoxelIsle`), and placement scripts stand things on its ground.
- The web realm should show the same domain to anyone with a browser.
- The Java server owns worlds, so it should be able to say what an isle is.

Before this ADR, the shape lived only inside an Unreal actor, written with `FMath`. Nothing could check it without
an editor, and a web copy would have drifted.

There was a second problem. Blender on Richmond's PC competes with Unreal for RAM, and only one editor fits.

## Decision

1. **One core, ported line for line, proven equal.**
   - `DaedalusVoxelIsleCore.h` is the shape in plain C++: no Unreal types, double precision, and no trig
     (`cos(atan2(y, x))` is `x / r`). `ADaedalusVoxelIsle` calls it.
   - `com.daedalus.world.island.VoxelIsle` (Java) and `static/reach-core.js` (browser) are line-for-line ports.
   - `core-test/voxel_isle_core_test.cpp --write voxel_isle_parity.txt` records seven isles: the five real ones
     plus two odd ones, a negative seed and `INT_MAX`. For each it records column and cube counts, cubes per layer,
     an FNV-1a hash of every cube, and 24 sample columns.
   - `VoxelIsleTest` (Java) and `tools/reach_parity.mjs` (node) recompute that file. One cube moved on any side
     fails.
   - The Orrery rules got the same treatment: `DaedalusOrreryCore.h`, which holds the herbs, brews, steeping and
     logbook, has a 37-check ASan/UBSan test.
2. **The web view reads the server.**
   - `GET /api/v1/reach/orrery` serves the five isles: settings, offsets, and column tops and bottoms as base64
     int16. It is public and cached.
   - `/reach.html` grows the cubes with `reach-core.js` and spot-checks its columns against the server's. The status
     line shows the result.
3. **Art is built in a cloud Blender.**
   - `tools/claude_island/orr_hq.py` rebuilds all 509 Orrery items with headless `bpy` 5.2:
     - bevelled boxes;
     - twice the curve segments;
     - smooth shading by angle;
     - metal, gloss and rough materials.
   - It exports glb plus `sent.json`, and runs the judge's Blender = file checks on each before keeping it.
   - The art watcher now ships a glb that is at least as new as the asset's `.blend`. That way a cloud rebuild
     replaces old PC art without deleting anything.
4. **Preflight before a build slot.** `tools/unreal_preflight/preflight.py` runs first in `unreal-job.ps1 -Run`.

## What it found

- The parity hash disagreed on its first run, even though every count matched. The cause was the C++ test's FNV
  offset: it was missing a digit. The Java side was right. This shows why the file carries counts *and* a hash: the
  counts said the shapes agreed, and the hash pointed at the test.
- Headless `bpy` exports nothing with `use_selection=True`: the file was a 132-byte glb. Because the judge compares
  the report with the file, every asset was refused, not shipped. `orr_hq.py` now exports the whole (single-asset)
  scene.
- The posture tests refused the new endpoint twice until it had a row in each table, the code's and the README's,
  as they should.

## Numbers

- Claude Island: 52,438 columns, 117,627 visible cubes. The whole Reach is 195,246 cubes in the browser.
- C++ isle test 14/14, Orrery core 37/37, Java parity 4/4, node parity 7/7, and artqueue 63/63.
- Cloud art: 509 of 509 built at full quality and under budget, with 0 judge failures.

## Held

- Moving `ADaedalusVoxelIsle` from `float` and UE's fast `Atan2` to the double-precision core can shift a terrace
  by a step. Before the change is relied on, re-run `orr_place.run()` and `orr_reach.run()` in the next editor
  slot, so props sit on the new ground. The trigger is the next Unreal rotation slot.
- MSVC's `pow` may differ from glibc's in the last bit. Parity is proven on Linux, Java and V8, but not yet against
  an MSVC build. The trigger is the next Windows `core-test` run (`run_sol_core.cmd` pattern), which should write
  its own parity file to diff.
