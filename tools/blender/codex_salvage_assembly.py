# SPDX-License-Identifier: MIT
"""Reproducible CopperPatina salvage power unit; five separate voxel meshes.

Blender: --background --factory-startup --python THIS -- --out FOLDER
Ordinary Python: python THIS --plan-only --out FOLDER

Reuses the existing modules, exposed-face mesher, palette and selected export
pipeline. Socket alignment is a source recipe, not implemented runtime snapping,
electrical wiring, gameplay, native collision or a saved Unreal assembly.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


_spec = importlib.util.spec_from_file_location(
    "_codex_salvage_modules", Path(__file__).with_name("codex_skyharbor_modules.py"))
MODULES = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MODULES)
ISLANDS = MODULES.ISLANDS
GRID = MODULES.GRID
VERSION = 1
VARIANT = "CopperPatina"
PLACEMENTS = (
    ("gearbox", "GearboxHousing", [0.0, 0.0, 1.5]),
    ("shaft", "DriveShaft", [0.0, -2.25, 2.0]),
    ("rotor", "TurbineRotor", [0.0, -3.75, 2.0]),
    ("battery", "CrystalBattery", [1.25, 0.0, 0.0]),
)


def _hash(value):
    return hashlib.sha256(ISLANDS._json(value).encode("utf-8")).hexdigest()


def _support_frame():
    """Quarter-grid rim and legs; battery-side feet stop at x=.5 metres."""
    cells = {}

    def box(x0, x1, y0, y1, z0, z1, colour):
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    cells[x, y, z] = colour

    for x0, x1 in ((-3, -1), (0, 2)):
        for y0, y1 in ((-3, -1), (1, 3)):
            box(x0, x1, y0, y1, 0, 5, "rock2")
            box(x0, x1, y0, y1, 0, 1, "roof")
    for y0 in (-3, 2):
        box(-3, 2, y0, y0 + 1, 0, 1, "roof")
        box(-3, 3, y0, y0 + 1, 5, 6, "roof")
    for x0 in (-3, 2):
        box(x0, x0 + 1, -3, 3, 5, 6, "leaf2")
    return [(x, y, z, cells[x, y, z]) for x, y, z in sorted(cells)]


def _world_socket(part, name):
    local = next(item for item in part["connection_points"] if item["name"] == name)
    position = [a + b for a, b in zip(part["location_metres"], local["position_metres"])]
    return dict(local, position_metres=position)


def _join(parts, role_a, socket_a, role_b, socket_b):
    a, b = _world_socket(parts[role_a], socket_a), _world_socket(parts[role_b], socket_b)
    delta = [x - y for x, y in zip(a["position_metres"], b["position_metres"])]
    opposed = all(x == -y for x, y in zip(a["forward"], b["forward"]))
    if any(delta) or not opposed or a["kind"] != b["kind"]:
        raise ValueError("assembly recipe has incompatible or misaligned sockets")
    return {
        "a": {"role": role_a, "socket": socket_a},
        "b": {"role": role_b, "socket": socket_b},
        "position_metres": a["position_metres"], "delta_metres": delta,
        "forward_a": a["forward"], "forward_b": b["forward"],
        "kind": a["kind"], "opposed_forward": opposed,
        "runtime_constraint_implemented": False,
    }


def plan(seed=86100):
    """Return local voxel meshes and an exact, translation-only assembly recipe."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    source_paths = (Path(__file__), Path(MODULES.__file__),
                    Path(ISLANDS.__file__), Path(ISLANDS.BASE.__file__),
                    Path(ISLANDS.ship.__file__), Path(ISLANDS.sides.__file__))
    dependencies = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in source_paths}
    config = {
        "assembly": "PowerUnit", "preset": VARIANT, "seed": seed,
        "version": VERSION, "voxel_metres": GRID,
        "placements": [{"role": role, "part": part, "location_metres": position}
                       for role, part, position in PLACEMENTS],
        "source_dependencies_sha256": dependencies,
        "source_sha256": _hash(dependencies),
    }
    name = "CodexSalvage_PowerUnit_%s" % seed
    meshes, parts = {}, {}
    for role, part_name, position in PLACEMENTS:
        part_seed = seed + MODULES.PARTS.index(part_name)
        cells, metadata = MODULES.plan(part_name, VARIANT, part_seed)
        meshes[role] = cells
        parts[role] = {
            "role": role, "part": part_name, "object_name": name + "_" + role,
            "source_generator": "codex_skyharbor_modules.plan",
            "source_config": metadata["config"],
            "source_config_sha256": metadata["config_sha256"],
            "voxel_sha256": metadata["voxel_sha256"],
            "pivot_metres": metadata["pivot_metres"],
            "location_metres": list(position), "rotation_euler_radians": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0], "rotation_axis": metadata["rotation_axis"],
            "connection_points": metadata["connection_points"],
        }
    meshes["support"] = _support_frame()
    parts["support"] = {
        "role": "support", "part": "PowerUnitSupportFrame",
        "object_name": name + "_support", "source_generator": "codex_salvage_assembly._support_frame",
        "voxel_sha256": _hash(meshes["support"]), "pivot_metres": [0.0, 0.0, 0.0],
        "location_metres": [0.0, 0.0, 0.0], "rotation_euler_radians": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0], "rotation_axis": None,
        "connection_points": [MODULES.socket("gearbox-seat", [0.0, 0.0, 1.5], [0, 0, 1], "gearbox-support")],
        "supports": {"role": "gearbox", "surface_z_metres": 1.5, "geometry_fit_only": True},
    }
    for part in parts.values():
        part["assembly_connection_points"] = [
            _world_socket(part, point["name"]) for point in part["connection_points"]]
    recipe = {
        "schema": "daedalus.codex-salvage-recipe.v1", "name": name,
        "config": config, "config_sha256": _hash(config), "snap_grid_metres": GRID,
        "assembly_origin_metres": [0.0, 0.0, 0.0], "parts": list(parts.values()),
        "joins": [_join(parts, "gearbox", "input", "shaft", "output"),
                  _join(parts, "shaft", "input", "rotor", "axle")],
        "electrical_wiring": {"implemented": False, "battery_role": "battery",
                              "description": "Adjacent battery only; no connection to gearbox or rotor."},
        "implemented_gameplay": False, "runtime_snapping_implemented": False,
        "native_collision_verified": False, "saved_unreal": False,
        "world_placement": "held; reproducible assembly coordinates only",
    }
    palette = sorted({cell[3] for cells in meshes.values() for cell in cells})
    world_cells = [(cell, parts[role]["location_metres"])
                   for role, cells in meshes.items() for cell in cells]
    report = {
        "schema": "daedalus.codex-salvage-assembly.v1", "name": name,
        "config": config, "config_sha256": _hash(config), "voxel_sha256": _hash(meshes),
        "recipe": recipe, "recipe_sha256": _hash(recipe), "mesh_count": len(meshes),
        "voxel_counts": {role: len(cells) for role, cells in meshes.items()},
        "palette_rgb": {key: list(ISLANDS.PALETTE[key]) for key in palette},
        "palette_surface": {key: ISLANDS.SURFACES[key] for key in palette},
        "bounds_metres": {
            "min": [min(cell[i] * GRID + location[i] for cell, location in world_cells) for i in range(3)],
            "max": [max((cell[i] + 1) * GRID + location[i] for cell, location in world_cells) for i in range(3)],
        },
        "provenance": {"author": "team-codex", "reuses": "Codex CopperPatina salvage module generators",
                       "complements": "Sol harbor kit; no Dock/Beacon/Boathouse duplication"},
        "collision": "No authored collision; native import and dynamic physics unverified.",
        "implemented_gameplay": False, "runtime_snapping_implemented": False,
        "native_collision_verified": False, "stage": "planned", "saved_unreal": False,
    }
    return meshes, report


def _paths(out_folder, name, seed):
    folder = Path(out_folder).resolve() / ("a%s" % seed)
    paths = {kind: folder / (name + suffix) for kind, suffix in (
        ("glb", ".glb"), ("fbx", ".fbx"), ("recipe", ".recipe.json"),
        ("receipt", ".receipt.json"), ("plan", ".plan.json"), ("sent", ".sent.json"))}
    if sys.platform == "win32" and any(len(str(path)) >= 260 for path in paths.values()):
        raise ValueError("assembly output path exceeds Windows limit; choose a shorter --out folder")
    return paths


def build(out_folder, seed=86100):
    """Export the five owned meshes; retain artifacts and restore scene selection."""
    started = time.perf_counter()
    meshes, report = plan(seed)
    generation_s = round(time.perf_counter() - started, 6)
    paths = _paths(out_folder, report["name"], seed)
    cached = ISLANDS._cached(paths["receipt"], report["config"])
    if cached and cached.get("recipe_sha256") == report["recipe_sha256"] and "recipe" in cached.get("artifacts", {}):
        return dict(cached, export_skipped=True)
    if any(paths[kind].exists() for kind in ("glb", "fbx", "receipt", "sent")):
        raise RuntimeError("retain existing assembly artifacts; choose a new --out folder or seed: " + str(paths["receipt"].parent))
    # A prior plan-only invocation is reusable only when its complete bytes still
    # match this source/config. Do not overwrite even a matching retained plan.
    for kind, value in (("plan", report), ("recipe", report["recipe"])):
        expected = (json.dumps(value, indent=2, sort_keys=True) + "\n").replace("\n", os.linesep).encode("utf-8")
        if paths[kind].exists() and paths[kind].read_bytes() != expected:
            raise RuntimeError("retain mismatched assembly " + kind + "; choose a new --out folder or seed")
    report["elapsed_s"] = {"generation": generation_s}
    bpy = ISLANDS.BASE.bpy
    if bpy is None or bpy.context.mode != "OBJECT":
        raise RuntimeError("export requires Blender Object mode during an owned turn")
    parts = {part["role"]: part for part in report["recipe"]["parts"]}
    if any(part["object_name"] in bpy.data.objects for part in parts.values()):
        raise RuntimeError("assembly objects already exist; choose a different seed")
    selected, active = list(bpy.context.selected_objects), bpy.context.view_layer.objects.active
    objects = []
    try:
        started = time.perf_counter()
        for role, cells in meshes.items():
            part = parts[role]
            obj = ISLANDS.BASE._mesh_from_voxels(part["object_name"], cells, scale=GRID)
            objects.append(obj)
            ISLANDS._palette_slots(bpy, obj, cells)
            obj.location = part["location_metres"]
            obj["daedalus_owner"] = ISLANDS.OWNER
            obj["daedalus_assembly_role"] = role
            obj["daedalus_config_sha256"] = report["config_sha256"]
            obj["daedalus_recipe_sha256"] = report["recipe_sha256"]
        report["elapsed_s"]["mesh"] = round(time.perf_counter() - started, 6)
        paths["receipt"].parent.mkdir(parents=True, exist_ok=True)
        if not paths["recipe"].exists():
            ISLANDS._write(paths["recipe"], report["recipe"])
        started = time.perf_counter()
        scope = {"PARAMS": json.dumps({"path": str(paths["glb"]), "objects": [obj.name for obj in objects]})}
        exec(ISLANDS.sides.BLENDER_EXPORT, scope)
        pipeline = ISLANDS.ship.prebuilt(report["name"], str(paths["glb"]), scope["result"])
        report.update(blender=pipeline["blender"], file=pipeline["file"])
        report["elapsed_s"]["glb_export"] = round(time.perf_counter() - started, 6)
        started = time.perf_counter()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in objects)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.export_scene.fbx(
            filepath=str(paths["fbx"]), use_selection=True, object_types={"MESH"},
            use_mesh_modifiers=True, apply_scale_options="FBX_SCALE_ALL",
            axis_forward="-Y", axis_up="Z", bake_anim=False)
        report["elapsed_s"]["fbx_export"] = round(time.perf_counter() - started, 6)
        report["artifacts"] = {
            kind: {"path": str(paths[kind]), "fingerprint": ISLANDS.ship.fingerprint(paths[kind])}
            for kind in ("glb", "fbx", "recipe")}
        report.update(stage="exported", export_skipped=False)
        ISLANDS._write(paths["sent"], pipeline)
        ISLANDS._write(paths["receipt"], report)
        return report
    finally:
        for obj in objects:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for obj in bpy.context.view_layer.objects:
            obj.select_set(False)
        for obj in selected:
            if obj.name in bpy.context.view_layer.objects:
                obj.select_set(True)
        if active and active.name in bpy.context.view_layer.objects:
            bpy.context.view_layer.objects.active = active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ISLANDS.ROOT / "engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/SalvageAssemblies")
    parser.add_argument("--seed", type=int, default=86100)
    parser.add_argument("--plan-only", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None
    args = parser.parse_args(argv)
    if args.plan_only:
        _, report = plan(args.seed)
        paths = _paths(args.out, report["name"], args.seed)
        if any(path.exists() for path in paths.values()):
            raise RuntimeError("retain existing assembly artifacts; choose a new --out folder or seed")
        ISLANDS._write(paths["plan"], report)
        ISLANDS._write(paths["recipe"], report["recipe"])
    else:
        report = build(args.out, args.seed)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
