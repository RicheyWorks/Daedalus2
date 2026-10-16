"""ONE granted farm-bay operation in the existing Blender GUI, never a launcher.

Caller verifies fresh compute/native custody, physical/virtual floors and exact
source pins before run(). On unknown wire outcome retain custody and read state;
never dispatch this operation again. All output directories are exclusive.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time

HERE = Path(__file__).resolve().parent
GENERATOR = HERE / "sky_farm_greenhouse_one_bay_r1.py"
RECIPE = HERE / "sky_farm_greenhouse_one_bay_r1.recipe.json"


def pin(path):
    path = Path(path)
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def scene_digest(scene):
    rows = []
    for obj in sorted(scene.objects, key=lambda item: item.name):
        row = {"name": obj.name, "type": obj.type, "matrix": [list(v) for v in obj.matrix_world],
               "materials": [slot.material.name if slot.material else None for slot in obj.material_slots]}
        if obj.type == "MESH":
            row.update(vertices=[list(v.co) for v in obj.data.vertices], polygons=[list(p.vertices) for p in obj.data.polygons])
        if obj.type == "CAMERA":
            row["camera"] = [obj.data.lens, obj.data.clip_start, obj.data.clip_end]
        if obj.type == "LIGHT":
            row["light"] = [obj.data.type, obj.data.energy, list(obj.data.color)]
        rows.append(row)
    value = {"scene": scene.name, "objects": rows, "world": scene.world.name if scene.world else None,
             "camera": scene.camera.name if scene.camera else None,
             "units": [scene.unit_settings.system, scene.unit_settings.scale_length],
             "render": [scene.render.engine, scene.render.resolution_x, scene.render.resolution_y,
                        scene.render.resolution_percentage, scene.render.filepath]}
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def observe():
    """Supported read-only baseline; no bpy operators and no writes."""
    import bpy
    scene, layer = bpy.context.scene, bpy.context.view_layer
    return {"read_only": True, "run_called": False, "pid": os.getpid(),
            "version": bpy.app.version_string, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "scene_hashes": {s.name: scene_digest(s) for s in bpy.data.scenes},
            "context": {"scene": scene.name, "view_layer": layer.name,
                        "active": layer.objects.active.name if layer.objects.active else None,
                        "selected": sorted(o.name for o in scene.objects if o.select_get()),
                        "mode": bpy.context.mode, "filepath": bpy.data.filepath},
            "dirty_observed": bpy.data.is_dirty, "render_running": bpy.app.is_job_running("RENDER"),
            "exporter_properties": list(bpy.ops.export_scene.gltf.get_rna_type().properties.keys()),
            "save_copy_supported": "copy" in bpy.ops.wm.save_as_mainfile.get_rna_type().properties}


def save_snapshot(directory, record, sequence, previous):
    value = dict(record, sequence=sequence, previous_snapshot=previous,
                 observed_at_utc=datetime.now(timezone.utc).isoformat())
    raw = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    path = Path(directory) / (str(sequence).zfill(4) + ".json")
    fd, staged = tempfile.mkstemp(prefix=".receipt-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(staged, path)
        if path.read_bytes() != raw:
            raise RuntimeError("Snapshot readback mismatch; reconcile, do not replay")
    finally:
        os.unlink(staged)
    return pin(path)


def run(allocation_id, output_dir, baseline_path, expected_pins):
    import bpy
    if type(allocation_id) is not int or allocation_id <= 32852:
        raise ValueError("exact NEW accepted farm-bay allocation required")
    expected_paths = {str(p.resolve()) for p in (GENERATOR, RECIPE, Path(__file__), Path(baseline_path))}
    if (not isinstance(expected_pins, list) or len(expected_pins) != 4
            or {str(Path(p["path"]).resolve()) for p in expected_pins} != expected_paths
            or any(pin(p["path"]) != p for p in expected_pins)):
        raise ValueError("source/recipe/runner/baseline pins differ")
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    observed = observe()
    if (not baseline.get("read_only") or baseline.get("run_called") is not False
            or baseline["pid"] != observed["pid"] or baseline["context"] != observed["context"]
            or baseline["scene_hashes"] != observed["scene_hashes"]
            or observed["render_running"] or not observed["save_copy_supported"]
            or observed["context"]["mode"] != "OBJECT" or not bpy.context.window
            or any(s.name.startswith("Bld_SkyFarm_GreenhouseBay_R1") for s in bpy.data.scenes)):
        raise RuntimeError("Current session differs or prior farm attempt exists; preserve and reconcile")
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError("Prior attempt/output directory exists; no replay")
    spec = importlib.util.spec_from_file_location("sky_farm_bay_r1", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    recipe = module.load_recipe(RECIPE)
    source_stats = module.validate_geometry(recipe, module.geometry(recipe))
    output.mkdir(parents=True)
    receipt = output / "operation"
    receipt.mkdir()
    record = {"schema": "daedalus.sky-farm.existing-session.v1",
              "operation_id": "sky-farm-greenhouse-r1-" + str(allocation_id),
              "accepted_allocation_hub": allocation_id, "inputs": expected_pins,
              "started_at_utc": datetime.now(timezone.utc).isoformat(), "state": "ACCEPTED_NOT_STARTED",
              "process_launched": False, "process_exit_code": None, "existing_blender_pid": os.getpid(),
              "original_context": observed["context"], "dirty_before": observed["dirty_observed"],
              "world_binding": None, "native_accepted": False, "visual_accepted": False}
    sequence, last = 0, None

    def emit(state):
        nonlocal sequence, last
        record["state"] = state
        sequence += 1
        last = save_snapshot(receipt, record, sequence, last)

    window, original, layer = bpy.context.window, bpy.context.scene, bpy.context.view_layer
    active, selected = layer.objects.active, tuple(o for o in original.objects if o.select_get())
    started = time.monotonic()
    emit("ACCEPTED_NOT_STARTED")
    try:
        backup = output / "whole-session-before.blend"
        emit("STARTUP_COPY_DISPATCHING")
        status = bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
        if status != {"FINISHED"} or not backup.is_file() or bpy.data.filepath != observed["context"]["filepath"]:
            raise RuntimeError("Whole-session copy not confirmed; preserve state")
        record.update(startup_backup=pin(backup), startup_copy_result=sorted(status))
        emit("STARTUP_COPY_VERIFIED")
        scene = bpy.data.scenes.new(recipe["asset_id"])
        window.scene = scene
        record["scene"] = scene.name
        emit("ISOLATED_SCENE_BUILD_RUNNING")
        objects, stats = module.build(scene, recipe)
        if stats != source_stats or len([o for o in objects if o.type == "MESH"]) != stats["mesh_count"]:
            raise RuntimeError("Built membership/statistics differ from tested source")
        for obj in scene.objects:
            obj.select_set(False)
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        source = output / (recipe["asset_id"] + ".blend")
        emit("SOURCE_COPY_DISPATCHING")
        status = bpy.ops.wm.save_as_mainfile(filepath=str(source), copy=True)
        if status != {"FINISHED"} or not source.is_file():
            raise RuntimeError("Source copy not confirmed")
        record.update(source=pin(source), source_copy_result=sorted(status))
        glb = output / (recipe["asset_id"] + ".glb")
        options = {"filepath": str(glb), "export_format": "GLB", "use_selection": True,
                   "use_active_scene": True, "export_apply": True, "export_yup": True,
                   "export_materials": "EXPORT", "export_extras": True,
                   "export_cameras": False, "export_lights": False, "export_animations": False}
        properties = bpy.ops.export_scene.gltf.get_rna_type().properties
        if any(key not in properties for key in options):
            raise RuntimeError("Installed exporter lacks required isolated-scene options")
        record["export_options"] = options
        emit("SELECTED_ACTIVE_SCENE_GLB_DISPATCHING")
        status = bpy.ops.export_scene.gltf(**options)
        if status != {"FINISHED"} or not glb.is_file():
            raise RuntimeError("Selected GLB not confirmed")
        record.update(glb=pin(glb), glb_operator_result=sorted(status), statistics=stats,
                      payload_objects=[{"name": o.name, "type": o.type, "role": o.get("role", o.get("socket_role")),
                                        "materials": [m.name for m in o.data.materials] if o.type == "MESH" else []}
                                       for o in objects])
        hero = output / "hero.png"
        scene.render.filepath = str(hero)
        emit("SOURCE_EXPORTED_HERO_RUNNING")
        status = bpy.ops.render.render(write_still=True)
        if status != {"FINISHED"} or not hero.is_file():
            raise RuntimeError("Hero not confirmed")
        record.update(hero=pin(hero), render_operator_result=sorted(status), settings=recipe["render"])
        manifest = {"schema": "daedalus.sky-farm.module-delivery.v1", "asset_id": recipe["asset_id"],
                    "operation_id": record["operation_id"], "allocation_id": allocation_id,
                    "units": "metres", "pivot": "bottom-centre (0,0,0)", "forward": "-Y",
                    "nominal_greenhouse_dimensions_m": [recipe["width"],recipe["length"],recipe["ridge_height"]],
                    "dimension_scope": "statistics.bounds_m includes rafters/ridge and path aprons; use these bounds for fit",
                    "statistics": stats, "payload_objects": record["payload_objects"],
                    "socket_positions_m": module.socket_positions(recipe),
                    "material_factors_raw_linear_rgba": module.PALETTE, "inputs": expected_pins,
                    "source": record["source"], "glb": record["glb"], "hero": record["hero"],
                    "render": recipe["render"], "catalogue_reference": recipe["catalogue_reference"],
                    "platform_proxy_exported": False, "world_binding": None,
                    "qualification": "Authored static module only; native fit/materials/collision/navigation/gameplay unverified"}
        manifest_path=output/"manifest.json"
        with manifest_path.open("x",encoding="utf-8") as stream:
            json.dump(manifest,stream,indent=2,allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        record["manifest"]=pin(manifest_path)
        emit("SOURCE_HERO_CREATED_REVIEW_PENDING")
    except Exception as error:
        record["error"] = type(error).__name__ + ": " + str(error)
        record["state"] = "TERMINAL_FAILED_PARTIAL_OUTPUTS_RECONCILE"
        raise
    finally:
        window.scene, window.view_layer = original, layer
        record["retained_scene_hashes"] = {name: scene_digest(bpy.data.scenes[name]) for name in baseline["scene_hashes"]}
        record["retained_scenes_preserved"] = record["retained_scene_hashes"] == baseline["scene_hashes"]
        record["original_context_restored"] = (
            bpy.context.scene == original and bpy.context.view_layer == layer and layer.objects.active == active
            and tuple(o for o in original.objects if o.select_get()) == selected
            and bpy.context.mode == observed["context"]["mode"] and bpy.data.filepath == observed["context"]["filepath"])
        record["dirty_after"] = bpy.data.is_dirty
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        record["seconds"] = round(time.monotonic()-started, 3)
        if not record["retained_scenes_preserved"] or not record["original_context_restored"]:
            state = "TERMINAL_CONTEXT_RECONCILIATION_REQUIRED"
        elif record["state"] == "SOURCE_HERO_CREATED_REVIEW_PENDING":
            state = "TERMINAL_SOURCE_HERO_CREATED_REVIEW_PENDING"
        else:
            state = record["state"]
        emit(state)
    if record["state"] != "TERMINAL_SOURCE_HERO_CREATED_REVIEW_PENDING":
        raise RuntimeError("Operation needs reconciliation, do not replay")
    return dict(record, terminal_snapshot=last)
