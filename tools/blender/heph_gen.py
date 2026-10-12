# Hephaestus procedural asset generator. Run: blender -b -P heph_gen.py -- <start> <count>
import bpy, bmesh, sys, json, os, hashlib, random, datetime
ART=r"C:\Users\730ri\projects\bot-team\art"
argv=sys.argv[sys.argv.index("--")+1:]; START,COUNT=int(argv[0]),int(argv[1])
MAT={"Wood":"8B5A2B","Stone":"8A8A8A","Copper":"C8703A","Bronze":"B0803A","Iron":"C9B49C","Steel":"9AA4AE","Gold":"F2C230","Starmetal":"7FE3FF","Obsidian":"2A2033","Crystal":"A070FF","Tin":"D0D4D8","Coal":"34343A","Basalt":"3C3A3A","Magma":"FF5A1F","Silver":"E0E0E8","Platinum":"E5E4E2","Nickel":"B8B0A0","Cobalt":"3355CC","Sulfur":"E8D84A","Salt":"F4F1EA","Clay":"B5653A","Heartstone":"D2304A","Emberite":"FF8A2A","Ash":"6E6A66","Lead":"5A5F6A","Zinc":"B4BCC4"}
def H(h): return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1,)
def plan():
    L=[]
    tools=["Hammer","Tongs","Chisel","Axe","Shovel","Sickle","Saw","File","Punch","Pickaxe","Hoe","Knife"]
    for m in ["Wood","Stone","Copper","Bronze","Iron","Steel","Obsidian","Starmetal"]:
        for t in tools[:9]: L.append(("Tool",f"Tool_Forge{t}_{m}","tool",m,0.8))
    ores=["Copper","Iron","Gold","Tin","Silver","Platinum","Nickel","Cobalt","Sulfur","Salt","Clay","Heartstone","Emberite","Obsidian","Crystal","Starmetal","Coal","Basalt","Magma","Ash","Bronze","Steel","Lead","Zinc"]
    for o in ores:
        L+= [("Item",f"Item_Ore_{o}","chunk",o,0.35),("Item",f"Item_Ingot_{o}","bar",o,0.3),("Item",f"Item_Nugget_{o}","nug",o,0.15)]
    herbs=["Emberleaf","Ashmint","Cinderroot","Sulfurbloom","Lavathistle","Forgefern","Smokesage","Glowcap","Starpetal","Ironbark","Saltgrass","Cometcress","Ventmoss","Charlily","Blazeberry","Coalclover","Mistwort","Dewbell","Thornwick","Sunspike","Frostfrond","Moonmallow","Ravenroot","Bloodnettle","Calmbloom","Bitterweed","Honeyreed","Quartzvine","Pyreweed","Shardsorrel","Vigorleaf","Duskthyme","Kilnpoppy","Boilbalm","Steamreed","Hearthbasil"]
    pal=["FF6A2A","9AC46A","7A4A2A","E8D84A","D24A6A","4A8A3A","9A9A8A","7FE3FF","E0B0FF","6A5A3A","D8D0A0","A070FF","3A6A4A","F0E0F0","C0303A","2A4A2A"]
    for i,h in enumerate(herbs):
        c=pal[i%len(pal)]; L+=[("Item",f"Item_Herb_{h}","plant",c,0.3),("Item",f"Item_Herb_{h}_Dried","bundle",c,0.2)]
    food=["Bread","Flatbread","Cheese","Butter","Milk","Egg","Omelet","Steak","Ribs","Sausage","Ham","Bacon","Stew","Soup","Porridge","Pie","Cake","Cookie","Honey","Jam","Apple","Pear","Plum","Berry","Carrot","Potato","Turnip","Onion","Corn","Pumpkin","Mushroom","Fish","FishGrilled","Crab","Kebab","Dumpling","Noodles","Rice","Curry","Taco","Burger","Fries","Pizza","Pancake","Waffle","Yogurt","Tea","Cocoa","Cider","Lemonade","Jerky","Smokedfish","Roastchicken","Drumstick","Salad","Sandwich","Muffin","Bun","Pretzel","Toffee","Candy","Sushi","Lavacake","Emberchili","Ashbread","Forgeroast","Meteorpie","Arkbiscuit","Hearthstew","Cinderbun","Sporesoup","Starjelly"]
    import colorsys
    for i,f in enumerate(food):
        r,g,b=colorsys.hsv_to_rgb((i*0.137)%1,0.55,0.85); L.append(("Item",f"Item_Food_{f}","food","%02X%02X%02X"%(int(r*255),int(g*255),int(b*255)),0.25))
    lg=["Trough","Feeder","FencePost","FenceRail","Gate","Saddle","Bell","Brush","Halter","Nestbox","Hutch","Coop","Stall","Haybale","Milkpail","Shears","Yoke","Collar"]
    for m in ["Wood","Iron","Bronze","Steel"]:
        for t in lg: L.append(("Prop",f"Prop_Ranch{t}_{m}","box" if t not in("Bell","Brush","Shears","Collar","Halter","Milkpail") else "small",m,1.0))
    wg=["Bucket","Canteen","Barrel","Filter","Wellhead","Cistern","Pipe","PipeElbow","Pump","RainCatch","Boiler","Still","Ladle","Jug","Flask","Trough","Spigot","Tank"]
    for m in ["Wood","Clay","Copper","Iron"]:
        for t in wg: L.append(("Prop",f"Prop_Water{t}_{m}","container",m,0.9))
    pr=["Anvil","Forge","Crucible","Brazier","Bellows","QuenchTub","Chimney","Grindstone","Workbench","ToolRack","IngotStack","Kiln","LavaRock","VentPlume","ObsidianSpire","MagmaPool","EmberBrazier","ForgeAltar"]
    for m in ["Stone","Iron","Basalt","Obsidian"]:
        for t in pr: L.append(("Prop",f"Prop_Forge{t}_{m}","struct",m,1.6))
    X=[("Prop","Prop_HephaestusAnvil_Great","struct","Obsidian",2.0),("Prop","Prop_HephaestusForge_Great","struct","Basalt",2.4),("Item","Item_Shard_Asteroid","chunk","Emberite",0.4),("Item","Item_Shard_Planet","chunk","Basalt",0.4),("Tool","Tool_HephaestusHammer","tool","Starmetal",1.0),("Prop","Prop_ArkRivetCrate","box","Iron",0.8),("Prop","Prop_LavaLantern","small","Magma",0.6)]
    return L[:500]+X
def cube(bm,cx,cy,z0,sx,sy,sz,mi):
    r=bmesh.ops.create_cube(bm,size=1)
    for v in r["verts"]: v.co.x=v.co.x*sx+cx; v.co.y=v.co.y*sy+cy; v.co.z=(v.co.z+0.5)*sz+z0
    for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index=mi
def build(shape,s,rnd):
    bm=bmesh.new(); j=lambda a:a*(0.85+0.3*rnd.random())
    if shape=="tool":
        cube(bm,0,0,0,0.06*s,0.06*s,s,1); cube(bm,0,0,s*0.85,j(0.35)*s,0.12*s,0.15*s,0)
    elif shape in("chunk","nug"):
        for k in range(3): cube(bm,j(0.1)*s*(k-1),j(0.1)*s*(k%2),0,j(0.6)*s,j(0.6)*s,j(0.55)*s,0)
    elif shape=="bar": cube(bm,0,0,0,s,0.4*s,0.25*s,0); cube(bm,0,0,0.25*s,0.8*s,0.3*s,0.08*s,0)
    elif shape=="plant":
        cube(bm,0,0,0,0.05,0.05,s,1)
        for k in range(4): cube(bm,(k%2-0.5)*0.12,((k//2)-0.5)*0.12,j(0.4)*s,0.14,0.06,0.04,0)
    elif shape=="bundle": cube(bm,0,0,0,0.1,s,0.1,0); cube(bm,0,0,0.02,0.12,0.03,0.12,1)
    elif shape=="food": cube(bm,0,0,0,j(1)*s,j(1)*s,j(0.5)*s,0); cube(bm,0,0,0.45*s,0.7*s,0.7*s,0.15*s,1)
    elif shape=="small": cube(bm,0,0,0,0.3,0.3,0.3,0); cube(bm,0,0,0.3,0.1,0.1,0.1,1)
    elif shape=="box": cube(bm,0,0,0,j(1.2)*s,j(0.6)*s,j(0.8)*s,0); cube(bm,0,0,j(0.8)*s,1.25*s,0.65*s,0.08,1)
    elif shape=="container":
        cube(bm,0,0,0,j(0.6)*s,j(0.6)*s,j(0.8)*s,0); cube(bm,0,0,0.8*s,0.66*s,0.66*s,0.06,1); cube(bm,0,-0.35*s,0.4*s,0.08,0.1,0.08,1)
    else:
        cube(bm,0,0,0,j(1.2)*s,j(1.0)*s,0.3*s,0); cube(bm,0,0,0.3*s,j(0.8)*s,j(0.7)*s,j(0.8)*s,1); cube(bm,0,0,1.1*s,0.5*s,0.4*s,0.2*s,0)
    return bm
done=[]
for kind,name,shape,mat,size in plan()[START:START+COUNT]:
    jp=os.path.join(ART,'jobs',name+'.json')
    if os.path.exists(jp) and 'hephaestus' not in open(jp).read(): print('SKIP_EXISTING',name); continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rnd=random.Random(name); bm=build(shape,size,rnd)
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob=bpy.data.objects.new(name,me); col=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col); col.objects.link(ob)
    base=H(MAT.get(mat,mat)); dark=tuple(c*0.55 for c in base[:3])+(1,)
    for i,c in enumerate((base,dark if shape!="tool" else H(MAT["Wood"]))):
        m=bpy.data.materials.new(f"{name}_M{i}"); m.diffuse_color=c; m.use_nodes=True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=c
        if mat in("Magma","Emberite","Starmetal","Crystal"): m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value=2.0; m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value=c
        me.materials.append(m)
    d=[round(x,2) for x in ob.dimensions]; tris=sum(len(p.vertices)-2 for p in me.polygons)
    os.makedirs(os.path.join(ART,kind),exist_ok=True)
    blend=os.path.join(ART,kind,name+".blend"); glb=os.path.join(ART,"glb",name+".glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob
    bpy.ops.export_scene.gltf(filepath=glb,use_selection=True,export_format='GLB')
    sha=hashlib.sha1(open(glb,'rb').read()).hexdigest(); now=datetime.datetime.now().isoformat(timespec='seconds')
    ok=tris<=3000 and len(me.materials)<=3
    job={"spec":1,"asset":name,"kind":kind,"blender":{"blend":blend,"glb":glb,"glb_sha1":sha,"tris":tris,"meshes":[{"name":name,"tris":tris,"materials":[m.name for m in me.materials],"dims_m":d}],"materials":[m.name for m in me.materials],"built_by":"hephaestus (heph_gen.py)","built_at":now,"selfcheck":{"ok":ok,"fails":[],"checked_at":now}}}
    json.dump(job,open(os.path.join(ART,"jobs",name+".json"),"w"),indent=2)
    done.append(f"{name}\t{kind}\t{max(d)}\t{tris}")
open(os.path.join(ART,"NOTES",f"heph_batch_{START}.tsv"),"w").write("\n".join(done)+"\n")
print("BATCH_DONE",START,len(done))
