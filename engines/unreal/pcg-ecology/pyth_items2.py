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
items=[]
# Climax Seed adventure props
for v in range(5): items.append(("Item_Quest_PYT_ClimaxSeed_V%d"%(v+1),[(0.12,0.12,0.14,0,0,0,"~bark"),(0.13,0.13,0.05,0,0,0.12,"^"+["gold","star","bark","moss","honey"][v])]))
for v in range(6):
    s=1.6+0.25*v; H=9*s
    items.append(("Prop_Tree_PYT_GreatOak_V%d"%(v+1),[(1.2*s,1.2*s,H*.5,0,0,0,"~bark")]+[(0.5*s,0.5*s,2.2*s,1.1*s*math.cos(a),1.1*s*math.sin(a),0,"~bark") for a in (0,2.1,4.2)]+[(6*s*j(),6*s*j(),H*.35,0,0,H*.45,"~leaf"),(4*s,4*s,H*.3,1.5*s,0,H*.7,"~moss"),(3.5*s,3.5*s,H*.25,-1.4*s,1,H*.75,"~leaf")]))
for v in range(6): items.append(("Prop_Dress_PYT_OldStump_V%d"%(v+1),[(1.6+0.2*v,1.6+0.2*v,0.8*j(),0,0,0,"~bark"),(1.4,1.4,0.02,0,0,0.8,"~hay"),(0.4,0.4,0.3,0.9,0,0,"moss")]))
for v in range(6): items.append(("Tool_PYT_FireweedTorch_V%d"%(v+1),[(0.05,0.05,0.8,0,0,0,"~bark"),(0.12,0.12,0.18,0,0,0.8,"^"+["red","yellow","flower"][v%3])]))
for k,c in (("Pioneer","flower"),("Meadow","leaf"),("Scrub","berry"),("Forest","bark"),("Riparian","willow")):
    for v in range(4): items.append(("Item_Seed_PYT_%sPouch_V%d"%(k,v+1),[(0.14,0.14,0.16,0,0,0,"~cloth"),(0.08,0.08,0.05,0,0,0.16,"^"+c)]))
for v in range(6): items.append(("Prop_Dress_PYT_AshScar_V%d"%(v+1),[(3*j(.3),2.5*j(.3),0.03,0,0,0,"dark"),(0.3,0.3,0.15,0.5,0.3,0,"dark"),(0.2,0.2,0.4,-0.6,0.2,0,"^flower")]))
for v in range(6): items.append(("Prop_Dress_PYT_WindthrowLog_V%d"%(v+1),[(4*j(),0.6,0.6,0,0,0,"bark"),(1.4,1.4,1.2,2.2,0,0,"~soil")]))
for v in range(5): items.append(("Prop_Live_PYT_Frog_V%d"%(v+1),[(0.12,0.1,0.06,0,0,0,"leaf"),(0.04,0.04,0.04,0.04,0.03,0.05,"yellow"),(0.04,0.04,0.04,0.04,-0.03,0.05,"yellow")]))
for v in range(5): items.append(("Prop_Live_PYT_Deer_V%d"%(v+1),[(1.1,0.35,0.5,0,0,0.75,"bark")]+[(0.08,0.08,0.75,x,y,0,"dark") for x in(-.4,.4) for y in(-.12,.12)]+[(0.25,0.18,0.25,0.6,0,1.15,"bark"),(0.03,0.2,0.3,0.6,0,1.4,"dark")]))
for v in range(5): items.append(("Prop_Sign_PYT_Chapter_V%d"%(v+1),[(0.1,0.1,1.4,0,0,0,"~bark"),(0.9,0.06,0.5,0,0,1.1,["leaf","flower","berry","pine","willow"][v])]))
rep=[build(n,b) for n,b in items]
print("PYT2_DONE total=%d ok=%d"%(len(rep),sum(r["ok"] for r in rep)))
