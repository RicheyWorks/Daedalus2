# Ruined Sky Harbor salvage modules

Seven separate reusable parts complement Sol's existing Dock/Beacon/Boathouse kit (`da716327`). They do not replace those assets or any original islands. Actual exports use the existing voxel mesher, palette-slot mapping, GLB export/witness and FBX conventions.

| Part | Local pivot / connection |
| --- | --- |
| BridgeCoupler | Near beam end; near/far beam sockets, 4 m span |
| SailPanel | Mast-seat corner; 3 m wide stepped panel, 4 m high |
| WagonWheel | Axle centre, rotation around local Y |
| TurbineRotor | Shaft centre, rotation around local Y; connected hub/blades |
| CrystalBattery | Base centre; battery seat and power port |
| GearboxHousing | Bottom centre; two opposed shaft ports |
| DriveShaft | Shaft centre; opposed endpoints, local Y axis |

`CopperPatina`, `DawnCrimson` and `StormAmethyst` provide coordinated color variants. The 21 seeds are `85000..85006`, `85100..85106` and `85200..85206`. Each receipt records quarter-metre grid geometry, source/config/voxel hashes, exact GLB/FBX hashes, connection positions/directions/types and proposed moving-part pivots. Native actor scale remains 1. These are static source assets; authored connection metadata does not implement runtime snapping, physics, crafting, persistence or quests.

Proposed story loop from user hub30513: salvage parts → restore bridges/lighthouse power → assemble a vehicle → reach another island. Nothing here claims that loop is implemented.

```powershell
python tools/blender/codex_skyharbor_modules.py --plan-only
# Claim/release Blender through the existing hub; use an isolated factory scene.
& 'C:/Program Files/Blender Foundation/Blender 4.3/blender.exe' --background --factory-startup --python-exit-code 1 --python tools/blender/codex_skyharbor_modules.py --
```

All 21 corrected export receipts completed on BLACKBEARD with Blender 4.3.1. `m<seed>` directories keep receipt paths short; binary exports remain local intermediates. The batch JSON contains the exact measured stage durations. Sum of receipt stages per seven-part variant, seconds; no performance comparison or native-import/save timing is implied:

| Variant | Generation | Mesh | GLB export + witness | FBX export |
| --- | ---: | ---: | ---: | ---: |
| CopperPatina | 0.011355 | 0.029775 | 1.001281 | 0.122525 |
| DawnCrimson | 0.010980 | 0.023458 | 0.119641 | 0.054135 |
| StormAmethyst | 0.011625 | 0.020430 | 0.102156 | 0.040411 |

Actual exported GLBs were re-imported into an isolated Blender scene and visually reviewed in `../QA/skyharbor-modules.png`. The first narrow rotor blades contained floating sections; wider blades/hub and a face-connectivity check corrected the geometry before this batch. Native material/collision, assembly, motion and final quality acceptance remain pending the owned Unreal turn.

Two production lessons: repeated long names exceeded the bundled Windows Python receipt path limit, so use short stable directory IDs rather than change machine settings; Blender returned exit 0 after a script exception, so use `--python-exit-code 1` and verify complete receipt stages/hashes before counting output.
