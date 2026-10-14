# Team Claude hand-off — 2026-10-14 (contest day), written 11:55 PT during Codex's editor slot

## State you inherit
- DaedalusWorld.umap saved 11:22 with **129 Team Claude islands** (deeds 240–368, actors `ClaudeIsland_<seed>_{body,clouds}`
  in folder Claude/Islands, tags District+ClaudeIsland), assets under `/Game/Daedalus/Art/Islands/ClaudeIslands/Island_C<seed>/`,
  shared material `M_VoxelVertexColour` (Codex binds it too — do not rename/reparent).
- FBX for seeds 369–699 are on disk (`engines/unreal/art/claude-islands/Island_C<seed>.fbx`, v4 generator, UCX boxes) and
  **not yet placed**. `tools/unreal_play/claude_islands.py 369 700 6` places them in the editor (background job via
  `engines\unreal\pc-job.ps1`), or `claude_islands_cmdlet.py` does it headless while the editor is closed.
- Editor baseline with the world open: 12–14 GB working set, RAM 85–96 %, commit 94–99 % (32 GB RAM, 22 GB auto pagefile).
  Every ~18–24 islands the runner saves + recycles the editor (4 min). Two GPU-driver crashes earlier today were commit
  exhaustion during multi-package saves; the runner saves one package at a time.

## How the pipeline works (all on main)
1. `tools/blender/voxel_island.py` — `plan(seed)` is pure Python (unit-testable): footprint harmonics (every 4th seed two-
   lobed), sand rim, grass/dirt/rock strata, hill + cottage + dirt path, pond + waterfall, 6 biomes by `seed % 6`
   (meadow/autumn/snow/cherry/volcanic/tropical) with biome trees (round/pine/palm/dead + blossom), lanterns, fenced
   garden, mushrooms, pier + sailboat, crystals, clouds. `greedy_quads` merges faces (40k → 11k); colour noise is in 4-voxel
   patches so it merges. `build()` exports FBX: body + clouds + `UCX_<body>_NN` boxes (one per walk-surface rectangle).
2. `tools/blender/export_islands.py` — headless: `blender -b --factory-startup --python-exit-code 1 --python … -- 500 700 [force]`,
   ~0.7 s per island, no GUI lock.
3. `engines/unreal/DaedalusLink/Content/Python/daedalus_claude_islands.py` — `import_island` (FbxImportUI: Nanite off, no lightmap
   UVs, no auto collision, vertex colours REPLACE), `clear_cell` (only the deed's own district actors), `place` (scale 0.01,
   1 voxel = 1 m, pivot = top centre on the deed's `top_cm`), `place_batch(seeds, realm)` (seed = deed number → idempotent),
   `count()`, `save_assets()`.
4. `tools/unreal_play/claude_islands.py` — background runner with recycle gate; `reimport` mode re-reads FBX for placed seeds.

## What I learned today (short; details in docs/AUTOMATION-LESSONS.md 10:05, 10:50, 11:45 entries)
- Unreal: Interchange builds **Nanite by default** on import (10–19 s + ~250 MB per island) — turn it off; FBX vertex colours
  are read as sRGB (encode the palette); the FBX importer nests `destination_name`; take asset paths from
  `task.imported_object_paths`; Rotator is (roll, pitch, yaw); `EditorLevelUtils.get_levels` shows 215 levels loaded in-editor.
- Memory: the editor's **baseline** (world + 214 sublevels) is the ceiling, not the imports. The fixes, ranked
  (docs/production/UNREAL-RESEARCH-2026-10-14.md): World Partition conversion → remove sublevels at session start →
  headless commandlet batches at turn boundaries → Interchange pipeline with `import_offset_uniform_scale`.
- Harness: a bridge call must fit 60 s → chunk by 3–6; long work goes through pc-job.ps1; gate on vitals but sample after the
  editor settles (otherwise a recycle loop); killing my own job is fine, never his apps.
- Connector (Epic MCP): server needs `ModelContextProtocol.StartServer` after every editor launch (Auto Start Server preference
  exists — Richey's setting), `doctor.py --fix` silences the popups; Tool Search mode hides toolsets, and we can ship our own
  `ToolsetDefinition` so the official connector runs the island pipeline directly.
- Blender for quality: generator-first (seed → plan → mesh) is what scales; biome palettes + landmark props read from the air;
  greedy meshing and patch noise keep the look while cutting faces 4×; per-rectangle UCX boxes give walkable collision.
- Sharing: headless Blender means we never need the GUI lock; Unreal is the shared scarce resource — hand off with a saved map
  and an explicit "UNREAL RELEASED"; nobody clears the other team's actors.

## What to discuss / decide (Richey)
1. World Partition conversion of DaedalusWorld (one-way; test with `-ConversionSuffix -ReportOnly`). Biggest lever.
2. Editor Preferences: Model Context Protocol → Auto Start Server; Python → Remote Execution (both his settings).
3. Pagefile / ChatGPT (4.7 GB, 21 processes) / Edge — his call; each GB is ~4 more islands per editor session.
4. Contest scoring: count = `daedalus_claude_islands.count()`; quality = screenshots from the air (set camera, viewport_screenshot).
