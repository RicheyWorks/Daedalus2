# SPDX-License-Identifier: MIT
"""Team Grok / 2Hot2Trot: Ark Landing Dock on the edge of the Grok island (Daedalus lore: after the
asteroid, arks fly between islands saving life; this is where one lands).
Builds into OUR streaming sublevel only (/Game/Grok/Maps/ArkDock_2hot2trot) and saves only it.
Re-runnable: deletes its own tagged actors (GROK_ArkDock) first.
  - landing pad + pier running out past the island edge
  - docked ark from shipped art (/Game/Daedalus/Art/Veh/Veh_Ark parts), primitives fallback
  - crafting bench (#7, station 'workbench') + smelter (#8, station 'smelter'), wired to
    data/economy/{stations,recipes}.json: actors carry Station_/Recipe_ tags and a recipe sign
  - lighting: pad spot, pier lanterns, smelter glow
Run: python ue_send.py ark_dock_ue.py 600   [ARK_ECON=<dir with recipes.json>]"""
import json, math, os, unreal

SUB = globals().get("ARK_SUB") or "/Game/Grok/Maps/ArkDock_2hot2trot"
TAG = "GROK_ArkDock"
FOLDER = "Grok/ArkDock"
ART = "/Game/Daedalus/Art/%s/%s/%s/StaticMeshes/%s"
CUBE, CYL = "/Engine/BasicShapes/Cube.Cube", "/Engine/BasicShapes/Cylinder.Cylinder"
ECON_DIRS = [globals().get("ARK_ECON") or "", r"C:\Users\730ri\projects\Daedalus2\data\economy",
             os.path.join(os.path.dirname(os.path.abspath(globals().get("__file__", "."))), "..", "..", "..", "data", "economy")]
log = []
L = unreal.EditorLoadingAndSavingUtils
_pre = [p.get_name() for p in L.get_dirty_map_packages()] + [p.get_name() for p in L.get_dirty_content_packages()]

def art(kind, pack, mesh=None):
    return unreal.load_asset(ART % (kind, pack, pack, mesh or pack))

# ---- crafting data (codex economy v0) ----
def econ():
    for d in ECON_DIRS:
        try:
            st = json.load(open(os.path.join(d, "stations.json"), encoding="utf-8"))["stations"]
            rc = json.load(open(os.path.join(d, "recipes.json"), encoding="utf-8"))["recipes"]
            return d, {s["id"]: s for s in st}, rc
        except Exception:
            continue
    return None, {}, []
ECON_DIR, STATIONS, RECIPES = econ()
log.append("economy data: %s (%d stations, %d recipes)" % (ECON_DIR, len(STATIONS), len(RECIPES)))

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); ew = ues.get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

# ---- 1) sublevel (create once, reuse) ----
def find_lvl(w):
    return next((s for s in unreal.EditorLevelUtils.get_levels(w) if SUB.split("/")[-1] in s.get_path_name()), None)
lvl = find_lvl(ew)
if lvl is None:
    if unreal.EditorAssetLibrary.does_asset_exist(SUB):
        unreal.EditorLevelUtils.add_level_to_world(ew, SUB, unreal.LevelStreamingAlwaysLoaded)
    else:
        unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, SUB, False)
    ew = ues.get_editor_world(); lvl = find_lvl(ew); log.append("sublevel added")
unreal.EditorLevelUtils.make_level_current(lvl)
for a in eas.get_all_level_actors():
    if a.actor_has_tag(TAG) and not a.actor_has_tag("GROK_ArkIsle"): eas.destroy_actor(a)

# ---- 2) find the island edge (away from the Wild Biomes so we don't build on them) ----
ps = next(a for a in eas.get_all_level_actors() if a.get_class().get_name() == "PlayerStart").get_actor_location()
def ground(x, y):
    h = unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(x, y, ps.z + 30000), unreal.Vector(x, y, ps.z - 60000),
        unreal.TraceTypeQuery.ECC_VISIBILITY, False, [], unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple(); return t[4].z if t[0] else None
_at = globals().get("ARK_DOCK_AT")   # (x, y, z, yaw_deg, edge_cm): set by ark_isle_ue.py to dock on our own island
if _at:
    ps = unreal.Vector(_at[0], _at[1], _at[2]); ANG = math.radians(_at[3]); EDGE = _at[4]; crowd = 0
else:
    busy = [a.get_actor_location() for a in eas.get_all_level_actors()
            if a.actor_has_tag("PYTH_WildBiome") or a.actor_has_tag("PYTH_EcoPlant")]
    best = None
    for k in range(24):
        ang = 2 * math.pi * k / 24; dx, dy = math.cos(ang), math.sin(ang)
        r, last = 0.0, None
        while r < 300000:
            if ground(ps.x + dx * r, ps.y + dy * r) is None:
                if r > 0: break
            else: last = r
            r += 500.0
        if last is None or last < 4000: continue
        ex, ey = ps.x + dx * last, ps.y + dy * last
        crowd = sum(1 for v in busy if math.hypot(v.x - ex, v.y - ey) < 6000)
        score = -crowd * 100 + last / 1000.0   # prefer empty shore, then farther out
        if best is None or score > best[0]: best = (score, ang, last, crowd)
    _, ANG, EDGE, crowd = best
DX, DY = math.cos(ANG), math.sin(ANG); PX, PY = -DY, DX     # outward + perpendicular
YAW = math.degrees(ANG)
def at(f, s=0.0):   # f = metres outward from the edge (negative = inland), s = metres sideways
    return ps.x + DX * (EDGE + f * 100) + PX * s * 100, ps.y + DY * (EDGE + f * 100) + PY * s * 100
padx, pady = at(-14)
GZ = ground(padx, pady) or ps.z
log.append("edge %d m from PlayerStart at %d deg, %d biome actors nearby" % (EDGE / 100, YAW % 360, crowd))

def put(mesh, x, y, z, size=None, scale=None, yaw=0.0, label="", tags=(), collide=True):
    m = unreal.load_asset(mesh) if isinstance(mesh, str) else mesh
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator(roll=0, pitch=0, yaw=YAW + yaw))
    a.static_mesh_component.set_static_mesh(m)
    if size:   # size in cm (x, y, z) relative to mesh bounds
        e = m.get_bounds().box_extent
        a.set_actor_scale3d(unreal.Vector(size[0] / max(e.x * 2, 1), size[1] / max(e.y * 2, 1), size[2] / max(e.z * 2, 1)))
    elif scale: a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    if not collide: a.static_mesh_component.set_collision_profile_name("NoCollision")
    a.set_actor_label(label); a.set_folder_path(FOLDER); a.tags = [TAG] + list(tags)
    return a
def fit(m, h):   # uniform scale so mesh is h cm tall
    return h / max(m.get_bounds().box_extent.z * 2, 1)

# ---- 3) landing pad + pier ----
put(CYL, padx, pady, GZ + 25, size=(2400, 2400, 50), label="ArkDock_LandingPad", tags=["ArkDock_Pad"])
put(CYL, padx, pady, GZ + 52, size=(1600, 1600, 4), label="ArkDock_PadRing", collide=False)
PIER_LEN = 40   # metres: from pad edge across the island lip out over the void
for i in range(PIER_LEN // 2):
    x, y = at(-2 + i * 2)
    put(CUBE, x, y, GZ + 40, size=(180, 500, 30), label="ArkDock_Pier_%02d" % i, tags=["ArkDock_Pier"])
    if i % 3 == 0:
        for side in (-2.6, 2.6):
            sx, sy = at(-2 + i * 2, side)
            put(CYL, sx, sy, GZ - 200, size=(40, 40, 600), label="ArkDock_Post_%02d_%s" % (i, "L" if side < 0 else "R"))
            lan = art("Prop", "Prop_Lantern") or art("Tool", "Tool_Lantern")
            if lan: put(lan, sx, sy, GZ + 100, scale=fit(lan, 60), label="ArkDock_Lantern_%02d" % i, collide=False)
            pl = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(sx, sy, GZ + 160), unreal.Rotator())
            pl.light_component.set_intensity(3000); pl.light_component.set_light_color(unreal.LinearColor(1.0, 0.75, 0.45, 1))
            pl.light_component.set_attenuation_radius(900)
            pl.set_actor_label("ArkDock_PierLight_%02d" % i); pl.set_folder_path(FOLDER + "/Lights"); pl.tags = [TAG]

# ---- 4) docked ark at the pier head ----
ax, ay = at(PIER_LEN - 2 + 16)
parts = [art("Veh", "Veh_Ark", n) for n in ("Veh_Ark_Hull", "Veh_Ark_WingL", "Veh_Ark_WingR", "Veh_Ark_Claw")]
hull = parts[0]
if hull:
    e = hull.get_bounds().box_extent; u = 3000.0 / max(e.x * 2, e.y * 2, 1)   # ~30 m long hull
    for n, m in zip(("Hull", "WingL", "WingR", "Claw"), parts):
        if m: put(m, ax, ay, GZ + 150, scale=u, yaw=90, label="ArkDock_Ark_" + n, tags=["ArkDock_Ark", "DAEDALUS_Ark"])
    anc = art("Veh", "Veh_ArkPart_Anchor_Bone")
    if anc:
        bx, by = at(PIER_LEN - 3, 3.5); put(anc, bx, by, GZ + 60, scale=fit(anc, 250), label="ArkDock_Anchor", tags=["ArkDock_Ark"])
    log.append("ark from shipped art Veh_Ark (%d parts, scale %.2f)" % (sum(1 for p in parts if p), u))
else:
    put(CUBE, ax, ay, GZ + 300, size=(3000, 900, 600), label="ArkDock_Ark_Hull", tags=["ArkDock_Ark", "DAEDALUS_Ark"])
    for s in (-1, 1):
        wx, wy = at(PIER_LEN + 14, s * 9); put(CUBE, wx, wy, GZ + 450, size=(1200, 1000, 60), label="ArkDock_Ark_Wing")
    log.append("ark from primitives (Veh_Ark not found)")

# ---- 5) crafting bench (#7) + smelter (#8) wired to economy data ----
def station(sid, pack_opts, h, f, s, label):
    m = next((x for x in (art("Prop", p) for p in pack_opts) if x), None) or unreal.load_asset(CUBE)
    x, y = at(f, s)
    recs = [r for r in RECIPES if r.get("station") == sid]
    tags = ["DAEDALUS_Station", "Station_" + sid, "GameBasic_" + label.split("_")[0]] + ["Recipe_" + r["id"] for r in recs]
    if STATIONS.get(sid): tags.append("StationTier_%d" % STATIONS[sid].get("tier", 0))
    a = put(m, x, y, GZ + 50, scale=fit(m, h), yaw=180, label="ArkDock_Station_" + sid, tags=tags)
    sign = eas.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(x, y, GZ + 50 + h + 120), unreal.Rotator(roll=0, pitch=0, yaw=YAW + 180))
    lines = [sid.upper()] + ["%s: %s -> %s" % (r["id"], " + ".join("%d %s" % (i["n"], i["item"]) for i in r["in"]),
             " + ".join("%d %s" % (o["n"], o["item"]) for o in r["out"])) for r in recs] or [sid.upper(), "(no recipes in data/economy)"]
    sign.text_render.set_text("\n".join(lines)); sign.text_render.set_world_size(40)
    sign.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    sign.set_actor_label("ArkDock_Sign_" + sid); sign.set_folder_path(FOLDER); sign.tags = [TAG]
    return a, recs
wb, wr = station("workbench", ["Prop_Workbench", "Prop_CraftingTable"], 110, -20, -8, "07_CraftingBench")
sm, sr = station("smelter", ["Prop_Smelter_Lit", "Prop_Smelter", "Prop_Furnace"], 260, -20, 8, "08_Smelter")
for p, f, s in (("Prop_Crate", -17, -11), ("Prop_StorageCrate_Ore", -17, 11), ("Prop_Barrel", -23, 11), ("Prop_Anvil", -23, -11)):
    m = art("Prop", p)
    if m: x, y = at(f, s); put(m, x, y, GZ + 50, scale=fit(m, 90), label="ArkDock_" + p)
glow_x, glow_y = at(-18.5, 8)
gl = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(glow_x, glow_y, GZ + 180), unreal.Rotator())
gl.light_component.set_intensity(12000); gl.light_component.set_light_color(unreal.LinearColor(1.0, 0.45, 0.15, 1))
gl.light_component.set_attenuation_radius(1200); gl.set_actor_label("ArkDock_SmelterGlow"); gl.set_folder_path(FOLDER + "/Lights"); gl.tags = [TAG]

# ---- 6) pad lighting + label ----
sp = eas.spawn_actor_from_class(unreal.SpotLight, unreal.Vector(padx, pady, GZ + 2500), unreal.Rotator(roll=0, pitch=-90, yaw=0))
sp.light_component.set_intensity(80000); sp.light_component.set_light_color(unreal.LinearColor(0.7, 0.85, 1.0, 1))
sp.light_component.set_outer_cone_angle(30); sp.light_component.set_attenuation_radius(4000)
sp.set_actor_label("ArkDock_PadSpot"); sp.set_folder_path(FOLDER + "/Lights"); sp.tags = [TAG]
bx, by = at(-14, 0)
lab = eas.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(bx, by, GZ + 900), unreal.Rotator(roll=0, pitch=0, yaw=YAW + 180))
lab.text_render.set_text("2HOT2TROT ARK DOCK"); lab.text_render.set_world_size(180)
lab.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
lab.set_actor_label("ArkDock_Label"); lab.set_folder_path(FOLDER); lab.tags = [TAG]

# ---- 7) save only our sublevel (+ persistent map only if it was clean before us) ----
unreal.EditorLevelUtils.make_level_current(lvl); saved = les.save_current_level() if not globals().get("ARK_NO_SAVE") else "deferred"
persist_saved = False
if not _pre and not globals().get("ARK_NO_SAVE"): persist_saved = L.save_dirty_packages(True, False)
dirty = [p.get_name() for p in L.get_dirty_map_packages()] + [p.get_name() for p in L.get_dirty_content_packages()]
cx, cy = at(-45, -25)
ues.set_level_viewport_camera_info(unreal.Vector(cx, cy, GZ + 2200), unreal.Rotator(roll=0, pitch=-22, yaw=YAW + 30))
result = {"sublevel_saved": saved, "persistent_saved": persist_saved, "dirty_before": _pre, "dirty_after": dirty,
          "actors": sum(1 for a in eas.get_all_level_actors() if a.actor_has_tag(TAG)),
          "workbench_recipes": [r["id"] for r in wr], "smelter_recipes": [r["id"] for r in sr],
          "dock_world": [round(padx), round(pady), round(GZ)], "yaw": round(YAW), "log": log}
