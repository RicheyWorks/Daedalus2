import unreal
act=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
D=unreal.Vector(290000-6000000,148500,0)
b=[x for x in act.get_all_level_actors() if x.actor_has_tag("BUF_Island")]
for x in b: x.set_actor_location(x.get_actor_location()+D,False,False)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor(): les.editor_request_end_play()
w=unreal.EditorLevelLibrary.get_editor_world()
ls=unreal.GameplayStatics.get_streaming_level(w,"Buffffff_Island"); unreal.EditorLevelUtils.make_level_current(ls)
s1=unreal.EditorLevelLibrary.save_current_level()
s2=unreal.EditorLoadingAndSavingUtils.save_map(w,"/Game/Daedalus/DaedalusWorld")
xs=[x.get_actor_location() for x in b]; c=lambda t: sum(1 for x in b if x.actor_has_tag(t))
print("BUFMV",len(b),"x",min(v.x for v in xs),max(v.x for v in xs),"y",min(v.y for v in xs),max(v.y for v in xs),"liv",c("Livestock"),"drink",c("Drinkable"),"herb",c("HerbBed"),"saved",s1,s2,"pie",les.is_in_play_in_editor())
