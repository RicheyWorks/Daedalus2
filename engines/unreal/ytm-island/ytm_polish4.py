# youtube-master polish pass v4 (scenery kit): herbs, livestock, water, stations. Same names as batch 1 (re-export, rows -> READY).
# BRIEF: metres, origin bottom centre, -Y front, <=3 flat slots, blocky bevelled boxes, one collection per asset.
import bpy, os, json, math, random
OUT = r"C:\Users\730ri\projects\bot-team\art\glb"
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\polish_v4.json"
def hexc(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1,)
MATS={}
def mat(n,h,em=0.0):
    n="YTM_"+n
    if n in MATS: return MATS[n]
    m=bpy.data.materials.new(n); m.use_nodes=True; p=m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value=hexc(h); p.inputs["Roughness"].default_value=0.8
    if em: p.inputs["Emission Color"].default_value=hexc(h); p.inputs["Emission Strength"].default_value=em
    MATS[n]=m; return m
def reset():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o,do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes): bpy.data.meshes.remove(me)
def box(col,sx,sy,sz,x,y,z,m,rz=0,rx=0,bev=0.15,name=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z+sz/2),rotation=(rx,0,rz))
    o=bpy.context.active_object; o.scale=(sx,sy,sz); bpy.ops.object.transform_apply(scale=True,rotation=True)
    if bev:
        b=o.modifiers.new("bev","BEVEL"); b.width=min(sx,sy,sz)*bev; b.segments=1
    o.data.materials.append(m)
    if name: o.name=name
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o); return o
made=[]
def asset(name,kind,size,build):
    reset(); col=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col)
    build(col)
    keep=[]
    for o in col.objects:
        m=o.data.materials[0]
        if m not in keep and len(keep)<3: keep.append(m)
        if m not in keep: o.data.materials[0]=keep[0]  # BRIEF: max 3 slots
    bpy.ops.object.select_all(action='DESELECT')
    for o in col.objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,name+".glb"),use_selection=True,export_format='GLB',export_apply=True)
    made.append({"asset":name,"kind":kind,"size":size})
WOOD=mat("Wood","#8A5A32"); STONE=mat("Stone","#8C8C94"); DARK=mat("Dark","#2A2A2A"); SOIL=mat("Soil","#5A3B22")
WATER=mat("Water","#3A9BD5",0.3); CLEAN=mat("CleanWater","#8FE3FF",0.8); STEM=mat("Stem","#3E7A2E"); BRASS=mat("Brass","#C9A040")

import sys
BATCH=int(os.environ.get("YTM_BATCH","0"))  # 0 = all, 1..3 = thirds
names=[a["asset"] for a in json.load(open(r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\batch1.json")) if any(k in a["asset"] for k in ("_Rock_","_Cliff_","_Boulder_","_Stump_","_Bush_","_Log_"))]
if BATCH: names=names[(BATCH-1)*len(names)//3:BATCH*len(names)//3]
ROCKS=[("#8C8C94","#6E6A64"),("#A89F8C","#7A705E"),("#5A6470","#3E4650"),("#7A8A70","#5A6A50"),("#B0A8A0","#8A8078")]
MOSS=mat("Moss","#5E8A3A"); BARK=mat("Bark","#5A3E26"); RING=mat("Ring","#C8A070"); BUSH=mat("Bush","#3F7A2E"); BUSH2=mat("Bush2","#5A9A3E"); BERRY=mat("Berry","#C03A4A")
for name in names:
    n=int(name.rsplit("_K",1)[1]); kind=name.split("_")[2]; r=random.Random(n*7919)
    a_,b_=ROCKS[n%5]; m1=mat(f"Rock{n%5}a",a_); m2=mat(f"Rock{n%5}b",b_)
    def b(col,kind=kind,r=r,m1=m1,m2=m2):
        if kind in("Rock","Boulder"):
            s=r.uniform(0.6,1.6) if kind=="Rock" else r.uniform(1.8,4.0)
            box(col,s,s*r.uniform(0.7,1.0),s*r.uniform(0.45,0.7),0,0,0,m1,rz=r.uniform(0,1.5),bev=0.2)
            for j in range(r.randint(2,4)):
                w=s*r.uniform(0.3,0.6); box(col,w,w*r.uniform(0.6,1),w*r.uniform(0.4,0.8),r.uniform(-0.4,0.4)*s,r.uniform(-0.4,0.4)*s,s*r.uniform(0.1,0.4),m2,rz=r.uniform(0,3),rx=r.uniform(-0.2,0.2),bev=0.2)
            if r.random()<0.6: box(col,s*0.6,s*0.5,0.06*s,r.uniform(-0.1,0.1)*s,0,s*r.uniform(0.45,0.65),MOSS,rz=r.uniform(0,3),bev=0.3)
        elif kind=="Cliff":
            h=r.uniform(4,10); w=r.uniform(3,7); z=0
            for j in range(r.randint(4,6)):
                lh=h/5*r.uniform(0.8,1.2); ww=w*(1-0.1*j)*r.uniform(0.85,1.05)
                box(col,ww,ww*r.uniform(0.5,0.8),lh,r.uniform(-0.3,0.3),r.uniform(-0.3,0.3),z,m1 if j%2==0 else m2,rz=r.uniform(-0.2,0.2),bev=0.08); z+=lh
            for j in range(3): box(col,w*0.3,w*0.25,0.15,r.uniform(-w/3,w/3),-w*0.3,r.uniform(0.5,z-0.5),MOSS,bev=0.3)
            box(col,w*0.7,w*0.5,0.2,0,0,z,MOSS,bev=0.3)
        elif kind=="Stump":
            d=r.uniform(0.5,1.1); h=r.uniform(0.4,0.9)
            box(col,d,d,h,0,0,0,BARK,bev=0.15); box(col,d*0.85,d*0.85,0.04,0,0,h,RING,bev=0)
            for k in range(4): box(col,d*0.5,0.18*d,0.18*d,d*0.45*math.cos(k*1.571+0.4),d*0.45*math.sin(k*1.571+0.4),0,BARK,rz=k*1.571+0.4,bev=0.2)
            if r.random()<0.5: box(col,0.12,0.12,0.15,d*0.2,0,h,mat("Shroom","#E8D0A0"),bev=0.3)
        elif kind=="Bush":
            s=r.uniform(0.6,1.5)
            for j in range(r.randint(4,7)):
                w=s*r.uniform(0.4,0.7); box(col,w,w,w*0.8,r.uniform(-0.3,0.3)*s,r.uniform(-0.3,0.3)*s,r.uniform(0,0.4)*s,BUSH if j%2 else BUSH2,rz=r.uniform(0,1.5),bev=0.3)
            if r.random()<0.5: [box(col,0.07,0.07,0.07,r.uniform(-0.35,0.35)*s,r.uniform(-0.35,0.35)*s,s*r.uniform(0.4,0.7),BERRY,bev=0) for _ in range(6)]
        else:
            L=r.uniform(1.5,4); d=r.uniform(0.3,0.6); ang=r.uniform(0,3)
            box(col,L,d,d,0,0,0,BARK,rz=ang,bev=0.2)
            for e in (-1,1): box(col,0.04,d*0.85,d*0.85,e*L/2*math.cos(ang),e*L/2*math.sin(ang),d*0.07,RING,rz=ang,bev=0)
            box(col,L*0.4,d*0.6,0.05,0.1,0,d,MOSS,rz=ang,bev=0.3)
            if r.random()<0.5: box(col,0.6,0.1,0.1,0,0,d*0.5,BARK,rz=ang+1.2,bev=0.2)
    asset(name,"prop","~1-10 m",b)
os.makedirs(os.path.dirname(LOG),exist_ok=True)
LOG=LOG.replace(".json",f"_b{BATCH}.json"); json.dump(made,open(LOG,"w"),indent=1); print("MADE",len(made))
