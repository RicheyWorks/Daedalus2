# data/islands/disksaver: DiskSaver Island (disk-saver, Team Grok)
| File | What it is |
|---|---|
| ISLAND.md | Design: layout, storyline, mechanics, Keeper's notes, editor-turn runbook |
| mechanics.json / check_mechanics.py | Data-driven gameplay tables + validator |
| ds_items.py, ds_items2.py, ds_food_fix.py | Blender 4.3 headless generators (one joined mesh per asset) -> glb/ |
| batch1b.json, batch2.json, batch1c_food.json, manifest.json | Item lists (500 items) |
| ds_island_ue.py, run_island.ps1 | Round-1 placement (171 actors at cell 4000000,4000000) |
| ds_island_fix_ue.py, ds_island_fix_light_ue.py, run_island_fix*.ps1 | Materials, mesh swap and gameplay hooks (full, or RAM-light with no reimports) |
| ds_canopy_ue.py, run_canopy.py, ds_finish_ue.py, turn4*.ps1 | Batched, resumable reimport (8 per batch, RAM pause) + finish pass |
| ds_capture_ue.py, ds_capture_cleanup_ue.py, turn5.ps1 | Island-only temporary lighting + screenshot/SceneCapture, temps removed, not saved |
| ds_save_ue.py, ds_lab_ue.py, turn3.ps1 | Save-first, label probe, round-3 runner |
| ds_layout.png, layout.py | Top-down layout map from a stubbed placement run |
All Unreal scripts touch only /Game/DiskSaver and the Island_DiskSaver sublevel, never delete saved content and never start or stop Play.
