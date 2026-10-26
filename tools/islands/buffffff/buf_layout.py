# Buffffff Island layout + hero shot (Blender, headless). Double size: 240 m diameter. Places every manifest asset.
import bpy, os, json, math, random
ROOT=r"C:\Users\730ri\projects\bot-team\art\buffffff"; G=os.path.join(ROOT,"glb")
man=json.load(open(os.path.join(ROOT,"manifest.json"))); rnd=random.Random(6)
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
def mat(n,c):
    m=bpy.data.materials.new(n); m.use_nodes=True; m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=c; return m
R=120.0
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=R,depth=8,location=(0,0,-4)); g=bpy.context.active_object; g.data.materials.append(mat("Grass",(0.25,0.55,0.2,1)))
bpy.ops.mesh.primitive_cone_add(vertices=96,radius1=R,radius2=0,depth=70,location=(0,0,-43),rotation=(math.pi,0,0)); bpy.context.active_object.data.materials.append(mat("Under",(0.35,0.25,0.18,1)))
bpy.ops.mesh.primitive_plane_add(size=2000,location=(0,0,-20)); bpy.context.active_object.data.materials.append(mat("Sea",(0.1,0.35,0.6,1)))
# zones (angle deg, dist m): water centre, herbs east, farm west, kitchen north, nft south
ZONE={"water":(0,0,25),"herb":(0,60,30),"tonic":(10,45,8),"station":(20,50,10),"livestock":(180,60,28),"food":(150,55,22),"farm":(200,75,25),"nft":(270,40,10),"apiary":(120,40,10),"decor":(90,30,40),"vehicle":(315,105,8),"kit":(None,0,0)}
COPIES={"kit":4,"herb":3,"livestock":2,"food":2,"decor":2,"apiary":2}
SCALE={"kit":1.8,"herb":2.0,"livestock":1.6,"farm":1.4,"water":1.6,"nft":2.0,"station":1.5,"apiary":1.6,"decor":1.4}
placed=0; out=[]; CACHE={}
for a in [m for m in man for _ in range(COPIES.get(m["group"],1))]:
    zn=a["group"]; ang,d,spr=ZONE.get(zn,(None,0,0))
    if ang is None:
        t=rnd.uniform(0,2*math.pi); r=rnd.uniform(85,115); x,y=r*math.cos(t),r*math.sin(t)
    else:
        t=math.radians(ang); x=d*math.cos(t)+rnd.uniform(-spr,spr); y=d*math.sin(t)+rnd.uniform(-spr,spr)
    yaw=rnd.uniform(0,6.28); sc_=SCALE.get(zn,1.0)*rnd.uniform(0.85,1.15)
    if a["asset"] not in CACHE:
        before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(G,a["asset"]+".glb"))
        CACHE[a["asset"]]=[o for o in set(bpy.data.objects)-before if o.parent is None]; objs=CACHE[a["asset"]]
    else:
        objs=[]
        for src in CACHE[a["asset"]]:
            o=src.copy(); bpy.context.scene.collection.objects.link(o); o.location=(0,0,0); objs.append(o)
    for o in objs: o.location.x+=x; o.location.y+=y; o.rotation_euler.z=yaw; o.scale=(sc_,sc_,sc_)
    placed+=1; out.append({"asset":a["asset"],"x":round(x,1),"y":round(y,1),"yaw":round(math.degrees(yaw),1),"s":round(sc_,2)})
json.dump(out,open(os.path.join(ROOT,"layout.json"),"w"))
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.55,0.75,1,1); w.node_tree.nodes["Background"].inputs[1].default_value=1.0
bpy.ops.object.light_add(type='SUN',rotation=(0.8,0.2,0.6)); bpy.context.active_object.data.energy=4
bpy.ops.object.camera_add(location=(150,-150,110)); cam=bpy.context.active_object; sc.camera=cam
c=cam.constraints.new('TRACK_TO'); bpy.ops.object.empty_add(location=(0,0,0)); c.target=bpy.context.active_object; c.track_axis='TRACK_NEGATIVE_Z'; c.up_axis='UP_Y'
cam.data.lens=28
sc.render.engine='BLENDER_EEVEE_NEXT'; sc.render.resolution_x=1920; sc.render.resolution_y=1080
sc.render.filepath=os.path.join(ROOT,"hero","Buffffff_Island_hero.png"); os.makedirs(os.path.join(ROOT,"hero"),exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,"Buffffff_Island.blend"))
bpy.ops.render.render(write_still=True); print("PLACED",placed)
