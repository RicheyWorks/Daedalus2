# SPDX-License-Identifier: MIT
"""Reproduce workshop terrain patches from the original exported island batch.

Ordinary Python only: no Blender/Unreal connection, mesh export, or native call.
Variants, origins and selected patches below retain the coordinator's staging
recipe. They are recorded metadata, not authority to claim new world space.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FOLDER = ROOT / "engines/unreal/DaedalusLink/Content/IslandSource/CodexContest"
STAGING = (
    {"preset": "cliff-garden", "variant": "CopperPatina", "origin_cm": [-369150, 348900, 18215.324],
     "patch": {"x": 10, "y": 20, "floor_z": 1}},
    {"preset": "river-canyon", "variant": "DawnCrimson", "origin_cm": [-369150, 323300, 18715.324],
     "patch": {"x": 0, "y": 15, "floor_z": 13}},
    {"preset": "summit-rim", "variant": "StormAmethyst", "origin_cm": [-369150, 297700, 17515.324],
     "patch": {"x": 30, "y": -5, "floor_z": 1}},
)


def _islands():
    source = ROOT / "tools/blender/codex_contest_island.py"
    spec = importlib.util.spec_from_file_location("_codex_workshop_islands", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _clear_patch(voxels):
    top = {}
    for x, y, z, _ in voxels["island"]:
        top[x, y] = max(top.get((x, y), z), z)
    wet = {(x, y) for x, y, _, _ in voxels["water"]}
    obstacles = {(x, y) for layer in ("trees", "cottage", "rocks", "flowers", "landmarks")
                 for x, y, _, _ in voxels[layer]}
    candidates = [(x, y) for x in range(-30, 31, 5) for y in range(-30, 31, 5)]
    for x, y in sorted(candidates, key=lambda point: abs(point[0] - 18) + abs(point[1] - 8)):
        patch = {(xx, yy) for xx in range(x - 3, x + 5) for yy in range(y - 6, y + 6)}
        if not patch.issubset(top) or patch & wet or patch & obstacles:
            continue
        if len({top[point] for point in patch}) == 1:
            return {"x": x, "y": y, "floor_z": top[x, y] + 1}
    raise ValueError("no clear flat 8-by-12-metre workshop patch in source terrain")


def plan_workshops(folder=DEFAULT_FOLDER):
    """Return the existing list-shaped source plan using original voxel hashes.

    The batch is the exported original revision, rather than HeroR2/HeroR3.
    Bounds/patches remain in Blender metres; staging origins are Unreal cm.
    Native orientation fitting and world placement are separate operations.
    """
    folder = Path(folder).resolve()
    batch = json.loads((folder / "codex-islands.batch.json").read_text(encoding="utf-8"))
    if not isinstance(batch, list):
        raise ValueError("island batch must be a list of original export receipts")
    islands, result = _islands(), []
    for staging in STAGING:
        found = [row for row in batch if row.get("config", {}).get("preset") == staging["preset"]]
        if len(found) != 1 or found[0].get("stage") != "exported" or found[0]["config"].get("revision"):
            raise ValueError("require exactly one original exported receipt for " + staging["preset"])
        info = found[0]
        _, voxels = islands.plan(info["config"]["preset"], info["config"]["seed"])
        voxel_sha = hashlib.sha256(islands._json(voxels).encode()).hexdigest()
        if voxel_sha != info["voxel_sha256"]:
            raise ValueError("terrain planning source differs from original exported geometry: " + info["name"])
        selected = _clear_patch(voxels)
        if selected != staging["patch"]:
            raise ValueError("selected patch differs from retained coordinator staging recipe: " + info["name"])
        bounds = {layer: {"min": [min(cell[axis] for cell in cells) for axis in range(3)],
                          "max": [max(cell[axis] + 1 for cell in cells) for axis in range(3)]}
                  for layer, cells in voxels.items() if cells}
        result.append({"island": info["name"], "variant": staging["variant"],
                       "island_origin_cm": list(staging["origin_cm"]), "source_patch_metres": selected,
                       "source_voxel_sha256": voxel_sha, "source_bounds": bounds})
    return result


def prepare(folder=DEFAULT_FOLDER, output=None):
    """Write a source plan, preserving any differing retained plan revision."""
    result = plan_workshops(folder)
    output = Path(output) if output is not None else Path(folder) / "codex-workshop-source-plan.json"
    if output.exists():
        if json.loads(output.read_text(encoding="utf-8")) != result:
            raise ValueError("existing source plan differs; retain it and choose a new --out path")
        return result
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", type=Path, default=DEFAULT_FOLDER,
                        help="original CodexContest export folder containing codex-islands.batch.json")
    parser.add_argument("--out", type=Path, help="retained output JSON; defaults to folder/codex-workshop-source-plan.json")
    args = parser.parse_args()
    result = prepare(args.folder, args.out)
    print(json.dumps([{key: value for key, value in row.items() if key != "source_bounds"}
                      for row in result], indent=2))


if __name__ == "__main__":
    main()
