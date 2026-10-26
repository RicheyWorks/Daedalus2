import unreal
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if ue.get_game_world(): les.editor_request_end_play()
pk=None
for a in es.get_all_level_actors():
    if a.get_actor_label()=="PI_Terrain": pk=a.get_outermost(); break
n=pk.get_name(); ok=False
if n.startswith("/Game/Prometheus/"): ok=unreal.EditorLoadingAndSavingUtils.save_packages([pk],True)
print("play",bool(ue.get_game_world()),"pkg",n,"saved",ok)
