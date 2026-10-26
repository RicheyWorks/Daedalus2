# Buffffff Island item generator (Buffffff, Team Grok). Run hidden: blender -b --factory-startup -P buf_items.py
# Metres, origin bottom centre, flat colour slots, one collection per asset, Kind_BUF_Name. Writes GLBs + manifest.
import bpy, os, json, math, random
ROOT = r"C:\Users\730ri\projects\bot-team\art\buffffff"
OUT = os.path.join(ROOT, "glb"); ART = r"C:\Users\730ri\projects\bot-team\art"; SAVE_BLEND = True; os.makedirs(OUT, exist_ok=True)
random.seed(666666)
def hexc(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1,)
MATS={}
def mat(n,h):
    n="BUF_"+n
    if n in MATS: return MATS[n]
    m=bpy.data.materials.new(n); m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=hexc(h); MATS[n]=m; return m
def reset():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o,do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes): bpy.data.meshes.remove(me)
def _link(col,o):
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o); return o
def box(col,sx,sy,sz,x,y,z,m,rz=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z+sz/2),rotation=(0,0,rz))
    o=bpy.context.active_object; o.scale=(sx,sy,sz); bpy.ops.object.transform_apply(scale=True,rotation=True)
    o.data.materials.append(m); return _link(col,o)
def cyl(col,r,h,x,y,z,m,v=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v,radius=r,depth=h,location=(x,y,z+h/2))
    o=bpy.context.active_object; o.data.materials.append(m); return _link(col,o)
def ball(col,r,x,y,z,m,sz=1.0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=r,location=(x,y,z+r*sz))
    o=bpy.context.active_object; o.scale=(1,1,sz); bpy.ops.object.transform_apply(scale=True); o.data.materials.append(m); return _link(col,o)
def cone(col,r,h,x,y,z,m,v=8):
    bpy.ops.mesh.primitive_cone_add(vertices=v,radius1=r,depth=h,location=(x,y,z+h/2))
    o=bpy.context.active_object; o.data.materials.append(m); return _link(col,o)
made=[]
def asset(name,kind,build,group):
    reset(); col=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col)
    build(col)
    bpy.ops.object.select_all(action='DESELECT')
    for o in col.objects: o.select_set(True)
    p=os.path.join(OUT,name+".glb")
    bpy.ops.export_scene.gltf(filepath=p,use_selection=True,export_format='GLB',export_apply=True)
    tris=sum(len(o.data.polygons) for o in col.objects)
    made.append({"asset":name,"kind":kind,"group":group,"faces":tris})
    if SAVE_BLEND:
        kd=os.path.join(ART,name.split("_")[0]); os.makedirs(kd,exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(kd,name+".blend"),copy=True)
WOOD=mat("Wood","#8A5A32"); STONE=mat("Stone","#8C8C94"); DARK=mat("Dark","#2A2A2A"); SOIL=mat("Soil","#5A3B22")
WATER=mat("Water","#3A9BD5"); CLEAN=mat("CleanWater","#8FE3FF"); STEM=mat("Stem","#3E7A2E"); GOLD=mat("BuffGold","#F2B630")
GLASS=mat("Glass","#CFEFFF"); CLAY=mat("Clay","#B8643C"); ROOF=mat("Roof","#5B2A86")
# ---- HERBS: six F-families x 4 herbs = 24 herbs; 4 growth stages + item + seed + dried = 7 each = 168
FAM={"Fire":("#E8473C","Speed"),"Frost":("#7FD4F2","Shield"),"Flora":("#5CCB4A","Heal"),
     "Flux":("#B05CE0","Jump"),"Fog":("#B8BCC8","Stealth"),"Fang":("#D68A2E","Strength")}
HERBNAMES={"Fire":["Zipwort","Blazemint","Dashpepper","Sparkroot"],"Frost":["Rimeleaf","Wardmoss","Iceclove","Bulwarkbell"],
 "Flora":["Mendling","Sapheal","Balmthistle","Lifelily"],"Flux":["Springfern","Hopvine","Gravisedge","Skyreed"],
 "Fog":["Hushcap","Mistsage","Shadebloom","Veilgrass"],"Fang":["Toughroot","Brawnbean","Ironnettle","Musclemallow"]}
HERBS=[]
for f,(c,eff) in FAM.items():
    for i,hn in enumerate(HERBNAMES[f]):
        HERBS.append((hn,f)); m=mat("Herb_"+f+str(i),c); shape=i
        for st in (1,2,3,4):
            h=0.12+0.16*st
            def b(col,h=h,m=m,st=st,shape=shape):
                cyl(col,0.025,h,0,0,0,STEM,6)
                for k in range(st+2):
                    a=k*2*math.pi/(st+2); r=0.06+0.03*st
                    if shape==0: box(col,0.1,0.05,0.03,r*math.cos(a),r*math.sin(a),h*0.35+0.05*k,m,a)
                    elif shape==1: ball(col,0.04+0.01*st,r*math.cos(a),r*math.sin(a),h*0.3+0.04*k,m)
                    elif shape==2: cone(col,0.04,0.12,r*math.cos(a),r*math.sin(a),h*0.3+0.05*k,m,5)
                    else: box(col,0.03,0.03,0.15,r*math.cos(a),r*math.sin(a),h*0.2+0.03*k,m,a)
                if st>=3: ball(col,0.06+0.02*st,0,0,h,m)
            asset(f"Prop_BUF_Herb_{hn}_S{st}","prop",b,"herb")
        asset(f"Item_BUF_Herb_{hn}","item",lambda col,m=m:(box(col,0.18,0.18,0.06,0,0,0,m),cyl(col,0.02,0.15,0,0,0.06,STEM,6)),"herb")
        asset(f"Item_BUF_Seed_{hn}","item",lambda col,m=m:(ball(col,0.05,0,0,0,SOIL),ball(col,0.025,0,0,0.08,m)),"herb")
        asset(f"Item_BUF_Dried_{hn}","item",lambda col,m=m:(box(col,0.22,0.06,0.04,0,0,0,mat("Dried","#7A6A40")),box(col,0.08,0.05,0.05,0.06,0,0.04,m)),"herb")
# ---- STACK TONICS: 6 single-family stacks x tiers 1-6 (stack height) = 36, plus 15 cross-family pairs x 2 = 30  -> 66
for f,(c,eff) in FAM.items():
    m=mat("Tonic_"+f,c)
    for t in range(1,7):
        def b(col,m=m,t=t):
            cyl(col,0.07,0.16,0,0,0,GLASS,10)
            for k in range(t): cyl(col,0.06,0.022,0,0,0.01+0.024*k,m,10)
            cyl(col,0.03,0.05,0,0,0.16,GOLD,8)
        asset(f"Item_BUF_Stack_{f}_x{t}","item",b,"tonic")
fl=list(FAM)
for i in range(6):
    for j in range(i+1,6):
        for seal in ("Water","Honey"):
            a,bb=fl[i],fl[j]
            asset(f"Item_BUF_Fuse_{a}{bb}_{seal}","item",lambda col,a=a,bb=bb,seal=seal:(cyl(col,0.07,0.08,0,0,0,mat("Tonic_"+a,FAM[a][0]),10),
                  cyl(col,0.07,0.08,0,0,0.08,mat("Tonic_"+bb,FAM[bb][0]),10),cyl(col,0.035,0.05,0,0,0.16,CLEAN if seal=="Water" else GOLD,8)),"tonic")
# ---- HERB TOOLS/STATIONS: 12
for n,(sx,sz,m) in {"StackMortar":(0.5,0.4,STONE),"SealPress":(0.9,1.1,WOOD),"DryingRack":(1.6,1.8,WOOD),"BuffCauldron":(1.0,0.9,DARK),
    "SeedVault":(1.2,1.0,STONE),"HerbBed":(2.0,0.3,SOIL),"Trellis":(1.5,2.2,WOOD),"Greenhouse":(4.0,3.0,GLASS),
    "CompostBin":(1.0,0.9,WOOD),"WaterCan":(0.35,0.3,GOLD),"Sickle":(0.4,0.05,DARK),"StackShelf":(1.4,1.8,WOOD)}.items():
    asset(f"Prop_BUF_Station_{n}","prop",lambda col,sx=sx,sz=sz,m=m:(box(col,sx,sx*0.7,sz*0.8,0,0,0,m),box(col,sx*0.6,sx*0.4,sz*0.2,0,0,sz*0.8,GOLD)),"station")
# ---- LIVESTOCK: 8 species x 4 ages + 2 coat variants of adult = 48
LIV=[("Buffalo","#5A3A28",1.8),("Fluffhen","#F4EFE2",0.45),("Puffgoat","#E8E2D0",0.95),("Muffpig","#E7A0A0",0.8),
     ("Tuffox","#6A4A32",1.9),("Snuffduck","#D9C24A",0.4),("Gruffsheep","#F4F4F4",1.0),("Ruffrabbit","#B89A7A",0.35)]
for ln,lc,s0 in LIV:
    for age,f,cv in (("Baby",0.5,lc),("Young",0.75,lc),("Adult",1.0,lc),("Elder",1.1,"#9A9A9A"),("AdultGold",1.0,"#F2B630"),("AdultPurple",1.0,"#7A3AB6")):
        m=mat("Liv_"+ln+age,cv); s=s0*f
        def b(col,s=s,m=m):
            leg=0.3*s
            for x in (-0.22*s,0.22*s):
                for y in (-0.3*s,0.3*s): cyl(col,0.06*s,leg,x,y,0,DARK,6).name="Leg"
            ball(col,0.42*s,0,0,leg*0.8,m,0.7).name="Body"
            ball(col,0.2*s,0,-0.5*s,leg+0.35*s,m).name="Head"
            box(col,0.08*s,0.08*s,0.12*s,0,-0.66*s,leg+0.42*s,GOLD).name="BuffTag"
        asset(f"Mob_BUF_{ln}_{age}","mob",b,"livestock")
# ---- FOOD LOOP: 8 products, 12 crops x 3 stages, 10 dishes raw/cooked, 8 feeds = 8+36+20+8 = 72
PROD=[("Milk","#FFFFFF"),("Egg","#F4EFE2"),("Wool","#F4F4F4"),("Bacon","#C8505A"),("Butter","#F2D870"),("Feather","#D9C24A"),("Hide","#6A4A32"),("Cheese","#F2C230")]
for pn,pc in PROD: asset(f"Item_BUF_Prod_{pn}","item",lambda col,m=mat("P_"+pn,pc):ball(col,0.1,0,0,0,m,0.9),"food")
CROPS=[("Clover","#3FAF4A"),("Oat","#D8B65A"),("Turnip","#E8D8E0"),("Beet","#B0304A"),("Potato","#C9A36A"),("Bean","#6FAF3A"),
       ("Corn","#E8C840"),("Squash","#E88A28"),("Berry","#B03CB0"),("Kale","#2F7F3F"),("Hay","#D8C070"),("Melon","#4FAF5A")]
for cn,cc in CROPS:
    for st in (1,2,3):
        asset(f"Prop_BUF_Crop_{cn}_S{st}","prop",lambda col,m=mat("C_"+cn,cc),st=st:(cyl(col,0.02,0.15*st,0,0,0,STEM,6),ball(col,0.04*st,0,0,0.15*st,m)),"food")
DISH=[("Stew","#A0522D"),("Omelet","#F2D22E"),("Pie","#D6A35C"),("Porridge","#E8DCC0"),("Roast","#8A3A2A"),
      ("Soup","#C87A3A"),("Salad","#7CCB4A"),("Bread","#D6A35C"),("Pancake","#E8B860"),("BuffBurger","#9A4A2A")]
for dn,dc in DISH:
    for st,c in (("Raw","#C0B0A0"),("Cooked",dc)):
        asset(f"Item_BUF_Food_{dn}_{st}","item",lambda col,m=mat(f"F_{dn}_{st}",c):(cyl(col,0.16,0.03,0,0,0,STONE,12),ball(col,0.11,0,0,0.03,m,0.6)),"food")
for fn,fc in (("HayBale","#D8C070"),("CloverBundle","#3FAF4A"),("GrainSack","#C9A36A"),("Slop","#7A6A40"),("Seedmix","#B89A5A"),("SaltLick","#E8E8E8"),("Mash","#A08050"),("BerryFeed","#B03CB0")):
    asset(f"Item_BUF_Feed_{fn}","item",lambda col,m=mat("Feed_"+fn,fc):box(col,0.5,0.35,0.35,0,0,0,m),"food")
# ---- FARM BUILDINGS & KITCHEN: 20
for bn,sz in (("Barn",7),("Coop",2.4),("Stable",4.5),("Sty",3),("Silo",3.5),("Hutch",1.4),("DuckHouse",1.8),("Dairy",4),("Smokehouse",3),("Granary",4)):
    asset(f"Bld_BUF_{bn}","building",lambda col,s=sz:(box(col,s,s*0.8,s*0.6,0,0,0,WOOD),cone(col,s*0.75,s*0.45,0,0,s*0.6,ROOF,4)),"farm")
for kn in ("Stove","Oven","Churn","Mill","CheesePress","Grill","Smoker","PrepTable","Pantry","Icebox"):
    asset(f"Prop_BUF_Kitchen_{kn}","prop",lambda col,kn=kn:(box(col,1.1,0.8,0.9,0,0,0,STONE if kn in("Stove","Oven","Grill") else WOOD),box(col,0.5,0.5,0.3,0,0,0.9,DARK)),"farm")
# ---- WATER SYSTEM: 14 structures x 3 variants = 42, vessels 6 x 2 = 12, troughs 4 -> 58
for wn,h in (("Spring",0.6),("Well",2.2),("HandPump",1.4),("RainCanopy",3.5),("Cistern",2.5),("SandFilter",1.6),("CharcoalFilter",1.5),
             ("SunStill",1.0),("Boiler",1.8),("Aqueduct",3.0),("Waterwheel",3.5),("Fountain",1.6),("Pond",0.4),("Reservoir",1.2)):
    for v in (1,2,3):
        def b(col,h=h,v=v,wn=wn):
            w=1.0+0.25*v
            if wn in("Spring","Pond","Reservoir"): cyl(col,w*1.5,h*0.5,0,0,0,STONE,12); cyl(col,w*1.35,0.05,0,0,h*0.5-0.03,CLEAN if wn=="Spring" else WATER,12)
            elif wn=="Aqueduct":
                for x in (-w,w): box(col,0.4,0.4,h,x,0,0,STONE)
                box(col,w*2+0.6,0.6,0.3,0,0,h,STONE); box(col,w*2+0.4,0.4,0.05,0,0,h+0.28,CLEAN)
            elif wn=="RainCanopy": [cyl(col,0.06,h,x,y,0,WOOD,6) for x in (-w,w) for y in (-w,w)]; cone(col,w*1.8,0.5,0,0,h,GLASS,4); cyl(col,0.4,0.8,0,0,0,WOOD,10)
            else: cyl(col,w*0.6,h*0.7,0,0,0,STONE if v!=2 else CLAY,10); cyl(col,w*0.5,0.05,0,0,h*0.7-0.02,CLEAN,10); box(col,0.15,0.15,h*0.3,w*0.5,0,h*0.7,GOLD)
        asset(f"Prop_BUF_Water_{wn}_V{v}","prop",b,"water")
for cn,s in (("Cup",0.12),("Canteen",0.25),("Jug",0.35),("Bucket",0.4),("Flask",0.2),("Waterskin",0.3)):
    for st in ("Empty","Full"):
        asset(f"Item_BUF_{cn}_{st}","item",lambda col,s=s,st=st:(cyl(col,s*0.5,s,0,0,0,CLAY,10),st=="Full" and cyl(col,s*0.42,0.02,0,0,s-0.02,CLEAN,10)),"water")
for tn,l in (("Small",1.2),("Long",3.0),("Round",1.6),("Gold",2.0)):
    asset(f"Prop_BUF_Trough_{tn}","prop",lambda col,l=l,tn=tn:(box(col,l,0.6,0.5,0,0,0,GOLD if tn=="Gold" else WOOD),box(col,l*0.9,0.5,0.04,0,0,0.46,CLEAN)),"water")
# ---- NFT / landmark set: deed stone, mint obelisk, BUFF statue, banners x6 = 9
asset("Prop_BUF_Landmark_MintObelisk","prop",lambda col:(box(col,1.2,1.2,6,0,0,0,DARK),cone(col,0.9,1.2,0,0,6,GOLD,4)),"nft")
asset("Prop_BUF_Landmark_DeedStone","prop",lambda col:(box(col,1.6,0.4,1.2,0,0,0,STONE),box(col,1.2,0.05,0.8,0,-0.22,0.2,GOLD)),"nft")
asset("Prop_BUF_Landmark_BuffStatue","prop",lambda col:(box(col,2,2,1,0,0,0,STONE),ball(col,1.0,0,0,1,GOLD,1.3),ball(col,0.5,0,-0.9,2.2,GOLD)),"nft")
for i,(f,(c,e)) in enumerate(FAM.items()):
    asset(f"Prop_BUF_Banner_{f}","prop",lambda col,c=c,f=f:(cyl(col,0.05,4,0,0,0,WOOD,6),box(col,1.0,0.05,1.6,0.5,0,2.2,mat("Ban_"+f,c))),"nft")
# ---- v2 additions: apiary (honey seal), fences/gates, paths, decor, herb plots, lamps, signs, boats = 160
HIVE=mat("Hive","#E8B830"); HONEY=mat("Honey","#F2A020")
for v in range(1,7): asset(f"Prop_BUF_Apiary_Hive_V{v}","prop",lambda col,v=v:[box(col,0.6,0.5,0.25,0,0,0.3*k,HIVE if k%2==0 else WOOD) for k in range(v%3+2)],"apiary")
for it in ("HoneyJar","HoneyComb","Beeswax","Smoker","BeeSuit","Extractor"): asset(f"Item_BUF_Apiary_{it}","item",lambda col:(cyl(col,0.1,0.18,0,0,0,GLASS,10),cyl(col,0.08,0.12,0,0,0.02,HONEY,10)),"apiary")
for f in FAM:
    for v in range(1,5): asset(f"Prop_BUF_HerbPlot_{f}_V{v}","prop",lambda col,f=f,v=v:(box(col,1.5+0.5*v,1.2,0.25,0,0,0,SOIL),box(col,1.6+0.5*v,0.1,0.35,0,0.6,0,WOOD),[ball(col,0.12,-0.6+0.4*k,0,0.25,mat("Herb_"+f+"0",FAM[f][0])) for k in range(v+2)]),"herb")
for v in range(1,13): asset(f"Prop_BUF_Fence_V{v}","prop",lambda col,v=v:([cyl(col,0.06,1+0.1*(v%3),x,0,0,WOOD,6) for x in (-1,1)],[box(col,2.1,0.06,0.1,0,0,z,GOLD if v>9 else WOOD) for z in (0.4,0.8)]),"farm")
for v in range(1,5): asset(f"Prop_BUF_Gate_V{v}","prop",lambda col,v=v:(cyl(col,0.1,1.6,-1.2,0,0,WOOD,6),cyl(col,0.1,1.6,1.2,0,0,WOOD,6),box(col,2.2,0.08,1.0,0,0,0.3,WOOD),box(col,0.4,0.1,0.3,0,0,1.5,GOLD)),"farm")
for v in range(1,21): asset(f"Prop_BUF_Path_V{v}","prop",lambda col,v=v:[cyl(col,0.4+0.05*(k%3),0.08,k*0.9,0.2*((k*v)%3-1),0,STONE,7) for k in range(3+v%4)],"kit")
for n,c in (("Lamp","#F2E070"),("Sign","#8A5A32"),("Bench","#8A5A32"),("Barrel","#6A4A32"),("Crate","#A07A4A"),("Cart","#8A5A32"),("Wheelbarrow","#6A6A6A"),("Scarecrow","#D8B65A")):
    for v in range(1,7): asset(f"Prop_BUF_Decor_{n}_V{v}","prop",lambda col,c=c,v=v:(box(col,0.5+0.1*v,0.5,0.6+0.15*v,0,0,0,mat("D_"+c,c)),ball(col,0.12,0,0,0.6+0.15*v,GOLD)),"decor")
for v in range(1,5): asset(f"Prop_BUF_Dock_V{v}","prop",lambda col,v=v:([cyl(col,0.12,2,x,y,-1,WOOD,6) for x in (-1.5,1.5) for y in (0,2*v)],box(col,3.4,2*v+0.4,0.15,0,v,1,WOOD)),"water")
for v in range(1,5): asset(f"Veh_BUF_Raft_V{v}","vehicle",lambda col,v=v:[cyl(col,0.15,2+0.5*v,0.32*k,0,0,WOOD,8) for k in range(5)],"water")
for f in FAM:
    for v in (1,2): asset(f"Prop_BUF_Shrine_{f}_V{v}","prop",lambda col,f=f,v=v:(box(col,1.2,1.2,0.6,0,0,0,STONE),cone(col,0.5,1.0+0.5*v,0,0,0.6,mat("Herb_"+f+"1",FAM[f][0]),6)),"nft")
for v in range(1,13): asset(f"Prop_BUF_FlowerPatch_V{v}","prop",lambda col,v=v:[ball(col,0.1,random.Random(v*9+k).uniform(-0.6,0.6),random.Random(v*7+k).uniform(-0.6,0.6),0,mat("Fl"+str((v+k)%6),list(FAM.values())[(v+k)%6][0])) for k in range(8)],"kit")
# ---- v3 additions: livestock tack, storage, pests/remedies, weather, signage = 120
for sp,_,_ in LIV:
    for t,c in (("Bell","#C9A040"),("Collar","#7A3AB6"),("Feeder","#8A5A32"),("Bed","#D8C070"),("NameTag","#F2B630")):
        asset(f"Prop_BUF_Tack_{sp}_{t}","prop",lambda col,c=c,t=t:(box(col,0.4,0.3,0.15 if t!="Feeder" else 0.4,0,0,0,mat("T_"+t,c)),ball(col,0.06,0,0,0.2,GOLD)),"livestock")
for st in ("Jar","Crock","Sack","Basket","Shelf","Cellar","Smokerack","Saltbox"):
    for v in (1,2,3): asset(f"Prop_BUF_Store_{st}_V{v}","prop",lambda col,v=v:(cyl(col,0.2+0.1*v,0.3+0.15*v,0,0,0,CLAY if v!=2 else WOOD,10),cyl(col,0.15+0.1*v,0.04,0,0,0.3+0.15*v,DARK,10)),"food")
for p,c in (("Aphid","#7CCB4A"),("Mite","#C8505A"),("Slug","#8A7A5A"),("Mildew","#E8E8E8"),("Rot","#5A3B22"),("Locust","#B8A040")):
    asset(f"Mob_BUF_Pest_{p}","mob",lambda col,c=c:(ball(col,0.05,0,0,0,mat("Pest_"+c,c),0.6),ball(col,0.03,0,-0.05,0.03,DARK)),"herb")
    asset(f"Item_BUF_Remedy_{p}","item",lambda col,c=c:(cyl(col,0.06,0.14,0,0,0,GLASS,8),cyl(col,0.05,0.08,0,0,0.01,mat("Rem_"+c,c),8)),"herb")
for w in ("RainGauge","WindVane","SunDial","Lightning Rod","FogNet","DewCollector","StormShelter","Weathercock"):
    w=w.replace(" ","")
    for v in (1,2): asset(f"Prop_BUF_Weather_{w}_V{v}","prop",lambda col,v=v:(cyl(col,0.05,1.5+v,0,0,0,DARK,6),box(col,0.6,0.1,0.4,0,0,1.5+v,GOLD)),"water")
for v in range(1,13): asset(f"Prop_BUF_Signpost_V{v}","prop",lambda col,v=v:(cyl(col,0.06,1.8,0,0,0,WOOD,6),[box(col,0.8,0.05,0.2,0.3*(1 if k%2 else -1),0,1.2+0.25*k,mat("Ban_"+fl[(v+k)%6],FAM[fl[(v+k)%6]][0])) for k in range(1+v%3)]),"decor")
# ---- ISLAND KIT: rocks/cliffs/trees/bushes/logs/paths to reach 560+
n=0; ROCKC=["#8C8C94","#6E6A64","#A89F8C","#5A6470","#7A8A70"]
while len(made)<860:
    n+=1; kind=["Rock","Cliff","Boulder","Tree","Bush","Log","PathStone","Pine"][n%8]
    def b(col,seed=n,kind=kind):
        r=random.Random(seed*7)
        if kind=="Tree": h=r.uniform(4,9); cyl(col,0.25,h,0,0,0,WOOD,8); ball(col,h*0.3,0,0,h*0.75,mat("Leaf"+str(seed%4),["#2F7F3F","#3FAF4A","#4F8F2F","#6FAF3A"][seed%4]))
        elif kind=="Pine": h=r.uniform(5,12); cyl(col,0.2,h*0.3,0,0,0,WOOD,8); [cone(col,h*0.25*(1-k*0.25),h*0.35,0,0,h*0.25+k*h*0.2,mat("Pine","#1F5F3F"),8) for k in range(3)]
        elif kind=="Bush": [ball(col,r.uniform(0.3,0.7),r.uniform(-0.4,0.4),r.uniform(-0.4,0.4),0,mat("Bush","#3F7A2E")) for _ in range(r.randint(2,4))]
        elif kind=="Log": bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=0.3,depth=r.uniform(2,5),location=(0,0,0.3),rotation=(0,math.pi/2,r.uniform(0,3))); o=bpy.context.active_object; o.data.materials.append(WOOD); _link(col,o)
        elif kind=="PathStone": cyl(col,r.uniform(0.3,0.8),0.1,0,0,0,STONE,7)
        else:
            s=r.uniform(0.6,4) if kind!="Cliff" else r.uniform(4,12); m=mat("Rock"+str(seed%5),ROCKC[seed%5])
            for j in range(r.randint(2,5)):
                w=s*r.uniform(0.5,1.0); box(col,w,w*r.uniform(0.6,1),s*r.uniform(0.3,0.8),r.uniform(-0.25,0.25)*s,r.uniform(-0.25,0.25)*s,0,m,r.uniform(0,1.5))
    asset(f"Prop_BUF_{kind}_K{n:03d}","prop",b,"kit")
json.dump(made,open(os.path.join(ROOT,"manifest.json"),"w"),indent=1); print("MADE",len(made))
