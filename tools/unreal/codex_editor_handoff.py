# SPDX-License-Identifier: MIT
"""Read the actual saved Codex editor state and write a final handoff bundle.

Root/operator runs this during its acknowledged turn. Native calls are reads:
PIE, current map/camera, actors/components, asset classes and dirty packages.
No import, actor/material change, map save, screenshot, or application setting.
--operator-no-inflight is a declaration, never a measured native queue state.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "connectors/claude-asset-pipeline"))
from asset_pipeline import wire
from codex_contest_island_delivery import DEST, SCENE, Mcp, _same_transform, fingerprint, package
from codex_saved_asset_assembly import _object_path, _read, _write

APP = "EditorToolset.EditorAppToolset"
MAP = "/Game/Daedalus/DaedalusWorld"
CONTENT = Path("C:/Unreal/DaedalusRealm/Content")
MAP_FILE = CONTENT / "Daedalus/DaedalusWorld.umap"
WORLD_FILES = ("codex-cliff-staging.world.json", "codex-remaining-staging.world.json",
               "codex-workshop.world.json", "codex-hero-r3.world.json")
PALETTE_FILES = ("codex-cliff-palette-native-v2.json", "codex-remaining-palette-native.json", "codex-hero-r3.palette.json")
ISLANDS = {"CodexIsland_cliff_garden_84022", "CodexIsland_river_canyon_84033",
           "CodexIsland_summit_rim_84011", "CodexIsland_summit_rim_84011_HeroR3"}
POWER = "CodexSalvage_PowerUnit_86100"
LATEST_MAP = {"sha256": "07ba7e6aa40583978d0b1b7d7d410b97dc23713b33e453b411ff4d5272753a1f", "bytes": 209237569}
PINS = {
    "original_manifest": {"sha256": "3770b329e26fb8d7c24b769dbeb7cb3513d3bd8b2dea1ebd768c6d41e3f0df79", "bytes": 35480},
    "importer": {"sha256": "dfac57ce929686dc1bca400da4a258405f0a1bd1cb783fa673793ba8f28de982", "bytes": 13679},
    "shared_material": {"sha256": "5da5a09f183424869300bac051e32da589328a63b28c2dbd8d61714faf3bbd58", "bytes": 9801},
}


def _file(path):
    path = Path(path).resolve()
    return {"path": str(path), **fingerprint(path), "mtime_ns": path.stat().st_mtime_ns}


def _asset_file(path):
    path = package(path)
    if not path.startswith(DEST + "/") or any(part in (".", "..") for part in path.split("/")):
        raise ValueError("asset leaves the owned namespace: " + path)
    return CONTENT / (path[len("/Game/"):] + ".uasset")


def _witness(value):
    return {key: value[key] for key in ("sha256", "bytes")}


def _local(folder):
    bundle, actors, plans = {}, [], {}

    def retain(relative):
        path = folder / relative
        value, witness = _read(path)
        bundle[relative] = {"file": {"path": str(path), **witness}, "receipt": value}
        return value

    for name in WORLD_FILES:
        world = retain(name)
        if world.get("stage") != "placed_and_saved" or world.get("save_return") is not True or world.get("saved_unreal") is not True:
            raise ValueError("world assembly lacks a confirmed save: " + name)
        if world.get("staging_only") is not True or world.get("ownership_tags_added") is not False or world["plan"]["map_package"] != MAP:
            raise ValueError("world assembly staging/map contract differs: " + name)
        actors.extend(world["actors"])
        plans[name] = world["plan"]
    labels = {row["label"] for row in actors}
    refs = {row["actor"]["refPath"] for row in actors}
    instances = {row.get("group", row.get("island")) for row in actors}
    if len(actors) != 63 or len(labels) != 63 or len(refs) != 63 or instances != ISLANDS:
        raise ValueError("require 63 distinct recorded actors across the four actual island instances")
    palettes = {name: retain(name) for name in PALETTE_FILES}
    reconciliation = retain("codex-cliff-palette-save-reconciled.json")
    cliff_file = bundle[PALETTE_FILES[0]]["file"]
    if reconciliation.get("stage") != "component_palette_saved" or reconciliation.get("save_return") is not True or reconciliation.get("prior_sha256") != cliff_file["sha256"]:
        raise ValueError("cliff palette save lacks its exact prior-receipt reconciliation")
    if Path(reconciliation["prior"]).resolve() != Path(cliff_file["path"]).resolve():
        raise ValueError("cliff reconciliation links a different source journal")
    if reconciliation["map_before"] == reconciliation["map_after"]:
        raise ValueError("cliff reconciliation has no changed saved map witness")
    expected_materials = {}
    for name, palette in palettes.items():
        if name != PALETTE_FILES[0] and (palette.get("stage") != "component_palette_saved" or palette.get("save_return") is not True):
            raise ValueError("palette lacks its confirmed save: " + name)
        for row in palette["applied"]:
            if row["label"] in expected_materials:
                raise ValueError("palette receipts assign one actor twice")
            expected_materials[row["label"]] = row["materials"]
    if set(expected_materials) != labels:
        raise ValueError("palette receipts do not cover the exact 63 actor labels")
    saved = retain("codex-prepared.unreal.json")
    retain("codex-saved.delivery.json")
    if saved.get("stage") != "assets_saved" or saved.get("saved_meshes") != 47:
        raise ValueError("prepared 47-mesh receipt is not saved")
    prepared = {row["path"]: row for group in saved["results"] for row in group["meshes"]}
    if len(prepared) != 47 or any(row.get("save_return") is not True for row in prepared.values()):
        raise ValueError("prepared native mesh set/save booleans differ")
    baseline = palettes[PALETTE_FILES[2]]["prepared_meshes_before"]
    if set(baseline) != set(prepared):
        raise ValueError("recorded prepared-mesh fingerprints differ from saved mesh paths")
    disk = {}
    for path, witness in baseline.items():
        actual = _file(_asset_file(path))
        if _witness(actual) != _witness(witness):
            raise ValueError("prepared native output bytes changed: " + path)
        disk[path] = dict(actual, origin="prepared_asset_receipt")
    admissions, power_paths = [], []
    receipt_files = sorted((folder / "NativeReceipts").glob("codex-ingestion-*.json"))
    for path in receipt_files:
        relative = path.relative_to(folder).as_posix()
        receipt = retain(relative)
        manifest = receipt["manifest"]
        key = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        destination = DEST + "/Ingestion/" + key[:24]
        if receipt.get("schema") != "daedalus.ingestion-receipt.v1" or receipt.get("state") != "saved" or receipt.get("save_confirmed") is not True or receipt.get("key") != key or receipt.get("destination") != destination:
            raise ValueError("guarded native receipt identity/save state differs: " + path.name)
        meshes = receipt["native_result"]["meshes"]
        paths = {row["path"] for row in meshes}
        if len(paths) != len(meshes) or set(receipt["outputs"]) != paths or any(row.get("save_return") is not True for row in meshes):
            raise ValueError("guarded native output/save set differs: " + path.name)
        if set(receipt["assets"].values()) != paths:
            raise ValueError("guarded native logical asset mapping differs: " + path.name)
        for asset_path, witness in receipt["outputs"].items():
            if not package(asset_path).startswith(destination + "/") or asset_path in disk:
                raise ValueError("guarded output is duplicated or leaves its exact admission destination")
            actual = _file(_asset_file(asset_path))
            if _witness(actual) != _witness(witness):
                raise ValueError("guarded native output bytes changed: " + asset_path)
            disk[asset_path] = dict(actual, origin=relative)
        admissions.append({"name": receipt["name"], "paths": sorted(paths), "receipt": relative,
                           "key": key, "state": receipt["state"], "save_confirmed": receipt["save_confirmed"]})
        if receipt["name"] == POWER:
            power_paths = sorted(paths)
    if len(receipt_files) != 3 or sorted(len(row["paths"]) for row in admissions) != [1, 5, 10] or len(disk) != 63 or len(power_paths) != 5:
        raise ValueError("require the actual prepared47 plus guarded1+10+5 saved mesh paths")
    for name in ("codex-adapter-adoption-fixed.json", "codex-hero-r3.adoption.json", "codex-power-unit.adoption.json",
                 "codex-workshop.dressing.json", "codex-workshop-source-plan.json", "codex-native-local-bounds.json", "codex-hero-r3.footprint.json"):
        retain(name)
    hero2 = list((folder / "HeroR2" / "h84011").glob("*.receipt.json"))
    if len(hero2) != 1:
        raise ValueError("require the retained HeroR2 source export receipt")
    hero2_receipt = retain(hero2[0].relative_to(folder).as_posix())
    if hero2_receipt.get("stage") != "exported":
        raise ValueError("HeroR2 source receipt is not exported")
    power_source_name = "SalvageAssemblies/a86100/CodexSalvage_PowerUnit_86100.receipt.json"
    power_source = retain(power_source_name)
    if power_source.get("stage") != "exported" or len(power_source.get("blender", {}).get("objects", [])) != 5:
        raise ValueError("PowerUnit retained source receipt differs from its five exported parts")
    for name in ("codex-prepared.delivery.json", "codex-hero-r3.delivery.json", "codex-power-unit.delivery.json"):
        retain(name)
    history = []
    for name in ("codex-cliff.palette.json", "codex-cliff-palette-repaired.json", "codex-cliff-palette-native.json", "codex-cliff-palette-native-v2.json", "codex-palette-stub-inspection.json", "codex-adapter-adoption-first-failed.json"):
        if (folder / name).is_file():
            old = retain(name)
            history.append({"journal": name, "recorded_stage": old.get("stage"), "recorded_error": old.get("error"),
                            "resolution_links": ["codex-cliff-palette-native-v2.json", "codex-cliff-palette-save-reconciled.json"]
                            if "palette" in name or ".palette." in name else ["codex-adapter-adoption-fixed.json"]})
    review_paths = {}
    for path in sorted((folder / "QA").glob("staging.*-review.json")):
        review = retain(path.relative_to(folder).as_posix())
        for view in review.get("views", []):
            image = Path(view["path"]).resolve()
            actual = _file(image)
            if _witness(actual) != _witness(view):
                raise ValueError("native screenshot differs from its review receipt: " + str(image))
            review_paths[str(image)] = {"receipt": path.relative_to(folder).as_posix(), "view": view}
    screenshots = []
    for image in sorted(folder.rglob("*.png")):
        actual = _file(image)
        proof = review_paths.get(actual["path"])
        screenshots.append(dict(actual, evidence="native_still_receipt" if proof else "source_or_unclassified_image", native_review=proof))
    pinned_paths = {"original_manifest": folder / "codex-prepared.delivery.json",
                    "importer": ROOT / "engines/unreal/DaedalusLink/Content/Python/daedalus_codex_prepared_assets.py",
                    "shared_material": CONTENT / "Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour.uasset"}
    pins = {}
    for name, path in pinned_paths.items():
        actual = _file(path)
        if _witness(actual) != PINS[name]:
            raise ValueError("pinned fingerprint differs: " + name)
        pins[name] = dict(actual, expected=PINS[name], matches=True)
    return {"actors": actors, "island_instances": sorted(instances), "plans": plans, "expected_materials": expected_materials,
            "disk_static_meshes": disk, "admissions": admissions, "power_paths": power_paths,
            "source_held": {"HeroR2": {"receipt": hero2[0].relative_to(folder).as_posix(), "stage": "exported_held_from_native_import"},
                            "PowerUnit": {"source_receipt": power_source_name, "exported_objects": 5, "stage": "saved_native_assets_held_from_world"}},
            "historical_journals": history, "screenshots": screenshots, "pinned_inputs": pins, "receipts": bundle}


NATIVE_READ = r'''import unreal
rows=ROWS
asset_paths=ASSETS
power_paths=set(POWER_PATHS)
all_actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
expected={row['label'] for row in rows}
by_label={}
power_references=[]
hero2_labels=[]
for actor in all_actors:
    label=actor.get_actor_label()
    if label in expected:by_label.setdefault(label,[]).append(actor)
    if label.startswith('CodexIsland_summit_rim_84011_HeroR2'):hero2_labels.append(label)
    component=actor.get_component_by_class(unreal.StaticMeshComponent)
    mesh=component.get_editor_property('static_mesh') if component else None
    if mesh and mesh.get_path_name() in power_paths:
        power_references.append({'actor':actor.get_path_name(),'label':label,'mesh_path':mesh.get_path_name()})
observed=[]
for row in rows:
    matches=by_label.get(row['label'],[])
    if len(matches)!=1:raise RuntimeError('missing/ambiguous handoff actor: '+row['label'])
    actor=matches[0]
    component=actor.get_component_by_class(unreal.StaticMeshComponent)
    mesh=component.get_editor_property('static_mesh')
    location,rotation,scale=actor.get_actor_location(),actor.get_actor_rotation(),actor.get_actor_scale3d()
    observed.append({'actor':{'refPath':actor.get_path_name()},'label':actor.get_actor_label(),'mesh_path':mesh.get_path_name(),
        'transform':{'location':{axis:getattr(location,axis) for axis in ('x','y','z')},
                     'rotation':{axis:getattr(rotation,axis) for axis in ('pitch','yaw','roll')},
                     'scale':{axis:getattr(scale,axis) for axis in ('x','y','z')}},
        'materials':[component.get_material(i).get_path_name() if component.get_material(i) else None for i in range(component.get_num_materials())],
        'override_materials':[material.get_path_name() if material else None for material in component.get_editor_property('override_materials')],
        'tags':[str(tag) for tag in actor.get_editor_property('tags')], 'folder':str(actor.get_folder_path())})
classes={}
for path in asset_paths:
    asset=unreal.EditorAssetLibrary.load_asset(path)
    classes[path]={'class':asset.get_class().get_name() if asset else None,'is_static_mesh':isinstance(asset,unreal.StaticMesh)}
result={'all_level_actor_count':len(all_actors),'actors':observed,'saved_asset_classes':classes,
        'dirty_map_packages':[value.get_name() for value in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
        'dirty_content_packages':[value.get_name() for value in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
        'power_unit_actor_references':power_references,'hero_r2_actor_labels':hero2_labels,
        'background_compilation':'not_queried','native_inflight_state':'not_queried'}
'''


def collect(folder, output=None, operator_no_inflight=False):
    folder = Path(folder).resolve()
    output = Path(output).resolve() if output else folder / "codex-editor-handoff-2040.json"
    local = _local(folder)
    protected = {Path(row["file"]["path"]).resolve() for row in local["receipts"].values()}
    protected |= {Path(row["path"]).resolve() for row in local["disk_static_meshes"].values()}
    protected |= {Path(row["path"]).resolve() for row in local["pinned_inputs"].values()}
    if output in protected or output == MAP_FILE.resolve() or not output.parent.is_dir():
        raise ValueError("output must be a separate handoff JSON in an existing directory")
    report = {"schema": "daedalus.codex-editor-handoff.v1", "stage": "local_evidence_collected",
              "collected_utc": datetime.now(timezone.utc).isoformat(), "folder": str(folder), "local": local,
              "operator_declaration": {"no_inflight_declared": bool(operator_no_inflight), "native_queue_state_measured": False},
              "background_compilation": "not_queried", "motion": "deferred", "collision": "deferred", "tests": "deferred",
              "staging_only": True, "ownership_tags_added_by_handoff": False, "native_calls": [],
              "map_before_readback": _file(MAP_FILE), "expected_latest_saved_map": LATEST_MAP}
    _write(output, report)

    def read_call(label, action):
        item = {"label": label, "state": "pending", "read_only": True}
        report["native_calls"].append(item)
        _write(output, report)
        try:
            result = action()
        except Exception as error:
            item.update(state="read_failed", error=str(error))
            _write(output, report)
            raise
        item.update(state="responded", result=result.server if isinstance(result, Mcp) else result)
        _write(output, report)
        return result

    try:
        mcp = read_call("MCP initialize", lambda: Mcp(timeout=60))
        # Mcp is not JSON data; initialization evidence is its actual server info.
        report["native_calls"][-1]["result"] = mcp.server
        pie = read_call("IsPIERunning", lambda: mcp.call(APP, "IsPIERunning"))
        current = read_call("get_current_level", lambda: mcp.call(SCENE, "get_current_level"))
        camera = read_call("GetCameraTransform", lambda: mcp.call(APP, "GetCameraTransform"))
        report["editor"] = {"pie_running": pie, "current_map": current, "camera": camera}
        if pie is not False or package(current) != MAP:
            raise RuntimeError("require the actual agreed map with PIE stopped for the readback")
        code = NATIVE_READ.replace("ROWS", repr(local["actors"])).replace("ASSETS", repr(sorted(local["disk_static_meshes"]))).replace("POWER_PATHS", repr(local["power_paths"]))
        native = read_call("execute_python actor/component/assets/dirty-package readback", lambda: wire.obj(
            wire.call(wire.UNREAL, "execute_python", code=code, unattended=False, timeout=90, side="Unreal"),
            side="Unreal", what="handoff readback"))
        issues = []
        observed = {row["label"]: row for row in native["actors"]}
        for expected in local["actors"]:
            actual = observed.get(expected["label"])
            if not actual or actual["actor"] != expected["actor"] or actual["mesh_path"] != expected["mesh_path"] or not _same_transform(actual["transform"], expected["transform"]):
                issues.append("actor identity/mesh/transform differs: " + expected["label"])
                continue
            if actual["materials"] != local["expected_materials"][expected["label"]]:
                issues.append("component material readback differs: " + expected["label"])
            if any(tag.lower() == "land" for tag in actual["tags"]):
                issues.append("staging actor has a Land tag: " + expected["label"])
            if not actual["folder"].startswith("CodexContest/Staging"):
                issues.append("actor leaves the recorded staging folder: " + expected["label"])
        if len(native["actors"]) != 63 or len(observed) != 63:
            issues.append("native actor readback is not the exact 63-row set")
        if set(native["saved_asset_classes"]) != set(local["disk_static_meshes"]) or not all(row["is_static_mesh"] is True for row in native["saved_asset_classes"].values()):
            issues.append("saved native asset class readback differs from 63 StaticMeshes")
        dirty = native["dirty_map_packages"] + native["dirty_content_packages"]
        own_dirty = [name for name in dirty if package(name) == MAP or package(name).startswith(DEST + "/")]
        if own_dirty:
            issues.append("owned map/content packages remain dirty")
        if native["power_unit_actor_references"] or native["hero_r2_actor_labels"]:
            issues.append("held PowerUnit or HeroR2 has native world references")
        after = _file(MAP_FILE)
        if _witness(after) != _witness(report["map_before_readback"]):
            issues.append("map bytes changed during the read-only handoff snapshot")
        if _witness(after) != LATEST_MAP:
            issues.append("map bytes differ from the latest recorded saved palette receipt")
        report.update(native_readback=native, own_dirty_packages=own_dirty, map_after_readback=after,
                      map_matches_latest_saved_receipt=_witness(after) == LATEST_MAP,
                      issues=issues, measured_actor_rows=len(observed), verified_saved_mesh_files=len(local["disk_static_meshes"]),
                      held={"PowerUnit": {"saved_meshes": 5, "native_actor_references": native["power_unit_actor_references"], "placement": "held"},
                            "HeroR2": {"stage": "source_exported_held", "native_actor_labels": native["hero_r2_actor_labels"]}},
                      stage="handoff_readback_completed" if not issues else "handoff_inspection_required")
        # The native read only reports these values; neither is inferred from
        # an empty dirty list or the operator's no-inflight declaration.
        report["native_inflight_state"] = "not_queried"
        _write(output, report)
        return report
    except Exception as error:
        report.update(stage="handoff_readback_incomplete", error=str(error))
        # A client object must never leak into the serialized evidence bundle.
        for item in report["native_calls"]:
            if isinstance(item.get("result"), Mcp):
                item["result"] = item["result"].server
        _write(output, report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--operator-no-inflight", action="store_true", help="operator declaration only; native queue/compilation state is not queried")
    args = parser.parse_args()
    result = collect(args.folder, args.out, args.operator_no_inflight)
    print(json.dumps({key: result[key] for key in ("stage", "measured_actor_rows", "verified_saved_mesh_files", "map_after_readback", "issues")}, indent=2))
    return 0 if not result["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
