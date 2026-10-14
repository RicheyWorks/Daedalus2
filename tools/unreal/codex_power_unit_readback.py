# SPDX-License-Identifier: MIT
"""Read the saved PowerUnit placement against the immutable 82-actor baseline.

Run only by the acknowledged editor operator after PowerUnit palette/save. Native
operations read state only. Five new actors reuse existing saved meshes: the
expected totals are 87 staging actors and 82 saved StaticMesh files, not 87 files.
No source/export edit, import, placement, material change, save, or screenshot.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from codex_admitted_asset_assembly import POWER_NAME, POWER_CONFIG_SHA256, _retained_contract, plan_admitted
from codex_editor_handoff import (
    APP, DEST, MAP, MAP_FILE, Mcp, NATIVE_READ, SCENE, _asset_file, _file,
    _same_transform, _witness, fingerprint, package, wire,
)
from codex_saved_asset_assembly import _read, _write

BASELINE = "codex-power-unit-2205.before.json"
BASELINE_SHA256 = "d0cbae6612cb26d9d977fc46a4f8fef8d4f2c67cdcecb61b1888216309be527e"
BASELINE_MAP = {"sha256": "8195054a37c2b6813f8993db6004c79157eb66e1710b93cadc5de6a72c65c6e7", "bytes": 209288788}
POWER_KEY = "e3f098e65a1dc4ddb1129b79da5cc81497da02ddc78b2b38543d955b9d940c39"
WORLD = "codex-power-unit-2205.world.json"
PALETTE = "codex-power-unit-2205.palette.json"
SOURCE = "SalvageAssemblies/a86100/CodexSalvage_PowerUnit_86100.receipt.json"
ADMISSION = "NativeReceipts/codex-ingestion-e3f098e65a1dc4ddb1129b79.json"


def _local_power(folder):
    evidence = {}

    def retain(relative):
        path = (folder / relative).resolve()
        value, witness = _read(path)
        evidence[relative] = {"file": dict(path=str(path), **witness), "receipt": value}
        return value

    baseline = retain(BASELINE)
    if evidence[BASELINE]["file"]["sha256"] != BASELINE_SHA256:
        raise ValueError("completed pre-PowerUnit baseline bytes changed")
    if baseline.get("schema") != "daedalus.codex-renewed-production-readback.v1" or baseline.get("stage") != "renewed_production_readback_completed" or baseline.get("issues") != []:
        raise ValueError("require the exact completed clean baseline readback")
    if baseline.get("measured_actor_rows") != 82 or baseline.get("verified_saved_mesh_files") != 82 or _witness(baseline["map_after_readback"]) != BASELINE_MAP:
        raise ValueError("baseline count/map witness differs")
    prior = baseline["native_readback"]
    old = {row["label"]: row for row in prior["actors"]}
    old_rows = baseline["local"]["actors"]
    disk = baseline["local"]["disk_static_meshes"]
    if len(old) != 82 or len(prior["actors"]) != 82 or len(old_rows) != 82 or {row["label"] for row in old_rows} != set(old) or len(disk) != 82:
        raise ValueError("baseline does not contain exact82 actor/file sets")
    if prior["dirty_map_packages"] or prior["dirty_content_packages"] or prior["power_unit_actor_references"] or prior["hero_r2_actor_labels"] or prior.get("hero_r2_mesh_references"):
        raise ValueError("pre-placement baseline was dirty or already referenced held assets")
    if set(prior["saved_asset_classes"]) != set(disk) or any(row.get("class") != "StaticMesh" or row.get("is_static_mesh") is not True for row in prior["saved_asset_classes"].values()):
        raise ValueError("baseline native mesh-class set differs from its82 files")
    world, palette, source, admission = (retain(path) for path in (WORLD, PALETTE, SOURCE, ADMISSION))
    if world.get("stage") != "placed_and_saved" or world.get("save_return") is not True or world.get("saved_unreal") is not True or world.get("staging_only") is not True or world.get("ownership_tags_added") is not False:
        raise ValueError("PowerUnit assembly lacks its exact confirmed staging save")
    recorded = world["plan"]
    if set(recorded.get("placements_cm", {})) != {POWER_NAME} or world.get("folder") != "CodexContest/Staging":
        raise ValueError("PowerUnit assembly identity/folder differs")
    if Path(recorded["saved_receipt"]).resolve() != (folder / ADMISSION).resolve():
        raise ValueError("PowerUnit assembly points to a different saved admission")
    plan = plan_admitted(folder / ADMISSION, recorded["placements_cm"][POWER_NAME], MAP, MAP_FILE)
    if plan["manifest_key"] != POWER_KEY or any(recorded.get(key) != value for key, value in plan.items()):
        raise ValueError("PowerUnit plan differs from its canonical saved admission")
    config = source["config"]
    expected = _retained_contract({"name": source.get("name"), "seed": config.get("seed"), "config_sha256": source.get("config_sha256"), "config": config}, {})
    if source.get("schema") != "daedalus.codex-salvage-assembly.v1" or source.get("stage") != "exported" or source.get("name") != POWER_NAME or source.get("config_sha256") != POWER_CONFIG_SHA256:
        raise ValueError("require the exact retained exported PowerUnit source receipt")
    if len(expected) != 5 or source["artifacts"]["fbx"]["fingerprint"] != plan["source_fingerprint"]:
        raise ValueError("PowerUnit source roles/FBX differ from its saved admission")
    objects, entries, rows = source["blender"]["objects"], plan["entries"], world["actors"]
    if any(len(values) != 5 for values in (objects, entries, rows)) or {row["name"] for row in objects} != expected or {row["label"] for row in entries} != expected or {row["label"] for row in rows} != expected:
        raise ValueError("PowerUnit source/plan/actor role sets differ")
    by_label = {row["label"]: row for row in entries}
    for row in rows:
        entry = by_label[row["label"]]
        if row.get("group") != POWER_NAME or row["mesh_path"] != entry["mesh_path"] or not _same_transform(row["transform"], entry["transform"]) or package(row["actor"]) != MAP:
            raise ValueError("PowerUnit saved actor mapping differs from its plan")
    if palette.get("stage") != "component_palette_saved" or any(palette.get(key) is not True for key in
            ("save_return", "prepared_meshes_unchanged", "additional_saved_meshes_unchanged", "shared_material_unchanged")) or palette.get("actors") != rows:
        raise ValueError("PowerUnit palette lacks its exact saved actor/preservation receipt")
    inputs = palette["candidate_inputs"]
    for field, relative in (("assembly", WORLD), ("source_receipt", SOURCE)):
        if Path(inputs[field]).resolve() != (folder / relative).resolve() or inputs[field + "_fingerprint"] != _witness(evidence[relative]["file"]):
            raise ValueError("PowerUnit palette input fingerprint differs: " + field)
    applied = palette.get("applied", [])
    materials = {row["label"]: row["materials"] for row in applied}
    if len(applied) != 5 or set(materials) != expected or any(not values or any(not isinstance(path, str) or not package(path).startswith(DEST + "/Palette/") for path in values) for values in materials.values()):
        raise ValueError("PowerUnit palette must cover the exact five roles with owned materials")
    paths = {row["mesh_path"] for row in rows}
    if len(paths) != 5 or set(admission["outputs"]) != paths or not paths.issubset(disk):
        raise ValueError("PowerUnit must reuse its five assets already included in baseline82")
    for path in paths:
        if _witness(admission["outputs"][path]) != _witness(disk[path]):
            raise ValueError("PowerUnit output bytes differ from their baseline witness")
    protected = dict(baseline["local"]["protected_files"])
    for item in evidence.values():
        protected[item["file"]["path"]] = item["file"]
    for path, witness in disk.items():
        actual = _file(_asset_file(path))
        if _witness(actual) != _witness(witness):
            raise ValueError("baseline saved StaticMesh bytes changed: " + path)
        protected[actual["path"]] = actual
    for artifact in source["artifacts"].values():
        if fingerprint(artifact["path"]) != artifact["fingerprint"]:
            raise ValueError("retained PowerUnit export/recipe bytes changed")
        protected[artifact["path"]] = dict(path=artifact["path"], **artifact["fingerprint"])
    for path in {value for values in materials.values() for value in values}:
        actual = _file(_asset_file(path))
        protected[actual["path"]] = actual
    for path, witness in protected.items():
        if fingerprint(path) != _witness(witness):
            raise ValueError("protected production input differs before native readback: " + path)
    actors = old_rows + rows
    if len(actors) != 87 or len({row["label"] for row in actors}) != 87 or len({row["actor"]["refPath"] for row in actors}) != 87 or set(old) & expected:
        raise ValueError("require82 distinct prior actors plus five distinct new PowerUnit actors")
    return {"baseline_input": evidence[BASELINE]["file"], "prior_native": prior, "actors": actors,
            "power_actors": rows, "power_paths": sorted(paths), "power_materials": materials,
            "disk_static_meshes": disk, "protected_files": protected, "evidence": evidence,
            "expected_latest_saved_map": _witness(palette["map_after"]), "folder": world["folder"]}


def collect(folder, output):
    folder, output = Path(folder).resolve(), Path(output).resolve()
    if output.exists() or not output.parent.is_dir() or output.suffix.lower() != ".json":
        raise ValueError("--out must be a new JSON path in an existing directory")
    local = _local_power(folder)
    before = _file(MAP_FILE)
    if _witness(before) != local["expected_latest_saved_map"]:
        raise ValueError("current map differs from the PowerUnit palette save witness")
    report = {"schema": "daedalus.codex-power-unit-production-readback.v1", "stage": "local_evidence_collected",
              "collected_utc": datetime.now(timezone.utc).isoformat(), "local": local, "native_calls": [],
              "map_before_readback": before, "expected_latest_saved_map": local["expected_latest_saved_map"],
              "scope": "82 prior actors plus five PowerUnit actors; all82 saved meshes preserved; zero new mesh imports",
              "staging_only": True, "ownership_changes": False,
              "limits": {"bar_acceptance": "not_established", "collision_walkability": "unverified", "motion_gameplay_electrical_snapping": "unverified",
                         "tests": "deferred_by_user", "background_compilation": "not_queried", "native_queue_state": "not_queried",
                         "actor_scan": "first StaticMeshComponent per loaded level actor"}}
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

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
        pie = read_call("IsPIERunning", lambda: mcp.call(APP, "IsPIERunning"))
        current = read_call("get_current_level", lambda: mcp.call(SCENE, "get_current_level"))
        camera = read_call("GetCameraTransform", lambda: mcp.call(APP, "GetCameraTransform"))
        report["editor"] = {"pie_running": pie, "current_map": current, "camera": camera}
        if pie is not False or package(current) != MAP:
            raise RuntimeError("require the agreed map with PIE stopped")
        code = NATIVE_READ.replace("hero2_labels=[]", "hero2_labels=[]\nhero2_mesh_references=[]")
        code = code.replace("observed=[]", "    if mesh and 'CodexIsland_summit_rim_84011_HeroR2' in mesh.get_path_name():\n        hero2_mesh_references.append({'actor':actor.get_path_name(),'label':label,'mesh_path':mesh.get_path_name()})\nobserved=[]")
        code = code.replace("'hero_r2_actor_labels':hero2_labels,", "'hero_r2_actor_labels':hero2_labels,'hero_r2_mesh_references':hero2_mesh_references,")
        code = code.replace("ROWS", repr(local["actors"])).replace("ASSETS", repr(sorted(local["disk_static_meshes"]))).replace("POWER_PATHS", repr(local["power_paths"]))
        native = read_call("execute_python87actors82meshes and dirty packages", lambda: wire.obj(
            wire.call(wire.UNREAL, "execute_python", code=code, unattended=False, timeout=90, side="Unreal"),
            side="Unreal", what="PowerUnit production readback"))
        issues = []
        observed = {row["label"]: row for row in native["actors"]}
        if len(native["actors"]) != 87 or len(observed) != 87 or set(observed) != {row["label"] for row in local["actors"]}:
            issues.append("native actor set differs from exact87")
        prior_fields = ("actor", "mesh_path", "transform", "materials", "override_materials", "folder", "tags")
        for row in local["prior_native"]["actors"]:
            actual = observed.get(row["label"], {})
            if any(actual.get(field) != row[field] for field in prior_fields):
                issues.append("prior actor state changed from completed82 baseline: " + row["label"])
        for row in local["power_actors"]:
            actual = observed.get(row["label"], {})
            if actual.get("actor") != row["actor"] or actual.get("mesh_path") != row["mesh_path"] or not actual.get("transform") or not _same_transform(actual["transform"], row["transform"]):
                issues.append("new PowerUnit actor identity/mesh/transform differs: " + row["label"])
            desired = local["power_materials"][row["label"]]
            if actual.get("materials") != desired or actual.get("override_materials") != desired or actual.get("folder") != local["folder"]:
                issues.append("new PowerUnit component palette/folder differs: " + row["label"])
            if any(tag.lower() in ("land", "deed") or tag.lower().startswith("deed:") for tag in actual.get("tags", [])):
                issues.append("new PowerUnit actor has an ownership tag: " + row["label"])
        expected_refs = {(row["actor"]["refPath"], row["label"], row["mesh_path"]) for row in local["power_actors"]}
        refs = native["power_unit_actor_references"]
        if len(refs) != 5 or {(row["actor"], row["label"], row["mesh_path"]) for row in refs} != expected_refs:
            issues.append("PowerUnit world references differ from the exact five saved actors")
        if native["hero_r2_actor_labels"] or native["hero_r2_mesh_references"]:
            issues.append("held HeroR2 has loaded world references")
        if native["saved_asset_classes"] != local["prior_native"]["saved_asset_classes"]:
            issues.append("saved82 StaticMesh class/path set changed")
        if native["dirty_map_packages"] or native["dirty_content_packages"]:
            issues.append("map/content dirty-package lists are not empty")
        pie_after = read_call("IsPIERunning after snapshot", lambda: mcp.call(APP, "IsPIERunning"))
        current_after = read_call("get_current_level after snapshot", lambda: mcp.call(SCENE, "get_current_level"))
        if pie_after is not False or package(current_after) != MAP:
            issues.append("PIE/current map changed during readback")
        for path, witness in local["protected_files"].items():
            if fingerprint(path) != _witness(witness):
                issues.append("protected production file changed during readback: " + path)
        after = _file(MAP_FILE)
        if _witness(after) != _witness(before) or _witness(after) != local["expected_latest_saved_map"]:
            issues.append("map changed during readback or differs from the final palette save")
        report.update(stage="power_unit_production_readback_completed" if not issues else "power_unit_production_inspection_required",
                      native_readback=native, map_after_readback=after, issues=issues, measured_actor_rows=len(observed),
                      verified_saved_mesh_files=82, new_actor_rows=5, new_saved_mesh_files=0, reused_saved_power_mesh_files=5,
                      prior82_actor_state_unchanged=not any(message.startswith("prior actor") for message in issues),
                      protected_disk_files_unchanged=not any(message.startswith("protected production file") for message in issues),
                      editor_after={"pie_running": pie_after, "current_map": current_after})
        _write(output, report)
        return report
    except Exception as error:
        report.update(stage="power_unit_production_readback_incomplete", error=str(error))
        _write(output, report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="new exclusive final production readback JSON path")
    args = parser.parse_args()
    result = collect(args.folder, args.out)
    print(json.dumps({key: result[key] for key in ("stage", "measured_actor_rows", "verified_saved_mesh_files", "map_after_readback", "issues")}, indent=2))
    return 0 if not result["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
