# DiskSaver Island batch generator: blocky assets per BRIEF.md (m units, origin bottom centre, -Y front, flat colours)
import bpy, os, sys, json, math, random
ART = r"C:\Users\730ri\projects\bot-team\art"
OUT = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\glb"
os.makedirs(OUT,exist_ok=True)
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\batch1b.json"
random.seed(7)
def hexc(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1,)
MATS={}
def mat(name,h):
    if name in MATS: return MATS[name]
    m=bpy.data.materials.new(name); m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=hexc(h); MATS[name]=m; return m
def reset():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o,do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def box(col,sx,sy,sz,x,y,z,m):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z+sz/2))
    o=bpy.context.active_object; o.scale=(sx,sy,sz)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.data.materials.append(m)
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o); return o
def export(name,col):
    bpy.ops.object.select_all(action='DESELECT')
    for o in col.objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,name+".glb"),use_selection=True,export_format='GLB',export_apply=True)
made=[]
def asset(name,kind,size,build):
    reset(); col=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col)
    build(col); export(name,col)
    tris=sum(len(o.data.polygons)*2 for o in col.objects)
    vs=[v.co for o in col.objects for v in o.data.vertices]
    dims=[max(v[i] for v in vs)-min(v[i] for v in vs) for i in range(3)]
    k=name.split("_",1)[0]; os.makedirs(os.path.join(ART,k),exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,k,name+".blend"),copy=True)
    made.append({"asset":name,"kind":kind,"size":size,"tris":tris,"max_dim_m":round(max(dims),2)})
# --- herbs: compression family, 10 species x 3 stages
HERBS=[("CacheLeaf","#4FD18B"),("BufferBloom","#4FA3FF"),("OverclockThorn","#FF8A2A"),("DefragMoss","#B8E05A"),("SwapRoot","#C25BFF"),
       ("ParityPetal","#FFE45C"),("ChecksumClover","#2FBF9F"),("LatencyLily","#9FC8FF"),("ZipVine","#FF5C8A"),("ArchiveSage","#8FA88F")]
STEM=mat("DS_Stem","#3E7A2E"); SOIL=mat("DS_Soil","#5A3B22")
for hn,hc in HERBS:
    m=mat("DS_"+hn,hc)
    for st,h in ((1,0.15),(2,0.35),(3,0.6)):
        def b(col,h=h,m=m,st=st):
            box(col,0.06,0.06,h,0,0,0,STEM)
            for i in range(st+1):
                a=i*2*math.pi/(st+1); r=0.08+0.04*st
                box(col,0.12,0.12,0.06,r*math.cos(a),r*math.sin(a),h*0.5+0.05*i,m)
            box(col,0.14*st/2+0.1,0.14*st/2+0.1,0.1,0,0,h,m)
        asset(f"Prop_DS_Herb_{hn}_S{st}","prop",f"~{h+0.1:.2f} m",b)
# --- herb item pickups (10)
for hn,hc in HERBS:
    m=mat("DS_"+hn,hc)
    asset(f"Item_DS_Herb_{hn}","item","~0.3 m",lambda col,m=m:(box(col,0.2,0.2,0.08,0,0,0,m),box(col,0.06,0.06,0.18,0,0,0.08,STEM)))
# --- livestock (5)
LIV=[("ByteHen","#F2EEE0",0.5),("MossGoat","#7E8F5A",1.0),("TidePig","#E7A0A0",0.8),("CacheCow","#2E2E36",1.6),("DriftDuck","#D9C24A",0.45)]
for ln,lc,s in LIV:
    m=mat("DS_"+ln,lc); dk=mat("DS_Dark","#2A2A2A")
    def b(col,s=s,m=m,dk=dk):
        leg=0.3*s
        for x in (-0.25*s,0.25*s):
            for y in (-0.3*s,0.3*s): box(col,0.12*s,0.12*s,leg,x,y,0,dk)
        box(col,0.7*s,1.0*s,0.5*s,0,0,leg,m)
        box(col,0.4*s,0.35*s,0.35*s,0,-0.6*s,leg+0.35*s,m)
    asset(f"Mob_DS_{ln}","mob",f"~{s:.1f} m",b)
# --- crops / feed (5)
for cn,cc in (("Clover","#3FAF4A"),("Groat","#D8B65A"),("Kelpweed","#2F7F6F"),("Bitroot","#B0304A"),("Spudlet","#C9A36A")):
    m=mat("DS_"+cn,cc)
    asset(f"Prop_DS_Crop_{cn}","prop","~0.5 m",lambda col,m=m:(box(col,0.9,0.9,0.1,0,0,0,SOIL),[box(col,0.15,0.15,0.4,x,y,0.1,m) for x in (-0.25,0.25) for y in (-0.25,0.25)]))
# --- food (5)
for fn,fc in (("Egg","#F4EFE2"),("GoatMilk","#FFFFFF"),("Stew","#A0522D"),("HerbTea","#6FBF73"),("Bread","#D6A35C")):
    m=mat("DS_F_"+fn,fc)
    asset(f"Item_DS_Food_{fn}","item","~0.25 m",lambda col,m=m:box(col,0.22,0.22,0.22,0,0,0,m))
# --- farm structures (5)
WOOD=mat("DS_Wood","#8A5A32"); STONE=mat("DS_Stone","#8C8C94"); GLOW=mat("DS_Glow","#7FE3FF")
asset("Bld_DS_Coop","building","~2 m",lambda col:(box(col,2,2,1.4,0,0,0,WOOD),box(col,2.2,2.2,0.3,0,0,1.4,STONE)))
asset("Prop_DS_Trough","prop","~0.6 m",lambda col:(box(col,1.6,0.6,0.5,0,0,0,WOOD),box(col,1.4,0.4,0.1,0,0,0.45,mat("DS_Water","#3A7BD5"))))
asset("Prop_DS_FencePen","prop","~1 m",lambda col:[box(col,0.12,0.12,1.0,x,0,0,WOOD) for x in (-1.5,-0.5,0.5,1.5)]+[box(col,3.2,0.08,0.1,0,0,z,WOOD) for z in (0.4,0.8)])
asset("Prop_DS_HerbCompressor","prop","~1.4 m",lambda col:(box(col,1,1,0.9,0,0,0,STONE),box(col,0.5,0.5,0.5,0,0,0.9,GLOW)))
asset("Prop_DS_DryingRack","prop","~1.6 m",lambda col:(box(col,0.1,0.1,1.6,-0.7,0,0,WOOD),box(col,0.1,0.1,1.6,0.7,0,0,WOOD),box(col,1.5,0.08,0.08,0,0,1.5,WOOD)))
os.makedirs(os.path.dirname(LOG),exist_ok=True)
json.dump(made,open(LOG,"w"),indent=1)
print("MADE",len(made))
