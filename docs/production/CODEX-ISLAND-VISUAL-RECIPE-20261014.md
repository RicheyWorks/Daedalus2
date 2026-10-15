# Operating the existing Unreal connectors: production lessons

This is the reproducible operating guide for the 2026-10-14 Codex island and
Aetherflow delivery checkpoint. Its purpose is to teach how to discover the
installed tools, choose a suitable route, notice what actually happened, and
retain enough evidence to continue safely. Values below are observations or
retained source settings, not a new project-wide rendering standard.

The completed Aetherflow world journal records three saved plant mesh assets,
two added decorative plant actors and one final map save. Glasskelp is saved but
held from world placement because its original geometry extends below the
waterline. This does not establish swimming, navigation, collision, animation,
ecology or full visual-bar acceptance. The final independent readback must be
read separately from that save journal.

## 1. Start with the outcome and the actual tool inventory

The production goal was saved, inspectable Unreal assets and additive staging,
with existing islands preserved. Blender scripts, GLBs, FBXs and attractive
source renders were intermediate results. A successful socket connection was
also only an intermediate result: it did not establish editor ownership, the
current map, the actual importer backend, a completed job or a saved package.

There are two existing Unreal routes in this repository:

| Route | Actual contract | Appropriate use in this delivery |
| --- | --- | --- |
| Epic Unreal MCP | `tools/unreal_mcp/client.py`; Streamable HTTP at `http://127.0.0.1:8000/mcp`; initialize and retain the MCP session | Discover toolsets, inspect each toolset, read PIE/map/camera state and use exposed actor/save operations |
| Existing Claude Unreal bridge | `connectors/claude-asset-pipeline/asset_pipeline/wire.py`; one JSON line each way over TCP, default `127.0.0.1:9877` | Execute a bounded inspected Unreal-Python body, run cooperative `daedalus.steps`, and use the existing screenshot route |

These are complementary interfaces to the same editor. Changing transport does
not acquire a second editor turn or authorize a second writer. No additional
editor, helper protocol, dependency, credential, network or security-setting
change was needed for this work.

For capability discovery, use the installed client's actual meta-tool contract:

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path("tools").resolve()))  # from the repository root
from unreal_mcp.client import Mcp

mcp = Mcp(timeout=30)
toolsets = mcp.toolsets()                         # list_toolsets
app_schema = mcp.describe("EditorToolset.EditorAppToolset")
pie = mcp.call("EditorToolset.EditorAppToolset", "IsPIERunning")
```

`Mcp.call` takes the **short** tool name as its second argument. Its client
unwraps `returnValue` when present. Discover the installed schema rather than
assuming every native property is represented by a connector tool. This guide
documents source/API operations that were inspected or used; it does not claim
any Unreal menu or UI experiment was performed.

## 2. Choose a route from the missing capability

The installed MCP interface did not expose every material parameter needed for
the retained palette. The production implementation inspected Unreal's existing
`MaterialEditingLibrary` route and used it through bounded Unreal Python. It
read back instance parent, `Tint`, `Roughness` and `Metallic`; the Aetherflow
profile additionally retained `Clearcoat` and `ClearcoatRoughness`, two-sided
behavior and a clearcoat material-attributes base.

The native material profile queried
`get_material_expression_input_names` and matched the exposed input names by
their semantic spelling. This was preferable to guessing pin labels or changing
an existing shared material. Existing island component overrides and new owned
material assets supplied the missing control while preserving the saved meshes
and the shared Claude vertex-colour material.

The concrete tool choice was:

1. Use MCP for the exposed editor-state, actor and save contract.
2. Use the existing wire route for a narrow native read or operation that the
   exposed tool schema could not express completely.
3. Verify the native return value and the affected object/package state.
4. Reserve UI operation for a capability that actually requires it; no such
   fallback is claimed in this delivery.

A read-only native-body example, using the existing envelope, is:

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path("connectors/claude-asset-pipeline").resolve()))
from asset_pipeline import wire

reply = wire.call(
    wire.UNREAL, "execute_python",
    code="import unreal\nresult={'engine': unreal.SystemLibrary.get_engine_version()}",
    unattended=False, timeout=30, side="Unreal")
value = wire.obj(reply, side="Unreal", what="engine version readback")
```

The `unattended=False` choice uses this bridge's direct editor route. It is not
an instruction to change Python Remote Execution or any project setting.

## 3. Distinguish requested options from observed behavior

The existing import caller uses `AssetImportTask`/`FbxImportUI`. Actual returned
assets in this session had `InterchangeAssetImportData`. Consequently several
requested FBX options were reported as `unavailable` through that object's
readback, while `nanite_enabled` was observed as false. The caller's settings
alone did not prove that the active backend applied every option.

The correct evidence was the actual `imported_object_paths`, exact source-name
set, saved asset class, output package bytes, native bounds and material slots.
The source importer requested no automatic collision, no Nanite, no generated
lightmap UVs and no imported textures/materials; these remain requested values
except where an effective native property was independently observed. Source
UCX counts are also not native collision or walkability acceptance.

Relevant implementation:
[`codex_reviewed_ingestion.py`](../../tools/unreal/codex_reviewed_ingestion.py),
[`codex_admitted_asset_assembly.py`](../../tools/unreal/codex_admitted_asset_assembly.py)
and the unchanged prepared-importer contract recorded in the admission receipts.

## 4. Know which response layer you are reading

`wire.call` parses the socket envelope and returns its `result`. For
`execute_python`, that returned value is itself a dictionary containing the
script's `stdout`, `result` and execution-mode information. `wire.obj` takes the
inner script result and deliberately requires a dictionary.

That distinction caused a real production failure. The component-override
script successfully returned a **list** of two applied actor/slot/material rows.
Passing it to the dictionary-only `wire.obj` validator raised
`expected a JSON object`. Both actors and their component materials already
existed; the map had not yet been saved. This was a response-shape failure after
known mutations, not evidence that those mutations had not happened.

The shared assembly helper now reads that known list result explicitly and
checks its row count, labels, exact source slot sets and material order. The
original failed journal was retained. The bounded reconciliation path verified
the actual actors, transforms, old actor state, all mesh files, PBR values,
dirty packages and outstanding bridge work, then performed the **first map-only
save**. It did not repeat a spawn or material assignment.

See [`codex_saved_asset_assembly.py`](../../tools/unreal/codex_saved_asset_assembly.py)
and `reconcile()` in
[`codex_aetherflow_delivery.py`](../../tools/unreal/codex_aetherflow_delivery.py).
The reconciliation route admits only the exact five responded actions and known
parser failure before any save attempt. A pending/uncertain save blocks it.

## 5. Cooperative jobs, asynchronous completion and queue observations

`daedalus.steps` advances a generator across editor ticks. Production imports
yielded between bounded items, using `budget_ms=1` and an admission deadline
inside the acknowledged operator's lease. Yielding is a responsiveness mechanism;
it does not make every native import or save call interruptible.

The installed bridge also has an explicit asynchronous transport capability:
an `async: true` request returns a `job_id`; `job_result(job_id=...)` reports
`running` or `done`, with the final reply after completion. Source inspection
confirmed this capability. The examples here do not assert that every production
call in this delivery used asynchronous submission.

The following queue lesson is from an actual retained reconciliation read:

| Observed field | Actual value | Meaning |
| --- | --- | --- |
| queued jobs | 0 | Nothing was waiting in the input queue at that observation |
| running job | one `execute_python`, exact code SHA | The readback itself, identified by its code rather than a reused label |
| unfinished asynchronous job boxes | empty | No retained async job box was still awaiting its done event |
| remote execution lock | false | No command held that bridge lock at the observation |
| `Queue.unfinished_tasks` | 1134 | Informational cumulative bookkeeping here, **not** 1134 active commands |

An earlier preflight falsely treated the inspecting command and that queue
counter as conflicting work. The corrected read compared the exact executing
code SHA in `_running` and inspected `_job_boxes` done events. The bridge's pump
consumes queued requests without balancing this counter with `task_done()`.
These are inspected implementation details, not a proposed stable public API.
The final general readback still reports queue/background compilation as
`not_queried`; a narrow reconciliation observation must not become a permanent
global idle claim.

## 6. A timeout or disconnect does not undo an operation

`wire.call` forwards its timeout as `bridge_timeout` as well as using it for the
socket wait. The existing wire-source documentation records an older case in
which a client response timed out while the editor kept running. Do not convert
that historical warning into a claim that this delivery suffered the same event.

For a timeout, closed connection or malformed response:

1. Retain the request identity/code SHA, raw reply if any, and journal state.
2. Treat a dispatched mutation with no conclusive response as uncertain.
3. Read its job status, retained receipt, exact actor/output state and disk
   witnesses through the existing route.
4. Reconcile a known result; do not resend the mutation merely because the
   client did not receive its preferred shape.

The actual Aetherflow response-shape incident followed this pattern. The saved
receipt names and actor labels make a result checkable without guessing from
the viewport. Existing journals refuse blind replay of an unfinished attempt.

## 7. Verify saves and measure the phase that actually ran

A save-return boolean is necessary evidence, but the production receipt also
binds exact `/Game` paths to `.uasset` files and SHA-256/byte counts. World saves
record the `.umap` witness. Readbacks compare dirty-map/content lists, PIE/map
state before and after the read, all protected source/output files and prior
actors' references, meshes, transforms, component materials, overrides, folders
and tags.

The final Aetherflow readback is explicitly bounded to 87 prior actors plus two
new actors and 82 prior mesh files plus three new ones. It also reads the five
PBR instances and their base, requires zero glasskelp/HeroR2 world references,
and preserves the existing five PowerUnit references. It reads only the first
StaticMeshComponent per loaded actor; it does not establish unloaded-world or
gameplay behavior.

Measured, single-run observations from `AetherflowR2/adoption.json` and
`AetherflowR2/world.json`:

| Phase | Recorded elapsed seconds | Scope |
| --- | ---: | --- |
| production import/save pass | 1.095737 | Three selected plant admissions through the existing guarded route |
| identical-input reuse pass | 0.462106 | Same prepared payloads; retained receipt/byte checks |
| actor assembly | 0.478248 | Recorded actor portion; the interrupted material-response phase was not timed completely |
| final map save | 20.560135 | One map-only save; returned true |

Final saved map witness: `0402ccf48ba037fb475e4cb4818b79158312888510628cd7b42f7ad317da8afa`,
209,306,026 bytes. These timings are not benchmarks, speedup measurements or a
promise for another map. The useful batching decision was to keep related small
assets in one bounded admission sequence and apply component materials before
one final world save. It was not to hide partial outcomes in a large blind batch.

## 8. Capture the real viewport and verify actual PNG pixels

The existing `viewport_screenshot` bridge helper calls
`unreal.AutomationLibrary.take_high_res_screenshot`. The native API's observed
default `force_game_view=true` can change the viewport display state even when
the wrapper has no explicit game-view parameter. A screenshot call is therefore
not assumed to be a perfectly inert read.

The updated
[`codex_staging_review.py`](../../tools/unreal/codex_staging_review.py) records
camera/view/dirty/map state, writes a journal **before** each camera/screenshot
call, requests bounded dimensions up to 3840×2160, decodes the returned PNG and
checks the IHDR pixel dimensions. A requested resolution is not proof of the
received resolution. It restores the temporary camera and game-view state after
all captures have known results, then checks display state and unchanged map
bytes. An uncertain capture remains inspection-required instead of triggering
an unrecorded replay/restoration sequence.

Inherited settings were read in
`CodexContest/codex-inherited-visual-settings-2255.json`: horizontal FOV 90,
`VMI_LIT`, game view false; Daedalus Sun intensity10, pitch−51.000031/yaw−60,
RGBA255/250/239/255, movable and shadow-casting. Temperature6500 is stored but
temperature use is false. The unbound enabled `Daedalus_PostFX` has manual
exposure and bias10.5 overrides; bloom override0.675. Stored min/max exposure
0.03/8 and physical-camera exposure true have their respective override flags
false. These are inherited readbacks, not lighting/exposure/FOV tuning performed
for this request. Effective project/CVar influences were not fully queried.

Inspect bright highlight clipping, the gray staging background and whole-frame
occlusion before attributing a color problem to the source palette. Camera
framing should show the complete object and a meaningful route/detail view.
An overhead view alone cannot establish a player-height entrance or clear crown
silhouette. The main operator appends the actual new presentation image paths
and their dimension/restore witnesses after capture completes.

## 9. Repeatable workflow and next connector improvements

For the next ready package: identify its exact reviewed payload and owner;
discover the installed tool schema; read the current editor/lease/job state;
pin source/config bytes; select the smallest suitable existing route; retain the
request before dispatch; verify the actual response type; bind imports to native
paths and saved bytes; inspect bounds, slots, framing and PBR values; save the
intended packages; independently read back preservation and dirty state; capture
and retain the actual images. Share the concrete recipe and limitations through
the established owner handoff. Do not turn a ready production package into broad
harness research or silently unhold an unfinished quality review.

Ranked follow-up proposals, **not implemented by this guide**:

1. A typed response envelope declaring whether the script result is an object,
   list, scalar or job reference; preserve raw outcomes when validation fails.
2. A supported queue/job-status endpoint with self identity, queued/running/done
   semantics and reliable counters, replacing dependence on private bridge fields.
3. Capability metadata distinguishing requested from effective importer options,
   units/axes, exposed material fields, screenshot display side effects and result
   schema. Report `unavailable` explicitly rather than guessing a default.
4. Bounded batch readback/admission APIs returning a result per item plus a
   checkpoint, with explicit save boundaries and partial-outcome recovery. Measure
   end-to-end latency before claiming an improvement over the existing batch path.

## Appendix: retained visual recipe and the actual adjustments

The complete palettes, surface values, layer scales, configuration and geometry
hashes live in these source receipts under
`engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/`:

| Candidate | Exact source receipt | Geometry/palette recipe |
| --- | --- | --- |
| HeroR4 | `HeroR4/h84011/CodexIsland_summit_rim_84011_HeroR4.receipt.json` | seed 84011; `summit-rim`; radius 46/depth 22/terrace 3/relief 21; palette seed 91022, `teal-coral-ivory-v1`; crown heights `[7,9,12,8,6,5,7]` |
| GardenGateR1 | `GardenGateR1/Final/h84022/CodexIsland_cliff_garden_84022_GardenGateR1.receipt.json` | seed 84022; `cliff-garden`; radius 46/depth 28/terrace 3/relief 18; palette seed 92022, `lime-seaglass-lavender-v1` |

The seed is only part of the identity: retain the revision, full configuration,
palette and source-code/inventory witnesses from the receipt. A later generator
edit can change its configuration/source hash even when the same seed produces
the same visible shape. Use the recorded source checkpoint and artifact hashes
for byte-level reproduction; do not overwrite a frozen export with a new build.

Hero's cataloged reference is Blender Boss (`blender-team` author, team unknown);
Garden's is Buffffff/Six-F (Grok provenance). Their source receipts preserve the
original image/manifests and inventory hash; new variants do not replace those
originals. [`codex_contest_island.py`](../../tools/blender/codex_contest_island.py)
reuses [`voxel_island.py`](../../tools/blender/voxel_island.py)'s exposed-face
mesher, shared corner cache and one object per layer. Terrain stays at 1 m;
only Hero's fitted route uses 0.25 m cells. Unequal crown heights, a pale path with
warm sand edges and omission of whole obstructing tree components create a
readable route and skyline. Garden's widened entry fan, fitted 3×3 gate-post
foundations and crop/cottage spurs connect its retained bowl layout.

The first Garden preview had a narrow entrance and a crop camera inside the
cliff. The retained adjustment widened the fan and raised the crop view. Wide
`gate_full`/`crown_full` views reveal occlusion hidden by a close crop. Retain both
player-height and full-frame evidence; these source fixes do not prove movement.

The full exact RGB/surface tables are in the receipts. Island RGB is sRGB:
convert once using `c/12.92` when `c<=0.04045`, otherwise
`((c+0.055)/1.055)**2.4`. Hero grass `(0.3185216,0.6469971,0.398152)` becomes
approximately `(0.082747,0.376183,0.131577)` linear; Garden grass
`(0.5124962,0.7235241,0.3416641)` becomes `(0.225790,0.482222,0.095589)`.
Read byte-color identity through `color_srgb` when assigning stable palette
slots: reading `.color` previously misidentified darker roles. Aetherflow GLB
factors are already linear and must not receive that conversion again.
Default island roughness/metallic is 0.85/0; water/foam 0.18/0,
crystals 0.28/0.12, roof 0.42/0.55 and trunk 0.72/0. Garden remaps cottage
wall/roof to sand/crystal; its actual used slots are authoritative.

The observed native basis is `origin_cm + (100*x,-100*y,100*z)`, actor scale 1,
zero rotation. Hero origin is `[-317950,297700,17515.324]`cm; Garden origin is
`[-343550,323300,18215.324]` cm. Their 256 m per-axis horizontal separation is
temporary staging. `codex-reviewed-2130.footprints.json` scanned 22,790 actors,
matched native source bounds and measured 50 m clearance above existing overlapping
tops. Check cloud-inclusive bounds, not just the 92 m body. Garden's floor cell
index Z0 has an exposed top at Z1 m; retained water tops at Z0.

Repeatable native camera names and exact centimetre eye/target offsets live in
`QA/hero-r4-native-local-views.json` (`overview`, `route`, `crown_full`) and
`QA/garden-gate-native-local-views.json` (`overview`, `gate_full`,
`courtyard_player`, `crops`). The inherited 90-degree FOV is read separately.
Preserve old revisions; the generator restores selection and removes only its
own created objects. A cache skip requires matching config and every artifact
hash. Preview GLBs remain a separate stage from final FBX/native delivery.
The Aetherflow R1 normal-preservation failure and R2 imported-custom-data join
are a separate source lesson: R2 recorded zero position/normal error without
loosening tolerances. Keep that evidence distinct from native image/collision
acceptance.

## Evidence handoff and platform boundary

The four presentation captures completed on2026-10-14 at23:01–23:02UTC. Each is an actual native3840×2160 PNG from the saved Unreal scene, not a Blender render or an upscaled image. All four were personally inspected for nonblank/full output, composition and private/editor UI. The wide frame retains physical staging plots; the court has bright inherited highlights, and the crop frame retains a foreground rim. None of these observations is a gameplay or final BAR acceptance result.

| Actual native image | What to inspect |
| --- | --- |
| [Hero ascent](../../engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/QA/CodexIsland_summit_rim_84011_HeroR4.social4k-2300-hero-hero_route.png) | Pale quarter-metre route leads toward the tiered crystal skyline; sky separates the silhouette |
| [Whole island](../../engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/QA/CodexIsland_summit_rim_84011_HeroR4.social4k-2300-hero-island_wide.png) | Full terrain/shoreline/cottage/tree distribution; existing surrounding plots remain visible |
| [Garden courtyard](../../engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/QA/CodexIsland_cliff_garden_84022_GardenGateR1.social4k-2300-garden-courtyard.png) | Player-height path, cottage, trees and terrace enclosure; inspect bright path highlights |
| [Crop detail](../../engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/QA/CodexIsland_cliff_garden_84022_GardenGateR1.social4k-2300-garden-crops_detail.png) | Repeated crop rows with clear aisles; foreground wall occupies the right edge |

Exact PNG hashes, byte counts, camera transforms and restoration witnesses are in `QA/staging.social4k-2300-hero-review.json` and `QA/staging.social4k-2300-garden-review.json`. Both record unchanged map SHA `0402ccf48ba037fb475e4cb4818b79158312888510628cd7b42f7ad317da8afa`, empty dirty lists and restored original game-view=false/FOV90. The original camera was restored within floating-point transform precision. Native `force_game_view=true` hid overlays temporarily; no lighting/exposure/FOV or world package was altered, and no Play session ran.

From the repository root, reproduce into a NEW revision name, preserving earlier captures:

```powershell
python tools/unreal/codex_staging_review.py engines/unreal/DaedalusLink/Content/IslandSource/CodexContest --island CodexIsland_summit_rim_84011_HeroR4 --revision NEW_PRESENTATION --assembly engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/codex-hero-r4.world.json --local-views engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/QA/social4k-hero-cameras.json --width 3840 --height 2160
```

Run only as the acknowledged operator on the matching saved map. Do not rerun an unfinished revision; inspect its journal/native outcome first. One-at-a-time native captures worked here; no GPU-memory benchmark or general safe4K ceiling was established. The connector's requested width/height metadata was independently checked against each PNG's actual IHDR dimensions.

The main operator links the actual final readback and newly captured images at
the safe checkpoint and shares this guide through the established owner hub.
The shared visual bar remains
`C:/Users/730ri/.codex/worktrees/island-mesh-pool/Daedalus2/docs/production/VISUAL-QUALITY-BAR.md`;
existing team lessons remain in `C:/Users/730ri/projects/bot-team/BOARD/LESSONS-LEARNED-UNREAL.md`.
This guide adds operating knowledge; it does not replace either source or confer
a BAR pass.

The separately reported Windows Library helper `os.setxattr` error belongs to
the artifact/platform delivery layer. It is not evidence of an Unreal connector,
import, shader or map-save failure. Keep those outcomes separate and retain the
available local/source deliverable while that platform limitation is resolved.

The exact Library reference resolved as2041×766 metadata, but local materialization failed on Windows `os.setxattr`; it was not visually inspected here. The subsequent official prepared-upload helper for the four images stopped before preparation with `Library prepare_uploads is not available` and no stdout/results. No Library create was confirmed or retried through a different route. Library delivery is pending while the exact local PNGs remain available. These are artifact-delivery limitations, not Unreal capture failures; nothing was posted to X.

## 2026-10-15 01:18 UTC: static gems and skinned Miri delivery

Current asset-only checkpoint is `CodexContest/codex-gems-miri-0118.checkpoint.json`: 102 tracked StaticMesh files, the same89 staging actors and unchanged saved map SHA0402ccf48ba037fb475e4cb4818b79158312888510628cd7b42f7ad317da8afa. Ruby/Sapphire/Emerald extend the earlier three saved eggs; all six retain their original FBX/sidecar/color witnesses. `tools/unreal/codex_catalogue_gems_delivery.py` reuses the first batch runner with a fresh folder and99-file baseline, never replaying that completed batch. Each gem's568 triangles and four source RGBA values passed native readback before save. Static catalogue unit100 assets retain build scale1 and REQUIRED future actor scale.01, including their existing pivot offset.

Miri v2 is a different contract: the inspected skinned GLB33b8c1a8a5a3bd513648faf56822b250b7b8254efb55f668031124c7f47d22bc uses the existing cast AssetImportTask/glTF route, native centimetres and actor scale1. Its17 newly saved assets are one SkeletalMesh, one Skeleton, three AnimSequences, eleven constant-PBR material instances and one generated PhysicsAsset. All17 authored joints/parents,1320 triangles, approximately99×141×227cm rest dimensions and exact linear base colors/roughness/metallic/opaque/double-sided materials passed readback. Do not bind the static vertex-colour material or apply the eggs' actor scale.

The first import returned successfully but its optional legacy AnimSequence.data_model track enumeration was null. It stopped before any save. Preserve `MiriV2/native.json` and the original pinned module; `known-import-readback.json` proves the returned17assets and changing native bone poses. `codex_miri_finish_delivery.py` and its pinned native companion perform first saves only, with no import branch. `finish-native.json` records17 true saves, and `readback.json` verifies those files, all102 prior static files/89actor fields and the map. Never rerun a dispatch or delete journals to bypass a partial/uncertain result.

Actual native phase observations: gem import/save.148427/.070432s, .112602/.017918s and .089536/.014802s; Miri import13.085156s and17 first saves totaling.945221s. No whole-intake or comparative speed claim follows. Source clip spans2/1.5/1s became native lengths2.0333333/1.5333333/1.0333333s; changing local pose samples do not establish continuous loop quality, planted feet, knee-gap correction, transitions, appearance, collision or gameplay. Generated physics is not authored collision acceptance. Nothing was placed and no world save, Play, test suite or project build ran.

PR157a22cd83f/v6 remains source-only for this editor: all10 owner source pins match, installed files match0/10, and loaded class reflection lacks its new raw-key/controller dispatch methods. Native minigame acceptance needs Minesweeper-preserving integration plus UHT/module build/load; this asset recipe does not replace a live plugin or start a competing build. The existing cabinet remains untouched. The eighteen previously held fish/water/Rainlight/dragon packets remain separate from these completed deliveries.

## 2026-10-15: compiled arcade source and visible Garden construction

`CodexContest/codex-arcade-compiled-0215.checkpoint.json` records the later source/build stage: PR157a22cd83f plus PR139 Minesweeper, eleven byte-exact published source files, successful UHT and a serial isolated module compile/link in556.72 seconds. The supported foreign-plugin build used a copied host/plugin, normal UnrealEd shared PCH, `-Module=DaedalusLink -MaxParallelActions=1 -NoEngineChanges -NoUBTMakefiles -NoHotReload`; canonical source, DLL and settings were preserved. Optional `-NoSharedPCH` exposed unrelated baseline incomplete-type includes and was removed before the successful retry. Keep that failed attempt separate; a new shadow DLL does not activate the running editor. This single-module build omits the metadata-writing leaf action: actual TargetMetadata and the unchanged canonical receipt both identify BuildId55116800 and the same module filename. Do not fabricate a new receipt or edit BuildId. Controlled normal activation and loaded-method/input acceptance remain pending.

The user's subsequent request to watch real construction produced `codex-garden-landing-0230.checkpoint.json`. The existing main editor was focused on GardenGateR1, and eleven new saved-module actors were assembled one at a time: four flush deck sections, two raised crystal posts and three arch-frame pieces. The source route surface is1m; native bounds verify the4m span and3.5m clear height on25cm connections. Existing palette bindings are copied onto new components; no shared asset changes are needed. All90 earlier Codex actor records (89 staging plus Pong) are unchanged. One map-only save returnedtrue in24.145565 seconds; staging is now100 actors and the map SHA is5690b48f9cdc9f50251c08127b161ab4f3afae49754b75316d561da2a3a80933. The original map is separately backed up. `codex-garden-landing-r1.recipe.json` preserves the exact placements/material templates, and three inspected960x540 native images show the empty route, eight-part assembly and saved arch. This is saved visual assembly, without charging, collision or gameplay acceptance. Earlier intake helpers intentionally retain historical map guards; use this additive checkpoint to reconcile the next intake rather than rewriting old receipts or relaxing protection.

## 2026-10-15: normal arcade activation completed

The later `CodexContest/codex-arcade-activated-0317.checkpoint.json` closes the pending installation/load stage above. The user authorized this bounded normal transition: `CLOSE_SLATE_MAINFRAME` requested the existing main-frame close workflow, zero editor processes were verified, and eleven exact source leaves plus the matching DLL/PDB were installed atomically with original source/binary/current-map backups. The canonical `.modules` stayed unchanged. A visible normal reopen loaded DaedalusWorld in PID28788; no forced close or concurrent editor was used.

OS loaded-image identity and backing DLL SHA80eca0a812b19e2e6a0d79d17b454eb9863bffbae72c36983206373f5d812e1d are recorded separately from native reflection. Both `submit_arcade_source_key` and `submit_arcade_source_controller_button` are present, and the existing cabinet's twelve-entry catalog matches installed source, including Minesweeper. All101 Codex actor records (100 staging plus Pong) retain identical transforms/folders/meshes/ordered material bindings. Map209329457B/SHA5690b48f9cdc9f50251c08127b161ab4f3afae49754b75316d561da2a3a80933 remains unchanged. Final readback is correct world, PIEfalse, clean packages and idle bridge queue. This proves activation and preservation, without dispatching input or establishing gameplay/HUD/controller/save-recovery acceptance.

Normal startup completed in190.62s despite a skinned-asset memory warning. Installed primary source confirms that an over-budget estimate still permits at least one compilation job; a quiet frame0 log alone did not establish deadlock. Actual logs subsequently advanced into the world and the bridge opened. No resource/settings changes or forced process action were needed. Free-memory observations are timestamped machine readings, not a general safe build/render budget.

The existing MCP server did not auto-start because current project settings have `bAutoStartServer=False`. Its already registered `ModelContextProtocol.StartServer 8000` console command restored the existing `/mcp` route at runtime without saving configuration. Actual OS listeners8000/9877 are both127.0.0.1 owned by28788; fresh native `IsPIERunning` returnedfalse and Slate selected the existing main window. A startup log announcing a server is insufficient by itself: verify the listener and a fresh read-only response.

`QA/garden-after-activation-corrected-0308.png` is the personally inspected960x540 native image of the preserved arch/landing. Python's positional Rotator arguments produced an initial wrong-axis view; the retained companion uses explicit `pitch=`, `yaw=`, `roll=` and verifies the returned camera. The failed view and historical03:05 pending/MCP-refused readback remain intact. No world content or map save was needed to restore this view. Eighteen source/adapter-held packets remain held, and future intake must explicitly reconcile this saved100-actor map checkpoint with historical guards.

## Later user-authorized bounded arcade acceptance

`CodexContest/codex-arcade-gameplay-0344.checkpoint.json` records39 passed checks against the installed version. The existing editor loaded a minimal unsaved blank level with one owned cabinet, floor and PlayerStart; its transient game-mode override spawned the real Hero. PIE had22 runtime actors. The cabinet's `auto_advance=False` prevented a second clock while explicit1/60s steps ran. The saved production world was never played or saved during this operation.

All12 catalog games started, advanced once and restarted. Further checks exercised Contra's ordered source-key bonus, separate controller-A method and native launch/restart, Shadow's jump dispatch, Minesweeper flags/safe first reveal/options, and a real Pong point and early serve. Synthetic keys delivered through the focused native Slate widget passed P pause/resume, R restart, the ordered Contra sequence and Enter launch. Actual Hero interaction opened the overlay; inspected2560x1392 native Slate captures show its game canvas, controls, status and source-specific HUD.

Star's save failure was real filesystem behavior: an empty owned directory occupied the originally absent exact save-file target, without permission/security changes. The failed atomic write preserved the pending run and rejected replacement/restart/option/unpause. Removing only that verified empty directory allowed a later real-time retry to save a24-byte DGS1 run. Continue restored the saved run. Synthetic Slate Escape closed the overlay while the same possessed Hero/PIE remained, released owned pause and hid the cursor. The generated run is retained as evidence; its original on-host absence was restored after EndPlay.

Hero EndPlay always writes `Saved/Config/DaedalusHero.json`; exact107-byte Hero and285-byte realm-save backups were made before PIE and restored afterward. The originally absent arcade directory is absent again. One supported reload of the original map exceeded the90s response socket, then completed normally; a separate read-only companion verified all101 actor records, map5690, camera, empty dirty lists and idle queue without replaying the load. Unsupported `PlayerController.get_pawn` readback was similarly reconciled through the supported Hero/controller relation without repeating Escape. No forced process action or settings change was needed.

One visual defect remains: Hero logbook, interaction prompt and character/weapon HUD text draw over the arcade canvas. The three `QA/arcade-acceptance-*.png` images preserve it. Global Hero HUD versus per-player arcade layer placement is a source-supported candidate cause, without a verified fix. This is no exclusive-HUD/visual/BAR pass. Physical controller axes/buttons, disconnect/reconnect, multiple local users, complete levels/game-over transitions and leaderboard failure recovery remain unverified. The39 checks prove their executed paths, not complete game acceptance. `tools/unreal/codex_arcade_acceptance_phases.py` retains the exact source generator whose six executed phase hashes match receipts; importing it performs no native action. Reuse requires a separately prepared owned blank PIE, save backups, explicit fixture control and complete restoration.

## HUD fix source intake; native closeout pending

The game owner subsequently supplied PR157head4b911de6/codebcfb1403, manifestv7. `CodexContest/codex-arcade-hud-fix-source-checkpoint.json` pins and integrates exactly three private presentation files: actor.cpp, Slate.cpp and Slate.h. The foreground host joins the global viewport above HUD10 while retaining engine player geometry, clipping, per-user hit testing and symmetric removal. Independent source/API review found no blocker. These are source claims, without a compiled or visible post-fix result.

Only the exact three-file patch is valid for this integrated branch: the full owner registry still lacks our Minesweeper additions. Before/after SHA256 pins were checked against installed and owned sources; the explicit-LF patch passed in a fresh owned foreign-plugin host. All other137 installed source files, current Mines core/merged registry, native157 DLL/PDB/metadata and all230 app-host files remain unchanged. The fresh host is `task-2/native-hud157`; its prepared single-module command preserves normal shared PCH, default mutex, MaxParallelActions1 and NoEngineChanges. Canonical source/DLL and the editor were untouched by this intake.

The user's requested build, normal activation and corrected screenshot/input/focus closeout remain pending an actual safe serial resource boundary. At04:17UTC the machine reported freephysical3196656KiB/freevirtual1959048KiB, with four existing hd_batch exporters live and no UBT. Producer yield requests31475/31486/31492/31520 have no substantive reply. The existing exporter has no persistent pause signal; a recent completed row or MEMWAIT is not an exclusive compute window. Source preparation is complete, and the owner-reported123 portable checks do not compile this wrapper. The previous39 native checks are explicitly pre-fix. App compilation stays separate and must not replace the live Mines/PR157 DLL with its older source snapshot.
