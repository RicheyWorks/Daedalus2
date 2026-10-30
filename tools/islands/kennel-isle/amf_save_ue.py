import unreal, json
out={}
try:
    les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if les.is_in_play_in_editor(): les.editor_request_end_play()
    out["pie_after"]=les.is_in_play_in_editor()
except Exception as e: out["pie_err"]=str(e)
saved=[]
world=unreal.EditorLevelLibrary.get_editor_world()
for lv in unreal.EditorLevelUtils.get_levels(world):
    p=lv.get_path_name()
    if "Island_AMF" in p or "WildBiomes_AMF_Pets" in p:
        try:
            ok=unreal.EditorLoadingAndSavingUtils.save_packages([lv.get_outermost()], True)
            saved.append([p,ok])
        except Exception as e: saved.append([p,str(e)])
out["saved"]=saved
try: unreal.SystemLibrary.execute_console_command(None,"Tab.CloseAll") 
except Exception as e: out["tab_err"]=str(e)
json.dump(out,open(r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_save.json","w"),indent=1)
