# ADR-062: BBA 1 asset LOD manifest and LOD selection (blender-team)

Status: accepted (code), in-game demo pending (unreal-team). Owner: Blender Boss / blender-team.

## Context
The Blender pipeline ships 5,457 catalog glbs, 3,447 with a `_LOD1` sibling at about 60-65% of the faces. Unreal, Java and the tools had no shared record of which assets have a LOD1, how big they are, or when to switch to it.

## Decision
- `BBA 1` is a plain-text manifest with one line per asset: `asset <id> lod0 <faces> lod1 <faces|-> radius <cm> switch <cm>`. All values are integers (faces and Unreal centimetres), and a bad line refuses the whole file with `line N: why`.
- `tools/islands/blenderboss/bba_manifest.py` writes `data/assets/catalog.bba` from the glbs. It reads the glTF accessors directly, so it doesn't need Blender. The default switch distance is 20 bounding radii, and never less than 5 m.
- Selection: draw LOD1 when it exists and distance >= switch. Budget: apply the distance rule first. Then, while the scene is over its face budget, switch the farthest LOD0 instances that have a LOD1 (ties go to the lower id, then the lower index).
- The header-only `DaedalusAssetLodCore.h` (plain C++17) and `com.daedalus.world.assets.AssetLodManifest` (Java) agree byte for byte. `core-test/asset_lod_core_test.cpp --write` writes `asset_lod_parity.txt`: 40 manifests, 240 selections, 120 budgets and 20 refusals. `AssetLodParityTest` reads it.

## In-game proof (pending)
The Blender team island in DaedalusWorld swaps catalog props to their `_LOD1` at the manifest switch distance, captured in game. This needs an unreal-team window.

## Addendum (unreal-team, 2026-10-13): how Unreal applies it
`DaedalusLink/Content/Python/daedalus_lod.py` puts each `_LOD1` glb into its static mesh as LOD 1 and sets LOD 1's
screen size to what the mesh covers at the manifest's switch distance (Unreal's ComputeBoundsScreenSize, 90 degree
FOV, 16:9: 1.778 r / d, so the default 20 radii is 0.089). The GPU then switches by itself; no per-frame code. `plan()`
is a dry run; `apply()` touches only meshes under the folder it is given whose names are manifest ids, and only
LOD 1. Its BBA parser is a port of DaedalusAssetLodCore.h: test_daedalus_lod.py replays asset_lod_parity.txt
(40 manifests, 240 selections, 20 refusals) 9/9. Running `apply` on blender-team's folder waits for their OK and an
editor turn.
