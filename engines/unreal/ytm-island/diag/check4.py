import bpy,json,os
G=r"C:\Users\730ri\projects\bot-team\art\glb"; out=[]
for a in json.load(open(r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\polish_v4_b3.json")):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=os.path.join(G,a["asset"]+".glb"))
    t=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in bpy.data.objects if o.type=="MESH")
    ms={m.name for o in bpy.data.objects if o.type=="MESH" for m in o.data.materials}
    out.append((a["asset"],t,len(ms)))
out.sort(key=lambda x:-x[1]); print("MAXTRIS",out[:3]); print("MAXSLOTS",max(x[2] for x in out))
