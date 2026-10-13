# youtube-master polish pass v2: herbs, livestock, water, stations. Same names as batch 1 (re-export, rows -> READY).
# BRIEF: metres, origin bottom centre, -Y front, <=3 flat slots, blocky bevelled boxes, one collection per asset.
import bpy, os, json, math, random
OUT = r"C:\Users\730ri\projects\bot-team\art\glb"
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\polish_v5.json"
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

GLASS=mat("Glass","#BFE8F0",0.2)
TONC={"Major":"#F2D22E","Minor":"#3E8EDE","Sus":"#7CCB4A","Dim":"#8A5CE0","Aug":"#E8473C","Seventh":"#8FE3FF"}
for cn,cc in TONC.items():
    liq=mat("Tonic_"+cn,cc,1.5)
    for t in (1,2,3,4):
        def b(col,t=t,liq=liq):
            w=0.12+0.025*t
            box(col,w,w,0.18+0.02*t,0,0,0,GLASS,bev=0.25)
            box(col,w*0.8,w*0.8,(0.18+0.02*t)*0.7,0,0,0.01,liq,bev=0.25)
            box(col,w*0.4,w*0.4,0.08,0,0,0.18+0.02*t,GLASS,bev=0.1)
            box(col,w*0.45,w*0.45,0.05,0,0,0.26+0.02*t,WOOD,bev=0.2)
            for k in range(t): box(col,w*1.02,w*1.02,0.015,0,0,0.04+0.04*k,BRASS if False else liq,bev=0)
        asset(f"Item_YTM_Tonic_{cn}_T{t}","item","~0.3 m",b)
os.makedirs(os.path.dirname(LOG),exist_ok=True); json.dump(made,open(LOG,"w"),indent=1); print("MADE",len(made))
