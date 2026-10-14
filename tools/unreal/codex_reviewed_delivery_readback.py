# SPDX-License-Identifier: MIT
"""Read the bounded renewed Codex production state without changing Unreal.

Operator-only entry point: combines the frozen 2040 baseline with exact saved
HeroR4 and GardenGateR1 admissions, assemblies and palette journals. Native calls
only read PIE/map/camera, actors/components, mesh classes and dirty packages.
This is production receipt verification, not BAR, collision or runtime testing.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from codex_admitted_asset_assembly import plan_admitted, _retained_contract
from codex_editor_handoff import (
    APP, CONTENT, DEST, MAP, MAP_FILE, Mcp, NATIVE_READ, SCENE, _asset_file,
    _file, _local, _same_transform, _witness, fingerprint, package, wire,
)
from codex_saved_asset_assembly import _read, _write

FROZEN = "codex-editor-handoff-2040.json"
FROZEN_SHA256 = "0d188a70bb0ff6bcc3b756998344e4776e14361b29b83cbb851f900651e77e2a"
CANDIDATES = (
    ("CodexIsland_summit_rim_84011_HeroR4", "codex-hero-r4", "4baeb945202507ea41b225c2", 10),
    ("CodexIsland_cliff_garden_84022_GardenGateR1", "codex-garden-gate-r1", "2383d5c07d1d765d74a847af", 9),
)


def _renewed_local(folder):
    local = _local(folder)
    evidence = {}

    def retain(path):
        path = Path(path).resolve()
        value, witness = _read(path)
        evidence[str(path)] = {"file": dict(path=str(path), **witness), "receipt": value}
        return value

    frozen = retain(folder / FROZEN)
    if evidence[str((folder / FROZEN).resolve())]["file"]["sha256"] != FROZEN_SHA256:
        raise ValueError("frozen 2040 packet bytes changed")
    if frozen.get("stage") != "handoff_readback_completed" or frozen.get("issues") != []:
        raise ValueError("frozen baseline was not a completed clean readback")
    frozen_rows = {row["label"]: row for row in frozen["native_readback"]["actors"]}
    old_labels = {row["label"] for row in local["actors"]}
    if len(frozen_rows) != 63 or set(frozen_rows) != old_labels:
        raise ValueError("frozen baseline actor labels differ from the original 63")
    for row in local["actors"]:
        saved = frozen_rows[row["label"]]
        if saved["actor"] != row["actor"] or saved["mesh_path"] != row["mesh_path"] or not _same_transform(saved["transform"], row["transform"]):
            raise ValueError("original actor receipt differs from its frozen readback")
        if saved["materials"] != local["expected_materials"][row["label"]]:
            raise ValueError("original palette receipt differs from its frozen component materials")
    actors = list(local["actors"])
    materials = dict(local["expected_materials"])
    disk = dict(local["disk_static_meshes"])
    folders = {label: row["folder"] for label, row in frozen_rows.items()}
    admissions, new_paths = [], set()
    final_map = None
    for name, stem, key24, count in CANDIDATES:
        world_path = folder / (stem + ".world.json")
        world = retain(world_path)
        if world.get("stage") != "placed_and_saved" or world.get("save_return") is not True or world.get("saved_unreal") is not True:
            raise ValueError("renewed assembly lacks a confirmed map save: " + stem)
        if world.get("staging_only") is not True or world.get("ownership_tags_added") is not False or world.get("folder") != "CodexContest/Staging":
            raise ValueError("renewed assembly staging contract differs: " + stem)
        recorded = world["plan"]
        if set(recorded.get("placements_cm", {})) != {name}:
            raise ValueError("renewed placement identity differs: " + stem)
        receipt_path = folder / "NativeReceipts2130" / ("codex-ingestion-" + key24 + ".json")
        receipt = retain(receipt_path)
        if Path(recorded["saved_receipt"]).resolve() != receipt_path.resolve():
            raise ValueError("renewed assembly points to a different saved admission")
        plan = plan_admitted(receipt_path, recorded["placements_cm"][name], MAP, MAP_FILE)
        if any(recorded.get(key) != value for key, value in plan.items()) or plan["manifest_key"][:24] != key24:
            raise ValueError("saved assembly plan differs from the canonical guarded admission")
        entries = {row["label"]: row for row in plan["entries"]}
        rows = world.get("actors", [])
        if len(rows) != count or len(entries) != count or {row["label"] for row in rows} != set(entries):
            raise ValueError("renewed assembly does not contain the exact ten/nine admitted roles")
        for row in rows:
            entry = entries[row["label"]]
            if row["mesh_path"] != entry["mesh_path"] or row.get("group") != name or not _same_transform(row["transform"], entry["transform"]):
                raise ValueError("renewed actor mapping differs from its guarded plan")
            if package(row["actor"]) != MAP:
                raise ValueError("renewed actor resides outside the agreed map")
            folders[row["label"]] = world["folder"]
        palette_path = folder / (stem + ".palette.json")
        palette = retain(palette_path)
        if palette.get("stage") != "component_palette_saved" or any(palette.get(key) is not True for key in
                ("save_return", "prepared_meshes_unchanged", "additional_saved_meshes_unchanged", "shared_material_unchanged")):
            raise ValueError("renewed palette lacks a confirmed preservation/save receipt: " + stem)
        if palette.get("actors") != rows:
            raise ValueError("renewed palette selected a different saved actor set")
        applied = palette.get("applied", [])
        if len(applied) != count or {row["label"] for row in applied} != set(entries):
            raise ValueError("renewed palette does not cover the exact admitted actor labels")
        inputs = palette["candidate_inputs"]
        if Path(inputs["assembly"]).resolve() != world_path.resolve() or inputs["assembly_fingerprint"] != fingerprint(world_path):
            raise ValueError("palette assembly witness differs from its saved world journal")
        source_path = Path(inputs["source_receipt"]).resolve()
        source = retain(source_path)
        if inputs["source_receipt_fingerprint"] != fingerprint(source_path) or source.get("name") != name or source.get("stage") != "exported":
            raise ValueError("palette source receipt identity/stage/fingerprint differs")
        config = source["config"]
        expected = _retained_contract({"name": name, "seed": config["seed"], "config_sha256": source["config_sha256"], "config": config}, {})
        if source["config_sha256"] != plan["config_sha256"] or config["seed"] != plan["seed"] or expected != set(entries):
            raise ValueError("source identity/config/roles differ from the saved admission")
        if source["artifacts"]["fbx"]["fingerprint"] != plan["source_fingerprint"]:
            raise ValueError("source FBX witness differs from the saved admission")
        for artifact in source["artifacts"].values():
            if fingerprint(artifact["path"]) != artifact["fingerprint"]:
                raise ValueError("retained source export bytes changed")
        for row in applied:
            if row["label"] in materials or not row["materials"] or any(not isinstance(path, str) or not package(path).startswith(DEST + "/Palette/") for path in row["materials"]):
                raise ValueError("renewed component palette is duplicated or leaves the owned palette")
            materials[row["label"]] = row["materials"]
        for path, witness in receipt["outputs"].items():
            if path in disk or path in new_paths:
                raise ValueError("renewed admission duplicates a retained mesh asset")
            actual = _file(_asset_file(path))
            if _witness(actual) != _witness(witness):
                raise ValueError("renewed saved mesh bytes differ")
            disk[path] = dict(actual, origin=str(receipt_path))
            new_paths.add(path)
        actors.extend(rows)
        admissions.append({"name": name, "key": receipt["key"], "receipt": str(receipt_path), "meshes": count,
                           "assembly": str(world_path), "palette": str(palette_path), "source": str(source_path)})
        final_map = _witness(palette["map_after"])
    if len(actors) != 82 or len({row["label"] for row in actors}) != 82 or len({row["actor"]["refPath"] for row in actors}) != 82:
        raise ValueError("require original63 plus19 distinct saved actor identities")
    if len(disk) != 82 or len(new_paths) != 19 or set(materials) != {row["label"] for row in actors}:
        raise ValueError("require82 saved mesh files and complete component palettes")
    palette_paths = {path for values in materials.values() for path in values}
    palette_paths.add(DEST + "/Palette/M_CodexPalette_v1")
    palette_disk = {path: _file(_asset_file(path)) for path in sorted(palette_paths)}
    protected = {row["file"]["path"]: row["file"] for row in local["receipts"].values()}
    protected.update({path: row["file"] for path, row in evidence.items()})
    protected.update({row["path"]: row for row in disk.values()})
    protected.update({row["path"]: row for row in palette_disk.values()})
    protected.update({row["path"]: row for row in local["pinned_inputs"].values()})
    for row in evidence.values():
        if row["receipt"].get("stage") == "exported":
            for artifact in row["receipt"].get("artifacts", {}).values():
                protected[artifact["path"]] = dict(path=artifact["path"], **artifact["fingerprint"])
    return {"baseline": local, "frozen": frozen_rows, "actors": actors, "expected_materials": materials,
            "expected_folders": folders, "disk_static_meshes": disk, "disk_palette_assets": palette_disk,
            "new_admissions": admissions, "new_mesh_paths": sorted(new_paths), "evidence": evidence,
            "protected_files": protected, "latest_map": final_map}


def collect(folder, output):
    folder, output = Path(folder).resolve(), Path(output).resolve()
    if output.exists() or not output.parent.is_dir() or output.suffix.lower() != ".json":
        raise ValueError("--out must name a new JSON file in an existing directory")
    local = _renewed_local(folder)
    if output == MAP_FILE.resolve() or str(output) in local["protected_files"]:
        raise ValueError("output must not overwrite a protected production input")
    before = _file(MAP_FILE)
    if _witness(before) != local["latest_map"]:
        raise ValueError("map bytes differ from the final GardenGateR1 palette save")
    report = {"schema": "daedalus.codex-renewed-production-readback.v1", "stage": "local_evidence_collected",
              "collected_utc": datetime.now(timezone.utc).isoformat(), "folder": str(folder), "local": local,
              "map_before_readback": before, "expected_latest_saved_map": local["latest_map"], "native_calls": [],
              "scope": "original63 plus HeroR4 ten and GardenGateR1 nine saved actors/assets; six named island instances",
              "limits": {"bar_acceptance": "not_established", "collision_walkability": "unverified", "motion_gameplay": "unverified",
                         "tests": "deferred_by_user", "background_compilation": "not_queried", "native_queue_state": "not_queried",
                         "source_stills": "appearance_only", "actor_scan": "first StaticMeshComponent per loaded level actor"},
              "staging_only": True, "ownership_changes": False}
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
        code = code.replace("ROWS", repr(local["actors"])).replace("ASSETS", repr(sorted(local["disk_static_meshes"]))).replace("POWER_PATHS", repr(local["baseline"]["power_paths"]))
        native = read_call("execute_python renewed actor/component/assets/dirty-package readback", lambda: wire.obj(
            wire.call(wire.UNREAL, "execute_python", code=code, unattended=False, timeout=90, side="Unreal"),
            side="Unreal", what="renewed production readback"))
        issues = []
        observed = {row["label"]: row for row in native["actors"]}
        for expected in local["actors"]:
            label = expected["label"]
            actual = observed.get(label)
            if not actual or actual["actor"] != expected["actor"] or actual["mesh_path"] != expected["mesh_path"] or not _same_transform(actual["transform"], expected["transform"]):
                issues.append("actor identity/mesh/transform differs: " + label)
                continue
            if actual["materials"] != local["expected_materials"][label]:
                issues.append("component materials differ: " + label)
            if actual["folder"] != local["expected_folders"][label]:
                issues.append("actor folder differs: " + label)
            if any(tag.lower() in ("land", "deed") or tag.lower().startswith("deed:") for tag in actual["tags"]):
                issues.append("staging actor has an ownership tag: " + label)
            if label in local["frozen"]:
                baseline = local["frozen"][label]
                if actual["override_materials"] != baseline["override_materials"] or actual["tags"] != baseline["tags"]:
                    issues.append("original actor overrides/tags differ from frozen2040: " + label)
            elif actual["override_materials"] != local["expected_materials"][label]:
                issues.append("new explicit component overrides differ: " + label)
        if len(native["actors"]) != 82 or len(observed) != 82 or set(observed) != set(local["expected_materials"]):
            issues.append("native actor readback is not the exact82-row set")
        if set(native["saved_asset_classes"]) != set(local["disk_static_meshes"]) or any(row.get("is_static_mesh") is not True or row.get("class") != "StaticMesh" for row in native["saved_asset_classes"].values()):
            issues.append("native classes differ from82 saved StaticMeshes")
        if native["dirty_map_packages"] or native["dirty_content_packages"]:
            issues.append("native map/content dirty-package lists are not empty")
        if native["power_unit_actor_references"] or native["hero_r2_actor_labels"] or native["hero_r2_mesh_references"]:
            issues.append("held PowerUnit or HeroR2 has loaded world references")
        pie_after = read_call("IsPIERunning after snapshot", lambda: mcp.call(APP, "IsPIERunning"))
        current_after = read_call("get_current_level after snapshot", lambda: mcp.call(SCENE, "get_current_level"))
        if pie_after is not False or package(current_after) != MAP:
            issues.append("PIE/current map changed during readback")
        for path, witness in local["protected_files"].items():
            if fingerprint(path) != _witness(witness):
                issues.append("protected production file changed during readback: " + path)
        after = _file(MAP_FILE)
        if _witness(after) != _witness(before) or _witness(after) != local["latest_map"]:
            issues.append("map bytes changed during readback or differ from final palette save")
        report.update(stage="renewed_production_readback_completed" if not issues else "renewed_production_inspection_required",
                      native_readback=native, map_after_readback=after, issues=issues, measured_actor_rows=len(observed),
                      verified_saved_mesh_files=len(local["disk_static_meshes"]), new_actor_rows=19, new_saved_mesh_files=19,
                      original63_component_materials_unchanged=all(observed.get(label, {}).get("materials") == row["materials"] for label, row in local["frozen"].items()),
                      protected_disk_files_unchanged=not any(message.startswith("protected production file") for message in issues),
                      editor_after={"pie_running": pie_after, "current_map": current_after},
                      held={"PowerUnit": {"saved_meshes": 5, "native_actor_references": native["power_unit_actor_references"]},
                            "HeroR2": {"stage": "source_exported_held", "native_actor_labels": native["hero_r2_actor_labels"], "native_mesh_references": native["hero_r2_mesh_references"]}})
        _write(output, report)
        return report
    except Exception as error:
        report.update(stage="renewed_production_readback_incomplete", error=str(error))
        _write(output, report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="new immutable readback JSON path; existing output is refused")
    args = parser.parse_args()
    result = collect(args.folder, args.out)
    print(json.dumps({key: result[key] for key in ("stage", "measured_actor_rows", "verified_saved_mesh_files", "map_after_readback", "issues")}, indent=2))
    return 0 if not result["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
