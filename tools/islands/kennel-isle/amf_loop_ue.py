# Kennel Isle working loop (art-master-flex, Team Grok). Run AFTER amf_island_ue.py, editor turn only:
#   python ue_send.py C:\Users\730ri\projects\bot-team\art\NOTES\amf\amf_loop_ue.py 600
# Adds interact volumes + gameplay tags + readable TextRender signs for the water / food / herb-brew chain,
# into OUR sublevel /Game/AMF/Maps/Island_AMF only. Idempotent: wipes actors tagged AMF_Loop first.
# Tags game code reads: Water_Drinkable, Food_Source, Herb_Source, Brew_Trough, AMF_Chain_<n>, AMF_Link_<from>_<to>.
import unreal, json
SUB = "/Game/AMF/Maps/Island_AMF"; TAG = "AMF_Loop"
O = unreal.Vector(4000000, 2000000, 2000)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eal = unreal.EditorAssetLibrary
les.set_current_level_by_name(SUB.split("/")[-1])
for a in eas.get_all_level_actors():
    if TAG in [str(t) for t in a.tags]: eas.destroy_actor(a)
byl = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
out = {"volumes": 0, "signs": 0, "tagged": 0, "props": 0, "missing": []}

def tag_existing(label, tags):
    a = byl.get(label)
    if a is None: out["missing"].append(label); return None
    a.tags = list(dict.fromkeys([str(t) for t in a.tags] + tags)); out["tagged"] += 1; return a

def vol(label, x, y, r, tags):     # interact sphere (overlap only) the player/pets walk into
    a = eas.spawn_actor_from_class(unreal.TriggerSphere, O + unreal.Vector(x, y, 60))
    a.set_actor_scale3d(unreal.Vector(r / 32.0, r / 32.0, r / 32.0))   # TriggerSphere radius 32 at scale 1
    a.set_actor_label(label); a.set_folder_path("AMF/KennelIsle/Loop"); a.tags = [TAG] + tags
    out["volumes"] += 1; return a

def sign(text, x, y, z=260, yaw=0, size=46, col=(255, 240, 180)):
    a = eas.spawn_actor_from_class(unreal.TextRenderActor, O + unreal.Vector(x, y, z), unreal.Rotator(0, 0, yaw))
    c = a.text_render
    c.set_text(text); c.set_world_size(size)
    c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    c.set_text_render_color(unreal.Color(col[0], col[1], col[2], 255))
    a.set_actor_label("Sign_" + text.split("\n")[0][:28].replace(" ", "_")); a.set_folder_path("AMF/KennelIsle/Signs")
    a.tags = [TAG, "AMF_Sign"]; out["signs"] += 1; return a

def prop(name, x, y, label, tags, yaw=0):
    for p in eal.list_assets("/Game/AMF/Art/", True, False):
        if p.split("/")[-1].split(".")[0] == name:
            m = unreal.load_asset(p)
            if isinstance(m, unreal.StaticMesh):
                a = eas.spawn_actor_from_object(m, O + unreal.Vector(x, y, 0), unreal.Rotator(0, 0, yaw))
                a.set_actor_label(label); a.set_folder_path("AMF/KennelIsle/Loop"); a.tags = [TAG] + tags
                out["props"] += 1; return a
    out["missing"].append(name); return None

# ---------- WATER: every drink point is tagged + has an overlap volume ----------
W = [("W9_Trough_0", 1500, -900), ("W9_Trough_1", 1500, -300), ("W9_Trough_2", 1500, 300), ("W9_Trough_3", 1500, 900),
     ("W9_Trough_Pen", -1600, 2100), ("W5_Cistern", 300, 0), ("W7_Well_Backup", -900, 300), ("W1_SpringPool", -2000, -2000)]
for lab, x, y in W:
    tag_existing(lab, ["Water_Drinkable", "AMF_Water"])
    vol("Drink_" + lab, x, y, 180, ["Water_Drinkable", "Interact_Drink", "AMF_Water", "Src_" + lab])
for lab in ["W2_Stream_%d" % i for i in range(6)] + ["W3_RainCatch_%d" % i for i in range(3)] + ["W4_SandCharcoalFilter", "W6_SolarStill_Backup"] + ["W8_Pipe_%d" % i for i in range(8)] + ["W8_PipeTee"]:
    tag_existing(lab, ["AMF_Water", "Water_Chain"])
for txt, x, y in [("1 SPRING\nraw water 40 L/min", -2000, -2000), ("2 STREAM\ncarries water downhill", -1100, -1100),
                  ("3 RAIN CATCHERS\n+15 L per rain", -300, 900), ("4 SAND+CHARCOAL FILTER\nraw -> DRINKABLE", 0, 0),
                  ("5 CISTERN 2000 L\ndrink here", 300, 150), ("6 PIPES\ncistern -> troughs", 850, 0),
                  ("7 TROUGHS\npets drink here (E)", 1500, 0), ("BACKUP: WELL", -900, 300), ("BACKUP: SOLAR STILL", 300, -400),
                  ("PEN TROUGH\ngoats + capybara drink", -1600, 2100)]:
    sign(txt, x, y, col=(150, 210, 255))

# ---------- FOOD: goats -> milk pail -> kibble bin -> feeders ----------
for g in [l for l in byl if l.startswith("Mob_PygmyGoat")]: tag_existing(g, ["Food_Producer", "Milk_Source"])
prop("Prop_Pet_AMF_Feeder_V1", -1300, 2300, "F1_MilkPail", ["Food_Source", "Food_Milk", "AMF_Food"])
vol("Collect_Milk", -1300, 2300, 160, ["Food_Source", "Food_Milk", "Interact_Collect", "AMF_Food"])
prop("Prop_Dress_AMF_Crate_V1", 1100, 600, "F2_KibbleBin", ["Food_Source", "Food_Kibble", "Craft_Station", "AMF_Food"])
vol("Craft_Kibble", 1100, 600, 170, ["Food_Source", "Craft_Kibble", "Interact_Craft", "Recipe_Milk+Starkibble", "AMF_Food"])
for i in range(4):
    y = -700 + i * 600
    tag_existing("Prop_Pet_AMF_Bowl_V%d" % (i + 1), ["Food_Source", "Pet_Feeder", "AMF_Food"])
    vol("Feed_%d" % i, 1700, y, 120, ["Food_Source", "Pet_Feeder", "Interact_Feed", "AMF_Food"])
for i in range(4): tag_existing("Prop_Live_AMF_HayBale_V%d" % (i + 1), ["Food_Source", "Food_Hay", "AMF_Food"])
for txt, x, y in [("A GOATS\ngraze hay -> milk", -2000, 2250), ("B MILK PAIL\ncollect milk (E)", -1300, 2300),
                  ("C KIBBLE BIN\nmilk + Starkibble = kibble", 1100, 600), ("D FEEDERS\npets eat kibble", 1700, 1100)]:
    sign(txt, x, y, col=(255, 220, 140))

# ---------- HERB GARDEN -> BREW TROUGH ----------
herbs = [l for l in byl if l.startswith("Prop_Herb_AMF_")]
for h in herbs: tag_existing(h, ["Herb_Source", "Interact_Harvest", "AMF_Herb", "Brew_Target_W9_Trough_3"])
vol("Harvest_HerbGarden", 975, 1700, 520, ["Herb_Source", "Interact_Harvest", "AMF_Herb"])
tag_existing("W9_Trough_3", ["Brew_Trough", "AMF_Brew", "Brew_Max3Herbs"])
vol("Brew_W9_Trough_3", 1500, 900, 200, ["Brew_Trough", "Interact_Brew", "Water_Drinkable", "AMF_Brew"])
for i in range(5):   # visible path of stepping stones garden -> brew trough
    prop("Prop_Dress_AMF_Rock_V%d" % (2 * i + 2), 1150 + i * 70, 1500 - i * 120, "Link_HerbToBrew_%d" % i, ["AMF_Link_Herb_Brew"])
for txt, x, y in [("HERB GARDEN\nharvest up to 3 herbs (E)", 975, 1500), ("BREW TROUGH\nsteep herbs -> pet tonic", 1500, 1050),
                  ("base: heal/shield/speed/fury/calm\nheart: stat   finish: duration", 1500, 1250)]:
    sign(txt, x, y, size=38 if txt.startswith("base") else 46, col=(170, 255, 170))
sign("KENNEL ISLE\nwater -> food -> herbs -> tonics", 0, -2600, z=600, size=120, col=(255, 255, 255))

les.save_current_level()
unreal.log("AMF_LOOP_RESULT " + json.dumps(out))
open(r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_loop.json", "w").write(json.dumps(out, indent=1))
