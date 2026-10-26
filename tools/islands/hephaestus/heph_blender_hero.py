# SPDX-License-Identifier: MIT
"""Off-editor Blender forge-overlook hero for Hephaestus Island.
Places layout.json as zone-colored proxies, imports the 7 hero GLBs from
bot-team/shots/hephaestus/hero_1625, camera at layout hero_cam_m.

  "C:\\Program Files\\Blender Foundation\\Blender 4.3\\blender.exe" -b -P tools/islands/hephaestus/heph_blender_hero.py

Writes bot-team/shots/hephaestus/hero_blender.png and prints mean RGB JSON.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Euler

ROOT = Path(r"C:\Users\730ri\projects\Daedalus2")
LAYOUT = ROOT / "data" / "islands" / "hephaestus" / "layout.json"
HERO_GLB = Path(r"C:\Users\730ri\projects\bot-team\shots\hephaestus\hero_1625")
OUT = Path(r"C:\Users\730ri\projects\bot-team\shots\hephaestus\hero_blender.png")

ZONE_RGBA = {
    "caldera_forge": (0.12, 0.08, 0.07, 1),
    "meteor_scar": (0.18, 0.10, 0.06, 1),
    "ark_drydock": (0.28, 0.30, 0.32, 1),
    "ash_fields": (0.32, 0.28, 0.18, 1),
    "livestock_pens": (0.38, 0.30, 0.18, 1),
    "hot_springs": (0.18, 0.42, 0.40, 1),
    "basalt_coast": (0.08, 0.08, 0.09, 1),
    "water_chain": (0.15, 0.35, 0.55, 1),
}
HERO_ASSETS = {
    "Prop_HephaestusForge_Great",
    "Prop_HephaestusAnvil_Great",
    "Tool_HephaestusHammer",
    "Item_Shard_Asteroid",
    "Item_Shard_Planet",
    "Prop_ArkRivetCrate",
    "Prop_LavaLantern",
}
EMISSIVE_ZONES = {"caldera_forge", "meteor_scar", "hot_springs"}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes) + list(bpy.data.materials) + list(bpy.data.lights) + list(bpy.data.cameras):
        try:
            if block.users == 0:
                if isinstance(block, bpy.types.Mesh):
                    bpy.data.meshes.remove(block)
                elif isinstance(block, bpy.types.Material):
                    bpy.data.materials.remove(block)
                elif isinstance(block, bpy.types.Light):
                    bpy.data.lights.remove(block)
                elif isinstance(block, bpy.types.Camera):
                    bpy.data.cameras.remove(block)
        except Exception:
            pass


def mat_for(zone: str, name: str):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    rgba = ZONE_RGBA.get(zone, (0.4, 0.4, 0.4, 1))
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.75
    if zone in ("caldera_forge", "meteor_scar"):
        bsdf.inputs["Metallic"].default_value = 0.35
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (1.0, 0.35, 0.05, 1)
            bsdf.inputs["Emission Strength"].default_value = 4.0 if zone == "caldera_forge" else 2.0
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = (1.0, 0.35, 0.05, 1)
    if zone == "hot_springs":
        bsdf.inputs["Roughness"].default_value = 0.15
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 0.4
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (0.4, 0.85, 0.9, 1)
    if zone == "water_chain":
        bsdf.inputs["Roughness"].default_value = 0.05
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = 0.6
    return m


def add_ground(radius=220.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=2.0, location=(0, 0, -1.0))
    ground = bpy.context.active_object
    ground.name = "HephGround"
    m = bpy.data.materials.new("M_HephAsh")
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.22, 0.18, 0.14, 1)
    bsdf.inputs["Roughness"].default_value = 0.95
    ground.data.materials.append(m)
    # caldera ring
    bpy.ops.mesh.primitive_torus_add(major_radius=28, minor_radius=3.5, major_segments=48, location=(0, 0, 1.5))
    ring = bpy.context.active_object
    ring.name = "CalderaRim"
    rm = mat_for("caldera_forge", "M_CalderaRim")
    ring.data.materials.append(rm)
    # magma pool
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=18, depth=0.6, location=(0, 0, 0.2))
    pool = bpy.context.active_object
    pool.name = "MagmaPool"
    pm = mat_for("caldera_forge", "M_MagmaPool")
    pool.data.materials.append(pm)


def import_glb(path: Path, loc, yaw_deg: float, scale: float):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    if not new:
        return None
    # parent under empty at placement
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=loc)
    root = bpy.context.active_object
    root.name = path.stem
    for o in new:
        o.parent = root
    root.rotation_euler = Euler((0, 0, math.radians(yaw_deg)), "XYZ")
    root.scale = (scale, scale, scale)
    return root


def proxy_box(asset: str, zone: str, loc, yaw_deg: float, scale: float):
    # size by asset class
    if asset.startswith("Mob_"):
        dims = (1.2, 0.8, 1.0)
    elif asset.startswith("Item_Herb_"):
        dims = (0.5, 0.5, 0.8)
    elif asset.startswith("WaterPlane") or "Spring" in asset or "HotSpring" in asset:
        dims = (4.0, 4.0, 0.3)
    elif asset.startswith("Prop_Ranch") or "Trough" in asset or "Fence" in asset:
        dims = (1.5, 0.4, 1.2)
    elif "Quench" in asset or "Anvil" in asset or "Forge" in asset:
        dims = (2.5, 2.5, 3.0)
    elif "Ark" in asset or "Hull" in asset:
        dims = (8.0, 3.0, 2.5)
    else:
        dims = (1.4, 1.4, 1.6)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = asset[:60]
    obj.scale = (dims[0] * scale, dims[1] * scale, dims[2] * scale)
    obj.rotation_euler = Euler((0, 0, math.radians(yaw_deg)), "XYZ")
    # lift so base sits on z
    obj.location.z = loc[2] + dims[2] * scale * 0.5
    m = mat_for(zone, f"M_{zone}_{asset[:40]}")
    if obj.data.materials:
        obj.data.materials[0] = m
    else:
        obj.data.materials.append(m)
    return obj


def setup_camera(cam_m, target_m, fov_deg):
    bpy.ops.object.camera_add(location=Vector(cam_m))
    cam = bpy.context.active_object
    cam.name = "HephHeroCam"
    direction = Vector(target_m) - Vector(cam_m)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens_unit = "FOV"
    cam.data.angle = math.radians(fov_deg)
    bpy.context.scene.camera = cam
    return cam


def setup_lights():
    # warm key (forge)
    bpy.ops.object.light_add(type="AREA", location=(20, -30, 40))
    key = bpy.context.active_object
    key.name = "ForgeKey"
    key.data.energy = 1200
    key.data.size = 25
    key.data.color = (1.0, 0.72, 0.45)
    # cool rim
    bpy.ops.object.light_add(type="AREA", location=(-40, 50, 30))
    fill = bpy.context.active_object
    fill.name = "AshFill"
    fill.data.energy = 400
    fill.data.size = 40
    fill.data.color = (0.55, 0.65, 0.85)
    # magma point
    bpy.ops.object.light_add(type="POINT", location=(0, 0, 6))
    magma = bpy.context.active_object
    magma.name = "MagmaPoint"
    magma.data.energy = 800
    magma.data.color = (1.0, 0.4, 0.08)
    # world
    world = bpy.data.worlds.new("HephWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.35, 0.28, 0.22, 1)
    bg.inputs[1].default_value = 0.6


def render(out: Path):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
    except Exception:
        try:
            prefs.compute_device_type = "CUDA"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
        except Exception:
            sc.cycles.device = "CPU"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.filepath = str(out)
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)


def mean_rgb(path: Path):
    try:
        from PIL import Image
    except ImportError:
        return None
    im = Image.open(path).convert("RGB")
    px = im.load()
    w, h = im.size
    step = max(1, (w * h) // 200_000)
    n = r = g = b = 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            pr, pg, pb = px[x, y]
            r += pr; g += pg; b += pb; n += 1
    return {"w": w, "h": h, "mean": {"R": round(r / n, 2), "G": round(g / n, 2), "B": round(b / n, 2)}, "n": n}


def main():
    lay = json.loads(LAYOUT.read_text(encoding="utf-8"))
    clear_scene()
    add_ground()
    setup_lights()
    placed = 0
    glb_hit = 0
    for p in lay["placements"]:
        asset = p["asset"]
        zone = p.get("zone") or "ash_fields"
        loc = (float(p["x"]), float(p["y"]), float(p.get("z") or 0))
        yaw = float(p.get("yaw") or 0)
        scale = float(p.get("scale") or 1.0)
        glb = HERO_GLB / f"{asset}.glb"
        if asset in HERO_ASSETS and glb.is_file():
            import_glb(glb, loc, yaw, scale)
            glb_hit += 1
        else:
            proxy_box(asset, zone, loc, yaw, scale)
        placed += 1
    cam_m = lay["hero_cam_m"]
    tgt_m = lay["hero_target_m"]
    fov = float(lay.get("hero_fov") or 55)
    setup_camera(cam_m, tgt_m, fov)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    render(OUT)
    stats = mean_rgb(OUT) or {}
    summary = {
        "ok": OUT.is_file() and OUT.stat().st_size > 10_000,
        "path": str(OUT),
        "bytes": OUT.stat().st_size if OUT.is_file() else 0,
        "placed": placed,
        "glb_hero": glb_hit,
        "rgb": stats,
    }
    print("HEPH_BLENDER_HERO", json.dumps(summary))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
