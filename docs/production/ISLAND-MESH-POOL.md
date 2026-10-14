# Island mesh pool — Claude request 29882

team-codex produced 12 asteroid fragments and six terrace pads with the existing owned material helpers. Each GLB is one render object, 92 m by 92 m maximum footprint, origin at top centre and flat walkable top at local Z=0. Fragments are 8–20 m thick, with deterministic faceted undersides; pads are 1–3 m thick. Each render shell and convex companion is closed/manifold, with 24-point convex top outlines. Geometry is deterministic per variant; FBX export timestamps mean binary repeatability is not promised.

Actual output: `C:/Unreal/DaedalusRealm/Content/Daedalus/Art/Islands`.

- `Island_Frag_01.glb` through `Island_Frag_12.glb`.
- `Island_Pad_01.glb` through `Island_Pad_06.glb`.
- Matching `.fbx` companion with one genuine closed convex `UCX_<name>_00` mesh.
- Matching `.collision.json`, coordinates explicitly Blender metres/+Z up.
- `island-mesh-pool.blend`, `island-mesh-pool.png`, and `island-mesh-pool.json` with hashes/metrics.

Regenerate with Blender 4.3: `blender --background --python tools/blender/island_mesh_pool.py -- OUTPUT --render`. Partial counts are bounded by `--fragments` (0..12) and `--pads` (0..6); an empty pool is refused. The manifest checkpoints each complete exported asset, so a completed partial batch can unblock the importer.

The GLB contains render geometry only. Named UCX collision is supplied through the companion FBX, following [Epic's FBX collision naming/pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine). Do not claim UCX collision imported through GLB automatically. Use either the FBX as the native static mesh source or apply the sidecar hull through the approved native collision path. Check the resulting StaticMesh collision and a player walk in Unreal. Keep One Convex Hull Per UCX enabled for the supplied single hull; the source collision mesh is already convex.

**Instance transforms:** expected imported bounds are 9,200 cm across and thickness ×100 cm. The old Engine Cube is 100 cm wide; this pool is already 92 m. Normalize old XY instance scales by 92, or compute new scale as desired width/92. Z scale is desired thickness / exported thickness. Top-centre translation places the mesh's local origin on the intended walk surface. Preserve per-deed decoration, actor ownership, ISM grouping and estate boundaries; do not move a land to compensate for wrong import scale.

Validation: actual Blender export of all 18 GLBs/FBXs, manifold checks, 92 m bounds, flat top/thickness checks and retained GLB hashes. Review camera far clip explicitly extends to 5,000 m to include every row. Render and manifest are presentation evidence; native bounds/collision/import and in-game walking are not yet proven. Claude owns assignment to district ISMs and that runtime proof. No Unreal command was called by this generator.

The actual 18 GLBs, FBX/collision companions, editable blend, review PNG and manifest are also retained in `engines/unreal/art/island-mesh-pool` in this branch, so the handoff can be recovered from GitHub without relying on the local Unreal checkout. Native import is still owner-controlled; no uasset or live level is replaced by this package.

## Native acceptance checkpoint — 2026-10-14 10:21 UTC

First four fragments were imported through the new Epic ModelContextProtocol connector using the existing `tools/unreal_mcp/client.py` HTTP client. Native folder: `/Game/Daedalus/Art/Islands/NativePool`. Each returned a StaticMesh reference; native `get_bounds` reports XY 9,200 cm and max Z=0. `ObjectTools.list_properties/get_properties` read back bodySetup/aggGeom: one convex hull, custom collision enabled, three material slots per mesh. All seven mesh/material packages were saved and their actual uasset file mtimes/sizes checked. Exact mesh/readback results are retained in `island-mesh-pool-native-report.json`.

This supersedes the import-pending statement above for Frag_01..04 only. Remaining fourteen meshes, district instance assignment, in-game walking and packaged inclusion remain pending. No land actors, district layout, materials elsewhere, editor settings or Play session were changed. Native IsPIERunning returned false, the current level was DaedalusWorld, the latest recorded job was terminal and the shared unreal lease was held by team-codex during imports. A legacy job exit marker of zero was not interpreted as a passing scenario: its tail reported 21/22.

## Complete native pool — 2026-10-14 10:27 UTC

All 18 meshes (12 fragments and six terrace pads) now pass native bounds, top-origin, material-reference and single-convex-hull readback. Native folder stays `NativePool`; 18 meshes plus five materials are saved as 23 uasset packages, with hashes/mtimes in `island-mesh-pool-native-files.json`. Full per-mesh collision vertices and bounds are retained in `island-mesh-pool-full-native-report.json`. Instance assignment, walking and cooked inclusion remain pending.

Reusable acceptance runner: `tools/unreal/island_pool_acceptance.py --client-root <existing tools/unreal_mcp directory> --source <export pool directory> --output <receipt.json>`. Default mode verifies without mutation. `--first/--last` bound the batch; `--import-new` checks source hashes and refuses existing mesh packages/import journals, requires team-codex's hub lease, checkpoints before dispatch and stops on failure without replay. `--save-verified` saves only observed mesh/material packages under the same lease. No editor settings or actor layout change.

Actual interruption: first pad imported correctly but the initial verifier incorrectly required fragment-specific three slots. Source generator confirmed pads have two slots; the checker was corrected, the already imported pad was inspected rather than reimported, and all 18 passed. This was a verifier assumption error, not an FBX/import failure.

## Additive World Zero placement pilot — 2026-10-14 10:31 UTC

Native MCP placed `RockShell_WZ_Deed1` (StaticMeshActor_3852) using Frag_01 at (40450,-9500,4022) cm, unit scale, below the existing 12m-thick Land_1 cube. The original actor1241 remains at (40450,-9500,4620), scale(92,92,12), with its original Land/Realm/Deed1/District55 tags. It was not replaced, moved or relabeled; props and floor are preserved. The new shell has a separate label, so it does not create a second Land_ deed. Native transform/tag readback and exact map save/hash evidence are in `island-rock-placement-pilot.json`; pre-mutation map backup stays local.

`set_actor_folder` timed out; this was not treated as failed creation. Readback found exactly one new actor and preserved original state. `save_assets` returned true and the map hash changed. Screenshot attempt through native CaptureViewport failed mid-response: 3,470,375 bytes received of 3,512,149, connection reset10054. No PNG or visual-quality acceptance claimed and no automatic retry. This pilot proves saved placement/state preservation, not appearance, walking or packaged inclusion. Do not expand until visual review.

## Actual native visual review — 2026-10-14 10:35 UTC

Two complete native CaptureViewport PNGs were received and inspected: close underside2,462,189bytes and oblique4,117,455bytes. Close view confirms the dark faceted underside; oblique shows preserved primitive floor/decor. These are evidence of current appearance, not a claim that the terrain has reached finished quality. Underside lighting/readability and base-floor treatment need polish; the pilot is not approved for expansion. Local review PNGs are under Documents/Codex/2026-10-14/project-inventory; their hashes/camera poses are retained in `island-pilot-visual-review.json`.

A distinct diagonal-side capture also reset mid-body (2,946,200of3,008,399bytes). The larger successful capture disproves a fixed3MBpayload cutoff. Installed EpicCaptureViewport reads active viewportSizeXY and offers no resolution/compression parameter; it restores temporary camera/showflags. Transfer cause remains unproven. Send failures and successes together to the harness owner, not just a threshold hypothesis. No settings or engine patch were used, and no failed mutating scene action was replayed.

## Component-only material reuse — 2026-10-14 10:43 UTC

Native MaterialInstanceTools.list_parameters confirmed BasicShapeMaterial actually exposes Color/Roughness. Existing Claude MI_Orr_Grass (Color .22,.5,.25) and MI_Orr_Rock (.33,.30,.38) were reused through component overrideMaterials on Land_1 and RockShell_WZ_Deed1 only. Shared material assets, static meshes, transforms and deed tags were unchanged. Before-bindings/map backup remain local, native before/after bindings and changed-map save evidence are retained in `island-material-pilot.json`.

The operation's final save response timed out20s; readback confirmed both bindings had applied, so neither override was replayed. After reconciling meshes/transforms/tags, a save returned true, with changed map hash and mtime10:42:37.711UTC. Native capture `rock-pilot-grass.png` (4,012,042bytes) was received/viewed from the same oblique pose: a green plateau patch is visible, original decoration stays. This is material/appearance progress, not finished terrain or walking proof; the surface still needs textural/vegetation detail.

## Existing-asset grove — 2026-10-14 10:56 UTC

Added and saved eight existing DiskSaver trees (variants08/13/18/23) in four edge clusters on the pilot. Actual native asset bounds/triangles, eight unique actor labels and transforms, ground traces and original floor/deed preservation are retained in `island-grove-placement.json`. Heights6..7.6m are derived from native bounds; rotated canopy bounds stay inside the floor and outside a12m central corridor. This is a visual-only grove, not new ecology entities, interactable trees or quest implementation.

Reusable source `tools/unreal/island_grove_pilot.py` defaults to a read-only checked plan. --apply requires solelease, exactflooridentity, unobstructed ground traces, absent labels/journal and local mapbackup. It checkpoints before each spawn and immediately after receiving actor identity; compares native transform with plan; stops without replay on uncertainty. Source is deliberately scoped to the one pilot, not a full-realm actor scatter.

Initial finalsave response timedout20s after all eight placements; eight unique labels/transforms/floor identity were reconciled without respawning, then a save returnedtrue and changed the map hash (mtime10:53:20UTC). Initial timed capture failed after19.39s (5,368,440of5,394,441JSONbytes); complete failure receipt is retained in `island-grove-capture-failure.json`. One deliberate fresh read-only observation subsequently received a4,037,805bytePNG, actuallyviewed at the same oblique pose: green treeclusters are visible, with two trees occluded by preserved original decoration. This confirms visible placement, not finished terrain or walking. Poot/helperreceived exacttiming/error/sourcehash data30112/30113. No sharedasset, transportsource, editorconfig, Play or districtconversion changes.
