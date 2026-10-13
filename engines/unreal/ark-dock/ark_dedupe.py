import unreal, json
# Ark Dock Isle dedupe: delete exact stacked duplicates in our sublevel only.
# Key = class + mesh set + location (1 cm) + rotation (0.1 deg) + scale (0.001). Keeps the first actor of each group.
SUB="ArkDock_2hot2trot"
DO_DELETE = globals().get("DO_DELETE", 0.0) > 0
ues=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
out={"playing": bool(ues.get_game_world())}
mine=[a for a in eas.get_all_level_actors() if SUB in a.get_level().get_path_name() and not isinstance(a,(unreal.WorldSettings,))]
out["before"]=len(mine)
def meshes(a):
    m=[]
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm=c.get_editor_property("static_mesh"); m.append(sm.get_path_name() if sm else "-")
    for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
        sk=c.get_editor_property("skeletal_mesh_asset") if hasattr(c,"skeletal_mesh_asset") else None
        m.append(sk.get_path_name() if sk else "skel")
    return tuple(sorted(m))
groups={}
for a in mine:
    l=a.get_actor_location(); r=a.get_actor_rotation(); s=a.get_actor_scale3d()
    k=(a.get_class().get_path_name(), meshes(a), round(l.x),round(l.y),round(l.z),
       round(r.pitch,1),round(r.yaw,1),round(r.roll,1), round(s.x,3),round(s.y,3),round(s.z,3))
    groups.setdefault(k,[]).append(a)
dups=[a for g in groups.values() for a in g[1:]]
out["groups"]=len(groups); out["dups"]=len(dups)
from collections import Counter
out["dup_classes"]=dict(Counter(a.get_class().get_name() for a in dups).most_common(8))
if DO_DELETE and not out["playing"] and dups:
    les.set_current_level_by_name(SUB)
    out["deleted"]=sum(1 for a in dups if eas.destroy_actor(a))
    out["after"]=len([a for a in eas.get_all_level_actors() if SUB in a.get_level().get_path_name() and not isinstance(a,(unreal.WorldSettings,))])
    les.set_current_level_by_name(SUB); out["saved"]=les.save_current_level()
print(json.dumps(out)); result=out
