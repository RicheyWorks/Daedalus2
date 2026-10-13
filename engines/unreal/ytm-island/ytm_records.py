# youtube-master hero props v1: herbs, livestock, water, stations. Same names as batch 1 (re-export, rows -> READY).
# BRIEF: metres, origin bottom centre, -Y front, <=3 flat slots, blocky bevelled boxes, one collection per asset.
import bpy, os, json, math, random
OUT = r"C:\Users\730ri\projects\bot-team\art\glb"
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\records_v1.json"
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

RECS=[('AndeanPanPipes', '#a6a193'), ('AppalachianHighLonesome', '#969489'), ('ArabicMaqam', '#a19a89'), ('ArabicTakht', '#9e9a87'), ('ArmenianDuduk', '#a3a599'), ('AustralianBushBand', '#a49681'), ('BalineseKecak', '#c4bcaa'), ('BalkanBrass', '#beb5a8'), ('BaroqueCounterpoint', '#959280'), ('BulgarianWomensChoir', '#bbb99d'), ('CairoOrchestra', '#a8b2b9'), ('CarpathianTrembita', '#a99c85')]
def disc(col,x,y,z,rx,c):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=0.3,depth=0.02,location=(x,y,z),rotation=(rx,0,0)); r=bpy.context.active_object; r.data.materials.append(BLACK)
    for cc in r.users_collection: cc.objects.unlink(r)
    col.objects.link(r)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=0.11,depth=0.025,location=(x,y,z),rotation=(rx,0,0)); l=bpy.context.active_object; l.data.materials.append(c)
    for cc in l.users_collection: cc.objects.unlink(l)
    col.objects.link(l)
for nm,c in RECS:
    def b(col,nm=nm,c=c):
        disc(col,0,0,0.31,1.5708,mat("Label"+nm,c)); box(col,0.2,0.1,0.02,0,0,0,WOOD)
    asset(f"Item_YTM_Record_{nm}","item","~0.6 m",b)
# record rack: open wood crate with 12 sleeves (cream) + 3 black records peeking out
def rack(col):
    box(col,1.4,0.7,0.06,0,0,0,WOOD)
    for x in (-0.7,0.7): box(col,0.06,0.7,0.7,x,0,0.06,WOOD)
    box(col,1.4,0.06,0.5,0,0.32,0.06,WOOD)
    for i in range(12): box(col,0.025,0.62,0.62,-0.6+i*0.109,0,0.1,CREAM)
    for x in (-0.38,0.0,0.38): box(col,0.02,0.6,0.08,x+0.05,0,0.7,BLACK)
asset("Prop_YTM_RecordRack","prop","~1.4 m",rack)
os.makedirs(os.path.dirname(LOG),exist_ok=True); json.dump(made,open(LOG,"w"),indent=1); print("MADE",len(made))
