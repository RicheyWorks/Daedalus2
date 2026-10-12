"""Youtube Master Island (youtube-master, Team Grok). Unreal Editor Python, run ONLY in a granted Grok editor turn:
  python ...\\pcg-ecology\\ue_send.py C:\\Users\\730ri\\projects\\bot-team\\art\\NOTES\\youtube-master\\ytm_island_ue.py 600
Double-size island (240 m) built from SHIPPED _YTM_ assets into own sublevel /Game/YTM/Maps/YTM_Island.
Zones: spawn + clean spring (<=40 m, drinkable water mandatory), well/pump/filter/boiler, spiral herb garden
(12 note-herbs, Brewbench), farm (pens, troughs, barn, coop, 24 livestock), kitchen (stove, mill, churn, smokehouse),
rock/cliff rim. Tags every actor YTM_Island. Idempotent (deletes its tagged actors first). No Play. Saves sublevel only."""
import math, random, unreal
SUB = "/Game/YTM/Maps/YTM_Island"; ART = "/Game/Daedalus/Art"; TAG = "YTM_Island"
R = 12000.0  # radius cm (240 m diameter = double size)
OFFSET = unreal.Vector(0, -2600000, 0)  # 26 km south of origin: clear of Wild Biomes rings 4.5-16 km
rnd = random.Random(2820)
eas = unreal.EditorAssetLibrary; act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not eas.does_asset_exist(SUB):
    unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, SUB, False)
ls = unreal.GameplayStatics.get_streaming_level(world, SUB.split("/")[-1])
if not ls:
    ls = unreal.EditorLevelUtils.add_level_to_world(world, SUB, unreal.LevelStreamingAlwaysLoaded)
unreal.EditorLevelUtils.make_level_current(ls.get_loaded_level())
for a in act.get_all_level_actors():
    if a.actor_has_tag(TAG): act.destroy_actor(a)
placed = {"ok":0,"missing":set()}
def mesh(name):
    kind = name.split("_")[0]
    p = f"{ART}/{kind}/{name}/{name}"
    if not eas.does_asset_exist(p):
        p2 = f"{ART}/{kind}/{name}"
        p = p2 if eas.does_asset_exist(p2) else None
    return eas.load_asset(p) if p else None
def put(name, x, y, z=0, yaw=None, s=1.0):
    m = mesh(name)
    if not m: placed["missing"].add(name); return None
    a = act.spawn_actor_from_object(m, unreal.Vector(OFFSET.x + x, OFFSET.y + y, OFFSET.z + z),
                                     unreal.Rotator(0, 0, rnd.uniform(0, 360) if yaw is None else yaw))
    a.set_actor_scale3d(unreal.Vector(s, s, s)); a.tags = [TAG]; a.set_folder_path("YTM_Island")
    placed["ok"] += 1; return a
# ground: stacked flat cliff/rock kit as a disc base + engine plane fallback
base = act.spawn_actor_from_class(unreal.StaticMeshActor, OFFSET, unreal.Rotator(0,0,0))
base.static_mesh_component.set_static_mesh(eas.load_asset("/Engine/BasicShapes/Cylinder"))
base.set_actor_scale3d(unreal.Vector(R/50, R/50, 20)); base.set_actor_location(OFFSET - unreal.Vector(0,0,2000), False, False)
base.tags = [TAG]; base.set_actor_label("YTM_Island_Ground")
grass = eas.load_asset("/Game/Daedalus/Materials/M_Grass") if eas.does_asset_exist("/Game/Daedalus/Materials/M_Grass") else None
if grass: base.static_mesh_component.set_material(0, grass)
ps = act.spawn_actor_from_class(unreal.TargetPoint, OFFSET + unreal.Vector(0,0,100), unreal.Rotator(0,0,0))
ps.set_actor_label("YTM_Island_Spawn"); ps.tags = [TAG, "YTM_Spawn"]
# WATER (mandatory): clean spring at 15 m from spawn + full water chain
for i,(n,ang,d) in enumerate([("Spring",0,1500),("Well",40,3000),("HandPump",80,2500),("Filter",120,2800),("Boiler",160,3200),
                               ("RainBarrel",200,2600),("Cistern",240,3400),("Fountain",300,2000),("Pool",330,4500)]):
    a = put(f"Prop_YTM_Water_{n}_V1", d*math.cos(math.radians(ang)), d*math.sin(math.radians(ang)))
    if a: a.tags = [TAG, "YTM_Water", "Drinkable" if n in ("Spring","Well","HandPump","Fountain") else "RawWater"]
# HERB GARDEN: spiral of 12 note-herbs x 4 stages at east (+x) 60 m
HERBS=["Doleaf","Sharpcress","Rebell","Flatfern","Mimint","Fasage","Hushmoss","Solthorn","Gloryroot","Lavine","Dronebloom","Tisquill"]
cx, cy = 6000, 0
put("Prop_YTM_Station_Brewbench", cx, cy, yaw=0)
for k in range(12*4):
    t = 0.6*k; r = 300 + 45*k
    a = put(f"Prop_YTM_Herb_{HERBS[k%12]}_S{k//12+1}", cx + r*math.cos(t), cy + r*math.sin(t))
    if a: a.tags = [TAG, "YTM_Herb", "Harvestable"]
# FARM: west (-x) 60 m, pens with troughs + livestock
fx, fy = -6000, 0
put("Bld_YTM_Barn", fx-1500, fy, yaw=90); put("Bld_YTM_Coop", fx, fy+1800, yaw=0); put("Bld_YTM_Silo", fx-1500, fy-1200)
LIV=["Mooncalf","ReefSheep","BubbleHen","Kelpig","DriftGoat","StormDuck","Hornox","Glowllama"]
for i,l in enumerate(LIV):
    px, py = fx + (i%4)*900 - 1000, fy + (i//4)*1100 - 500
    for e in range(4): put("Prop_YTM_Fence_V1", px + [-350,350,0,0][e], py + [0,0,-350,350][e], yaw=[90,90,0,0][e], s=3.5)
    t = put("Prop_YTM_Water_RainBarrel_V2", px+200, py+200, yaw=0)
    if t: t.tags=[TAG,"YTM_Trough"]
    for age in ("Calf","Adult","Elder"):
        a = put(f"Mob_YTM_{l}_{age}", px + rnd.uniform(-200,200), py + rnd.uniform(-200,200))
        if a: a.tags = [TAG, "YTM_Livestock", l, age]
    for st in (1,2,3): put(f"Prop_YTM_Crop_{['Clover','Saltgrass','Groat','Kelpweed','Bitroot','Reedcorn','Spudlet','Moonbean'][i]}_S{st}", px-500+st*150, py-600)
# KITCHEN: north (+y) 50 m
for i,s in enumerate(["Stove","Mill","Churn","Press","Smokehouse","Loom","Smelter"]): put(f"Prop_YTM_Station_{s}", -1800+i*600, 5000, yaw=180)
# RIM: rock/cliff kit around the edge
kit = [a for a in eas.list_assets(ART+"/Prop", True, False) if "_YTM_Cliff_" in a or "_YTM_Rock_" in a or "_YTM_Boulder_" in a]
names = sorted({p.split("/")[-1].split(".")[0] for p in kit})
for k in range(120):
    if not names: break
    ang = 2*math.pi*k/120; r = R*rnd.uniform(0.88,0.98)
    put(names[k % len(names)], r*math.cos(ang), r*math.sin(ang), s=rnd.uniform(1.0,2.5))
for k in range(80):
    ang = rnd.uniform(0, 2*math.pi); r = R*rnd.uniform(0.35,0.85)
    nm = [n for n in names if "Rock" in n or "Boulder" in n] or names
    if nm: put(nm[k % len(nm)], r*math.cos(ang), r*math.sin(ang))
# GAMEPLAY hooks (DaedalusLink C++ on branch grok/ytm-homestead; skipped if not compiled yet)
LIVDATA={"Mooncalf":("Milk",6),"ReefSheep":("Wool",10),"BubbleHen":("Egg",4),"Kelpig":("Bacon",12),"DriftGoat":("Cheese",8),"StormDuck":("Feather",5),"Hornox":("Hide",15),"Glowllama":("GlowFleece",20)}
hooks=0
for a in [x for x in act.get_all_level_actors() if x.actor_has_tag(TAG)]:
    loc=a.get_actor_location(); tags=[str(t) for t in a.tags]
    if "YTM_Water" in tags and hasattr(unreal,"DaedalusWaterSource"):
        w=act.spawn_actor_from_class(unreal.DaedalusWaterSource, loc, unreal.Rotator(0,0,0))
        lab=a.get_actor_label()
        w.set_editor_property("quality","clean" if "Drinkable" in tags else "raw")
        w.set_editor_property("treats", "Filter" in lab or "Boiler" in lab)
        w.tags=[TAG,"YTM_WaterLogic"]; hooks+=1
    if "YTM_Livestock" in tags and hasattr(unreal,"DaedalusLivestock"):
        sp=tags[2]; age=tags[3]; prod,every=LIVDATA[sp]
        l=act.spawn_actor_from_class(unreal.DaedalusLivestock, loc, unreal.Rotator(0,0,0))
        for k,v in (("species",sp),("age",age),("product",prod),("produce_every_min",float(every))): l.set_editor_property(k,v)
        a.attach_to_actor(l,"",unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
        l.tags=[TAG,"YTM_LivestockLogic"]; hooks+=1
    if a.get_actor_label().startswith("Prop_YTM_Station_Brewbench") and hasattr(unreal,"DaedalusBrewBench"):
        b=act.spawn_actor_from_class(unreal.DaedalusBrewBench, loc, unreal.Rotator(0,0,0)); b.tags=[TAG]; hooks+=1
unreal.log(f"YTM_Island: gameplay hooks {hooks} (0 = DaedalusLink homestead classes not compiled yet)")
# drinkable-water check (mandatory): a clean source within 40 m of spawn
sp=ps.get_actor_location()
ok=[x for x in act.get_all_level_actors() if x.actor_has_tag("Drinkable") and (x.get_actor_location()-sp).length()<=4000]
unreal.log(("YTM_Island WATER OK: " if ok else "YTM_Island WATER FAIL: ")+str(len(ok))+" drinkable sources within 40 m of spawn")
les.save_current_level()
unreal.log(f"YTM_Island: placed {placed['ok']} actors, missing {len(placed['missing'])}: {sorted(placed['missing'])[:20]}")
