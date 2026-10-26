# youtube-master polish pass v3: herbs, livestock, water, stations. Same names as batch 1 (re-export, rows -> READY).
# BRIEF: metres, origin bottom centre, -Y front, <=3 flat slots, blocky bevelled boxes, one collection per asset.
import bpy, os, json, math, random
OUT = r"C:\Users\730ri\projects\bot-team\art\glb"
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\polish_v3.json"
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

LEAF=mat("Leaf","#4FA84A"); CERAM=mat("Ceramic","#E8DCC0"); GLASS=mat("Glass","#BFE8F0",0.2)
# ---- CROPS v3: tilled bed with furrows, stage plants with species shapes
CROPS=[("Clover","#3FAF4A","leafy"),("Groat","#D8B65A","grain"),("Kelpweed","#2F7F6F","frond"),("Bitroot","#B0304A","root"),("Spudlet","#C9A36A","root"),
 ("Moonbean","#C8C0F0","vine"),("Reedcorn","#E8C840","grain"),("Saltgrass","#A8C8A0","grain"),("Pumplet","#E88A28","gourd"),("Chordberry","#B03CB0","bush")]
for cn,cc,shape in CROPS:
    m=mat("C_"+cn,cc,0.6 if cn in("Moonbean","Chordberry") else 0)
    for st in (1,2,3):
        def b(col,m=m,st=st,shape=shape):
            box(col,1.0,1.0,0.12,0,0,0,SOIL)
            for x in (-0.25,0.25): box(col,0.18,0.95,0.05,x,0,0.12,SOIL,bev=0.3)
            for x in (-0.25,0.25):
                for y in (-0.3,0.0,0.3):
                    z=0.17; h=0.1*st+0.05
                    box(col,0.04,0.04,h,x,y,z,STEM,bev=0)
                    if shape in("leafy","frond","vine"):
                        for k in range(2+st): box(col,0.12+0.03*st,0.04,0.02,x+0.06*math.cos(k*2.1),y+0.06*math.sin(k*2.1),z+h*0.5+0.03*k,LEAF if st<3 else m,rz=k*2.1,rx=0.4)
                    elif shape=="grain":
                        box(col,0.05,0.05,0.06*st,x,y,z+h,m,bev=0.2)
                    elif shape=="root":
                        box(col,0.14,0.04,0.03,x,y,z+h,LEAF,rz=0.6,rx=0.4); 
                        if st==3: box(col,0.12,0.12,0.1,x,y,z-0.02,m)
                    elif shape=="gourd":
                        box(col,0.2,0.05,0.02,x,y,z+0.02,LEAF); 
                        if st>=2: box(col,0.08*st,0.08*st,0.06*st,x+0.05,y,z,m)
                    else:
                        box(col,0.1*st,0.1*st,0.08*st,x,y,z+h*0.6,LEAF)
                        if st==3: [box(col,0.04,0.04,0.04,x+0.06*math.cos(k),y+0.06*math.sin(k),z+h*0.6+0.12,m,bev=0) for k in range(3)]
        asset(f"Prop_YTM_Crop_{cn}_S{st}","prop",f"~{0.15+0.12*st:.2f} m",b)
# ---- ANIMAL PRODUCTS v3
def prod(col,pn,m):
    if pn=="Milk": box(col,0.16,0.16,0.28,0,0,0,CERAM); box(col,0.1,0.1,0.06,0,0,0.28,CERAM); box(col,0.12,0.12,0.02,0,0,0.33,m,bev=0)
    elif pn in("Wool","GlowFleece"): [box(col,0.14,0.14,0.12,0.07*math.cos(k*2.1),0.07*math.sin(k*2.1),0.03*(k%2),m,bev=0.4) for k in range(3)]; box(col,0.12,0.12,0.1,0,0,0.12,m,bev=0.4)
    elif pn=="Egg":
        for k in range(3): box(col,0.08,0.08,0.11,0.06*math.cos(k*2.1),0.06*math.sin(k*2.1),0.03,m,bev=0.4)
        box(col,0.26,0.26,0.05,0,0,0,WOOD)
    elif pn=="Bacon": [box(col,0.24,0.06,0.02,0,(k-1)*0.065,0.02*k,m if k%2 else mat("Fat","#F4D8D0"),bev=0.1) for k in range(3)]
    elif pn=="Cheese": box(col,0.26,0.26,0.14,0,0,0,m,rz=0.785); box(col,0.08,0.26,0.14,0.12,0,0,mat("Rind","#D89A20"),rz=0.785)
    elif pn=="Feather": box(col,0.03,0.03,0.3,0,0,0,CERAM,bev=0); box(col,0.1,0.02,0.22,0,0,0.06,m,bev=0.2)
    else: box(col,0.3,0.24,0.03,0,0,0,m,rz=0.3); box(col,0.2,0.18,0.03,0.04,0.02,0.03,m,rz=-0.2)
for pn,pc in [("Milk","#FFFFFF"),("Wool","#F4F4F4"),("Egg","#F4EFE2"),("Bacon","#C8505A"),("Cheese","#F2C230"),("Feather","#D9C24A"),("Hide","#6A4A32"),("GlowFleece","#C8B8F0")]:
    m=mat("P_"+pn,pc,1.2 if pn=="GlowFleece" else 0)
    asset(f"Item_YTM_Prod_{pn}","item","~0.3 m",lambda col,pn=pn,m=m:prod(col,pn,m))
# ---- DISHES v3: plate/bowl + dish shape; raw = pale, cooked = coloured + garnish
DISH=[("Stew","#A0522D","bowl"),("Omelet","#F2D22E","plate"),("Pie","#D6A35C","pie"),("Porridge","#E8DCC0","bowl"),("Roast","#8A3A2A","roast"),("Soup","#C87A3A","bowl"),("Salad","#7CCB4A","bowl"),("Bread","#D6A35C","loaf")]
for dn,dc,sh in DISH:
    for st in ("Raw","Cooked"):
        c=dc if st=="Cooked" else "#C8B8A8"; m=mat(f"F_{dn}_{st}",c)
        def b(col,m=m,sh=sh,st=st):
            if sh=="bowl":
                box(col,0.26,0.26,0.1,0,0,0,CERAM); box(col,0.22,0.22,0.02,0,0,0.09,m,bev=0)
                if st=="Cooked": [box(col,0.04,0.04,0.03,0.06*math.cos(k*2),0.06*math.sin(k*2),0.1,LEAF,bev=0) for k in range(3)]
            elif sh in("plate","roast"):
                box(col,0.32,0.32,0.03,0,0,0,CERAM)
                box(col,0.2 if sh=="plate" else 0.18,0.16 if sh=="plate" else 0.14,0.04 if sh=="plate" else 0.12,0,0,0.03,m,bev=0.3)
                if st=="Cooked": box(col,0.04,0.04,0.02,0.05,0.03,0.07 if sh=="plate" else 0.15,LEAF,bev=0)
            elif sh=="pie":
                box(col,0.3,0.3,0.06,0,0,0,CERAM); box(col,0.26,0.26,0.06,0,0,0.04,m,bev=0.2)
                if st=="Cooked": [box(col,0.24,0.02,0.01,0,0,0.1,mat("Crust","#B07A3A"),rz=k*0.785,bev=0) for k in range(4)]
            else:
                box(col,0.3,0.16,0.14,0,0,0,m,bev=0.4)
                if st=="Cooked": [box(col,0.03,0.12,0.01,(k-1)*0.08,0,0.14,mat("Crust","#B07A3A"),bev=0) for k in range(3)]
        asset(f"Item_YTM_Food_{dn}_{st}","item","~0.25 m",b)
# ---- CONTAINERS v3
for cn,s in (("Cup",0.12),("Canteen",0.25),("Jug",0.35),("Bucket",0.4),("Flask",0.2)):
    for st in ("Empty","Full"):
        def b(col,cn=cn,s=s,st=st):
            body=WOOD if cn in("Cup","Bucket") else (GLASS if cn=="Flask" else CERAM)
            if cn=="Canteen": box(col,s,s*0.4,s,0,0,0,body); box(col,s*0.2,s*0.2,s*0.15,0,0,s,DARK); box(col,s*1.1,0.02,0.02,0,0,s*0.9,DARK,bev=0)
            elif cn=="Flask": box(col,s,s,s*0.6,0,0,0,body); box(col,s*0.35,s*0.35,s*0.5,0,0,s*0.6,body); box(col,s*0.3,s*0.3,s*0.1,0,0,s*1.1,WOOD)
            elif cn=="Jug": box(col,s*0.8,s*0.8,s*0.8,0,0,0,body); box(col,s*0.4,s*0.4,s*0.25,0,0,s*0.8,body); box(col,0.05,s*0.15,s*0.45,s*0.45,0,s*0.3,body)
            else:
                box(col,s,s,s*0.9,0,0,0,body)
                for z in (s*0.15,s*0.7): box(col,s*1.05,s*1.05,0.02,0,0,z,DARK,bev=0)
                if cn=="Bucket": box(col,0.02,s*1.05,0.02,0,0,s*1.2,DARK,bev=0)
                else: box(col,0.03,s*0.3,s*0.5,s*0.55,0,s*0.2,body)
            if st=="Full": box(col,s*0.7,s*0.7 if cn!="Canteen" else s*0.3,0.015,0,0,(s*0.88 if cn in("Cup","Bucket") else s*0.58),CLEAN,bev=0)
        asset(f"Item_YTM_{cn}_{st}","item",f"~{s:.2f} m",b)
# ---- FARM BUILDINGS v3 (<=15k tris): walls, pitched stepped roof, door, windows
ROOF=mat("Roof","#B03A2E"); TRIM=mat("Trim","#F4EFE2")
for bn,sz in (("Barn",6),("Coop",2.2),("Stable",4),("PigPen",3),("Silo",3)):
    def b(col,bn=bn,s=sz):
        if bn=="Silo":
            for k in range(12): box(col,s*0.3,0.25,s*2.2,s*0.5*math.cos(k*0.524),s*0.5*math.sin(k*0.524),0,STONE,rz=k*0.524+1.571)
            for k in range(4): box(col,s*(1.0-0.22*k),s*(1.0-0.22*k),0.3,0,0,s*2.2+0.3*k,ROOF)
            box(col,0.6,0.1,1.2,0,-s*0.52,0,WOOD); return
        if bn=="PigPen":
            for k in range(8): box(col,0.15,0.15,1.0,s/2*math.cos(k*0.785),s/2*math.sin(k*0.785),0,WOOD)
            box(col,s*0.5,s*0.5,0.9,s*0.15,s*0.15,0,WOOD); box(col,s*0.6,s*0.6,0.1,s*0.15,s*0.15,0.9,ROOF); box(col,s*0.6,s*0.4,0.03,-s*0.15,-s*0.1,0,SOIL,bev=0); return
        h=s*0.55
        box(col,s,s*0.8,h,0,0,0,WOOD)
        for k in range(5): box(col,s*1.1,s*0.8*(1-0.18*k)+0.1,s*0.07,0,0,h+s*0.07*k,ROOF)
        box(col,s*0.3,0.08,h*0.6,0,-s*0.4,0,DARK)
        for x in (-s*0.15,s*0.15): box(col,0.04,0.1,h*0.6,x,-s*0.41,0,TRIM,bev=0)
        for x in (-s*0.35,s*0.35): box(col,s*0.14,0.06,s*0.12,x,-s*0.41,h*0.55,TRIM)
    asset(f"Bld_YTM_{bn}","building",f"~{sz} m",b)
for i in range(4):
    def b(col,i=i):
        for x in (-0.5,0.5): box(col,0.14,0.14,1.0+0.1*(i%2),x,0,0,WOOD); box(col,0.18,0.18,0.06,x,0,1.0+0.1*(i%2),TRIM)
        for z in [(0.3,0.7),(0.25,0.55,0.85),(0.5,),(0.3,0.7)][i]: box(col,1.1,0.06,0.1,0,0,z,WOOD)
        if i==3: box(col,1.0,0.04,0.04,0,0,0.5,WOOD,rx=0,rz=0.0,bev=0)
    asset(f"Prop_YTM_Fence_V{i+1}","prop","~1 m",b)
# ---- HERB PICKUPS + SEED PACKETS v3
HERBS=[("Doleaf","#E8473C"),("Rebell","#F28C28"),("Mimint","#F2D22E"),("Fasage","#7CCB4A"),("Solthorn","#2FBF9F"),("Lavine","#3E8EDE"),
 ("Tisquill","#8A5CE0"),("Sharpcress","#E05CB4"),("Flatfern","#5C7A3E"),("Dronebloom","#B0B8C8"),("Hushmoss","#9FD8C0"),("Gloryroot","#D6A35C")]
PAPER=mat("Paper","#E6DCC4")
for hn,hc in HERBS:
    m=mat("Herb_"+hn,hc)
    def bi(col,m=m):
        box(col,0.04,0.04,0.25,0,0,0,STEM,bev=0); box(col,0.05,0.05,0.02,0,0,0.1,mat("Twine","#C8A060"),bev=0)
        for k in range(5): box(col,0.1,0.04,0.02,0.05*math.cos(k*1.26),0.05*math.sin(k*1.26),0.18+0.02*k,LEAF,rz=k*1.26,rx=0.5)
        box(col,0.08,0.08,0.06,0,0,0.27,m,rz=0.785)
    asset(f"Item_YTM_Herb_{hn}","item","~0.33 m",bi)
    asset(f"Item_YTM_Seed_{hn}","item","~0.16 m",lambda col,m=m:(box(col,0.12,0.03,0.16,0,0,0,PAPER),box(col,0.08,0.035,0.08,0,0,0.05,m,bev=0),box(col,0.12,0.035,0.02,0,0,0.14,m,bev=0)))
os.makedirs(os.path.dirname(LOG),exist_ok=True); json.dump(made,open(LOG,"w"),indent=1); print("MADE",len(made))
