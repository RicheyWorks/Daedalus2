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

## Queue rejection and partial first saves

The small-static adapter records bounded rejection diagnostics while calling the original queue guard unchanged. It reports the current running request and reply-box identity, queued request descriptors and code hashes, unfinished asynchronous boxes, and remote-lock state. This is a non-atomic observation, not permission to ignore a queue or exclude a matching label. A tick budget does not register an asynchronous job box: the bridge does that only for explicitly asynchronous requests before execution.

During production steps, a complete snapshot containing only the exact owned generator and verified queued READ `ping` requests can yield at most three times so the existing bridge pump answers them. Each attempt reruns the original guard and absolute deadline; waiting does not reset the deadline. The adapter never consumes or completes queued requests. Unknown requests, mutators, incomplete snapshots, other running work, async boxes, a remote lock or persistent contention preserve the original refusal. Wait evidence is durable before yielding. Public preflight and readback remain immediate checks. The first subsequent three-asset production packet saved successfully without needing this conditional wait; the wait branch has source review, not direct runtime acceptance.

Read every item receipt after a failed packet. A late rejection can follow a true first save and leave the next imported object dirty before binding. Preserve that journal, inspect the exact retained objects, and use a separately journaled binding/first-save recovery for the known unfinished object. Read back the explicitly saved subset; prepare any still-absent remaining source as a distinct new packet against the extended baseline. Never infer zero effects from the failure tail or restart the original batch. The executed native-source revisions must remain available by their recorded hashes after source changes.

## Copperfall translated roots, raw emission and retained recovery

The exact Copperfall handoff is a closed three-role/292-triangle subset, not a generic full-scene importer. Run the [delivery adapter](../../tools/unreal/codex_copperfall_delivery.py) with an explicit current saved baseline. Preparation is file-only; runtime phases use the same existing bridge and ownership/resource guards:

```powershell
python tools/unreal/codex_copperfall_delivery.py prepare --baseline <ABSOLUTE_CURRENT_BASELINE>
python tools/unreal/codex_copperfall_delivery.py run
python tools/unreal/codex_copperfall_delivery.py readback
```

Any retained dispatch or uncertain result forbids another `run`. A null/truncated readback cannot mark success or release compute; retain its attempt and reconcile the saved package bytes before another read-only attempt. `finalize` requires the complete explicit native readback contract and performs no native import/save.

For the actual observed case only—six existing unsaved Copperfall outputs, exactly the three Nanite-on mismatches, no files on disk, the same original compute lease, unchanged saved scene/camera and no conflicting work—the [recovery recipe](../../tools/unreal/codex_copperfall_nanite_recovery.py) provides separate `observe` and `run` phases. It uses the installed `StaticMeshEditorSubsystem.set_nanite_settings(mesh, settings, True)` contract only on the three new unsaved meshes. It rechecks absolute source/render bounds, counts, raw PBR/emission, build scale, lightmap generation and metadata before six first saves. Recovery writes a new `RecoveryNaniteOffR1` journal; original failed evidence remains unchanged. Finish with `codex_copperfall_delivery.py readback --folder <ABSOLUTE_RECOVERY_FOLDER>`. Partial recovery is another reconciliation boundary, never an automatic replay.

The source roots have nonidentity translations, so identity-transform Sunspool evidence cannot establish their conversion. Actual Copperfall bounds matched authored world coordinates under XZY/metres-to-centimetres with build1 and future actor1. Preserve those absolute pivots; do not recenter, multiply by .01 or apply the node translation again. Symmetric bounds alone do not establish handedness or final appearance.

The Heartstone's named native `EmissiveFactor` RGB matched raw linear source `[0.06730775933426258, 0.24419823056754808, 0.21828978386953146]`; named `EmissiveStrength` matched the glTF default1. Parameter presence and finite values are required, so a missing getter returning black/zero cannot pass. Other roles retain zero emission. No palette/gamma replacement or shared-parent modification is allowed.

Count exact native package identities separately from source geometry and actor placement. The verified24-hour asset increase was158, not the cumulative141 selected ledger;64 already-saved palette packages lay outside that selected ledger. The namespace ended that window at205 and reached211 after this later Copperfall batch. BridgeCoupler imported into a new destination reuses a pre-window payload, and ten palette-variant parts preserve HeroR3 geometry: these are new native object paths, not claims of new geometry. Source exports, repeated saves/moves and queued candidates do not establish new saved native assets.

## Copperfall placement completed — 15 October, 20:16 UTC

The three admitted Copperfall roles subsequently completed placement, map save and independent readback. All 140 prior tracked actors remained unchanged; the new actors share translation `[-316100,299550,17348.324]` cm, zero rotation and scale 1, preserving their source layout and raw materials. Their component collision remains disabled for decorative use. This placement stage adds three actors and zero imported/new assets, packages or island versions. One map save returned true in 20.973694 seconds; totals are now 143 tracked actors, 211 protected packages and 184 preserved accepted C++ sources.

Preserve rejected native geometry evidence instead of weakening acceptance. The first candidate's rank-1 flower conflicts stopped preparation before spawning; subsequent read-only reconciliation retained both rank-1 and rank-2 conflicts and accepted only rank 3 with zero blockers. The [executed R2 ground proof](../../tools/unreal/codex_copperfall_ground_check.py) checks 25 complete flat cells/50 triangles and the full-height clearance volume against overlapping static components and actual instances. Its 0.02cm support tolerance and original guards remain intact. Source-boundary sensitivity is a possible interpretation, not proof of an axis-conversion defect.

That source file is a newline-normalized published copy of the executed R2 recipe: LF size 13,506 bytes, SHA256 `ab81cb1f8ab0fdfa57051cbb7b55414d1d8d18feef87886a9c6ddbd0b819599c`. The retained executed CRLF recipe remains 13,748 bytes, SHA256 `65dfa51b6cf477a8239376c4ca4eb64181cead65ec86dfbac8857aa7a194be68`; only newlines differ and BODY semantics are unchanged. It exports a pure `BODY` string and has no import-time native effects. The existing guarded `g.native` environment supplies its exact configuration and runtime names; it is not a portable standalone CLI. Its retained pre-placement baseline predates the three new obstacles, so the completed scene is not an instruction to repeat it. It creates only transient inspection meshes and cannot itself place actors or save packages/maps.

MAIN's actual player/context PNG review and preserved context viewport are recorded separately from geometric acceptance. No additional pose/material change or repeated map save was required. Full visual BAR and runtime collision/navigation/interaction acceptance remain unclaimed. The final local completion receipt at `native-ingestion/CopperfallPlinthHeartstoneSubsetR1/PlacementR2/ConstructionViewsR1/completion.json` is timestamped `2026-10-15T20:16:16.511291+00:00`. Its final baseline is 502,728 bytes, SHA256 `1555dff971c6b3e487253aa7fa202ea368b0a38d3ee83959b198bf69d1224a63`; map SHA256 is `72cb0c195975afa4b272417f67181f09774b95e7d5b061d7438ec2e70a85cd44` at 209,408,537 bytes. The later view stage saved no map and verified compute release. Earlier asset-only sections remain historical stages of the same retained delivery.
