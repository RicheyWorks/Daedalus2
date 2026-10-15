# Qualified static delivery and recovery notes

Draft source handoff by codex-play-guard / guard_audit, 2026-10-15. Complements the [visual recipe](CODEX-ISLAND-VISUAL-RECIPE-20261014.md) and [team handoff loop](../TEAM-HANDOFF-LOOP.md). Detailed machine receipts and operational identities stay in the local production board.

The delivery adapter is [codex_qualified_static_delivery.py](../../tools/unreal/codex_qualified_static_delivery.py), backed by [daedalus_codex_qualified_static.py](../../engines/unreal/DaedalusLink/Content/Python/daedalus_codex_qualified_static.py). It uses the qualified static Interchange route. It does not make a source-only catalogue entry native-ready, and it does not provide a second editor owner.

## Commands and evidence boundaries

The following are interface examples, not instructions to repeat an existing delivery. Substitute owner-reviewed local paths and distinct saved asset names. The native owner must admit the packet against the current production baseline before `run`.

```powershell
python tools/unreal/codex_qualified_static_delivery.py prepare --folder <NEW_PACKET_FOLDER> --qualification <QUALIFICATION_JSON> --baseline <CURRENT_BASELINE_JSON>
python tools/unreal/codex_qualified_static_delivery.py run --folder <PREPARED_PACKET_FOLDER>
python tools/unreal/codex_qualified_static_delivery.py readback --folder <PREPARED_PACKET_FOLDER>
```

`prepare` requires qualified source evidence, the operator's recorded personal inspection of source views, matching source identities and the current baseline. It refuses an existing output folder. `run` journals dispatch and applies owner/resource/scene guards before native work. The qualified contract records unit/build/future actor scales, pivot, material/color route and exact static output; another source's successful recipe does not admit a different packet automatically.

If the native response is uncertain or only some saves are known, retain the original dispatch/native receipts. Read back an explicit distinct subset of assets whose original native receipt has `save_return: true`:

```powershell
python tools/unreal/codex_qualified_static_delivery.py readback --folder <PREPARED_PACKET_FOLDER> --readback-names <KNOWN_SAVED_ASSET_A> <KNOWN_SAVED_ASSET_B>
```

This reconciles known saves; it never resumes imports or invents a successful save. It verifies exact packet paths, preserved receipts/output bytes and current scene/baseline conditions. An existing `native-readback.json` refuses another native readback. If native readback completed but local finalization was interrupted, use:

```powershell
python tools/unreal/codex_qualified_static_delivery.py finalize --folder <PREPARED_PACKET_FOLDER>
```

`finalize` checks the completed readback, creates local package backups and the extended baseline, and verifies release of this operation's compute lease when applicable. It performs no native import or save. It still reads the coordination service and can release an owned compute lease; it is not an offline command. A later owned compute lease is protected from accidental release. Preserve conflicts for diagnosis rather than overwriting retained evidence.

## Acceptance and next work

A saved asset plus clean readback establishes the stated package/source preservation boundary. Placement and map save require separate receipts. Source screenshots, a saved package, or a camera-only native capture do not establish native appearance, collision, navigation or playability. Preserve the original author's source/preview provenance and compare source views with native views under the exact admitted unit/material route before visual approval.

Recovery priorities are: admit against the latest baseline rather than a historical source count; reconcile known native effects before retrying any mutation; and separate asset-save acceptance from placement, visual and runtime acceptance. Keep protective play limits unchanged during recovery and fit owned native checks within their existing contract. Improvements proposed for the existing adapter/native and source-packet owners are clearer current-baseline admission receipts, explicit saved-subset recovery guidance, and matched source/native view evidence. These are proposals, not new owner assignments or acceptance claims.

## Producer-specific palette and API output lesson

The [palette-transfer helper](../../engines/unreal/DaedalusLink/Content/Python/daedalus_codex_palette_transfer.py) supports only the proven producer contract `voxel_island_q_pow_1_over_2_2_v1`: the producer exports palette channels raised to `1/2.2`, so the owned material uses inverse `Power2.2`. This is a producer-specific transfer, not a universal sRGB decoder or a lighting/visual-quality fix. Matching source and render-LOD vertex colors alone does not establish that the material interprets them correctly.

Verify the installed API's actual output contract. In the inspected UE5.8 path, VertexColor's default RGB output is unnamed (`''`); named R/G/B/A outputs are individual channels. `get_input_node_output_name_for_material_expression` returns a string or `None`, not a success/name tuple. The helper verifies the exact graph, exponent, roughness, connections and producer/owner metadata before read-only reuse. An incompatible graph is preserved and rejected. Reuse performs no mutation, compile or save and does not recheck compile state; fresh creation returns an unsaved material. Admission, new-component binding, asset/map saves and subsequent native appearance review remain the caller's separate responsibilities.

## Retained native names and observed default flags

The [Sunspool three-role module](../../engines/unreal/DaedalusLink/Content/Python/daedalus_codex_sunspool_subset.py) uses a qualified static GLB subset and exact linear PBR evidence. A returned native name can differ from the declared source role beyond expected punctuation changes. Preserve the original import journal and actual code points; the cause may remain unknown. Reconcile an explicit source-role-to-existing-native-object mapping using the pinned payload, exact triangle count, absolute bounds, material identity and effective PBR properties. A name mismatch alone does not justify renaming or reimporting an object. Keep failed attempts and first-save evidence separate.

Default auto-glTF import settings are observed behavior, not a guaranteed option contract. In the observed three-mesh delivery, Nanite was initially enabled even though the meshes were small; it was explicitly disabled only on the three new owned meshes before their first saves. Lightmap-UV generation was false and simple-collision count zero. Recheck the actual flags and geometry after any admitted correction. These observations do not establish authored collision, navigation or runtime performance.

Check installed API availability before a recovery mutation. One attempted recovery stopped on an unsupported asset-editor getter before recording any mutation intent or save. A distinct recovery reconciled the existing objects through direct owned-mesh properties, with no asset-editor open/close and no import replay. Asset saves, placement/map saves and visual/playability acceptance remain separate receipts; the tiny subset does not establish acceptance of the full source scene.
