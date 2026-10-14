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

The earlier asset-only delivery completed in Claude's explicitly opened temporary window (hub30667), and the editor was released in hub30681. `daedalus_codex_prepared_assets.py` reused the existing AssetImportTask pattern and `daedalus.steps` route, yielding between payloads. All three island families and 21 modules were imported and saved: 47 unique native StaticMeshes, 47 true save returns and 47 `.uasset` files present on disk. Exact paths/material readbacks are in `codex-prepared.unreal.json`; `codex-saved.delivery.json` contains disk evidence and a compact summary. That temporary window included no world placement or map save; later staging is recorded below.

All 47 native meshes reported `InterchangeAssetImportData` and Nanite disabled. Requested FbxImportUI flags remain separate from observed settings; those import-data fields were unavailable through Interchange and are not claimed applied. The resumed 24-step batch took 21.6 seconds; recorded import stages for 23 new tasks sum to 14.454402 seconds, and its 47 saves sum to 1.602452 seconds. The first module's separate import/name recovery is excluded from those stage sums; no comparative speedup is claimed.

The first single-mesh module was renamed to the task's destination name. Exact source-file SHA, 400×100×50 cm bounds and palette slots were inspected before assigning the existing vertex-colour material and saving, without reimporting. The adapter now accepts that alias only for a single expected source object and persists returned import paths before validation can raise.

After the full editor handoff, the three saved islands were assembled at scale 1 in `/Game/Daedalus/DaedalusWorld`: cliff-garden has nine layer actors, river-canyon nine and summit-rim eight, totaling 26. `codex-cliff-staging.world.json` and `codex-remaining-staging.world.json` record exact actors, mesh paths, transforms, true map-only save returns and changed map fingerprints. The additive `codex_saved_asset_assembly.py` helper places only receipt-bound saved meshes and refuses conflicting existing actors.

The later workshop dressing added all 21 saved module variants plus six BridgeCoupler support copies, nine actors per island and 27 total. `codex-workshop.dressing.json` retains the fitted placements; `codex-workshop.world.json` records all 55 native mutations responding and a true map-only save. The resulting 53 Codex actors are staging actors in `CodexContest/Staging` and `CodexContest/Staging/Workshops`, with no ownership/admission tags added. Dressing took 5.684576 seconds and the map save 21.320304 seconds, as recorded in that receipt. The saved map SHA is `9da80c3ff526988e8897b7e6f7e0c38153aad7b19db16dd2ff83f595042c48cc`. These receipts establish saved staging; importer admission and movement/gameplay acceptance remain separate.

`tools/unreal/codex_workshop_terrain.py` promotes the source-only terrain recipe into a reusable folder CLI. It reuses the island planner, verifies each original voxel SHA and retains the exact clear flat patches, colour variants and coordinator-agreed staging origins in `codex-workshop-source-plan.json`. Origins are metadata from this accepted staging turn; they do not authorize future placement. Native local bounds and orientation fitting are recorded separately in `codex-native-local-bounds.json` and the dressing plan. No editor connection or export occurs when preparing this source plan:

```powershell
python tools/unreal/codex_workshop_terrain.py engines/unreal/DaedalusLink/Content/IslandSource/CodexContest
```

Matching existing plans are reused; a differing retained plan requires a new `--out` path.

HeroR2 seed84011 is a separate retained export in `HeroR2/h84011`, with overview/route/crown renders in `HeroR2/QA`. It adds a pale summit route, fitted crystal crown and Blender surface recipes. It remains held from native import and world placement; one-metre route steps are a known refinement gap, and stills do not prove movement. Reproduce into a new output revision with `--hero --preset summit-rim --seed 84011 --out NEW_FOLDER`; existing mismatched export revisions now refuse overwrite. `review_codex_hero.py --receipt RECEIPT --out QA_FOLDER` reproduces the three source views in an isolated factory Blender process.

HeroR3 is retained separately in `HeroR3/h84011`, with the same three camera views inspected in `HeroR3/QA`. The route alone uses quarter-metre exposed-face geometry fitted onto the metre terrain; the whole island is not subdivided. Recipe: `--hero --hero-revision HeroR3 --preset summit-rim --seed 84011 --out NEW_FOLDER`. It exported ten meshes, GLB SHA `56c6b939a326b7474e9cd96d8b4a38f9a69ccf88b2b41556315a4238d4c807f9` and FBX SHA `47d14ae998b1e6a28c51404fc81e722a4f21795acf4f4654ed13357e01b5a987`. HeroR2 remains intact as a source comparison. HeroR3 subsequently completed a guarded ten-mesh native save and identical-input skip through PR146, under `/CodexContest/Ingestion/f0499dd9dad812f597cf54dd`; exact evidence is in `codex-hero-r3.adoption.json` and its native receipt. After footprint acceptance30806 and fresh native clearance, all ten layers were additively placed at `[-343550,297700,17515.324]` cm and saved, retaining the original three islands. Its vivid palette is saved, with overview/route/crown native captures in `QA`. The latest map SHA is `07ba7e6aa40583978d0b1b7d7d410b97dc23713b33e453b411ff4d5272753a1f`, 209237569 bytes. This gives four named island instances (three seeds and a hero revision), 63 staging actors and 63 saved StaticMesh assets; the matching numbers describe different sets. Movement/collision acceptance remains unverified.

The five-part seed86100 power unit also completed a guarded native save and identical-input skip under `/CodexContest/Ingestion/e3f098e65a1dc4ddb1129b79`. It remains an asset-only assembly with zero world actors. Its three Blender views and exact source connection recipe are retained in `SalvageAssemblies`; no runtime electrical or snapping implementation is claimed.

## Reusable production lessons

The reviewed PR146 adapter at `05fc3c2521c62e06de88bf85106eee0dd55086ab` was used through the existing ticked bridge after the saved workshop checkpoint. One BridgeCoupler imported and saved in a separate `/CodexContest/Ingestion/1ada37f4787d5ef4ce7678f0` revision; the identical-input second pass reported `unchanged_skipped=true`. `codex-adapter-adoption-fixed.json` and `NativeReceipts/codex-ingestion-1ada37f4787d5ef4ce7678f0.json` retain actual loaded hashes, native save proof and output witnesses. The earlier pre-admission failure is retained separately. No fingerprint guard was bypassed, and the original prepared manifest/importer/47 assets remain unchanged. This extra revision is one additional mesh asset, not another placed island.

The initial `QA/*.native-overview.png` and `QA/cliff-workshop.png` captures record the pale appearance with the shared vertex-colour material. Later `QA/*.palette-native-overview.png` and `QA/cliff-workshop.palette.png` record the vivid owned palette on the same staging. Per-slot **component overrides** use source sRGB colours converted to linear material parameters, plus owned roughness/metallic profiles; the prepared mesh packages and shared material are unchanged. The 18 cliff overrides required a separate known-outcome map-save reconciliation; remaining35 used `modify()` before material assignment. The latest explicit map save returned true, SHA `9b62e8d19f2d957f597f8ce4b7915e59973b11343624fae5a5fa5c08f6bca4a6`. No exposure, lighting, project or Nanite settings changed. Stills prove appearance only, not the final visual bar, collision or motion.

1. UE 5.8's configured FBX default ignores vertex colours; the existing native `import_file` does not override it. Named palette slots preserve colour through reusable owned material instances without changing shared import settings. One parameterized base and colour-hash instances are shared across islands.
2. BMesh byte-colour attributes expose both sRGB and linear values. The first export read linear `.color` to identify the existing sRGB palette and incorrectly mapped grass/rock to dirt. `.color_srgb` fixes key identification; the corrected actual export witness includes the expected grass, rock and sand slots. New palette values are then written in linear space for consistent receiving material parameters.
3. Existing actor transforms alone cannot prove a changed mesh revision was delivered. Verify the exact label and static mesh path as well, and retain the pending call target before dispatch so uncertain results can be inspected without blindly repeating writes.
4. A Python component `set_material()` readback and a true map-save return did not persist the first overrides: map bytes stayed identical because the package was clean. Mark the exact owned actor/component dirty with `modify()` before changing properties, then verify an explicit map-only save changes the bytes. Retain the first outcome and reconciliation separately.
5. The installed material tool binding rejected `usedWithNanite`/`usedWithInstancedStaticMeshes`, and its `list_parameters` call was unavailable. The existing native `MaterialEditingLibrary` path worked for the owned palette after inspection confirmed a zero-expression stub. Reuse validated, clean palette instances without resaving them; do not change shared material or editor settings to repair an owned asset.

Syntax parsing and real Blender generation/export were completed. Harness and gameplay tests remain deferred by the user's production workflow; these assets are not a walkability or gameplay acceptance claim.
