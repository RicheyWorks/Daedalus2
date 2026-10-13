import unreal, math
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ew=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
vols=[a for a in eas.get_all_level_actors() if a.actor_has_tag("PYTH_Eco") or a.actor_has_tag("PYTH_EcoNative")]
def items(v):
    out=[];bym={}
    for c in v.get_components_by_class(unreal.InstancedStaticMeshComponent):
        m=c.get_editor_property("static_mesh").get_name(); bym[m]=bym.get(m,0)+c.get_instance_count()
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,True); out.append((t.translation,t.scale3d.z))
    return out,bym
def fit(its):
    n=fl=sk=0; ds=[]
    for loc,sz in its:
        base=loc.z-sz*50
        h=unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(loc.x,loc.y,base+3000), unreal.Vector(loc.x,loc.y,base-3000), unreal.TraceTypeQuery.ECC_VISIBILITY, False, vols, unreal.DrawDebugTrace.NONE, True)
        n+=1
        if not h: fl+=1; continue
        d=base-h.to_tuple()[4].z; ds.append(abs(d))
        if d>10: fl+=1
        elif d<-10: sk+=1
    ds.sort()
    return {"n":n,"floating":fl,"sunk":sk,"p95_cm":round(ds[int(len(ds)*0.95)],1) if ds else None}
def nnR(its):
    pts=[(l.x,l.y) for l,_ in its]; n=len(pts)
    if n<3: return None
    import collections
    cell=200.0; g=collections.defaultdict(list)
    for p in pts: g[(int(p[0]//cell),int(p[1]//cell))].append(p)
    tot=0
    for p in pts:
        best=1e9; k=1
        while best==1e9 and k<20:
            for i in range(-k,k+1):
                for j in range(-k,k+1):
                    for q in g.get((int(p[0]//cell)+i,int(p[1]//cell)+j),()):
                        if q is not p: best=min(best,math.hypot(q[0]-p[0],q[1]-p[1]))
            k+=1
        tot+=best
    return round((tot/n)/(0.5/math.sqrt(n/(3500.0*3500.0))),2)
r={}
for v in vols:
    its,bym=items(v); r["native" if v.actor_has_tag("PYTH_EcoNative") else "python_pcg"]={"by_mesh":bym,"fit":fit(its),"clark_evans_all":nnR(its)}
result=r
