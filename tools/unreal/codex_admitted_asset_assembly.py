# SPDX-License-Identifier: MIT
"""Assemble a guarded, saved ten-layer Codex island receipt additively.

Local planning verifies admission identity and disk witnesses. Actual placement
uses the existing journaled saved-asset execution body during the root operator's
acknowledged editor turn. No imports, ownership tags, or material edits occur.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from codex_contest_island_delivery import DEST, _transform, fingerprint, package
from codex_saved_asset_assembly import _object_path, _read, execute_plan

NAMESPACE = DEST + "/Ingestion"


def _witness(value):
    if not isinstance(value, dict) or re.fullmatch("[0-9a-f]{64}", str(value.get("sha256", ""))) is None or type(value.get("bytes")) is not int or value["bytes"] <= 0:
        raise ValueError("saved/source witness requires a SHA256 and positive byte count")
    return {"sha256": value["sha256"], "bytes": value["bytes"]}


def plan_admitted(receipt_path, placement_cm, map_path, map_file):
    """Produce the existing execution-plan shape from a genuine single receipt.

    No fabricated batch summary is used. The manifest's ten source names must
    match native_result, assets, imported_object_paths and on-disk outputs.
    The explicit map file identifies the Content root for /Game disk witnesses.
    """
    receipt_path = Path(receipt_path).resolve()
    receipt, receipt_fp = _read(receipt_path)
    if receipt.get("schema") != "daedalus.ingestion-receipt.v1" or receipt.get("state") != "saved" or receipt.get("save_confirmed") is not True or receipt.get("save_call_completed") is not True:
        raise ValueError("require a guarded saved receipt with confirmed completed saves")
    manifest = receipt.get("manifest", {})
    if manifest.get("schema") != receipt["schema"]:
        raise ValueError("embedded admission manifest schema differs")
    key = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    if receipt.get("key") != key:
        raise ValueError("receipt admission key differs from its canonical manifest")
    settings = manifest.get("settings", {})
    destination = NAMESPACE + "/" + key[:24]
    if manifest.get("destination") != NAMESPACE or settings.get("namespace") != NAMESPACE or receipt.get("destination") != destination:
        raise ValueError("receipt destination is not the exact owned Ingestion/key24 revision")
    native = receipt.get("native_result", {})
    name = settings.get("name")
    if settings.get("kind") != "island" or native.get("kind") != "island" or not isinstance(name, str) or re.fullmatch("CodexIsland_[A-Za-z0-9_]+", name) is None:
        raise ValueError("only exact owned island-kind receipts can be assembled")
    if receipt.get("name") != name or native.get("name") != name or native.get("destination") != destination or native.get("stage") != "assets_saved_held_from_world":
        raise ValueError("native saved identity differs from its admission settings")
    if re.fullmatch("[0-9a-f]{64}", str(settings.get("config_sha256", ""))) is None or type(settings.get("seed")) is not int:
        raise ValueError("receipt lacks the config/seed witness")
    source = manifest.get("source", {})
    source_fp = _witness(source)
    if fingerprint(source["path"]) != source_fp:
        raise ValueError("admitted source FBX bytes changed after the saved receipt")
    objects = settings.get("objects", [])
    if not isinstance(objects, list) or len(objects) != 10:
        raise ValueError("this guarded island plan requires ten recorded source objects")
    names = [row.get("name") for row in objects]
    if len(set(names)) != 10 or any(not isinstance(value, str) or not value.startswith(name + "_") or re.fullmatch("[A-Za-z0-9_]+", value) is None for value in names):
        raise ValueError("source object names are duplicated or leave the admitted island identity")
    meshes = native.get("meshes", [])
    if not isinstance(meshes, list) or len(meshes) != 10 or {row.get("source_name") for row in meshes} != set(names):
        raise ValueError("native source-name set differs from its ten admitted objects")
    transform = _transform(placement_cm)
    if not isinstance(map_path, str) or not map_path.startswith("/Game/") or ":" in map_path:
        raise ValueError("supply the explicitly agreed /Game map package")
    map_package, map_file = package(map_path), Path(map_file).resolve()
    if not map_file.is_file() or map_file.suffix.lower() != ".umap":
        raise ValueError("supply the explicit existing map file")
    content_roots = [parent for parent in map_file.parents if parent.name.lower() == "content"
                     and (parent / (map_package[len("/Game/"):] + ".umap")).resolve() == map_file]
    if len(content_roots) != 1:
        raise ValueError("map file does not identify an unambiguous Content root for its package")
    content = content_roots[0]
    outputs = receipt.get("outputs", {})
    assets = receipt.get("assets", {})
    if not isinstance(outputs, dict) or not isinstance(assets, dict) or set(assets) != set(names):
        raise ValueError("saved output or logical asset mapping differs")
    entries, paths, disk_outputs = [], set(), {}
    for row in sorted(meshes, key=lambda value: value["source_name"]):
        source_name = row["source_name"]
        path = _object_path(row["path"])
        exact_path = destination + "/" + source_name + "." + source_name
        if path != exact_path or row.get("save_return") is not True or _object_path(assets[source_name]) != path or path in paths:
            raise ValueError("native saved path/save result differs for " + source_name)
        paths.add(path)
        witness = _witness(outputs.get(path))
        disk_path = (content / (package(path)[len("/Game/"):] + ".uasset")).resolve()
        if not disk_path.is_file() or fingerprint(disk_path) != witness:
            raise ValueError("native output file bytes differ: " + str(disk_path))
        disk_outputs[path] = dict(path=str(disk_path), **witness)
        entries.append({"label": source_name, "mesh_path": path, "group": name, "transform": transform})
    imported = native.get("imported_object_paths", [])
    if set(outputs) != paths or not isinstance(imported, list) or len(imported) != 10 or {_object_path(path) for path in imported} != paths:
        raise ValueError("native returned/output path sets differ from the admitted source mapping")
    if fingerprint(receipt_path) != receipt_fp:
        raise ValueError("admission receipt changed during local planning")
    return {"schema": "daedalus.codex-admitted-assembly.v1", "manifest": str(receipt_path),
            "manifest_embedded": True, "manifest_key": key, "manifest_fingerprint": receipt_fp,
            "saved_receipt": str(receipt_path), "saved_receipt_fingerprint": receipt_fp,
            "validated_saved_meshes": len(entries), "native_output_fingerprints": disk_outputs,
            "source_fingerprint": source_fp, "config_sha256": settings["config_sha256"], "seed": settings["seed"],
            "map_package": map_package, "map_file": str(map_file), "placements_cm": {name: placement_cm},
            "entries": entries}


def assemble_admitted(receipt_path, placement_cm, map_path, map_file, journal_path, timeout=120):
    return execute_plan(plan_admitted(receipt_path, placement_cm, map_path, map_file), journal_path, timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--placement-cm", nargs=3, type=float, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--map", dest="map_path", required=True)
    parser.add_argument("--map-file", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assemble_admitted(args.receipt, args.placement_cm, args.map_path,
                                       args.map_file, args.journal), indent=2))


if __name__ == "__main__":
    main()
