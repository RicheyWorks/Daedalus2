# SPDX-License-Identifier: MIT
"""The code each editor runs. Each is sent through its bridge's run-Python command and sets `result`.

Each script is self-contained (it imports only bpy or unreal and the standard library), so it works
the same through the real editor, the stand-in, or a bot that pastes it into the editor's own console.
"""
import json

BLENDER_EXPORT = r'''
import bpy, json, os
P = json.loads(PARAMS)
want = P.get("objects") or [o.name for o in bpy.context.view_layer.objects if o.type == "MESH" and o.visible_get()]
missing = [n for n in want if n not in bpy.data.objects]
if missing:
    raise ValueError("no such Blender objects: %s" % ", ".join(missing))
for o in bpy.context.view_layer.objects:
    o.select_set(o.name in want)
os.makedirs(os.path.dirname(P["path"]), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=P["path"], export_format="GLB", use_selection=True,
                          export_apply=True, export_yup=True)
dg = bpy.context.evaluated_depsgraph_get()
objs = []
for name in want:
    ob = bpy.data.objects[name]
    if ob.type != "MESH":
        continue
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    tris = len(me.loop_triangles)
    if len(me.vertices):
        lo = [min(v.co[i] for v in me.vertices) for i in range(3)]
        hi = [max(v.co[i] for v in me.vertices) for i in range(3)]
        dims = sorted((h - l for l, h in zip(lo, hi)), reverse=True)
    else:
        dims = [0.0, 0.0, 0.0]
    used = sorted({me.materials[t.material_index].name for t in me.loop_triangles
                   if t.material_index < len(me.materials) and me.materials[t.material_index] is not None})
    ev.to_mesh_clear()
    objs.append({"name": name, "triangles": tris, "materials": used, "dims": [round(d, 5) for d in dims]})
result = {"path": P["path"], "bytes": os.path.getsize(P["path"]), "objects": objs,
          "blender": bpy.app.version_string}
'''

UNREAL_IMPORT = r'''
import unreal, json
P = json.loads(PARAMS)
task = unreal.AssetImportTask()
task.set_editor_property("filename", P["path"])
task.set_editor_property("destination_path", P["dest"])
task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", True)
task.set_editor_property("save", bool(P.get("save", True)))
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
paths = [str(p) for p in (task.get_editor_property("imported_object_paths") or [])]
if not paths:
    paths = [str(p) for p in unreal.EditorAssetLibrary.list_assets(P["dest"], recursive=True)]
meshes, materials = [], []
for path in paths:
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        continue
    if isinstance(asset, unreal.StaticMesh):
        box = asset.get_bounding_box()
        size = [box.max.x - box.min.x, box.max.y - box.min.y, box.max.z - box.min.z]
        slots = [str(m.get_editor_property("material_slot_name")) for m in asset.get_editor_property("static_materials")]
        # Count the imported geometry (the source mesh description), not LOD0's render data: with Nanite on (UE 5.8's
        # import default) LOD0 is the Nanite fallback, which simplifies (a 440-triangle pickaxe rendered as 422).
        render = asset.get_num_triangles(0)
        desc = asset.get_static_mesh_description(0)
        source = desc.get_triangle_count() if desc is not None else render
        try:
            nanite = bool(asset.get_editor_property("nanite_settings").get_editor_property("enabled"))
        except Exception:
            nanite = False
        meshes.append({"path": path, "name": asset.get_name(), "triangles": source, "render_triangles": render,
                       "nanite": nanite, "materials": slots, "dims_cm": sorted(size, reverse=True)})
        # UE 5.8.3 reports only the meshes as imported: count the materials the meshes actually use (a folder
        # listing would also count a previous import's leftovers and hide a lost material).
        for m in asset.get_editor_property("static_materials"):
            mi = m.get_editor_property("material_interface")
            if mi is not None and not mi.get_path_name().startswith("/Engine/") \
                    and all(x["path"] != mi.get_path_name() for x in materials):
                materials.append({"path": mi.get_path_name(), "name": mi.get_name()})
    elif isinstance(asset, unreal.MaterialInterface) and all(x["path"] != path for x in materials):
        materials.append({"path": path, "name": asset.get_name()})
result = {"dest": P["dest"], "imported": paths, "meshes": meshes, "materials": materials}
'''


def script(template, **params):
    """The template with its parameters bound (as JSON, so no quoting can break the code)."""
    return "PARAMS = %r\n" % json.dumps(params) + template
