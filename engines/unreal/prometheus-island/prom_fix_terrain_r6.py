# Prometheus r5: terrain transform fix + ground snap. OBJ is Z-up meters, (x,y,z)=(lx,ly,h) matching heights.json / pi_place hz().
# Diagnosis: r2 auto-fit kept scale 100 regardless of import units; derive scale from mesh bounds, then search 24 rotations x mirror by traces.
import unreal, json, math
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAL=unreal.EditorAssetLibrary

R={}; G="/Game/Prometheus"; PIMAP=G+"/Maps/PrometheusIsland"; SRC="C:/Users/730ri/projects/_wt-prom-island/data/islands/prometheus/"
if not les.set_current_level_by_name("PrometheusIsland"): raise RuntimeError("PrometheusIsland not loaded")
A={a.get_actor_label():a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")}
T=A["PI_Terrain"]; C=T.get_actor_location(); sm=T.static_mesh_component; mesh=sm.static_mesh
I=json.load(open(SRC+"island.json")); HM=json.load(open(SRC+"heights.json")); N=I["N"]; S=I["size_m"]*100.0; P=I["peak_m"]*100.0
def hz(lx,ly):
    j=(lx/S+0.5)*(N-1); i=(ly/S+0.5)*(N-1)
    if not (0<=i<N-1 and 0<=j<N-1): return None
    i0,j0=int(i),int(j); fi,fj=i-i0,j-j0
    h=HM[i0][j0]*(1-fi)*(1-fj)+HM[i0][j0+1]*(1-fi)*fj+HM[i0+1][j0]*fi*(1-fj)+HM[i0+1][j0+1]*fi*fj
    return None if h<=0.06 else h*P
bb=mesh.get_bounding_box(); ext=[bb.max.x-bb.min.x,bb.max.y-bb.min.y,bb.max.z-bb.min.z]
R0=dict(rot=[T.get_actor_rotation().roll,T.get_actor_rotation().pitch,T.get_actor_rotation().yaw],scale=[T.get_actor_scale3d().x,T.get_actor_scale3d().y,T.get_actor_scale3d().z],local_extent=[round(e,2) for e in ext])
# r6: translation least-squares (keep rotation/scale). Residual = trace height - expected; fit dx,dy grid then dz = mean residual. Revert if mean abs err > 300 cm.
samples=[(x,y) for x in range(-18000,18001,3000) for y in range(-18000,18001,3000) if hz(x,y) is not None]
L0=T.get_actor_location()
def resid(off):
    T.set_actor_location(L0+off,False,False); out=[]
    for x,y in samples:
        r=sm.line_trace_component(C+unreal.Vector(x,y,40000),C+unreal.Vector(x,y,-40000),True,False,False)
        if isinstance(r,tuple) and r[0]: out.append((r[1].z-C.z)-hz(x,y))
    return out
def err(rs):
    if len(rs)<len(samples)*0.7: return 1e9
    m=sum(rs)/len(rs); return sum(abs(v-m) for v in rs)/len(rs)
best=(err(resid(unreal.Vector(0,0,0))),0,0); base=best[0]
for step in (1500,500):
    bx,by=best[1],best[2]
    for dx in range(bx-3*step,bx+3*step+1,step):
        for dy in range(by-3*step,by+3*step+1,step):
            e=err(resid(unreal.Vector(dx,dy,0)))
            if e<best[0]: best=(e,dx,dy)
rs=resid(unreal.Vector(best[1],best[2],0)); dz=-sum(rs)/len(rs) if rs else 0
T.set_actor_location(L0+unreal.Vector(best[1],best[2],dz),False,False)
fin=sum(abs(v) for v in resid(unreal.Vector(best[1],best[2],dz)))/max(1,len(rs))
kept=fin<=300
if not kept: T.set_actor_location(L0,False,False)
print("r6 base_err_cm",round(base),"best",best[1],best[2],round(dz),"final_err_cm",round(fin),"kept",kept,"samples",len(samples))
