# Headless Blender: build 500 Prometheus Island items (seeded), export one FBX each + manifest.json
import bpy, bmesh, random, math, json, os, sys
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"fbx"); os.makedirs(OUT,exist_ok=True)
START=int(sys.argv[sys.argv.index("--")+1]) if "--" in sys.argv else 0
COUNT=int(sys.argv[sys.argv.index("--")+2]) if "--" in sys.argv else 500
HERBS=["Yarrow","Plantain","Chamomile","Valerian","Feverfew","Mint","Elderflower","Sage","Comfrey","Willow","Hypericum","Nettle"]
PC=["C","Cs","D","Ds","E","F","Fs","G","Gs","A","As","B"]
CROPS=["Barley","Oat","Flax","Pea","Turnip","Kale","Squash","Bean","Clover","Lucerne","Millet","Buckwheat"]
spec=[]
for i,h in enumerate(HERBS):
    for st in ("Sprout","Bloom","Seed"):
        for v in range(3): spec.append(("Herb_%s_%s_%s_V%d"%(PC[i],h,st,v),"herb",dict(stage=st,pc=i)))
W=[("StreamSeg",40),("SpringBasin",4),("RainCatcher",12),("Cistern",6),("StillPart",10),("Pipe",16),("Trough",12)]
for n,c in W:
    for v in range(c): spec.append(("Water_%s_V%02d"%(n,v),"water",dict(kind=n)))
L=[("PenFence",20),("Feeder",10),("HayBale",12),("Shelter",8),("SaltLick",4),("Nestbox",6)]
for n,c in L:
    for v in range(c): spec.append(("Stock_%s_V%02d"%(n,v),"stock",dict(kind=n)))
for c in CROPS:
    for st in ("Sprout","Grown","Ripe"): spec.append(("Crop_%s_%s"%(c,st),"crop",dict(stage=st)))
for v in range(60): spec.append(("ToneStone_%s_V%02d"%(PC[v%12],v),"tone",dict(pc=v%12)))
for v in range(60): spec.append(("Rock_Basalt_V%02d"%v,"rock",{}))
for v in range(30): spec.append(("Tree_Spruce_V%02d"%v,"tree",{}))
for v in range(20): spec.append(("Fungus_Shelf_V%02d"%v,"fungus",{}))
for n,c in [("Vinyl",12),("PressPlate",4),("Speaker",6),("Lantern",4)]:
    for v in range(c): spec.append(("Music_%s_V%02d"%(n,v),"music",dict(kind=n)))
assert len(spec)==500, len(spec)

def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
def prim(kind,loc=(0,0,0),scale=(1,1,1),rot=(0,0,0),**kw):
    f={"cube":bpy.ops.mesh.primitive_cube_add,"cyl":bpy.ops.mesh.primitive_cylinder_add,"cone":bpy.ops.mesh.primitive_cone_add,
       "ico":bpy.ops.mesh.primitive_ico_sphere_add,"uv":bpy.ops.mesh.primitive_uv_sphere_add,"torus":bpy.ops.mesh.primitive_torus_add}[kind]
    f(location=loc,rotation=rot,**kw); o=bpy.context.active_object; o.scale=scale; return o
def jitter(o,R,amt):
    for v in o.data.vertices: v.co.x+=R.uniform(-amt,amt); v.co.y+=R.uniform(-amt,amt); v.co.z+=R.uniform(-amt,amt)
def build(name,cat,p,R):
    s=R.uniform(0.85,1.2)
    if cat=="herb":
        h={"Sprout":0.15,"Bloom":0.45,"Seed":0.55}[p["stage"]]*s
        prim("cyl",(0,0,h/2),(0.012,0.012,h/2),vertices=6)
        for j in range(3+p["pc"]%4):
            a=j*2.39; prim("ico",(0.06*math.cos(a),0.06*math.sin(a),h*R.uniform(0.3,0.8)),(0.05,0.02,0.015),(0,0,a),subdivisions=1)
        if p["stage"]!="Sprout": prim("uv",(0,0,h),(0.04,0.04,0.03),segments=8,ring_count=6)
    elif cat=="water":
        k=p["kind"]
        if k=="StreamSeg": o=prim("cube",(0,0,-0.2),(2.5*s,0.9*s,0.25)); jitter(o,R,0.05)
        elif k=="SpringBasin": prim("torus",(0,0,0.2),(1.6*s,1.6*s,1.0),major_radius=1,minor_radius=0.25); prim("cyl",(0,0,0.05),(1.5*s,1.5*s,0.05),vertices=24)
        elif k=="RainCatcher": prim("cone",(0,0,1.6),(1.2*s,1.2*s,0.3),(math.pi,0,0),vertices=16); prim("cyl",(0,0,0.7),(0.1,0.1,0.7),vertices=8); prim("cyl",(0,0,0.25),(0.5,0.5,0.25),vertices=16)
        elif k=="Cistern": prim("cyl",(0,0,1.0),(1.4*s,1.4*s,1.0),vertices=24); prim("cone",(0,0,2.3),(1.5*s,1.5*s,0.3),vertices=24)
        elif k=="StillPart": prim("cube",(0,0,0.3),(1.0*s,0.7,0.3)); prim("cube",(0,0,0.75),(1.0*s,0.7,0.02),(0.15,0,0))
        elif k=="Pipe": prim("cyl",(0,0,0),(0.08,0.08,1.5*s),(0,math.pi/2,0),vertices=10)
        else: prim("cube",(0,0,0.25),(1.2*s,0.4,0.25))
    elif cat=="stock":
        k=p["kind"]
        if k=="PenFence":
            for x in (-1,1): prim("cube",(x*1.2,0,0.5),(0.06,0.06,0.5))
            for z in (0.35,0.75): prim("cube",(0,0,z),(1.25,0.03,0.05))
        elif k=="Feeder": prim("cube",(0,0,0.4),(0.8*s,0.35,0.15)); prim("cube",(0,0,0.15),(0.7,0.3,0.15))
        elif k=="HayBale": prim("cyl",(0,0,0.6),(0.6*s,0.6*s,0.6),(math.pi/2,0,0),vertices=16)
        elif k=="Shelter": prim("cube",(0,0,0.9),(1.8*s,1.4,0.9)); prim("cube",(0,0,2.0),(2.0*s,1.6,0.08),(0.1,0,0))
        elif k=="SaltLick": o=prim("cube",(0,0,0.15),(0.2,0.2,0.15)); jitter(o,R,0.03)
        else: prim("cube",(0,0,0.25),(0.4,0.4,0.25))
    elif cat=="crop":
        h={"Sprout":0.12,"Grown":0.5,"Ripe":0.8}[p["stage"]]*s
        for j in range(5): prim("cone",(R.uniform(-.2,.2),R.uniform(-.2,.2),h/2),(0.04,0.04,h/2),vertices=5)
    elif cat=="tone":
        h=1.2+0.25*(12-p["pc"])*s  # lower pitch = taller stone (longer column, darker tone)
        o=prim("cyl",(0,0,h/2),(0.35*s,0.3*s,h/2),vertices=7); jitter(o,R,0.04)
        prim("torus",(0,0,h*0.7),(0.42*s,0.42*s,1),major_radius=1,minor_radius=0.04)
    elif cat=="rock": o=prim("ico",(0,0,0.4*s),(R.uniform(.5,1.6)*s,R.uniform(.5,1.4),R.uniform(.3,.9)),subdivisions=2); jitter(o,R,0.12)
    elif cat=="tree":
        h=R.uniform(5,9)*s; prim("cyl",(0,0,h/2),(0.18,0.18,h/2),vertices=8)
        for j in range(4): prim("cone",(0,0,h*0.35+j*h*0.15),(1.4-j*0.3,1.4-j*0.3,h*0.18),vertices=10)
    elif cat=="fungus":
        for j in range(3): prim("cyl",(0,0,0.2+j*0.18),(0.3-j*0.06,0.22-j*0.04,0.03),vertices=12)
    else:
        k=p["kind"]
        if k=="Vinyl": prim("cyl",(0,0,0.01),(0.15,0.15,0.005),vertices=32); prim("cyl",(0,0,0.012),(0.05,0.05,0.004),vertices=16)
        elif k=="PressPlate": prim("cyl",(0,0,0.5),(0.5,0.5,0.5),vertices=24); prim("cyl",(0,0,1.4),(0.6,0.6,0.08),vertices=24); prim("cube",(0,0,2.0),(0.15,0.15,0.6))
        elif k=="Speaker": prim("cube",(0,0,0.6),(0.4,0.35,0.6)); prim("cyl",(0,-0.36,0.4),(0.25,0.25,0.02),(math.pi/2,0,0),vertices=20)
        else: prim("cyl",(0,0,0.9),(0.04,0.04,0.9),vertices=6); prim("uv",(0,0,1.85),(0.15,0.15,0.18),segments=10,ring_count=6)
    bpy.ops.object.select_all(action="SELECT"); bpy.context.view_layer.objects.active=bpy.context.selected_objects[0]
    bpy.ops.object.join(); o=bpy.context.active_object; o.name=name; o.data.name=name
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    bpy.ops.object.shade_flat()
    return o
man=[]
for idx,(name,cat,p) in enumerate(spec[START:START+COUNT],START):
    clear(); R=random.Random(15000+idx); o=build(name,cat,p,R)
    tris=sum(len(f.vertices)-2 for f in o.data.polygons)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT,name+".fbx"),use_selection=True,apply_scale_options="FBX_SCALE_ALL",mesh_smooth_type="FACE",bake_space_transform=True)
    man.append(dict(i=idx,name=name,cat=cat,tris=tris,**p))
json.dump(man,open(os.path.join(os.path.dirname(OUT),"manifest_%03d.json"%START),"w"),indent=0)
print("BUILT",START,len(man))
