# SPDX-License-Identifier: MIT
"""Separate salvage machinery for the proposed Ruined Sky Harbor kit.

Complements Sol's existing dock/beacon/boathouse kit; no replacement terrain or
gameplay implementation. Uses the existing voxel mesher and selected export path.
Blender: --background --factory-startup --python THIS -- --out FOLDER
Ordinary Python: python THIS --plan-only
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

_spec = importlib.util.spec_from_file_location("codex_islands", Path(__file__).with_name("codex_contest_island.py"))
ISLANDS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ISLANDS)
GRID = .25
VARIANTS = {"CopperPatina": {"metal": "roof", "accent": "leaf2"},
            "DawnCrimson": {"metal": "sand", "accent": "flower_r"},
            "StormAmethyst": {"metal": "rock", "accent": "crystal"}}
PARTS = ("BridgeCoupler", "SailPanel", "WagonWheel", "TurbineRotor", "CrystalBattery", "GearboxHousing", "DriveShaft")


def socket(name, position, forward, kind):
    return {"name": name, "position_metres": position, "forward": forward, "up": [0,0,1], "kind": kind}


def plan(part, variant, seed):
    """One local-pivot part, quarter-metre grid, deterministic palette/detail."""
    style = VARIANTS[variant]
    rng = random.Random(seed)
    cells = {}
    def box(x0, x1, y0, y1, z0, z1, colour):
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    cells[x,y,z] = colour
    joints, axis = [], None
    if part == "BridgeCoupler":
        box(0,16,-2,2,-1,1,"trunk")
        for x in (0,7,15):
            box(x,x+1,-2,2,-1,1,style["metal"])
        joints = [socket("near",[0,0,0],[-1,0,0],"bridge-beam"), socket("far",[4,0,0],[1,0,0],"bridge-beam")]
    elif part == "SailPanel":
        for z in range(16):
            for x in range(max(1, 12-z//2)):
                cells[x,-1,z] = "cloud" if (z//3)%2 else style["accent"]
        joints = [socket("mast-seat",[0,0,0],[0,-1,0],"sail-mast")]
    elif part in ("WagonWheel", "TurbineRotor"):
        outer = 5.5 if part == "WagonWheel" else 8.0
        phase = rng.choice((0, math.pi/8))
        for x in range(-8,8):
            for z in range(-8,8):
                r = math.hypot(x+.5,z+.5)
                angle = math.atan2(z+.5,x+.5) + phase
                if part == "WagonWheel":
                    solid = 4.0 <= r < outer or (1.6 <= r < outer and (abs(x+.5)<.6 or abs(z+.5)<.6))
                    colour = "rock2" if r >= 4 else style["metal"]
                else:
                    solid = 1.6 <= r < outer and (r < 3.6 or abs(math.sin(4*angle)) < .65)
                    colour = style["metal"] if r < 3.6 else style["accent"]
                if solid:
                    for y in (-1,0): cells[x,y,z] = colour
        axis = [0,1,0]
        joints = [socket("axle",[0,0,0],[0,1,0],"shaft-0.5m")]
    elif part == "CrystalBattery":
        box(-3,3,-3,3,0,3,"rock2")
        for z in range(3,9):
            width = 2 if z < 6 else 1
            box(-width,width,-width,width,z,z+1,style["accent"])
        box(-3,3,-3,3,0,1,style["metal"])
        joints = [socket("battery-seat",[0,0,0],[0,0,-1],"battery-base"), socket("power",[0,-.75,.5],[0,-1,0],"power-port")]
    elif part == "GearboxHousing":
        box(-3,3,-3,3,0,4,"rock2")
        box(-2,2,-2,2,3,4,style["metal"])
        for x in (-3,2):
            for y in (-3,2): box(x,x+1,y,y+1,3,4,"window")
        joints = [socket("input",[0,-.75,.5],[0,-1,0],"shaft-0.5m"), socket("output",[0,.75,.5],[0,1,0],"shaft-0.5m")]
    elif part == "DriveShaft":
        box(-1,1,-6,6,-1,1,style["metal"])
        for y in (-6,5): box(-2,2,y,y+1,-2,2,style["accent"])
        axis = [0,1,0]
        joints = [socket("input",[0,-1.5,0],[0,-1,0],"shaft-0.5m"), socket("output",[0,1.5,0],[0,1,0],"shaft-0.5m")]
    else:
        raise ValueError("unknown part")
    voxels = [(x,y,z,cells[x,y,z]) for x,y,z in sorted(cells)]
    if part in ("WagonWheel", "TurbineRotor"):
        # A rotating part must not contain floating blade/spoke fragments.
        pending = set(cells)
        todo = [min(pending)]
        pending.remove(todo[0])
        while todo:
            x,y,z = todo.pop()
            for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                neighbour = x+dx,y+dy,z+dz
                if neighbour in pending:
                    pending.remove(neighbour)
                    todo.append(neighbour)
        if pending:
            raise ValueError("rotating module contains disconnected voxel pieces")
    config = {"part": part, "preset": variant, "seed": seed, "version": 1, "voxel_metres": GRID,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes() + Path(ISLANDS.__file__).read_bytes() + Path(ISLANDS.BASE.__file__).read_bytes()).hexdigest()}
    name = "CodexModule_%s_%s_%s" % (variant, part, seed)
    info = {"schema": "daedalus.codex-module.v1", "name": name, "config": config,
            "config_sha256": hashlib.sha256(ISLANDS._json(config).encode()).hexdigest(),
            "voxel_sha256": hashlib.sha256(ISLANDS._json(voxels).encode()).hexdigest(),
            "palette_rgb": {key: list(ISLANDS.PALETTE[key]) for key in sorted(set(cells.values()))},
            "pivot_metres": [0,0,0], "rotation_axis": axis, "connection_points": joints,
            "snap_grid_metres": GRID, "stage": "planned", "saved_unreal": False,
            "provenance": {"author": "team-codex", "design_request_hub": 30513,
                           "complements": "Sol harbor kit da716327; no duplicate Dock/Beacon/Boathouse geometry"},
            "collision": "native automatic import behavior unverified; no authored dynamic physics",
            "proposed_loop": "salvage parts -> restore bridges/lighthouse power -> assemble vehicle -> reach next island",
            "implemented_gameplay": False, "runtime_snapping_implemented": False}
    return voxels, info


def build(folder, part, variant, seed):
    started = time.perf_counter()
    cells, info = plan(part, variant, seed)
    info["elapsed_s"] = {"generation": round(time.perf_counter()-started,6)}
    # Keep directory IDs short: Blender's bundled Windows Python rejected a
    # repeated long module name in a >260-character receipt path during export.
    folder = Path(folder).resolve() / ("m%05d" % seed)
    receipt = folder / (info["name"] + ".receipt.json")
    if sys.platform == "win32" and len(str(receipt)) >= 260:
        raise ValueError("export receipt path exceeds Windows limit; choose a shorter --out folder")
    cached = ISLANDS._cached(receipt, info["config"])
    if cached:
        return dict(cached, export_skipped=True)
    bpy = ISLANDS.BASE.bpy
    if bpy is None or bpy.context.mode != "OBJECT":
        raise RuntimeError("export requires Blender Object mode during an owned turn")
    name = info["name"] + "_part"
    if name in bpy.data.objects:
        raise RuntimeError("module already exists in this scene")
    folder.mkdir(parents=True, exist_ok=True)
    selected, active = list(bpy.context.selected_objects), bpy.context.view_layer.objects.active
    obj = None
    try:
        started = time.perf_counter()
        obj = ISLANDS.BASE._mesh_from_voxels(name,cells,scale=GRID)
        ISLANDS._palette_slots(bpy,obj,cells)
        obj["daedalus_owner"] = "codex-contest"
        info["elapsed_s"]["mesh"] = round(time.perf_counter()-started,6)
        glb, fbx = folder/(info["name"]+".glb"), folder/(info["name"]+".fbx")
        started = time.perf_counter()
        scope = {"PARAMS": json.dumps({"path":str(glb),"objects":[obj.name]})}
        exec(ISLANDS.sides.BLENDER_EXPORT,scope)
        pipeline = ISLANDS.ship.prebuilt(info["name"],str(glb),scope["result"])
        info.update(blender=pipeline["blender"],file=pipeline["file"])
        info["elapsed_s"]["glb_export"] = round(time.perf_counter()-started,6)
        started = time.perf_counter()
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={"MESH"},
                                 apply_scale_options="FBX_SCALE_ALL",axis_forward="-Y",axis_up="Z",bake_anim=False)
        info["elapsed_s"]["fbx_export"] = round(time.perf_counter()-started,6)
        info["artifacts"] = {kind:{"path":str(path),"fingerprint":ISLANDS.ship.fingerprint(path)}
                             for kind,path in (("glb",glb),("fbx",fbx))}
        info.update(stage="exported",export_skipped=False)
        ISLANDS._write(receipt,info)
        return info
    finally:
        if obj is not None:
            mesh = obj.data
            bpy.data.objects.remove(obj,do_unlink=True)
            if mesh.users == 0: bpy.data.meshes.remove(mesh)
        for item in bpy.context.view_layer.objects: item.select_set(False)
        for item in selected:
            if item.name in bpy.context.view_layer.objects: item.select_set(True)
        if active and active.name in bpy.context.view_layer.objects: bpy.context.view_layer.objects.active=active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=ISLANDS.ROOT/"engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/SkyHarborModules")
    parser.add_argument("--plan-only",action="store_true")
    parser.add_argument("--variant",choices=list(VARIANTS)+["all"],default="all")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    results = []
    for variant_index,variant in enumerate(VARIANTS):
        if args.variant not in ("all",variant): continue
        for part_index,part in enumerate(PARTS):
            seed = 85000+variant_index*100+part_index
            if args.plan_only:
                cells,info = plan(part,variant,seed)
                ISLANDS._write(args.out/(info["name"]+".plan.json"),info)
            else:
                info = build(args.out,part,variant,seed)
            results.append(info)
    ISLANDS._write(args.out/"skyharbor-modules.batch.json",results)
    print(json.dumps({"stage":"planned" if args.plan_only else "exported","modules":len(results),
                      "names":[r["name"] for r in results]},indent=2))


if __name__ == "__main__": main()
