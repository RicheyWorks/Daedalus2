# SPDX-License-Identifier: MIT
"""Team Grok Wild Biomes: place 5 biomes into OUR streaming sublevel /Game/Pythagoras/Maps/WildBiomes_Pythagoras.
Saves the sublevel only; reports dirty packages of the persistent map (never saves others' work).
Run: python ue_send.py wild_biomes_ue.py 600"""
import sys, math, unreal
D = r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology"
if D not in sys.path: sys.path.insert(0, D)
import importlib, ecology_rules, island_flora, wild_biomes
for m in (ecology_rules, island_flora, wild_biomes): importlib.reload(m)
SUB = "/Game/Pythagoras/Maps/WildBiomes_Pythagoras"
ART = "/Game/Daedalus/Art/Prop/%s/%s/StaticMeshes/%s"
MESH = {"Oak": ["Prop_Tree_Oak_Mature", "Prop_Tree_Oak_Young"], "Pine": ["Prop_Tree_Pine_Mature", "Prop_Tree_Pine_Young"],
        "Willow": ["Prop_Tree_Willow_Mature", "Prop_Tree_Willow_Young"], "Sedge": ["Prop_Grass_Sedge"],
        "Grass": ["Prop_Grass_MeadowGrass", "Prop_Grass_TallGrass"], "Fern": ["Prop_Fern_Bracken", "Prop_Shrub_Fern"],
        "Bramble": ["Prop_Berry_Blackberry"]}
HEIGHT = {"Oak": 1400, "Pine": 1600, "Willow": 1000, "Bramble": 150, "Sedge": 60, "Grass": 70, "Fern": 80}  # cm
log = []
def load(n):
    m = unreal.load_asset(ART % (n, n, n))
    if not m:
        hits = unreal.EditorAssetLibrary.list_assets("/Game/Daedalus/Art/Prop/" + n, True)
        m = next((unreal.load_asset(h) for h in hits if h.split(".")[-1] == n), None)
    return m
meshes = {k: [m for m in (load(n) for n in v) if m] for k, v in MESH.items()}
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); ew = ues.get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
# 1) sublevel (create once, reuse)
lvl = None
for s in unreal.EditorLevelUtils.get_levels(ew):
    if SUB.split("/")[-1] in s.get_path_name(): lvl = s
if lvl is None:
    if unreal.EditorAssetLibrary.does_asset_exist(SUB):
        unreal.EditorLevelUtils.add_level_to_world(ew, SUB, unreal.LevelStreamingAlwaysLoaded)
    else:
        unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, SUB, False)
    ew = ues.get_editor_world()
    lvl = next(s for s in unreal.EditorLevelUtils.get_levels(ew) if SUB.split("/")[-1] in s.get_path_name())
    log.append("sublevel added")
unreal.EditorLevelUtils.make_level_current(lvl)
# clear our previous run (only our tagged actors inside our sublevel)
for a in eas.get_all_level_actors():
    if a.actor_has_tag("PYTH_WildBiome"): eas.destroy_actor(a)
# 2) find 5 ground patches around PlayerStart
ps = next(a for a in eas.get_all_level_actors() if a.get_class().get_name() == "PlayerStart").get_actor_location()
def ground(x, y):
    h = unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(x, y, ps.z + 30000), unreal.Vector(x, y, ps.z - 60000),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple(); return t[4].z if t[0] else None   # (blocking, ..., impact_point idx 4)
W = wild_biomes.W * 100
def cover(cx, cy):
    hs = [ground(cx + (i / 4 - .5) * W, cy + (j / 4 - .5) * W) for i in range(5) for j in range(5)]
    return sum(h is not None for h in hs) / 25.0
eco = [a.get_actor_location() for a in eas.get_all_level_actors() if a.actor_has_tag("PYTH_EcoPlant")]
ex = (sum(v.x for v in eco) / len(eco), sum(v.y for v in eco) / len(eco)) if eco else (ps.x, ps.y)
cands = []
for r in (4500, 6500, 9000, 12000, 16000):
    for k in range(16):
        a = 2 * math.pi * k / 16; cx, cy = ps.x + r * math.cos(a), ps.y + r * math.sin(a)
        if math.hypot(cx - ex[0], cy - ex[1]) < 3500: continue
        c = cover(cx, cy)
        if c >= 0.7: cands.append((c, -r, cx, cy))
cands.sort(reverse=True); spots = []
for c, nr, cx, cy in cands:
    if all(math.hypot(cx - x, cy - y) > W * 1.15 for x, y in spots): spots.append((cx, cy))
    if len(spots) == 5: break
log.append(f"spots {len(spots)} of {len(cands)} candidates")
# 3) place
counts, floating = {}, 0
bios = wild_biomes.all_biomes()
for (name, pts), (cx, cy) in zip(bios.items(), spots):
    n = 0
    for p in pts:
        ms = meshes.get(p["species"])
        if not ms: continue
        x, y = cx + (p["x"] / wild_biomes.W - .5) * W, cy + (p["y"] / wild_biomes.W - .5) * W
        z = ground(x, y)
        if z is None: floating += 1; continue
        tgt = HEIGHT[p["species"]] * p["scale"]
        m = ms[1] if len(ms) > 1 and p["scale"] < 0.9 else ms[0]
        dz = (m.get_bounds().box_extent.z * 2) or 100.0
        act = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z - 5), unreal.Rotator(roll=0, pitch=0, yaw=p["yaw"]))
        act.static_mesh_component.set_static_mesh(m); act.static_mesh_component.set_collision_profile_name("NoCollision")
        u = tgt / dz; act.set_actor_scale3d(unreal.Vector(u, u, u))
        act.set_actor_label(f"WB_{name}_{p['species']}_{n}"); act.set_folder_path(f"Pythagoras/WildBiomes/{name}")
        act.tags = ["PYTH_WildBiome", "PYTH_WB_" + name]; n += 1
    counts[name] = n
    lab = eas.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(cx, cy, (ground(cx, cy) or ps.z) + 1800), unreal.Rotator())
    lab.text_render.set_text(name); lab.text_render.set_world_size(250); lab.set_actor_label("WB_Label_" + name)
    lab.set_folder_path("Pythagoras/WildBiomes"); lab.tags = ["PYTH_WildBiome"]
# 4) save only our sublevel
unreal.EditorLevelUtils.make_level_current(lvl); les.save_current_level()
dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()] + \
        [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
if spots:
    cam = unreal.Vector(spots[0][0] - 6000, spots[0][1] - 6000, ground(*spots[0]) + 4500 if ground(*spots[0]) else ps.z + 4500)
    ues.set_level_viewport_camera_info(cam, unreal.Rotator(roll=0, pitch=-30, yaw=45))
result = {"counts": counts, "spots": [(round(x), round(y)) for x, y in spots], "skipped_no_ground": floating,
          "missing_meshes": [k for k, v in meshes.items() if not v], "dirty_after_save": dirty, "log": log}
