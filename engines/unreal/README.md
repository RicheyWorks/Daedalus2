# Daedalus in Unreal Engine 5

Generate a world once, then deploy it to any engine (ADR-029, ADR-032). This folder holds everything you
need on the Unreal side. It is MIT licensed, like the rest of Daedalus.

| Path | What it is |
|---|---|
| `setup-unreal.ps1` | One PowerShell script that does the whole setup: the Epic launcher (through winget), finding UE 5.4+, a project, installing and enabling the plugin, downloading the World Package, building, and importing. |
| `DaedalusLink/` | The UE5 plugin. Its **Daedalus World** actor streams a live world from a Daedalus server and keeps it current. |
| `DaedalusLink/Content/Python/import_world_package.py` | An editor script that imports a World Package as materials, chunk meshes and the ark, and adds a live actor to the level. |
| `DaedalusLink/Source/DaedalusLink/Public/DaedalusMeshCore.h` | The cube mesher, in standard C++17 with no engine code. It follows the same rules as the Java exporter and the web realm. |
| `core-test/` | Parity tests that check `DaedalusMeshCore.h` against the Java mesher and against a live server. |

## Quick start (Windows)

You still have to do two things yourself: sign in to Epic, and accept the Unreal Engine EULA. The
script never does either for you.

```powershell
cd Daedalus2\engines\unreal ; .\setup-unreal.ps1 -Project C:\Unreal\DaedalusRealm\DaedalusRealm.uproject -InstallLauncher -Build -Import
```

To see what it would do without changing anything, add `-WhatIfOnly`. Other options:

- `-Server http://host:8088`: which Daedalus server to download from
- `-World <id>`: which world to download
- `-EnginePath D:\UE_5.5`: use an engine the launcher does not know about (the script otherwise looks in
  the launcher's list, the registry and `<drive>:\Epic Games\UE_*`, and takes the newest)
- `-NoServerStart`: don't start a local server

What it downloads for you, when missing:
- **A Daedalus server.** If `-Server` is on this PC and not answering, the script builds the server
  and starts it in its own window. It installs Java 21 (`winget`, Microsoft OpenJDK) and Maven
  (from Apache, into `%LOCALAPPDATA%\Daedalus`) if they are missing.
- **The C++ tools** (`-Build`). Visual Studio 2022 Community with "Game development with C++", via
  `winget`. This is a large download, and its installer shows its own license and progress.

## The Daedalus World actor

Drop **Daedalus World** into any level and set **Server Url** and **World Id**. Then press **Load World**
in the Details panel, or press Play.

1. **On load**, it reads `/package/manifest` (the palette, islands, sky gates and the world's mount), then
   `/chunks`, then `/chunk/blocks` for each chunk.
2. **It meshes each chunk** with `DaedalusMeshCore.h`. Each chunk becomes a `ProceduralMeshComponent`
   with two sections:
   - opaque cubes, which have collision
   - translucent cubes (water, glass, rainbows, gate doorways), which you can walk through
3. **During play**, it polls every `PollSeconds`. It refetches only the chunks whose revision changed,
   and remeshes their neighbours as well. Arks glide between berths using the server's clock.
4. **`TravelThroughGate(Gate)`** makes the actor the world on the other side of that gate. This is the
   Unreal side of the sky gates from ADR-031.

Coordinates: Daedalus uses metres, +Y up and is right-handed. Unreal uses centimetres, +Z up and is
left-handed. A Daedalus `(x, y, z)` appears at Unreal `(x, z, y) × UnitsPerCube` (the default is 100).

## Checking it here (no Unreal needed)

```bash
cd engines/unreal/core-test && g++ -std=c++17 -O2 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public mesh_core_test.cpp -o mesh_core_test && ./mesh_core_test isle8.mesh.txt
```

- `isle8.mesh.txt` is written by `MeshFixtureTest` in `daedalus-core`. If the Java mesher changes, that
  test fails until the fixture is rewritten with `-Ddaedalus.fixtures.write=true`, and this test then
  shows whether Unreal still agrees.
- `python3 live_parity.py http://localhost:8088 world-zero > live.mesh.txt && ./mesh_core_test live.mesh.txt`
  reads a running server the way the actor does, and checks the result against the server's own
  `world.glb`.
