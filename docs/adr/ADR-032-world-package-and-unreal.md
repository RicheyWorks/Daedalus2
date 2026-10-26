# ADR-032: World Packages — generate once, deploy to any engine; Unreal Engine 5 first

**Status:** Accepted
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Charter:** ADR-029, slice 3
**Prompted by:** "making Daedalus engine-independent. Imagine generating a world once and being able to
deploy it into different game engines … this has always been the goal from the start." · "Unreal Engine
5 … we can start that now, make the plugin for it and handle the downloads via PowerShell." · "Blender
is our workhorse."

## Question

So far a Daedalus world could only be seen in one place, the web realm. The realm draws it with its
own mesher in `realm.js`. Blender only saw it through one-off scripts. Unreal could not see it at all.
What does a world have to become so that any engine can stand it up, and what is the least Unreal
needs in order to be the first engine that does?

## Decision

**1. A World Package is the unit of export.**
`GET /api/v1/world/{id}/package` returns `<id>-r<revision>.daedalus.zip`, which contains:

| File | Contents |
|---|---|
| `manifest.json` | format `daedalus-world-package` v1; the world (id, style, title, seed, revision); units and axes; geometry stats; the **palette** (ordinal, type, sRGB, `translucent`, `seeThrough` for every cube type); islands (slot, seed, radius, origin, dock, deed owner); sky gates (doorway, cloud berth, where they lead); arks (berth, MOORED or SAILING); the world's mount; the assets; where the live API and STOMP frames are; and the deed contract when one is configured |
| `world.glb` | glTF 2.0 binary, one node per 16³ chunk, `POSITION`/`NORMAL`/`COLOR_0` with uint32 indices. Material `daedalus_opaque`, plus `daedalus_translucent` (BLEND, double-sided) for water, glass, rainbows and gate doorways. Metres, +Y up, right-handed: glTF's own conventions, so no engine needs a transform |
| `assets/ark.glb` | The Blender-made ark (ADR-022), with its placement rule in the manifest |
| `README.txt` | What the package is, in plain words |

`/package/manifest` and `/package/world.glb` are also served on their own, so an engine can stream them.
All three routes are public, like the chunks they are made from.

**2. One mesher, written down once and then ported, never redrawn by eye.**
`WorldMesher` (core) is the Java version of the realm's rules:
- a face is drawn when the cube beyond it is see-through and of a different type
- faces are shaded ±X .86, +Y 1, −Y .62, +Z .94, −Z .78, times the per-cube grain
- colours are sRGB decoded to linear and clamped to 0..1, because glTF requires it

`BlockColors` is now the single colour table used by the portraits (ADR-027), the package and the
plugin. `IslandPortrait` reads from it, and its golden digest did not move. `Glb` writes the binary
glTF with no dependencies. Output is deterministic: the same world gives the same GLB and the same zip,
byte for byte, because zip entry times are pinned to the DOS epoch.

**3. Mesh once per revision; describe the world every time.**
Meshing is the expensive part. It runs on a private copy taken under the world lock (`WorldService.copy`)
and is kept until a cube changes (`WorldService.revision`). The manifest is rebuilt on every request,
because an ark sets sail without moving a cube. The GLB carries an ETag of `id-revision`. The zip
carries none, because it can change within one revision.

**4. The Unreal plugin, `engines/unreal/DaedalusLink`.**
- **`DaedalusMeshCore.h`** is the mesher in standard C++17 with no Unreal code in it, so Godot, a CLI,
  or anything else can use it. It matches Java to the bit: Java's `int` hash is reproduced with
  `uint32` wrap-around, and the decoded colour is held as a `float` before shading.
- **`ADaedalusWorldActor`** (shown in the editor as "Daedalus World"):
  - reads the manifest's palette, so a new cube type needs no new plugin
  - streams `/chunks` and `/chunk/blocks`
  - builds one `ProceduralMeshComponent` per chunk: an opaque section with collision, and a
    translucent section you can walk through
  - polls during play, refetches only chunks whose revision moved, and remeshes their six neighbours
  - glides arks between berths on the server's clock
  - `TravelThroughGate(g)` makes the actor the world on the other side of gate `g` (ADR-031)
  - Axes: Daedalus `(x, y, z)` m → Unreal `(x, z, y) × 100` cm. Swapping the axes turns right-handed
    counter-clockwise faces into the left-handed clockwise faces Unreal draws, so the indices stay as
    they are. `bFlipWinding` exists in case a project's materials disagree.
- **`Content/Python/import_world_package.py`** checks a package, then:
  - makes vertex-colour materials
  - imports `world.glb` and the ark through Interchange
  - places them in `/Game/Daedalus/DaedalusWorld` (made if missing, then saved)
  - adds a live actor that is already configured

  With `--live` it skips the bake. With `--dry-run`, or outside Unreal, it only checks the package and
  prints the plan; it exits 1 on an invalid package.

**5. `engines/unreal/setup-unreal.ps1` does the downloads.**
Every step checks first and says what it found, so the script is safe to run again:
- installs the Epic Games Launcher with `winget` (`-InstallLauncher`)
- finds UE 5.4+ from `LauncherInstalled.dat`, or opens the launcher's Library page when none is installed
- uses an existing project or makes a blank one
- copies and enables the plugin, along with ProceduralMeshComponent, PythonScriptPlugin and
  EditorScriptingUtilities
- downloads and checks the package
- `-Build` runs `RunUAT BuildPlugin` and installs the result
- `-Import` runs the Python import headless
- `-WhatIfOnly` prints the plan without changing anything

You sign in to Epic and accept the Unreal EULA yourself. The script passes no `--accept-*` flags.

## What it found

- **Colours over 1.0.** The first export failed Khronos validation with `ACCESSOR_NON_CLAMPED`: the
  brightest cloud, after its grain, reached 1.0028. The realm never noticed, because WebGL clamps. Every
  exporter now clamps, and the parity test pins it.
- **A cache that would have lied.** The first package service cached the whole package per revision.
  Revision counts cubes, and ships are not cubes, so an ark under way would have been reported as moored.
  The cache now holds only geometry, and a test sets sail and checks the manifest.
- **"Daedalus null".** `getImplementationVersion()` is null outside a packaged jar. The generator string
  now says `dev` there.
- **SpotBugs' exposed representations** (`int[]` coordinates, `byte[]` payloads). Coordinates are now
  immutable `[x, y, z]` lists. `Built` copies its bytes in and out, and a test writes into a returned
  copy and checks that the cache is untouched.
- **Setup script crashes, found by running it.** The script parsed cleanly, but under PowerShell 7 it
  stopped at step 2 because `$env:ProgramData` is null off Windows. It also told a user with a wrong
  world id that the server was down. Both are fixed. The second case now says "no world '<id>' (GET
  /api/v1/worlds lists them)".
- **A parity test that could not see winding.** The first C++ parity test compared faces, positions,
  normals and colours. A mutant that wound every face backwards still passed all 52 checks: right about
  every vertex, blind to the order they make a triangle in. Both sides now sum the index order too, and
  that mutant fails 23 of 52.

## Numbers

- **Island 11 (r18) plus gate 0:** 51 chunks, 13,845 faces, 27,690 triangles, a 2.37 MB GLB.
  - Khronos glTF-Validator: 0 errors, 0 warnings, for both the world and the ark.
  - three.js GLTFLoader: 51 nodes, 27,690 triangles.
  - Blender 4.3.1 import: 51 objects, both materials, vertex colours rendering.
  - The zip is 528 KB.
- **C++ parity.**
  - Committed fixture: 52/52, with 2,778 faces across 17 chunks, including every see-through kind
    touching every other.
  - Live: 53/53 on world-zero (13,845 faces, equal to the server's own GLB) and 48/48 on isle-two.
  - The canary (stone made see-through) is detected.
- **Mutants against `DaedalusMeshCore.h`:** 5 tried and 4 killed (−Z shade, the same-type cull,
  the hash shift, winding).
  - One is equivalent: changing the sRGB linear-segment divisor (12.92 → 12.9) cannot show, because no
    palette channel is ≤ 10, so that branch never runs for a cube colour. It is measured, not assumed.
- **Tests.** Java: `WorldMesherTest` 7, `MeshFixtureTest` 1, `WorldPackageControllerTest` 5. The posture
  test now covers 3 more public routes. Gate: `install` on 5 modules, green. Browser harness: a new
  "World Package" section. three.js loads the served GLB in the realm's own page, and it must carry
  exactly the triangles the realm draws.

- **CI.** `.github/workflows/engines.yml` runs the parity test with gcc and clang, checks that the
  import script refuses a non-package, and on Windows runs the setup's plan for real: it makes a
  project, then checks that the plugin was copied and enabled. The mesher also compiles and passes as
  C++20, which is UE5's default.

## Not verified here

There is no Unreal Engine in this sandbox, so these have not been run:
- The plugin compiled in UE. The C++ was syntax-checked with clang against stand-in Unreal headers.
- `import_world_package.py` running inside the editor. Its standalone checks and plan did run.
- `winget`, `RunUAT` and `UnrealEditor-Cmd`.

The first run on Windows is the test of these: `setup-unreal.ps1 -InstallLauncher -Build -Import`.

## Held

- **STOMP in Unreal** instead of polling. This waits until polling every 2 seconds is too slow for
  play. It needs the WebSockets module and a STOMP client.
- **Godot and Unity importers.** `DaedalusMeshCore.h` and the package are ready for them. They are held
  until someone asks for one of those engines.
- **Greedy meshing.** 27,690 triangles for an island is fine. This is held until a world's GLB
  exceeds 50 MB.
