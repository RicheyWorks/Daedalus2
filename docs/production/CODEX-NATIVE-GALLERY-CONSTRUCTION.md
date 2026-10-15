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
