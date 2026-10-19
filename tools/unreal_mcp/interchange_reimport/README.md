# Interchange reimport identity test (P1 item e)

Reusable check that a glTF asset imported with UE 5.8 Interchange can be reimported from the SAME source path with new bytes, and keeps its identity. Built for buffffff 48347/48367 (request `buf-ueb-p1-epic-scrapes-20261019`), applying the Epic primary-source findings in link 48194. The fixture is blender-team 48374 (`Prop_PracticeCrate` A/B, recipe Daedalus2 df2c93b4).

| File | What |
|---|---|
| `expectations.json` | Fixture A/B facts: bytes, sha256, tris, UCX, socket, materials, UE cm |
| `glb_intake.py` | Stdlib-only intake gate: `python glb_intake.py expectations.json A <A.glb>`, exit 0 only if every check passes |
| `test_glb_intake.py` | Offline tests over a synthetic GLB (`python -m unittest test_glb_intake`) |
| `ue_reimport_test.py` | In-editor stages, one per bridge call: `start_import`, `poll`, `facts`, `save_test_root`, `start_reimport`, `poll`, `compare_identity` |
| `observed-20261019.json` | First live run, values below |

## Rules (48194)
- `import_asset` returning True only means STARTED. Completion is the `on_assets_import_done` delegate, so `poll()` it from a later call and never block the game thread waiting.
- Done is not success: read the facts and compare object identity (`compare_identity`), not import order.
- Imports are not undoable: use a test-only content folder. `start_import` refuses a non-empty root, and `save_test_root` refuses if anything outside the root is dirty.
- Stock Interchange pipelines (no override), so the results describe the project default.

## First live run (2026-10-19 01:55-01:58 PT, PID 23632, test root `/Game/Daedalus/Tests/InterchangeFixture20261019`)

| Check | A import | B reimport (same source path) |
|---|---|---|
| Completion | started=true, done after 18.2 s, 3 objects | started=true, done after 5.5 s, 1 object |
| Identity | `.../Prop_PracticeCrate/StaticMeshes/Prop_PracticeCrate` | same path, **same UObject = true** |
| Tris LOD0 | 132 (= glTF) | 256 with Nanite on: the Nanite fallback mesh (target Auto). With Nanite off it's **264**, which matches the glTF. Settled in PR #203 (main a3a019b2) |
| Bounds cm | 52 x 52 x 50 | 52 x 53 x 50 (+1 cm on UE Y = Blender Y) |
| Materials | 2 MICs `Prop_PracticeCrate_M0/M1` (parent `/InterchangeAssets/gltf/MaterialInstances/MI_Default_Opaque_DS`), BaseColorFactor = linear wood/dark | same 2 refs, no new material assets (existing materials reused) |
| Collision | **UCX_ kept: 1 convex element**, 0 box/sphere/capsule | **1 convex, updated: hull extent 52 x 53 x 50 cm** (24 verts) |
| Socket | **socket `Top` imported** (corrected: the first run reported 0 because `StaticMesh.Sockets` is protected from Python and the reader swallowed the error) | `Top` kept |
| Nanite | enabled (stock default) | enabled |
| Save | 3 packages saved true (materials needed a second save to clear dirty) | 1 package saved true, 0 dirty |

Fresh-process reopen: PENDING. This happens in the batched rebuild/restart slot (48355). See `docs/production/epic/commandlet-flag-parsing-20261019.md` for why a commandlet can't run while 23632 is open.

Findings for the pipeline owners:
- glTF `UCX_<Mesh>` children DO become convex collision with stock Interchange, and the collision updates on reimport.
- glTF `SOCKET_<Name>` empties DO become StaticMesh sockets (`SOCKET_Top` becomes socket `Top`) with stock 5.8 Interchange. Correction to the first-run result, verified live in PR #203 (main a3a019b2). The `<Asset>.sockets.json` sidecar stays as a cross-check.
- The 8-tri gap on B is the Nanite fallback mesh: 256 tris with Nanite on, 264 with Nanite off. The source glb is fine.
- Nanite is on by default for glTF static meshes here. Packets that freeze `build_nanite=false` must override it.