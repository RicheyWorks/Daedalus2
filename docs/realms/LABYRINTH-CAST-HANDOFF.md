# Labyrinth cast — batch 1

Owner: team-codex/Astra. Native import, animation setup and Play evidence: unreal-team/Claude. Scope confirmed on the team hub, messages 28609 and 28619. Other realms belong to blender-team.

This first batch contains **three of the proposed 32 roster entries**, not the complete cast. Names and jobs follow `REALM-CASTS.md`; gameplay and lore remain proposals until implemented or approved. In particular, the Heartstone explanation and the Apprentice knowing the impact's secret cause are not established canon.

## Delivered characters

| ID | Silhouette and equipment | Proposed usable role | Triangles |
|---|---|---|---:|
| Mob_Lab_Wayfinder | Hood, asymmetric shoulder cape, survey pack, compass, chalk | Hero presentation for maze exploration | 1,424 |
| Mob_Lab_ThreadSpinnerAri | Wide brim, apron, double spool backpack | Thread supplies and path-marking quests | 1,348 |
| Mob_Lab_LanternKeeper | Tall brass-tipped hat, chest plate, carried cage lantern | Light supplies and safe-route hints | 1,462 |

The visual direction is low-poly crafted figures in muted teal, terracotta, ivory and aged brass. These are distinct equipment silhouettes, not palette-only duplicates. Materials contain no external textures or borrowed character designs.

## Rig and import

All three share `LabyrinthHumanoidV1`: 14 bones with identical names and rest transforms. Root → pelvis → spine → head, plus paired thigh/calf/foot and arm/forearm chains. Meshes use deliberately rigid part weighting (one bone per vertex), giving a segmented puppet appearance. This is not a smooth organic deformation rig. No hand, facial, cloth, IK, attack or interaction animation is included yet.

Each GLB includes one skin and two clips: Idle (48-frame cycle) and Walk (24-frame cycle), authored at 24 fps. Walk is in place; movement speed/root motion must be handled by the Unreal host. Quaternions may change sign at the loop boundary: q and −q represent the same orientation. The validator accounts for that equivalence.

Authoring uses metres, feet at Z=0, forward −Y in Blender; GLB uses the standard Y-up conversion. Verify UE scale and facing after import. BBA 1 rows contain measured triangle counts and conservative origin-centred bounds in centimetres. `lod1 -` explicitly means no reduced mesh is delivered. The existing BBA static-mesh importer must not be assumed to apply skeletal LODs; Claude should handle skeletal import through the appropriate Unreal path.

## Reproduction and evidence

```text
blender --background --python tools/blender/labyrinth_cast.py -- OUTPUT
python tools/blender/validate_labyrinth_cast.py OUTPUT
```

Local delivery: `C:/Users/730ri/Documents/Codex/2026-10-13/labyrinth-cast/`.

Files: three GLBs, `labyrinth-cast-batch1.blend`, `manifest.json`, `labyrinth-cast.bba`, labeled `contact-sheet.png`, walk-pose preview and `validation.json`. The generator is committed so the package can be reproduced on another machine.

Validation checks the actual exported bytes: GLB headers/length, accessor bounds, finite positions, triangle indices/counts, normalized nonnegative skin weights, joint indices, matching shared rest skeletons, both non-static animation clips, increasing timestamps, normalized quaternions, loop continuity, manifest hashes and BBA counts. All three pass. Rendered review corrected apron/belt intersections before delivery.

The inspected shared `art/glb/Mob_*.glb` catalog (excluding LOD siblings) had no skins or animation clips. This finding does not rule out an unpublished source rig elsewhere; the team was asked for one. Existing static mobs were not represented as compatible rigs.

## Claude's acceptance

Import all three as skeletal assets, confirm one reusable skeleton, play both clips, verify scale/facing, inspect elbows/knees and carried lantern through a complete walk cycle, and place them together in a Labyrinth review scene. Bind actual movement and interaction separately. Record a short video plus exact source/art hashes; until then this is **validated Blender art, not proven Unreal gameplay**.

Next batches should add the remaining humanoid jobs before quadrupeds, insects, flying creatures and the Folding Maze boss. Their anatomical rigs should be compatible within families; a single humanoid skeleton should not be forced onto all species. Shops, quest rewards, path marking and lantern functionality remain separate server/native tasks.

## Lessons

Check exported skins and clips before claiming a reusable rig. Validate animation endpoints as orientations, not raw quaternion signs. Match BBA accounting to the actual mesh type; static LOD tooling is not skeletal LOD support. Keep batch counts and in-game proof explicit during handoff.
