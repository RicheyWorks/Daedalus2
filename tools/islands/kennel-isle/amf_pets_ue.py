# Team Grok / Wild Biomes - art-master-flex (AMF): Cane Corso companion + wild pets.
# Idempotent: deletes every actor tagged AMF_Pets in OUR sublevel, then re-places deterministically (seed 1789).
# Works only in our own streaming sublevel /Game/AMF/Maps/WildBiomes_AMF_Pets inside /Game/Daedalus/DaedalusWorld.
# Editor turn:  python ue_send.py amf_pets_ue.py 600      (Claude bridge, editor already open)
# Headless:     UnrealEditor-Cmd.exe C:\Unreal\DaedalusRealm\DaedalusRealm.uproject -run=pythonscript
#               -script="C:\Users\730ri\projects\bot-team\art\NOTES\amf\amf_pets_ue.py" -unattended -nullrhi -nosplash
import math, random, json, unreal
MAP = "/Game/Daedalus/DaedalusWorld"
SUB = "/Game/AMF/Maps/WildBiomes_AMF_Pets"
MOB = "/Game/Daedalus/Art/Mob/"
TAG = "AMF_Pets"
SEED = 1789
# biome -> fauna (only Mob_* folders that exist; missing ones are skipped)
FAUNA = {
    "YoungMeadow":     ["Mob_Hare", "Mob_Rabbit", "Mob_Butterfly", "Mob_Bee", "Mob_Pheasant", "Mob_Mouse", "Mob_Grasshopper", "Mob_PygmyGoat", "Mob_Capybara"],
    "BrambleScrub":    ["Mob_Hedgehog", "Mob_Fox", "Mob_Robin", "Mob_Boar_Wild", "Mob_Ladybird"],
    "PineStand":       ["Mob_Squirrel", "Mob_Lynx", "Mob_Wolf", "Mob_Owl", "Mob_Marmot", "Mob_RedPanda"],
    "OldGrowthOak":    ["Mob_Deer", "Mob_Deer_Red", "Mob_Badger", "Mob_Moth_Luna", "Mob_Firefly"],
    "WillowRiverbank": ["Mob_Frog", "Mob_Heron", "Mob_Duck", "Mob_Dragonfly", "Mob_Newt", "Mob_MossTurtle", "Mob_Capybara"],
}
WINGED = {m: True for m in ("Mob_Butterfly","Mob_Bee","Mob_Pheasant","Mob_Robin","Mob_Owl","Mob_Moth_Luna","Mob_Firefly","Mob_Heron","Mob_Duck","Mob_Dragonfly","Mob_Ladybird","Mob_Grasshopper")}
ISLAND = (4000000.0, 2000000.0, 1950.0)   # Kennel Isle origin; top of KennelIsle_Ground (z 2000-100+50)
PER_BIOME = 6            # 5 biomes x 6 = 30 animals (+ Corso)
log, placed = [], []
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ew = ues.get_editor_world()
if ew is None or "DaedalusWorld" not in ew.get_path_name():          # headless commandlet path
    unreal.EditorLoadingAndSavingUtils.load_map(MAP); ew = ues.get_editor_world(); log.append("loaded map")

def parts(mob, root=None):
    """Static meshes of a Mob_*: single mesh, or Body/Head/Leg* parts (same pivot, attached to Body)."""
    # v3 fix: only meshes inside THIS asset's own folder and named <asset> or <asset>_<Part>.
    # The old prefix match also pulled stray WingL/WingR meshes from neighbouring folders, which then
    # floated off the pup and camp props. Parts are attached with the root's pivot (see spawn()).
    ms, base = [], (root or MOB) + mob + "/"
    if not unreal.EditorAssetLibrary.does_directory_exist(base.rstrip("/")): return ms
    for p in unreal.EditorAssetLibrary.list_assets(base, True, False):
        if "/StaticMeshes/" not in p or not p.startswith(base): continue
        nm = p.split("/")[-1].split(".")[0]
        if nm != mob and not nm.startswith(mob + "_"): continue
        if "Wing" in nm and not WINGED.get(mob): continue      # no wings on dogs/props
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh): ms.append(a)
    ms.sort(key=lambda m: (0 if m.get_name() in (mob, mob + "_Body") else 1, m.get_name()))
    return ms

# 1) our sublevel (create once, reuse)
short = SUB.split("/")[-1]
lvl = next((l for l in unreal.EditorLevelUtils.get_levels(ew) if short in l.get_path_name()), None)
if lvl is None:
    if unreal.EditorAssetLibrary.does_asset_exist(SUB):
        unreal.EditorLevelUtils.add_level_to_world(ew, SUB, unreal.LevelStreamingAlwaysLoaded)
    else:
        unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, SUB, False)
    ew = ues.get_editor_world()
    lvl = next(l for l in unreal.EditorLevelUtils.get_levels(ew) if short in l.get_path_name())
    log.append("sublevel added")
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).set_current_level_by_name(lvl.get_outer().get_name())
for a in eas.get_all_level_actors():
    if a.actor_has_tag(TAG): eas.destroy_actor(a)

allA = eas.get_all_level_actors()
ps = next((a for a in allA if a.get_class().get_name() == "PlayerStart"), None)
P = ps.get_actor_location() if ps else unreal.Vector(*ISLAND)
def ground(x, y):
    h = unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(x, y, P.z + 30000), unreal.Vector(x, y, P.z - 60000),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    if h is None: return None
    t = h.to_tuple()
    if t[0]: return t[4].z
    if abs(x - ISLAND[0]) < 2900 and abs(y - ISLAND[1]) < 2900: return ISLAND[2]   # Kennel Isle ground cube
    return None

# 2) biome centres: Pythagoras' WB_Label_<biome> if present, else a ring around PlayerStart with ground
centres = {}
for a in allA:
    n = a.get_actor_label()
    if n.startswith("WB_Label_") and n[9:] in FAUNA:
        v = a.get_actor_location(); centres[n[9:]] = (v.x, v.y)
rng = random.Random(SEED)
k = 0
for b in FAUNA:
    if b in centres: continue
    for r in (3000, 4500, 6500, 9000):
        ang = 2 * math.pi * (k + 0.5) / len(FAUNA); x, y = P.x + r * math.cos(ang), P.y + r * math.sin(ang)
        if ground(x, y) is not None: centres[b] = (x, y); break
    k += 1
# 2b) v3 fallback: no labels / no ground ring -> put the missing biomes on Kennel Isle's own meadow
MEADOW = {"YoungMeadow": (-300, -900), "BrambleScrub": (-1100, 200), "PineStand": (900, -1900),
          "OldGrowthOak": (-300, 2300), "WillowRiverbank": (-1300, -1100)}   # offsets from ISLAND, clear of the stream/pen
fb = [b for b in FAUNA if b not in centres]
for b in fb: centres[b] = (ISLAND[0] + MEADOW[b][0], ISLAND[1] + MEADOW[b][1])
if fb: log.append("fallback KennelIsle meadow for " + ",".join(fb))
log.append("centres " + ",".join(f"{b}:{'label' if any(l.get_actor_label()=='WB_Label_'+b for l in allA) else 'ring'}" for b in centres))

def spawn(mob, x, y, yaw, label, folder, extra_tags, root=None):
    ms = parts(mob, root)
    if not ms: return None
    z = ground(x, y)
    if z is None: return None
    root = None
    lo = min(m.get_bounds().origin.z - m.get_bounds().box_extent.z for m in ms)
    z = z - lo                                    # sit the whole assembly on the ground, parts share one pivot
    for i, m in enumerate(ms):
        act = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator(roll=0, pitch=0, yaw=yaw))
        act.static_mesh_component.set_static_mesh(m)
        act.static_mesh_component.set_collision_profile_name("NoCollision")
        act.set_actor_label(label if i == 0 else f"{label}_{m.get_name().split('_')[-1]}")
        act.set_folder_path(folder); act.tags = [TAG] + extra_tags
        if root is None: root = act
        else: act.attach_to_actor(root, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    return root

# 3) Corso: 2.5 m right-behind the hero spawn, facing the same way
f = ps.get_actor_rotation() if ps else unreal.Rotator(0, 0, 0); yr = math.radians(f.yaw)
cx, cy = P.x - 250 * math.cos(yr) + 200 * math.cos(yr + math.pi / 2), P.y - 250 * math.sin(yr) + 200 * math.sin(yr + math.pi / 2)
c = spawn("Mob_CaneCorso", cx, cy, f.yaw, "AMF_Companion_CaneCorso", "AMF/Companion", ["AMF_Companion"])
placed.append({"mob": "Mob_CaneCorso", "ok": bool(c)})

# 3b) v2: pet camp next to the Corso (pup, bed, feeder, water bowl, kennel); skipped quietly until imported
PROP = MOB.replace("/Mob/", "/Prop/")
for dx, dy, asset, root in [(-150, 120, "Mob_CorsoPup", None), (0, 260, "Prop_PetBed_Wicker", PROP), (160, 240, "Prop_PetFeeder", PROP),
                            (220, 120, "Prop_PetWaterBowl", PROP), (-60, 450, "Prop_Kennel", PROP)]:
    x = cx + dx * math.cos(yr) - dy * math.sin(yr); y = cy + dx * math.sin(yr) + dy * math.cos(yr)
    a = spawn(asset, x, y, f.yaw + 180, "AMF_Camp_" + asset.split("_", 1)[1], "AMF/Companion/Camp", ["AMF_Companion", "AMF_Camp"], root)
    placed.append({"mob": asset, "ok": bool(a), "optional": True})

# 4) wild animals, seeded per biome
for b, mobs in FAUNA.items():
    if b not in centres: log.append("no ground for " + b); continue
    bx, by = centres[b]; br = random.Random(f"{SEED}-{b}")
    for i in range(PER_BIOME):
        mob = mobs[i % len(mobs)]
        a, r = br.uniform(0, 2 * math.pi), (br.uniform(150, 500) if b in fb else br.uniform(400, 2200))
        act = spawn(mob, bx + r * math.cos(a), by + r * math.sin(a), br.uniform(0, 360), f"AMF_{b}_{mob[4:]}_{i}", f"AMF/Wild/{b}", ["AMF_Wild", "AMF_B_" + b])
        placed.append({"mob": mob, "biome": b, "ok": bool(act)})

# 5) idle/wander: no wander BP / BT exists in the project yet -> static placement; tags let a later BP pick them up
log.append("behaviour: static (no wander Blueprint/BehaviorTree found in /Game)")
# 6) save only our sublevel
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).set_current_level_by_name(lvl.get_outer().get_name()); les.save_current_level()
ok = [p for p in placed if p["ok"]]
res = {"sublevel": SUB, "placed": len(ok), "failed": [p["mob"] for p in placed if not p["ok"] and not p.get("optional")], "skipped_optional": [p["mob"] for p in placed if not p["ok"] and p.get("optional")],
       "mobs": sorted({p["mob"] for p in ok}), "log": log}
unreal.log("AMF_PETS_RESULT " + json.dumps(res))
open(r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_run.json", "w").write(json.dumps(res, indent=1))

