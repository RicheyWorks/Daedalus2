# Native Gallery construction

The reusable source is `engines/unreal/DaedalusLink/Content/Python/daedalus_codex_native_geometry.py`. Importing it performs no Unreal work. It uses installed Geometry Script APIs to create one new StaticMesh without Blender, payload import, booleans or separate cube actors.

Status: the initial native StaticMesh creation attempt crashed on the engine assertion `NumUVs > 0`: the original vertex buffers omitted UV0. It did not reach material binding or a confirmed asset save. The source now supplies UV0 before append, box-projects it and validates every triangle before persistent creation. A subsequent transient call stopped safely before persistent creation because a math factory was unavailable; the source now uses the actual documented `Transform.translation` and `Transform.scale3d` properties. Persistent creation, saving, placement and saved readback of this corrected revision remain unverified. No native visual or gameplay acceptance is claimed.

This standalone experiment is parked. Its source and failed revision are retained; production follows the requested ingestion, polish, then further ingestion order.

## Hollow planter recipe

All coordinates are native Unreal centimetres. Defaults are width 300, depth 160, height 80 and wall/floor thickness 12. The base pivot is `(0,0,0)`; bounds are `(-150,-80,0)` to `(150,80,80)`. The cavity is 276×136cm with its floor at Z12. Future actor scale is `(1,1,1)`.

Four counterclockwise rings contain 16 positions: outer bottom, outer top, inner floor and inner top. Four outer walls, four inner walls, four rim strips, the bottom and the cavity floor form 14 quads, split into 28 triangles. The visible cavity opens upward, while the solid shell has one connected component and no boundary edges. Per-face normals retain the cut-block appearance.

`planter_buffers(...)` returns pure vertex/triangle data plus the recipe. `make_planter_dynamic_mesh(ue, **dimensions)` appends that data to one transient DynamicMesh and verifies 16 vertices, 28 triangles, one component and a closed shell. It creates no persistent asset.

Every append includes exactly one finite UV0 value per input vertex. This is required because `AppendBuffersToMesh` resets the mesh UV-layer count from the contiguous full-length UV arrays in its buffers; allocating a channel before append is insufficient. Whole-mesh box projection then replaces the seed mapping. Before persistent creation, every triangle must have valid, finite, nondegenerate UV0 coordinates. This is a surface UV channel, separate from optional lightmap UV generation, which remains disabled.

## Source contracts

The relevant headers are below `Engine/Plugins/Runtime/GeometryScripting/Source`:

| Python class/method | Contract and source |
| --- | --- |
| `GeometryScriptSimpleMeshBuffers` | Reflected vertices, triangles, normals, UV and color arrays; `GeometryScriptingCore/Public/GeometryScript/MeshBasicEditFunctions.h:21–58`. |
| `GeometryScript_MeshEdits.append_buffers_to_mesh` | TargetMesh, Buffers, MaterialID=0, deferred notifications=false; returns mesh plus an output triangle-index list. Same header:425–436. |
| `GeometryScript_Normals.set_per_face_normals` | TargetMesh; `MeshNormalsFunctions.h:129–133`. |
| `GeometryScript_MeshQueries` | `get_vertex_count`, `get_is_closed_mesh`, `get_num_open_border_edges`, `get_num_connected_components`, `get_mesh_bounding_box`; `MeshQueryFunctions.h:43–80,175–179`. Vertex count is on this library, not DynamicMesh. |
| `GeometryScript_MeshQueries` UV readback | `get_num_uv_sets(mesh)` and `get_triangle_u_vs(mesh,0,triangle_id)`; the latter returns three Vector2Ds and a validity flag. `MeshQueryFunctions.h:253–286`. |
| `GeometryScript_UVs.set_mesh_u_vs_from_box_projection` | Mesh, channel0, box transform, mandatory `GeometryScriptMeshSelection()` and minimum island triangle count2; empty selection processes the whole mesh. `MeshUVFunctions.h:456–464`. The UV layer must already exist. |
| `Transform` | Construct `Transform()`, then set exposed `translation` and `scale3d` editor properties. Projection uses centre `(0,0,height/2)` and positive scale `(width,depth,height)`. These property names were checked against the actual UE5.8 Python docstring. |
| `GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh` | FromDynamicMesh, AssetPathAndName, Options; returns StaticMesh plus Outcome. `GeometryScriptingEditor/Public/GeometryScript/CreateNewAssetUtilityFunctions.h:175–182`. Confirm the actual Python tuple before calling. |
| `GeometryScriptCreateNewStaticMeshAssetOptions` | Explicitly set `enable_collision=False`, `enable_nanite=False`, `enable_recompute_normals=False`, `enable_recompute_tangents=False`; same header:47–79. Collision defaults true. |

The module also lists the reflected box, transform and material-ID helpers for later caller-selected construction. They are not needed for this direct shell recipe.

## Fresh creation and separate saving

`create_planter_asset_unsaved(ue, asset_path, owned_material, write_intent, **dimensions)` accepts only a legal new path below `/Game/Daedalus/Art/Islands/CodexContest/Native/GalleryCity/`. It rejects an existing asset or a globally colliding asset name. It requires an existing caller-owned material and the caller's durable intent writer.

The sole operator owns admission: current editor/resource ownership, a clean compatible scene, preserved baseline and source identity. The caller's existing journal must persist and flush each mutation intent before creation, material binding, metadata changes and saving. A failed or uncertain creation is reconciled separately; do not repeat it to resume.

The native creation utility itself checks path syntax but provides no fresh-path guard. Its implementation creates/registers a dirty package, disables creation undo internally, and does not save it to disk. The sketch therefore returns the new unsaved mesh after binding its one material slot. It creates no actors and never saves a map.

Before a separate `EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)`, inspect exact source/render triangles and bounds, complete UV0, build scale 1, Nanite disabled, collision count 0 and the exact bound material. Record source recipe, palette/material provenance and actor scale 1 metadata with an intent. Require a true save result and independent saved-package/readback evidence. Preserve partial dirty work on failure; no automatic cleanup or overwrite is provided.

## Palette ownership

Each caller supplies its original palette/material references and records the exact chosen asset path and source provenance. This recipe has no vertex-color palette or automatic color conversion. Use an existing owned material whose inputs match the caller's intended appearance; shared parents remain unchanged.

Preserve source linear PBR factors directly. A producer-specific encoded vertex palette needs its separately evidenced transfer contract; do not apply that transfer to linear PBR materials or assume a universal gamma correction. Material readback and native views remain distinct from source geometry acceptance.

## Completed intake and placement — 15 October, 19:37 UTC

The corrected Gallery recipe remains parked without persistent native acceptance. Production instead placed the already-saved Lotus at a source-backed HeroR4 waterline, reused the existing producer-compatible palette on its new component, saved the map once and independently read it back. The pivot preserves 25cm below and 80cm above the water surface. Nine native water samples and bounded static-mesh triangle clearance passed. The map save returned true in 20.678024s; all 139 previous tracked actors remained unchanged, giving 140. The native detail image shows the plant seated in the water; pale appearance and physics/ecology/navigation remain unaccepted. A temporary detail camera was subsequently restored exactly after a positional Rotator construction mistake was reconciled; explicit pitch/yaw/roll fields avoid that argument-order assumption.

The next exact Copperfall subset, source head `b4bc16d330308b1849abf9303e732b10c5773936`, contains three nodes/292 triangles in 18,732 bytes, SHA256 `3a0a9b8a36b8dbf9199f78b9110a8e70742759b61f89b13b49354f43afdfd142`. The [bounded GLB profile](../../engines/unreal/DaedalusLink/Content/Python/daedalus_codex_copperfall_subset.py) and [delivery runner](../../tools/unreal/codex_copperfall_delivery.py) reuse the existing Sunspool/Miri/catalogue route. Actual Interchange naming, authored translations baked into absolute XZY centimetres, build scale 1, linear PBR, named emission parameters and provenance are inspected before saves. No shared material is replaced and no producer-specific palette transfer applies to this raw PBR packet.

One import measured4.229492s. The first attempt stopped before saves because the three new meshes had Nanite enabled; lightmap-UV generation was already false. After read-only reconciliation established exactly six unsaved objects and no unrelated mismatch, [the bounded recovery](../../tools/unreal/codex_copperfall_nanite_recovery.py) disabled Nanite only on those three new meshes, revalidated the original contract, recorded metadata and performed six first saves. All returned true and independent readback/backups completed. No import replay, map save or actor placement occurred for Copperfall. The full269-role source remains provenance only.

Saved namespace inventory is now211 packages, with140 tracked actors and184 accepted C++ sources preserved. This corrects a count-scope issue: the earlier141-package protection ledger omitted64 already-saved palette packages. Those64 were independently reconciled and backed up before further production; expanding the ledger did not create or import64 assets. The exact24-hour window ending19:04UTC contains158 new saved object packages:93 imported/first saved plus65 created natively/saved. It contains138 new retained construction actors and six saved staging versions across three base seeds; these are not six BAR/runtime-approved islands. Existing receipts retain the complete path/class/time/hash lists and cross-team coverage limits.

## Completed Copperfall placement and construction views — 15 October, 20:16 UTC

The later completed state places the three already-saved Copperfall roles on HeroR4 and preserves all 140 previous tracked actors. Each new actor uses the common translation `[-316100,299550,17348.324]` cm, zero rotation and scale `[1,1,1]`, retaining the authored relative layout, mesh pivots and raw materials. Component collision is disabled for this decorative construction. The placement adds three actors, with zero imports, new assets/packages or island versions. The map was saved once: true, measured 20.973694 seconds. Current protected totals are 143 actors, 211 packages and 184 accepted C++ sources.

The [published R2 ground-check source](../../tools/unreal/codex_copperfall_ground_check.py) is a pure `BODY` module and a newline-normalized copy of the executed recipe: published LF size 13,506 bytes, SHA256 `ab81cb1f8ab0fdfa57051cbb7b55414d1d8d18feef87886a9c6ddbd0b819599c`; retained executed CRLF size 13,748 bytes, SHA256 `65dfa51b6cf477a8239376c4ca4eb64181cead65ec86dfbac8857aa7a194be68`. Only newlines differ; BODY semantics are unchanged. It creates transient DynamicMesh copies for inspection. It proves all 25 complete flat ground cells from 50 triangles, including each cell's corner union, shared diagonal and opposite half-square sides within 0.02cm coordinate tolerance. The accepted rank-3 candidate has zero clearance blockers across the bounded full-height volume after checking overlapping StaticMeshComponents and actual instanced-mesh transforms, including terrain. Non-static geometry and physics/navigation/runtime acceptance remain separate.

The original rank-1 and rank-2 candidate receipts retain their native flower-geometry conflicts. Neither blocker was ignored, and no guard was relaxed to admit rank 3. A source-boundary sensitivity explanation remains an inference; an axis-conversion cause was not established.

The module exports the string `BODY`; importing it does not contact Unreal or execute that body. The existing sole-operator recipe inserts it after the established `g.native` preflight, supplies `cfg`, `unreal`, `math`, `json` and the editor actor subsystem `sub`, and captures `result`. It is the retained fixed-location pre-placement proof for the admitted baseline, not a standalone CLI or general placement solver. Repeating it after construction would encounter the newly placed roles as obstacles. Ownership, current resources, queue state, preserved baseline, placement and saving remain the caller's responsibilities.

MAIN personally reviewed the actual `player.png` and `context.png` at 20:16:14 UTC. The faceted teal heartstone and copper base are readable, the plinth visibly meets the ground, and the flowering beds remain separate in those two images. No extra pose/material mutation or repeated map save was needed. The viewport remains on the construction and adjoining HeroR4 garden. These two fixed views do not establish unseen-face coverage, full visual BAR approval or runtime collision/navigation/interaction acceptance.

The local completion receipt is `native-ingestion/CopperfallPlinthHeartstoneSubsetR1/PlacementR2/ConstructionViewsR1/completion.json`, completed at `2026-10-15T20:16:16.511291+00:00`. Its final `saved-production-baseline.json` is 502,728 bytes, SHA256 `1555dff971c6b3e487253aa7fa202ea368b0a38d3ee83959b198bf69d1224a63`; the saved map is 209,408,537 bytes, SHA256 `72cb0c195975afa4b272417f67181f09774b95e7d5b061d7438ec2e70a85cd44`. The camera/view stage made zero map-save calls and released its compute lease with no issues. Those local binary receipts and images are separate from this source publication.
