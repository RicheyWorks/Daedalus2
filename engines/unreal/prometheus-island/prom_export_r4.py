# Prometheus r4: export PrometheusIsland actor transforms (UE cm, relative to PI_Terrain) to JSON for Blender parity. Read-only, no saves.
import unreal, json
es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ue.get_game_world(): unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
acts=[a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")]
C=[a for a in acts if a.get_actor_label()=="PI_Terrain"][0].get_actor_location(); out=[]
for a in acts:
    l=a.get_actor_location(); r=a.get_actor_rotation(); s=a.get_actor_scale3d(); d={"label":a.get_actor_label(),"class":a.get_class().get_name(),
      "loc":[round(l.x-C.x,1),round(l.y-C.y,1),round(l.z-C.z,1)],"rot":[round(r.roll,2),round(r.pitch,2),round(r.yaw,2)],"scale":[round(s.x,3),round(s.y,3),round(s.z,3)],"tags":[str(t) for t in a.tags]}
    smc=a.get_component_by_class(unreal.StaticMeshComponent)
    if smc and smc.static_mesh: d["mesh"]=smc.static_mesh.get_path_name()
    out.append(d)
p="C:/Users/730ri/projects/_wt-prom-island/data/islands/prometheus/ue_transforms.json"
json.dump({"origin_cm":[C.x,C.y,C.z],"units":"cm, UE left-handed, relative to PI_Terrain","actors":out},open(p,"w"),indent=1)
print("R4",json.dumps({"exported":len(out),"path":p,"pie":bool(ue.get_game_world())}))
# 2nd step: retry hidden SceneCapture hero now that world lighting is fixed (Sky Director Clear). No saves.
W=ue.get_editor_world(); OUT="C:/Users/730ri/projects/bot-team/art/prometheus_island/shots"
cam=C+unreal.Vector(-26000,-20000,16000); tgt=C+unreal.Vector(0,0,1500)
rt=unreal.RenderingLibrary.create_render_target2d(W,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8)
c=es.spawn_actor_from_class(unreal.SceneCapture2D,cam,unreal.MathLibrary.find_look_at_rotation(cam,tgt)); sc=c.capture_component2d
sc.set_editor_property("texture_target",rt); sc.set_editor_property("capture_source",unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR); sc.set_editor_property("fov_angle",55.0)
sc.capture_scene(); unreal.RenderingLibrary.export_render_target(W,rt,OUT,"PI_hero_ue_r4.png"); es.destroy_actor(c); print("R4SHOT ok")
