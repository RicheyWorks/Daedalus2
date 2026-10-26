import unreal
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ew=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
n=fl=sk=0; worst=0.0; ds=[]
for a in eas.get_all_level_actors():
    if not a.actor_has_tag("PYTH_EcoPlant"): continue
    loc=a.get_actor_location(); base=loc.z-a.get_actor_scale3d().z*50
    h=unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(loc.x,loc.y,base+3000), unreal.Vector(loc.x,loc.y,base-3000), unreal.TraceTypeQuery.ECC_VISIBILITY, False, [a], unreal.DrawDebugTrace.NONE, True)
    n+=1
    if not h: fl+=1; continue
    d=base-h.to_tuple()[4].z; ds.append(d); worst=max(worst,abs(d))
    if d>10: fl+=1
    elif d<-10: sk+=1
ds.sort()
result={"plants":n,"floating_gt10cm":fl,"sunk_gt10cm":sk,"worst_cm":round(worst,1),"median_cm":round(ds[len(ds)//2],2) if ds else None}
