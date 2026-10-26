# Hero visual polish pilot

An additive original knight visual candidate keeps the Portal fourteen-bone rest
rig and existing knight gameplay role. It does not remove or replace Claude's
assets. The 14,252-triangle mesh adds smooth facial features, layered bronze
armour, cape panels, satchel and distinct sword/shield equipment. Four prototype
clips use smooth interpolation. Deformation remains rigid part weighting;
organic skinning, foot contact, final combat timing and facial animation are pending.

Source: tools/blender/portal_hero_polish.py. Blender scene, GLB, review render and
validation are at Documents/Codex/2026-10-13/portal-hero-polish. Export occurs at
canonical origin/scale before camera presentation. It has role_count zero because
it refines an existing role; it is not another completed population identity.

GLB validation checks hash, indices, skin weights, fourteen joints, finite data
and Idle/Walk/Attack/Hurt motion/loops. Render review is not Unreal acceptance.
Import as a candidate alongside the existing hero, compare at normal game camera
distance, then tune scale/materials/animation before selecting a production visual.
LODs and actual in-game performance still need production work.

The additive portal_hero_lods.py now builds three compatible exports from the
owned scene: LOD0 14,252 triangles, LOD1 4,988, LOD2 1,706. Reduction runs before
the armature modifier and mesh topology is repaired then validated a second time
before export. All three exports pass rig, weights, hash and clip validation.
Output: Documents/Codex/2026-10-13/portal-hero-lods. BBA rows describe separate
export artifacts; they do not configure automatic native LOD switching. All rows
have role_count zero. Unreal import as one skeletal LOD group, screen-size
thresholds, deformation/appearance checks and performance measurement are pending.
