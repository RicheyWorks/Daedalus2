# Blender to Unreal ingestion upgrade

Audit date: 2026-10-14. Owner: Poot (`pootscoot`), confirmed by coordinator hub30610. Scope: continuous Blender production and a concurrent, bounded upgrade around the existing importer. The later continuous-production direction in30639 supersedes the earlier backlog-only pause. Preserve the current importer owner, assets, namespaces and warm DDC.

**Current checkpoint, 2026-10-15 00:35 UTC:** the Codex PR146 adapter at `05fc3c2521c62e06de88bf85106eee0dd55086ab` has actual operator import/save and unchanged-reuse receipts. The combined palette/placement runner at `98afbf8ba23c181d775035314ffabead74b4b58c` is now integrated as two unchanged source blobs in operator PR147 at `69fc0048312606f7184be7b8c3458752027e9d8d` (hub31247, integration commit `a99a825f`). Its optimized native execution still awaits a new qualifying voxel delivery; no completed operation was replayed or speedup measured. Root has not operated Unreal, installed source, changed settings or interrupted the sole operator. The original audit and historical handoff snapshots below are retained; this current checkpoint supersedes their pending Codex-source-adoption statements. Claude-wrapper adoption remains unverified.

## Measured production bottleneck and bounded fix

User priority: remove avoidable delay in the existing Blender-to-Unreal delivery path while builders continue. `codex-play-guard` remains the only Unreal writer; screenshots are a separate bounded task. Source inspection used its clean production checkout at `0075e19f32fdc04c967653d0f2f6c9e23232a013` (PR147), not a replacement importer or a second editor.

Evidence base: `engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/` in that checkout, absolute path `C:/Users/730ri/Documents/Codex/2026-10-14/task-2/contest-island-production/`. The guarded import receipts record PR146 `reviewed_head`, `runtime_head` and loaded file hashes. The native importer SHA256 remains `dfac57ce929686dc1bca400da4a258405f0a1bd1cb783fa673793ba8f28de982`.

| Actual production slice | Guarded import | Palette bridge elapsed | Placement | Placement map save | Later palette map save |
| --- | ---: | ---: | ---: | ---: | ---: |
| HeroR4, 10 meshes | 10.198029 s | 93.7 s; 17 instances created / 7 reused | 2.763550 s | 24.459607 s | 24.212257 s |
| GardenGateR1, 9 meshes | 10.071391 s | 85.7 s; 16 created / 6 reused | 2.618201 s | 24.627979 s | 24.246945 s |
| PowerUnit, 5 reused meshes | No new mesh import | 0.1 s; 4 reused | 0.936072 s | 20.504441 s | 21.345374 s |
| Aetherflow, 3 meshes / 2 actors | 1.095737 s | 56.6 s combined material creation/compilation/save checkpoint | 0.478248 s | 20.560135 s | Binding included in this save |

Exact receipts: Hero/Garden `codex-hero-r4.adoption.json`, `codex-garden-gate-r1.adoption.json` and their corresponding `.world.json`/`.palette.json`; summary `codex-reviewed-2130.checkpoint.json`; PowerUnit `codex-power-unit-2205.world.json`/`.palette.json`; Aetherflow `AetherflowR2/adoption.json`, `AetherflowR2/world.json`, `codex-aetherflow-2245.checkpoint.json`. Palette elapsed includes creation, compilation and asset saves, whose individual contributions were not timed. Native mesh-import receipts under `C:/Unreal/DaedalusRealm/Saved/Daedalus/Ingestion/CodexContest/receipts/` are Hero `4baeb945202507ea41b225c2`, Garden `2383d5c07d1d765d74a847af` and Aetherflow `d8c672752101e94807fc2be5`, `cd8a88ba64e2e4c0da04c799`, `645581c6f428658f3d6433e7`.

Fresh palette creation is the largest measured stage. The clearest redundant work is the **second full-map save**: Hero/Garden saved four times for 97.546788 s, of which the two later saves consumed 48.459202 s. Their two guarded imports totaled 20.269420 s. This is an observed avoidable-work baseline, **not a demonstrated speedup**. Palette reuse already works and must be retained. The map is approximately 209 MB in these receipts; that size and a large actor count do not establish a hardware ceiling.

The existing [admitted palette assembly runner](https://github.com/RicheyWorks/Daedalus2/blob/98afbf8ba23c181d775035314ffabead74b4b58c/tools/unreal/codex_admitted_palette_assembly.py) now prepares/reuses assets through the unchanged `daedalus_codex_staging_palette.palette_steps`, verifies source/config/FBX/mesh/material-slot and saved-output witnesses, then passes bounded component overrides to [the existing saved-asset executor](https://github.com/RicheyWorks/Daedalus2/blob/98afbf8ba23c181d775035314ffabead74b4b58c/tools/unreal/codex_saved_asset_assembly.py). Binding occurs before its sole final map-only save. The first slice accepts one retained HeroR3/HeroR4/GardenGateR1/PowerUnit candidate, using the existing admission contracts. It does not replace the queue, importer, palette generator or legacy separate-palette fallback.

The two journals remain distinct. A completed palette journal can be reused only with identical inputs and saved palette bytes. A pending, partial, malformed, changed or uncertain journal stops for native inspection; no response/parser failure triggers a mutation replay. The executor retains each native response before interpreting it, accepts the list-shaped component response, and preserves existing Aetherflow support. Its current PR147 base already removed the earlier dict-only `wire.obj` assumption; direct-list tolerance is additional compatibility, not a claim to have newly fixed that historical failure. New timing fields record local preflight, each mutation call, component binding, map save and total executor elapsed. Palette preparation records exact-slot readback and palette-asset call elapsed. No compilation-completion claim follows from save=true.

Manual review caught an initial bridge guard rejecting its own generator request. Source `ed12c601` excludes only the exact type plus a unique per-call label, and still refuses other jobs/queued work, remote lock activity and dirty packages before palette mutation. Two independent source reviews examined actual recipes/bridge code; no tests, Python compilation or native calls were used for this review. Root leaves the active operator checkout and editor untouched.

### Normal-use handoff and remaining evidence

Operator31146 acknowledged the source ownership/no-overlap and reported the current compatible voxel set already delivered. Its source-only compatibility finding31154 was valid: the completed-palette path returned before live preflight. Correction `98afbf8ba23c181d775035314ffabead74b4b58c` extracts the existing read-only checks into a common helper, used by both fresh preparation and completed-journal reuse. Reuse validates its completed contract, checks current PIE/map/bridge activity/dirty packages/native mesh slots, then revalidates the contract. It never writes or restages the completed journal, changes its fingerprint, dispatches palette generation, or retries an uncertain mutation. The fresh path still records returned readback/timing before its existing palette sequence. Manual source review closed the finding; no tests/editor calls/adoption occurred in this correction. On a current PR147 checkout, adopt the two PR155 runner files; if already on `ed12c601`, apply the single correction commit. Keep exact existing journal paths and source/admission witnesses. A compatible new normal delivery remains necessary for native acceptance, with no extra approval or Claude-ACK gate.

Ownership/adoption requests are hub31099 and31120; isolated source claim is31105. Operator31146 reports four native4K captures complete at a safe saved boundary, without writer transfer. The sole operator next selects the exact reviewed retained voxel candidate/revision, uses this source checkout, and records the loaded head and actual palette/assembly journals. An already placed packet must not be replayed merely to manufacture timing evidence. The next reviewed Server_Rack or transparent Aetherflow packet is outside this bounded voxel contract.

Source integration is complete: `codex-pr155-source-integration-2350.json` records module blob `e4c24d36` and executor blob `14860b59` matching PR155, with three unchanged dependencies and all96 saved mesh files/map preserved. This is source readback, not an optimized native run. The operator's current suitable Hero/Garden/Power packets are already delivered; p91011/rack/fish/water use different contracts. No additional code extension or already-completed mutation is required merely to close the source-integration item.

Reproducible CLI shape (owner supplies exact admission/export paths and agreed centimetre coordinates; this example was **not executed**):

```powershell
python tools/unreal/codex_admitted_palette_assembly.py NATIVE_SAVED_RECEIPT.json `
  --source-receipt EXPORTED_SOURCE_RECIPE.json --placement-cm X_CM Y_CM Z_CM `
  --map /Game/Daedalus/DaedalusWorld --map-file C:/Unreal/DaedalusRealm/Content/Daedalus/DaedalusWorld.umap `
  --palette-journal NEW_PALETTE_JOURNAL.json --journal NEW_ASSEMBLY_JOURNAL.json
```

The operator must retain the existing exclusive turn and check actual jobs before use. A known empty material stub still uses the existing inspected-repair route, not automatic repair here. Successful adoption requires palette saved-output proof, exact actor/mesh/transform/component readbacks, one map-save response, preserved imported meshes/shared material and clean packages. Saved staging is separate from visual, collision, gameplay and runtime acceptance.

Missing measurements remain explicit:

- Immutable queue snapshot `C:/Users/730ri/Documents/Codex/2026-10-14/task/island-import-manifest-20261014.json`, SHA256 `57285255cf168bd5e41eea1e77f94afe484ae8ead4d089ab78276e9efdd483f4`, was captured at 21:35:16.0999441 UTC. It precedes Hero admission by 415.615437 s and Garden by 521.497109 s; no enqueue timestamp proves those are pure queue waits. Hero saved assets to Garden admission leaves 96.181681 s unclassified.
- Fresh palette compile/create/save subdivisions, background asset compilation and hardware saturation are unknown. Examined ingestion receipts explicitly say `background_compilation: not_queried`.
- Aetherflow's response-shape failure was reconciled without replay. Its two recovery checkpoints leave a 40.594876 s unclassified gap; there is no complete retry-duration timer.
- Native capture review files in `QA/staging.*-review.json` provide completion timestamps: Hero three-view completion span 0.988862 s, Garden four-view span 1.611487 s. Initial capture latency is absent. These are not bulk-delivery timings.
- Full-world snapshots are 4.25–7.85 MB, but scan durations are unmeasured. Placement itself took under 3 s for Hero/Garden. Fewer scans, queue polling changes, importer hash reductions or a persistent drain need evidence before they displace this narrow save fix.

Actionable next integration step: optimized native execution during a real compatible delivery, returning new phase receipts and one-save count; source integration is already complete. Instrument fresh material creation/recompile/asset saves separately if it still dominates. Root has not demonstrated reduced wall time, throughput, visual approval or a hardware limit.

## Immediate result and source

Interchange is already processing the current FBX imports on this machine. Installing or globally switching an importer is unnecessary for the first slice. The added orchestration calls the existing `AssetImportTask/FbxImportUI` path and preserves its material/collision postprocessing.

- [Saved-item entry point](../../engines/unreal/DaedalusLink/Content/Python/daedalus_claude_ingestion.py): `import_saved_batch`, at most three distinct island seeds, asset import/save only.
- [Portable receipt primitives](../../engines/unreal/DaedalusLink/Content/Python/daedalus_ingestion_receipts.py): SHA256/byte witnesses, canonical manifest key, immutable input snapshot, atomic receipt replacement, explicit uncertain-outcome gate and one upgraded-batch lock.
- [Existing importer seam](../../engines/unreal/DaedalusLink/Content/Python/daedalus_claude_islands.py): optional `source_file` and `on_imported` arguments. Existing calls keep their original behavior. The wrapper forces a verified import rather than trusting the old path-only cache.

The manifest binds source bytes/path, destination, the named `claude_voxel_fbx_existing_options_v1` preset and explicit import/postprocessing settings, engine version, backend control readbacks, loaded Python code identity, importer/orchestration source files and existing project default INIs. The per-item receipt records the requested native API and separate import/postprocess/save call-completion fields; available tools are not represented as called. Callers must include additional file dependencies for customized pipelines, materials or other external inputs. UE's existing source-file hash alone does not cover that complete identity.

Per-mesh import-data class and stored pipeline-class observations are also recorded via the installed `InterchangeAssetImportData.GetPipelines` API (`InterchangeAssetImportData.h:148-170`). An unavailable observation remains explicit; configured default pipeline assets alone are not an actual-use receipt. Background compilation is recorded as `not_queried`, separate from native save-call completion.

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

The official [pipeline-stack wrapper API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangePipelineStackOverride?application_version=5.7) is also an architectural reference; local5.8.3 header signatures above are authoritative here. The task header documents that Interchange ignores `destination_name`; multi-mesh naming must respect the pipeline (`AssetImportTask.h:42-44`, `InterchangeGenericAssetsPipeline.h:59-73`). The actual Codex importer also supports a verified single-mesh destination-name alias in its bounds check; the adapter preserves that observed contract. The first implementation keeps the current working route instead of switching stacks.

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

### Linked study, owner and actual-use map

| Study / applicable capability | Owner / outcome at this checkpoint |
| --- | --- |
| [Epic Interchange guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine) | Read by this audit; local API/stack assets verified. Existing Claude FBX imports complete through Interchange in the preserved log; new wrapper not loaded. Export hook is documented nonfunctional; runtime cooking advice is not an editor-ingestion requirement |
| [Epic DDC guide](https://dev.epicgames.com/documentation/unreal-engine/using-derived-data-cache-in-unreal-engine?lang=en-US) | Existing engine session uses local Zen/filesystem DDC per disk log. Preserve it; no new cache settings or measured hit-rate claim |
| [Asset compilation manager](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/FAssetCompilingManager) | Installed save chain reviewed. `StaticMesh.cpp:7356-7366` fences that static mesh during normal serialization. Save chain does not directly call generic finish-for-objects; material shader/global completion remains unverified. No global wait added |
| [UE5.8 compilation controls](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-console-variables-reference) | `Editor.AsyncAssetCompilationMaxMemoryUsage`, `MemoryPerCore` and concurrency settings govern native compilation, not total import admission. Effective current values were not queried from the owner-held editor and were absent from inspected log/default project config; no overrides made |
| [EA/Motive Texture Sets compiler](https://github.com/electronicarts/texturesets/blob/main/Docs/Technical/Compilation.md) | Reference supplied by parallel research: immutable in-flight input and delayed payload allocation. This slice queues at most three descriptors/manifests, streams hashes, then imports/loads one item at a time. No Texture Sets install, engine patch or speedup claim |
| Native programmatic batching / InterchangeTests / Dataprep | Metadata/installed source inspected. Programmatic script execution, tests and Dataprep operation execution remain deferred; no all-tools adoption claim |

Root's actual native use consists of metadata discovery only. Existing owner log imports are separate evidence and do not prove the new source was called, compiled, saved or adopted. Future wrapper receipts record requested preset/settings and observed pipeline provenance after an actual owner-controlled call.

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

Deployment is **not complete**. For the frozen Claude milestone, hub30667 opened an asset-only CodexContest window until18:44UTC/11:44Pacific; builder30669 claimed it for the existing24-asset batch. Claude deferred loading the ClaudeIslands wrapper until prior use elsewhere, so that namespace/first-use condition remains its separate boundary. The Codex follow-up below fits the actual owner importer and full18:40-20:40UTC slot; its current pending boundary is the sole operator's accepted gap and actual adapter load/save/skip receipts. Root runs no competing editor operation.

### Deployment handoff for the accepted owner

The Claude source milestone is frozen in draftPR146; initial code was published at6537927f and its final runtime code atd3b7ce14. The three Python files in this Claude milestone are its complete runtime slice. The Codex follow-up adds a fourth Python file at837e23c4. These Claude instructions are a handoff, **not executed deployment**.

1. Between completed owner jobs, identify the active import module's `__file__` and approved plugin/script path. The on-disk project has `P/Plugins/DaedalusLink`; do not assume a Git checkout is already the live Python source. Record the reviewed Git head and retain the previous importer file through the owner's existing backup flow.
2. Stage only `daedalus_ingestion_receipts.py`, `daedalus_claude_ingestion.py` and the reviewed `daedalus_claude_islands.py` seam together in that approved Python source path. No engine binary, config, plugin enablement, DDC change or editor restart is required by this slice. Copying files alone does not mean they were loaded.
3. The owner loads/reloads the receipt module, existing importer and new wrapper between jobs, then records actual module paths. The wrapper itself checks the snapshot/callback signature and hashes loaded code before mutation. Keep all legacy imports quiescent; its batch lock cannot coordinate an unmodified legacy caller.
4. Select one agreed existing FBX seed or up to three, in the **ClaudeIslands** namespace, and call the example entry point. Preserve per-item receipt paths, native API/preset/pipeline observations and exact saved asset paths. This is an owner-authorized production import, not permission to start the deferred test/benchmark suite or save a world map.
5. If the receipt is `uncertain`, an output is dirty, a lock exists or save proof is missing, stop and inspect that specific outcome. Do not erase receipts, silently unlock based on PID expiry or set retry flags blindly. Release the agreed window explicitly when done.

Rollback, if needed, uses the owner's retained importer source and a between-job reload. Preserve receipt/snapshot evidence; reverting Python does not undo imported assets. The current CodexContest window does not satisfy step4, and no Root deployment was attempted.

### Codex production-use follow-up

Owner30702 identified the actual working native importer as `daedalus_codex_prepared_assets.py`, sourceSHA256 `dfac57ce929686dc1bca400da4a258405f0a1bd1cb783fa673793ba8f28de982`, published inPR147. Its24-group/47-mesh import completed before this adapter; that outcome is not new-wrapper adoption. The older CLI delivery path is not substituted for this verified backend.

The separate [Codex adapter](../../engines/unreal/DaedalusLink/Content/Python/daedalus_codex_ingestion.py) now reuses the portable receipt layer with that exact importer. It executes verified source bytes in a private module, preserves its ROOT and working fallback, and delegates mesh alias/bounds/material/save handling to `import_all`. The original24-input manifest and47 saved assets are untouched. An admitted entry gets an immutable FBX snapshot and a full-key revision under `/Game/Daedalus/Art/Islands/CodexContest/Ingestion`; the caller may select another subfolder of that same owned root. Shared vertex-color material is reused **read-only**, bound as a dependency, never edited or saved by the adapter.

One-to-three selected entries yield one item at a time for the existing owner `daedalus.steps` runner. Preflight identities are checked again between editor ticks and before unchanged skip. Saved proof includes the exact revision, native metadata/material/geometry, clean packages and disk witnesses. Unfinished item gates remain effective after a key change. Separate native reports/private manifests/snapshots live under `Saved/Daedalus/Ingestion/CodexContest`; neither old delivery receipts nor native fallback reports are replaced.

Owner recipe, **not yet executed**. Load the new adapter and portable receipt module from this reviewed checkout in the sole operator's existing Python context; do not replace its current importer. Pass the generator to the existing steps runner rather than draining it synchronously:

```python
import daedalus_codex_ingestion as ingestion
steps = ingestion.import_steps(
    r"C:/Users/730ri/Documents/Codex/2026-10-14/task-2/contest-island-production/engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/codex-prepared.delivery.json",
    ["CodexModule_CopperPatina_BridgeCoupler_85000"],
    r"C:/Users/730ri/Documents/Codex/2026-10-14/task-2/contest-island-production/engines/unreal/DaedalusLink/Content/Python/daedalus_codex_prepared_assets.py",
    "dfac57ce929686dc1bca400da4a258405f0a1bd1cb783fa673793ba8f28de982",
)
```

The actual full18:40-20:40UTC handoff30701/30708 has occurred, with `codex-play-guard` the sole operator. Source readiness does not prove load/use: the operator must accept a gap after its current job, retain actual new native save/receipt evidence, then an identical-input skip receipt. User authorizes production use as validation; separate test suites remain deferred. Root has not claimed the editor or executed this recipe.

Actual19:12UTC handoff checkpoint: READY reached the operator/coordinator in30736/30737; coordinator30739 prioritizes the first visible placement/world save before adapter use. Supported task readback confirms the existing operator thread is idle after its latest turn failed with a usage-limit error. Coordinator30745 reports its supported resume attempt failed before execution with an `AbsolutePathBuf` deserialization error. Root tool discovery exposes no separate cloud-thread resume route; the held editor lock does not establish active execution. The agreed project `Saved/Daedalus/Ingestion/CodexContest` receipt directory is absent at this checkpoint. Adapter load/use and production acceptance remain unverified. Resume the existing sole operator through its supported parent task route, then follow the one-module recipe; no second operator or editor takeover is introduced.

Latest Claude recommendations (owner-reported19s to1.2s after greedy meshes/Nanite off) are compatible references, not a wrapper benchmark. This adapter preserves the verified Codex importer with requested Nanite off/vertex-color REPLACE and its normal100cm bounds contract. Baking an additional0.01 import scale would violate that existing contract and is not added. Pipeline-stack overrides, UCX recognition, async completion callbacks and a custom toolset remain separate follow-ups requiring installed-version and actual saved-output proof. No experimental uFBX, remote-execution enablement, world restructuring, scheduler replacement or resource downloads are introduced by this slice.

## Deferred validation checklist

No checklist item was executed in this slice. Current user instructions defer tests/benchmarks and preserve the live editor.

- Portable receipt checks: source/settings/dependency/engine/backend/loaded-code changes invalidate keys; corrupt receipts stop; missing/modified/dirty outputs cannot skip; snapshot changes stop; lock ownership cannot be stolen; unfinished states require explicit reconciliation.
- Owner native acceptance: confirm loaded source head and seam, actual backend/options, body/material/collision/bounds, explicit saves and clean packages; rerun identical input and retain a real unchanged-skip receipt.
- Resume/failure cases: saved first item survives later failure, missing input causes no mutations, save failure never earns `saved`, editor crash/unknown import remains blocked until inspected, wrong namespace and dirty existing outputs are refused.
- Keep imported/saved assets separate from world placement, quality approval, gameplay/collision acceptance and throughput measurement. No mock or filesystem receipt proves a playable scene.
