# SPDX-License-Identifier: MIT
"""Ark Dock Isle (island:2hot2trot, Team Grok). Run ONLY on a granted Grok editor turn, never launches an editor.
  python ue_send.py ark_isle_ue.py 900 ARK_ORIGIN=x,y,z      (cm; the cell Buffffff/board assigns to 2hot2trot)
Builds into our own sublevel only and saves only it:
  - island base (240 m, double size), ocean ring + shoreline rocks, drinkable pond (DAEDALUS_Water/Drinkable)
  - 600+ items from shipped /Game/Daedalus/Art (ark_isle_layout.py), placed in batches of 50
  - 5 livestock pens with shipped Mob_ animals, troughs, gates
  - Ark Mortar herb-combo station (herb_combos.json) + the ark dock with workbench #7 and smelter #8 (ark_dock_ue.py)
Rerun-safe: removes its own GROK_ArkIsle/GROK_ArkDock actors first."""
import os, sys, json, math, importlib, unreal
D = globals().get("ARK_DIR") or r"C:\Users\730ri\projects\Daedalus2-ark-dock\engines\unreal\ark-dock"
if D not in sys.path: sys.path.insert(0, D)
import ark_isle_layout; importlib.reload(ark_isle_layout)
SUB = "/Game/Grok/Maps/ArkDock_2hot2trot"; TAG = "GROK_ArkIsle"; FOLDER = "Grok/ArkIsle"; MATS = "/Game/Grok/Materials"
o = globals().get("ARK_ORIGIN")
if not o: raise RuntimeError("ARK_ORIGIN=x,y,z (cm) required: build only inside the cell assigned to 2hot2trot")
OX, OY, OZ = [float(v) for v in str(o).split(",")]
R = float(globals().get("ARK_RADIUS_M", 120.0))
L = unreal.EditorLoadingAndSavingUtils; EA = unreal.EditorAssetLibrary
_pre = [p.get_name() for p in L.get_dirty_map_packages()] + [p.get_name() for p in L.get_dirty_content_packages()]
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); ew = ues.get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log = []
# sublevel
def find_lvl(w): return next((s for s in unreal.EditorLevelUtils.get_levels(w) if SUB.split("/")[-1] in s.get_path_name()), None)
lvl = find_lvl(ew)
if lvl is None:
    if EA.does_asset_exist(SUB): unreal.EditorLevelUtils.add_level_to_world(ew, SUB, unreal.LevelStreamingAlwaysLoaded)
    else: unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, SUB, False)
    ew = ues.get_editor_world(); lvl = find_lvl(ew); log.append("sublevel added")
unreal.EditorLevelUtils.make_level_current(lvl)
for a in eas.get_all_level_actors():
    if a.actor_has_tag(TAG) or a.actor_has_tag("GROK_ArkDock"): eas.destroy_actor(a)
# tinted materials (our folder only)
def mat(name, rgb):
    p = MATS + "/" + name
    if EA.does_asset_exist(p): return unreal.load_asset(p)
    mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(*rgb, 1))
    EA.save_loaded_asset(mi); return mi
M_GRASS, M_SAND, M_WATER, M_SEA = mat("MI_Ark_Grass", (.18, .42, .14)), mat("MI_Ark_Sand", (.76, .68, .48)), mat("MI_Ark_Pond", (.08, .35, .55)), mat("MI_Ark_Sea", (.03, .16, .32))
def prim(shape, x, y, z, sx, sy, sz, m, label, tags=(), collide=True):
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator())
    a.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/%s.%s" % (shape, shape)))
    a.set_actor_scale3d(unreal.Vector(sx / 100, sy / 100, sz / 100)); a.static_mesh_component.set_material(0, m)
    if not collide: a.static_mesh_component.set_collision_profile_name("NoCollision")
    a.set_actor_label(label); a.set_folder_path(FOLDER + "/Terrain"); a.tags = [TAG] + list(tags); return a
D_ = 2 * R * 100
prim("Cylinder", OX, OY, OZ - 1500, D_, D_, 3000, M_GRASS, "ArkIsle_Ground", ["DAEDALUS_Island", "Island_2hot2trot"])
prim("Cylinder", OX, OY, OZ - 1560, D_ + 1600, D_ + 1600, 3000, M_SAND, "ArkIsle_Beach", ["Shoreline"])
prim("Cylinder", OX, OY, OZ - 400, D_ + 30000, D_ + 30000, 40, M_SEA, "ArkIsle_Sea", ["DAEDALUS_Water", "Shoreline", "Saltwater"], collide=False)
lay, meta = ark_isle_layout.layout(R)
pc, pr = meta["pond"]["c"], meta["pond"]["r"]
prim("Cylinder", OX + pc[0] * 100, OY + pc[1] * 100, OZ + 3, pr * 200, pr * 200, 6, M_WATER, "ArkIsle_Pond", ["DAEDALUS_Water", "Drinkable", "Pond"], collide=False)
for i in range(6):   # stream from pond to the sea (west)
    prim("Cube", OX + (pc[0] - pr - 6 - i * 7) * 100, OY + math.sin(i) * 300, OZ + 3, 800, 300, 6, M_WATER, "ArkIsle_Stream_%d" % i, ["DAEDALUS_Water", "Drinkable", "Stream"], collide=False)
# meshes (multipart packs: spawn every StaticMesh in the pack at the same pivot)
cache = {}
def meshes(kind, pack):
    k = (kind, pack)
    if k not in cache:
        ms = [unreal.load_asset(p) for p in EA.list_assets("/Game/Daedalus/Art/%s/%s" % (kind, pack), True)]
        cache[k] = [m for m in ms if isinstance(m, unreal.StaticMesh)]
    return cache[k]
placed, missing, batch = 0, set(), 0
for i, p in enumerate(lay):
    ms = meshes(p["kind"], p["pack"])
    if not ms: missing.add(p["pack"]); continue
    tall = max(max(m.get_bounds().box_extent.z for m in ms) * 2, 1)
    zoff = min(m.get_bounds().origin.z - m.get_bounds().box_extent.z for m in ms)
    u = p["h"] * 100 / tall
    x, y = OX + p["x"] * 100, OY + p["y"] * 100
    for j, m in enumerate(ms):
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, OZ - zoff * u), unreal.Rotator(roll=0, pitch=0, yaw=p["yaw"]))
        a.static_mesh_component.set_static_mesh(m); a.set_actor_scale3d(unreal.Vector(u, u, u))
        if p["kind"] == "Prop" and p["zone"] not in ("camp",) and not p["zone"].startswith("pen"): a.static_mesh_component.set_collision_profile_name("NoCollision")
        a.set_actor_label("ArkIsle_%s_%03d%s" % (p["pack"], i, "" if j == 0 else "_%d" % j))
        a.set_folder_path("%s/%s" % (FOLDER, p["zone"])); a.tags = [TAG, "ArkIsle_Item", "Zone_" + p["zone"]] + p["tags"]
    placed += 1
    if placed % 50 == 0: batch += 1; unreal.log("[ark-isle] placed %d" % placed)
log.append("placed %d items in %d batches; missing packs %s" % (placed, batch + 1, sorted(missing)))
# Ark Mortar herb-combo station
combos = json.load(open(os.path.join(D, "herb_combos.json"), encoding="utf-8"))
mx, my = OX - 3000, OY - 2400
mm = meshes("Prop", "Prop_PrepTable") or meshes("Prop", "Prop_EnchantingTable")
for j, m in enumerate(mm):
    u = 110 / max(m.get_bounds().box_extent.z * 2, 1)
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(mx, my, OZ), unreal.Rotator())
    a.static_mesh_component.set_static_mesh(m); a.set_actor_scale3d(unreal.Vector(u, u, u))
    a.set_actor_label("ArkIsle_Station_ark_mortar" + ("" if j == 0 else "_%d" % j)); a.set_folder_path(FOLDER + "/Crafting")
    a.tags = [TAG, "DAEDALUS_Station", "Station_ark_mortar", "HerbCombo"] + ["Recipe_" + r["id"] for r in combos["recipes"]]
sg = eas.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(mx, my, OZ + 260), unreal.Rotator())
sg.text_render.set_text("ARK MORTAR\n" + "\n".join("%s = %s" % (" + ".join(i["item"] for i in r["in"]), r["id"]) for r in combos["recipes"]))
sg.text_render.set_world_size(40); sg.set_actor_label("ArkIsle_Sign_Mortar"); sg.set_folder_path(FOLDER + "/Crafting"); sg.tags = [TAG]
# sun-side fill light for the island
for k, (dx, dy) in enumerate(((0, 0), (-55, 0), (-10, 55))):
    pl = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(OX + dx * 100, OY + dy * 100, OZ + 1500), unreal.Rotator())
    pl.light_component.set_intensity(40000); pl.light_component.set_attenuation_radius(6000)
    pl.light_component.set_light_color(unreal.LinearColor(1, .9, .75, 1)); pl.set_actor_label("ArkIsle_Fill_%d" % k)
    pl.set_folder_path(FOLDER + "/Lights"); pl.tags = [TAG]
# the ark dock on our east (+X) shore
g = dict(globals()); g.update(ARK_DOCK_AT=(OX, OY, OZ, 0.0, R * 100 - 200), ARK_NO_SAVE=True, ARK_SUB=SUB)
g["__file__"] = os.path.join(D, "ark_dock_ue.py")
exec(open(g["__file__"], encoding="utf-8").read(), g)
dock = g.get("result")
# save only our sublevel + our materials
unreal.EditorLevelUtils.make_level_current(lvl); saved = les.save_current_level()
for p in [p.get_name() for p in L.get_dirty_content_packages()]:
    if p.startswith("/Game/Grok/"): EA.save_asset(p, False)
persist_saved = L.save_dirty_packages(True, False) if not _pre else False
dirty = [p.get_name() for p in L.get_dirty_map_packages()] + [p.get_name() for p in L.get_dirty_content_packages()]
ues.set_level_viewport_camera_info(unreal.Vector(OX - 9000, OY - 16000, OZ + 9000), unreal.Rotator(roll=0, pitch=-28, yaw=58))
result = {"items_placed": placed, "missing": sorted(missing), "sublevel_saved": saved, "persistent_saved": persist_saved,
          "dirty_before": _pre, "dirty_after": dirty, "dock": dock, "log": log}
