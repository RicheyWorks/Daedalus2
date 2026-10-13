"""youtube-master: import 18 READY hero props (QUEUE 6302-6319) + place on YTM_Island. Idempotent (tag YTM_Hero). Saves YTM_Island sublevel only."""
import unreal
GLB = r"C:\Users\730ri\projects\bot-team\art\glb"; ART = "/Game/Daedalus/Art"; SUB = "/Game/YTM/Maps/YTM_Island"
OFFSET = unreal.Vector(0, -2600000, 0); TAG = "YTM_Hero"
eas = unreal.EditorAssetLibrary; act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
SIGNS = {"TheSpring":(1500,400,200),"Drink":(1200,-500,160),"HerbGarden":(4800,300,270),"Melody":(5200,-700,250),"Seeds":(4600,1100,290),
 "TheFarm":(-4800,300,90),"Pens":(-5200,-700,110),"Kitchen":(300,4000,180),"RecordingIsle":(0,-900,0),"Richeyworks":(-600,-700,20),
 "ArkDock":(0,-11000,0),"Jukebox":(-900,600,300)}
props = [("Prop",f"Prop_YTM_Sign_{k}",v) for k,v in SIGNS.items()]
props += [("Prop","Prop_YTM_RecordShrine",(-800,1200,135)),("Prop","Prop_YTM_Jukebox",(-1100,700,120))]
props += [("Item",f"Item_YTM_Record_{r}",(-800+60*(i-1.5),1000,85)) for i,r in enumerate(["AmericanOldTime","Alpine","CelticPipes","Gamelan"])]
tasks=[]
for kind,name,_ in props:
    t=unreal.AssetImportTask(); t.filename=f"{GLB}\\{name}.glb"; t.destination_path=f"{ART}/{kind}/{name}"
    t.automated=True; t.replace_existing=True; t.save=True; tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
ls = unreal.GameplayStatics.get_streaming_level(world, "YTM_Island"); unreal.EditorLevelUtils.make_level_current(ls)
for a in act.get_all_level_actors():
    if a.actor_has_tag(TAG): act.destroy_actor(a)
def mesh(path):
    for p in eas.list_assets(path, True, False):
        o = eas.load_asset(p)
        if isinstance(o, unreal.StaticMesh): return o
placed=0
for kind,name,(x,y,yaw) in props:
    m = mesh(f"{ART}/{kind}/{name}")
    if not m: unreal.log_warning("YTM_Hero missing "+name); continue
    a = act.spawn_actor_from_object(m, unreal.Vector(OFFSET.x+x, OFFSET.y+y, OFFSET.z), unreal.Rotator(0,0,yaw))
    a.set_actor_label(name); a.tags=["YTM_Island", TAG]; placed+=1
unreal.log("YTM_Hero placed %d/%d" % (placed, len(props)))
unreal.EditorLoadingAndSavingUtils.save_current_level()
