# Youtube Master Island batch generator (youtube-master, Team Grok). Run: blender -b -P ytm_items.py
# BRIEF.md rules: metres, origin bottom centre, -Y front, 1-3 flat colour slots, one collection per asset, Kind_Name.
import bpy, os, json, math, random
OUT = r"C:\Users\730ri\projects\bot-team\art\glb"
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\batch1.json"
random.seed(2820)
def hexc(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1,)
MATS={}
def mat(n,h):
    n="YTM_"+n
    if n in MATS: return MATS[n]
    m=bpy.data.materials.new(n); m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=hexc(h); MATS[n]=m; return m
def reset():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o,do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes): bpy.data.meshes.remove(me)
def box(col,sx,sy,sz,x,y,z,m,rz=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z+sz/2),rotation=(0,0,rz))
    o=bpy.context.active_object; o.scale=(sx,sy,sz); bpy.ops.object.transform_apply(scale=True,rotation=True)
    o.data.materials.append(m)
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o); return o
made=[]
def asset(name,kind,size,build):
    reset(); col=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col)
    build(col)
    bpy.ops.object.select_all(action='DESELECT')
    for o in col.objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,name+".glb"),use_selection=True,export_format='GLB',export_apply=True)
    made.append({"asset":name,"kind":kind,"size":size})
WOOD=mat("Wood","#8A5A32"); STONE=mat("Stone","#8C8C94"); DARK=mat("Dark","#2A2A2A"); SOIL=mat("Soil","#5A3B22")
WATER=mat("Water","#3A9BD5"); CLEAN=mat("CleanWater","#8FE3FF"); STEM=mat("Stem","#3E7A2E"); BRASS=mat("Brass","#C9A040")
# ---- HERBS: 12 "note herbs" (herb-combo mechanic = chords), 4 growth stages + item + seed = 72
HERBS=[("Doleaf","C","#E8473C"),("Rebell","D","#F28C28"),("Mimint","E","#F2D22E"),("Fasage","F","#7CCB4A"),
 ("Solthorn","G","#2FBF9F"),("Lavine","A","#3E8EDE"),("Tisquill","B","#8A5CE0"),("Sharpcress","C#","#E05CB4"),
 ("Flatfern","Eb","#5C7A3E"),("Dronebloom","Bb","#B0B8C8"),("Hushmoss","F#","#9FD8C0"),("Gloryroot","Ab","#D6A35C")]
for hn,note,hc in HERBS:
    m=mat("Herb_"+hn,hc)
    for st in (1,2,3,4):
        h=0.1+0.17*st
        def b(col,h=h,m=m,st=st):
            box(col,0.05,0.05,h,0,0,0,STEM)
            for i in range(st+1):
                a=i*2*math.pi/(st+1); r=0.07+0.035*st
                box(col,0.1,0.1,0.05,r*math.cos(a),r*math.sin(a),h*0.4+0.06*i,m,a)
            if st>=3: box(col,0.12,0.12,0.12,0,0,h,m)
        asset(f"Prop_YTM_Herb_{hn}_S{st}","prop",f"~{h+0.12:.2f} m",b)
    asset(f"Item_YTM_Herb_{hn}","item","~0.3 m",lambda col,m=m:(box(col,0.2,0.2,0.08,0,0,0,m),box(col,0.05,0.05,0.18,0,0,0.08,STEM)))
    asset(f"Item_YTM_Seed_{hn}","item","~0.15 m",lambda col,m=m:(box(col,0.14,0.1,0.1,0,0,0,SOIL),box(col,0.06,0.06,0.06,0,0,0.1,m)))
# ---- HERB COMBO results: 24 tonics (chord brews) as bottles
CHORDS=["Major","Minor","Sus","Dim","Aug","Seventh"]
TONC=["#F2D22E","#3E8EDE","#7CCB4A","#8A5CE0","#E8473C","#D6A35C"]
for ci,cn in enumerate(CHORDS):
    for tier in (1,2,3,4):
        m=mat("Tonic_"+cn,TONC[ci])
        asset(f"Item_YTM_Tonic_{cn}_T{tier}","item","~0.3 m",lambda col,m=m,t=tier:(box(col,0.16+0.02*t,0.16+0.02*t,0.2,0,0,0,m),box(col,0.06,0.06,0.08,0,0,0.2,BRASS)))
# ---- LIVESTOCK: 8 species x 3 ages (calf/adult/elder) = 24, parts split for anim
LIV=[("Mooncalf","#E8E2D0",1.5),("ReefSheep","#F4F4F4",1.0),("BubbleHen","#F2EEE0",0.45),("Kelpig","#E7A0A0",0.8),
 ("DriftGoat","#7E8F5A",0.95),("StormDuck","#D9C24A",0.4),("Hornox","#6A4A32",1.8),("Glowllama","#C8B8F0",1.6)]
for ln,lc,s0 in LIV:
    m=mat("Liv_"+ln,lc)
    for age,f in (("Calf",0.55),("Adult",1.0),("Elder",1.15)):
        s=s0*f
        def b(col,s=s,m=m):
            leg=0.3*s
            for x in (-0.25*s,0.25*s):
                for y in (-0.3*s,0.3*s): box(col,0.12*s,0.12*s,leg,x,y,0,DARK).name="Leg"
            box(col,0.7*s,1.0*s,0.5*s,0,0,leg,m).name="Body"
            box(col,0.4*s,0.35*s,0.35*s,0,-0.6*s,leg+0.35*s,m).name="Head"
        asset(f"Mob_YTM_{ln}_{age}","mob",f"~{s:.2f} m",b)
# ---- FOOD loop: products (8) + raw/cooked dishes 8x2 + crops 10 x3 stages = 54
PROD=[("Milk","#FFFFFF"),("Wool","#F4F4F4"),("Egg","#F4EFE2"),("Bacon","#C8505A"),("Cheese","#F2C230"),("Feather","#D9C24A"),("Hide","#6A4A32"),("GlowFleece","#C8B8F0")]
for pn,pc in PROD: asset(f"Item_YTM_Prod_{pn}","item","~0.25 m",lambda col,m=mat("P_"+pn,pc):box(col,0.22,0.22,0.2,0,0,0,m))
DISH=[("Stew","#A0522D"),("Omelet","#F2D22E"),("Pie","#D6A35C"),("Porridge","#E8DCC0"),("Roast","#8A3A2A"),("Soup","#C87A3A"),("Salad","#7CCB4A"),("Bread","#D6A35C")]
for dn,dc in DISH:
    for st,c in (("Raw","#C0B0A0"),("Cooked",dc)):
        asset(f"Item_YTM_Food_{dn}_{st}","item","~0.25 m",lambda col,m=mat(f"F_{dn}_{st}",c):(box(col,0.3,0.3,0.06,0,0,0,STONE),box(col,0.22,0.22,0.12,0,0,0.06,m)))
CROPS=[("Clover","#3FAF4A"),("Groat","#D8B65A"),("Kelpweed","#2F7F6F"),("Bitroot","#B0304A"),("Spudlet","#C9A36A"),("Moonbean","#C8C0F0"),("Reedcorn","#E8C840"),("Saltgrass","#A8C8A0"),("Pumplet","#E88A28"),("Chordberry","#B03CB0")]
for cn,cc in CROPS:
    for st in (1,2,3):
        asset(f"Prop_YTM_Crop_{cn}_S{st}","prop",f"~{0.1+0.2*st:.1f} m",lambda col,m=mat("C_"+cn,cc),st=st:(box(col,0.9,0.9,0.1,0,0,0,SOIL),[box(col,0.12+0.03*st,0.12+0.03*st,0.15*st,x,y,0.1,m) for x in (-0.25,0.25) for y in (-0.25,0.25)]))
# ---- DRINKABLE WATER (mandatory): sources, treatment, containers = 30
WS=[("Well",1.6),("Spring",0.6),("Cistern",2.0),("RainBarrel",1.2),("HandPump",1.3),("Fountain",1.8),("Filter",1.4),("Boiler",1.2),("Aqueduct",2.5),("Pool",0.4)]
for wn,h in WS:
    for v in (1,2):
        def b(col,h=h,v=v):
            box(col,1.4,1.4,h*0.7,0,0,0,STONE if v==1 else WOOD)
            box(col,1.1,1.1,0.08,0,0,h*0.7-0.1,WATER if wn not in("Filter","Boiler") else CLEAN)
            if wn in("Well","HandPump","Boiler"): box(col,0.15,0.15,h*0.3,0.5,0,h*0.7,BRASS)
        asset(f"Prop_YTM_Water_{wn}_V{v}","prop",f"~{h:.1f} m",b)
for cn,s in (("Cup",0.12),("Canteen",0.25),("Jug",0.35),("Bucket",0.4),("Flask",0.2)):
    for st,c in (("Empty",None),("Full",CLEAN)):
        asset(f"Item_YTM_{cn}_{st}","item",f"~{s:.2f} m",lambda col,s=s,c=c:(box(col,s,s,s,0,0,0,WOOD),c and box(col,s*0.8,s*0.8,0.02,0,0,s-0.01,c)))
# ---- ISLAND KIT (double size 240 m): terrain, rocks, cliffs, stations = rest to 500
for k in range(1,9):
    asset(f"Prop_YTM_Station_{['Brewbench','Stove','Smelter','Mill','Churn','Press','Loom','Smokehouse'][k-1]}","prop","~1.4 m",
          lambda col,k=k:(box(col,1.2,0.8,0.9,0,0,0,WOOD),box(col,0.6,0.5,0.4,0,0,0.9,[BRASS,STONE,DARK,STONE,WOOD,BRASS,WOOD,DARK][k-1])))
for bn,sz in (("Barn",6),("Coop",2.2),("Stable",4),("PigPen",3),("Silo",3)):
    asset(f"Bld_YTM_{bn}","building",f"~{sz} m",lambda col,s=sz:(box(col,s,s*0.8,s*0.6,0,0,0,WOOD),box(col,s*1.1,s*0.9,s*0.15,0,0,s*0.6,mat("Roof","#B03A2E"))))
for i in range(4): asset(f"Prop_YTM_Fence_V{i+1}","prop","~1 m",lambda col,i=i:[box(col,0.12,0.12,1.0,x,0,0,WOOD) for x in (-0.5,0.5)]+[box(col,1.1,0.08,0.1,0,0,z,WOOD) for z in (0.3,0.7)][:2+i%2])
ROCKC=["#8C8C94","#6E6A64","#A89F8C","#5A6470","#7A8A70"]
n=0
while len(made)<500:
    n+=1; kind=["Rock","Cliff","Boulder","Stump","Bush","Log"][n%6]; c=ROCKC[n%5]
    s=random.uniform(0.6,4.0) if kind in("Rock","Boulder") else random.uniform(3,10) if kind=="Cliff" else random.uniform(0.5,1.5)
    m=mat(f"Kit_{kind}_{n%5}",c if kind in("Rock","Cliff","Boulder") else ("#3F7A2E" if kind=="Bush" else "#6A4A32"))
    def b(col,s=s,m=m,seed=n):
        r=random.Random(seed)
        for j in range(r.randint(2,4)):
            w=s*r.uniform(0.5,1.0); box(col,w,w*r.uniform(0.6,1.0),s*r.uniform(0.3,0.7),r.uniform(-0.2,0.2)*s,r.uniform(-0.2,0.2)*s,0,m,r.uniform(0,1.5))
    asset(f"Prop_YTM_{kind}_K{n:03d}","prop",f"~{s:.1f} m",b)
os.makedirs(os.path.dirname(LOG),exist_ok=True); json.dump(made,open(LOG,"w"),indent=1); print("MADE",len(made))
