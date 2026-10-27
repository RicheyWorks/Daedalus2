# Ground and routes R10

Before:273visual Cave Floor instances repeated a raised block grid with deep
dark seams. They had NoCollision; a separate hidden104x105m slab provided the
actual physical floor. Both tile materials were already owned scene copies.

After: the273instances remain intact but hidden in editor/game rendering. A new
continuous NoCollision render surface uses the existing owned GroundSage material,
0.15cm above the unchanged20cm physical surface. The physical collider stays
hidden, BlockAll and unchanged. No original meshes/materials, material parameters,
instance transforms, bounds or ground physics were edited. No terrain build.

Three connected amber route groups now connect the existing arrival activity to
spawn, the chart landmarks and the Stillwater approach. Main route width3.2m,
arrival/garden branches2.4m. Thirteen new render actors total, including ground
and small turn junctions. Fifty-four old scattered route pavers are hidden rather
than deleted; their existing physics is retained. Existing R7activity/keeper,
seed/chart/save state, meadow/garden scenery and273floor instances remain.

Rollback: restore the exact recorded visual-floor/paver visibility and hidden
flags, remove only CommonsR10 actors, then save the owned map. Before-map backup
is retained locally. Do not reveal the physical collider as a visual workaround.

The first callback saved the map, then its final bridge pending check failed:
an endpoint variable named b shadowed the bridge module. This was not an engine
crash or rollback. The retained saved phase,13new actors, clean packages and
unchanged collider were read back in the capture closeout; no edits were replayed.
Task source now uses descriptive endpoint names. Full initial reply retained.

Matched before/after player-height and overview editor views accompany build.json.
The visible tile grid is gone and routes continuous. Flat/plain ground and dark
perimeter remain visual gaps. No Play, collision grid, reload or qualification
loop was run; benchmark quality and gameplay regression acceptance are unclaimed.
Next supplied production batch: one Bird Feeder native import for a modest
garden-care station. Additional barrel/compost variants await the revised source
manifest. Same category/name is not proof of identical design; use unique targets
without overwriting existing assets. No bird AI/crafting/economy systems.
