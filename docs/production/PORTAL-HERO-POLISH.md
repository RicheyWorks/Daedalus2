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
