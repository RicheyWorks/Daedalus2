# SPDX-License-Identifier: MIT
"""Owner-run saved receipts around the actual Codex prepared-asset importer.

Loads a private copy of the reviewed importer; never changes its working file,
globals in another caller, Claude destinations, material, or placement logic.
Use the existing daedalus.steps owner runner; each yield follows one saved item.
"""
import copy
import hashlib
import importlib.util
import inspect
import json
import marshal
import math
from pathlib import Path
import re
import time

import unreal
import daedalus_ingestion_receipts as receipts


OWNED_ROOT = "/Game/Daedalus/Art/Islands/CodexContest"
MAX_BATCH = 3


def _load_importer(path, expected_sha256):
    path = Path(path).resolve()
    if path.name != "daedalus_codex_prepared_assets.py" or not re.fullmatch("[0-9a-f]{64}", expected_sha256):
        raise ValueError("supply the reviewed Codex importer path and full source SHA256")
    if path.stat().st_size > 1048576:
        raise ValueError("oversized importer source")
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != expected_sha256:
        raise ValueError("importer source differs from the accepted owner revision")
    spec = importlib.util.spec_from_file_location("_codex_ingestion_backend_" + expected_sha256[:16], path)
    module = importlib.util.module_from_spec(spec)
    # Execute the verified bytes, never a timestamp/size-valid stale .pyc.
    exec(compile(source, str(path), "exec"), module.__dict__)
    if module.ROOT != OWNED_ROOT or "asset_names" not in inspect.signature(module.import_all).parameters:
        raise ValueError("unsupported owner importer contract; fallback remains untouched")
    if receipts.fingerprint(path)["sha256"] != expected_sha256:
        raise ValueError("importer changed while loading")
    return module


def _file(path):
    package = path.split(".", 1)[0]
    if not package.startswith("/Game/"):
        raise ValueError("only project assets are supported")
    return Path(unreal.Paths.project_content_dir()) / (package[len("/Game/"):] + ".uasset")


def _dirty():
    return {package.get_name() for package in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def _backend(native):
    return {"api": "AssetTools.import_asset_tasks/AssetImportTask/FbxImportUI",
            "selected_preset": "codex_prepared_existing_options_v1",
            "fbx_cvar_readback": unreal.SystemLibrary.get_console_variable_int_value("Interchange.FeatureFlags.Import.FBX"),
            "loaded_code": {name: hashlib.sha256(marshal.dumps(getattr(native, name).__code__)).hexdigest()
                            for name in ("import_all", "_verify", "_tags", "_observed_import")},
            "loaded_receipt_code": {
                function.__module__ + "." + function.__name__: hashlib.sha256(marshal.dumps(function.__code__)).hexdigest()
                for function in (import_steps, _manifest, _verify_saved, receipts.manifest,
                                 receipts.validate_receipt, receipts.write_receipt, receipts.verified_snapshot,
                                 receipts.may_skip, receipts.require_retry_permission)}}


def _manifest(entry, source_manifest, native, namespace, dependencies):
    settings = {"preset": "codex_prepared_existing_options_v1",
                "requested_import_options": source_manifest["import_options"],
                "material": native.MATERIAL, "shared_material_policy": "read-only reuse",
                "name": entry["name"], "kind": entry["kind"], "seed": entry["seed"],
                "config_sha256": entry["config_sha256"], "objects": entry["objects"],
                "namespace": namespace, "placement": False}
    return receipts.manifest(entry["fbx"]["path"], namespace, settings,
                             unreal.SystemLibrary.get_engine_version(), _backend(native), dependencies)


def _verify_saved(native, entry, record, dirty, destination):
    if record.get("destination") != destination:
        return False
    paths = list(record["assets"].values())
    for path, witness in record["outputs"].items():
        if (not path.startswith(destination + "/") or not native.EAL.does_asset_exist(path)
                or path.split(".", 1)[0] in dirty or not _file(path).is_file()
                or receipts.fingerprint(_file(path)) != witness):
            return False
    meshes = [native.EAL.load_asset(path) for path in paths]
    if any(not isinstance(mesh, unreal.StaticMesh) for mesh in meshes):
        return False
    native._verify(entry, meshes)       # Retain single-object alias/bounds contract.
    tags, material = native._tags(entry), native.EAL.load_asset(native.MATERIAL)
    for mesh in meshes:
        if any(native.EAL.get_metadata_tag(mesh, key) != value for key, value in tags.items()):
            return False
        if any(mesh.get_material(i) != material for i in range(len(mesh.get_editor_property("static_materials")))):
            return False
    return True


def import_steps(manifest_path, asset_names, importer_file, expected_importer_sha256,
                 namespace=None, deadline_epoch=None, retry_uncertain=False, dependencies=()):
    """At most three existing prepared entries, with an editor tick between them.

    The owner's exact24 manifest remains the backend contract. A private manifest
    changes only the admitted entry's immutable source/destination. Existing
    prepared receipts and47 saved assets are preserved. No world operation.
    """
    names = list(asset_names)
    if (not 1 <= len(names) <= MAX_BATCH or any(not isinstance(name, str) for name in names)
            or len(set(names)) != len(names)):
        raise ValueError("select one to three distinct prepared asset names")
    if type(retry_uncertain) is not bool:
        raise ValueError("retry_uncertain must be an explicit boolean")
    if deadline_epoch is not None and (isinstance(deadline_epoch, bool)
            or not isinstance(deadline_epoch, (int, float)) or not math.isfinite(deadline_epoch)):
        raise ValueError("deadline must be a finite epoch")
    namespace = namespace or OWNED_ROOT + "/Ingestion"
    if (not namespace.startswith(OWNED_ROOT + "/")
            or any(not re.fullmatch("[A-Za-z0-9_]+", part) for part in namespace.split("/")[1:])):
        raise ValueError("revision namespace must remain under CodexContest")
    if Path(manifest_path).stat().st_size > 1048576:
        raise ValueError("oversized prepared manifest")
    source_manifest_witness = receipts.fingerprint(manifest_path)
    source_manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if receipts.fingerprint(manifest_path) != source_manifest_witness:
        raise ValueError("prepared manifest changed while reading")
    entries = source_manifest.get("assets", [])
    if (source_manifest.get("schema") != "daedalus.codex-prepared-delivery.v1" or len(entries) != 24
            or len({entry["name"] for entry in entries}) != 24):
        raise ValueError("preserve the owner's exact24 prepared manifest")
    by_name = {entry["name"]: entry for entry in entries}
    if not set(names).issubset(by_name):
        raise ValueError("unknown prepared selection")
    native = _load_importer(importer_file, expected_importer_sha256)
    material = native.EAL.load_asset(native.MATERIAL)
    if not isinstance(material, unreal.MaterialInterface) or not _file(native.MATERIAL).is_file():
        raise RuntimeError("shared read-only material is not loaded and saved")
    dependencies = list(dependencies) + [__file__, receipts.__file__, native.__file__, manifest_path, _file(native.MATERIAL)]
    config = Path(unreal.Paths.project_dir()) / "Config"
    dependencies += [path for path in (config / "DefaultEngine.ini", config / "DefaultEditor.ini") if path.is_file()]
    manifests = {name: _manifest(by_name[name], source_manifest, native, namespace, dependencies) for name in names}
    if receipts.fingerprint(manifest_path) != source_manifest_witness:
        raise ValueError("prepared manifest changed during preflight")
    for entry in entries:
        expected = {field: entry["fbx"][field] for field in ("sha256", "bytes")}
        if receipts.fingerprint(entry["fbx"]["path"]) != expected:
            raise ValueError("prepared input changed before admission: " + entry["name"])
        if not entry["destination"].startswith(OWNED_ROOT + "/"):
            raise ValueError("original manifest contains an unowned destination")
    root = Path(unreal.Paths.project_saved_dir()) / "Daedalus" / "Ingestion" / "CodexContest"
    with receipts.exclusive_batch(root):
        for name in names:
            if deadline_epoch is not None and time.time() >= deadline_epoch - 90:
                return {"state": "window_paused", "remaining_from": name}
            entry, manifest = by_name[name], manifests[name]
            if _manifest(entry, source_manifest, native, namespace, dependencies) != manifest:
                raise RuntimeError("admitted source/settings/dependencies changed between editor ticks; no item started")
            key = receipts.manifest_key(manifest)
            destination = namespace + "/" + key[:24]
            receipt_path = root / "receipts" / (key[:24] + ".json")
            # One stable item gate also blocks unknown outcomes after a key changes.
            gate_path = root / "items" / (hashlib.sha256(name.encode()).hexdigest()[:24] + ".json")
            gate = receipts.read_receipt(gate_path)
            receipts.require_retry_permission(gate, retry_uncertain)
            previous = receipts.read_receipt(receipt_path)
            dirty = _dirty()
            if native.MATERIAL.split(".", 1)[0] in dirty:
                raise RuntimeError("shared material has unsaved edits; no save/mutation of it is authorized")
            if any(package.startswith(destination + "/") for package in dirty):
                raise RuntimeError("owned revision has unsaved edits; inspect before ingestion")
            if previous and previous["state"] == "saved" and receipts.may_skip(
                    previous, key, lambda path, witness: (native.EAL.does_asset_exist(path)
                    and path.split(".", 1)[0] not in dirty and _file(path).is_file()
                    and receipts.fingerprint(_file(path)) == witness)):
                if not _verify_saved(native, entry, previous, dirty, destination):
                    raise RuntimeError("saved metadata/material/geometry changed; no automatic overwrite")
                if _manifest(entry, source_manifest, native, namespace, dependencies) != manifest:
                    raise RuntimeError("source/dependencies changed while verifying an unchanged skip")
                yield {"name": name, "state": "saved", "unchanged_skipped": True,
                       "receipt": str(receipt_path), "assets": previous["assets"]}
                continue
            if native.EAL.does_directory_exist(destination) and not retry_uncertain:
                raise RuntimeError("revision exists without matching saved proof; inspect before reuse")
            record = {"schema": receipts.SCHEMA, "key": key, "manifest": manifest, "name": name,
                      "state": "input_verified", "save_confirmed": False, "started_utc": receipts.utc_now(),
                      "destination": destination, "backend_source": native.__file__,
                      "backend_source_sha256": expected_importer_sha256,
                      "api": "native.import_all -> AssetImportTasks/FbxImportUI -> SaveLoadedAsset",
                      "background_compilation": "not_queried", "world_placed": 0}

            def state(value, **fields):
                record.update(fields)
                record.update(state=value, updated_utc=receipts.utc_now())
                receipts.write_receipt(gate_path, record)
                receipts.write_receipt(receipt_path, record)

            state("input_verified")
            try:
                expected = {field: entry["fbx"][field] for field in ("sha256", "bytes")}
                work = root / "native" / key[:24]
                snapshot = receipts.verified_snapshot(entry["fbx"]["path"], expected, work / "input")
                private = copy.deepcopy(source_manifest)
                admitted = next(item for item in private["assets"] if item["name"] == name)
                admitted["fbx"]["path"], admitted["destination"] = snapshot, destination
                private_path, report_path = work / "manifest.json", work / "native.json"
                receipts.write_receipt(private_path, private)
                state("import_started", snapshot=snapshot, native_report=str(report_path))
                report = native.import_all(str(private_path), str(report_path), deadline_epoch, [name])
                if report["stage"] == "window_paused" and not report["results"]:
                    state("input_failed", reason="owner deadline reached before any item mutation")
                    return {"state": "window_paused", "remaining_from": name}
                if report["stage"] != "assets_saved" or report["saved_groups"] != 1 or len(report["results"]) != 1:
                    raise RuntimeError("owner native import did not return one saved group")
                result = report["results"][0]
                if result["destination"] != destination or not result["meshes"]:
                    raise RuntimeError("native saved destination/mesh proof differs")
                if any(row["save_return"] is not True for row in result["meshes"]):
                    raise RuntimeError("native save did not confirm every mesh")
                assets = {row["source_name"]: row["path"] for row in result["meshes"]}
                state("postprocessed", assets=assets, native_result=result, save_call_completed=True)
                if (receipts.fingerprint(snapshot) != expected
                        or _manifest(entry, source_manifest, native, namespace, dependencies) != manifest):
                    raise RuntimeError("source/snapshot/settings/dependencies changed during delivery")
                dirty = _dirty()
                outputs = {path: receipts.fingerprint(_file(path)) for path in assets.values()}
                record["outputs"] = outputs
                if native.MATERIAL.split(".", 1)[0] in dirty or not _verify_saved(native, entry, record, dirty, destination):
                    raise RuntimeError("saved native/disk/metadata/material/geometry proof differs")
                state("saved", save_confirmed=True, saved_utc=receipts.utc_now())
                yield {"name": name, "state": "saved", "unchanged_skipped": False,
                       "receipt": str(receipt_path), "assets": assets}
            except Exception as error:
                failed_from = record["state"]
                state("input_failed" if failed_from == "input_verified" else "uncertain",
                      save_confirmed=False, failed_from=failed_from, error=str(error))
                raise
