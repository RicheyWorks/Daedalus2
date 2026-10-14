# SPDX-License-Identifier: MIT
"""Dress three staging islands with the 21 already-saved Codex module meshes.

The root operator supplies a terrain/orientation-fitted plan and owns execution.
This helper makes additive staging actors only; it neither imports assets nor
adds ownership/admission tags. Pending native outcomes require inspection.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

from codex_contest_island_delivery import (
    ACTOR, ASSET, DEST, SCENE, Mcp, _properties, _same_transform, fingerprint, package,
)
from codex_saved_asset_assembly import _object_path, _read, _write

FOLDER = "CodexContest/Staging/Workshops"


def _transform(value):
    fields = {"location": ("x", "y", "z"), "rotation": ("pitch", "yaw", "roll"), "scale": ("x", "y", "z")}
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError("transform requires location, Euler rotation in degrees, and positive scale")
    result = {}
    for group, axes in fields.items():
        vector = value[group]
        if not isinstance(vector, dict) or set(vector) != set(axes):
            raise ValueError("transform has differing vector fields: " + group)
        if any(isinstance(vector[axis], bool) or not isinstance(vector[axis], (int, float))
               or not math.isfinite(vector[axis]) for axis in axes):
            raise ValueError("transform coordinates/angles/scales must be finite numbers")
        if group == "scale" and any(vector[axis] <= 0 for axis in axes):
            raise ValueError("every scale component must be positive")
        result[group] = {axis: vector[axis] for axis in axes}
    return result


def plan_dressing(saved_receipt_path, dressing_plan_path, map_path, map_file):
    """Validate local receipt and explicit {entries:[...]} plan without app calls.

    Every entry has label, mesh_path, transform, role, island. All 21 saved module
    paths and all three exact island names must occur. BridgeCoupler duplicates
    may provide legs/supports; other module paths occur once.
    """
    saved, saved_fp = _read(saved_receipt_path)
    supplied, plan_fp = _read(dressing_plan_path)
    if saved.get("stage") != "assets_saved" or saved.get("saved_groups") != 24 or saved.get("saved_meshes") != 47:
        raise ValueError("require the confirmed 24-group/47-mesh prepared asset receipt")
    modules, islands = {}, set()
    for group in saved.get("results", []):
        if group.get("kind") == "island":
            islands.add(group["name"])
        elif group.get("kind") == "module":
            meshes = group.get("meshes", [])
            if group.get("stage") != "assets_saved_held_from_world" or len(meshes) != 1:
                raise ValueError("module requires one confirmed saved mesh: " + group["name"])
            mesh = meshes[0]
            path = _object_path(mesh["path"])
            if mesh.get("save_return") is not True or not package(path).startswith(DEST + "/Prepared/module/"):
                raise ValueError("module path is unsaved or outside the owned prepared module namespace")
            if path in modules:
                raise ValueError("duplicate saved module mesh path")
            modules[path] = {"name": group["name"], "source_name": mesh["source_name"]}
    if len(modules) != 21 or len(islands) != 3:
        raise ValueError("receipt does not identify all 21 modules and three islands")
    raw_entries = supplied.get("entries") if isinstance(supplied, dict) else None
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("dressing plan must contain a nonempty entries list")
    entries, labels = [], set()
    for row in raw_entries:
        if not isinstance(row, dict) or set(row) != {"label", "mesh_path", "transform", "role", "island"}:
            raise ValueError("each dressing entry requires exactly label, mesh_path, transform, role, island")
        label, role = row["label"], row["role"]
        if not isinstance(label, str) or not label.startswith("CodexDress_") or len(label) <= len("CodexDress_"):
            raise ValueError("all actor labels require the exact own prefix CodexDress_")
        if any(character in label for character in "\r\n\x00") or label in labels:
            raise ValueError("actor label is duplicated or contains control characters")
        if not isinstance(role, str) or not role.strip() or row["island"] not in islands:
            raise ValueError("each entry requires a role and an exact saved island name")
        path = _object_path(row["mesh_path"])
        if path not in modules:
            raise ValueError("dressing mesh is not one of the 21 actual saved module paths: " + path)
        labels.add(label)
        entries.append(dict(row, mesh_path=path, transform=_transform(row["transform"])))
    counts = Counter(row["mesh_path"] for row in entries)
    if set(counts) != set(modules) or {row["island"] for row in entries} != islands:
        raise ValueError("plan must represent all 21 unique module paths across all three islands")
    if any(count > 1 and "_BridgeCoupler_" not in modules[path]["name"] for path, count in counts.items()):
        raise ValueError("only BridgeCoupler meshes may have extra support copies")
    if not isinstance(map_path, str) or not map_path.startswith("/Game/") or ":" in map_path:
        raise ValueError("supply the explicit confirmed /Game map package")
    map_package, map_file = package(map_path), Path(map_file).resolve()
    if not map_file.is_file() or map_file.suffix.lower() != ".umap" or map_file.stem != map_package.rsplit("/", 1)[-1]:
        raise ValueError("existing map file must match the explicit map package name")
    return {"schema": "daedalus.codex-module-dressing.v1", "saved_receipt": str(Path(saved_receipt_path).resolve()),
            "saved_receipt_fingerprint": saved_fp, "dressing_plan": str(Path(dressing_plan_path).resolve()),
            "dressing_plan_fingerprint": plan_fp, "map_package": map_package, "map_file": str(map_file),
            "module_paths": modules, "islands": sorted(islands), "entries": entries, "folder": FOLDER}


def dress_saved_modules(saved_receipt_path, dressing_plan_path, map_path, map_file, journal_path, timeout=120):
    """Add/reuse exact staging actors and save only the explicit map once.

    This does not repair/bypass importer admission, tag actors as admitted, or
    establish terrain fit. The root operator supplies and reviews that fit.
    """
    plan = plan_dressing(saved_receipt_path, dressing_plan_path, map_path, map_file)
    journal_path = Path(journal_path).resolve()
    if journal_path in {Path(plan[key]) for key in ("saved_receipt", "dressing_plan", "map_file")}:
        raise ValueError("journal must not overwrite an input")
    if not journal_path.parent.is_dir():
        raise ValueError("journal parent must already exist")
    previous = None
    if journal_path.exists():
        previous, _ = _read(journal_path)
        if previous.get("stage") != "placed_and_saved" or previous.get("plan") != plan:
            raise RuntimeError("unresolved or differing dressing journal requires outcome inspection")
    report = {"plan": plan, "stage": "preflight", "map_before": fingerprint(plan["map_file"]),
              "created_actors": 0, "reused_actors": 0, "actors": [], "native_mutations": [],
              "save_return": None, "saved_unreal": False, "staging_only": True,
              "ownership_tags_added": False, "admitted": False}
    if previous:
        report["previous_completed_run"] = {key: previous.get(key) for key in ("map_after", "save_return")}
    _write(journal_path, report)

    def require_map():
        if package(mcp.call(SCENE, "get_current_level")) != plan["map_package"]:
            raise RuntimeError("current map differs from the confirmed map; no further mutation")

    def verify(actor, entry):
        if package(actor) != plan["map_package"]:
            raise RuntimeError("actor resides in a different level package")
        if mcp.call(ACTOR, "get_label", actor=actor) != entry["label"]:
            raise RuntimeError("actor search returned a different exact label")
        component = mcp.call(ACTOR, "get_root_component", actor=actor)
        mesh = _properties(mcp, component, ["staticMesh"])["staticMesh"]
        if _object_path(mesh) != entry["mesh_path"]:
            raise RuntimeError("actor has a different exact mesh path; no replacement permitted")
        if not _same_transform(mcp.call(ACTOR, "get_actor_transform", actor=actor), entry["transform"]):
            raise RuntimeError("actor transform differs; no actor movement permitted")

    def mutation(toolset, tool, **arguments):
        require_map()
        action = {"toolset": toolset, "tool": tool, "arguments": arguments, "state": "pending"}
        report["native_mutations"].append(action)
        report["stage"] = "native_mutation_pending"
        _write(journal_path, report)
        try:
            result = mcp.call(toolset, tool, **arguments)
        except Exception as error:
            action.update(state="uncertain", error=str(error))
            report["stage"] = "native_outcome_uncertain"
            _write(journal_path, report)
            raise
        action.update(state="responded", result=result)
        report["stage"] = "native_response_received"
        _write(journal_path, report)
        return result

    try:
        mcp = Mcp(timeout=timeout)
        require_map()
        # Validate every existing actor before the first native mutation.
        for path in plan["module_paths"]:
            loaded = mcp.call(ASSET, "load_asset", asset_path=package(path))
            if not loaded or _object_path(loaded) != path:
                raise RuntimeError("module could not be loaded by its exact saved receipt path")
        existing = {}
        for entry in plan["entries"]:
            found = mcp.call(SCENE, "find_actors", name=entry["label"], tag="", collision_channels=[])
            if not isinstance(found, list) or len(found) > 1:
                raise RuntimeError("ambiguous existing actor; no replacement permitted: " + entry["label"])
            if found:
                verify(found[0], entry)
                existing[entry["label"]] = found[0]
        if fingerprint(plan["map_file"]) != report["map_before"]:
            raise RuntimeError("map bytes changed during preflight; re-coordinate ownership")
        started = time.perf_counter()
        for entry in plan["entries"]:
            actor = existing.get(entry["label"])
            if actor is None:
                actor = mutation(SCENE, "add_to_scene_from_asset", asset_path=package(entry["mesh_path"]),
                                 name=entry["label"], xform=entry["transform"], snap_to_ground=False)
                if not actor:
                    raise RuntimeError("spawn returned no actor; inspect native outcome before another attempt")
                report["created_actors"] += 1
            else:
                require_map()
                report["reused_actors"] += 1
            verify(actor, entry)
            mutation(SCENE, "set_actor_folder", actor=actor, folder_path=FOLDER)
            report["actors"].append(dict(entry, actor=actor))
            report["stage"] = "placed_unsaved"
            _write(journal_path, report)
        report["dressing_s"] = round(time.perf_counter() - started, 6)
        started = time.perf_counter()
        report["save_return"] = mutation(ASSET, "save_assets", asset_paths=[plan["map_package"]])
        report["map_save_s"] = round(time.perf_counter() - started, 6)
        if report["save_return"] is not True:
            raise RuntimeError("map save did not return true; dressing remains unconfirmed")
        report["map_after"] = fingerprint(plan["map_file"])
        if report["map_after"] == report["map_before"]:
            raise RuntimeError("map bytes did not change; saved dressing is unconfirmed")
        require_map()
        for entry in report["actors"]:
            verify(entry["actor"], entry)
        report.update(stage="placed_and_saved", saved_unreal=True)
        _write(journal_path, report)
        return report
    except Exception as error:
        report["error"] = str(error)
        if report["stage"] != "native_outcome_uncertain":
            report["stage"] = "inspection_required" if report["native_mutations"] else "preflight_failed"
        _write(journal_path, report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("saved_receipt", type=Path)
    parser.add_argument("dressing_plan", type=Path)
    parser.add_argument("--map", dest="map_path", required=True)
    parser.add_argument("--map-file", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(dress_saved_modules(args.saved_receipt, args.dressing_plan, args.map_path,
                                         args.map_file, args.journal), indent=2))


if __name__ == "__main__":
    main()
