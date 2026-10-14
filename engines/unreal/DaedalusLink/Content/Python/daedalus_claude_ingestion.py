# SPDX-License-Identifier: MIT
"""Bounded, saved-receipt orchestration around Claude's working FBX importer.

Owner entry point: import_saved_batch([240, 241, 242]). This imports/saves owned
assets only. It never places actors, clears deeds, changes import backends or
enables plugins. Start only between the current owner's legacy import jobs.
"""
import hashlib
import inspect
import marshal
from pathlib import Path

import unreal
import daedalus_claude_islands as islands
import daedalus_ingestion_receipts as receipts


MAX_BATCH = 3
SETTINGS = {
    "preset": "claude_voxel_fbx_existing_options_v1",
    "automated": True, "replace_existing": True, "task_save": False,
    "async": False, "import_materials": False, "import_textures": False,
    "import_as_skeletal": False, "import_mesh": True, "combine_meshes": False,
    "generate_lightmap_u_vs": False, "auto_generate_collision": False,
    "build_nanite": False, "vertex_color_import_option": "REPLACE",
    "material": islands.MAT, "roughness": 0.9,
    "collision": "existing simple collision or complex-as-simple body fallback",
    "postprocessor": "daedalus_claude_islands.import_island",
}


def _backend():
    # Read controls only. Zero can also mean an unregistered cvar, so this is
    # readback identity, not a claim that a particular backend is disabled.
    return {"entrypoint": "AssetImportTask/FbxImportUI",
            "interchange_class_present": hasattr(unreal, "InterchangeManager"),
            "fbx_cvar_readback": unreal.SystemLibrary.get_console_variable_int_value(
                "Interchange.FeatureFlags.Import.FBX"),
            "fbx_worker_cvar_readback": unreal.SystemLibrary.get_console_variable_int_value(
                "Interchange.FeatureFlags.Translator.UseWorker.FBX"),
            "loaded_importer_code": {
                name: hashlib.sha256(marshal.dumps(getattr(islands, name).__code__)).hexdigest()
                for name in ("import_island", "material", "_simple_collision")},
            "loaded_orchestration_code": {
                function.__module__ + "." + function.__name__: hashlib.sha256(marshal.dumps(function.__code__)).hexdigest()
                for function in (import_saved_batch, _manifest, _destination_matches, receipts.fingerprint,
                                 receipts.manifest, receipts.validate_receipt, receipts.write_receipt,
                                 receipts.verified_snapshot, receipts.may_skip, receipts.require_retry_permission)}}


def _package_file(path):
    package = path.split(".", 1)[0]
    if not package.startswith(islands.ROOT + "/"):
        raise ValueError("asset outside the owned Claude island namespace: " + path)
    return Path(unreal.Paths.project_content_dir()) / (package[len("/Game/"):] + ".uasset")


def _dirty_packages():
    return {package.get_name() for package in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def _pipeline_observation(mesh):
    """Read saved import-data provenance; unavailable observations stay explicit."""
    try:
        data = mesh.get_editor_property("asset_import_data")
        if data is None:
            return {"state": "absent"}
        pipelines = data.get_pipelines() if hasattr(data, "get_pipelines") else None
        return {"state": "observed", "import_data_class": data.get_class().get_path_name(),
                "pipeline_classes": [pipeline.get_class().get_path_name() for pipeline in pipelines]
                if pipelines is not None else None}
    except Exception as error:
        return {"state": "unavailable", "error": str(error)}


def _destination_matches(path, witness, dirty):
    return (unreal.EditorAssetLibrary.does_asset_exist(path)
            and path.split(".", 1)[0] not in dirty
            and _package_file(path).is_file()
            and receipts.fingerprint(_package_file(path)) == witness)


def _manifest(seed, dependencies):
    source = Path(islands.GLB_DIR) / ("Island_C%d.fbx" % seed)
    return receipts.manifest(source, islands.ROOT + "/Island_C%d" % seed,
                             SETTINGS, unreal.SystemLibrary.get_engine_version(),
                             _backend(), dependencies)


def import_saved_batch(seeds, dependencies=(), force=False, retry_uncertain=False):
    """Import at most three islands and return saved assets per item.

    Resume repeats this same entry point: completed items skip only with matching
    inputs and native/disk outputs. An interrupted/mutating item stops by default.
    Explicit retry_uncertain requires the owner to inspect the previous outcome;
    it performs a fresh import, never infers that dirty assets were saved.
    """
    seeds = list(seeds)
    if type(force) is not bool or type(retry_uncertain) is not bool:
        raise ValueError("force and retry_uncertain must be explicit booleans")
    if any(isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2147483647 for seed in seeds):
        raise ValueError("island seeds must be nonnegative 32-bit integers")
    if not 1 <= len(seeds) <= MAX_BATCH or len(set(seeds)) != len(seeds):
        raise ValueError("supply one to three distinct island seeds")
    if not {"source_file", "on_imported"}.issubset(inspect.signature(islands.import_island).parameters):
        raise RuntimeError("snapshot/callback importer seam is not loaded; owner must load the reviewed source between jobs")
    dependencies = list(dependencies) + [__file__, islands.__file__, receipts.__file__]
    config_root = Path(unreal.Paths.project_dir()) / "Config"
    dependencies += [path for path in (config_root / "DefaultEngine.ini", config_root / "DefaultEditor.ini") if path.is_file()]
    if len(dependencies) > 32:
        raise ValueError("at most 32 dependencies including code and project defaults")
    # Preflight every input before the first asset mutation.
    manifests = {seed: _manifest(seed, dependencies) for seed in seeds}
    if any(value["source"]["bytes"] == 0 for value in manifests.values()):
        raise ValueError("empty FBX input; no import performed")
    root = Path(unreal.Paths.project_saved_dir()) / "Daedalus" / "Ingestion" / "ClaudeIslands"
    results = []
    with receipts.exclusive_batch(root):
        for seed in seeds:
            name, manifest = "Island_C%d" % seed, manifests[seed]
            key = receipts.manifest_key(manifest)
            receipt_path = root / "receipts" / (name + ".json")
            previous = receipts.read_receipt(receipt_path)
            receipts.require_retry_permission(previous, retry_uncertain)
            dirty = _dirty_packages()
            destination = manifest["destination"]
            if any(package == islands.MAT or package.startswith(destination + "/") for package in dirty):
                raise RuntimeError("owned destination/material has unsaved edits; owner must reconcile them before ingestion")
            if not force and receipts.may_skip(previous, key, lambda path, witness: _destination_matches(path, witness, dirty)):
                results.append({"seed": seed, "state": "saved", "unchanged_skipped": True,
                                "key": key, "assets": previous["assets"], "receipt": str(receipt_path)})
                continue
            record = {"schema": receipts.SCHEMA, "seed": seed, "key": key, "manifest": manifest,
                      "state": "input_verified", "save_confirmed": False, "started_utc": receipts.utc_now(),
                      "api": {"import": "AssetTools.import_asset_tasks/AssetImportTask/FbxImportUI",
                              "postprocess": "daedalus_claude_islands.import_island",
                              "save": "EditorAssetLibrary.save_loaded_assets"},
                      "import_call_completed": False, "postprocess_completed": False,
                      "save_call_completed": False, "background_compilation": "not_queried"}
            receipts.write_receipt(receipt_path, record)

            def state(value, **fields):
                record.update(fields)
                record.update(state=value, updated_utc=receipts.utc_now())
                receipts.write_receipt(receipt_path, record)

            try:
                expected = {field: manifest["source"][field] for field in ("sha256", "bytes")}
                snapshot = receipts.verified_snapshot(manifest["source"]["path"], expected,
                                                     root / "snapshots" / key[:24])
                state("import_started", snapshot=snapshot)
                assets = islands.import_island(seed, force=True, save=False, source_file=snapshot,
                                               on_imported=lambda paths: state("imported", imported_paths=paths,
                                                                               import_call_completed=True))
                if not ("body" in assets or "island" in assets):
                    raise RuntimeError("import returned no body; no saved receipt")
                if any(not path.startswith(manifest["destination"] + "/") for path in assets.values()):
                    raise RuntimeError("import returned an asset outside this item's destination")
                paths = sorted(set(assets.values()) | {islands.MAT})
                if not all(unreal.EditorAssetLibrary.does_asset_exist(path) for path in paths):
                    raise RuntimeError("postprocessed asset is missing")
                state("postprocessed", assets=assets, postprocess_completed=True)
                loaded = [unreal.EditorAssetLibrary.load_asset(path) for path in paths]
                if any(asset is None for asset in loaded):
                    raise RuntimeError("postprocessed asset could not be loaded")
                state("postprocessed", pipeline_observations={
                    path: _pipeline_observation(asset) for path, asset in zip(paths, loaded)
                    if path in assets.values()})
                state("save_started")
                if unreal.EditorAssetLibrary.save_loaded_assets(loaded, only_if_is_dirty=True) is not True:
                    raise RuntimeError("explicit item asset save did not confirm success")
                state("save_started", save_call_completed=True)
                if receipts.fingerprint(snapshot) != expected:
                    raise RuntimeError("import snapshot changed; inspect saved outcome")
                # A concurrent source/config change never earns a matching saved key.
                if _manifest(seed, dependencies) != manifest:
                    raise RuntimeError("source/importer/settings changed during delivery; inspect saved outcome")
                dirty = _dirty_packages()
                outputs = {}
                for path in paths:
                    if (not unreal.EditorAssetLibrary.does_asset_exist(path) or not _package_file(path).is_file()
                            or path.split(".", 1)[0] in dirty):
                        raise RuntimeError("saved output is absent from registry or disk")
                    outputs[path] = receipts.fingerprint(_package_file(path))
                state("saved", save_confirmed=True, outputs=outputs, saved_utc=receipts.utc_now())
                results.append({"seed": seed, "state": "saved", "unchanged_skipped": False,
                                "key": key, "assets": assets, "receipt": str(receipt_path)})
            except Exception as error:
                failed_state = "input_failed" if record["state"] == "input_verified" else "uncertain"
                # Persist uncertainty before propagating; earlier saved items remain resumable.
                state(failed_state, save_confirmed=False, failed_from=record["state"], error=str(error))
                raise
    return results
