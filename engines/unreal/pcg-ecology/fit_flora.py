import unreal
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ew=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
n=fl=sk=0; std=0
for a in eas.get_all_level_actors():
    if not a.actor_has_tag("PYTH_EcoPlant"): continue
    if not a.actor_has_tag("PYTH_Flora"): std+=1; continue
    loc=a.get_actor_location()
    h=unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(loc.x,loc.y,loc.z+3000), unreal.Vector(loc.x,loc.y,loc.z-3000), unreal.TraceTypeQuery.ECC_VISIBILITY, False, [a], unreal.DrawDebugTrace.NONE, True)
    n+=1
    if not h: fl+=1; continue
    d=loc.z-h.to_tuple()[4].z
    if d>10: fl+=1
    elif d<-10: sk+=1
result={"flora":n,"standins_left":std,"floating":fl,"sunk":sk}
