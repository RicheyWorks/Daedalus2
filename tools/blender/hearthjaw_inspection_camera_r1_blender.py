"""File-only by default; future ONE background COPY inspection, never a GUI caller.

Execution needs a separate resource/operation authorization; --execute is not a
grant. No live camera/bounds or image-quality evidence exists from source tests.
API references (4.3.1): source/creator/creator_args.cc; windowmanager/intern/
wm_files.cc (open_mainfile use_scripts/load_ui, save_as_mainfile relative_remap);
makesrna/intern/rna_object_api.cc (evaluated_get/visible_get). Official sources:
https://github.com/blender/blender/tree/v4.3.1/source/blender
Retained producer mechanics: realm_ecology_pack.render / premium_transit_pack.setup.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import sys
import types

CALLER = "hearthjaw_inspection_camera_r1_blender.py"
FROZEN = {
    "hearthjaw_inspection_camera_r1.py": (10958, "c035f66188ca4f0e9b873861e5b8656223989fcd079cd8715e45273a3d177bbb"),
    "hearthjaw_inspection_camera_r1.recipe.json": (5002, "4da06be276a72e9bfbb0ffe44c00576d556378000a619ed724de38dce3c4ea5c"),
    "hearthjaw_inspection_camera_r1_test.py": (11106, "eeda9fc7a52f974e589d37cd703799b007d9704a11cff251ab475eaed03c27b3"),
}
PROPOSAL = {"directory": "artifacts/ecology/sky-botanical-pilot-r1/inspection/hearthjaw-camera-r1",
            "image": "hearthjaw_inspection_r1.png", "scene": "hearthjaw_inspection_r1.blend", "approved": False}
PRESENTATION = "artifacts/ecology/sky-botanical-pilot-r1/jobs/sky_hearthjaw/sky/sky_Ecology_Presentation.blend"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(path, missing=False, lstat=None):
    """Inspect ancestors BEFORE resolution; reject symlinks AND Windows junctions.

    This is a local admission check, not race-proof containment against another
    writer replacing directories during the operation. External custody remains required.
    """
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "absolute unambiguous path required")
    inspect = lstat or os.lstat
    for part in reversed((path, *path.parents)):
        try:
            info = inspect(part)
        except FileNotFoundError:
            require(missing, "required path missing: " + str(part))
            continue
        require(not stat.S_ISLNK(info.st_mode)
                and not (getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT),
                "symlink/reparse path refused: " + str(part))
        require(part == path or stat.S_ISDIR(info.st_mode), "non-directory ancestor")
    return path


def checked_bytes(path, size, sha):
    path = safe_path(path)
    require(path.is_file(), "regular pinned file required")
    raw = path.read_bytes()
    require(len(raw) == size and digest(raw) == sha, "pinned file changed: " + str(path))
    return raw


def output_plan(presentation, proposal):
    require(proposal == PROPOSAL, "unknown output proposal")
    presentation = safe_path(presentation)
    require(len(presentation.parents) >= 7, "presentation layout differs")
    project = presentation.parents[6]
    require(project / PRESENTATION == presentation, "canonical presentation path differs")
    root = project / PROPOSAL["directory"]
    safe_path(root.parent.parent)
    safe_path(root, missing=True)
    require(not os.path.lexists(root), "inspection root exists; no overwrite/replay")
    return {"root": root, "copy": root / "retained_presentation_copy.blend",
            "scene": root / PROPOSAL["scene"], "image": root / PROPOSAL["image"],
            "receipt": root / "hearthjaw_inspection_r1.receipt.json"}


def preflight(here=None):
    here = safe_path(Path(here or __file__).absolute())
    require(here.name == CALLER, "caller filename differs")
    raw = {name: checked_bytes(here.parent / name, *pin) for name, pin in FROZEN.items()}
    recipe = json.loads(raw["hearthjaw_inspection_camera_r1.recipe.json"])
    require(recipe.get("source_only") is True and recipe.get("runtime_ready") is False
            and recipe.get("render_authorized") is False, "recipe is not the frozen source proposal")
    require(len(recipe["input_pins"]) == 3 and len(recipe["frozen_source_pins"]) == 6,
            "exact three canonical and six producer inputs required")
    for pin in recipe["input_pins"] + recipe["frozen_source_pins"]:
        checked_bytes(Path(pin["path"]), pin["bytes"], pin["sha256"])
    paths = output_plan(Path(recipe["input_pins"][0]["path"]), recipe["future_output_proposal"])
    return {"caller": here, "caller_sha256": digest(here.read_bytes()), "recipe": recipe,
            "helper_bytes": raw["hearthjaw_inspection_camera_r1.py"], "paths": paths}


def launch_prefix(here):
    return ["--background", "--factory-startup", "--disable-autoexec", "--threads", "1",
            "--python-exit-code", "2", "--python", str(here)]


def require_launch(prefix, state, sha):
    require(prefix == launch_prefix(state["caller"]), "exact background/factory/autoexec-disabled command required")
    require(sha == state["caller_sha256"], "explicit exact caller SHA256 required")


def copy_presentation(source, target):
    """Only ordinary file copying; target must be fresh, even on failed attempts."""
    raw = checked_bytes(Path(source["path"]), source["bytes"], source["sha256"])
    target = safe_path(target, missing=True)
    require(not os.path.lexists(target), "presentation copy exists; no overwrite")
    with target.open("xb") as out:
        out.write(raw)
    checked_bytes(target, source["bytes"], source["sha256"])


def staged_inventory(rows, plants):
    """Validate collected metadata; never synthesize a live observation."""
    expected = {name: ("plant", stage) for stage, name in enumerate(plants)}
    for base, role in (("Habitat_Platform", "pedestal"), ("Platform_Edge", "rim")):
        expected.update({base + (".%03d" % stage if stage else ""): (role, stage) for stage in range(3)})
    expected["Presentation_Floor"] = ("background", None)
    require(isinstance(rows, list) and all(isinstance(r, dict) and isinstance(r.get("name"), str)
            and isinstance(r.get("type"), str) for r in rows)
            and len({r["name"] for r in rows}) == len(rows), "distinct named inventory required")
    meshes = [row for row in rows if row["type"] == "MESH"]
    require({row["name"] for row in meshes} == set(expected), "exact nine staged meshes plus floor required")
    require(all(row["type"] in ("MESH", "CAMERA", "LIGHT", "EMPTY") for row in rows),
            "unassigned renderable object type")
    result = []
    for row in meshes:
        require(row["visible_render"] is True, "hidden staged mesh unsupported")
        role, stage = expected[row["name"]]
        corners = row["world_corners"]
        require(len(corners) == 8 and all(len(v) == 3 and all(type(x) in (int, float)
                and math.isfinite(x) for x in v) for v in corners), "eight finite evaluated world corners required")
        result.append(dict(name=row["name"], role=role, stage=stage, world_corners=corners))
    return result


def check_quality(q):
    require(q["engine"] == "CYCLES" and q["device"] == "CPU" and q["samples"] == 40
            and q["threads_mode"] == "FIXED" and q["threads"] == 1,
            "existing CPU1/40-sample settings required; caller will not change quality")
    require(q["resolution"] == [1800, 1400] and q["percentage"] == 100 and q["full_frame"]
            and q["format"] == "PNG" and q["metres"] is True, "unsupported output/units")


def atom(value):
    if type(value) in (str, bool, int) or value is None:
        return value
    if type(value) is float:
        require(math.isfinite(value), "nonfinite witness field")
        return value
    if isinstance(value, set):
        return sorted(value)
    return [atom(v) for v in value]


def scalars(value, omit=()):
    skip = {"rna_type", "is_updated", "is_updated_data", "is_evaluated", "is_runtime_data", *omit}
    return {p.identifier: atom(getattr(value, p.identifier)) for p in value.bl_rna.properties
            if p.identifier not in skip and p.type in ("BOOLEAN", "INT", "FLOAT", "STRING", "ENUM")}


def nodes(tree):
    if tree is None:
        return None
    return {"nodes": [{"name": n.name, "fields": scalars(n),
                       "inputs": [(s.identifier, atom(s.default_value)) for s in n.inputs
                                  if hasattr(s, "default_value") and s.type != "SHADER"]}
                      for n in sorted(tree.nodes, key=lambda n: n.name)],
            "links": sorted((l.from_node.name, l.from_socket.identifier,
                             l.to_node.name, l.to_socket.identifier) for l in tree.links)}


def field_witness(scene):
    """Recorded fields only, NOT full semantic equality of arbitrary Blender data."""
    objects = []
    for obj in sorted(scene.objects, key=lambda o: o.name):
        matrix = [list(row) for row in obj.matrix_world]
        if obj == scene.camera:
            matrix = [row[:3] for row in matrix[:3]]  # translation is the allowed camera change
        row = {"name": obj.name, "type": obj.type, "matrix": matrix,
               "scale": list(obj.scale), "hide_render": obj.hide_render}
        if obj.type == "MESH":
            geometry = {"vertices": [list(v.co) for v in obj.data.vertices],
                        "faces": [(list(p.vertices), p.material_index, p.use_smooth) for p in obj.data.polygons]}
            row.update(geometry_sha256=digest(json.dumps(geometry, allow_nan=False).encode()),
                       materials=[m.name if m else None for m in obj.data.materials])
        if obj.type in ("CAMERA", "LIGHT"):
            row["data"] = scalars(obj.data, ("ortho_scale",) if obj == scene.camera else ())
        objects.append(row)
    materials = {m.name: m for o in scene.objects if o.type == "MESH" for m in o.data.materials if m}
    return {"objects": objects,
            "materials": {name: {"fields": scalars(m), "nodes": nodes(m.node_tree)} for name, m in sorted(materials.items())},
            "world": {"fields": scalars(scene.world), "nodes": nodes(scene.world.node_tree)},
            "render": scalars(scene.render, ("filepath",)), "image": scalars(scene.render.image_settings),
            "cycles": scalars(scene.cycles), "view": scalars(scene.view_settings),
            "display": scalars(scene.display_settings), "units": scalars(scene.unit_settings)}


def collect(bpy, recipe):
    from mathutils import Vector
    scene, layer = bpy.context.scene, bpy.context.view_layer
    require(len(bpy.data.scenes) == 1 and len(scene.view_layers) == 1 and layer.use,
            "one scene and one enabled view layer required")
    require(not bpy.data.libraries and not scene.use_nodes and scene.sequence_editor is None,
            "linked/composited/sequenced presentation unsupported")
    require(not any(img.source == "FILE" and not img.packed_file for img in bpy.data.images),
            "external image dependency unsupported")
    def check_layer(item):
        require(not item.exclude and not item.holdout and not item.indirect_only
                and not item.collection.hide_render, "unsupported collection visibility")
        for child in item.children:
            check_layer(child)
    check_layer(layer.layer_collection)
    graph = bpy.context.evaluated_depsgraph_get()
    require(not any(i.is_instance for i in graph.object_instances), "instanced geometry unsupported")
    rows = []
    for obj in scene.objects:
        require(not obj.modifiers and not obj.constraints and obj.animation_data is None
                and obj.parent is None and getattr(obj.data, "animation_data", None) is None,
                "animated/parented/constrained/modified object unsupported")
        row = {"name": obj.name, "type": obj.type, "visible_render": not obj.hide_render}
        if obj.type == "MESH":
            require(obj.visible_get(view_layer=layer), "viewport/render membership must agree")
            require(obj.data.shape_keys is None, "shape keys unsupported")
            evaluated = obj.evaluated_get(graph)
            row["world_corners"] = [list(evaluated.matrix_world @ Vector(c)) for c in evaluated.bound_box]
        rows.append(row)
    render, cam = scene.render, scene.camera
    require(cam is not None and cam.name == "Botanical_Family_Camera", "active canonical camera required")
    q = dict(engine=render.engine, device=scene.cycles.device, samples=scene.cycles.samples,
             threads_mode=render.threads_mode, threads=render.threads,
             resolution=[render.resolution_x, render.resolution_y], percentage=render.resolution_percentage,
             full_frame=not render.use_border and not render.use_crop_to_border and not render.use_multiview,
             format=render.image_settings.file_format,
             metres=scene.unit_settings.system == "METRIC" and scene.unit_settings.scale_length == 1)
    check_quality(q)
    m = cam.matrix_world
    camera = dict(projection=cam.data.type, location=list(m.translation), right=list(m.col[0][:3]),
                  up=list(m.col[1][:3]), forward=[-v for v in m.col[2][:3]],
                  sensor_fit=cam.data.sensor_fit, shift=[cam.data.shift_x, cam.data.shift_y],
                  clip_start=cam.data.clip_start, clip_end=cam.data.clip_end, ortho_scale=cam.data.ortho_scale)
    bounds = dict(schema=recipe["bounds_schema"], units="metres", full_frame=q["full_frame"],
                  presentation_sha256=recipe["input_pins"][0]["sha256"], resolution=q["resolution"],
                  pixel_aspect=[render.pixel_aspect_x, render.pixel_aspect_y], camera=camera,
                  objects=staged_inventory(rows, recipe["expected_plant_names"]))
    return bounds, q, rows


def execute_copy(state):
    # ONLY reached after complete file/path/pin + explicit command/SHA validation.
    import bpy
    require(bpy.app.background and tuple(bpy.app.version) == (4, 3, 1) and not bpy.data.filepath,
            "fresh Blender4.3.1 background startup required")
    require(not bpy.app.autoexec_fail, "startup autoexec failure")
    recipe, paths = state["recipe"], state["paths"]
    # Revalidate immediately before the first write. A retained partial root is terminal;
    # never remove it or retry this version after an uncertain/failed operation.
    fresh = preflight(state["caller"])
    require(fresh["caller_sha256"] == state["caller_sha256"], "caller changed since admission")
    paths["root"].parent.mkdir(exist_ok=True)
    safe_path(paths["root"].parent)
    paths["root"].mkdir()
    source = recipe["input_pins"][0]
    copy_presentation(source, paths["copy"])
    require(bpy.ops.wm.open_mainfile(filepath=str(paths["copy"]), load_ui=False, use_scripts=False) == {"FINISHED"},
            "copy open failed")
    require(Path(bpy.data.filepath) == paths["copy"] and not bpy.app.autoexec_fail, "copy/autoexec admission failed")
    scene = bpy.context.scene
    bounds, quality, inventory = collect(bpy, recipe)
    helper = types.ModuleType("hearthjaw_frozen_fit")
    exec(compile(state["helper_bytes"], str(state["caller"].parent / "hearthjaw_inspection_camera_r1.py"), "exec"), helper.__dict__)
    fit = helper.plan_from_bounds(recipe, bounds)
    before = field_witness(scene)
    filepath_before = scene.render.filepath
    scene.camera.location = fit["location"]
    scene.camera.data.ortho_scale = fit["ortho_scale"]
    scene.render.filepath = str(paths["image"])
    bpy.context.view_layer.update()
    after_bounds, after_quality, after_inventory = collect(bpy, recipe)
    after = field_witness(scene)
    require(before == after and quality == after_quality and inventory == after_inventory,
            "recorded protected fields changed")
    for axis in ("right", "up", "forward"):
        require(bounds["camera"][axis] == after_bounds["camera"][axis], "camera orientation changed")
    forward = bounds["camera"]["forward"]
    require(abs(sum((after_bounds["camera"]["location"][i]-bounds["camera"]["location"][i])*forward[i]
                    for i in range(3))) < 1e-5, "camera forward depth changed")
    require(max(abs(a-b) for a, b in zip(after_bounds["camera"]["location"], fit["location"])) < 1e-5
            and abs(after_bounds["camera"]["ortho_scale"]-fit["ortho_scale"]) < 1e-5,
            "applied camera differs from computed fit")
    for key in ("scene", "image", "receipt"):
        safe_path(paths[key], missing=True)
        require(not os.path.lexists(paths[key]), "fresh output required")
    require(bpy.ops.wm.save_as_mainfile(filepath=str(paths["scene"]), compress=True, relative_remap=False,
                                       check_existing=False) == {"FINISHED"}, "inspection save failed")
    require(bpy.ops.render.render(write_still=True, scene=scene.name) == {"FINISHED"}, "inspection render failed")
    terminal = field_witness(scene)
    require(terminal == before, "recorded fields changed during save/render")
    for pin in recipe["input_pins"] + recipe["frozen_source_pins"]:
        checked_bytes(Path(pin["path"]), pin["bytes"], pin["sha256"])
    outputs = []
    for key in ("copy", "scene", "image"):
        p = safe_path(paths[key])
        raw = p.read_bytes()
        require(raw, "empty output")
        outputs.append(dict(path=str(p), bytes=len(raw), sha256=digest(raw)))
    receipt = dict(schema="daedalus.hearthjaw-copy-inspection.v1", observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   state="ONE_COPY_INSPECTION_RENDER_RETURNED_FINISHED", caller_sha256=state["caller_sha256"],
                   actual_bounds_before=bounds, actual_bounds_after=after_bounds, actual_inventory=inventory,
                   actual_quality=quality, fit=fit, before_fields=before, after_fields=after, terminal_fields=terminal,
                   filepath_before=filepath_before, filepath_after=str(paths["image"]), outputs=outputs,
                   field_coverage="Object matrices/scales, mesh vertices/faces/material slots, scalar material/node/socket/light/world/render/cycles/view/display/unit fields. Not a complete semantic proof; arbitrary nested/custom data, all mesh attributes and visual quality are not certified.",
                   image_quality_accepted=False, native_accepted=False, process_exit_code=None)
    with paths["receipt"].open("x", encoding="utf-8") as out:
        json.dump(receipt, out, indent=2, allow_nan=False)
        out.write("\n")
    return {"state": receipt["state"], "receipt": str(paths["receipt"]), "image_quality_accepted": False}


def main(argv=None):
    try:
        tokens = list(sys.argv[1:] if argv is None else argv)
        prefix = None
        if "--" in tokens:
            index = tokens.index("--")
            prefix, tokens = tokens[:index], tokens[index+1:]
        parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
        def refuse(message):
            raise ValueError(message)
        parser.error = refuse
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--caller-sha256")
        args = parser.parse_args(tokens)
        require(args.execute or args.caller_sha256 is None, "SHA requires explicit execute")
        state = preflight()
        result = dict(state="COPY_CALLER_VALIDATED_ACTUAL_DATA_PENDING", source_only=True, runtime_ready=False,
                      execution_authorized=False, app_calls=0, actual_bounds=None, actual_camera=None,
                      actual_sensor_fit=None, fit=None,
                      caller_sha256=state["caller_sha256"], proposed_paths={k: str(v) for k, v in state["paths"].items()})
        if args.execute:
            require_launch(prefix, state, args.caller_sha256)
            result = execute_copy(state)
        else:
            require(prefix is None, "dry run uses ordinary Python without Blender flags")
        print(json.dumps(result, allow_nan=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, AttributeError) as error:
        print(json.dumps({"state": "REFUSED_OR_PARTIAL_RETAINED_NO_REPLAY", "error": str(error),
                          "actual_data_from_this_error": None}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
