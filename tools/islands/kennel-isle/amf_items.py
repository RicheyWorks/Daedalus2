# Kennel Isle (art-master-flex) procedural item batch. Blender 4.3, run: blender -b --python amf_items.py
import bpy, random, os, json, math, sys
OUT = r"C:\Users\730ri\projects\bot-team\art\glb\amf"
os.makedirs(OUT, exist_ok=True)
R = random.Random(7)
P = dict(wood=(0.55,0.36,0.2),dark=(0.3,0.2,0.12),stone=(0.55,0.55,0.58),water=(0.25,0.6,0.95),
 leaf=(0.3,0.7,0.25),moss=(0.35,0.55,0.25),copper=(0.78,0.44,0.23),iron=(0.79,0.7,0.61),hay=(0.9,0.8,0.4),
 red=(0.8,0.2,0.2),cloth=(0.75,0.6,0.85),glass=(0.7,0.9,1.0),gold=(0.95,0.76,0.19),star=(0.5,0.89,1.0),white=(0.95,0.95,0.9))
mats={}
def mat(n):
    if n in mats: return mats[n]
    m=bpy.data.materials.new("M_AMF_"+n); c=P[n] if isinstance(n,str) and n in P else n
    m.diffuse_color=(*c,1); m.use_nodes=True; m.node_tree.nodes["Principled BSDF"].inputs[0].default_value=(*c,1)
    mats[n]=m; return m
def build(name, boxes):
    # boxes: (sx,sy,sz, x,y,z_bottom, matname)
    bpy.ops.object.select_all(action='DESELECT')
    objs=[]; used=[]
    for sx,sy,sz,x,y,z,mn in boxes:
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z+sz/2)); o=bpy.context.object
        o.scale=(sx,sy,sz); bpy.ops.object.transform_apply(scale=True)
        if mn not in used: used.append(mn)
        o.data.materials.append(mat(mn)); objs.append(o)
    used=used[:3]
    for o in objs:
        mn=o.data.materials[0].name[6:]
        o.data.materials.clear(); [o.data.materials.append(mat(u)) for u in used]
        idx=used.index(mn) if mn in used else 0
        for p in o.data.polygons: p.material_index=idx
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]
    if len(objs)>1: bpy.ops.object.join()
    o=bpy.context.object; o.name=name
    bpy.context.scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    col=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col)
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o)
    tris=sum(len(p.vertices)-2 for p in o.data.polygons)
    dims=tuple(round(d,2) for d in o.dimensions)
    ok = tris<=3000 and len(o.data.materials)<=3 and min(v.co.z for v in o.data.vertices)>=-1e-4
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    if ok:
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,name+".glb"),use_selection=True,export_format='GLB',export_apply=True)
    bpy.data.objects.remove(o); bpy.data.collections.remove(col)
    return dict(asset=name,tris=tris,dims=dims,ok=ok)
def j(a=0.15): return 1+R.uniform(-a,a)
items=[]
HERBS=[("Barkbalm","leaf","red"),("Pawmint","leaf","white"),("Howlroot","moss","dark"),("Snoutsage","leaf","cloth"),
 ("Furfern","moss","leaf"),("Wagwort","leaf","gold"),("Ironfang","moss","iron"),("Dewclaw","leaf","water"),
 ("Starkibble","leaf","star"),("Coppercap","moss","copper"),("Guardthistle","leaf","red"),("Dozeleaf","moss","cloth")]
def herb(v,leafc,flc):
    h=0.25*j(.3); b=[(0.06,0.06,h,0,0,0,"moss")]
    n=3+v
    for i in range(n):
        a=i*2*math.pi/n; r=0.09*j()
        b.append((0.1*j(),0.05,0.04,math.cos(a)*r,math.sin(a)*r,h*R.uniform(.3,.8),leafc))
    b.append((0.08,0.08,0.06,0,0,h,flc)); return b
for nm,l,f in HERBS:
    for v in range(5): items.append(("Prop_Herb_AMF_%s_V%d"%(nm,v+1),herb(v,l,f)))
    for v in range(5): items.append(("Item_Herb_AMF_%s_Bundle%d"%(nm,v+1),[(0.05,0.05,0.12,0,0,0,"cloth")]+[(0.04,0.04,0.12*j(),R.uniform(-.04,.04),R.uniform(-.04,.04),0.08,l) for _ in range(2+v)]+[(0.05,0.05,0.04,0,0,0.2,f)]))
TON=["Mend","Bulwark","Dash","Keen","Calm","Fury","Thick","Glow","Swim","Bond"]
for i,t in enumerate(TON):
    for k,c in enumerate(["red","star","gold","leaf"]):
        items.append(("Item_Tonic_AMF_%s_T%d"%(t,k+1),[(0.12,0.12,0.04,0,0,0,"glass"),(0.1,0.1,0.14+0.02*k,0,0,0.04,c),(0.05,0.05,0.06,0,0,0.18+0.02*k,"wood")]))
def well(v): s=1.4*j(.1); return [(s,s,0.8,0,0,0,"stone"),(s*.7,s*.7,0.05,0,0,0.75,"water"),(0.1,0.1,1.4,-s/2,0,0.8,"wood"),(0.1,0.1,1.4,s/2,0,0.8,"wood"),(s*1.3,s*.9,0.12,0,0,2.2,"dark")]
def spring(v): s=1.8*j(); return [(s,s,0.35,0,0,0,"stone"),(s*.8,s*.8,0.05,0,0,0.33,"water"),(0.4*j(),0.4,0.6*j(),s*.3,s*.3,0.3,"stone"),(0.3,0.3,0.3,-s*.35,0,0.3,"moss")]
def rain(v): s=1.6*j(); return [(0.12,0.12,1.6,x*s/2,y*s/2,0,"wood") for x in(-1,1) for y in(-1,1)]+[(s,s,0.06,0,0,1.6,"cloth"),(0.6,0.6,0.8,0,0,0,"copper")]
def still(v): return [(1.0,0.8,0.5,0,0,0,"stone"),(0.6,0.6,0.7*j(),0,0,0.5,"copper"),(0.9,0.12,0.08,0.4,0,1.0,"copper"),(0.4,0.4,0.4,0.8,0,0,"glass")]
def trough(v): L=1.2+0.3*v; return [(L,0.5,0.35,0,0,0,"wood"),(L*.9,0.38,0.04,0,0,0.3,"water")]
def cistern(v): s=1.5*j(); return [(s,s,1.6*j(),0,0,0,"stone"),(s*1.05,s*1.05,0.1,0,0,1.65,"wood"),(0.2,0.2,0.2,s/2,0,0.2,"copper")]
def filt(v): return [(0.8,0.8,0.4,0,0,0,"wood"),(0.7,0.7,0.2,0,0,0.4,"hay"),(0.7,0.7,0.2,0,0,0.6,"dark"),(0.7,0.7,0.1,0,0,0.8,"stone")]
for i in range(8): items+= [("Prop_Water_AMF_Well_V%d"%(i+1),well(i)),("Prop_Water_AMF_SpringBasin_V%d"%(i+1),spring(i)),("Prop_Water_AMF_RainCatcher_V%d"%(i+1),rain(i)),("Prop_Water_AMF_SolarStill_V%d"%(i+1),still(i)),("Prop_Water_AMF_Cistern_V%d"%(i+1),cistern(i)),("Prop_Water_AMF_Filter_V%d"%(i+1),filt(i))]
for i in range(12): items.append(("Prop_Water_AMF_Trough_V%d"%(i+1),trough(i%6)))
for i in range(8):
    m=["copper","wood","iron","stone"][i%4]
    items+= [("Prop_Water_AMF_PipeStraight_V%d"%(i+1),[(1.0,0.15,0.15,0,0,0,m)]),("Prop_Water_AMF_PipeElbow_V%d"%(i+1),[(0.5,0.15,0.15,0.25,0,0,m),(0.15,0.5,0.15,0,0.25,0,m)]),("Prop_Water_AMF_PipeTee_V%d"%(i+1),[(1.0,0.15,0.15,0,0,0,m),(0.15,0.5,0.15,0,0.25,0,m)])]
PC=["red","water","gold","cloth","leaf"]
for i in range(20): c=PC[i%5]; items.append(("Prop_Pet_AMF_Bowl_V%d"%(i+1),[(0.3*j(),0.3,0.1,0,0,0,c),(0.24,0.24,0.02,0,0,0.09,["water","hay"][i%2])]))
for i in range(20): c=PC[i%5]; s=0.6+0.05*(i%6); items.append(("Prop_Pet_AMF_Bed_V%d"%(i+1),[(s*1.3,s,0.12,0,0,0,"wood"),(s*1.2,s*.9,0.1,0,0,0.12,c),(s*1.3,0.1,0.2,0,s/2,0.12,c)]))
for i in range(15): s=1.0+0.1*(i%5); items.append(("Prop_Pet_AMF_Kennel_V%d"%(i+1),[(s,s*1.2,s*.8,0,0,0,"wood"),(s*1.1,s*1.3,0.15,0,0,s*.8,PC[i%5]),(s*.4,0.05,s*.5,0,-s*.6,0,"dark")]))
for i in range(15): items.append(("Prop_Pet_AMF_Feeder_V%d"%(i+1),[(0.5,0.4,0.15,0,0,0,"wood"),(0.3,0.3,0.6*j(),0,0.05,0.15,"glass"),(0.3,0.3,0.3,0,0.05,0.15,"hay")]))
TOY=[("Ball",lambda c:[(0.15,0.15,0.15,0,0,0,c)]),("Bone",lambda c:[(0.3,0.06,0.06,0,0,0,"white"),(0.08,0.12,0.08,0.15,0,0,"white"),(0.08,0.12,0.08,-0.15,0,0,"white")]),("Rope",lambda c:[(0.4,0.05,0.05,0,0,0,c),(0.08,0.08,0.08,0.2,0,0,"hay"),(0.08,0.08,0.08,-0.2,0,0,"hay")])]
for i in range(30): n,f=TOY[i%3]; items.append(("Prop_Pet_AMF_Toy%s_V%d"%(n,i//3+1),f(PC[i%5])))
for i in range(20): items.append(("Prop_Live_AMF_Fence_V%d"%(i+1),[(0.1,0.1,1.0,-0.5,0,0,"wood"),(0.1,0.1,1.0,0.5,0,0,"wood"),(1.0,0.06,0.08,0,0,0.7,["wood","dark"][i%2]),(1.0,0.06,0.08,0,0,0.35,"wood")]))
for i in range(15): items.append(("Prop_Live_AMF_HayBale_V%d"%(i+1),[(1.0*j(),0.6,0.5*j(),0,0,0,"hay"),(0.05,0.62,0.52,0.25,0,0,"dark")]))
for i in range(10): items.append(("Prop_Live_AMF_GoatShelter_V%d"%(i+1),[(2.0,1.6,1.2,0,0,0,"wood"),(2.2,1.8,0.15,0,0,1.2,PC[i%5]),(1.0,1.6,0.3,0,0,0,"hay")]))
for i in range(15): items.append(("Prop_Live_AMF_Gate_V%d"%(i+1),[(0.12,0.12,1.1,-0.75,0,0,"dark"),(0.12,0.12,1.1,0.75,0,0,"dark"),(1.4,0.06,0.9,0,0,0.1,["wood","iron","copper"][i%3])]))
for i in range(30): s=0.4+R.random()*1.4; items.append(("Prop_Dress_AMF_Rock_V%d"%(i+1),[(s,s*j(.4),s*.6*j(),0,0,0,"stone"),(s*.5,s*.5,s*.3,s*.2,0,s*.5,["stone","moss"][i%2])]))
for i in range(30): s=0.5+R.random(); items.append(("Prop_Dress_AMF_Bush_V%d"%(i+1),[(s,s,s*.7,0,0,0,"leaf"),(s*.6,s*.6,s*.4,0.1,0.1,s*.6,"moss")]+([(0.1,0.1,0.1,s*.4,0,s*.5,"red")] if i%3==0 else [])))
for i in range(20): s=0.5+0.1*(i%5); items.append(("Prop_Dress_AMF_Crate_V%d"%(i+1),[(s,s,s,0,0,0,"wood"),(s*1.02,0.06,s*1.02,0,0,0,"dark")]))
for i in range(16): items.append(("Prop_Dress_AMF_Lantern_V%d"%(i+1),[(0.12,0.12,1.4+0.1*(i%4),0,0,0,"dark"),(0.3,0.3,0.3,0,0,1.4+0.1*(i%4),"gold")]))
only = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
rep=[]
for n,b in items:
    rep.append(build(n,b))
json.dump(rep,open(os.path.join(OUT,"_amf_report.json"),"w"),indent=0)
print("AMF_DONE total=%d ok=%d"%(len(rep),sum(r["ok"] for r in rep)))
