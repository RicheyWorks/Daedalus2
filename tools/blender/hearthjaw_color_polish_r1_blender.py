"""SOURCE ONLY until separately allocated. ONE fresh COPY, 17 colors, fixed R2 view.

Default: pinned file reads + JSON stdout, no bpy, output directory or asset writes.
Historical comparisons normalize ONLY 25 declared ID.session_uid leaves; fresh
same-process protection retains every UID. Blender v4.3.1 rna_ID.cc2126 and
DNA_ID.h416 describe this session identifier. No tag/UI/float normalization.
https://github.com/blender/blender/blob/v4.3.1/source/blender/makesrna/intern/rna_ID.cc#L2126
No source/mock result establishes RNA compatibility or improved rendered pixels.
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import types

# Explicit bootstrap works with Blender --python and isolated runpy/exec callers.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

CALLER = "hearthjaw_color_polish_r1_blender.py"
INTENT = "hearthjaw-color-polish-r1"
ROOT = Path("C:/Users/730ri/projects/Daedalus2/artifacts/ecology/sky-botanical-pilot-r1/inspection") / INTENT
PINS = {
    "hearthjaw_color_polish_r1.py": [(15371, "17c42423085c14a803734dad6b16e2630024ecc19a72ce27e42488de8904ade2")],
    "hearthjaw_color_polish_r1.recipe.json": [
        (10075, "88766c8ff6ebe6082ea238869c177892aeab6609a0f73673d1aa3b613c798535"),
        (10315, "84afcd8b77ae6d5a9e946041e5fef339e81d8745bb665144720cc06d0e10eab8")],
    "hearthjaw_inspection_camera_r1_blender.py": [(30233, "6d5ff10c57516ed56a52edd804e0db7f5f6bd26a570d36ba3726b9e49b657c2f")],
    "hearthjaw_inspection_camera_r1.recipe.json": [(5002, "4da06be276a72e9bfbb0ffe44c00576d556378000a619ed724de38dce3c4ea5c")],
}
UID_OBJECTS = {"Botanical_Family_Camera", "Fill", "Key", "Rim"}
PROTECTED_MATERIALS = {"Presentation_Backdrop", "Presentation_Botanical_Plinth", "Presentation_Plinth_Rim"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    """JSON tuple/list representation only; never omit fields or round numbers."""
    return json.loads(json.dumps(value, allow_nan=False))


def load_source(raw, path, name):
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def dependencies(here):
    raw = {}
    for name, accepted in PINS.items():
        data = (here.parent/name).read_bytes()
        require((len(data), digest(data)) in accepted, "frozen sibling pin differs: "+name)
        raw[name] = data
    color = load_source(raw["hearthjaw_color_polish_r1.py"], here.parent/"hearthjaw_color_polish_r1.py", "hearthjaw_color_frozen")
    old = load_source(raw["hearthjaw_inspection_camera_r1_blender.py"], here.parent/"hearthjaw_inspection_camera_r1_blender.py", "hearthjaw_collect_frozen")
    return color, old, raw


def uid_paths(fields, recipe):
    """Exact target-specific paths, NOT recursive stripping of keys named UID."""
    material_names = {name for s in recipe["stages"] for name in s["material_slots"]} | PROTECTED_MATERIALS
    require(set(fields["materials"]) == material_names and len(material_names) == 20, "historical material inventory differs")
    objects = fields["objects"]
    require(len(objects) == 14 and {o["name"] for o in objects if "data" in o} == UID_OBJECTS,
            "historical camera/light inventory differs")
    return [("materials", name, "fields", "session_uid") for name in sorted(material_names)] + [
        ("objects", i, "data", "session_uid") for i, o in enumerate(objects) if o["name"] in UID_OBJECTS
    ] + [("world", "fields", "session_uid")]


def historical_stable(fields, paths):
    result = copy.deepcopy(fields); found = set()
    def find(value, path=()):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "session_uid": found.add(path+(key,))
                find(item, path+(key,))
        elif isinstance(value, list):
            for i, item in enumerate(value): find(item, path+(i,))
    find(result)
    require(found == set(paths) and len(found) == 25, "unknown/missing session_uid path; HOLD")
    values = []
    for path in paths:
        node = result
        for key in path[:-1]: node = node[key]
        value = node[path[-1]]
        require(type(value) is int and 0 < value < 2**32, "invalid session_uid")
        values.append(value); del node[path[-1]]
    require(len(set(values)) == len(values), "duplicate session_uid")
    return result, values


def paths_for(old):
    old.safe_path(ROOT.parent)
    old.safe_path(ROOT, missing=True)
    require(not os.path.lexists(ROOT), "color attempt root exists; consumed/no replay")
    return dict(root=ROOT, copy=ROOT/"R2-input-copy.blend", scene=ROOT/"Hearthjaw_Color_Polish_R1.blend",
                image=ROOT/"Hearthjaw_Color_Polish_R1.png", receipt=ROOT/"hearthjaw_color_polish_r1.receipt.json")


def preflight(here=None):
    here = Path(here or __file__).absolute()
    require(here.name == CALLER, "caller filename differs")
    color, old, raw = dependencies(here); old.safe_path(here)
    for name in raw: old.safe_path(here.parent/name)
    recipe_path = here.parent/"hearthjaw_color_polish_r1.recipe.json"
    plan = color.load_plan(recipe_path)
    recipe = json.loads(raw[recipe_path.name]); historical = json.loads(color.checked(recipe["inputs"]["receipt"]))
    legacy_recipe = json.loads(raw["hearthjaw_inspection_camera_r1.recipe.json"])
    for pin in list(recipe["inputs"].values()) + recipe["source_pins"] + [s["glb"] for s in recipe["stages"]]:
        old.safe_path(pin["path"])
    paths = paths_for(old)
    require(Path(recipe["inputs"]["scene"]["path"]).parent == ROOT.parent/"hearthjaw-camera-r2", "literal R2 source required")
    require(Path(recipe["job_root"]) not in paths["root"].parents, "canonical job output refused")
    uid = uid_paths(historical["after_fields"], recipe); historical_stable(historical["after_fields"], uid)
    return dict(caller=here, self_sha256=digest(here.read_bytes()), color=color, old=old, recipe=recipe,
                legacy_recipe=legacy_recipe, historical=historical, plan=plan, paths=paths, uid_paths=uid,
                sibling_pins=[dict(path=str(here.parent/name), bytes=len(data), sha256=digest(data)) for name, data in raw.items()])


def launch_prefix(here):
    return ["--background", "--factory-startup", "--disable-autoexec", "--threads", "1",
            "--python-exit-code", "2", "--python", str(here)]


def require_launch(prefix, state, args):
    require(prefix == launch_prefix(state["caller"]), "exact background/factory/disable-autoexec/CPU1 launch required")
    require(args.self_sha256 == state["self_sha256"] and args.operation == INTENT,
            "exact self SHA and operation required")
    require(type(args.grant_id) is int and args.grant_id > 0, "future actual allocation ID required; flag alone is not authorization")


def extra_witness(bpy, old):
    """Same-process geometry/attribute and object RNA protection beyond R2 coverage.

    Read every exposed scalar value of mesh vertices/edges/loops/polygons and
    named attribute data (including UV/color/normal attributes). Unknown empty
    attribute item serialization holds. This is bounded RNA coverage, not proof
    of arbitrary unexposed/custom/nested semantics or a reopened saved scene.
    """
    result = {}
    for obj in sorted(bpy.context.scene.objects, key=lambda o:o.name):
        row = dict(object=old.scalars(obj), data_name=obj.data.name if obj.data else None,
                   matrix_world=[list(x) for x in obj.matrix_world],
                   slots=[dict(name=s.material.name if s.material else None, link=s.link) for s in obj.material_slots])
        if obj.type == "MESH":
            mesh = obj.data
            row["mesh"] = dict(fields=old.scalars(mesh), vertices=[old.scalars(x) for x in mesh.vertices],
                edges=[old.scalars(x) for x in mesh.edges], loops=[old.scalars(x) for x in mesh.loops],
                polygons=[old.scalars(x) for x in mesh.polygons], attributes=[])
            for attr in sorted(mesh.attributes, key=lambda a:a.name):
                data = [old.scalars(x) for x in attr.data]
                require(all(data), "unsupported empty attribute serialization")
                row["mesh"]["attributes"].append(dict(name=attr.name, data_type=attr.data_type, domain=attr.domain, data=data))
        result[obj.name] = row
    return wire(result)


def snapshot(bpy, state):
    old = state["old"]; bounds, quality, inventory = old.collect(bpy, state["legacy_recipe"])
    facts = old.presentation_conditions(bpy)
    require(old.classify_presentation(facts)["safe_to_continue"], "presentation conditions unsupported")
    return wire(dict(fields=old.field_witness(bpy.context.scene), bounds=bounds, quality=quality,
                     inventory=inventory, presentation=facts, extra=extra_witness(bpy, old)))


def admit_fresh(state, before):
    hist = state["historical"]; color = state["color"]
    stable_old, old_uid = historical_stable(hist["after_fields"], state["uid_paths"])
    stable_new, new_uid = historical_stable(before["fields"], state["uid_paths"])
    require(color.fingerprint(stable_old) == color.fingerprint(stable_new),
            "historical/fresh non-UID field incompatibility; HOLD before any colors")
    require(before["bounds"] == hist["actual_bounds_after"] and before["quality"] == hist["actual_quality"]
            and before["inventory"] == hist["actual_inventory"]
            and before["presentation"] == hist["presentation_after"]["conditions"],
            "fixed R2 bounds/camera/quality/inventory/presentation differs")
    # Rebind ONLY protection digests to the freshly admitted IDs, in memory.
    # Never normalize fresh before/after or modify the published plan/recipe.
    plan = copy.deepcopy(state["plan"]); bindings = [e["binding"] for e in plan["edits"]]
    plan["protected_scene_sha256"] = color.fingerprint(color.protected_record(before["fields"], bindings))
    for edit in plan["edits"]:
        edit["protected_material_sha256"] = color.fingerprint(color.protected_record(before["fields"], [edit["binding"]])["materials"][edit["binding"]["material"]])
    return plan, [dict(path=list(p), historical=a, fresh=b) for p, a, b in zip(state["uid_paths"], old_uid, new_uid)]


def material_targets(bpy, state, before):
    """References come from exact plant slots; never global material-name mutation."""
    targets = []; identities = set()
    for edit in state["plan"]["edits"]:
        b = edit["binding"]; obj = bpy.context.scene.objects[b["object"]]
        require(obj.type == "MESH" and len(obj.material_slots) == len(obj.data.materials), "plant slots unsupported")
        slot = obj.material_slots[b["slot"]]; mat = slot.material
        require(slot.link == "DATA" and mat is obj.data.materials[b["slot"]] and mat.name == b["material"], "plant binding changed")
        require(mat.library is None and mat.node_tree.library is None and mat.is_editable and mat.users == 1
                and not mat.use_fake_user and not mat.use_extra_user and mat.animation_data is None
                and mat.node_tree.animation_data is None, "shared/linked/animated material HOLD")
        users = [(o.name, i) for o in bpy.data.objects for i, s in enumerate(o.material_slots) if s.material is mat]
        require(users == [(b["object"], b["slot"])], "unknown/nonplant material user HOLD")
        state["color"].shader(before["fields"]["materials"][mat.name])
        node = mat.node_tree.nodes["Principled BSDF"]; socket = node.inputs["Base Color"]
        require(not socket.is_linked and mat.name not in identities, "linked/duplicate color target HOLD")
        require(list(socket.default_value) == list(mat.diffuse_color) == edit["before_linear_rgba"], "fresh color binding differs")
        identities.add(mat.name); targets.append((mat, socket, edit["proposed_linear_rgba"]))
    require(len(targets) == 17, "exact 17 plant-owned targets required")
    return targets


def verify_after(state, before, after, plan):
    state["color"].verify_color_only(before["fields"], after["fields"], before["bounds"], after["bounds"], plan)
    for key in ("bounds", "quality", "inventory", "presentation", "extra"):
        require(before[key] == after[key], "same-process protected witness changed: "+key)


def durable(path, value):
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, indent=2, allow_nan=False); out.write("\n"); out.flush(); os.fsync(out.fileno())


def png_dimensions(raw):
    require(len(raw) >= 33 and raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[12:16] == b"IHDR", "PNG header missing")
    dimensions = list(struct.unpack(">II", raw[16:24])); require(dimensions == [1800, 1400], "matched PNG dimensions differ")
    return dimensions


def execute_copy(state, grant_id):
    import bpy  # first app import, only after launch/self/input/output admission
    require(bpy.app.background and tuple(bpy.app.version) == (4, 3, 1) and not bpy.data.filepath
            and not bpy.app.autoexec_fail, "fresh Blender4.3.1 background startup required")
    properties = bpy.ops.wm.open_mainfile.get_rna_type().properties.keys()
    require({"filepath", "load_ui", "use_scripts"} <= set(properties), "safe-open RNA unsupported; no fallback")
    fresh = preflight(state["caller"])
    require(fresh["self_sha256"] == state["self_sha256"], "caller changed since admission")
    paths = state["paths"]; paths["root"].mkdir()  # exclusive, consumed even if partial
    try:
        durable(paths["root"]/"attempt.json", dict(schema="daedalus.hearthjaw-color-attempt.v1", operation=INTENT,
            self_sha256=state["self_sha256"], grant_id_binding=grant_id, allocation_authority="external; ID flag alone is not authorization",
            input_scene=state["recipe"]["inputs"]["scene"], state="ATTEMPT_CONSUMED_BEFORE_COPY"))
        old = state["old"]; old.copy_presentation(state["recipe"]["inputs"]["scene"], paths["copy"])
        require(bpy.ops.wm.open_mainfile(filepath=str(paths["copy"]), load_ui=False, use_scripts=False) == {"FINISHED"}, "copy open failed")
        require(Path(bpy.data.filepath) == paths["copy"] and not bpy.app.autoexec_fail, "copy path/autoexec failed")
        before = snapshot(bpy, state); durable(paths["root"]/"before.json", before)
        plan, compatibility = admit_fresh(state, before)
        targets = material_targets(bpy, state, before)  # validate ALL 17 before ANY setter
        for mat, socket, rgba in targets:
            socket.default_value = rgba; mat.diffuse_color = rgba
        scene = bpy.context.scene; scene.render.filepath = str(paths["image"])
        bpy.context.view_layer.update()
        after = snapshot(bpy, state); durable(paths["root"]/"after-color.json", after); verify_after(state, before, after, plan)
        require(scene.render.filepath == str(paths["image"]), "output binding differs")
        for key in ("scene", "image", "receipt"):
            old.safe_path(paths[key], missing=True); require(not os.path.lexists(paths[key]), "fresh output required")
        require(bpy.ops.wm.save_as_mainfile(filepath=str(paths["scene"]), compress=True, relative_remap=False, check_existing=False) == {"FINISHED"}, "color copy save failed")
        require(bpy.ops.render.render(write_still=True, scene=scene.name) == {"FINISHED"}, "matched render failed")
        terminal = snapshot(bpy, state); durable(paths["root"]/"terminal.json", terminal); verify_after(state, before, terminal, plan)
        require(terminal == after and scene.render.filepath == str(paths["image"]), "save/render changed protected state")
        outputs = []
        for key in ("copy", "scene", "image"):
            p = old.safe_path(paths[key]); raw = p.read_bytes(); require(raw, "empty output")
            if key == "image": png_dimensions(raw)
            outputs.append(dict(path=str(p), bytes=len(raw), sha256=digest(raw)))
        for pin in list(state["recipe"]["inputs"].values()) + state["recipe"]["source_pins"] + [s["glb"] for s in state["recipe"]["stages"]]:
            state["color"].checked(pin)
        for pin in state["sibling_pins"]:
            state["color"].checked(pin)
        require(digest(state["caller"].read_bytes()) == state["self_sha256"], "caller changed during operation")
        receipt = dict(schema="daedalus.hearthjaw-color-copy.v1", state="ONE_COPY_COLOR_SAVE_MATCHED_RENDER_RETURNED_FINISHED",
            operation=INTENT, observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), self_sha256=state["self_sha256"],
            grant_id_binding=grant_id, inputs=state["recipe"]["inputs"], historical_uid_comparison=compatibility,
            same_process_uids_protected=True, targets=plan["edits"], outputs=outputs, actual_camera=terminal["bounds"]["camera"],
            actual_quality=terminal["quality"], image_quality_accepted=False, native_accepted=False, process_exit_code=None,
            qualification="Application/save/render operator results plus bounded recorded-state proof only. External process-terminal/resource receipts, pixel review and any native acceptance remain separate. No reopened-scene proof.")
        durable(paths["receipt"], receipt)
        return dict(state=receipt["state"], receipt=str(paths["receipt"]), quality_accepted=False, process_exit_code=None)
    except Exception as error:
        durable(paths["root"]/"failure.json", dict(state="FAILED_OR_UNCERTAIN_CONSUMED_NO_REPLAY", error=type(error).__name__+": "+str(error), process_exit_code=None))
        raise


def main(argv=None):
    app_attempted = False
    try:
        tokens = list(sys.argv[1:] if argv is None else argv); prefix = None
        if "--" in tokens:
            i = tokens.index("--"); prefix, tokens = tokens[:i], tokens[i+1:]
        parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
        def refuse(message): raise ValueError(message)
        parser.error = refuse
        parser.add_argument("--execute", action="store_true"); parser.add_argument("--self-sha256")
        parser.add_argument("--operation"); parser.add_argument("--grant-id", type=int)
        args = parser.parse_args(tokens); state = preflight()
        result = dict(state="SOURCE_COPY_ADAPTER_FILE_VALIDATED_RUNTIME_UNOBSERVED", source_only=True, execution_authorized=False,
            self_sha256=state["self_sha256"], operation=INTENT, proposed_paths={k:str(v) for k,v in state["paths"].items()},
            app_calls=0, output_writes=0, actual=dict(author=None, application=None, export=None, render=None, native=None, quality=None),
            fresh_session_compatibility=None, declared_historical_uid_paths=[list(p) for p in state["uid_paths"]],
            prerequisites="Separate actual one-process CPU1 allocation, fresh floors/custody/lease/input-source-output guards, exact launch+self SHA+operation+actual grant binding, and actual RNA compatibility. No grant comes from this CLI.")
        if args.execute:
            require_launch(prefix, state, args); app_attempted = True; result = execute_copy(state, args.grant_id)
        else:
            require(prefix is None and args.self_sha256 is None and args.operation is None and args.grant_id is None,
                    "execute-only fields refused by inert default")
        print(json.dumps(result, allow_nan=False)); return 0
    except (ValueError, KeyError, TypeError, OSError, AttributeError, RuntimeError) as error:
        print(json.dumps(dict(state="HOLD_OR_PARTIAL_CONSUMED_NO_REPLAY", error=str(error), app_attempted=app_attempted,
                             actual=None, process_exit_code=None), allow_nan=False)); return 2


if __name__ == "__main__":
    raise SystemExit(main())
