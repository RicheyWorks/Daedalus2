# youtube-master polish pass v2: herbs, livestock, water, stations. Same names as batch 1 (re-export, rows -> READY).
# BRIEF: metres, origin bottom centre, -Y front, <=3 flat slots, blocky bevelled boxes, one collection per asset.
import bpy, os, json, math, random
OUT = r"C:\Users\730ri\projects\bot-team\art\glb"
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\polish_v2.json"
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
# ---- HERBS v2: stem + leaf fans that grow per stage + flower head (note colour, glowing at S4)
HERBS=[("Doleaf","#E8473C"),("Rebell","#F28C28"),("Mimint","#F2D22E"),("Fasage","#7CCB4A"),("Solthorn","#2FBF9F"),("Lavine","#3E8EDE"),
 ("Tisquill","#8A5CE0"),("Sharpcress","#E05CB4"),("Flatfern","#5C7A3E"),("Dronebloom","#B0B8C8"),("Hushmoss","#9FD8C0"),("Gloryroot","#D6A35C")]
LEAF=mat("Leaf","#4FA84A")
for i,(hn,hc) in enumerate(HERBS):
    flower=mat("Herb_"+hn,hc); glow=mat("HerbGlow_"+hn,hc,1.5)
    for st in (1,2,3,4):
        h=0.1+0.17*st
        def b(col,h=h,st=st,i=i,flower=flower,glow=glow):
            box(col,0.05,0.05,h,0,0,0,STEM,bev=0)
            tiers=st+1
            for t in range(tiers):
                z=0.04+h*0.75*t/tiers; L=0.14+0.05*st-0.03*t
                for k in range(3+(i%3)):
                    a=2*math.pi*k/(3+(i%3))+t*0.5
                    box(col,L,0.06,0.025,L/2*math.cos(a),L/2*math.sin(a),z,LEAF,rz=a,rx=0.35,bev=0.2)
            if st>=2:
                s=0.06+0.03*st
                box(col,s,s,s*0.7,0,0,h,glow if st==4 else flower,rz=0.785)
                if st>=3:
                    for k in range(4): box(col,s*0.6,s*0.25,s*0.2,s*0.55*math.cos(k*1.571),s*0.55*math.sin(k*1.571),h+s*0.2,glow if st==4 else flower,rz=k*1.571)
        asset(f"Prop_YTM_Herb_{hn}_S{st}","prop",f"~{h+0.15:.2f} m",b)
# ---- LIVESTOCK v2: legs, body, head with snout/ears, tail; species features (horns, wool, comb, glow); parts named for anim
LIV=[("Mooncalf","#E8E2D0",1.5,"horns"),("ReefSheep","#F4F4F4",1.0,"wool"),("BubbleHen","#F2EEE0",0.45,"bird"),("Kelpig","#E7A0A0",0.8,"snout"),
 ("DriftGoat","#7E8F5A",0.95,"horns"),("StormDuck","#D9C24A",0.4,"bird"),("Hornox","#6A4A32",1.8,"bighorns"),("Glowllama","#C8B8F0",1.6,"neck")]
for ln,lc,s0,feat in LIV:
    m=mat("Liv_"+ln,lc); acc=mat("LivAcc_"+ln,{"wool":"#FFFFFF","bird":"#E8473C","neck":"#C8B8F0"}.get(feat,"#D8C8A0"),1.2 if feat=="neck" else 0)
    for age,f in (("Calf",0.55),("Adult",1.0),("Elder",1.15)):
        s=s0*f
        def b(col,s=s,m=m,acc=acc,feat=feat):
            if feat=="bird":
                for x in (-0.12*s,0.12*s): box(col,0.06*s,0.06*s,0.35*s,x,0,0,acc,bev=0,name="Leg")
                box(col,0.6*s,0.75*s,0.5*s,0,0.05*s,0.35*s,m,name="Body")
                box(col,0.3*s,0.3*s,0.3*s,0,-0.35*s,0.75*s,m,name="Head")
                box(col,0.12*s,0.18*s,0.08*s,0,-0.55*s,0.85*s,acc,name="Head_Beak")
                box(col,0.06*s,0.2*s,0.12*s,0,-0.35*s,1.05*s,acc,name="Head_Comb")
                for x in (-0.32*s,0.32*s): box(col,0.06*s,0.5*s,0.3*s,x,0.05*s,0.45*s,m,name="Wing")
                return
            leg=0.35*s
            for x in (-0.25*s,0.25*s):
                for y in (-0.3*s,0.3*s): box(col,0.13*s,0.13*s,leg,x,y,0,DARK,bev=0.1,name="Leg")
            body_w=0.85*s if feat=="wool" else 0.7*s
            box(col,body_w,1.0*s,0.5*s,0,0,leg,m,name="Body")
            if feat=="wool":
                for k in range(6): box(col,0.3*s,0.3*s,0.2*s,(k%2-0.5)*0.4*s,(k//2-1)*0.3*s,leg+0.45*s,acc,name="Body_Wool")
            hz=leg+0.35*s; hy=-0.6*s
            if feat=="neck":
                box(col,0.22*s,0.22*s,0.6*s,0,-0.45*s,leg+0.3*s,m,name="Neck"); hz=leg+0.85*s; hy=-0.55*s
            box(col,0.38*s,0.35*s,0.34*s,0,hy,hz,m,name="Head")
            box(col,0.24*s,0.15*s,0.16*s,0,hy-0.22*s,hz+0.02*s,acc if feat=="snout" else DARK,name="Head_Snout")
            for x in (-0.2*s,0.2*s): box(col,0.08*s,0.05*s,0.14*s,x,hy+0.05*s,hz+0.3*s,m,rz=0.3,name="Head_Ear")
            if feat in("horns","bighorns"):
                hl=0.3*s if feat=="bighorns" else 0.18*s
                for x in (-1,1): box(col,hl,0.07*s,0.07*s,x*(0.15*s+hl/2),hy,hz+0.3*s,acc,name="Head_Horn")
            if feat=="neck": box(col,0.5*s,0.6*s,0.04*s,0,0,leg+0.5*s,acc,name="Body_GlowBlanket")
            box(col,0.07*s,0.25*s,0.07*s,0,0.6*s,leg+0.35*s,m,rx=-0.6,name="Tail")
        asset(f"Mob_YTM_{ln}_{age}","mob",f"~{s:.2f} m",b)
# ---- WATER v2: proper shapes per source, glowing clean water for drinkable ones
WS=[("Well",1.6),("Spring",0.6),("Cistern",2.0),("RainBarrel",1.2),("HandPump",1.3),("Fountain",1.8),("Filter",1.4),("Boiler",1.2),("Aqueduct",2.5),("Pool",0.4)]
DRINK={"Well","Spring","HandPump","Fountain","Filter","Boiler"}
for wn,h in WS:
    for v in (1,2):
        mm=STONE if v==1 else WOOD; wm=CLEAN if wn in DRINK else WATER
        def b(col,wn=wn,h=h,mm=mm,wm=wm):
            if wn=="Well":
                for k in range(8): box(col,0.55,0.2,0.8,0.55*math.cos(k*0.785),0.55*math.sin(k*0.785),0,mm,rz=k*0.785+1.571)
                box(col,0.9,0.9,0.05,0,0,0.6,wm,bev=0)
                for x in (-0.6,0.6): box(col,0.1,0.1,1.6,x,0,0.8,WOOD)
                box(col,1.6,1.0,0.12,0,0,2.4,mm,rx=0); box(col,1.4,0.08,0.08,0,0,2.0,WOOD); box(col,0.2,0.2,0.25,0,0,1.5,BRASS)
            elif wn=="Spring":
                for k in range(7): box(col,0.4,0.35,0.3+0.1*(k%3),1.0*math.cos(k*0.9),1.0*math.sin(k*0.9),0,mm,rz=k)
                box(col,1.6,1.6,0.04,0,0,0.1,wm,bev=0); box(col,0.25,0.25,0.5,0,0,0.1,wm,bev=0.3)
            elif wn=="HandPump":
                box(col,1.2,0.8,0.4,0,0.2,0,mm); box(col,1.0,0.6,0.04,0,0.2,0.36,wm,bev=0)
                box(col,0.18,0.18,1.2,0,-0.3,0,BRASS); box(col,0.08,0.4,0.08,0,-0.3,1.1,BRASS,rx=0.3); box(col,0.6,0.06,0.06,0.3,-0.3,1.2,DARK,rz=0)
            elif wn=="Fountain":
                box(col,2.0,2.0,0.45,0,0,0,mm); box(col,1.7,1.7,0.04,0,0,0.42,wm,bev=0)
                box(col,0.35,0.35,1.2,0,0,0.45,mm); box(col,0.9,0.9,0.15,0,0,1.5,mm); box(col,0.3,0.3,0.3,0,0,1.65,wm,bev=0.3)
            elif wn in("Filter","Boiler"):
                box(col,1.0,1.0,0.3,0,0,0,mm)
                box(col,0.7,0.7,0.9,0,0,0.3,BRASS if wn=="Boiler" else mm); box(col,0.15,0.15,0.6,0.45,0,0.9,BRASS)
                box(col,0.5,0.5,0.04,0,0,1.2,wm,bev=0)
                if wn=="Boiler": box(col,0.4,0.4,0.3,0,0,0,DARK)
            elif wn in("Cistern","RainBarrel"):
                r=0.5 if wn=="RainBarrel" else 0.9
                for k in range(10): box(col,r*0.65,0.12,h*0.8,r*math.cos(k*0.628),r*math.sin(k*0.628),0,mm,rz=k*0.628+1.571)
                for z in (0.15,h*0.65): box(col,2*r+0.1,0.06,0.06,0,0,z,DARK,bev=0)
                box(col,r*1.6,r*1.6,0.04,0,0,h*0.75,wm,bev=0)
            elif wn=="Aqueduct":
                for x in (-1.2,1.2): box(col,0.5,0.6,2.0,x,0,0,mm)
                box(col,3.0,0.8,0.4,0,0,2.0,mm); box(col,3.0,0.5,0.05,0,0,2.38,wm,bev=0)
            else:
                for k in range(10): box(col,0.6,0.3,0.25,1.4*math.cos(k*0.628),1.4*math.sin(k*0.628),0,mm,rz=k*0.628+1.571)
                box(col,2.6,2.6,0.04,0,0,0.12,wm,bev=0)
        asset(f"Prop_YTM_Water_{wn}_V{v}","prop",f"~{h:.1f} m",b)
# ---- STATIONS v2
ST=["Brewbench","Stove","Smelter","Mill","Churn","Press","Loom","Smokehouse"]
FIRE=mat("Fire","#FF8A2A",3.0); TON=mat("TonicGlow","#8A5CE0",2.0)
def station(col,k):
    if k=="Brewbench":
        box(col,1.4,0.7,0.85,0,0,0,WOOD); box(col,1.5,0.8,0.08,0,0,0.85,WOOD)
        for i in range(4): box(col,0.14,0.14,0.22,-0.5+i*0.33,0.1,0.93,TON,bev=0.1)
        box(col,0.4,0.4,0.35,0.45,-0.1,0.93,BRASS)
        for i in range(12): box(col,0.08,0.03,0.12,-0.6+i*0.11,0.3,1.3,TON if i%2 else BRASS,bev=0)
        for x in (-0.7,0.7): box(col,0.06,0.06,0.5,x,0.3,0.93,WOOD)
    elif k in("Stove","Smelter","Smokehouse"):
        w={"Stove":1.0,"Smelter":1.2,"Smokehouse":1.6}[k]
        box(col,w,w,w*0.8,0,0,0,STONE); box(col,w*0.5,0.05,w*0.3,0,-w/2,0.15,FIRE,bev=0)
        box(col,0.25,0.25,w*0.9,w*0.3,w*0.3,w*0.8,STONE); box(col,w*1.05,w*1.05,0.1,0,0,w*0.8,DARK)
    elif k=="Mill":
        box(col,1.0,1.0,0.5,0,0,0,STONE); box(col,0.9,0.9,0.15,0,0,0.5,STONE,rz=0.4); box(col,0.1,1.2,0.1,0,0,0.9,WOOD); box(col,0.15,0.15,0.4,0,0,0.6,WOOD)
    elif k=="Churn":
        box(col,0.5,0.5,0.9,0,0,0,WOOD); [box(col,0.55,0.55,0.05,0,0,z,DARK,bev=0) for z in (0.15,0.7)]; box(col,0.06,0.06,0.6,0,0,0.9,WOOD)
    elif k=="Press":
        for x in (-0.5,0.5): box(col,0.15,0.15,1.4,x,0,0,WOOD)
        box(col,1.2,0.2,0.2,0,0,1.3,WOOD); box(col,0.7,0.7,0.4,0,0,0,WOOD); box(col,0.1,0.1,0.8,0,0,0.5,BRASS)
    else:
        for x in (-0.6,0.6): box(col,0.12,0.6,1.3,x,0,0,WOOD)
        box(col,1.3,0.12,0.12,0,0,1.25,WOOD); box(col,1.0,0.05,0.8,0,0,0.4,mat("Cloth","#C8B8F0"),bev=0)
for k in ST: asset(f"Prop_YTM_Station_{k}","prop","~1.4 m",lambda col,k=k:station(col,k))
os.makedirs(os.path.dirname(LOG),exist_ok=True); json.dump(made,open(LOG,"w"),indent=1); print("MADE",len(made))
