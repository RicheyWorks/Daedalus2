# Prometheus Island hero render, headless Blender (Cycles). Layout ported 1:1 from pi_place.py (UE cm -> Blender m, Y mirrored).
# usage: blender -b -P pi_blender_hero.py -- OUT.png [samples] [res_pct]
import bpy, json, math, random, os, sys, glob
A=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
OUT=A[0] if A else "PI_hero_blender.png"; SAMP=int(A[1]) if len(A)>1 else 128; PCT=int(A[2]) if len(A)>2 else 100
HERE=os.path.dirname(os.path.abspath(__file__)); D=os.path.normpath(HERE+"/../../../data/islands/prometheus")+"/"
COATS="C:/Users/730ri/projects/bot-team/art/coats8/"
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
man=[]
for f in sorted(glob.glob(D+"manifest_*.json")): man+=json.load(open(f))
I=json.load(open(D+"island.json")); HM=json.load(open(D+"heights.json")); N=I["N"]; S=I["size_m"]*100.0; P=I["peak_m"]*100.0
def hz(lx,ly):
    j=(lx/S+0.5)*(N-1); i=(ly/S+0.5)*(N-1)
    if not (0<=i<N-1 and 0<=j<N-1): return None
    i0,j0=int(i),int(j); fi,fj=i-i0,j-j0
    h=HM[i0][j0]*(1-fi)*(1-fj)+HM[i0][j0+1]*(1-fi)*fj+HM[i0+1][j0]*fi*(1-fj)+HM[i0+1][j0+1]*fi*fj
    return None if h<=0.06 else h*P
def L(lx,ly,dz=0):
    z=hz(lx,ly); return None if z is None else (lx/100.0,-ly/100.0,(z+dz)/100.0)
def mat(n,rgb,rough=0.8,metal=0.0,emit=0.0,tex=None):
    m=bpy.data.materials.new(n); m.use_nodes=True; b=m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value=(*rgb,1); b.inputs["Roughness"].default_value=rough; b.inputs["Metallic"].default_value=metal
    if emit: b.inputs["Emission Color"].default_value=(*rgb,1); b.inputs["Emission Strength"].default_value=emit
    if tex:
        t=m.node_tree.nodes.new("ShaderNodeTexImage"); t.image=bpy.data.images.load(tex); m.node_tree.links.new(t.outputs[0],b.inputs["Base Color"])
    return m
PAL={"herb":(0.18,0.40,0.12),"water":(0.10,0.35,0.55),"stock":(0.45,0.30,0.16),"crop":(0.55,0.48,0.18),"tone":(0.30,0.30,0.34),
     "rock":(0.25,0.24,0.23),"tree":(0.08,0.25,0.10),"fungus":(0.50,0.30,0.14),"music":(0.06,0.05,0.05)}
MAT={k:mat("M_"+k,v,0.3 if k=="music" else 0.8,0.6 if k=="music" else 0) for k,v in PAL.items()}
WATER=mat("M_Water",(0.05,0.30,0.45),0.05); WATER.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value=0.6
GROUND=mat("M_Ground",(0.06,0.11,0.035),0.95)
HERBC=[mat("M_HerbPC%02d"%i,tuple(0.15+0.5*x for x in (0.5+0.5*math.cos(i*0.5236),0.6,0.5+0.5*math.sin(i*0.5236))),0.6) for i in range(12)]
coatpng=sorted(glob.glob(COATS+"T_Coat_*.png")); CM=[mat("M_Coat%d"%k,(1,1,1),0.7,tex=p) for k,p in enumerate(coatpng)]
# terrain from heightmap (same grid UE used)
import bmesh
me=bpy.data.meshes.new("Terrain"); bm=bmesh.new(); V={}
for i in range(N):
    for j in range(N):
        lx=(j/(N-1)-0.5)*S; ly=(i/(N-1)-0.5)*S; h=HM[i][j]; V[i,j]=bm.verts.new((lx/100,-ly/100,(h*P if h>0.06 else -300)/100))
for i in range(N-1):
    for j in range(N-1): bm.faces.new((V[i,j],V[i,j+1],V[i+1,j+1],V[i+1,j]))
bm.to_mesh(me); bm.free(); T=bpy.data.objects.new("PI_Terrain",me); sc.collection.objects.link(T); T.data.materials.append(GROUND)
for p in me.polygons: p.use_smooth=True
bpy.ops.mesh.primitive_plane_add(size=4000,location=(0,0,-1.5)); sea=bpy.context.object; sea.data.materials.append(WATER)
# item import cache (one FBX import per item, reused via linked duplicates)
SRC={}
def src(m):
    if m["name"] in SRC: return SRC[m["name"]]
    before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=D+"fbx/"+m["name"]+".fbx")
    new=[o for o in bpy.data.objects if o not in before and o.type=="MESH"]
    for o in bpy.data.objects:
        if o not in before and o.type!="MESH": bpy.data.objects.remove(o)
    if not new: SRC[m["name"]]=None; return None
    if len(new)>1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in new: o.select_set(True)
        bpy.context.view_layer.objects.active=new[0]; bpy.ops.object.join()
    o=new[0]; o.parent=None; o.hide_render=True; o.hide_viewport=True; SRC[m["name"]]=o; return o
n=0
def put(m,loc,yaw=0,mt=None,s=1.0):
    global n
    if loc is None: return
    o0=src(m) if isinstance(m,dict) else m
    if o0 is None: return
    o=o0.copy(); sc.collection.objects.link(o); o.hide_render=False; o.hide_viewport=False
    o.location=loc; o.rotation_euler=(o0.rotation_euler[0],o0.rotation_euler[1],math.radians(-yaw)); o.scale=tuple(v*s for v in o0.scale)
    if mt:
        o.data=o0.data.copy(); o.data.materials.clear(); o.data.materials.append(mt)
        for ms in o.material_slots: ms.link="OBJECT"; ms.material=mt
    n+=1; return o
by={}
for m in man: by.setdefault(m["cat"],[]).append(m)
rnd=random.Random(15)
def path(t):
    i=N*(0.62-0.4*t); j=N*(0.40+0.32*t+0.06*math.sin(t*9)); return ((j/(N-1)-0.5)*S,(i/(N-1)-0.5)*S)
W_=lambda k:[m for m in by.get("water",[]) if m.get("kind")==k]
sx,sy=path(0); put(W_("SpringBasin")[0],L(sx,sy,-20),0,WATER)
for k,m in enumerate(W_("SpringBasin")[1:]): put(m,L(sx+300*(k+1),sy+200,-20),k*40,MAT["rock"],0.6)
segs=W_("StreamSeg")
for k,m in enumerate(segs):
    t=(k+0.5)/len(segs); x,y=path(t); x2,y2=path(min(1,t+0.02)); put(m,L(x,y,-15),math.degrees(math.atan2(y2-y,x2-x)),WATER,1.6)
cx_,cy_=path(0.55); cx_+=1800
for k,m in enumerate(W_("Cistern")): put(m,L(cx_+k*420,cy_,0),0,MAT["rock"])
for k,m in enumerate(W_("Pipe")): put(m,L(cx_+300+k*300,cy_+700,30),0,MAT["music"])
penx,peny=cx_+5200,cy_+600
for k,m in enumerate(W_("Trough")): put(m,L(penx+(k%6)*500-1250,peny+(k//6)*2600-1300,0),90*(k//6),WATER)
for k,m in enumerate(W_("RainCatcher")): a=k*0.5236; put(m,L(cx_-2600+2200*math.cos(a),cy_+2200*math.sin(a),0),0,MAT["music"])
ex,ey=path(1.0)
for k,m in enumerate(W_("StillPart")): put(m,L(ex+(k%5)*260-520,ey-900+(k//5)*240,0),0,WATER)
# heart: jukebox stand-in (UE jukebox is an editor-only asset) + presser, vinyl, speakers, lanterns
hx,hy=-2500.0,1500.0; hl=L(hx,hy,0)
if hl:
    bpy.ops.mesh.primitive_cube_add(size=1,location=(hl[0],hl[1],hl[2]+1.0)); jb=bpy.context.object; jb.scale=(1.2,0.7,2.0); jb.data.materials.append(mat("M_Juke",(1.0,0.45,0.12),0.3,0.2,4.0))
mus=by.get("music",[])
for k,m in enumerate([m for m in mus if m["kind"]=="PressPlate"]): put(m,L(hx+600+k*260,hy-500,0),0,MAT["music"])
for k,m in enumerate([m for m in mus if m["kind"]=="Vinyl"]): put(m,L(hx+600+k*60,hy-250,95),0,MAT["music"])
for k,m in enumerate([m for m in mus if m["kind"]=="Speaker"]): a=k*1.047; put(m,L(hx+900*math.cos(a),hy+900*math.sin(a),0),math.degrees(a)+90,MAT["music"])
LAMP=mat("M_Lamp",(1.0,0.6,0.25),0.4,0,8.0)
for k,m in enumerate([m for m in mus if m["kind"]=="Lantern"]): a=k*1.571+0.78; put(m,L(hx+1300*math.cos(a),hy+1300*math.sin(a),0),0,LAMP)
# harmonic herb garden, circle of fifths
gx,gy=-2500.0,-4500.0; herbs=by.get("herb",[])
for pos in range(12):
    pc=(pos*7)%12; a=pos*0.5236; bx,by_=gx+2000*math.cos(a),gy+2000*math.sin(a)
    for q,m in enumerate([m for m in herbs if m["pc"]==pc]): put(m,L(bx+(q%3)*70-70,by_+(q//3)*70-70,0),rnd.uniform(0,360),HERBC[pc],1.6)
for k,m in enumerate(by.get("tone",[])): a=k*0.1047; put(m,L(gx+3200*math.cos(a),gy+3200*math.sin(a),0),math.degrees(a),MAT["tone"],1.3)
# pens, farm, livestock (coated stand-ins), crops
st=by.get("stock",[])
for k,m in enumerate([m for m in st if m["kind"]=="PenFence"]):
    side=k//5; i=k%5; dx,dy=[(i*500-1000,-1500),(1500,i*600-1200),(i*500-1000,1500),(-1500,i*600-1200)][side]
    put(m,L(penx+dx,peny+dy,0),0 if side%2==0 else 90,MAT["stock"])
for k,m in enumerate([m for m in st if m["kind"]!="PenFence"]): put(m,L(penx+2600+(k%8)*450,peny-1600+(k//8)*700,0),rnd.uniform(0,360),MAT["stock"])
for k in range(16):
    p=L(penx+rnd.uniform(-1100,1100),peny+rnd.uniform(-1100,1100),70)
    if p and CM:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6,location=p); o=bpy.context.object; o.scale=(1.5,0.8,0.8); o.rotation_euler[2]=rnd.uniform(0,6.28); o.data.materials.append(CM[k%len(CM)]); bpy.ops.object.shade_smooth()
for k,m in enumerate(by.get("crop",[])): put(m,L(penx-4200+(k%12)*300,peny-2600+(k//12)*350,0),0,MAT["crop"],1.5)
def scatter(cat,mt,rmin,rmax,s):
    for k,m in enumerate(by.get(cat,[])):
        for _ in range(20):
            a=rnd.uniform(0,6.283); r=rnd.uniform(rmin,rmax); p=L(r*math.cos(a),r*math.sin(a),0)
            if p: put(m,p,rnd.uniform(0,360),mt,s); break
scatter("rock",MAT["rock"],8000,21000,1.5); scatter("tree",MAT["tree"],7000,19000,1.0); scatter("fungus",MAT["fungus"],7000,18000,1.0)
# warm soft light: low golden sun + Nishita sky + heart glow
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True; sky=w.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type="NISHITA"; sky.sun_elevation=math.radians(14); sky.sun_rotation=math.radians(215)
w.node_tree.links.new(sky.outputs[0],w.node_tree.nodes["Background"].inputs[0]); w.node_tree.nodes["Background"].inputs[1].default_value=0.6
bpy.ops.object.light_add(type="SUN",rotation=(math.radians(76),0,math.radians(215))); s=bpy.context.object.data; s.energy=3.0; s.color=(1.0,0.78,0.55); s.angle=math.radians(4)
if hl: bpy.ops.object.light_add(type="POINT",location=(hl[0],hl[1],hl[2]+6)); l=bpy.context.object.data; l.energy=60000; l.color=(1,0.65,0.35); l.shadow_soft_size=4
# hero camera (same framing as UE PI_HeroCam / PI_hero_v2)
CAMX=[float(v) for v in os.environ.get("PIB_CAM","-120,-95,80").split(",")]; TGT=[float(v) for v in os.environ.get("PIB_TGT","-5,15,14").split(",")]
FOC={"pens":(penx,peny),"garden":(gx,gy),"heart":(hx,hy)}.get(os.environ.get("PIB_FOCUS",""))
if FOC and L(*FOC):
    fx,fy,fz=L(*FOC); TGT=[fx,fy,fz+1]; CAMX=[fx-22,fy-18,fz+12]
bpy.ops.object.camera_add(location=CAMX); cam=bpy.context.object; sc.camera=cam; cam.data.lens=35
tgt=bpy.data.objects.new("tgt",None); sc.collection.objects.link(tgt); tgt.location=TGT
c=cam.constraints.new("TRACK_TO"); c.target=tgt; c.track_axis="TRACK_NEGATIVE_Z"; c.up_axis="UP_Y"; cam.data.clip_end=5000
sc.render.engine="CYCLES"; cy=sc.cycles; cy.samples=SAMP; cy.use_denoising=True
try:
    pr=bpy.context.preferences.addons["cycles"].preferences; pr.compute_device_type="OPTIX"; pr.get_devices()
    for d in pr.devices: d.use=(d.type!="CPU")
    cy.device="GPU"
except Exception as e: print("GPU fallback",e)
sc.render.resolution_x=1920; sc.render.resolution_y=1080; sc.render.resolution_percentage=PCT
sc.view_settings.view_transform="Filmic"; sc.view_settings.look="Medium High Contrast"; sc.view_settings.exposure=-1.3
sc.render.filepath=os.path.abspath(OUT); sc.render.image_settings.file_format="PNG"
import mathutils; objs=[o for o in sc.objects if o.type=="MESH" and not o.hide_render and o.name not in ("PI_Terrain",sea.name)]; cen=sum((o.location for o in objs),mathutils.Vector())/max(1,len(objs)); print("PIB centroid",tuple(round(v,1) for v in cen))
print("PIB placed",n,"unique",len([v for v in SRC.values() if v]),"device",cy.device)
bpy.ops.render.render(write_still=True); print("PIB wrote",sc.render.filepath)
