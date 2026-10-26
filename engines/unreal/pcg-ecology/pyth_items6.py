# island:pythagoras (Wild Biomes) procedural item batch. Blender 4.3, run: blender -b --python pyth_items.py
import bpy, random, os, json, math, sys
OUT = r"C:\Users\730ri\projects\bot-team\art\glb\pythagoras"
os.makedirs(OUT, exist_ok=True)
R = random.Random(42)
P = dict(wood=(0.55,0.36,0.2),dark=(0.3,0.2,0.12),stone=(0.55,0.55,0.58),water=(0.25,0.6,0.95),
 leaf=(0.3,0.7,0.25),moss=(0.35,0.55,0.25),copper=(0.78,0.44,0.23),iron=(0.79,0.7,0.61),hay=(0.9,0.8,0.4),
 red=(0.8,0.2,0.2),cloth=(0.75,0.6,0.85),glass=(0.7,0.9,1.0),gold=(0.95,0.76,0.19),star=(0.5,0.89,1.0),white=(0.95,0.95,0.9),bark=(0.35,0.25,0.18),pine=(0.15,0.4,0.2),birch=(0.9,0.9,0.85),willow=(0.5,0.7,0.35),berry=(0.3,0.1,0.4),honey=(0.95,0.65,0.1),soil=(0.3,0.22,0.15),flower=(0.95,0.5,0.7),purple=(0.6,0.3,0.8),yellow=(1.0,0.9,0.2))
mats={}
def mat(n):
    if n in mats: return mats[n]
    m=bpy.data.materials.new("M_PYT_"+n); c=P[n] if isinstance(n,str) and n in P else n
    m.diffuse_color=(*c,1); m.use_nodes=True; m.node_tree.nodes["Principled BSDF"].inputs[0].default_value=(*c,1)
    mats[n]=m; return m
def build(name, boxes):
    # boxes: (sx,sy,sz, x,y,z_bottom, matname)
    bpy.ops.object.select_all(action='DESELECT')
    objs=[]; used=[]
    for sx,sy,sz,x,y,z,mn in boxes:
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z+sz/2)) if mn[:1]!="~" and mn[:1]!="^" else (bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=0.5,depth=1,location=(x,y,z+sz/2)) if mn[0]=="~" else bpy.ops.mesh.primitive_cone_add(vertices=8,radius1=0.5,depth=1,location=(x,y,z+sz/2))); mn=mn.lstrip("~^"); o=bpy.context.object
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
# batch 6: chapter 9 "Keystone Beaver"
items=[]; ST=["flower","leaf","berry","pine"]
for v in range(6): items.append(("Prop_Live_PYT_BeaverLodge_V%d"%(v+1),[(2.4*j(),2.0*j(),0.3,0,0,0,"~moss"),(2.0,1.6,1.0,0,0,0.3,"^bark")]+[(0.1,0.1,1.2*j(),R.uniform(-.8,.8),R.uniform(-.6,.6),0.4,"~bark") for _ in range(5)]))
for v in range(6): items.append(("Prop_Ground_PYT_ReedBed_V%d"%(v+1),[(2.0*j(),1.4*j(),0.05,0,0,0,"~water")]+[(0.04,0.04,1.2*j(),R.uniform(-.9,.9),R.uniform(-.6,.6),0.05,"~"+["willow","hay","leaf"][v%3]) for _ in range(9)]))
for v in range(6): items.append(("Prop_Dress_PYT_FloodMarker_V%d"%(v+1),[(0.1,0.1,1.8,0,0,0,"~bark")]+[(0.25,0.03,0.08,0.1,0,0.3+0.3*k,["white","red"][k%2]) for k in range(5)]))
for v in range(6): items.append(("Prop_Live_PYT_Frog_V%d"%(v+1),[(0.25,0.2,0.1,0,0,0,["leaf","moss","willow"][v%3]),(0.08,0.08,0.08,0.06,0.07,0.1,"~white"),(0.08,0.08,0.08,0.06,-0.07,0.1,"~white")]))
for v in range(6): items.append(("Prop_Food_PYT_WillowBark_V%d"%(v+1),[(0.6*j(),0.12,0.12,0,0.15*k,0,"~willow") for k in range(3)]))
rep=[build(n,b) for n,b in items]
print("PYT6_DONE total=%d ok=%d"%(len(rep),sum(r["ok"] for r in rep)))
