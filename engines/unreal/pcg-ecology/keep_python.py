import unreal
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ew=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for v in [a for a in eas.get_all_level_actors() if a.actor_has_tag("PYTH_Eco") or a.actor_has_tag("PYTH_EcoNative")]:
    pc=v.get_component_by_class(unreal.PCGComponent)
    pc.set_editor_property("generation_trigger", unreal.PCGComponentGenerationTrigger.GENERATE_ON_DEMAND)
    pc.cleanup_local(True)
left=sum(c.get_instance_count() for a in eas.get_all_level_actors() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent) if a.actor_has_tag("PYTH_Eco") or a.actor_has_tag("PYTH_EcoNative"))
n=fl=sk=0
for a in eas.get_all_level_actors():
    if not a.actor_has_tag("PYTH_EcoPlant"): continue
    loc=a.get_actor_location(); base=loc.z-a.get_actor_scale3d().z*50
    h=unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(loc.x,loc.y,base+3000), unreal.Vector(loc.x,loc.y,base-3000), unreal.TraceTypeQuery.ECC_VISIBILITY, False, [a], unreal.DrawDebugTrace.NONE, True)
    n+=1
    if not h: fl+=1; continue
    d=base-h.to_tuple()[4].z
    if d>10: fl+=1
    elif d<-10: sk+=1
result={"pcg_instances_left":left,"python_actors":n,"floating":fl,"sunk":sk}
