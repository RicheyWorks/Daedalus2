# Interchange import harness (P1 item f, includes the BIP1 five-slot receiver)

This applies the Epic primary-source import findings (link 48194) and the lessons from the item e live run (PR197) to one harness. It also covers the BIP1 five-slot terrain receiver that source packet `519f28bb` (flagship_terrain_33) requires. Requested in buffffff 48347/48367/48520 (request `buf-ueb-p1-epic-scrapes-20261019`). The socket sidecar follows blender-team 48521.

| File | Role |
|---|---|
| `harness_core.py` | Engine-free plan, sidecar, receiver profile and verdict. Plain stdlib. |
| `test_harness_core.py` | 42 engine-free tests (`python -m unittest test_harness_core`) |
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
7. **Sockets.** Stock UE 5.8 glTF Interchange keeps `SOCKET_` empties as native sockets (48725; the item e "dropped" result was a reader false negative); the sidecar is a cross-check and carries socket rotation. Axes: UE = 100·(gX, gZ, gY) = 100·(Bx, −By, Bz), so blender-team fronts (Blender −Y) land on UE +Y; no export rotation, yaw −90 at placement (buffffff 48769). The harness reads `<Asset>.sockets.json` next to the glb: name, parent, `location_cm`, rotation (pitch/yaw/roll, or a dict), all in Unreal space with +X forward and +Z up. `location` (blender-team's key, with top-level `units: cm`) is accepted as `location_cm`; other units are refused. `add_sockets()` calls `mesh.modify()` first, then adds them after import. If the sidecar is missing but the glb has `SOCKET_` empties, you get a warning, and nothing is invented.
8. **UCX** stays as glTF children. It becomes convex collision, and the hull extent is read through `export_text()` because 5.8 hides VertexData from Python.
9. **Second save.** Material instances can be dirty again after the first save, so `save()` loops up to 3 passes and reports the count.

## Native status (first run 2026-10-19, UE 5.8, `/Game/Daedalus/Tests/InterchangeFixture20261019`)
- All stages ran live: `start` (override pipeline), `poll`, `add_sockets`, `set_nanite`, `facts`, `save`. Verdict ok on the B reimport, with same UObject, 2 slots in order, UCX convex 52x53x50 cm, socket Top at (0,0,50) cm, and a clean 1-pass save.
- UE 5.8 API facts found on that run and fixed here:
  - `override_pipelines` takes `SoftObjectPath`, not pipeline objects;
  - `StaticMesh.Sockets` is protected from Python, so use `find_socket`/`add_socket`/`get_sockets_by_tag`;
  - `generate_lightmap_u_vs` lives on `mesh_pipeline`, not `common_meshes_properties` (fixed);
  - `collision=false` must also turn off the automatic collision: `mesh_pipeline.collision` defaults True and `fallback_collision_type` defaults CONVEX18DOP (that made terrain_33's 24-vert hull). The harness sets collision False and fallback NONE, `evaluate()` asserts `no_simple_collision`, and `strip_simple_collision()` cleans existing assets;
  - a **reimport keeps the asset's Nanite setting** and ignores the override's `build_nanite`. `evaluate()` catches this (`nanite_as_planned=False`), and `set_nanite()` applies the plan.
- **Sockets:** stock 5.8 glTF Interchange DOES import `SOCKET_Top` as socket `Top`. The item e "dropped" result was a false negative: its reader swallowed the protected-property error. The sidecar is kept as a cross-check and is the **rotation carrier**: `add_sockets` keeps the native socket, asserts its position matches the sidecar within 0.5 cm, then sets `relative_rotation` from the sidecar (native empties come in as [0,180,-90], a glTF-to-UE basis artefact). Native and sidecar rotations are logged. Opt out per asset with `sidecar_rotation: false`.
- **8 triangles (item e):** settled. With Nanite on (fallback target Auto), LOD0 is 256 tris. With Nanite off, it's 264 tris, which matches the glTF. The Nanite fallback mesh was the cause; the source is fine.
- terrain_33 into its real root (item g) needs a checkpoint, a five-slot readback, and a save of only the 6 new packages. The fresh reopen happens in the batched restart.

## Open
- PCG note only, no code (48194): `GenerateLocal`/`GetTaskId` is pending work, not completion. Require the generation callback plus an output count, and keep streaming completion as a separate gate. There is no PCG user yet.