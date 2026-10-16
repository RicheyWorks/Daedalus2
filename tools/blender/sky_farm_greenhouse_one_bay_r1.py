"""One relative-coordinate farm bay. Pure geometry is usable without Blender.

Call build(scene, recipe) only from the preserved-session runner after its grant.
No reset, file open, deletion, network, process launch or world placement.
"""
import json
import math
from pathlib import Path

PALETTE = {
    "frame": (0.23, 0.40, 0.33, 1), "copper": (0.63, 0.30, 0.12, 1),
    "glass": (0.52, 0.82, 0.72, 0.16), "soil": (0.12, 0.065, 0.028, 1),
    "leaf": (0.18, 0.48, 0.095, 1), "leaf_light": (0.48, 0.68, 0.16, 1),
    "path": (0.52, 0.55, 0.50, 1),
}
FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
         (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def load_recipe(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != "daedalus.sky-farm-greenhouse.recipe.v1":
        raise ValueError("unknown recipe schema")
    for name in ("width", "length", "eave_height", "ridge_height", "aisle_width", "bed_width",
                 "bed_length", "bed_height", "path_apron"):
        v = value.get(name)
        if type(v) not in (int, float) or not math.isfinite(v) or not 0 < v <= 32:
            raise ValueError("invalid dimension: " + name)
    if (value["units"] != "metres" or value["world_binding"] is not None
            or value["eave_height"] < 2.4 or value["ridge_height"] <= value["eave_height"]
            or value["aisle_width"] < 1.4 or value["bed_length"] > value["length"] - 1
            or value["aisle_width"] + 2 * value["bed_width"] + 1 > value["width"]
            or type(value["plants_per_bed"]) is not int or value["plants_per_bed"] != 12):
        raise ValueError("recipe violates bounded bay/aisle contract")
    return value


def geometry(r):
    parts = []

    def box(name, role, mat, center, size, tilt=0):
        x, y, z = center
        a, b, c = (n / 2 for n in size)
        co = [(-a, -b, -c), (a, -b, -c), (a, b, -c), (-a, b, -c),
              (-a, -b, c), (a, -b, c), (a, b, c), (-a, b, c)]
        cs, sn = math.cos(tilt), math.sin(tilt)
        vertices = [(x + u * cs + w * sn, y + v, z - u * sn + w * cs) for u, v, w in co]
        parts.append({"name": name, "role": role, "material": mat,
                      "vertices": vertices, "faces": FACES})

    w, length, eave, ridge = (r[k] for k in ("width", "length", "eave_height", "ridge_height"))
    for side in (-1, 1):
        for i, y in enumerate((-length / 2, 0, length / 2)):
            box(f"Post_{side}_{i}", "frame", "frame", (side * (w / 2 - .06), y, eave / 2), (.12, .12, eave))
        box(f"SideRail_{side}", "frame", "frame", (side * (w / 2 - .06), 0, eave), (.14, length, .14))
        box(f"SideGlass_{side}", "glass", "glass", (side * (w / 2 - .05), 0, 1.65), (.025, length - .24, 1.9))
        rise, run = ridge - eave, w / 2
        angle = math.atan2(rise, run) * side
        roof_width = math.hypot(run, rise)
        box(f"RoofGlass_{side}", "glass", "glass", (side * w / 4, 0, (ridge + eave) / 2),
            (roof_width, length, .025), angle)
        for i, y in enumerate((-length / 2, 0, length / 2)):
            box(f"Rafter_{side}_{i}", "frame", "frame", (side * w / 4, y, (ridge + eave) / 2 + .04),
                (roof_width + .16, .10, .10), angle)
    box("Ridge", "frame", "copper", (0, 0, ridge + .06), (.12, length + .15, .12))
    for side in (-1, 1):
        x = side * (r["aisle_width"] / 2 + .22 + r["bed_width"] / 2)
        h, bw, bl = r["bed_height"], r["bed_width"], r["bed_length"]
        box(f"Soil_{side}", "bed", "soil", (x, 0, h - .10), (bw - .12, bl - .12, .18))
        for edge in (-1, 1):
            box(f"BedSide_{side}_{edge}", "bed", "copper", (x + edge * (bw / 2 - .04), 0, h / 2), (.08, bl, h))
            box(f"BedEnd_{side}_{edge}", "bed", "copper", (x, edge * (bl / 2 - .04), h / 2), (bw - .16, .08, h))
        for i in range(12):
            px = x + (-.36 if i % 2 == 0 else .36)
            py = (i // 2 - 2.5) * .88
            box(f"Stem_{side}_{i}", "crop", "leaf", (px, py, h + .14), (.06, .06, .30))
            for leaf in (-1, 1):
                box(f"Leaf_{side}_{i}_{leaf}", "crop", "leaf_light" if i % 3 == 0 else "leaf",
                    (px + leaf * .13, py, h + .27), (.35, .24, .05), leaf * -.40)
    for i in range(20):
        span = length + 2 * r["path_apron"]
        y = -span / 2 + (i + .5) * span / 20
        box(f"Path_{i:02}", "path", "path", (0, y, .025), (r["aisle_width"], span / 20, .05))
    return parts


def bounds(part):
    return [[min(v[k] for v in part["vertices"]) for k in range(3)],
            [max(v[k] for v in part["vertices"]) for k in range(3)]]


def group_geometry(parts):
    groups = {}
    for part in parts:
        key = (part["role"], part["material"])
        group = groups.setdefault(key, {"vertices": [], "faces": [], "source_parts": []})
        offset = len(group["vertices"])
        group["vertices"].extend(part["vertices"])
        group["faces"].extend(tuple(offset+i for i in face) for face in part["faces"])
        group["source_parts"].append(part["name"])
    return groups


def validate_geometry(r, parts):
    names = [p["name"] for p in parts]
    if len(set(names)) != len(names) or not parts:
        raise ValueError("duplicate or empty geometry")
    triangles = 0
    for p in parts:
        if p["material"] not in PALETTE or any(not math.isfinite(v) for co in p["vertices"] for v in co):
            raise ValueError("invalid material/vertex")
        for face in p["faces"]:
            if len(face) != 4 or any(type(i) is not int or not 0 <= i < len(p["vertices"]) for i in face):
                raise ValueError("invalid face")
            a, b, c = (p["vertices"][i] for i in face[:3])
            ab, ac = [b[k] - a[k] for k in range(3)], [c[k] - a[k] for k in range(3)]
            normal = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]]
            if sum(v*v for v in normal) < 1e-12:
                raise ValueError("degenerate face")
            triangles += 2
        lo, hi = bounds(p)
        # Conservative AABB obstruction test: human corridor above path to 2.1m.
        if p["role"] != "path" and (lo[0] < r["aisle_width"]/2 and hi[0] > -r["aisle_width"]/2
                and lo[1] < r["length"]/2 and hi[1] > -r["length"]/2 and lo[2] < 2.1 and hi[2] > .05):
            raise ValueError("geometry obstructs central walking corridor: " + p["name"])
    path = [bounds(p) for p in parts if p["role"] == "path"]
    span = r["length"] + 2*r["path_apron"]
    for i in range(81):
        y = -span/2 + i*span/80
        if not any(lo[0] <= 0 <= hi[0] and lo[1]-1e-9 <= y <= hi[1]+1e-9 and abs(hi[2]-.05) < 1e-9
                   for lo, hi in path):
            raise ValueError("path support gap")
    if triangles > 15000:
        raise ValueError("building triangle budget exceeded")
    return {"primitive_count": len(parts), "mesh_count": len(group_geometry(parts)),
            "triangles": triangles, "path_samples": 81,
            "clear_aisle_width_m": r["aisle_width"], "clear_corridor_height_m": 2.1,
            "bounds_m": [[min(v[k] for p in parts for v in p["vertices"]) for k in range(3)],
                         [max(v[k] for p in parts for v in p["vertices"]) for k in range(3)]],
            "native_collision_verified": False, "world_binding": None}


def build(scene, r):
    import bpy
    from mathutils import Vector
    parts = geometry(r)
    stats = validate_geometry(r, parts)
    collection = bpy.data.collections.new(r["asset_id"])
    scene.collection.children.link(collection)
    mats, objects = {}, []
    for name, color in PALETTE.items():
        mat = bpy.data.materials.new("SFG_R1_" + name)
        mat.diffuse_color = color
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = .25 if name == "glass" else .7
        bsdf.inputs["Alpha"].default_value = color[3]
        if name == "glass":
            bsdf.inputs["Transmission Weight"].default_value = .25
        mats[name] = mat
    for (role, material), group in group_geometry(parts).items():
        name = "SFG_R1_" + role + "_" + material
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(group["vertices"], [], group["faces"])
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.data.materials.append(mats[material])
        obj["role"] = role
        obj["source_parts"] = json.dumps(group["source_parts"])
        obj["units"] = "metres"
        objects.append(obj)
    for name, y in (("Entry", -r["length"]/2), ("Repeat", r["length"]/2)):
        obj = bpy.data.objects.new("SFG_R1_SOCKET_" + name, None)
        obj.location = (0, y, 0)
        obj["socket_role"] = name
        collection.objects.link(obj)
        objects.append(obj)
    showcase = bpy.data.collections.new("SFG_R1_SHOWCASE_ONLY")
    scene.collection.children.link(showcase)
    # Neutral gray support is a render proxy, explicitly excluded from export.
    mesh = bpy.data.meshes.new("SFG_R1_PROXY")
    mesh.from_pydata([(-3.5,-5.5,-.25),(3.5,-5.5,-.25),(3.5,5.5,-.25),(-3.5,5.5,-.25),
                      (-3.5,-5.5,0),(3.5,-5.5,0),(3.5,5.5,0),(-3.5,5.5,0)],[],FACES)
    proxy = bpy.data.objects.new("SFG_R1_PlatformProxy_NOT_NATIVE", mesh)
    showcase.objects.link(proxy)
    proxy.data.materials.append(mats["path"])
    camera = bpy.data.objects.new("SFG_R1_Hero", bpy.data.cameras.new("SFG_R1_Hero"))
    showcase.objects.link(camera)
    camera.location = (10, -14, 11)
    camera.rotation_euler = (Vector((0, 0, 1.1))-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.ortho_scale = "ORTHO", 15
    scene.camera = camera
    for name, pos, power, size in (("Key", (2,-5,11), 1700, 7), ("Fill", (-6,-1,6), 900, 6)):
        light = bpy.data.lights.new("SFG_R1_"+name,"AREA")
        light.energy, light.shape, light.size = power,"DISK",size
        obj = bpy.data.objects.new(light.name,light)
        showcase.objects.link(obj)
        obj.location=pos
        obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat("-Z","Y").to_euler()
    world=bpy.data.worlds.new("SFG_R1_World")
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs[0].default_value=(.16,.22,.28,1)
    world.node_tree.nodes["Background"].inputs[1].default_value=.5
    scene.world=world
    scene.unit_settings.system,scene.unit_settings.scale_length="METRIC",1.0
    scene.render.engine="CYCLES"
    scene.cycles.device,scene.cycles.samples="CPU",r["render"]["samples"]
    scene.render.threads_mode,scene.render.threads="FIXED",r["render"]["threads"]
    scene.render.resolution_x,scene.render.resolution_y=r["render"]["width"],r["render"]["height"]
    scene.render.resolution_percentage=100
    return objects, stats
