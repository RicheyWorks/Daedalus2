# SPDX-License-Identifier: MIT
"""Deliver Codex biome exports with the existing Epic MCP client and native tools.

Run only during the team's accepted Unreal turn. --placements supplies owner-agreed
free locations in centimetres; the script never clears cells or removes actors.
An import-only run saves meshes but is not reported as a placed/saved island.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "connectors" / "claude-asset-pipeline"))
from unreal_mcp.client import Mcp
from asset_pipeline.ship import fingerprint, import_snapshot

SCENE = "editor_toolset.toolsets.scene.SceneTools"
ACTOR = "editor_toolset.toolsets.actor.ActorTools"
MESH = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
ASSET = "editor_toolset.toolsets.asset.AssetTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
MAT = "editor_toolset.toolsets.material.MaterialTools"
INSTANCE = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
DEST = "/Game/Daedalus/Art/Islands/CodexContest"
PALETTE = DEST + "/Palette"
LAYERS = ("island", "water", "trees", "cottage", "flowers", "rocks", "crystals", "clouds", "landmarks")


def reference(path):
    if isinstance(path, dict):
        return path
    return {"refPath": path if "." in path else path + "." + path.rsplit("/", 1)[1]}


def package(path):
    if isinstance(path, dict):
        path = path["refPath"]
    return str(path).split(":", 1)[0].split(".", 1)[0]


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _layer(path):
    name = package(path).rsplit("/", 1)[-1]
    for layer in LAYERS:
        if name.endswith("_" + layer):
            return layer
    raise ValueError("unexpected imported mesh; no placement: " + name)


def _tags(receipt, artifact):
    return {"codex_owner": "codex-contest", "codex_sha256": artifact["sha256"],
            "codex_bytes": str(artifact["bytes"]), "codex_config": receipt["config_sha256"],
            "codex_seed": str(receipt["config"]["seed"]), "codex_preset": receipt["config"]["preset"]}


def _verified_metadata(mcp, paths, expected):
    for path in paths:
        actual = mcp.call(ASSET, "get_metadata_tags", asset_path=package(path))
        if not isinstance(actual, dict) or any(actual.get(k) != v for k, v in expected.items()):
            return False
    return bool(paths)


def _bounds_dimensions(bounds):
    # Native FBox serializes min/max vectors, rather than actor-scale dimensions.
    low, high = bounds["min"], bounds["max"]
    if bounds.get("isValid") is not True or any(not math.isfinite(v[axis]) for v in (low, high) for axis in ("x", "y", "z")):
        raise ValueError("native bounds are not valid finite coordinates")
    if any(high[axis] < low[axis] for axis in ("x", "y", "z")):
        raise ValueError("native bounds are reversed")
    return sorted([high[axis] - low[axis] for axis in ("x", "y", "z")], reverse=True)


def _check_geometry(mcp, receipt, paths):
    expected = {row["name"].rsplit("_", 1)[-1]: row for row in receipt["blender"]["objects"]}
    by_layer = {_layer(path): package(path) for path in paths}
    if len(by_layer) != len(paths) or set(by_layer) != set(expected):
        raise ValueError("native imported layers differ from the selected Blender export")
    for layer, path in by_layer.items():
        actual = _bounds_dimensions(mcp.call(MESH, "get_bounds", mesh=reference(path)))
        want = sorted([100.0 * value for value in expected[layer]["dims"]], reverse=True)
        if any(abs(a - b) > max(1.0, .01 * b) for a, b in zip(actual, want)):
            raise ValueError("native dimensions differ for %s: %s cm, expected %s" % (layer, actual, want))
    return by_layer


def _transform(location):
    if len(location) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in location):
        raise ValueError("placement must be three centimetre coordinates")
    if not all(math.isfinite(v) for v in location):
        raise ValueError("placement coordinates must be finite")
    return {"location": dict(zip(("x", "y", "z"), location)),
            "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}


def _same_transform(actual, expected):
    return all(abs(actual[group][key] - value) < .01
               for group, values in expected.items() for key, value in values.items())


def _properties(mcp, instance, names):
    value = mcp.call(OBJ, "get_properties", instance=instance, properties=names)
    return json.loads(value) if isinstance(value, str) else value


def _palette(mcp, receipts):
    """Reuse one parameterized base and hash-named palette instances across islands."""
    colours = {}
    for receipt in receipts:
        for key, rgb in receipt["palette_rgb"].items():
            if key in colours and colours[key] != rgb:
                raise ValueError("palette key has conflicting colours in this batch")
            colours[key] = rgb
    existing = mcp.call(ASSET, "find_assets", folder_path=PALETTE, name="", recursive=True)
    if not isinstance(existing, list):
        raise RuntimeError("palette enumeration did not return a list")
    existing = {package(path) for path in existing}
    base_path = PALETTE + "/M_CodexPalette_v1"
    save_paths = []
    if base_path in existing:
        base = mcp.call(ASSET, "load_asset", asset_path=base_path)
        parameters = mcp.call(MAT, "list_parameters", material=base)
        if not any(p.get("name") == "Tint" and p.get("type") == "Vector" for p in parameters):
            raise RuntimeError("existing palette base does not expose Tint; refusing modification")
    else:
        base = mcp.call(MAT, "create_material", folder_path=PALETTE, asset_name="M_CodexPalette_v1")
        if mcp.call(OBJ, "set_properties", instance=base, values=json.dumps({
                "usedWithNanite": True, "usedWithInstancedStaticMeshes": True})) is not True:
            raise RuntimeError("owned palette material usage flags did not confirm success")
        for parameter, expression_class, default, output in (
            ("Tint", "VectorParameter", {"r": 1, "g": 1, "b": 1, "a": 1}, "MP_BaseColor"),
            ("Roughness", "ScalarParameter", .9, "MP_Roughness"),
        ):
            expression = mcp.call(MAT, "add_expression", material_or_function=base,
                                  expression_class={"refPath": "/Script/Engine.MaterialExpression" + expression_class}, x=-300, y=0)
            if mcp.call(OBJ, "set_properties", instance=expression,
                        values=json.dumps({"parameterName": parameter, "defaultValue": default})) is not True:
                raise RuntimeError("palette expression properties did not confirm success")
            outputs = mcp.call(MAT, "get_expression_output_names", expression=expression)
            mcp.call(MAT, "connect_to_output", expression=expression, output_name=outputs[0], material_property=output)
        mcp.call(MAT, "recompile", material_or_function=base)
        save_paths.append(base_path)
    flags = _properties(mcp, base, ["usedWithNanite", "usedWithInstancedStaticMeshes"])
    if flags.get("usedWithNanite") is not True or flags.get("usedWithInstancedStaticMeshes") is not True:
        raise RuntimeError("palette base usage flag readback differs")
    materials = {}
    for key, rgb in sorted(colours.items()):
        tint = dict(zip(("r", "g", "b", "a"), list(rgb) + [1]))
        suffix = hashlib.sha256(json.dumps(tint, sort_keys=True).encode()).hexdigest()[:12]
        path = PALETTE + "/MI_Codex_%s_%s" % (key, suffix)
        if path in existing:
            material = mcp.call(ASSET, "load_asset", asset_path=path)
            parent = _properties(mcp, material, ["parent"])["parent"]
            if package(parent) != base_path:
                raise RuntimeError("existing palette instance has a different parent")
        else:
            material = mcp.call(INSTANCE, "create", folder_path=PALETTE, asset_name=path.rsplit("/", 1)[1], parent=base)
            mcp.call(INSTANCE, "set_vector_parameter", instance=material, name="Tint", value=tint)
            save_paths.append(path)
        readback = mcp.call(INSTANCE, "get_vector_parameter", instance=material, name="Tint")
        if any(abs(readback[channel] - value) > .001 for channel, value in tint.items()):
            raise RuntimeError("palette colour readback differs")
        materials["CodexVoxel_" + key] = material
    return materials, save_paths


def deliver(receipt_paths, placements=None, map_path=None, map_file=None):
    """Hash-bound import skip, stable material binding, then one explicit batch save.

    Changed payloads use a revision folder because native import_file refuses
    existing assets. Existing actors must already match; they are never moved or
    replaced implicitly. Native calls are single attempts: uncertain outcomes stop.
    """
    receipts = [json.loads(Path(path).read_text(encoding="utf-8")) for path in receipt_paths]
    if not receipts or len({r["name"] for r in receipts}) != len(receipts):
        raise ValueError("supply distinct exported island receipts")
    for receipt in receipts:
        if receipt.get("schema") != "daedalus.codex-island.v1" or receipt.get("stage") != "exported":
            raise ValueError("delivery requires exported receipts, not plans")
        artifact = receipt["artifacts"]["fbx"]
        if fingerprint(artifact["path"]) != artifact["fingerprint"]:
            raise ValueError("FBX changed after export; no import performed")
    for path in receipt_paths:
        journal = Path(path).with_suffix(".unreal.json")
        if journal.is_file():
            previous = json.loads(journal.read_text(encoding="utf-8"))
            if previous.get("stage") not in ("placed_and_saved", "assets_saved"):
                raise RuntimeError("unfinished delivery journal requires outcome inspection before another attempt: " + str(journal))
    if placements is not None:
        if set(placements) != {r["name"] for r in receipts} or not map_path or not map_file:
            raise ValueError("placement requires one agreed location per island and explicit map package/file")
        transforms = {name: _transform(location) for name, location in placements.items()}
        if not Path(map_file).is_file():
            raise ValueError("map file must already exist; no application performed")
        before_map = fingerprint(map_file)
    else:
        transforms, before_map = {}, None

    mcp = Mcp(timeout=120)
    call_journal = Path(receipt_paths[0]).parent.parent / "codex-delivery.calls.jsonl"
    if call_journal.is_file():
        lines = call_journal.read_text(encoding="utf-8").splitlines()
        if lines and json.loads(lines[-1])["state"] in ("pending", "uncertain"):
            raise RuntimeError("previous native call requires inspection: " + str(call_journal))
    original_call = mcp.call

    def record(value):
        with call_journal.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, sort_keys=True) + "\n")

    def observed_call(toolset, tool, **arguments):
        target = {"toolset": toolset, "tool": tool, "arguments": arguments}
        record(dict(target, state="pending"))
        try:
            value = original_call(toolset, tool, **arguments)
        except Exception as error:
            record(dict(target, state="uncertain", error=str(error)))
            raise
        record(dict(target, state="responded", result=value))
        return value

    mcp.call = observed_call
    if placements is not None:
        current = mcp.call(SCENE, "get_current_level")
        if package(current) != package(map_path):
            raise RuntimeError("current level differs from the owner-agreed map; no import performed")

    materials, save_paths = _palette(mcp, receipts)
    results, new_actors = [], 0
    for receipt, receipt_path in zip(receipts, receipt_paths):
        artifact = receipt["artifacts"]["fbx"]["fingerprint"]
        name = receipt["name"]
        dest = DEST + "/" + name + "/" + artifact["sha256"][:16]
        expected = _tags(receipt, artifact)
        result = {"name": name, "preset": receipt["config"]["preset"], "seed": receipt["config"]["seed"],
                  "stage": "delivery_started", "saved_unreal": False, "placed": False,
                  "fbx": artifact, "destination": dest, "elapsed_s": {}}
        result_path = Path(receipt_path).with_suffix(".unreal.json")
        write(result_path, result)
        started = time.perf_counter()
        paths = mcp.call(ASSET, "find_assets", folder_path=dest, name="",
                         asset_type={"refPath": "/Script/Engine.StaticMesh"}, recursive=True)
        if not isinstance(paths, list):
            raise RuntimeError("native asset enumeration did not return a list")
        if paths:
            if not _verified_metadata(mcp, paths, expected):
                raise RuntimeError("revision folder has unverified assets; refusing overwrite")
            result["import_skipped"] = True
        else:
            snapshot = import_snapshot(receipt["artifacts"]["fbx"]["path"], artifact)
            result["import_snapshot"] = snapshot
            result["stage"] = "import_pending"
            write(result_path, result)
            paths = mcp.call(MESH, "import_file", folder_path=dest, asset_name=name, source_file=snapshot,
                             import_materials=False, import_textures=False, combine_meshes=False)
            if not isinstance(paths, list) or not paths:
                raise RuntimeError("native import returned no meshes; outcome requires inspection")
            result["import_skipped"] = False
        result.update(stage="import_confirmed", imported_paths=paths)
        write(result_path, result)
        result["elapsed_s"]["import_or_skip"] = round(time.perf_counter() - started, 6)
        by_layer = _check_geometry(mcp, receipt, paths)
        for path in by_layer.values():
            slots = mcp.call(MESH, "get_material_slots", mesh=reference(path))
            if not isinstance(slots, list) or not slots:
                raise RuntimeError("native mesh has no usable material slot")
            for slot in slots:
                if slot not in materials:
                    raise RuntimeError("native palette slot differs: " + str(slot))
                if mcp.call(MESH, "set_material", mesh=reference(path), slot_name=slot, material=materials[slot]) is not True:
                    raise RuntimeError("stable material binding did not confirm success")
            mcp.call(ASSET, "update_metadata_tags", asset_path=path, set_tags=expected, remove_tags=[])
            save_paths.append(path)
        if not _verified_metadata(mcp, list(by_layer.values()), expected):
            raise RuntimeError("source metadata readback differs; no saved-island claim")
        result.update(stage="assets_prepared", meshes=by_layer)
        write(result_path, result)
        if placements is not None:
            actors = {}
            for layer, path in by_layer.items():
                label = name + "_" + layer
                found = mcp.call(SCENE, "find_actors", name=label, tag="", collision_channels=[])
                if not isinstance(found, list) or len(found) > 1:
                    raise RuntimeError("ambiguous existing Codex actor; no replacement performed")
                if found:
                    actor = found[0]
                    if mcp.call(ACTOR, "get_label", actor=actor) != label:
                        raise RuntimeError("actor name search matched another label; refusing reuse")
                    component = mcp.call(ACTOR, "get_root_component", actor=actor)
                    mesh = _properties(mcp, component, ["staticMesh"])["staticMesh"]
                    if package(mesh) != path:
                        raise RuntimeError("existing actor uses another mesh revision; use a new seed/location")
                    if not _same_transform(mcp.call(ACTOR, "get_actor_transform", actor=actor), transforms[name]):
                        raise RuntimeError("existing actor transform differs; refusing implicit movement")
                else:
                    result.update(stage="spawn_pending", pending_actor={"label": label, "asset": path, "transform": transforms[name]})
                    write(result_path, result)
                    actor = mcp.call(SCENE, "add_to_scene_from_asset", asset_path=path, name=label,
                                     xform=transforms[name], snap_to_ground=False)
                    new_actors += 1
                    result["pending_actor"]["returned_actor"] = actor
                    write(result_path, result)
                    mcp.call(SCENE, "set_actor_folder", actor=actor, folder_path="Codex/ContestIslands")
                if not _same_transform(mcp.call(ACTOR, "get_actor_transform", actor=actor), transforms[name]):
                    raise RuntimeError("actor transform readback differs")
                actors[layer] = actor
            result.update(stage="placed_unsaved", placed=True, actors=actors, location_cm=placements[name])
            result.pop("pending_actor", None)
            write(result_path, result)
        results.append((result, result_path))

    if placements is not None:
        save_paths.append(package(map_path))
    started = time.perf_counter()
    for result, result_path in results:
        result.update(stage="batch_save_pending", save_packages=sorted(set(save_paths)))
        write(result_path, result)
    if mcp.call(ASSET, "save_assets", asset_paths=sorted(set(save_paths))) is not True:
        raise RuntimeError("explicit batch save did not confirm success; outputs remain unconfirmed")
    elapsed = round(time.perf_counter() - started, 6)
    after_map = fingerprint(map_file) if placements is not None else None
    if new_actors and after_map == before_map:
        raise RuntimeError("map bytes did not change after new actor creation; saved placement is unconfirmed")
    for result, result_path in results:
        if not _verified_metadata(mcp, list(result["meshes"].values()), _tags(
                next(r for r in receipts if r["name"] == result["name"]), result["fbx"])):
            raise RuntimeError("post-save metadata readback differs")
        result["elapsed_s"]["batch_save_shared"] = elapsed
        result["stage"] = "placed_and_saved" if placements is not None else "assets_saved"
        result["saved_unreal"] = True
        if placements is not None:
            result["map"] = {"package": package(map_path), "before": before_map, "after": after_map}
        write(result_path, result)
    return [result for result, _ in results]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", nargs="+", type=Path)
    parser.add_argument("--placements", type=Path, help="JSON {island_name: [x_cm,y_cm,z_cm]} agreed at handoff")
    parser.add_argument("--map", dest="map_path")
    parser.add_argument("--map-file", type=Path)
    args = parser.parse_args()
    locations = json.loads(args.placements.read_text(encoding="utf-8")) if args.placements else None
    print(json.dumps(deliver(args.receipts, locations, args.map_path, args.map_file), indent=2))


if __name__ == "__main__":
    main()
