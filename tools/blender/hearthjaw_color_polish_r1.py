"""Deterministic pigment PROPOSAL only: input reads and JSON stdout, no application.

Targets exactly the recorded plant slots' Base Color and viewport diffuse_color.
All shader weights/emission, graphs, geometry, camera and presentation stay protected.
Recorded source colors are already stronger than the pale rendered appearance;
neither the cause nor a future visual improvement is established by this plan.
sRGB decoding: https://www.w3.org/TR/css-color-4/#color-conversion-code
glTF base factors are linear; https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import struct

ROLES = tuple("M_Eco_sky_"+x for x in ("stem", "leaf", "leafLight", "flower", "gill", "glow", "root"))
STAGE_ROLES = ((ROLES[1], ROLES[3], ROLES[6]), ROLES, ROLES)
NAMESPACE = "hearthjaw-color-polish-r1"
COLOR_SPACE = "scene_linear_RGBA_float32"
ALLOWED = ["Principled BSDF.inputs.Base Color", "material.diffuse_color"]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def rgba(value):
    require(isinstance(value, list) and len(value) == 4 and all(type(x) in (int, float)
            and math.isfinite(x) and 0 <= x <= 1 for x in value) and value[3] == 1,
            "finite bounded linear RGBA with alpha1 required")
    return value


def srgb_channel(value):
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1, "sRGB channel out of range")
    return value/12.92 if value <= .04045 else ((value+.055)/1.055)**2.4


def srgb_hex_linear(value):
    require(isinstance(value, str) and re.fullmatch(r"#[0-9A-F]{6}", value), "uppercase #RRGGBB sRGB required")
    return [struct.unpack("<f", struct.pack("<f", srgb_channel(int(value[i:i+2], 16)/255)))[0]
            for i in (1, 3, 5)] + [1.0]


def glb_json(raw):
    """Read material metadata only; not a geometry/import validation or GLB writer."""
    require(len(raw) >= 20 and raw[:4] == b"glTF", "GLB header missing")
    version, total = struct.unpack_from("<II", raw, 4)
    require(version == 2 and total == len(raw), "GLB version/length differs")
    offset, chunks = 12, []
    while offset < total:
        require(offset+8 <= total, "truncated GLB chunk header")
        size, kind = struct.unpack_from("<II", raw, offset); offset += 8
        require(size % 4 == 0 and offset+size <= total, "truncated/unaligned GLB chunk")
        chunks.append((kind, raw[offset:offset+size])); offset += size
    require(chunks and chunks[0][0] == 0x4E4F534A and sum(k == 0x4E4F534A for k, _ in chunks) == 1,
            "exact one first JSON chunk required")
    return json.loads(chunks[0][1])


def shader(material):
    require(isinstance(material, dict) and isinstance(material.get("fields"), dict)
            and material["fields"].get("use_nodes") is True, "node material record required")
    graph = material.get("nodes")
    require(isinstance(graph, dict) and isinstance(graph.get("nodes"), list) and len(graph["nodes"]) == 2,
            "only recorded direct Principled/output graph supported")
    rows = graph["nodes"]
    require(all(isinstance(n, dict) and isinstance(n.get("fields"), dict) for n in rows), "malformed graph node")
    bsdf = [n for n in rows if n["name"] == "Principled BSDF" and n["fields"].get("bl_idname") == "ShaderNodeBsdfPrincipled"]
    output = [n for n in rows if n["name"] == "Material Output" and n["fields"].get("bl_idname") == "ShaderNodeOutputMaterial"]
    require(len(bsdf) == len(output) == 1 and all(n["fields"].get("mute") is False for n in rows)
            and output[0]["fields"].get("is_active_output") is True
            and graph.get("links") == [["Principled BSDF", "BSDF", "Material Output", "Surface"]],
            "unknown/muted/linked-color material graph")
    inputs = bsdf[0].get("inputs")
    require(isinstance(inputs, list) and all(isinstance(x, list) and len(x) == 2 and isinstance(x[0], str) for x in inputs)
            and len({x[0] for x in inputs}) == len(inputs), "distinct socket records required")
    sockets = dict(inputs)
    require("Base Color" in sockets and sockets.get("Alpha") == 1, "opaque Base Color socket required")
    rgba(sockets["Base Color"]); rgba(material["fields"]["diffuse_color"])
    require(sockets["Base Color"] == material["fields"]["diffuse_color"], "viewport/source Base Color differs")
    fingerprint(material)  # Reject all nonfinite or non-JSON records, not only the colors.
    return bsdf[0], sockets


def validate_recipe(recipe):
    require(isinstance(recipe, dict) and recipe.get("schema") == "daedalus.hearthjaw-color-proposal.v1"
            and recipe.get("source_only") is True and recipe.get("namespace") == NAMESPACE
            and recipe.get("allowed_targets") == ALLOWED and recipe.get("color_space") == COLOR_SPACE,
            "unknown color-only proposal contract")
    require(isinstance(recipe.get("palette_srgb_hex"), dict) and set(recipe["palette_srgb_hex"]) == set(ROLES),
            "exact seven-role palette required")
    palette = {role: srgb_hex_linear(recipe["palette_srgb_hex"][role]) for role in ROLES}
    require(isinstance(recipe.get("stages"), list) and all(isinstance(x, dict) and type(x.get("index")) is int
            for x in recipe["stages"]) and [x["index"] for x in recipe["stages"]] == [0, 1, 2],
            "exact ordered three stage bindings required")
    return palette


def protected_record(fields, bindings):
    """Remove precisely the two permitted color leaves from a recorded-state copy."""
    result = copy.deepcopy(fields)
    for name in {b["material"] for b in bindings}:
        mat = result["materials"][name]; node, _ = shader(mat)
        del mat["fields"]["diffuse_color"]
        node["inputs"] = [x for x in node["inputs"] if x[0] != "Base Color"]
    return result


def make_plan(recipe, receipt, stage_docs):
    palette = validate_recipe(recipe)
    require(isinstance(receipt, dict) and receipt.get("schema") == "daedalus.hearthjaw-copy-inspection.v2"
            and receipt.get("operation_intent") == "hearthjaw-camera-r2"
            and receipt.get("state") == "ONE_COPY_INSPECTION_RENDER_RETURNED_FINISHED", "pinned R2 receipt required")
    fields = receipt["after_fields"]
    require(receipt["before_fields"] == fields == receipt["terminal_fields"], "R2 protected field witnesses differ")
    require(isinstance(fields, dict) and isinstance(fields.get("objects"), list)
            and isinstance(fields.get("materials"), dict), "scene records missing")
    require(all(isinstance(o, dict) and isinstance(o.get("name"), str)
            and isinstance(o.get("materials", []), list)
            and all(isinstance(n, str) for n in o.get("materials", [])) for o in fields["objects"]),
            "malformed object/material-slot records")
    objects = {o["name"]: o for o in fields["objects"]}
    require(len(objects) == len(fields["objects"]), "duplicate scene object record")
    plant_names = {"Display_Prop_Eco_sky_hearthjaw_G%d" % i for i in range(3)}
    users = {}
    for obj in fields["objects"]:
        for slot, name in enumerate(obj.get("materials", [])):
            users.setdefault(name, []).append((obj["name"], slot))
    edits, bindings = [], []
    require(set(stage_docs) == {0, 1, 2}, "exact three GLB material documents required")
    for stage in recipe["stages"]:
        index, name = stage["index"], stage["object_name"]
        require(name == "Display_Prop_Eco_sky_hearthjaw_G%d" % index, "unknown plant target")
        obj, doc = objects[name], stage_docs[index]
        require(obj.get("type") == "MESH" and fingerprint(obj) == stage["object_sha256"], "stage object/binding changed")
        require(tuple(stage["roles"]) == STAGE_ROLES[index]
                and obj.get("materials") == stage["material_slots"]
                and len(obj["materials"]) == len(stage["roles"]), "stage slot count/order differs")
        require([m["name"] for m in doc["materials"]] == stage["roles"]
                and len(doc["meshes"]) == len(doc["nodes"]) == 1, "GLB role layout differs")
        primitive_materials = [p["material"] for p in doc["meshes"][0]["primitives"]]
        require(primitive_materials == stage["primitive_materials"]
                and set(primitive_materials) == set(range(len(stage["roles"]))), "GLB primitive/material mapping differs")
        for slot, (role, material_name) in enumerate(zip(stage["roles"], obj["materials"])):
            require(all(owner in plant_names for owner, _ in users[material_name]), "HOLD shared nonplant/protected material user")
            mat = fields["materials"][material_name]
            require(users[material_name] == [(name, slot)] and mat["fields"].get("users") == 1
                    and not mat["fields"].get("use_fake_user") and not mat["fields"].get("is_library_indirect"),
                    "HOLD shared/unknown material ownership; slot-local copy isolation required")
            require(fingerprint(mat) == stage["material_sha256"][slot], "recorded material changed")
            node, sockets = shader(mat)
            factor = rgba(doc["materials"][slot]["pbrMetallicRoughness"]["baseColorFactor"])
            require(max(abs(a-b) for a, b in zip(factor, sockets["Base Color"])) <= 1e-6,
                    "GLB linear factor/socket mapping differs")
            binding = dict(stage=index, object=name, slot=slot, material=material_name, role=role)
            bindings.append(binding)
            edits.append(dict(binding=binding, material_scope="verified fresh-copy plant slot only; no canonical/global/shared mutation",
                              before_linear_rgba=sockets["Base Color"], proposed_linear_rgba=palette[role],
                              targets=ALLOWED, color_space=COLOR_SPACE,
                              protected_material_sha256=fingerprint(protected_record(fields, [binding])["materials"][material_name]),
                              recorded_bsdf_weight_retained=sockets.get("Weight"),
                              recorded_emission_retained={k: sockets[k] for k in ("Emission Color", "Emission Strength")}))
    require(len(edits) == 17, "actual three/seven/seven slots required, never add absent roles")
    return dict(schema="daedalus.hearthjaw-color-plan.v1", namespace=NAMESPACE, source_only=True,
                color_space=COLOR_SPACE, palette_srgb_hex=recipe["palette_srgb_hex"], palette_linear_rgba=palette,
                edits=edits, protected_scene_sha256=fingerprint(protected_record(fields, bindings)),
                protected_camera_sha256=fingerprint(receipt["actual_bounds_after"]["camera"]),
                protected_bounds_sha256=fingerprint(receipt["actual_bounds_after"]["objects"]),
                numeric_palette_luminance={role: sum(c*w for c, w in zip(palette[role][:3], (.2126, .7152, .0722))) for role in ROLES},
                numeric_metric_qualification="Source factors only, not rendered contrast or visual acceptance.",
                actual=dict(author=None, application=None, export=None, render=None, native=None, quality=None),
                render_authorized=False, runtime_ready=False, app_calls=0, output_writes=0,
                qualification="One proposed pigment variant. Recorded Weight0 is retained metadata, not an effective shader-weight inference or diagnosis. Matched pixels and a separate copy-only application are unimplemented/unrun.")


def verify_color_only(before, after, before_bounds, after_bounds, plan):
    """Check hypothetical recorded fields only; this does not apply any edit."""
    bindings = [edit["binding"] for edit in plan["edits"]]
    require(fingerprint(protected_record(before, bindings)) == plan["protected_scene_sha256"]
            == fingerprint(protected_record(after, bindings)),
            "noncolor field, object, graph or shader setting changed")
    require(fingerprint(before_bounds["camera"]) == plan["protected_camera_sha256"]
            == fingerprint(after_bounds["camera"])
            and fingerprint(before_bounds["objects"]) == plan["protected_bounds_sha256"]
            == fingerprint(after_bounds["objects"]), "camera or measured object bounds changed")
    for edit in plan["edits"]:
        mat = after["materials"][edit["binding"]["material"]]; _, sockets = shader(mat)
        require(sockets["Base Color"] == mat["fields"]["diffuse_color"] == edit["proposed_linear_rgba"], "planned color differs")
    return True


def checked(pin):
    require(isinstance(pin, dict) and isinstance(pin.get("path"), str) and type(pin.get("bytes")) is int
            and pin["bytes"] >= 0 and isinstance(pin.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]), "malformed input pin")
    raw = Path(pin["path"]).read_bytes()
    require(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"], "pinned input changed")
    return raw


def load_plan(path):
    recipe = json.loads(Path(path).read_text(encoding="utf-8")); validate_recipe(recipe)
    require(isinstance(recipe.get("inputs"), dict) and set(recipe["inputs"]) == {"scene", "image", "receipt", "manifest"}
            and isinstance(recipe.get("source_pins"), list), "exact pinned inputs/source list required")
    raw = {key: checked(pin) for key, pin in recipe["inputs"].items()}
    for pin in recipe["source_pins"]:
        checked(pin)
    manifest = json.loads(raw["manifest"]); receipt = json.loads(raw["receipt"])
    rows = [g for family in manifest["families"] for species in family["species"] if species["key"] == "sky_hearthjaw" for g in species["growthStages"]]
    require([r["index"] for r in rows] == [0, 1, 2], "manifest stage identities differ")
    docs = {}
    for expected, actual in zip(recipe["stages"], rows):
        pin = expected["glb"]; g = actual["lods"][0]["glb"]
        require(actual["assetId"] == expected["asset_id"] and all(pin[k] == g[k] for k in ("bytes", "sha256"))
                and Path(pin["path"]) == Path(recipe["job_root"]) / g["file"], "manifest-bound GLB pin differs")
        docs[expected["index"]] = glb_json(checked(pin))
    for key in ("scene", "image"):
        require(any(all(row[k] == recipe["inputs"][key][k] for k in ("path", "bytes", "sha256"))
                    for row in receipt["outputs"]), "R2 output/receipt binding differs")
    return make_plan(recipe, receipt, docs)


def main(argv=None):
    try:
        parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
        def refuse(message):
            raise ValueError(message)
        parser.error = refuse
        parser.add_argument("--recipe", type=Path, default=Path(__file__).with_suffix(".recipe.json"))
        args = parser.parse_args(argv)
        print(json.dumps(load_plan(args.recipe), allow_nan=False, sort_keys=True))
        return 0
    except (ValueError, KeyError, TypeError, OSError, struct.error) as error:
        print(json.dumps(dict(state="HOLD_FILE_ONLY", error=str(error), actual=dict(author=None, application=None,
              export=None, render=None, native=None, quality=None), app_calls=0, output_writes=0)))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
