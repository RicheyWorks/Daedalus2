import unreal, json
D="C:/Users/730ri/projects/Daedalus2/data/economy/"
rec=json.load(open(D+"recipes.json"))["recipes"]
es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ue.get_game_world(): raise RuntimeError("PIE running")
for a in es.get_all_level_actors():
    if a.get_actor_label().startswith("DA_Craft_"): es.destroy_actor(a)
jb=[a for a in es.get_all_level_actors() if a.get_actor_label()=="DA_JukeboxCabinet"]
base=jb[0].get_actor_location()+unreal.Vector(900,0,0)
S=[("Workbench","workbench"),("Furnace","bloomery"),("Anvil","anvil"),("Loom","spinning_wheel"),("Cauldron","cookpot"),("Starforge","refinery")]
out=[]
for i,(p,st) in enumerate(S):
    c=[x for x in unreal.EditorAssetLibrary.list_assets("/Game/Daedalus/Art/Prop/Prop_"+p,True,False) if x.split(".")[-1]=="Prop_"+p] if unreal.EditorAssetLibrary.does_directory_exist("/Game/Daedalus/Art/Prop/Prop_"+p) else ["/Game/Daedalus/Art/Prop/Prop_"+p]; m=unreal.load_asset(c[0]) if c else None
    if m and not isinstance(m,unreal.StaticMesh): out.append((p,type(m).__name__)); continue
    if not m: out.append((p,"missing")); continue
    loc=base+unreal.Vector(0,(i-2.5)*350,0)
    a=es.spawn_actor_from_class(unreal.StaticMeshActor,loc); a.set_actor_label("DA_Craft_"+p); a.static_mesh_component.set_static_mesh(m)
    lines=[r["id"]+": "+" + ".join("%s x%d"%(x["item"],x["n"]) for x in r["in"]) for r in rec if r["station"]==st]
    t=es.spawn_actor_from_class(unreal.TextRenderActor,loc+unreal.Vector(0,0,260)); t.set_actor_label("DA_Craft_Label_"+p)
    c=t.text_render; c.set_text(st.upper()+"\n"+"\n".join(lines)); c.set_world_size(22); c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    t.set_actor_rotation(unreal.Rotator(0,0,180),False)
    out.append((p,len(lines)))
unreal.EditorLevelLibrary.save_current_level()
print("yard",out)
