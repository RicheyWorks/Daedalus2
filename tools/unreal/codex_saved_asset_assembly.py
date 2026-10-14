# SPDX-License-Identifier: MIT
"""Add already-saved Codex island layers during an owner-agreed Unreal turn.

No imports, mesh/material edits, actor moves/deletions, or implicit level saves.
Locations are centimetres; every layer retains the export's common origin at
rotation zero and scale one. Root/operator supplies the placements and map.
An unfinished journal requires inspection, never an automatic mutation retry.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from codex_contest_island_delivery import (
    ACTOR, ASSET, DEST, SCENE, Mcp, _properties, _same_transform, _transform,
    fingerprint, package, reference,
)


def _read(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _object_path(value):
    value = value.get("refPath") if isinstance(value, dict) else value
    if not isinstance(value, str) or not value.startswith("/Game/") or ":" in value:
        raise ValueError("expected a native /Game asset reference")
    return reference(value)["refPath"]


def plan_saved(manifest_path, saved_path, placements, map_path, map_file):
    """Read-only local plan; validate all saved paths, then select island groups.

    placements is {exact_manifest_island_name: [x_cm, y_cm, z_cm]}; a nonempty
    subset is supported. Modules are validated but never placed by this helper.
    """
    manifest, manifest_fp = _read(manifest_path)
    saved, saved_fp = _read(saved_path)
    if manifest.get("schema") != "daedalus.codex-prepared-delivery.v1":
        raise ValueError("unrecognized prepared-delivery manifest")
    if saved.get("stage") != "assets_saved" or saved.get("manifest_sha256") != manifest_fp["sha256"]:
        raise ValueError("saved receipt is incomplete or belongs to different manifest bytes")
    assets, results = manifest.get("assets", []), saved.get("results", [])
    if not assets or len(assets) != manifest.get("prepared_groups") or len(results) != len(assets):
        raise ValueError("prepared/saved group counts differ")
    by_name = {row["name"]: row for row in results}
    if len(by_name) != len(results) or len({a["name"] for a in assets}) != len(assets):
        raise ValueError("duplicate group names")
    verified, all_paths = {}, set()
    for asset in assets:
        name = asset["name"]
        result = by_name.get(name)
        destination = asset["destination"]
        if not destination.startswith(DEST + "/Prepared/") or package(destination) != destination:
            raise ValueError("manifest destination leaves the owned prepared namespace")
        if not result or result.get("kind") != asset["kind"] or result.get("destination") != destination:
            raise ValueError("saved group does not match manifest: " + name)
        if result.get("stage") != "assets_saved_held_from_world":
            raise ValueError("group does not have a confirmed asset-save receipt: " + name)
        expected = {row["name"] for row in asset["objects"]}
        if len(expected) != len(asset["objects"]):
            raise ValueError("duplicate source objects: " + name)
        meshes = result.get("meshes", [])
        if len(meshes) != len(expected) or {row.get("source_name") for row in meshes} != expected:
            raise ValueError("saved source_name mapping differs: " + name)
        entries = []
        for row in meshes:
            path = _object_path(row["path"])
            if row.get("save_return") is not True or not package(path).startswith(destination + "/"):
                raise ValueError("unconfirmed or foreign saved mesh: " + path)
            if path in all_paths:
                raise ValueError("one saved mesh is assigned to multiple source objects")
            all_paths.add(path)
            # Use the actual receipt mapping. Single-mesh FBX imports may have
            # an asset alias different from source_name; suffix guessing loses it.
            entries.append({"label": row["source_name"], "mesh_path": path})
        verified[name] = {"kind": asset["kind"], "entries": sorted(entries, key=lambda e: e["label"])}
    if set(by_name) != set(verified) or len(all_paths) != manifest.get("expected_meshes"):
        raise ValueError("saved receipt has extra groups or a differing mesh count")
    if saved.get("saved_groups") != len(assets) or saved.get("saved_meshes") != len(all_paths):
        raise ValueError("receipt summary does not match its saved objects")
    if not isinstance(placements, dict) or not placements:
        raise ValueError("supply a nonempty dictionary of owner-agreed island placements")
    map_package = package(map_path)
    if not isinstance(map_path, str) or not map_package.startswith("/Game/") or ":" in map_path:
        raise ValueError("supply the explicit owner-agreed /Game map package")
    map_file = Path(map_file).resolve()
    if not map_file.is_file() or map_file.suffix.lower() != ".umap" or map_file.stem != map_package.rsplit("/", 1)[-1]:
        raise ValueError("explicit existing .umap file must match the agreed map name")
    entries = []
    for name, location in sorted(placements.items()):
        group = verified.get(name)
        if not group or group["kind"] != "island":
            raise ValueError("placements may select only exact saved island group names: " + str(name))
        transform = _transform(location)
        for row in group["entries"]:
            entries.append(dict(row, group=name, transform=transform))
    if len({row["label"] for row in entries}) != len(entries):
        raise ValueError("placement plan contains duplicate actor labels")
    return {"schema": "daedalus.codex-saved-assembly.v1", "manifest": str(Path(manifest_path).resolve()),
            "manifest_fingerprint": manifest_fp, "saved_receipt": str(Path(saved_path).resolve()),
            "saved_receipt_fingerprint": saved_fp, "validated_saved_meshes": len(all_paths),
            "map_package": map_package, "map_file": str(map_file), "placements_cm": placements,
            "entries": entries}


def _write(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def assemble_saved(manifest_path, saved_path, placements, map_path, map_file, journal_path, timeout=120):
    """Execute an additive plan, verifying exact actors and saving only its map.

    Call only after the root operator has the actual editor handoff. A failed or
    pending journal deliberately blocks another run; inspect native outcomes
    before selecting a new journal. No actor is removed or moved to resolve it.
    """
    plan = plan_saved(manifest_path, saved_path, placements, map_path, map_file)
    journal_path = Path(journal_path).resolve()
    if journal_path in (Path(plan["manifest"]), Path(plan["saved_receipt"]), Path(plan["map_file"])):
        raise ValueError("assembly journal must not overwrite an input")
    previous = None
    if journal_path.exists():
        previous, _ = _read(journal_path)
        if previous.get("stage") != "placed_and_saved" or previous.get("plan") != plan:
            raise RuntimeError("unfinished or different assembly journal requires inspection: " + str(journal_path))
    if not journal_path.parent.is_dir():
        raise ValueError("journal parent directory must already exist")
    before_map = fingerprint(plan["map_file"])
    report = {"plan": plan, "stage": "preflight", "map_before": before_map,
              "created_actors": 0, "reused_actors": 0, "actors": [], "native_mutations": [],
              "save_return": None, "saved_unreal": False, "staging_only": True,
              "ownership_tags_added": False, "folder": "CodexContest/Staging"}
    if previous:
        report["previous_completed_run"] = {key: previous.get(key) for key in
                                             ("map_before", "map_after", "created_actors", "reused_actors", "save_return")}
    _write(journal_path, report)
    mcp = Mcp(timeout=timeout)

    def require_map():
        current = mcp.call(SCENE, "get_current_level")
        if package(current) != plan["map_package"]:
            raise RuntimeError("current map differs from the explicitly agreed map; no further mutation")

    def verified_actor(actor, entry):
        if package(actor) != plan["map_package"]:
            raise RuntimeError("actor resides in another level package; inspect before map save")
        if mcp.call(ACTOR, "get_label", actor=actor) != entry["label"]:
            raise RuntimeError("actor search matched a different label: " + entry["label"])
        component = mcp.call(ACTOR, "get_root_component", actor=actor)
        actual_mesh = _properties(mcp, component, ["staticMesh"])["staticMesh"]
        if _object_path(actual_mesh) != entry["mesh_path"]:
            raise RuntimeError("existing actor has a different exact mesh path: " + entry["label"])
        if not _same_transform(mcp.call(ACTOR, "get_actor_transform", actor=actor), entry["transform"]):
            raise RuntimeError("actor transform differs; no movement permitted: " + entry["label"])

    def mutation(toolset, tool, **arguments):
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
        require_map()
        # Check the entire requested set before the first spawn. A broad name
        # search returning another actor is also a conflict, never authority to
        # rename, replace, delete, or move it.
        existing = {}
        for entry in plan["entries"]:
            loaded = mcp.call(ASSET, "load_asset", asset_path=package(entry["mesh_path"]))
            if not loaded or _object_path(loaded) != entry["mesh_path"]:
                raise RuntimeError("saved mesh could not be loaded by its exact receipt path")
            found = mcp.call(SCENE, "find_actors", name=entry["label"], tag="", collision_channels=[])
            if not isinstance(found, list) or len(found) > 1:
                raise RuntimeError("ambiguous actor search: " + entry["label"])
            if found:
                verified_actor(found[0], entry)
                existing[entry["label"]] = found[0]
        if fingerprint(plan["map_file"]) != before_map:
            raise RuntimeError("map file changed during preflight; re-coordinate ownership")
        started = time.perf_counter()
        for entry in plan["entries"]:
            require_map()
            actor = existing.get(entry["label"])
            if actor is None:
                actor = mutation(SCENE, "add_to_scene_from_asset", asset_path=package(entry["mesh_path"]),
                                 name=entry["label"], xform=entry["transform"], snap_to_ground=False)
                if not actor:
                    raise RuntimeError("spawn returned no actor; inspect its outcome before another run")
                report["created_actors"] += 1
            else:
                report["reused_actors"] += 1
            verified_actor(actor, entry)
            mutation(SCENE, "set_actor_folder", actor=actor, folder_path=report["folder"])
            report["actors"].append(dict(entry, actor=actor))
            report["stage"] = "placed_unsaved"
            _write(journal_path, report)
        report["assembly_s"] = round(time.perf_counter() - started, 6)
        require_map()
        # This is the sole save operation. Meshes and materials were saved by
        # the import receipt and are never included in this map-only request.
        started = time.perf_counter()
        save_return = mutation(ASSET, "save_assets", asset_paths=[plan["map_package"]])
        report["save_return"] = save_return
        report["map_save_s"] = round(time.perf_counter() - started, 6)
        if save_return is not True:
            raise RuntimeError("map save did not return true; placement is unconfirmed")
        after_map = fingerprint(plan["map_file"])
        report["map_after"] = after_map
        if report["created_actors"] and after_map == before_map:
            raise RuntimeError("map bytes did not change after new actor creation; saved placement is unconfirmed")
        require_map()
        for row in report["actors"]:
            verified_actor(row["actor"], row)
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
    parser.add_argument("manifest", type=Path)
    parser.add_argument("saved_receipt", type=Path)
    parser.add_argument("--placements", type=Path, required=True, help="owner-agreed JSON {island_name: [x_cm,y_cm,z_cm]}")
    parser.add_argument("--map", dest="map_path", required=True)
    parser.add_argument("--map-file", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    placements = json.loads(args.placements.read_text(encoding="utf-8"))
    print(json.dumps(assemble_saved(args.manifest, args.saved_receipt, placements,
                                    args.map_path, args.map_file, args.journal), indent=2))


if __name__ == "__main__":
    main()
