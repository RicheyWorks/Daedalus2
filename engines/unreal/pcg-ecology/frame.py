import unreal, math
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ues=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ps=[a.get_actor_location() for a in eas.get_all_level_actors() if a.actor_has_tag("PYTH_EcoPlant")]
cx=sum(p.x for p in ps)/len(ps); cy=sum(p.y for p in ps)/len(ps); zs=sorted(p.z for p in ps); cz=zs[len(zs)//2]
R=max(max(abs(p.x-cx),abs(p.y-cy)) for p in ps)
loc=unreal.Vector(cx-R*1.6, cy-R*1.6, cz+R*1.4)
ues.set_level_viewport_camera_info(loc, unreal.Rotator(roll=0, pitch=-38, yaw=45))
result={"centre":[round(cx),round(cy),round(cz)],"R":round(R),"cam":[round(loc.x),round(loc.y),round(loc.z)]}
