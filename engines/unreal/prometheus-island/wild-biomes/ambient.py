import unreal
D="C:/Users/730ri/projects/bot-team/art/audio/"
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if ue.get_game_world(): raise RuntimeError("PIE running")
B=[("rain_piano","SW_Amb_Day_RainPiano","DA_Amb_Day","day",0.5),("forest_night_seed","SW_Amb_Night_ForestSeed","DA_Amb_Night","night",0.5),("storm_pad","SW_Amb_Weather_StormPad","DA_Amb_Weather_Storm","weather",0.0)]
ts=[]
for f,n,_,_,_ in B:
    t=unreal.AssetImportTask(); t.filename=D+f+".wav"; t.destination_path="/Game/DaedalusAudio"; t.destination_name=n; t.automated=True; t.replace_existing=True; t.save=True; ts.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(ts)
for a in es.get_all_level_actors():
    if a.get_actor_label().startswith("DA_Amb_"): es.destroy_actor(a)
jb=[a for a in es.get_all_level_actors() if a.get_actor_label()=="DA_JukeboxCabinet"][0].get_actor_location()
out=[]
for i,(f,n,lab,tag,vol) in enumerate(B):
    w=unreal.load_asset("/Game/DaedalusAudio/"+n); w.set_editor_property("looping",True); unreal.EditorAssetLibrary.save_loaded_asset(w)
    a=es.spawn_actor_from_class(unreal.AmbientSound,jb+unreal.Vector(-300,(i-1)*300,0)); a.set_actor_label(lab)
    a.tags=[unreal.Name("DA_Ambient"),unreal.Name("TOD_"+tag)]
    c=a.get_component_by_class(unreal.AudioComponent); c.set_sound(w); c.set_editor_property("allow_spatialization",False)
    c.set_editor_property("volume_multiplier",vol)
    out.append((lab,n,vol))
sky=[(a.get_actor_label(),a.get_class().get_name()) for a in es.get_all_level_actors() if any(k in a.get_class().get_name() for k in ("DirectionalLight","SkyAtmosphere","SkyLight","TimeOfDay","DayNight","Sun"))]
unreal.EditorLevelLibrary.save_current_level()
print("amb",out); print("sky",sky)
