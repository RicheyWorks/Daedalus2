# DiskSaver Island batch generator: blocky assets per BRIEF.md (m units, origin bottom centre, -Y front, flat colours)
import bpy, os, sys, json, math, random
ART = r"C:\Users\730ri\projects\bot-team\art"
OUT = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\glb"
os.makedirs(OUT,exist_ok=True)
LOG = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\batch2.json"
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
    obs=list(col.objects)
    if len(obs)>1:   # one mesh per asset, named after it: Unreal imports one StaticMesh <name> (no stray Cube/Cube.001 parts)
        bpy.context.view_layer.objects.active=obs[0]; bpy.ops.object.join()
    o=col.objects[0]; o.name=name; o.data.name=name
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

import colorsys
def shade(h,k):
    r,g,b,_=hexc(h); hh,l,ss=colorsys.rgb_to_hls(r,g,b); r,g,b=colorsys.hls_to_rgb((hh+0.04*k)%1,min(0.9,max(0.1,l*(0.8+0.15*k))),ss)
    return '#%02X%02X%02X'%(int(r*255),int(g*255),int(b*255))
STEM=mat("DS_Stem","#3E7A2E"); SOIL=mat("DS_Soil","#5A3B22"); WOOD=mat("DS_Wood","#8A5A32"); STONE=mat("DS_Stone","#8C8C94")
WATER=mat("DS_Water","#3A7BD5"); LEAF=mat("DS_Leaf","#3F9F3A"); BARK=mat("DS_Bark","#6B4423"); GRASS=mat("DS_Grass","#5DBB4A")
CROPS=[("Clover","#3FAF4A"),("Groat","#D8B65A"),("Kelpweed","#2F7F6F"),("Bitroot","#B0304A"),("Spudlet","#C9A36A")]
for cn,cc in CROPS:
  for st in (1,2,3):
    for v in range(4):
      m=mat(f"DS_{cn}{v}",shade(cc,v)); h=0.15*st
      asset(f"Prop_DS_Crop_{cn}_S{st}_V{v}","prop","~0.5 m",lambda col,m=m,h=h,st=st:(box(col,0.9,0.9,0.1,0,0,0,SOIL),[box(col,0.1+0.03*st,0.1+0.03*st,h,x,y,0.1,m) for x in (-0.25,0.25) for y in (-0.25,0.25)]))
HERBS=[("CacheLeaf","#4FD18B"),("BufferBloom","#4FA3FF"),("OverclockThorn","#FF8A2A"),("DefragMoss","#B8E05A"),("SwapRoot","#C25BFF"),("ParityPetal","#FFE45C"),("ChecksumClover","#2FBF9F"),("LatencyLily","#9FC8FF"),("ZipVine","#FF5C8A"),("ArchiveSage","#8FA88F")]
for hn,hc in HERBS:
  for st,h in ((1,0.15),(2,0.35),(3,0.6)):
    for v in (1,2,3):
      m=mat(f"DS_{hn}{v}",shade(hc,v))
      def b(col,h=h,m=m,st=st,v=v):
        box(col,0.06,0.06,h,0,0,0,STEM)
        for i in range(st+v):
          a=i*2*math.pi/(st+v); r=0.08+0.04*st
          box(col,0.1,0.1,0.06,r*math.cos(a),r*math.sin(a),h*0.4+0.05*i,m)
        box(col,0.12*st/2+0.1,0.12*st/2+0.1,0.1,0,0,h,m)
      asset(f"Prop_DS_Herb_{hn}_S{st}_V{v}","prop",f"~{h+0.1:.2f} m",b)
for i in range(40):
  s_=0.4+0.15*i; m=mat(f"DS_Rock{i%5}",shade("#8C8C94",i%5-2))
  asset(f"Prop_DS_Rock_{i:02d}","prop",f"~{s_:.1f} m",lambda col,s_=s_,m=m,i=i:(box(col,s_,s_*0.8,s_*0.6,0,0,0,m),box(col,s_*0.6,s_*0.5,s_*0.4,s_*0.15*((i%3)-1),0,s_*0.6,m)))
for i in range(20):
  L=1+(i%4)*0.5; gate=i>=12
  asset(f"Prop_DS_Fence_{'Gate' if gate else 'Seg'}_{i:02d}","prop","~1 m",lambda col,L=L,gate=gate:[box(col,0.12,0.12,1.0,x,0,0,WOOD) for x in (-L/2,L/2)]+[box(col,L,0.08,0.1,0,0,z,WOOD if not gate else STONE) for z in (0.4,0.8)])
FOODS=[("Egg","#F4EFE2"),("GoatMilk","#FFFFFF"),("Stew","#A0522D"),("HerbTea","#6FBF73"),("Bread","#D6A35C"),("Cheese","#F2C94C"),("RoastSpud","#B5803A"),("BitrootSoup","#9E2A3A"),("GroatPorridge","#E6D3A3"),("KelpWrap","#2F6F5F")]
for fn,fc in FOODS:
  for v in range(4):
    m=mat(f"DS_F_{fn}{v}",shade(fc,v)); sz=0.18+0.04*v
    asset(f"Item_DS_Food_{fn}_V{v}","item","~0.25 m",lambda col,m=m,sz=sz:(box(col,sz,sz,sz*0.8,0,0,0,m),box(col,sz*0.6,sz*0.6,sz*0.2,0,0,sz*0.8,m)))
LIV=[("ByteHen","#F2EEE0",0.5),("MossGoat","#7E8F5A",1.0),("TidePig","#E7A0A0",0.8),("CacheCow","#2E2E36",1.6),("DriftDuck","#D9C24A",0.45)]
dk=mat("DS_Dark","#2A2A2A")
for ln,lc,s0 in LIV:
  for v in range(6):
    m=mat(f"DS_{ln}{v}",shade(lc,v-2)); s=s0*(0.6 if v<2 else 1.0+0.05*v)
    def b(col,s=s,m=m):
      leg=0.3*s
      for x in (-0.25*s,0.25*s):
        for y in (-0.3*s,0.3*s): box(col,0.12*s,0.12*s,leg,x,y,0,dk)
      box(col,0.7*s,1.0*s,0.5*s,0,0,leg,m); box(col,0.4*s,0.35*s,0.35*s,0,-0.6*s,leg+0.35*s,m)
    asset(f"Mob_DS_{ln}_{'Young' if v<2 else 'Adult'}{v}","mob",f"~{s:.1f} m",b)
WP=[("Well",lambda col:(box(col,1.4,1.4,0.8,0,0,0,STONE),box(col,1.0,1.0,0.05,0,0,0.75,WATER),box(col,0.1,0.1,1.6,-0.6,0,0.8,WOOD),box(col,0.1,0.1,1.6,0.6,0,0.8,WOOD),box(col,1.5,1.5,0.15,0,0,2.4,WOOD))),
    ("CisternBarrel",lambda col:(box(col,0.8,0.8,1.1,0,0,0,WOOD),box(col,0.7,0.7,0.05,0,0,1.08,WATER))),
    ("FilterBarrel",lambda col:(box(col,0.7,0.7,1.0,0,0,0,WOOD),box(col,0.6,0.6,0.2,0,0,1.0,mat("DS_Sand","#D9C38A")),box(col,0.2,0.1,0.1,0,-0.4,0.15,STONE))),
    ("Canteen",lambda col:(box(col,0.18,0.08,0.24,0,0,0,mat("DS_Leather","#7A5230")),box(col,0.05,0.05,0.05,0,0,0.24,STONE))),
    ("Bucket",lambda col:(box(col,0.3,0.3,0.3,0,0,0,WOOD),box(col,0.26,0.26,0.03,0,0,0.27,WATER))),
    ("SpringRocks",lambda col:(box(col,2.0,1.6,0.5,0,0,0,STONE),box(col,1.0,0.8,0.06,0,0,0.47,WATER),box(col,0.6,0.6,0.9,0.6,0.3,0,STONE))),
    ("Gutter",lambda col:(box(col,2.0,0.2,0.1,0,0,1.8,WOOD),box(col,0.1,0.1,1.8,0.95,0,0,WOOD))),
    ("PondEdge",lambda col:(box(col,3.0,3.0,0.2,0,0,0,STONE),box(col,2.6,2.6,0.05,0,0,0.18,WATER)))]
for wn,wb in WP:
  for v in range(5):
    asset(f"Prop_DS_Water_{wn}_V{v}","prop","~1 m",wb)
TILES=[("Grass",GRASS),("Dirt",SOIL),("Sand",mat("DS_Sand","#D9C38A")),("Stone",STONE),("Moss",mat("DS_MossT","#6F8F3A")),("Clay",mat("DS_Clay","#B5683A"))]
for tn,tm in TILES:
  for v in range(10):
    h=0.5+0.5*(v%5); w=1+(v//5)
    asset(f"Prop_DS_Tile_{tn}_{v}","prop",f"~{w} m",lambda col,h=h,w=w,tm=tm:box(col,w,w,h,0,0,0,tm))
for i in range(40):
  h=2+0.25*i; lm=mat(f"DS_Leaf{i%4}",shade("#3F9F3A",i%4-1))
  asset(f"Prop_DS_Tree_{i:02d}","prop",f"~{h:.1f} m",lambda col,h=h,lm=lm,i=i:(box(col,0.3,0.3,h*0.6,0,0,0,BARK),box(col,h*0.55,h*0.55,h*0.38,0,0,h*0.55,lm),[box(col,h*0.32,h*0.32,h*0.26,dx*h*0.3,dy*h*0.3,h*0.5,lm) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))],box(col,h*0.34,h*0.34,h*0.22,0,0,h*0.9,lm),box(col,h*0.18,h*0.18,h*0.12,0,0,h*1.08,lm) if i%2 else None))
MISC=[("Campfire",lambda col:(box(col,0.8,0.8,0.15,0,0,0,STONE),box(col,0.3,0.3,0.4,0,0,0.15,mat("DS_Fire","#FF7A1A")))),
      ("Cauldron",lambda col:(box(col,0.7,0.7,0.6,0,0,0,dk),box(col,0.6,0.6,0.05,0,0,0.56,WATER))),
      ("Haystack",lambda col:box(col,1.2,1.2,1.0,0,0,0,mat("DS_Hay","#E2C25A"))),
      ("FeedSack",lambda col:box(col,0.4,0.3,0.5,0,0,0,mat("DS_Sack","#C8B48A"))),
      ("CompostBin",lambda col:(box(col,1.0,1.0,0.8,0,0,0,WOOD),box(col,0.9,0.9,0.1,0,0,0.75,SOIL)))]
for mn,mb in MISC:
  for v in range(4):
    asset(f"Prop_DS_{mn}_V{v}","prop","~1 m",mb)
os.makedirs(os.path.dirname(LOG),exist_ok=True)
json.dump(made,open(LOG,"w"),indent=1)
print("MADE",len(made))
