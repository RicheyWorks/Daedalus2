# SkyFarm greenhouse bay R1

The first bay is a partial opaque delivery under
`/Game/Daedalus/Art/SkyFarm/GreenhouseBayR1`. Thirteen packages have confirmed
first saves and independent asset readback: seven StaticMeshes and six direct
Materials. Seven decorative actors are placed at the shared origin
`[-5000, -19000, 5218]` cm, with zero rotation and unit scale. The glass mesh and
its transmission Material remain unsaved and unplaced.

The operator confirmed one map save returned `TRUE`, taking
`19.778900199999043` seconds. Independent final world readback then confirmed
the partial delivery: **231 saved packages, 152 selected actors and the unchanged
184-source baseline**, with all 13 new package backups verified. Compute release
was confirmed at `2026-10-16T08:17:15.487200Z`; the compute lock was absent
afterward and only the Unreal ownership lease remained. Hub receipt: `32963`.

## Retained source and evidence

Producer packet:
`C:/Users/730ri/Documents/Codex/2026-10-13/task-3/sky-farm-greenhouse-delivery-r1/`.

- `Bld_SkyFarm_GreenhouseBay_R1.glb`: 88,052 bytes, SHA256
  `1e208959d249b8b781027ad2bae69dbb70bb4472db01e9bf12da707d93ad7d0a`.
- `manifest.json`: 5,639 bytes, SHA256
  `7082cd07018dfa21254023ab5e715645e11e099a455a13cd81d59e2ad4f62a96`.
- Eight identity-transform mesh roots contain 1,452 triangles. The seven opaque
  groups contain 1,404; the held glass contains 48. Both copper groups share one
  material. Entry/Repeat empty roots are metadata, not spawned actors.
- Source bounds use the existing baked glTF XZY conversion to centimetres once;
  mesh build scale and actor scale stay one. Preserve the common source pivot.

Receipts live under
`C:/Users/730ri/Documents/Codex/2026-10-14/task-2/native-ingestion/SkyFarmGreenhouseBayR1/`:

- `independent-source-qualification.json` records the source geometry and raw PBR.
- `DeliveryR1/asset-native.json` retains the original one-import terminal halt.
  The import returned all 15 paths in 7.7791436 seconds; it attempted no saves.
- `DeliveryR1/actual-shared-MF_Default_Body.t3d` retains the actual built-in
  function witness (253,210 bytes, SHA256
  `e016a4d2d605b4a29cad34749488f1c360049d02f256c3e337e853c82317f9b7`).
- `DeliveryR1/RecoveryR2/asset-remaining-native.json` and
  `asset-remaining-readback-result.json` confirm all 13 opaque saves/readbacks.
- `DeliveryR1/RecoveryR2/world_place-result.json` records actors `StaticMeshActor_4268`
  through `_4274`, preservation of all 22,871 prior world actor digest records
  and the 145 prior selected actor records, plus fresh floor/clearance evidence.
- `DeliveryR1/RecoveryR2/camera-restore-result.json` confirms restoration of the
  original camera. Its sibling `world_save-result.json` records the map save.
- `DeliveryR1/RecoveryR2/world_readback-result.json`: 367,830 bytes; final native
  stage `PARTIAL_GREENHOUSE_SEVEN_PLACED_ONE_MAP_SAVED_READBACK`.
- `DeliveryR1/RecoveryR2/saved-production-baseline.json`: 523,455 bytes, SHA256
  `7d7a33679e79b909b7f382a42144bbceccff475281e3cdbd2248e0b829e4614e`.
  The saved map is 209,423,517 bytes, SHA256
  `f8887fde80262c7c20d4ab5a4160fb89df10438ed5e4d4d4d85a4367b074cd5f`.
- `DeliveryR1/RecoveryR2/completion.json`: 13,789 bytes, SHA256
  `d2174594c7e3820848d78eabf69066eb13f2b82d745b010a5c79372ff4478b81`.
  Its sibling `compute-release.json` records the verified release.
- `DeliveryR1/RecoveryR2/native-greenhouse-partial.png`: 1,806,276 bytes, SHA256
  `8fab316e5401bb068d8bbdf05bc1fa7e1986c1daa2167721c40c299e62ade4a3`.
  The operator personally reviewed the teal frame, tan beds, green foliage and
  pale aisle; absent glass is an explicit partial-delivery limitation.

## Receiving lessons

The custom stack used `InterchangeGenericAssetsPipeline`. Its material import
mode defaults to `ImportAsMaterials`; importing materials does not imply MIC
outputs. Native reconciliation proved eight StaticMeshes and seven
`/Script/Engine.Material` objects, all initially unsaved. The original MIC-only
inventory guard correctly stopped before metadata, saves or placement.

The remaining-only receiver qualifies those existing objects without importing
again or replacing their materials. Its closed direct-Material qualifier checks
four expressions, 89 unique function inputs, exactly three connected linear
RGB/metallic/roughness constants, the actual default alpha/emission/strength,
effective opaque/double-sided flags, and all 30 material roots using explicit
class defaults plus public T3D serialization. It does not clear errors from the
old named-parameter validator or assume missing parameters mean zero.

`Vector4f` preview values expose editable reflected fields `X`, `Y`, `Z`, `W`.
Read them with `get_editor_property`; generated `.x` attributes were unavailable.
That first remaining-only attempt halted before tags or saves, was retained,
and the corrected source received a new recovery receipt.

The host's file mapper admits only the closed 15 greenhouse names in this exact
namespace, maps them to the fixed Content directory, and delegates every old
package to the existing mapper. This resolves the older Ingestion-only path
restriction without changing shared source. World phases admit their exact
`execute_python` marker; asset phases use the existing labelled steps guard.

## Source entry points and limits

- `tools/unreal/codex_skyfarm_greenhouse_delivery.py`: retained dispatches,
  source pins, remaining-phase selection, backups and file-only finalization.
- `engines/unreal/DaedalusLink/Content/Python/daedalus_codex_skyfarm_greenhouse.py`:
  frozen original import and additive world phases.
- `daedalus_codex_skyfarm_greenhouse_remaining.py`: private receiving adapter,
  qualification, metadata and previously unattempted first saves.
- `daedalus_codex_skyfarm_direct_material.py`: read-only strict direct graph
  qualifier. Corrected executed checkpoint: 10,171 bytes, SHA256
  `3f71debd42dc3348df5821540b7cbad23cca188b498e31a49a6133679d79ff15`.

Any retained dispatch or partial journal forbids automatic replay. Reconcile
uncertain outcomes read-only; do not reimport or repeat a save. Keep held glass
files absent and save only the intended map, never all dirty content. New
actors have collision disabled; no gameplay, navigation, walking, crop,
grapple, transmission-glass or physics acceptance is claimed. No tests, Play,
build, editor restart or global-setting changes were part of this delivery.
The preservation digest covers actor poses and static-component records, not
all instance transforms or complete serialized actor properties.

## 32971 glass receiving contract — source stage

Codex's file-only qualifier and delivery parser now retain the original BLEND
alpha `0.1599999964237213` independently from transmission `0.25`. Installed
UE5.8 source maps this role to `MF_Transmission_Body`, ThinTranslucent,
Translucent and SurfacePerPixelLighting. Qualification requires the separate
ThinTranslucent custom output as well as all 30 ordinary roots; an alpha-only
graph cannot pass. A connected `AlphaMode=2` constant and an evidenced function
default of 2 are both source-backed forms. No output index is guessed.

Sixteen tiny offline contract checks pass, including custom-output, mask,
extra-connection, raw-factor and empty-evidence regressions. The file-only
preparer verifies the original GLB/manifest, baseline and ten installed source/
body pins. `GlassSourceR1/qualification.json` retains the source result.
Neither new module collects native state or dispatches editor work. Existing
glass graph/defaults, native API return shapes and actual transmitted appearance
remain unknown: the previous graph inspections explicitly skipped glass.
Next is a separately scoped guarded read-only observation of the two held
objects after the producer's actual terminal/release. Saving, placement and
visual acceptance require later admission; both objects remain held.
