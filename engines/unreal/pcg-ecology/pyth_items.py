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
# trees: trunk cylinder + crown (oak/alder box-ish cylinders, pine/birch cones, willow drooping)
def tree(kind,v):
    s=0.6+0.1*v; H=(5 if kind in("Oak","Alder") else 7 if kind=="Pine" else 6)*s*j(.1)
    t=[(0.35*s,0.35*s,H*.45,0,0,0,"~"+("birch" if kind=="Birch" else "bark"))]
    if kind=="Pine": t+=[(2.4*s*(1-k*.25),2.4*s*(1-k*.25),H*.35,0,0,H*(.3+k*.22),"^pine") for k in range(3)]
    elif kind=="Birch": t+=[(1.6*s,1.6*s,H*.6,0,0,H*.4,"^leaf")]
    elif kind=="Willow": t+=[(3.2*s,3.2*s,H*.35,0,0,H*.45,"~willow")]+[(0.25,0.25,H*.4,1.3*s*math.cos(a),1.3*s*math.sin(a),H*.2,"willow") for a in (0,1.6,3.1,4.7)]
    else: t+=[(3.0*s*j(),3.0*s*j(),H*.5,0,0,H*.4,"~"+("leaf" if kind=="Oak" else "moss")),(1.8*s,1.8*s,H*.3,0.6*s,0,H*.75,"~leaf")]
    return t
for k in ("Oak","Pine","Willow","Birch","Alder"):
    for v in range(15): items.append(("Prop_Tree_PYT_%s_V%02d"%(k,v+1),tree(k,v)))
def shrub(c,dot,v):
    s=0.6+0.08*v; return [(s,s,s*.8,0,0,0,"~"+c),(s*.7,s*.7,s*.5,0.1,-0.1,s*.6,"~"+c)]+[(0.08,0.08,0.08,s*.4*math.cos(a),s*.4*math.sin(a),s*.5,dot) for a in (0,2,4)]
for k,c,d in (("Bramble","leaf","berry"),("Hazel","moss","bark"),("Elder","leaf","white"),("Gorse","pine","yellow")):
    for v in range(10): items.append(("Prop_Shrub_PYT_%s_V%02d"%(k,v+1),shrub(c,d,v)))
# succession herbs (herb combo): 12 herbs, each tied to a seral stage
HERBS=[("Fireweed","leaf","flower",0),("Yarrow","leaf","white",0),("Plantain","moss","moss",0),
 ("Selfheal","leaf","purple",1),("Meadowsweet","leaf","white",1),("Comfrey","moss","purple",1),
 ("Nettle","leaf","leaf",2),("Mullein","moss","yellow",2),("Valerian","leaf","flower",2),
 ("Woodsorrel","leaf","white",3),("Ramsons","leaf","white",3),("Wintergreen","pine","red",3)]
def herb(v,l,f):
    h=0.25*j(.3); b=[(0.06,0.06,h,0,0,0,"~moss")]
    for i in range(3+v):
        a=i*2*math.pi/(3+v); r=0.09*j(); b.append((0.1*j(),0.05,0.04,math.cos(a)*r,math.sin(a)*r,h*R.uniform(.3,.8),l))
    return b+[(0.08,0.08,0.06,0,0,h,"^"+f)]
for nm,l,f,_ in HERBS:
    for v in range(5): items.append(("Prop_Herb_PYT_%s_V%d"%(nm,v+1),herb(v,l,f)))
    for v in range(5): items.append(("Item_Herb_PYT_%s_Bundle%d"%(nm,v+1),[(0.05,0.05,0.12,0,0,0,"~hay")]+[(0.04,0.04,0.12*j(),R.uniform(-.04,.04),R.uniform(-.04,.04),0.08,l) for _ in range(2+v)]+[(0.05,0.05,0.04,0,0,0.2,f)]))
for v in range(12): items.append(("Item_Tea_PYT_Succession_T%02d"%(v+1),[(0.14,0.14,0.18,0,0,0,"~glass"),(0.12,0.12,0.12,0,0,0.02,["leaf","flower","honey","purple"][v%4]),(0.06,0.06,0.05,0,0,0.18,"~bark")]))
# ground layer
for k,c in (("Sedge","moss"),("MeadowGrass","leaf"),("Fern","pine"),("Wildflower","flower"),("Clover","leaf"),("Moss","moss")):
    for v in range(10): items.append(("Prop_Ground_PYT_%s_V%02d"%(k,v+1),[(0.05,0.05,(0.3+0.05*v)*j(.3),R.uniform(-.15,.15),R.uniform(-.15,.15),0,c) for _ in range(5+v)]+([(0.06,0.06,0.05,0,0,0.35,"flower")] if k=="Wildflower" else [])))
# water (drinkable chain: spring -> stream -> pond -> reed filter -> well/cistern -> troughs)
WAT=[("Spring",lambda s:[(s*1.8,s*1.8,0.3,0,0,0,"~stone"),(s*1.5,s*1.5,0.04,0,0,0.3,"~water"),(0.5,0.5,0.6,s*.6,0,0.2,"stone")]),
 ("StreamSegment",lambda s:[(3.0,1.0*s,0.04,0,0,0,"water"),(3.0,0.2,0.15,0,0.6*s,0,"stone"),(3.0,0.2,0.15,0,-0.6*s,0,"stone")]),
 ("PondBasin",lambda s:[(5*s,4*s,0.2,0,0,0,"~soil"),(4.6*s,3.6*s,0.04,0,0,0.18,"~water")]),
 ("ReedFilter",lambda s:[(1.4*s,1.0,0.3,0,0,0,"stone"),(1.2*s,0.8,0.04,0,0,0.28,"water")]+[(0.04,0.04,1.0,R.uniform(-.5,.5)*s,R.uniform(-.3,.3),0.3,"willow") for _ in range(8)]),
 ("Well",lambda s:[(1.4*s,1.4*s,0.8,0,0,0,"~stone"),(1.0*s,1.0*s,0.04,0,0,0.78,"~water"),(0.1,0.1,1.4,-.7*s,0,0.8,"bark"),(0.1,0.1,1.4,.7*s,0,0.8,"bark"),(1.8*s,1.2,0.12,0,0,2.2,"dark")]),
 ("Cistern",lambda s:[(1.6*s,1.6*s,1.6,0,0,0,"~stone"),(1.7*s,1.7*s,0.1,0,0,1.6,"~bark")]),
 ("Trough",lambda s:[(1.4*s,0.5,0.35,0,0,0,"bark"),(1.3*s,0.4,0.04,0,0,0.3,"water")]),
 ("RainBarrel",lambda s:[(0.7*s,0.7*s,1.0,0,0,0,"~bark"),(0.6*s,0.6*s,0.04,0,0,0.98,"~water"),(1.2,1.2,0.05,0,0,1.4,"^cloth")])]
for k,f in WAT:
    for v in range(8): items.append(("Prop_Water_PYT_%s_V%d"%(k,v+1),f(0.8+0.06*v)))
# livestock + food loop (sheep graze meadow, hens scratch scrub, bees work wildflowers)
for v in range(10): items.append(("Prop_Live_PYT_Fence_V%02d"%(v+1),[(0.1,0.1,1.0,-0.6,0,0,"~bark"),(0.1,0.1,1.0,0.6,0,0,"~bark"),(1.3,0.06,0.08,0,0,0.7,"bark"),(1.3,0.06,0.08,0,0,0.35,"bark")]))
for v in range(10): items.append(("Prop_Live_PYT_HenCoop_V%02d"%(v+1),[(1.4,1.0,0.9,0,0,0.3,"bark"),(1.5,1.1,0.1,0,0,1.2,["red","dark","moss"][v%3])]+[(0.1,0.1,0.3,x,y,0,"bark") for x in(-.6,.6) for y in(-.4,.4)]))
for v in range(10): items.append(("Prop_Live_PYT_Beehive_V%02d"%(v+1),[(0.5,0.5,0.25*(k+1)*0+0.25,0,0,0.3+0.26*k,["white","honey","yellow"][(v+k)%3]) for k in range(2+v%3)]+[(0.6,0.6,0.3,0,0,0,"~bark")]))
for v in range(10): items.append(("Prop_Live_PYT_SheepShelter_V%02d"%(v+1),[(2.4,1.8,1.3,0,0,0,"bark"),(2.6,2.0,0.15,0,0,1.3,"moss"),(1.2,1.8,0.3,0,0,0,"hay")]))
for v in range(10): items.append(("Prop_Live_PYT_HayRack_V%02d"%(v+1),[(1.2,0.6,0.6,0,0,0.4,"bark"),(1.1,0.5,0.5,0,0,0.5,"hay")]))
for v in range(10): items.append(("Prop_Live_PYT_Feeder_V%02d"%(v+1),[(0.6,0.4,0.15,0,0,0,"bark"),(0.3,0.3,0.5,0,0,0.15,"~glass"),(0.28,0.28,0.25,0,0,0.15,"~hay")]))
FOOD=[("HoneyJar","honey"),("EggBasket","white"),("Wool","white"),("MilkPail","white"),("BerryBasket","berry"),("HerbBread","hay"),("Cheese","yellow"),("NutSack","bark")]
for k,c in FOOD:
    for v in range(5): items.append(("Item_Food_PYT_%s_V%d"%(k,v+1),[(0.25,0.25,0.15,0,0,0,"~bark"),(0.2*j(),0.2,0.1+0.02*v,0,0,0.15,"~"+c)]))
# dressing
for v in range(10): items.append(("Prop_Dress_PYT_Log_V%02d"%(v+1),[(2.0*j(),0.4,0.4,0,0,0,"bark"),(0.2,0.2,0.3,0.6,0,0.35,"moss")]))
for v in range(10): items.append(("Prop_Dress_PYT_Stump_V%02d"%(v+1),[(0.6*j(),0.6,0.4*j(),0,0,0,"~bark"),(0.5,0.5,0.02,0,0,0.4,"~hay")]))
for v in range(10): items.append(("Prop_Dress_PYT_Rock_V%02d"%(v+1),[(0.8*j(.4),0.6*j(.4),0.4*j(.4),0,0,0,"stone"),(0.4,0.4,0.2,0.1,0,0.35,"moss")]))
for v in range(11): items.append(("Prop_Dress_PYT_Mushroom_V%02d"%(v+1),[(0.05,0.05,0.12,0,0,0,"~white"),(0.16,0.16,0.07,0,0,0.12,"^"+["red","bark","yellow"][v%3])]))
only = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
if only: items=[i for i in items if any(o in i[0] for o in only)]
rep=[build(n,b) for n,b in items]
json.dump(rep,open(os.path.join(OUT,"_pyt_report.json"),"w"),indent=0)
print("PYT_DONE total=%d ok=%d"%(len(rep),sum(r["ok"] for r in rep)))
