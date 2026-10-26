import bpy,glob,os
for f in sorted(glob.glob(r"C:\Users\730ri\projects\bot-team\art\glb\*YTM_Sign_*.glb")+glob.glob(r"C:\Users\730ri\projects\bot-team\art\glb\*YTM_Record*.glb")+glob.glob(r"C:\Users\730ri\projects\bot-team\art\glb\Prop_YTM_Jukebox.glb")):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=f)
    t=0;m=set()
    for o in bpy.context.scene.objects:
        if o.type=='MESH':
            o.data.calc_loop_triangles(); t+=len(o.data.loop_triangles); m|={s.name for s in o.data.materials if s}
    print("TRIS",os.path.basename(f),t,len(m))
