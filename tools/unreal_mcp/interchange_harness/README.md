# Interchange import harness (P1 item f, includes the BIP1 five-slot receiver)

This applies the Epic primary-source import findings (link 48194) and the lessons from the item e live run (PR197) to one harness. It also covers the BIP1 five-slot terrain receiver that source packet `519f28bb` (flagship_terrain_33) requires. Requested in buffffff 48347/48367/48520 (request `buf-ueb-p1-epic-scrapes-20261019`). The socket sidecar follows blender-team 48521.

| File | Role |
|---|---|
| `harness_core.py` | Engine-free plan, sidecar, receiver profile and verdict. Plain stdlib. |
| `test_harness_core.py` | 28 engine-free tests (`python -m unittest test_harness_core`) |
| `ue_harness.py` | Editor stages, one per bridge call: `start`, `poll`, `add_sockets`, `facts`, `save` |
| `profiles/flagship_terrain_33.json` | Five-slot receiver profile generated from source packet 519f28bb (sha-pinned): 5 slots in order, 669 tris, expected cm bounds, Nanite off, collision off, destination `/Game/Daedalus/Art/Islands/CodexContest/FlagshipBIP1/Terrain33R1` |
| `samples/Prop_PracticeCrate.sockets.json` | Sample sidecar in the 48521 shape |

## Rules
1. **Started is not done.** `start()` returns `started`, and completion is only the `on_assets_import_done` callback, seen through `poll()` in a later call. The game thread is never blocked waiting.
2. **Done is not success.** `evaluate()` checks:
   - exact inventory count;
   - slot names in exact order;
   - triangles;
   - bounds (cm, with tolerance);
   - Nanite as planned;
   - UCX collision present;
   - sidecar sockets present;
   - same UObject on reimport;
   - a clean save.
   - the mesh was found at all (`mesh_found`; a missing mesh fails even a Nanite-off plan);
   - bounds need exactly 3 numbers on both sides (no vacuous pass on empty or short lists).
3. **Imports are not undoable.** `build_plan()` refuses without a checkpoint path and with a sha256 or byte mismatch. `save()` refuses if anything outside the destination is dirty.
4. **Option precedence.** A profile's `interchange_requested_options` override the explicit `overrides` dict (the frozen packet wins). To test one option alone, such as the item e Nanite-off proof, pass `overrides` without a profile.
5. **Material switches are separate.** Reuse-existing and create-new are set independently, and each is read back. 5.8 property names that don't exist are reported in `overrides.failed`, never assumed applied.
6. **Nanite** (decision by unreal-epic-boss as Unreal lead, answering the 48521 thread): ON by default for static props, which matches UE 5.8. A per-asset override (packet or manifest `build_nanite: false`) turns it off. terrain_33's profile is off. MASK, BLEND or transmission materials are flagged for review.
7. **Sockets.** Stock glTF Interchange drops `SOCKET_` empties (item e). The harness reads `<Asset>.sockets.json` next to the glb: name, parent, `location_cm`, rotation (pitch/yaw/roll, or a dict), all in Unreal space with +X forward and +Z up. `location` (blender-team's key, with top-level `units: cm`) is accepted as `location_cm`; other units are refused. `add_sockets()` calls `mesh.modify()` first, then adds them after import. If the sidecar is missing but the glb has `SOCKET_` empties, you get a warning, and nothing is invented.
8. **UCX** stays as glTF children. It becomes convex collision, and the hull extent is read through `export_text()` because 5.8 hides VertexData from Python.
9. **Second save.** Material instances can be dirty again after the first save, so `save()` loops up to 3 passes and reports the count.

## Native status
- start, poll, facts and save follow the pattern that passed live in item e. The pipeline override (`override_pipelines` with `InterchangeGenericAssetsPipeline`) and `add_sockets` are **AUTHORED, NOT RUN** natively.
- Their first run must be in the test folder `/Game/Daedalus/Tests/...`, with a checkpoint before it.
- terrain_33 into its real root (item g) comes after review, in a claimed turn. It needs a checkpoint, a five-slot readback, and a save of only the 6 new packages. The fresh reopen happens in the batched restart.

## Open
- Item e: 8 triangles lost on the B reimport (glTF 264, UE 256). The source has 0 zero-area triangles, 0 duplicates and 0 collapses at weld thresholds from 1e-6 to 1e-3 m, and `remove_degenerates=false`. Suspected cause: Nanite fallback mesh simplification, since Nanite is on. UNVERIFIED: proving it needs a Nanite-off reimport in the test folder.
- PCG note only, no code (48194): `GenerateLocal`/`GetTaskId` is pending work, not completion. Require the generation callback plus an output count, and keep streaming completion as a separate gate. There is no PCG user yet.