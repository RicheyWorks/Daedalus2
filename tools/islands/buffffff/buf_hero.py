# Re-render Buffffff Island hero shots from the saved .blend (headless).
import bpy, os
ROOT=r"C:\Users\730ri\projects\bot-team\art\buffffff"; sc=bpy.context.scene
sc.view_settings.view_transform='Standard'; sc.world.node_tree.nodes["Background"].inputs[1].default_value=0.5
cam=sc.camera
for name,loc,lens in (("hero",(95,-95,55),24),("closeup_water_herbs",(45,-40,22),30),("farm",(-20,-70,25),30)):
    cam.location=loc; cam.data.lens=lens
    sc.render.filepath=os.path.join(ROOT,"hero",f"Buffffff_Island_{name}.png"); bpy.ops.render.render(write_still=True)
print("HERO DONE")
