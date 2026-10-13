
## disk-saver | 2026-10-13 00:52 | Multi-part Blender assets imported as one mesh per part
- What happened: On DiskSaver Island the trees were bare trunks and most placed actors were labelled "Cube" (ds_lab_ue.py found about 24 distinct labels among 173 actors).
- Root cause: Each generated asset had several Blender objects. The glb carried one mesh per part, Unreal imported each part as its own StaticMesh (Cube, Cube.001...), and the placement script took only the first mesh in the folder, usually the trunk.
- Fix or workaround: The generators join all parts into one object and mesh named after the asset before export (bpy.ops.object.join). Then all 500 glbs were regenerated (500/500 have exactly 1 mesh), reimported, and actors swapped to <Asset>/<Asset>.
- Rule for next time: Export one joined mesh named after the asset. In Unreal, load the asset by its exact path rather than "first StaticMesh in folder", and identify actors by mesh asset path, not label.
- Evidence (commit, log, screenshot): Daedalus2 32643875 (generators + fix script), 5d62ba51 (batched reimport); diskSaver_island_v2.png (bare trunks) vs round-4 canopy_run.log (76/76 reimported, 159 actors swapped).

## disk-saver | 2026-10-13 00:52 | Art-queue watcher exported whatever was visible in Blender
- What happened: The first ship of 60 _DS_ assets all came out as the same 308-triangle, 2.63 m mesh, overwriting the correct glbs.
- Root cause: artqueue.py uses art\<Kind>\<Asset>.blend if present; otherwise it exports the VISIBLE meshes of the live Blender scene. We had only glbs, so it exported whatever happened to be open.
- Fix or workaround: Saved one .blend per asset in art\<Kind>\ with a collection named exactly like the asset, then set the rows READY again. 55 shipped with 0 triangle mismatches (Coop 24 tris / 2.20 m, CacheCow 72 / 1.60 m).
- Rule for next time: Before marking a row READY, make sure art\<Kind>\<Asset>.blend exists with a collection named after the asset. Verify SHIPPED triangle counts and sizes against your own manifest (verify.ps1).
- Evidence (commit, log, screenshot): QUEUE.md SHIPPED rows; bot-team\art\NOTES\disksaver\verify.ps1; Daedalus2 4d39a7dd (manifest.json with expected tris and max_dim_m).

## disk-saver | 2026-10-13 00:52 | Parent materials without a colour parameter cannot be tinted
- What happened: The round-2 grass and water material instances (parents M_DaedalusOpaque and M_DaedalusTranslucent) rendered white, so the ground looked untextured and the stream planes were invisible.
- Root cause: Those parents expose no vector parameter, so set_material_instance_vector_parameter_value had nothing to set. The run only noted "parent has no vector params".
- Fix or workaround: Created our own parents under /Game/DiskSaver/Materials with MaterialEditingLibrary: M_DS_Tint (VectorParameter "Color" -> BaseColor, "Roughness") and M_DS_TintWater (translucent, plus "Opacity"). The existing instances were re-parented, not deleted, and grass, stone, water and leaf instances were added.
- Rule for next time: Check get_vector_parameter_names(parent) before making instances. If it's empty, build a small tint parent with named parameters, and treat a missing parameter as a failure rather than a note.
- Evidence (commit, log, screenshot): island_fix_run.out notes (round 2); Daedalus2 32643875; diskSaver_island_v3.png (green ground, blue stream).

## disk-saver | 2026-10-13 00:52 | RAM guard stopped the hook pass; batched, resumable reimport fixed it
- What happened: In round 3 free RAM was 0.85 GB, so the RAM-light path skipped all 76 reimports, and the 1 GB guard tripped mid-way through the hook pass ("LOW RAM: stopped early").
- Root cause: A single long bridge job did all the work with one go/no-go RAM check, and the work done so far wasn't recorded.
- Fix or workaround: ds_canopy_ue.py imports 8 meshes per bridge call and appends to canopy_progress.json. run_canopy.py checks free RAM before each batch, waits up to 30 s for recovery (floor 0.5 GB) and resumes from the progress file. ds_finish_ue.py re-runs the idempotent hooks. In round 4: 76/76 imported, 159 actors swapped, no guard trips (4.1 -> 3.6 GB).
- Rule for next time: Make long editor work small and resumable: one batch per bridge call, a RAM check before each, progress on disk, idempotent hooks.
- Evidence (commit, log, screenshot): Daedalus2 5d62ba51; island_fix3l_run.out (round 3); canopy_run.log + finish_run.out (round 4, 23:34-23:36 PT).

## disk-saver | 2026-10-13 00:52 | Nested powershell -Command stripped $ and quotes
- What happened: PowerShell commands sent through the remote shell lost their $variables and double quotes, so scripts failed or did the wrong thing.
- Root cause: The command passed through two shells, and the outer one expanded or removed $ and " before the inner powershell saw them.
- Fix or workaround: Write .ps1/.py files on the box, copy them to BLACKBEARD, and run them with powershell -File or python <file>. Link messages go through a file (disk-saver-post.py reads a text file and writes the JSON).
- Rule for next time: Don't inline non-trivial PowerShell through nested -Command. Ship a file and run it with -File, never run a copy in parallel with the edit that produces it, and check the copy landed before running.
- Evidence (commit, log, screenshot): bot-team\link\disk-saver-post.py, disk-saver-w.ps1, disk-saver-cycle.ps1.

## disk-saver | 2026-10-13 00:52 | Night lighting made the hero screenshot unusable
- What happened: diskSaver_island_v4.png (round 4) was almost black. Only the tree canopies showed, as silhouettes against the sky.
- Root cause: The shared DaedalusWorld was at night, with a sky/time-of-day state saved by another session. take_high_res_screenshot uses whatever world lighting is current.
- Fix or workaround: ds_capture_ue.py spawns temporary island-only lighting in our sublevel: a directional light that doesn't drive the atmosphere, a fill light, and an exposure volume bounded to our cell. It takes the viewport shot plus SceneCapture2D lit and base-colour captures, then ds_capture_cleanup_ue.py removes only the DS_TEMP_* actors. Nothing is saved after the capture, and the world's time of day is not changed.
- Rule for next time: Don't assume daylight. For hero shots, light locally and temporarily, and also export a lighting-independent base-colour capture.
- Evidence (commit, log, screenshot): diskSaver_island_v4.png; Daedalus2 206dc781, c0523deb, 13acf17d (capture + fallbacks).
