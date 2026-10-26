import unreal, math
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ew=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
def fit(items):
    n=fl=sk=0; worst=0
    for loc, sz in items:
        base=loc.z-sz*50
        h=unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(loc.x,loc.y,base+3000), unreal.Vector(loc.x,loc.y,base-3000), unreal.TraceTypeQuery.ECC_VISIBILITY, False, [], unreal.DrawDebugTrace.NONE, True)
        n+=1
        if not h: fl+=1; continue
        d=base-h.to_tuple()[4].z; worst=max(worst,abs(d))
        if d>10: fl+=1
        elif d<-10: sk+=1
    return {"n":n,"floating":fl,"sunk":sk,"worst_cm":round(worst,1)}
nv=[a for a in eas.get_all_level_actors() if a.actor_has_tag("PYTH_EcoNative")][0]
pc=nv.get_component_by_class(unreal.PCGComponent)
nat=[]; bymesh={}
for c in nv.get_components_by_class(unreal.InstancedStaticMeshComponent):
    m=c.get_editor_property("static_mesh").get_name()
    bymesh[m]=bymesh.get(m,0)+c.get_instance_count()
    for i in range(c.get_instance_count()):
        t=c.get_instance_transform(i, True); nat.append((t.translation, t.scale3d.z))
py=[(a.get_actor_location(), a.get_actor_scale3d().z) for a in eas.get_all_level_actors() if a.actor_has_tag("PYTH_EcoPlant")]
pybymesh={}
for a in eas.get_all_level_actors():
    if a.actor_has_tag("PYTH_EcoPlant"):
        m=a.static_mesh_component.static_mesh.get_name(); pybymesh[m]=pybymesh.get(m,0)+1
result={"native_generated":pc.get_editor_property("generated"),"native_by_mesh":bymesh,"native_fit":fit(nat),"python_by_mesh":pybymesh,"python_fit":fit(py)}
