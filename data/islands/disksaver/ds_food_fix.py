# DiskSaver Island batch generator: blocky assets per BRIEF.md (m units, origin bottom centre, -Y front, flat colours)
import bpy, os, sys, json, math, random
ART = r"C:\Users\730ri\projects\bot-team\art"
OUT = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\glb"
os.makedirs(OUT,exist_ok=True)
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\batch1c_food.json"
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

ACC=mat("DS_Accent","#7A5230"); TOP=mat("DS_TopCream","#FFF6E0")
for fn,fc in (("Egg","#F4EFE2"),("GoatMilk","#FFFFFF"),("Stew","#A0522D"),("HerbTea","#6FBF73"),("Bread","#D6A35C")):
    m=mat("DS_F_"+fn,fc)
    asset(f"Item_DS_Food_{fn}","item","~0.3 m",lambda col,m=m:(box(col,0.22,0.22,0.2,0,0,0,m),box(col,0.16,0.16,0.05,0,0,0.2,TOP),box(col,0.26,0.26,0.03,0,0,0,ACC)))
json.dump(made,open(LOG,"w"),indent=1)
print("MADE",len(made))
