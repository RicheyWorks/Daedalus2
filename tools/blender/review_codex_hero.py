# SPDX-License-Identifier: MIT
"""Render a retained Codex export from overview, route and crown cameras.

Blender --background --factory-startup --python THIS -- --receipt RECEIPT --out OUT
Source appearance evidence only; this does not validate Unreal movement/collision.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector


def review(receipt_path, out):
    if not bpy.app.background or bpy.data.filepath:
        raise RuntimeError("review requires an isolated background factory scene")
    if any(obj.name not in {"Cube", "Camera", "Light"} for obj in bpy.data.objects):
        raise RuntimeError("do not replace an existing Blender scene for a preview")
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    payload = Path(receipt["artifacts"]["glb"]["path"])
    actual = hashlib.sha256(payload.read_bytes()).hexdigest()
    if actual != receipt["artifacts"]["glb"]["fingerprint"]["sha256"]:
        raise RuntimeError("export differs from the retained receipt")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(payload))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 960, 720, 100
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.045, .06, .10, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .7
    for rotation, energy in (((.35,-.45,-.4),3), ((.6,.8,2.3),1)):
        bpy.ops.object.light_add(type="SUN")
        bpy.context.object.rotation_euler = rotation
        bpy.context.object.data.energy = energy
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.clip_end = 2000
    scene.camera = camera
    # Blender resolves bare render filenames relative to the drive root; supply
    # an absolute workspace path even when the CLI recipe uses a relative out.
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    views = []
    for name, position, target, kind, framing in (
        ("overview", (110,-140,105), (0,0,-3), "ORTHO", 150),
        ("route", (28,-49,8), (9,-10,11), "PERSP", 35),
        ("crown", (-22,-26,33), (0,0,18), "PERSP", 45),
    ):
        camera.location = position
        camera.rotation_euler = (Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
        camera.data.type = kind
        if kind == "ORTHO": camera.data.ortho_scale = framing
        else: camera.data.lens = framing
        path = out / (name + ".png")
        scene.render.filepath = str(path)
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        views.append({"name": name, "path": str(path), "position": position, "target": target,
                      "camera_type": kind, "framing": framing, "elapsed_s": round(time.perf_counter()-started,6),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    result = {"stage": "source_multiview_rendered", "name": receipt["name"], "seed": receipt["config"]["seed"],
              "glb_sha256": actual, "views": views, "saved_unreal": False,
              "acceptance": "appearance only; Unreal, collision and movement remain unverified"}
    (out / "hero.review.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    review(args.receipt, args.out)
