# Prometheus round-3 turn: livestock genome calls ONLY (RAM-gated). was round-2: terrain flip fix, genome livestock calls, warm hero re-shot, optional Wild Biomes. Saves ONLY own packages.
import unreal, json, math, os, re, ctypes
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAL=unreal.EditorAssetLibrary; at=unreal.AssetToolsHelpers.get_asset_tools()
R={}
def free_gb():
    class M(ctypes.Structure): _fields_=[("l",ctypes.c_ulong),("ml",ctypes.c_ulong),("tp",ctypes.c_ulonglong),("ap",ctypes.c_ulonglong),("tf",ctypes.c_ulonglong),("af",ctypes.c_ulonglong),("tv",ctypes.c_ulonglong),("av",ctypes.c_ulonglong),("x",ctypes.c_ulonglong)]
    m=M(); m.l=ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); return m.ap/2**30
if ue.get_game_world(): les.editor_request_end_play(); R["pie_stopped_at_start"]=True
W=ue.get_editor_world(); G="/Game/Prometheus"; PIMAP=G+"/Maps/PrometheusIsland"
SRC="C:/Users/730ri/projects/bot-team/art/prometheus_island/"
if not les.set_current_level_by_name("PrometheusIsland"): raise RuntimeError("PrometheusIsland not loaded")
A={a.get_actor_label():a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")}
# 2) genome calls LAST, only with >=1 GB free (imports are the crash risk)
R["ram_before_calls_gb"]=round(free_gb(),2)
if R["ram_before_calls_gb"]>=1.0:
    ts=[]
    for f in sorted(os.listdir(SRC+"calls")):
        if f.endswith(".wav") and not EAL.does_asset_exist(G+"/Audio/Calls/"+f[:-4]):
            t=unreal.AssetImportTask(); t.filename=SRC+"calls/"+f; t.destination_path=G+"/Audio/Calls"; t.destination_name=f[:-4]; t.automated=True; t.save=True; ts.append(t)
    if ts: at.import_asset_tasks(ts)
    for a in es.get_all_level_actors():
        if a.get_actor_label().startswith("PI_Call_"): es.destroy_actor(a)
    nc=0
    for lab,a in list(A.items()):
        m=re.match(r"PI_Stock_([A-Za-z]+)_(.+)_(\d\d)$",lab)
        if not m: continue
        sw=unreal.load_asset(G+"/Audio/Calls/SW_Call_PI_"+m.group(2))
        if not sw: continue
        sw.set_editor_property("looping",True); EAL.save_loaded_asset(sw)
        s=es.spawn_actor_from_class(unreal.AmbientSound,a.get_actor_location()+unreal.Vector(0,0,120)); s.set_actor_label("PI_Call_"+lab[9:]); s.tags=[unreal.Name("PI"),unreal.Name("livestock_call")]
        ac=s.get_component_by_class(unreal.AudioComponent); ac.set_sound(sw); ac.set_editor_property("volume_multiplier",0.3); ac.set_editor_property("override_attenuation",True)
        st=ac.get_editor_property("attenuation_overrides"); st.set_editor_property("spatialize",True); st.set_editor_property("falloff_distance",1200.0)
        st.set_editor_property("attenuate_with_lpf",True); st.set_editor_property("lpf_frequency_at_max",1500.0); ac.set_editor_property("attenuation_overrides",st)
        s.attach_to_actor(a,"",unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False); nc+=1
    R["calls"]=nc
    EAL.save_asset(PIMAP,False); EAL.save_directory(G,only_if_is_dirty=True,recursive=True)
else: R["calls"]="SKIPPED: RAM %.2f GB < 1 GB"%R["ram_before_calls_gb"]
if ue.get_game_world(): les.editor_request_end_play()
R["pie"]=bool(ue.get_game_world()); print("R3",json.dumps(R))
