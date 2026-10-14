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
