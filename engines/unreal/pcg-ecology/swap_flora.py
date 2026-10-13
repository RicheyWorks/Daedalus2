# SPDX-License-Identifier: MIT
"""Swap the ecology stand-ins of one species (PYTH_SPECIES) for the Blender team's shipped flora meshes,
keeping each plant's ground point and target height. Art-queue meshes have their origin at the bottom centre
(BRIEF), stand-ins at their centre. Trees: smaller plants get the Young mesh (a size-structured stand).
Saves the map only. Run: python ue_send.py swap_flora.py 300 PYTH_SPECIES=Oak"""
import unreal
SP = globals().get("PYTH_SPECIES", "Oak")
ART = "/Game/Daedalus/Art/Prop/%s/%s/StaticMeshes/%s"
MAP = {"Oak": ["Prop_Tree_Oak_Mature", "Prop_Tree_Oak_Young"], "Pine": ["Prop_Tree_Pine_Mature", "Prop_Tree_Pine_Young"],
       "Willow": ["Prop_Tree_Willow_Mature", "Prop_Tree_Willow_Young"], "Sedge": ["Prop_Grass_Sedge"],
       "Grass": ["Prop_Grass_MeadowGrass", "Prop_Grass_TallGrass"], "Fern": ["Prop_Fern_Bracken", "Prop_Shrub_Fern"],
       "Bramble": ["Prop_Berry_Blackberry"]}
def load(n):
    m = unreal.load_asset(ART % (n, n, n))
    if not m:
        hits = unreal.EditorAssetLibrary.list_assets("/Game/Daedalus/Art/Prop/" + n, True)
        m = next((unreal.load_asset(h) for h in hits if h.split(".")[-1] == n), None)
    return m
meshes = [m for m in (load(n) for n in MAP[SP]) if m]
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
plants = [a for a in eas.get_all_level_actors() if a.actor_has_tag("PYTH_EcoPlant") and a.get_actor_label().startswith("Eco_%s_" % SP)]
done = 0
if meshes:
    hs = sorted(a.get_actor_scale3d().z for a in plants); cut = hs[len(hs) // 3] if hs else 0
    dims = [m.get_bounds().box_extent.z * 2 or 100.0 for m in meshes]
    for a in plants:
        smc = a.static_mesh_component
        if smc.static_mesh in meshes: continue
        sc = a.get_actor_scale3d(); loc = a.get_actor_location()
        ground = loc.z - sc.z * 50; target = sc.z * 100
        i = 1 if (len(meshes) > 1 and sc.z < cut) else 0
        smc.set_static_mesh(meshes[i])
        for k in range(smc.get_num_materials()): smc.set_material(k, None)   # drop the stand-in tint
        u = target / dims[i]
        a.set_actor_scale3d(unreal.Vector(u, u, u))
        a.set_actor_location(unreal.Vector(loc.x, loc.y, ground), False, False)
        smc.set_collision_profile_name("NoCollision")
        a.tags = ["PYTH_EcoPlant", "PYTH_Flora"]
        done += 1
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
result = {"species": SP, "meshes": [m.get_name() for m in meshes], "plants": len(plants), "swapped": done}
