# Blender to Unreal ingestion upgrade

Audit date: 2026-10-14. Owner: Poot (`pootscoot`), confirmed by coordinator hub30610. Scope: continuous Blender production and a concurrent, bounded upgrade around the existing importer. The later continuous-production direction in30639 supersedes the earlier backlog-only pause. Preserve the current importer owner, assets, namespaces and warm DDC.

**Status: source implementation, unvalidated and not loaded.** No tests, benchmarks, builds, add-on installation, plugin changes, console-variable changes, editor restart, asset import or live deployment were performed by this lane. Native discovery used only `list_toolsets` and `describe_toolset`. Installed does not mean enabled; enabled does not prove an operation worked.

## Immediate result and source

Interchange is already processing the current FBX imports on this machine. Installing or globally switching an importer is unnecessary for the first slice. The added orchestration calls the existing `AssetImportTask/FbxImportUI` path and preserves its material/collision postprocessing.

- [Saved-item entry point](../../engines/unreal/DaedalusLink/Content/Python/daedalus_claude_ingestion.py): `import_saved_batch`, at most three distinct island seeds, asset import/save only.
- [Portable receipt primitives](../../engines/unreal/DaedalusLink/Content/Python/daedalus_ingestion_receipts.py): SHA256/byte witnesses, canonical manifest key, immutable input snapshot, atomic receipt replacement, explicit uncertain-outcome gate and one upgraded-batch lock.
- [Existing importer seam](../../engines/unreal/DaedalusLink/Content/Python/daedalus_claude_islands.py): optional `source_file` and `on_imported` arguments. Existing calls keep their original behavior. The wrapper forces a verified import rather than trusting the old path-only cache.

The manifest binds source bytes/path, destination, the named `claude_voxel_fbx_existing_options_v1` preset and explicit import/postprocessing settings, engine version, backend control readbacks, loaded Python code identity, importer/orchestration source files and existing project default INIs. The per-item receipt records the requested native API and separate import/postprocess/save call-completion fields; available tools are not represented as called. Callers must include additional file dependencies for customized pipelines, materials or other external inputs. UE's existing source-file hash alone does not cover that complete identity.

Unchanged skip requires a structurally consistent `saved` receipt, matching manifest key, asset membership, existing native assets, matching saved `.uasset` byte witnesses and no dirty output packages. Inputs with missing receipts receive a verified import; existing filenames alone do not earn a skip. Dirty owned destinations/materials stop before mutation so another author's unsaved edits are not overwritten.

Receipts distinguish `input_verified`, `import_started`, `imported`, `postprocessed`, `save_started`, `saved`, `input_failed` and `uncertain`. A successful native save, unchanged source/snapshot/config identity, output files and clean output packages precede `saved`. The existing material helper may also save a newly created material during postprocessing; receipt stages do not imply that all writes happen only in the final save call.

Repeating a batch skips completed items and resumes safe pre-import failures. Interrupted or mutating outcomes require owner inspection before explicit `retry_uncertain=True`; no automatic blind replay occurs. Previously saved items survive a later item failure. Corrupt receipts and stale locks stop for inspection. The lock protects upgraded callers only: legacy jobs must be quiescent before owner use.

Owner example, **not executed or validated**:

```python
import daedalus_claude_ingestion as ingestion
results = ingestion.import_saved_batch([240, 241, 242])
```

This is a synchronous, bounded entry point suitable for one existing Python job. It does not place actors, clear deeds, save a world map, enable worker parallelism or claim asynchronous completion. Receipts and snapshots live under `Saved/Daedalus/Ingestion/ClaudeIslands/`; snapshots remain available for outcome inspection. Retention/cleanup is an owner task, not an automatic deletion policy.

## Installed Blender capabilities

Evidence prefixes: `B=C:/Program Files/Blender Foundation/Blender 4.3/4.3/scripts`; `U=C:/Users/730ri/AppData/Roaming/Blender Foundation/Blender/4.3`; `H=C:/Users/730ri/projects/blender-harness`.

| Installed capability | Exact evidence | Supported control / limit |
| --- | --- | --- |
| Blender 4.3.1 | `Blender 4.3/blender.exe` numeric PE version4.3.1.0 | Executable metadata only; no app launch |
| FBX exporter5.12.5 | `B/addons_core/io_scene_fbx/__init__.py:5-15,534-552` | Native scene/collection batch modes and `use_batch_own_dir`; implementation `export_fbx_bin.py:3668-3747` |
| FBX subset/transform/animation | Same `__init__.py:302-360,485-526` | Selection, visibility, collections, axes/units/scale, actions/NLA/sampling. Bake-space-transform has armature/animation restrictions |
| glTF exporter4.3.47 | `B/addons_core/io_scene_gltf2/__init__.py:5-16,135-142,566-689` | GLB/separate glTF, collection/scene/selection filtering and animation modes |
| Source geometry reuse | glTF `blender/exp/mesh.py:15-42`; Blender `startup/bl_ui/space_view3d.py:2669-2676,2739` | Mesh-data/modifier/material cache, collection instances and linked duplicates; not a durable cross-run receipt |
| Optional glTF GPU instances | glTF `__init__.py:920-925`, `blender/exp/exporter.py:168-181` | Default false; restricted instance shape/material support. Unreal acceptance unverified |
| Claude Blender Bridge1.0.2 | `U/scripts/addons/claude_blender_bridge/__init__.py:15-21,247-254` | Installed Python-execution/inspection/render seam; no dedicated batch-import command established |
| Existing export harness | H head`ea430882774cd9a1b439d0873ee0e5bea3510b53`; `bharness/context.py:26-32`, `plugins/export.py:10-25,44-67` | `export.glb`/`export.lod`, selected-collection export and GLB re-read; existing source, not a new execution receipt |
| Existing batched handoff/instances | `H/assets/headless.py:15-38`, `assets/runner.py:65-76`, `HANDOFF-SPEC.md:27-28` | Collection instances and exact pre-exported-file handoff already documented |

The standard user add-on directory contained only Claude Blender Bridge. No Send2UE, UE2Rigify, Blender-for-Unreal, Bsend or BPainter installation was found in the audited built-in/user/extension roots. Custom preference paths and add-on enabled state remain unknown; `userpref.blend` was not opened in Blender. Other source-format menu entries are build-option guarded and were not runtime probed.

## Installed Unreal capabilities and actual importer

Engine prefix `E=C:/Program Files/Epic Games/UE_5.8/Engine`; project `P=C:/Unreal/DaedalusRealm`.

| Capability | Installed / configured / observed evidence |
| --- | --- |
| UE5.8.3, CL58210709, compatibleCL55116800 | `E/Build/Build.version:2-9`, branch`++UE5+Release-5.8` |
| Python3.11.8 | `E/Binaries/ThirdParty/Python3/Win64/python311.dll` PE version; `Python3.Build.cs:126,189` |
| Python + Editor Scripting | Explicitly enabled in `P/DaedalusRealm.uproject:16-21`; MCP/AllToolsets at32-37 |
| Interchange Runtime/Editor/Assets | Corresponding `E/Plugins/Interchange/{Runtime,Editor,Assets}/*.uplugin:3-4,13`, metadata version1.0/default enabled |
| DatasmithImporter / USDImporter / InterchangeOpenUSD | Installed, default disabled; USD beta, OpenUSD experimental. Their descriptors under Enterprise/Importers/Interchange Extensions were inspected |
| Visual Dataprep | Installed `DataprepEditor.uplugin`, default disabled; loaded importer/editor support not established |
| DataValidation / InterchangeTests | Installed/default enabled; log mounts establish loaded plugins, not validation or test execution |

Stable session evidence: `P/Saved/Logs/DaedalusRealm-backup-2026.10.14-18.00.50.log`. Plugin mounts at238,303-307,320,339 show Python, Interchange, Editor Scripting and Datasmith **Content**. Lines5264-5276 show Interchange FBXSDK translation/import of `Island_C366.fbx` at17:50:41-46UTC;5479-5491 show another FBX. This disproves assuming that `FbxImportUI` necessarily selects the legacy backend. It does not prove every requested option was applied. Different asset durations are not a controlled throughput comparison.

Installed FBX translator source `E/Plugins/Interchange/Runtime/Source/Import/Private/Fbx/InterchangeFbxTranslator.cpp:34-53` defaults `Interchange.FeatureFlags.Import.FBX` and `.FBX.ToLevel` true and `Interchange.FeatureFlags.Translator.UseWorker.FBX` false. Effective runtime values were not changed or queried during this audit. `GetConsoleVariableIntValue` also returns zero for missing variables (`KismetSystemLibrary.h:628-631`); receipt readbacks are not proof that zero means disabled.

The [Epic Interchange guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine) describes shipped pipeline assets, default enablement, pipeline customization and remembered reimport settings; it still labels FBX support experimental. Local5.8.3 source and the preserved session log determine this machine's actual route. Hidden engine/plugin content is a visibility issue, not a missing install. Actual pipeline assets are present under `E/Plugins/Interchange/Runtime/Content/Pipelines/`, including FBX/OBJ, GLTF, materials, textures and scene stacks; `E/Config/BaseEngine.ini:3784-3790` selects format-specific defaults. No visibility or stack setting was changed.

### Existing batch, reimport and completion APIs

| Local source | Real control / implication |
| --- | --- |
| `E/Source/Developer/AssetTools/Public/IAssetTools.h:542`; `Private/AssetTools.cpp:2955-3003` | `ImportAssetTasks` accepts an array, but loops tasks. Array submission alone does not establish parallel imports |
| `E/Source/Editor/UnrealEd/Public/AssetImportTask.h:42-89` | Automated/replace/save/async flags; async format-dependent; `GetObjects` can block. Poll completion first when adding async later |
| `E/Source/Runtime/Interchange/Engine/Public/InterchangeManager.h:385-466` | `InterchangePipelineStackOverride` in task options, `AddPipeline`, explicit reimport asset/source index and completion delegates |
| Same `InterchangeManager.h:685-694,755-765` | `ScriptedImportAssetAsync` / scene equivalent return started, not completed |
| `E/Source/Runtime/Engine/Classes/EditorFramework/AssetImportData.h:32-46` | Existing source-file hash/timestamp metadata; not complete settings/dependency/save identity |
| `InterchangeAssetImportData.h:148-170` | Stored translator/pipeline settings already exist |
| `E/Plugins/Editor/EditorScriptingUtilities/.../Public/EditorAssetLibrary.h:70,271` | Existing asset-existence and explicit loaded-asset array save APIs used by the wrapper |
| `E/Source/Editor/UnrealEd/Public/FileHelpers.h:138-144` | Existing dirty-content-package query used to refuse unsaved destination edits |

The official [pipeline-stack wrapper API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangePipelineStackOverride?application_version=5.7) is also an architectural reference; local5.8.3 header signatures above are authoritative here. Interchange ignores task `destination_name`; multi-mesh naming must respect the pipeline (`AssetImportTask.h:42-44`, `InterchangeGenericAssetsPipeline.h:59-73`). The first implementation keeps the current working route instead of switching stacks.

### Exposed native connector tools

Actual `list_toolsets`/four `describe_toolset` responses on2026-10-14 returned these version1.0 schemas. Local discovery receipt: `Documents/Codex/2026-10-13/task-3/live/ingestion-native-schema-receipt.json`.

| Tool | Real supported control / boundary |
| --- | --- |
| `StaticMeshTools.import_file` | Source file/destination/name; material/texture/combine flags; returns asset refs. No reimport, async, Nanite or collision option was exposed in this schema |
| `AssetTools.find_assets`, `save_assets` | Native destination lookup; explicit asset-path array save. Empty array saves all dirty assets, so use explicit owned paths |
| `ProgrammaticToolset.execute_tool_script` | Batches registered tool calls in one sandboxed script. Requires `get_execution_environment` and output-schema inspection before use; batching reduces RPC count, not proven mesh-build time |
| `SceneTools.add_to_scene_from_asset`, `create_level_instance` | Existing-asset and saved-level reuse already exposed |
| `AssetTools.duplicate` | Copies assets/folders; this is not shared-geometry deduplication |

No registered-tool script or asset operation was executed. This wrapper uses the direct Python importer because its known options and postprocessor fit the current Claude content. Native programmatic batching is available for the separately owned Codex delivery module after its owner reviews the execution environment.

### DDC, source formats and reusable processing

Preserved log1080-1086: ZenLocal healthy, common local DDC writable at `C:/Users/730ri/AppData/Local/UnrealEngine/Common/DerivedDataCache`; ZenShared/filesystem Shared/Cloud unavailable through unconfigured hosts/paths. Engine pak cache opened; project pak cache absent. Preserve this warm local cache. DDC reuse is not evidence that an asset was imported and saved. Native overrides are in `E/Config/BaseEngine.ini:2722-2742,2823-2824,2866-2868`; no cache path was changed or cleared.

FBX/OBJ/glTF/GLB translators are installed. USD and Datasmith scene paths exist but their importer availability is not established for this session. Blender is absent from Epic's [official Datasmith supported-app list](https://dev.epicgames.com/documentation/unreal-engine/datasmith-supported-software-and-file-types); do not assume an official Blender Datasmith exporter.

Existing reuse primitives include `StaticMeshComponent.SetStaticMesh`, `InstancedStaticMeshComponent.AddInstances` and Level Instances (`StaticMeshComponent.h:450`, `InstancedStaticMeshComponent.h:271-275`). Repeated geometry can reuse a saved mesh with separate transforms. The current wrapper returns saved mesh paths but does not rewrite placement or consolidate another owner's actors.

Dataprep already ships LOD, collision, material substitution, mesh consolidation and Nanite operations (`Plugins/Enterprise/DataprepEditor/.../Private/DataprepOperations.h:40,98,125,189,305,376,523,576`). See [Epic's operation reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/dataprep-operation-reference-in-unreal-engine). Producer compatibility and loaded availability need later owner validation; no algorithms or plugins were duplicated/enabled here. Installed InterchangeTests offers reusable import/reimport assertions for later checks, including [static-mesh test functions](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/InterchangeTests/UStaticMeshImportTestFunctions). Tests remain deferred.

## Public reusable sources and compatibility boundaries

| Candidate | Verified source / terms | Decision for this slice |
| --- | --- | --- |
| Epic Send2UE | [MIT notice](https://github.com/EpicGames/BlenderTools/blob/main/LICENSE.md), [import task wrapper](https://github.com/EpicGames/BlenderTools/blob/main/send2ue/dependencies/unreal.py), [linked-mesh extension](https://github.com/EpicGames/BlenderTools/blob/main/send2ue/resources/extensions/instance_assets.py), [extension hooks](https://github.com/EpicGames/BlenderTools/blob/main/send2ue/core/extension.py) | Useful orchestration/reference patterns; no donor code copied. Path/base64 identity is not content hashing. [2.4.3 release](https://github.com/EpicGames/BlenderTools/releases/tag/20231109043947) testedUE5.3, not proof for installed5.8.3 |
| Poly-Hammer BlenderTools | [Release evidence](https://github.com/poly-hammer/BlenderTools/releases/tag/20251123002929), testedUE5.3/5.4 | Not installed; no5.8.3 compatibility or throughput claim |
| Blender-for-Unreal | [Releases](https://github.com/xavier150/Blender-For-UnrealEngine-Addons/releases), GPL-3.0-or-later;4.4.6 reportsUE5.8 support | Reference only; no GPL code copied into this MIT connector, no installation |
| Epic PythonSamples | [Repository](https://github.com/EpicGames/PythonSamples): FBX/Interchange/Dataprep examples, olderREADMEUE4.26, archived2026-07-31 | Example/reference; root redistribution terms not established, no copying |

## Rollout boundary and implementation priorities

1. Publish this bounded source/doc slice as an unvalidated draft. Preserve Blender production in parallel; no queue-length stop directive.
2. Claude owner reviews the thin importer seam and selects a between-job load window. The actual loaded seam signature is checked before mutation; copying a file does not prove a cached Python module was reloaded.
3. Keep the working FBX backend, lighting/collision/material requirements and DDC. First import an owner-selected batch of at most three items, then retain exact native asset/save receipts when execution is authorized.
4. Apply the portable receipt primitive to the existing Codex delivery owner module through its established artifact/material contract. Do not apply Claude's vertex-color material, scale0.01 or deed clearing to harbor, skeletal-worker or palette-slot assets.
5. Later, inspect programmatic execution constraints and consolidate registered calls; reuse shared geometry and existing Dataprep/Interchange tests where compatible. Async, new formats, worker parallelism and new add-ons are separate owner-controlled changes.

Deployment is **not complete**. Claude hub30626 offered a future20-minute fresh-editor window restricted to `/Game/Daedalus/Art/Islands/CodexContest`, asset saves only, noPIE/world-map saves, with actual `UNREAL WINDOW OPEN` required. That does not authorize running this ClaudeIslands wrapper in Claude's namespace. No accepted load/use window for this wrapper has been received. Source work continues independently; the Codex delivery owner can use its separate accepted window for existing prepared content.

## Deferred validation checklist

No checklist item was executed in this slice. Current user instructions defer tests/benchmarks and preserve the live editor.

- Portable receipt checks: source/settings/dependency/engine/backend/loaded-code changes invalidate keys; corrupt receipts stop; missing/modified/dirty outputs cannot skip; snapshot changes stop; lock ownership cannot be stolen; unfinished states require explicit reconciliation.
- Owner native acceptance: confirm loaded source head and seam, actual backend/options, body/material/collision/bounds, explicit saves and clean packages; rerun identical input and retain a real unchanged-skip receipt.
- Resume/failure cases: saved first item survives later failure, missing input causes no mutations, save failure never earns `saved`, editor crash/unknown import remains blocked until inspected, wrong namespace and dirty existing outputs are refused.
- Keep imported/saved assets separate from world placement, quality approval, gameplay/collision acceptance and throughput measurement. No mock or filesystem receipt proves a playable scene.
