# SPDX-License-Identifier: MIT
"""Owner-run import/save of existing Codex FBX payloads; no world placement.

Uses the verified daedalus_claude_islands AssetImportTask pattern. Execute this
file in the acknowledged owner's Unreal Python context, then call import_all
with the prepared manifest path. Never clears cells, replaces actors or restarts.
"""
import hashlib
import json
import math
from pathlib import Path
import time

import unreal

ROOT = "/Game/Daedalus/Art/Islands/CodexContest"
MATERIAL = "/Game/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour"
EAL = unreal.EditorAssetLibrary


def fingerprint(path):
    digest, size = hashlib.sha256(), 0
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "bytes": size}


def _write(path, report):
    Path(path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _meshes(folder):
    out = []
    for path in EAL.list_assets(folder, recursive=True, include_folder=False):
        asset = EAL.load_asset(path)
        if isinstance(asset, unreal.StaticMesh):
            out.append(asset)
    return out


def _tags(entry):
    return {"codex_owner": "codex-contest", "codex_sha256": entry["fbx"]["sha256"],
            "codex_bytes": str(entry["fbx"]["bytes"]), "codex_config": entry["config_sha256"],
            "codex_seed": str(entry["seed"]), "codex_kind": entry["kind"]}


def _verify(entry, meshes):
    expected = {row["name"]: row for row in entry["objects"]}
    actual = {}
    for mesh in meshes:
        name = mesh.get_name()
        match = [key for key in expected if name == key or name.endswith("_" + key)]
        if len(match) != 1 or match[0] in actual:
            raise RuntimeError("imported mesh identity differs: " + name)
        actual[match[0]] = mesh
    if set(actual) != set(expected):
        raise RuntimeError("imported mesh set differs for " + entry["name"])
    for name, mesh in actual.items():
        bounds = mesh.get_bounding_box()
        dims = sorted([bounds.max.x-bounds.min.x, bounds.max.y-bounds.min.y, bounds.max.z-bounds.min.z], reverse=True)
        want = sorted([100.0 * value for value in expected[name]["dims"]], reverse=True)
        if not all(math.isfinite(value) and value >= 0 for value in dims):
            raise RuntimeError("native bounds are not finite for " + name)
        if any(abs(a-b) > max(1.0, .01*b) for a,b in zip(dims,want)):
            raise RuntimeError("metre-to-centimetre bounds differ for " + name)
    return actual


def import_all(manifest_path, report_path=None):
    """Import/save the prepared batch; saved assets remain held from placement.

    Byte-bound revision folders preserve earlier assets. Unknown/pending import
    outcomes require inspection; no automatic retries or overwrite is performed.
    UV/Nanite/collision flags are per-task options, not shared settings changes.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("schema") != "daedalus.codex-prepared-delivery.v1":
        raise ValueError("unsupported delivery manifest")
    entries = manifest["assets"]
    if len(entries) != 24 or len({entry["name"] for entry in entries}) != 24:
        raise ValueError("expected the exact prepared 3-island/21-module batch")
    for entry in entries:
        if fingerprint(entry["fbx"]["path"]) != {key: entry["fbx"][key] for key in ("sha256", "bytes")}:
            raise ValueError("prepared FBX changed: " + entry["name"])
        if not entry["destination"].startswith(ROOT + "/"):
            raise ValueError("destination outside owned namespace")
    material = EAL.load_asset(MATERIAL)
    if not isinstance(material, unreal.MaterialInterface):
        raise RuntimeError("existing vertex-colour material unavailable; nothing imported")
    report_path = report_path or str(Path(manifest_path).with_name("codex-prepared.unreal.json"))
    if Path(report_path).is_file():
        prior = json.loads(Path(report_path).read_text(encoding="utf-8"))
        if prior.get("stage") != "assets_saved":
            raise RuntimeError("unfinished import report requires outcome inspection: " + report_path)
        Path(report_path + "." + str(time.time_ns()) + ".previous").write_text(json.dumps(prior), encoding="utf-8")
    report = {"stage": "prepared", "prepared_groups": 24, "prepared_islands": 3, "prepared_modules": 21,
              "imported_groups": 0, "saved_groups": 0, "saved_meshes": 0, "world_placed": 0,
              "material": MATERIAL, "results": [], "manifest_sha256": fingerprint(manifest_path)["sha256"]}
    _write(report_path, report)
    for entry in entries:
        dest = entry["destination"]
        result = {"name": entry["name"], "kind": entry["kind"], "destination": dest,
                  "stage": "prepared", "meshes": [], "elapsed_s": {}}
        report["results"].append(result)
        meshes = _meshes(dest)
        tags = _tags(entry)
        if meshes:
            if not all(all(EAL.get_metadata_tag(mesh,key) == value for key,value in tags.items()) for mesh in meshes):
                raise RuntimeError("existing revision metadata differs; no overwrite: " + dest)
            result["import_skipped"] = True
        else:
            task = unreal.AssetImportTask()
            task.filename = entry["fbx"]["path"]
            task.destination_path = dest
            task.destination_name = entry["name"]
            task.automated, task.replace_existing, task.save = True, False, False
            options = unreal.FbxImportUI()
            options.import_mesh, options.import_materials, options.import_textures = True, False, False
            options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
            data = options.static_mesh_import_data
            data.combine_meshes = False
            data.generate_lightmap_u_vs = False
            data.auto_generate_collision = False
            data.build_nanite = False
            data.vertex_color_import_option = unreal.VertexColorImportOption.REPLACE
            task.options = options
            result["stage"] = "import_pending"
            report["stage"] = "import_pending"
            _write(report_path, report)
            started = time.perf_counter()
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            result["elapsed_s"]["import"] = round(time.perf_counter()-started,6)
            result["imported_object_paths"] = [str(path) for path in task.imported_object_paths]
            meshes = _meshes(dest)
            result["import_skipped"] = False
        verified = _verify(entry, meshes)
        result["stage"] = "imported"
        report["imported_groups"] += 1
        _write(report_path, report)
        for source_name, mesh in verified.items():
            for index in range(len(mesh.get_editor_property("static_materials"))):
                mesh.set_material(index, material)
                if mesh.get_material(index) != material:
                    raise RuntimeError("material assignment readback differs: " + mesh.get_path_name())
            # Same owner fallback on owned terrain only; no walkability claim.
            if entry["kind"] == "island" and source_name.endswith("_island"):
                body = mesh.get_editor_property("body_setup")
                if body is not None:
                    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            for key,value in tags.items(): EAL.set_metadata_tag(mesh,key,value)
            row = {"path": mesh.get_path_name(), "source_name": source_name, "save_return": None,
                   "material_paths": [mesh.get_material(i).get_path_name() for i in range(len(mesh.get_editor_property("static_materials")))]}
            result["meshes"].append(row)
            result["stage"] = "save_pending"
            report["stage"] = "save_pending"
            _write(report_path, report)
            started = time.perf_counter()
            row["save_return"] = bool(EAL.save_loaded_asset(mesh, only_if_is_dirty=False))
            row["save_s"] = round(time.perf_counter()-started,6)
            _write(report_path, report)
            if not row["save_return"]:
                raise RuntimeError("asset save returned false: " + row["path"])
            if any(EAL.get_metadata_tag(mesh,key) != value for key,value in tags.items()):
                raise RuntimeError("saved source metadata differs: " + row["path"])
            report["saved_meshes"] += 1
        result["stage"] = "assets_saved_held_from_world"
        report["saved_groups"] += 1
        _write(report_path, report)
    report["stage"] = "assets_saved"
    _write(report_path, report)
    return report
