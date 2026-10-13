# Prometheus hero v2: builds the v1 scene (pi_blender_hero.py, no render), then smooth bilinear terrain,
# real materials, stylized jukebox + coated livestock, golden hour, three-quarter close camera.
# usage: blender -b -P pi_blender_hero_v2.py -- OUT.png [samples] [res_pct]
import os, sys, math, bpy, bmesh, mathutils, colorsys
os.environ["PIB_NORENDER"]="1"; HERE=os.path.dirname(os.path.abspath(__file__))
_a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
sys.argv=sys.argv[:sys.argv.index("--")+1]+[os.path.join(HERE,"_v1_unused.png")] if "--" in sys.argv else sys.argv
g={"__file__":os.path.join(HERE,"pi_blender_hero.py"),"__name__":"__main__"}
exec(compile(open(g["__file__"],encoding="utf-8").read(),g["__file__"],"exec"),g)
OUT=_a[0] if _a else "PI_hero_v2.png"; SAMP=int(_a[1]) if len(_a)>1 else 256; PCT=int(_a[2]) if len(_a)>2 else 100
sc=bpy.context.scene; N,S,P,HM=g["N"],g["S"],g["P"],g["HM"]
def nodes(m): return m.node_tree.nodes, m.node_tree.links
# ---- 1) terrain: 3x bilinear grid + subdivision, soft shoreline (no cliff skirts)
def hraw(lx,ly):
    j=min(N-1.001,max(0,(lx/S+0.5)*(N-1))); i=min(N-1.001,max(0,(ly/S+0.5)*(N-1))); i0,j0=int(i),int(j); fi,fj=i-i0,j-j0
    return HM[i0][j0]*(1-fi)*(1-fj)+HM[i0][j0+1]*(1-fi)*fj+HM[i0+1][j0]*fi*(1-fj)+HM[i0+1][j0+1]*fi*fj
old=bpy.data.objects["PI_Terrain"]; bpy.data.objects.remove(old)
M=3*(N-1)+1; me=bpy.data.meshes.new("TerrainV2"); bm=bmesh.new(); V={}
for i in range(M):
    for j in range(M):
        lx=(j/(M-1)-0.5)*S; ly=(i/(M-1)-0.5)*S; h=hraw(lx,ly)
        z=h*P if h>0.06 else 0.06*P*(h/0.06)**2-250*(1-h/0.06)
        V[i,j]=bm.verts.new((lx/100,-ly/100,z/100))
for i in range(M-1):
    for j in range(M-1): bm.faces.new((V[i,j],V[i,j+1],V[i+1,j+1],V[i+1,j]))
bm.normal_update(); bm.to_mesh(me); bm.free()
T=bpy.data.objects.new("PI_Terrain",me); sc.collection.objects.link(T)
for p in me.polygons: p.use_smooth=True
sm=T.modifiers.new("smooth","SMOOTH"); sm.factor=0.5; sm.iterations=4
ss=T.modifiers.new("subd","SUBSURF"); ss.levels=1; ss.render_levels=1
# grass gradient: shore sand -> deep green -> dry gold on ridges, noise-broken
gm=bpy.data.materials.new("M_GrassV2"); gm.use_nodes=True; nd,lk=nodes(gm); b=nd["Principled BSDF"]; b.inputs["Roughness"].default_value=0.92
geo=nd.new("ShaderNodeNewGeometry"); sep=nd.new("ShaderNodeSeparateXYZ"); lk.new(geo.outputs["Position"],sep.inputs[0])
noi=nd.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value=0.08; noi.inputs["Detail"].default_value=6
mth=nd.new("ShaderNodeMath"); mth.operation="MULTIPLY_ADD"; mth.inputs[1].default_value=1/38.0; lk.new(sep.outputs[2],mth.inputs[0])
nm=nd.new("ShaderNodeMath"); nm.operation="MULTIPLY"; nm.inputs[1].default_value=0.25; lk.new(noi.outputs["Fac"],nm.inputs[0]); lk.new(nm.outputs[0],mth.inputs[2])
cr=nd.new("ShaderNodeValToRGB"); e=cr.color_ramp.elements
e[0].position=0.12; e[0].color=(0.32,0.26,0.14,1); e[1].position=0.95; e[1].color=(0.16,0.15,0.06,1)
for pos,col in ((0.2,(0.05,0.10,0.025,1)),(0.5,(0.07,0.14,0.03,1)),(0.75,(0.09,0.13,0.035,1))): x=e.new(pos); x.color=col
lk.new(mth.outputs[0],cr.inputs[0]); lk.new(cr.outputs[0],b.inputs["Base Color"])
bp=nd.new("ShaderNodeBump"); bp.inputs["Strength"].default_value=0.25; n2=nd.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value=3.0; lk.new(n2.outputs["Fac"],bp.inputs["Height"]); lk.new(bp.outputs[0],b.inputs["Normal"])
T.data.materials.append(gm)
# ---- 2) water + stone shaders (edit shared v1 materials in place)
def water(m):
    nd,lk=nodes(m); b=nd["Principled BSDF"]; b.inputs["Base Color"].default_value=(0.02,0.09,0.10,1); b.inputs["Roughness"].default_value=0.03
    b.inputs["Transmission Weight"].default_value=0.85; b.inputs["IOR"].default_value=1.333
    w=nd.new("ShaderNodeTexWave"); w.inputs["Scale"].default_value=0.6; w.inputs["Distortion"].default_value=4; bp=nd.new("ShaderNodeBump"); bp.inputs["Strength"].default_value=0.08
    lk.new(w.outputs["Fac"],bp.inputs["Height"]); lk.new(bp.outputs[0],b.inputs["Normal"])
def stone(m,base):
    nd,lk=nodes(m); b=nd["Principled BSDF"]; vo=nd.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value=6; cr=nd.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color=(base[0]*0.6,base[1]*0.6,base[2]*0.6,1); cr.color_ramp.elements[1].color=(*base,1)
    lk.new(vo.outputs["Distance"],cr.inputs[0]); lk.new(cr.outputs[0],b.inputs["Base Color"]); b.inputs["Roughness"].default_value=0.85
    bp=nd.new("ShaderNodeBump"); bp.inputs["Strength"].default_value=0.4; lk.new(vo.outputs["Distance"],bp.inputs["Height"]); lk.new(bp.outputs[0],b.inputs["Normal"])
water(g["WATER"]); stone(g["MAT"]["rock"],(0.22,0.20,0.18)); stone(g["MAT"]["tone"],(0.30,0.27,0.22))
nd,_=nodes(g["MAT"]["stock"]); nd["Principled BSDF"].inputs["Base Color"].default_value=(0.30,0.18,0.08,1)
# ---- 3) stylized jukebox (replaces v1 cube)
jb=[o for o in sc.objects if o.type=="MESH" and o.data.materials and o.data.materials[0].name=="M_Juke"]
hl=g["L"](g["hx"],g["hy"],0)
for o in jb: bpy.data.objects.remove(o)
def m(n,rgb,rough=0.4,metal=0.0,emit=0.0): return g["mat"](n,rgb,rough,metal,emit)
WOOD=m("M_JukeWood",(0.16,0.06,0.025),0.35); CHROME=m("M_Chrome",(0.8,0.75,0.65),0.15,1.0); GLOW=m("M_JukeGlow",(1.0,0.42,0.10),0.3,0,12.0); GLOW2=m("M_JukeGlow2",(1.0,0.75,0.35),0.3,0,6.0)
def add(kind,loc,scale,mt,rot=(0,0,0),**kw):
    getattr(bpy.ops.mesh,"primitive_%s_add"%kind)(location=loc,rotation=rot,**kw); o=bpy.context.object; o.scale=scale; o.data.materials.append(mt); return o
if hl:
    x,y,z=hl; s=1.6
    add("cube",(x,y,z+1.0*s),(0.75*s,0.45*s,1.0*s),WOOD)
    add("cylinder",(x,y,z+2.0*s),(0.75*s,0.75*s,0.45*s),WOOD,(math.pi/2,0,0),vertices=48)
    add("cylinder",(x,y-0.47*s,z+2.0*s),(0.6*s,0.6*s,0.02*s),GLOW2,(math.pi/2,0,0),vertices=48)
    for k in range(5): add("cube",(x-0.5*s+k*0.25*s,y-0.46*s,z+1.0*s),(0.04*s,0.02*s,0.7*s),GLOW)
    add("cube",(x,y-0.47*s,z+0.25*s),(0.7*s,0.03*s,0.06*s),CHROME); add("cube",(x,y-0.47*s,z+1.75*s),(0.7*s,0.03*s,0.04*s),CHROME)
    bpy.ops.object.light_add(type="POINT",location=(x,y-3,z+2.5)); l=bpy.context.object.data; l.energy=4000; l.color=(1,0.55,0.25); l.shadow_soft_size=1.5
# ---- 4) livestock: body + head + legs + ears, coat-textured
coats=g["CM"]; sheep=[o for o in sc.objects if o.type=="MESH" and o.data.materials and o.data.materials[0].name.startswith("M_Coat")]
DARK=m("M_Hoof",(0.03,0.025,0.02),0.6)
for o in sheep:
    c=o.data.materials[0]; p=o.location.copy(); yaw=o.rotation_euler[2]; bpy.data.objects.remove(o)
    R=mathutils.Matrix.Rotation(yaw,4,"Z"); base=p-mathutils.Vector((0,0,0.7)); parts=[]
    def at(v): return base+R@mathutils.Vector(v)
    parts.append(add("uv_sphere",at((0,0,0.85)),(0.75,0.42,0.42),c,(0,0,yaw),segments=24,ring_count=12))
    parts.append(add("uv_sphere",at((0.78,0,1.1)),(0.26,0.2,0.22),c,(0,0,yaw),segments=16,ring_count=8))
    for ex in (-0.12,0.12): parts.append(add("uv_sphere",at((0.72,ex*1.4,1.32)),(0.05,0.12,0.03),c,(0,0,yaw),segments=8,ring_count=4))
    for lx,ly in ((0.45,0.2),(0.45,-0.2),(-0.45,0.2),(-0.45,-0.2)): parts.append(add("cylinder",at((lx,ly,0.25)),(0.07,0.07,0.25),DARK,(0,0,yaw),vertices=8))
    for q in parts: bpy.ops.object.shade_smooth()
for o in [o for o in sc.objects if o.type=="LIGHT" and o.data.energy>=50000]: o.data.energy=8000
# ---- 5) golden hour, dark + warm
for o in [o for o in sc.objects if o.type=="LIGHT" and o.data.type=="SUN"]: bpy.data.objects.remove(o)
w=sc.world; sky=[n for n in w.node_tree.nodes if n.type=="TEX_SKY"][0]; sky.sun_elevation=math.radians(4.5); sky.sun_rotation=math.radians(240); sky.air_density=2.5; sky.dust_density=3.0; sky.sun_disc=False; sky.sun_intensity=0.25
w.node_tree.nodes["Background"].inputs[1].default_value=0.25
bpy.ops.object.light_add(type="SUN",rotation=(math.radians(84),0,math.radians(240-90))); s=bpy.context.object.data; s.energy=1.6; s.color=(1.0,0.58,0.28); s.angle=math.radians(6)
for o in [o for o in sc.objects if o.type=="MESH" and o.data.materials and o.data.materials[0].name=="M_Lamp"]:
    bpy.ops.object.light_add(type="POINT",location=o.location+mathutils.Vector((0,0,1.6))); l=bpy.context.object.data; l.energy=900; l.color=(1,0.55,0.22); l.shadow_soft_size=0.6
# ---- 6) three-quarter close camera on heart + herb ring + stream
L=g["L"]; pts=[L(g["hx"],g["hy"]),L(g["gx"],g["gy"])]+[L(*g["path"](t)) for t in (0.25,0.35,0.45)]
pts=[mathutils.Vector(p) for p in pts if p]; hv=pts[0]; gv=pts[1]; tgt=hv.lerp(gv,0.35)+mathutils.Vector((0,0,2))
off=mathutils.Vector([float(v) for v in os.environ.get("PIB2_OFF","-16,-24,9").split(",")])
cam=sc.camera; cam.constraints.clear(); cam.location=hv+off; cam.data.lens=float(os.environ.get("PIB2_LENS","30"))
d=(tgt+mathutils.Vector((0,0,-4)))-cam.location; cam.rotation_euler=d.to_track_quat("-Z","Y").to_euler()
cam.data.dof.use_dof=True; cam.data.dof.focus_distance=d.length; cam.data.dof.aperture_fstop=8
sc.view_settings.view_transform="Filmic"; sc.view_settings.look="Medium High Contrast"; sc.view_settings.exposure=float(os.environ.get("PIB2_EXP","-0.6"))
sc.cycles.samples=SAMP; sc.render.resolution_percentage=PCT; sc.render.filepath=os.path.abspath(OUT)
print("PIB2 tgt",tuple(round(v,1) for v in tgt),"cam",tuple(round(v,1) for v in cam.location))
bpy.ops.render.render(write_still=True); print("PIB2 wrote",sc.render.filepath)
