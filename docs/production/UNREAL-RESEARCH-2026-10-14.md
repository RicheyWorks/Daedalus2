# Unreal 5.8 research for the island pipeline (2026-10-14, Richey: "do deep research like they did")

Verified against Epic docs unless marked UNVERIFIED. Full URLs inline.

## Interchange import (what our importer really does)
- FBX goes through Interchange by default since 5.7; legacy path = `Interchange.FeatureFlags.Import.FBX False` (ini-able).
  https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine
- Our readback proves the FbxImportUI flags land on the mesh (nanite_settings.enabled False, vertex colours present),
  so either the legacy flag is active in this project or Interchange maps them. The documented Interchange way is
  `unreal.InterchangePipelineStackOverride().add_pipeline(p)` as `task.options` with
  `p = unreal.InterchangeGenericAssetsPipeline()`: `mesh_pipeline.build_nanite/generate_lightmap_u_vs/collision/
  import_collision_according_to_mesh_name/one_convex_hull_per_ucx/combine_static_meshes_behavior`,
  `common_meshes_properties.vertex_color_import_option`, `import_offset_uniform_scale` (bake our 0.01 at import).
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericMeshPipeline
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangePipelineStackOverride
- UCX_<mesh>_NN boxes are honoured by both paths (Interchange: the two collision flags above).
- Async: `InterchangeManager.scripted_import_asset_async` + `ImportAssetParameters.on_assets_import_done`.
- uFBX parser (`bUseUfbxParser`, experimental in 5.8) is faster on heavy FBX — try on the 11k-quad islands.

## Editor memory (our real ceiling: 12–14 GB baseline, commit limit at ~20 islands/session)
1. **World Partition** conversion makes the world open unloaded; load regions/GUIDs from Python
   (`unreal.WorldPartitionBlueprintLibrary.load_actors/unload_actors/get_intersecting_actor_descs`).
   `UnrealEditor.exe <Proj> -run=WorldPartitionConvertCommandlet <Map>.umap -AllowCommandletRendering
   -SCCProvider=None -ConversionSuffix [-ReportOnly] [-OnlyMergeSubLevels]`.
   https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition-in-unreal-engine
   This is the structural fix; it also replaces ADR-063's hand-rolled district streaming. Needs Richey's go (one-way
   conversion of DaedalusWorld; do it on a copy with -ConversionSuffix first).
2. Interim: `unreal.EditorLevelUtils.remove_level_from_world(level)` on the 214 realm sublevels at session start
   (removes from the world list → re-add the one you edit with `add_level_to_world`). Python has no
   `should_be_visible_in_editor`; `set_levels_visibility` only hides (still loaded).
3. Headless batch: `UnrealEditor-Cmd.exe Proj.uproject -run=pythonscript -script=<py> -nullrhi -unattended
   -NoShaderCompile -NoSplash` — no viewport, no GPU residency, exits when done; load the map yourself with
   `LevelEditorSubsystem.load_level`. Cannot run while the editor has the same map open (package clashes); fits the
   turn boundary (editor closed → commandlet → editor reopened).
   https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python
4. Generate Mesh Distance Fields (Project Settings > Rendering) adds build time + memory per static mesh; our
   DefaultEngine.ini has no override, so it is at the default (off) — leave it.

## Unreal MCP plugin (official page)
https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-mcp-in-unreal-editor — Auto Start Server in
Editor Preferences > General > Model Context Protocol (default off; also `-ModelContextProtocolStartServer`),
`ModelContextProtocol.GenerateClientConfig ClaudeCode` writes `.mcp.json`, Tool Search mode exposes only the three
meta-tools, no byte limit documented, `ModelContextProtocol.PaginationPageSize`. Toolsets are Python
`unreal.ToolsetDefinition` files under Content/Python — we can add our own toolset (island import/placement) so the
official connector drives the contest pipeline directly. Companion: MCP Inspector, `unreal-mcp` Claude Code plugin
with a create-toolset skill.

## Python 5.8
Python 3.11.8; no batched spawn (one `spawn_actor_from_class` per actor); `StaticMeshEditorSubsystem.
set_nanite_settings/set_generate_lightmap_uv/add_simple_collisions`; Remote Control API (HTTP/WebSocket) as an
alternative transport.

## Downloads
Fab limited-time-free rotates fortnightly (nothing voxel/stylised verified today); Epic BlenderTools (Send to
Unreal) on GitHub; PCG is scriptable (`unreal.PCGComponent.generate`) and 5.8 improved ISM reuse for large sets —
the route for mass prop placement after the contest.

## Ranked actions
1. World Partition conversion of DaedalusWorld (ask Richey; -ReportOnly first).  2. remove_level_from_world for the
realm sublevels at session start.  3. Commandlet batch at turn boundaries (-nullrhi).  4. Explicit importer choice
(legacy flag in ini, or Interchange pipeline with import_offset_uniform_scale 0.01).  5. uFBX parser trial.
6. MCP Auto Start + our own ToolsetDefinition.  7. Async import pipelining.  8. PCG for props.
