# SPDX-License-Identifier: MIT
"""Recolour a retained Codex island GLB without regenerating its geometry.

Ordinary Python: --receipt SOURCE --out NEW_FOLDER --palette-seed 91011 --plan-only
Blender: --background --factory-startup --python THIS -- [same args, no plan-only]
The geometry seed is inherited; palette_seed controls only a local colour PRNG.
Exports remain held from Unreal. No shared scene save, bridge or native call.
"""
import argparse
import colorsys
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import struct
import sys
import time

_spec = importlib.util.spec_from_file_location("_codex_palette_islands", Path(__file__).with_name("codex_contest_island.py"))
ISLANDS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ISLANDS)
ship, sides = ISLANDS.ship, ISLANDS.sides
PROFILE = "coherent-bounded-hsv-v1"
GROUPS = {
    "vegetation": {"grass", "grass2", "leaf", "leaf2"},
    "liquid": {"water", "foam", "window"},
    "accent": {"blossom", "blossom2", "crystal", "crystal2", "flower_r", "flower_y"},
    "earth": {"dirt", "dirt2", "rock", "rock2", "sand", "trunk", "roof", "door"},
}


def _hash(value):
    return hashlib.sha256(ISLANDS._json(value).encode()).hexdigest()


def _linear(value):
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def _luminance(rgb):
    return sum(weight * _linear(value) for weight, value in zip((.2126, .7152, .0722), rgb))


def _palette(source, seed):
    rng = random.Random(seed)
    hue = rng.uniform(-.055, .055)
    shifts = {group: [hue + rng.uniform(-.018, .018), rng.uniform(.92, 1.08), rng.uniform(-.035, .035)]
              for group in (*GROUPS, "neutral")}
    palette, original_hsv = {}, {}
    for key, rgb in sorted(source.items()):
        if len(rgb) != 3 or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1 for value in rgb):
            raise ValueError("source palette requires finite RGB values in [0,1]")
        h, s, v = original_hsv[key] = colorsys.rgb_to_hsv(*rgb)
        group = next((name for name, keys in GROUPS.items() if key in keys), "neutral")
        dh, sm, dv = shifts[group]
        # Near-neutral whites stay near-neutral instead of acquiring random tint.
        palette[key] = list(colorsys.hsv_to_rgb((h + (dh if s >= .12 else 0)) % 1,
                           min(.96, max(0, s * sm)), min(.98, max(.08, v + dv))))
    separation = []
    for a, b in (("grass", "grass2"), ("rock", "rock2"), ("water", "foam"), ("crystal", "crystal2")):
        if a not in palette or b not in palette:
            continue
        dark, light = sorted((a, b), key=lambda key: _luminance(source[key]))
        for _ in range(24):
            if _luminance(palette[light]) - _luminance(palette[dark]) >= .06:
                break
            for key, delta in ((light, .01), (dark, -.01)):
                h, s, v = colorsys.rgb_to_hsv(*palette[key])
                lo, hi = max(.08, original_hsv[key][2] - .12), min(.98, original_hsv[key][2] + .12)
                palette[key] = list(colorsys.hsv_to_rgb(h, s, max(lo, min(hi, v + delta))))
        separation.append({"dark": dark, "light": light, "linear_luminance_gap": round(_luminance(palette[light]) - _luminance(palette[dark]), 6)})
    return {key: [round(value, 7) for value in rgb] for key, rgb in sorted(palette.items())}, {
        "profile": PROFILE, "global_hue_turns": hue, "group_shifts": shifts,
        "max_value_shift_from_source": .12, "contrast_target": .06, "measured_palette_gaps": separation,
        "colour_policy": "recipe RGB is sRGB; shader/vertex assignments use converted linear RGB"}


def plan(receipt_path, palette_seed=91011):
    if isinstance(palette_seed, bool) or not isinstance(palette_seed, int):
        raise ValueError("palette_seed must be an integer")
    receipt_path = Path(receipt_path).resolve()
    raw = receipt_path.read_bytes()
    source = json.loads(raw)
    if source.get("schema") != "daedalus.codex-island.v1" or source.get("stage") != "exported":
        raise ValueError("require an existing exported Codex island source receipt")
    geometry_seed = source["config"]["seed"]
    if type(geometry_seed) is not int:
        raise ValueError("source geometry seed must be explicit")
    glb = source["artifacts"]["glb"]
    if ship.fingerprint(glb["path"]) != glb["fingerprint"]:
        raise ValueError("retained source GLB differs from its receipt")
    objects = source["blender"]["objects"]
    if not objects or len({row["name"] for row in objects}) != len(objects):
        raise ValueError("source object identities are absent or duplicated")
    palette, profile = _palette(source["palette_rgb"], palette_seed)
    dependencies = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (
        Path(__file__), Path(ISLANDS.__file__), Path(ISLANDS.BASE.__file__), Path(ship.__file__), Path(sides.__file__), Path(ship.glb.__file__))}
    config = {"version": 1, "seed": geometry_seed, "geometry_seed": geometry_seed, "palette_seed": palette_seed,
              "profile": PROFILE, "source_name": source["name"], "source_receipt": str(receipt_path),
              "source_receipt_sha256": hashlib.sha256(raw).hexdigest(), "source_glb": copy.deepcopy(glb),
              "source_config_sha256": source["config_sha256"], "wrapper_sha256": dependencies[Path(__file__).name],
              "source_dependencies_sha256": dependencies, "placement": copy.deepcopy(source.get("placement"))}
    name = "CodexPalette_g%s_p%s" % (geometry_seed, palette_seed)
    mapping = {row["name"]: name + row["name"][len(source["name"]):] for row in objects}
    if any(not old.startswith(source["name"] + "_") for old in mapping) or len(set(mapping.values())) != len(mapping):
        raise ValueError("source object names do not identify distinct retained layers")
    recipe = {"schema": "daedalus.codex-palette-recipe.v1", "name": name, "geometry_seed": geometry_seed,
              "palette_seed": palette_seed, "profile": profile, "palette_rgb": palette,
              "source_objects": copy.deepcopy(objects), "object_name_mapping": mapping,
              "source_glb": copy.deepcopy(glb), "source_receipt_sha256": config["source_receipt_sha256"],
              "wrapper_sha256": config["wrapper_sha256"], "placement": config["placement"],
              "object_transform_policy": "unchanged from imported source GLB; no placement generated"}
    return {"schema": "daedalus.codex-palette-variant.v1", "name": name, "config": config, "config_sha256": _hash(config),
            "recipe": recipe, "recipe_sha256": _hash(recipe), "palette_rgb": palette,
            "palette_surface": copy.deepcopy(source.get("palette_surface", {key: ISLANDS.SURFACES[key] for key in palette})),
            "bounds_metres": copy.deepcopy(source.get("bounds_metres")), "stage": "planned", "saved_unreal": False,
            "placement": config["placement"], "world_placement": "held; source placement unchanged",
            "collision": "GLB does not carry original UCX hulls; none regenerated; native collision unverified."}


def _paths(out, report):
    folder = Path(out).resolve() / ("p%s" % report["config"]["palette_seed"])
    paths = {key: folder / (report["name"] + suffix) for key, suffix in (
        ("plan", ".plan.json"), ("recipe", ".recipe.json"), ("receipt", ".receipt.json"),
        ("sent", ".sent.json"), ("glb", ".glb"), ("fbx", ".fbx"))}
    if sys.platform == "win32" and any(len(str(path)) >= 260 for path in paths.values()):
        raise ValueError("palette output path exceeds Windows limit; choose a shorter new --out folder")
    return paths


def _retain(path, value):
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise RuntimeError("retain differing palette revision; choose a new --out folder: " + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _geometry(obj):
    digest = hashlib.sha256()
    for row in obj.matrix_world:
        digest.update(struct.pack("<4d", *row))
    for vertex in obj.data.vertices:
        digest.update(struct.pack("<3d", *vertex.co))
    for polygon in obj.data.polygons:
        digest.update(struct.pack("<I", len(polygon.vertices)))
        for index in polygon.vertices:
            digest.update(struct.pack("<I", index))
    return digest.hexdigest()


def build(receipt_path, out, palette_seed=91011):
    report = plan(receipt_path, palette_seed)
    paths = _paths(out, report)
    cached = ISLANDS._cached(paths["receipt"], report["config"])
    if cached and cached.get("recipe_sha256") == report["recipe_sha256"] and {"plan", "recipe", "sent", "glb", "fbx"} <= set(cached.get("artifacts", {})):
        return dict(cached, export_skipped=True)
    if any(paths[key].exists() for key in ("receipt", "sent", "glb", "fbx")):
        raise RuntimeError("retain incomplete/mismatched palette exports; choose a new --out folder")
    import bpy
    if not bpy.app.background or bpy.data.filepath or any(obj.name not in {"Cube", "Camera", "Light"} for obj in bpy.data.objects):
        raise RuntimeError("palette export requires an isolated background factory scene")
    _retain(paths["plan"], report)
    _retain(paths["recipe"], report["recipe"])
    source = report["config"]["source_glb"]
    before_objects = set(bpy.data.objects)
    objects = []
    elapsed = {}
    try:
        started = time.perf_counter()
        bpy.ops.import_scene.gltf(filepath=source["path"])
        imported = set(bpy.data.objects) - before_objects
        objects = [obj for obj in imported if obj.type == "MESH"]
        by_name = {obj.name: obj for obj in objects}
        mapping = report["recipe"]["object_name_mapping"]
        if set(by_name) != set(mapping):
            raise RuntimeError("imported GLB object identities differ from its retained source receipt")
        geometry = {name: _geometry(obj) for name, obj in by_name.items()}
        materials = {}
        for old_name, obj in sorted(by_name.items()):
            mesh = obj.data
            keys = []
            for material in mesh.materials:
                if material is None or not material.name.startswith("CodexVoxel_"):
                    raise RuntimeError("imported mesh lacks an explicit named palette slot")
                key = material.name[len("CodexVoxel_"):]
                if key not in report["palette_rgb"]:
                    raise RuntimeError("imported palette slot differs from source recipe: " + material.name)
                keys.append(key)
                if key not in materials:
                    material.use_nodes = True
                    shader = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
                    if shader is None:
                        raise RuntimeError("imported palette material lacks Principled BSDF")
                    linear = tuple(_linear(value) for value in report["palette_rgb"][key]) + (1.0,)
                    material.diffuse_color = linear
                    for link in list(shader.inputs["Base Color"].links):
                        material.node_tree.links.remove(link)
                    colour_node = material.node_tree.nodes.new("ShaderNodeVertexColor")
                    colour_node.layer_name = "Col"
                    shader.inputs["Base Color"].default_value = (1, 1, 1, 1)
                    material.node_tree.links.new(colour_node.outputs["Color"], shader.inputs["Base Color"])
                    for parameter in ("Roughness", "Metallic"):
                        shader.inputs[parameter].default_value = report["palette_surface"][key][parameter.lower()]
                    materials[key] = material
            for colour in list(mesh.color_attributes):
                mesh.color_attributes.remove(colour)
            colour = mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="CORNER")
            mesh.color_attributes.active_color = colour
            mesh.color_attributes.render_color_index = 0
            for index, key in enumerate(keys):
                mesh.materials[index] = materials[key]
            for polygon in mesh.polygons:
                key = keys[polygon.material_index]
                rgba = tuple(_linear(value) for value in report["palette_rgb"][key]) + (1.0,)
                for loop in polygon.loop_indices:
                    colour.data[loop].color = rgba
            if _geometry(obj) != geometry[old_name]:
                raise RuntimeError("palette operation changed source geometry or object transform")
            obj.name = mapping[old_name]
        elapsed["import_and_recolour"] = round(time.perf_counter() - started, 6)
        report["source_geometry_sha256"] = geometry
        report["geometry_and_transforms_unchanged"] = True
        report["blender_object_transforms"] = {obj.name: [list(row) for row in obj.matrix_world] for obj in objects}
        started = time.perf_counter()
        scope = {"PARAMS": json.dumps({"path": str(paths["glb"]), "objects": sorted(obj.name for obj in objects)})}
        exec(sides.BLENDER_EXPORT, scope)
        pipeline = ship.prebuilt(report["name"], str(paths["glb"]), scope["result"])
        report.update(blender=pipeline["blender"], file=pipeline["file"])
        elapsed["glb_export_and_witness"] = round(time.perf_counter() - started, 6)
        started = time.perf_counter()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in objects)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.export_scene.fbx(filepath=str(paths["fbx"]), use_selection=True, use_mesh_modifiers=True,
                                 apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z", bake_anim=False)
        elapsed["fbx_export"] = round(time.perf_counter() - started, 6)
        if ship.fingerprint(source["path"]) != source["fingerprint"] or hashlib.sha256(Path(receipt_path).read_bytes()).hexdigest() != report["config"]["source_receipt_sha256"]:
            raise RuntimeError("retained source changed during palette export")
        _retain(paths["sent"], pipeline)
        report.update(stage="exported", export_skipped=False, elapsed_s=elapsed,
                      artifacts={key: {"path": str(paths[key]), "fingerprint": ship.fingerprint(paths[key])}
                                 for key in ("plan", "recipe", "sent", "glb", "fbx")})
        _retain(paths["receipt"], report)
        return report
    finally:
        for obj in list(set(bpy.data.objects) - before_objects):
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--palette-seed", type=int, default=91011)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    if args.plan_only:
        report = plan(args.receipt, args.palette_seed)
        paths = _paths(args.out, report)
        _retain(paths["plan"], report)
        _retain(paths["recipe"], report["recipe"])
    else:
        report = build(args.receipt, args.out, args.palette_seed)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
