# Codex original-derived voxel islands

These are new seeded variants, preserving every original asset. The complete initial 13-entry catalog is in `original-islands-inventory.json`; its limitations distinguish historical images, component sheets, source designs and native acceptance. Seven historical island images and the Sol/Orrery component sheets were inspected. Missing whole-scene views are recorded, without guessed authorship.

| Preset / seed | Original design used | Evidenced author / team | New design features |
| --- | --- | --- | --- |
| summit-rim / 84011 | Blender Boss Island | blender-team / unknown | Circular water rim, stepped central summit, pastel voxel trees |
| cliff-garden / 84022 | Buffffff / Six-F | buffffff / Grok | Enclosing cliff bowl, colourful crop grid, lime/cyan/lavender accents |
| river-canyon / 84033 | Prometheus Island | prometheus / Grok | Branching canyon, gold-green plateaus, white pillar ring |

Each receipt embeds source-image paths, original author evidence, catalog SHA, seed/config/source SHA and deterministic voxel SHA. Body XY fits within 92 metres; clouds can extend outside it. Native actor scale is 1 because geometry is exported in metres. Collision uses equal-height rectangular UCX patches; the jagged underside is approximated, and native collision remains unverified.

## Generate and export

Ordinary Python prepares plans without opening editors:

```powershell
python tools/blender/codex_contest_island.py --plan-only --all
python tools/blender/codex_contest_island.py --plan-only --preset river-canyon --seed 84133
```

After obtaining the existing hub's Blender turn, use the installed Blender executable. `--background --factory-startup` uses an isolated scene; the script reuses `voxel_island.plan`, `_mesh_from_voxels`, `asset_pipeline.sides.BLENDER_EXPORT`, `ship.prebuilt`, file witnesses and hashes. It never calls the existing generator's global island cleanup or saves the shared scene.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 4.3/blender.exe' --background --factory-startup --python tools/blender/codex_contest_island.py -- --all
```

Export-cache hits require matching source/config and matching GLB/FBX bytes. The FBX includes every selected island layer plus named UCX, rather than only the terrain. Receipts and batch metadata are checked in; binary exports remain local intermediate artifacts.

Measured Blender 4.3.1 export on BLACKBEARD, 2026-10-14; seconds are receipt stages, with no comparison/speedup claim:

| Preset | Generation | Mesh | GLB export + witness | FBX + collision |
| --- | ---: | ---: | ---: | ---: |
| summit-rim | 0.246018 | 0.736664 | 0.904279 | 0.553915 |
| cliff-garden | 0.272723 | 0.899757 | 0.379183 | 0.505621 |
| river-canyon | 0.270194 | 0.813635 | 0.355320 | 0.273257 |

## Deliver during the accepted Unreal turn

`tools/unreal/codex_contest_island_delivery.py` composes the existing Epic MCP client, native FBX import, asset metadata, material, actor and explicit save tools. Hash revision folders avoid overwriting originals. Matching package SHA/config metadata permits an unchanged import skip; retained unfinished journals require outcome inspection before another attempt. A source hash alone never proves native delivery.

Supply all three exported `.receipt.json` paths, plus an owner-agreed placement JSON mapping the three island names to free `[x_cm,y_cm,z_cm]` coordinates, the current map package and its actual `.umap` file. The script verifies current level, layer count, metre-to-centimetre dimensions, material slots, source metadata, exact reused actor identity and transforms. It creates only new Codex actors; no cell clearing, actor deletion or implicit movement is performed. One explicit batch save includes only the prepared assets and agreed map. A new placement requires changed map bytes after the native save. Import-only runs report `assets_saved`; completed placement reports `placed_and_saved`.

Actual asset-only delivery completed in Claude's explicitly opened temporary window (hub30667), and the editor was released in hub30681. `daedalus_codex_prepared_assets.py` reused the existing AssetImportTask pattern and `daedalus.steps` route, yielding between payloads. All three island families and 21 modules are imported and saved: 47 unique native StaticMeshes, 47 true save returns and 47 `.uasset` files present on disk. Exact paths/material readbacks are in `codex-prepared.unreal.json`; `codex-saved.delivery.json` contains disk evidence and a compact summary. No world placement or map save occurred.

All 47 native meshes reported `InterchangeAssetImportData` and Nanite disabled. Requested FbxImportUI flags remain separate from observed settings; those import-data fields were unavailable through Interchange and are not claimed applied. The resumed 24-step batch took 21.6 seconds; recorded import stages for 23 new tasks sum to 14.454402 seconds, and its 47 saves sum to 1.602452 seconds. The first module's separate import/name recovery is excluded from those stage sums; no comparative speedup is claimed.

The first single-mesh module was renamed to the task's destination name. Exact source-file SHA, 400×100×50 cm bounds and palette slots were inspected before assigning the existing vertex-colour material and saving, without reimporting. The adapter now accepts that alias only for a single expected source object and persists returned import paths before validation can raise.

HeroR2 seed84011 is a separate retained export in `HeroR2/h84011`, with overview/route/crown renders in `HeroR2/QA`. It adds a pale summit route, fitted crystal crown and Blender surface recipes. It remains held from native import and world placement; one-metre route steps are a known refinement gap, and stills do not prove movement. Reproduce into a new output revision with `--hero --preset summit-rim --seed 84011 --out NEW_FOLDER`; existing mismatched export revisions now refuse overwrite. `review_codex_hero.py --receipt RECEIPT --out QA_FOLDER` reproduces the three source views in an isolated factory Blender process.

## Reusable production lessons

1. UE 5.8's configured FBX default ignores vertex colours; the existing native `import_file` does not override it. Named palette slots preserve colour through reusable owned material instances without changing shared import settings. One parameterized base and colour-hash instances are shared across islands.
2. BMesh byte-colour attributes expose both sRGB and linear values. The first export read linear `.color` to identify the existing sRGB palette and incorrectly mapped grass/rock to dirt. `.color_srgb` fixes key identification; the corrected actual export witness includes the expected grass, rock and sand slots. New palette values are then written in linear space for consistent receiving material parameters.
3. Existing actor transforms alone cannot prove a changed mesh revision was delivered. Verify the exact label and static mesh path as well, and retain the pending call target before dispatch so uncertain results can be inspected without blindly repeating writes.

Syntax parsing and real Blender generation/export were completed. Harness and gameplay tests remain deferred by the user's production workflow; these assets are not a walkability or gameplay acceptance claim.
