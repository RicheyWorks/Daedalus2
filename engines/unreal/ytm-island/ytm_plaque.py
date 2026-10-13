# youtube-master hero props v1: herbs, livestock, water, stations. Same names as batch 1 (re-export, rows -> READY).
# BRIEF: metres, origin bottom centre, -Y front, <=3 flat slots, blocky bevelled boxes, one collection per asset.
import bpy, os, json, math, random
OUT = r"C:\Users\730ri\projects\bot-team\art\glb"
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\plaque_v1.json"
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

FONT=r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\fonts\plex-Bold.ttf"
INK=mat("Ink","#1c1915"); CREAM=mat("Cream","#e6dcc4"); BLACK=mat("Black","#0b0b0b"); WHITE=mat("White","#ffffff",0.6)
def text(col,s,size,x,y,z,m,rx=1.5708,depth=0.02):
    bpy.ops.object.text_add(location=(x,y,z),rotation=(rx,0,0)); t=bpy.context.active_object
    t.data.body=s; t.data.size=size; t.data.extrude=depth; t.data.resolution_u=1; t.data.align_x='CENTER'
    try: t.data.font=bpy.data.fonts.load(FONT,check_existing=True)
    except Exception: pass
    bpy.ops.object.convert(target='MESH'); o=bpy.context.active_object
    o.data.materials.clear(); o.data.materials.append(m)
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o); return o

LINES=["a fragment of one shattered planet.","it kept its spring.","the arks carried what they could:","seeds, animals, a few songs."]
def plaque(col):
    box(col,1.6,0.3,0.9,0,0,0,STONE,bev=0.04)
    box(col,1.4,0.04,0.7,0,-0.16,0.1,BLACK)
    for i,t in enumerate(LINES): text(col,t,0.075,0,-0.19,0.68-i*0.15,WHITE,depth=0.0)
asset("Prop_YTM_LorePlaque","prop","~1.6 m",plaque)
os.makedirs(os.path.dirname(LOG),exist_ok=True); json.dump(made,open(LOG,"w"),indent=1); print("MADE",len(made))
