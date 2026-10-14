# SPDX-License-Identifier: MIT
"""Codex biome variants of the existing voxel_island planner and mesher.

Ordinary Python: python tools/blender/codex_contest_island.py --plan-only --all
Blender console (during an owned turn): import codex_contest_island as islands;
islands.build_batch(output_folder, keep=False)

No editor connection is opened here. Export receipts are intermediate artifacts;
an island counts as delivered only after the existing native Unreal importer saves it.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "connectors" / "claude-asset-pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))
from asset_pipeline import ship, sides  # existing export script, hashes and GLB witness

_spec = importlib.util.spec_from_file_location("_codex_voxel_base", Path(__file__).with_name("voxel_island.py"))
BASE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BASE)

VERSION = 1
OWNER = "codex-contest"
INVENTORY = ROOT / "engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/original-islands-inventory.json"
PALETTE = dict(BASE.PAL, grass=(.40,.76,.28), grass2=(.67,.83,.32), rock=(.37,.42,.61),
               rock2=(.20,.24,.39), sand=(.95,.79,.38), water=(.14,.74,.93), leaf=(.27,.73,.43),
               leaf2=(.29,.82,.73), blossom=(.90,.38,.77), blossom2=(.98,.67,.89), crystal=(.70,.42,.96))
SURFACES = {key: {"roughness": .85, "metallic": 0.0} for key in PALETTE}
for _key in ("water", "foam"):
    SURFACES[_key] = {"roughness": .18, "metallic": 0.0}
for _key in ("crystal", "crystal2"):
    SURFACES[_key] = {"roughness": .28, "metallic": .12}
SURFACES["roof"] = {"roughness": .42, "metallic": .55}
SURFACES["trunk"] = {"roughness": .72, "metallic": 0.0}
PRESETS = {
    "summit-rim": {"seed": 84011, "radius": 46, "depth": 22, "terrace": 3, "relief": 21,
                   "original": "blender-boss", "features": ["circular water rim", "stepped central summit", "pastel block trees"]},
    "cliff-garden": {"seed": 84022, "radius": 46, "depth": 28, "terrace": 3, "relief": 18,
                     "original": "buffffff", "features": ["enclosing block cliff bowl", "orderly crop beds", "lime/cyan/lavender accents"]},
    "river-canyon": {"seed": 84033, "radius": 46, "depth": 26, "terrace": 3, "relief": 15,
                     "original": "prometheus", "features": ["branching river canyon", "gold-green plateaus", "white pillar ring"]},
}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def configuration(preset, seed=None, hero=False):
    if preset not in PRESETS:
        raise ValueError("unknown preset: " + str(preset))
    config = dict(PRESETS[preset], preset=preset, version=VERSION, voxel_metres=1.0)
    if hero:
        if preset != "summit-rim":
            raise ValueError("hero revision currently uses the inspected summit-rim original")
        config["revision"] = "HeroR3" if hero is True else str(hero)
        if config["revision"] not in ("HeroR2", "HeroR3"):
            raise ValueError("unknown retained hero revision")
        config["features"] = config["features"] + ["winding pale summit route", "crystal summit crown", "fitted flowering groves"]
        if config["revision"] == "HeroR3":
            config["features"] += ["quarter-metre fitted summit treads"]
    catalog = json.loads(INVENTORY.read_text(encoding="utf-8"))
    original = next(entry for entry in catalog["entries"] if entry["id"] == config["original"])
    config["reference"] = {key: original.get(key) for key in ("id", "name", "author", "team", "provenance", "image", "sources", "manifest")}
    config["reference"]["inventory_sha256"] = hashlib.sha256(INVENTORY.read_bytes()).hexdigest()
    config["reference"]["inspection"] = "historical image and original source catalog; not current native acceptance"
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        config["seed"] = seed
    # A source change invalidates the export cache, including changes in reused code.
    config["source_sha256"] = hashlib.sha256(
        Path(__file__).read_bytes() + Path(BASE.__file__).read_bytes()).hexdigest()
    return config


def identity(config):
    return "CodexIsland_%s_%s%s" % (config["preset"].replace("-", "_"), config["seed"],
                                      "_" + config["revision"] if config.get("revision") else "")


def plan(preset="summit-rim", seed=None, hero=False):
    """Reuse the seeded footprint, strata and dressing; apply bounded biome terraces.

    The body fits inside 92 x 92 metres. Clouds may extend outside that footprint.
    All randomness is local; dictionary/list order and voxel hash are reproducible.
    """
    config = configuration(preset, seed, hero)
    radius = config["radius"]
    original = BASE.plan(config["seed"], radius, config["depth"])
    old_top = {}
    old_bottom = {}
    for x, y, z, _ in original["island"]:
        if not (-radius <= x < radius and -radius <= y < radius):
            continue
        old_top[x, y] = max(z, old_top.get((x, y), z))
        old_bottom[x, y] = min(z, old_bottom.get((x, y), z))
    rng = random.Random(config["seed"] ^ 0xDAEDA1)
    waves = [(rng.uniform(0, math.tau), rng.uniform(.035, .075)) for _ in range(3)]

    def height(x, y):
        r = math.hypot(x + .5, y + .5) / radius
        falloff = max(0.0, 1.0 - r ** 2)
        noise = sum(math.sin(x * f + p) * math.cos(y * f - p) for p, f in waves) / 3
        if preset == "summit-rim":
            value = config["relief"] * max(0, 1 - r / .65) + 1.5 * noise
        elif preset == "cliff-garden":
            value = config["relief"] * max(0, min(1, (r - .63) / .18)) + 1.5 * noise if r > .63 else 0
        else:
            value = 6 + config["relief"] * falloff * (.45 + .25 * noise)
        return math.floor(value / config["terrace"]) * config["terrace"]

    heights = {xy: height(*xy) for xy in old_top}
    # Reuse the existing pond/channel layout; keep one horizontal liquid surface.
    wet = {(x, y) for x, y, z, _ in original["water"] if z == -1 and (x, y) in heights}
    liquid_level = -5 if preset == "river-canyon" else 0
    if preset == "summit-rim":
        wet |= {xy for xy in heights if radius - 4 < math.hypot(xy[0]+.5, xy[1]+.5) < radius - 2}
    elif preset == "river-canyon":
        phase = waves[0][0]
        wet = {xy for xy in heights if abs(xy[1] - 4 * math.sin(xy[0] / 14 + phase)) < 2.5 or
               (xy[0] > -4 and abs(xy[1] - .65 * xy[0] - 2) < 2)}
    for xy in wet:
        heights[xy] = liquid_level - 2

    route = set()
    if hero:
        # A broad ribbon climbs the existing summit rather than a detached prop.
        # One-metre steps are visual terrain; native movement remains unverified.
        for index in range(38):
            t = index / 37
            cx, cy = round(8 + 5 * math.sin(t * math.pi * 1.4)), -40 + index
            level = round(18 * t)
            for x in range(cx - 2, cx + 3):
                for y in range(cy - 1, cy + 2):
                    if (x, y) in heights:
                        heights[x, y] = level
                        wet.discard((x, y))
                        route.add((x, y))

    # The inherited cottage gets a level foundation, rather than sheared walls.
    cottage_xy = {(x, y) for x, y, _, _ in original["cottage"] if (x, y) in heights}
    cottage_level = max((heights[xy] for xy in cottage_xy), default=0)
    for xy in cottage_xy:
        heights[xy] = cottage_level
        wet.discard(xy)
        route.discard(xy)

    route_steps = {}
    if hero and config["revision"] == "HeroR3":
        # Quarter-metre exposed-face geometry rests on the metre terrain. Keep
        # the dense grid confined to the route rather than subdividing the island.
        deck, low = {}, {}
        for yq in range(-160, -11):
            t = min(1.0, max(0.0, (yq / 4 + 40) / 37))
            cxq = round((8 + 5 * math.sin(t * math.pi * 1.4)) * 4)
            zq = math.floor(18 * t * 4) + 4
            for xq in range(cxq - 8, cxq + 9):
                xy = math.floor(xq / 4), math.floor(yq / 4)
                if xy in route:
                    deck[xq, yq] = zq
                    low[xy] = min(low.get(xy, zq), zq)
        for xy, zq in low.items():
            heights[xy] = math.floor(zq / 4) - 1
        for (xq, yq), zq in deck.items():
            xy = math.floor(xq / 4), math.floor(yq / 4)
            for heightq in range((heights[xy] + 1) * 4, zq + 1):
                route_steps[xq, yq, heightq] = "flower_w" if (yq // 12) % 5 else "sand"

    voxels = {layer: [] for layer in original}
    for x, y, z, colour in original["island"]:
        xy = x, y
        if xy not in heights:
            continue
        dz = heights[xy] - old_top[xy]
        if z == old_top[xy]:
            if xy in route:
                colour = "rock2" if route_steps else ("flower_w" if (x + y) % 7 else "sand")
            elif xy in wet:
                colour = "sand"
            elif preset == "cliff-garden" and heights[xy] >= 9:
                colour = "rock"
            elif preset == "summit-rim" and heights[xy] >= 12:
                colour = "rock" if heights[xy] < 18 else "flower_w"
            elif preset == "river-canyon":
                colour = "grass2"
        voxels["island"].append((x, y, z + dz, colour))

    liquid, accent = "water", "foam"
    voxels["water"] = [(x, y, liquid_level - 1, liquid) for x, y in sorted(wet)]
    # Preserve the existing waterfall column, extended to the local underside.
    falls = {(x, y) for x, y, z, _ in original["water"] if z < -1 and (x, y) in wet}
    for x, y in sorted(falls):
        bottom = old_bottom[x, y] + heights[x, y] - old_top[x, y] - 4
        for z in range(liquid_level - 2, bottom - 1, -1):
            voxels["water"].append((x, y, z, accent if z % 3 == 0 else liquid))

    # Translate connected tree canopies together, anchored to their lowest voxel.
    trees = {(x, y, z): c for x, y, z, c in original["trees"]}
    remaining = set(trees)
    while remaining:
        start = min(remaining)
        component, todo = [], [start]
        remaining.remove(start)
        while todo:
            p = todo.pop()
            component.append(p)
            for dx, dy, dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                q = p[0]+dx, p[1]+dy, p[2]+dz
                if q in remaining:
                    remaining.remove(q)
                    todo.append(q)
        root = min(component, key=lambda p: (p[2], p[0], p[1]))
        xy = root[:2]
        if xy not in heights or xy in wet or (hero and any((x, y) in route for x, y, _ in component)):
            continue
        shift = heights[xy] - old_top[xy]
        for x, y, z in component:
            colour = trees[x, y, z]
            voxels["trees"].append((x, y, z + shift, colour))

    for layer in ("cottage", "flowers", "rocks", "crystals", "clouds"):
        for x, y, z, colour in original[layer]:
            xy = x, y
            if layer == "clouds":
                shift = 0
            elif xy not in heights or (xy in wet and layer != "crystals"):
                continue
            elif hero and xy in route and layer in ("flowers", "rocks"):
                continue
            elif layer == "cottage":
                shift = cottage_level
                if preset == "cliff-garden":
                    colour = {"wall": "sand", "roof": "crystal"}.get(colour, colour)
            elif layer == "crystals":
                # Crystals attach to their own column's underside, not a global depth.
                shift = old_bottom[xy] + heights[xy] - old_top[xy] + config["depth"] + 4
            else:
                shift = heights[xy] - old_top[xy]
            voxels[layer].append((x, y, z + shift, colour))

    voxels["landmarks"] = []
    if route_steps:
        voxels["route_steps"] = [(x,y,z,colour) for (x,y,z),colour in sorted(route_steps.items())]
    if hero:
        # Repeated fitted pedestals make a readable crown, clear of the cottage.
        for index in range(7):
            angle = math.pi * .7 + index * math.pi * 1.3 / 6
            x, y = round(8 * math.cos(angle)), round(8 * math.sin(angle))
            if (x, y) not in heights or (x, y) in cottage_xy or (x, y) in route:
                continue
            floor = heights[x, y] + 1
            for z in range(floor, floor + 3):
                voxels["landmarks"].append((x, y, z, "rock2"))
            for z in range(floor + 3, floor + 6):
                voxels["landmarks"].append((x, y, z, "crystal2" if index % 2 else "crystal"))
    if preset == "cliff-garden":
        # New colourful crop-grid geometry derived from Six-F's observed layout.
        for row in range(4):
            for col in range(3):
                for x in range(10 + col * 5, 14 + col * 5):
                    for y in range(-19 + row * 4, -17 + row * 4):
                        if (x, y) in heights and (x, y) not in wet and heights[x, y] == 0:
                            voxels["landmarks"].append((x, y, 1, "dirt"))
                            if (x + y) % 2 == 0:
                                voxels["landmarks"].append((x, y, 2, ("blossom", "sand", "crystal2")[col]))
    elif preset == "river-canyon":
        # An architectural ring, not a copy of Prometheus's source assets.
        for index in range(10):
            angle = index * math.tau / 10
            x, y = int(-20 + 7 * math.cos(angle)), int(20 + 7 * math.sin(angle))
            if (x, y) in heights and (x, y) not in wet:
                for z in range(heights[x, y] + 1, heights[x, y] + 6):
                    voxels["landmarks"].append((x, y, z, "flower_w"))

    # Sort/deduplicate once: overlapping trees and clouds never create duplicate cells.
    for layer, cells in voxels.items():
        cells = {(x, y, z): c for x, y, z, c in cells}
        voxels[layer] = [(x, y, z, cells[x, y, z]) for x, y, z in sorted(cells)]
    return config, voxels


def receipt(config, voxels):
    all_cells = [cell for cells in voxels.values() for cell in cells]
    scaled_cells = [(cell, .25 if layer == "route_steps" else 1.0) for layer,cells in voxels.items() for cell in cells]
    return {
        "schema": "daedalus.codex-island.v1", "name": identity(config), "config": config,
        "config_sha256": hashlib.sha256(_json(config).encode()).hexdigest(),
        "voxel_sha256": hashlib.sha256(_json(voxels).encode()).hexdigest(),
        "voxels": BASE.stats(voxels), "palette": sorted({c[3] for c in all_cells}),
        "palette_rgb": {key: list(PALETTE[key]) for key in sorted({c[3] for c in all_cells})},
        "palette_surface": {key: SURFACES[key] for key in sorted({c[3] for c in all_cells})},
        "layer_voxel_metres": {layer: .25 if layer == "route_steps" else 1.0 for layer in voxels},
        "bounds_metres": {"min": [min(c[i] * scale for c,scale in scaled_cells) for i in range(3)],
                          "max": [max((c[i] + 1) * scale for c,scale in scaled_cells) for i in range(3)]},
        "stage": "planned", "saved_unreal": False,
    }


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _cached(path, config):
    """Skip export only when source/config AND every recorded file's bytes match."""
    if not path.is_file():
        return None
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("config") != config or saved.get("stage") != "exported":
            return None
        artifacts = saved.get("artifacts", {})
        if not artifacts or not {"glb", "fbx"} <= set(artifacts):
            return None
        for item in artifacts.values():
            if ship.fingerprint(item["path"]) != item["fingerprint"]:
                return None
        return saved
    except (OSError, ValueError, KeyError, TypeError):
        return None


def build(out_folder, preset="summit-rim", seed=None, keep=False, hero=False):
    """Export through the existing pipeline during an explicitly coordinated turn.

    Uses metre geometry, existing VoxelVertexColour, selected objects only, a sibling
    FBX for native import, and named UCX cells matching terraced surface columns.
    Never deletes another island or saves/replaces the shared Blender scene.
    """
    bpy = BASE.bpy
    if bpy is None:
        raise RuntimeError("build requires Blender bpy; use --plan-only outside Blender")
    if bpy.context.mode != "OBJECT":
        raise RuntimeError("finish the owner's current edit operation before exporting")
    config = configuration(preset, seed, hero)
    name = identity(config)
    folder = Path(out_folder).resolve() / ("h" + str(config["seed"]) if hero else name)
    saved_path = folder / (name + ".receipt.json")
    cached = _cached(saved_path, config)
    if cached:
        return dict(cached, export_skipped=True)
    if saved_path.exists() or (folder / (name + ".glb")).exists() or (folder / (name + ".fbx")).exists():
        raise RuntimeError("retain existing revision; choose a new output folder or seed: " + str(folder))
    started = time.perf_counter()
    config, voxels = plan(preset, seed, hero)
    report = receipt(config, voxels)
    report["elapsed_s"] = {"generation": round(time.perf_counter() - started, 6)}
    folder.mkdir(parents=True, exist_ok=True)
    glb_path, fbx_path = folder / (name + ".glb"), folder / (name + ".fbx")
    if any(o.name.startswith(name + "_") for o in bpy.data.objects):
        raise RuntimeError("island objects already exist; use a different seed or keep=False on the first export")
    selected = list(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    objects, hulls = [], []
    try:
        started = time.perf_counter()
        for layer, cells in voxels.items():
            if cells:
                obj = BASE._mesh_from_voxels(name + "_" + layer, cells, scale=.25 if layer == "route_steps" else 1.0)
                _palette_slots(bpy, obj, cells)
                obj["daedalus_owner"] = OWNER
                obj["daedalus_config_sha256"] = report["config_sha256"]
                objects.append(obj)
        report["elapsed_s"]["mesh"] = round(time.perf_counter() - started, 6)
        started = time.perf_counter()
        # Execute the repository's existing selected-object export/report contract.
        scope = {"PARAMS": json.dumps({"path": str(glb_path), "objects": [o.name for o in objects]})}
        exec(sides.BLENDER_EXPORT, scope)
        pipeline = ship.prebuilt(name, str(glb_path), scope["result"])
        report["blender"] = pipeline["blender"]
        report["file"] = pipeline["file"]
        report["elapsed_s"]["glb_export"] = round(time.perf_counter() - started, 6)
        started = time.perf_counter()
        _collision(bpy, name, voxels["island"], hulls)
        for o in bpy.context.view_layer.objects:
            o.select_set(o in objects or o in hulls)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, use_mesh_modifiers=True,
                                 apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z",
                                 bake_anim=False)
        report["elapsed_s"]["fbx_export"] = round(time.perf_counter() - started, 6)
        report["collision_hulls"] = len(hulls)
        report["artifacts"] = {kind: {"path": str(path), "fingerprint": ship.fingerprint(path)}
                               for kind, path in (("glb", glb_path), ("fbx", fbx_path))}
        report["stage"] = "exported"
        report["export_skipped"] = False
        _write(folder / (name + ".sent.json"), pipeline)
        _write(saved_path, report)
        return report
    finally:
        # Only remove objects created by this invocation, even after an export fails.
        for obj in hulls + ([] if keep else objects):
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


def _palette_slots(bpy, obj, cells):
    """Keep existing vertex colours, and encode face colours as stable slot names.

    Native FBX import_file defaults to ignoring vertex colours. Palette slots let
    the receiving native tools bind stable project colour assets without changing
    shared importer defaults. GLB still uses the existing vertex-colour shader.
    """
    keys = sorted({cell[3] for cell in cells})
    mesh = obj.data
    colour = mesh.color_attributes.get("Col")
    if colour is None:
        raise RuntimeError("existing voxel mesher did not produce Col attributes")
    original = mesh.materials[0]
    mesh.materials.clear()
    for key in keys:
        name = "CodexVoxel_" + key
        material = bpy.data.materials.get(name)
        if material is None:
            material = original.copy()
            material.name = name
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Roughness"].default_value = SURFACES[key]["roughness"]
        shader.inputs["Metallic"].default_value = SURFACES[key]["metallic"]
        mesh.materials.append(material)
    for polygon in mesh.polygons:
        # BMesh's byte-color layer stores the base palette as sRGB. Reading its
        # linear .color here misidentifies grass/rock as darker dirt palette keys.
        rgb = colour.data[polygon.loop_start].color_srgb[:3]
        key = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(rgb, BASE.PAL[k])))
        polygon.material_index = keys.index(key)
        for loop_index in polygon.loop_indices:
            colour.data[loop_index].color = PALETTE[key] + (1.0,)


def _collision(bpy, name, body, hulls):
    """One bounded convex box per terraced patch, never a hull across the lagoon.

    Greedy rectangular coalescing of equal-height columns leaves lagoon floors
    and terrace heights intact. Each rectangle reaches its lowest column bottom;
    this approximates the jagged underside while avoiding thousands of hulls.
    Names target the body mesh, so native FBX UCX association is explicit.
    """
    columns = {}
    for x, y, z, _ in body:
        lo, hi = columns.get((x, y), (z, z))
        columns[x, y] = min(lo, z), max(hi, z)
    pending = set(columns)
    while pending:
        x, y = min(pending)
        lo, hi = columns[x, y]
        width = 1
        while (x + width, y) in pending and columns[x + width, y][1] == hi:
            width += 1
        depth = 1
        while all((xx, y + depth) in pending and columns[xx, y + depth][1] == hi
                  for xx in range(x, x + width)):
            depth += 1
        for xx in range(x, x + width):
            for yy in range(y, y + depth):
                lo = min(lo, columns[xx, yy][0])
                pending.remove((xx, yy))
        # A primitive box is already convex; no edit-mode/global-selection operation.
        mesh = bpy.data.meshes.new("UCX_%s_island_%03d" % (name, len(hulls)))
        verts = [(xx, yy, zz) for zz in (lo, hi + 1) for yy in (y, y + depth) for xx in (x, x + width)]
        mesh.from_pydata(verts, [], [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
        obj = bpy.data.objects.new(mesh.name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj["daedalus_owner"] = OWNER
        hulls.append(obj)
    return hulls


def build_batch(out_folder, keep=False):
    """Three selected-only exports in one owned Blender turn; no app acquisition."""
    results = [build(out_folder, preset, keep=keep) for preset in PRESETS]
    _write(Path(out_folder) / "codex-islands.batch.json", results)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=PRESETS, default="summit-rim")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--hero", action="store_true", help="retained summit-rim HeroR2 revision; preserve prepared exports")
    parser.add_argument("--hero-revision", choices=("HeroR2", "HeroR3"), default="HeroR3")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "engines/unreal/DaedalusLink/Content/IslandSource/CodexContest")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None
    args = parser.parse_args(argv)
    if args.all and args.seed is not None:
        parser.error("--seed names one island; omit --all")
    if args.hero and args.all:
        parser.error("--hero prepares one summit-rim revision")
    if args.plan_only:
        results = []
        for preset in PRESETS if args.all else [args.preset]:
            started = time.perf_counter()
            config, voxels = plan(preset, args.seed, args.hero_revision if args.hero else False)
            value = receipt(config, voxels)
            value["elapsed_s"] = {"generation": round(time.perf_counter() - started, 6)}
            _write(args.out / (identity(config) + ".plan.json"), value)
            results.append(value)
    else:
        results = build_batch(args.out) if args.all else [build(args.out, args.preset, args.seed, hero=args.hero_revision if args.hero else False)]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
