import unreal, json
SUB="ArkDock_2hot2trot"; DX=150000.0; DY=-5851500.0
DO_MOVE = globals().get("DO_MOVE", 0.0) > 0
ues=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
out={"playing": bool(ues.get_game_world())}
mine=[a for a in eas.get_all_level_actors() if SUB in a.get_level().get_path_name() and not isinstance(a,(unreal.WorldSettings,))]
out["actors"]=len(mine)
out["items"]=len([a for a in mine if a.actor_has_tag("ArkIsle_Item")])
out["tagged"]=len([a for a in mine if a.actor_has_tag("GROK_ArkIsle") or a.actor_has_tag("GROK_ArkDock")])
def bounds():
    mn=[1e18]*3; mx=[-1e18]*3
    for a in mine:
        if not (a.actor_has_tag("GROK_ArkIsle") or a.actor_has_tag("GROK_ArkDock")): continue
        o,e=a.get_actor_bounds(False)
        if e.x>1e6: continue
        for i,(c,h) in enumerate(((o.x,e.x),(o.y,e.y),(o.z,e.z))):
            mn[i]=min(mn[i],c-h); mx[i]=max(mx[i],c+h)
    return [round(v) for v in mn],[round(v) for v in mx]
out["before"]=bounds()
if DO_MOVE and not out["playing"]:
    les.set_current_level_by_name(SUB)
    moved=0
    for a in mine:
        if a.get_attach_parent_actor(): continue
        l=a.get_actor_location(); a.set_actor_location(unreal.Vector(l.x+DX,l.y+DY,l.z),False,True); moved+=1
    out["moved"]=moved; out["after"]=bounds()
    les.set_current_level_by_name(SUB); out["saved"]=les.save_current_level()
    mn,mx=out["after"]; cx=(mn[0]+mx[0])/2; cy=(mn[1]+mx[1])/2
    ues.set_level_viewport_camera_info(unreal.Vector(cx-9000,cy-16000,9000),unreal.Rotator(roll=0,pitch=-28,yaw=58))
print(json.dumps(out)); result=out
