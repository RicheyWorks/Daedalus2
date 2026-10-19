"""Engine-free core of the Interchange import harness (P1 item f).

Everything here is plain Python 3 stdlib so it can be tested without Unreal. The editor
side (ue_harness.py) only executes a plan built here and returns raw facts; the verdict
is computed here too. Rules applied (Epic primary-source findings, link 48194, plus the
live run of item e, PR197):

* import/reimport returning True only means STARTED; completion is OnAssetsImportDone.
* Done is not success: compare the full output inventory and object identity.
* Imports are not undoable: a checkpoint must exist before the first native call.
* Reuse-existing-materials and create-new-materials are SEPARATE switches.
* Nanite is ON by default in UE 5.8 for static meshes; a per-asset override turns it off
  (terrain_33 and any packet that says off). Masked/translucent materials are flagged.
* Stock glTF Interchange drops SOCKET_ empties: sockets come from <Asset>.sockets.json.
* UCX_ children become convex collision; hull extent is read via export_text.
* Material instances can stay dirty after the first save: save loops until clean (max 3).
"""
import hashlib
import json
import os
import struct

SCHEMA = "daedalus.interchange-harness-plan.v1"
SIDE_SCHEMA_KEYS = ("name", "parent", "location_cm", "rotation")
MAX_SAVE_PASSES = 3


class PlanError(ValueError):
    pass


# ---------------------------------------------------------------- GLB reading (stdlib)

def read_glb(data):
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise PlanError("not a glTF 2 binary or length mismatch")
    clen, ctype = struct.unpack_from("<I4s", data, 12)
    if ctype != b"JSON":
        raise PlanError("first chunk is not JSON")
    return json.loads(data[20:20 + clen])


def glb_summary(gltf):
    nodes = gltf.get("nodes", [])
    mats = gltf.get("materials", [])
    return {
        "nodes": [n.get("name") for n in nodes],
        "socket_empties": [n.get("name") for n in nodes if str(n.get("name", "")).startswith("SOCKET_") and "mesh" not in n],
        "ucx": [n.get("name") for n in nodes if str(n.get("name", "")).startswith("UCX_")],
        "materials": [{"name": m.get("name"), "alpha": m.get("alphaMode", "OPAQUE"),
                       "transmission": "KHR_materials_transmission" in m.get("extensions", {})} for m in mats],
    }


# ---------------------------------------------------------------- sockets sidecar

def load_sidecar(path):
    """Read <Asset>.sockets.json. Accepts a list or {"sockets": [...]}. Validates every entry.

    Location key: "location_cm", or "location" as blender-team ships it (48521 shape, top-level
    "units": "cm"). Any top-level units other than cm is refused rather than guessed.
    """
    with open(path, encoding="utf-8-sig") as fh:
        raw = json.load(fh)
    if isinstance(raw, dict) and str(raw.get("units", "cm")).lower() != "cm":
        raise PlanError("sidecar: units %r not supported (cm only)" % raw.get("units"))
    entries = raw.get("sockets", raw) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise PlanError("sidecar: expected a list of sockets")
    out, seen = [], set()
    for i, e in enumerate(entries):
        if isinstance(e, dict) and "location_cm" not in e and "location" in e:
            e = dict(e, location_cm=e["location"])
        missing = [k for k in SIDE_SCHEMA_KEYS if k not in e]
        if missing:
            raise PlanError("sidecar entry %d missing %s" % (i, ",".join(missing)))
        name = str(e["name"])
        if name.startswith("SOCKET_"):
            name = name[len("SOCKET_"):]
        if not name or name in seen:
            raise PlanError("sidecar entry %d: empty or duplicate socket name %r" % (i, name))
        seen.add(name)
        loc, rot = e["location_cm"], e["rotation"]
        if isinstance(rot, dict):
            rot = [rot.get("pitch", 0.0), rot.get("yaw", 0.0), rot.get("roll", 0.0)]
        if len(loc) != 3 or len(rot) != 3:
            raise PlanError("sidecar entry %d: location_cm and rotation need 3 numbers" % i)
        out.append({"name": name, "parent": str(e["parent"]), "location_cm": [float(x) for x in loc],
                    "rotation_pyr": [float(x) for x in rot], "scale": [float(x) for x in e.get("scale", [1, 1, 1])]})
    return out


def socket_plan(glb_path, sidecar_path=None):
    """Sockets to add after import, plus warnings. Sidecar wins; SOCKET_ empties alone only warn."""
    sidecar_path = sidecar_path or default_sidecar_path(glb_path)
    with open(glb_path, "rb") as fh:
        summary = glb_summary(read_glb(fh.read()))
    warnings = []
    if os.path.exists(sidecar_path):
        sockets = load_sidecar(sidecar_path)
        glb_names = {n[len("SOCKET_"):] for n in summary["socket_empties"]}
        missing_in_side = sorted(glb_names - {s["name"] for s in sockets})
        if missing_in_side:
            warnings.append("glb has SOCKET_ empties not in sidecar: %s" % ",".join(missing_in_side))
        return {"sidecar": sidecar_path, "sockets": sockets, "warnings": warnings}
    if summary["socket_empties"]:
        warnings.append("SOCKET_ empties %s found but no sidecar %s; stock glTF Interchange drops them, so no sockets will be added"
                        % (",".join(summary["socket_empties"]), os.path.basename(sidecar_path)))
    return {"sidecar": None, "sockets": [], "warnings": warnings}


def default_sidecar_path(glb_path):
    base = os.path.splitext(glb_path)[0]
    return base + ".sockets.json"


# ---------------------------------------------------------------- plan

def material_review(summary):
    flags = []
    for m in summary["materials"]:
        if m["alpha"] in ("MASK", "BLEND") or m["transmission"]:
            flags.append("%s alpha=%s transmission=%s: review before Nanite/approval" % (m["name"], m["alpha"], m["transmission"]))
    return flags


def build_plan(glb_path, test_root, asset, sha256=None, nbytes=None, overrides=None, profile=None, checkpoint=None):
    """Build an import plan. Refuses without a checkpoint path (imports are not undoable).

    Option precedence: profile["interchange_requested_options"] OVERRIDES the explicit
    ``overrides`` dict (the frozen source packet wins). To test an option on its own, for
    example the item e Nanite-off proof, pass ``overrides`` WITHOUT a profile.
    """
    if not checkpoint:
        raise PlanError("checkpoint path required before any import (imports are not undoable)")
    if not test_root.startswith("/Game/"):
        raise PlanError("destination must be a /Game content path")
    with open(glb_path, "rb") as fh:
        data = fh.read()
    digest = hashlib.sha256(data).hexdigest()
    if sha256 and digest != sha256.lower():
        raise PlanError("sha256 mismatch: %s != %s" % (digest, sha256))
    if nbytes is not None and len(data) != nbytes:
        raise PlanError("byte count mismatch: %d != %d" % (len(data), nbytes))
    gltf = read_glb(data)
    summary = glb_summary(gltf)
    ov = dict(overrides or {})
    if profile:  # profile wins over explicit overrides (see docstring)
        ov.update(profile.get("interchange_requested_options", {}))
    nanite = bool(ov.get("build_nanite", True))  # UE 5.8 default ON for static props
    plan = {
        "schema": SCHEMA, "asset": asset, "source": glb_path.replace("\\", "/"), "sha256": digest, "bytes": len(data),
        "destination": test_root, "checkpoint": checkpoint,
        "options": {
            "build_nanite": nanite,
            "reuse_existing_materials": bool(ov.get("reuse_existing_materials", True)),
            "create_new_materials": bool(ov.get("create_new_materials", True)),
            "import_materials": bool(ov.get("import_materials", True)),
            "collision_from_ucx": bool(ov.get("collision", True)),
            "generate_lightmap_uvs": bool(ov.get("generate_lightmap_u_vs", False)),
            "bake_meshes": bool(ov.get("bake_meshes", True)),
        },
        "material_review": material_review(summary),
        "glb": summary,
        "sockets": socket_plan(glb_path),
        "expect": (profile or {}).get("expect", {}),
    }
    if not nanite:
        plan["nanite_reason"] = ov.get("nanite_reason", "per-asset override")
    return plan


# ---------------------------------------------------------------- verdict

def _close(a, b, tol):
    """Both sides must be exactly 3 numbers (x, y, z) and each axis within tol.

    zip() alone would let empty or short lists pass vacuously (review 48565 fix 1)."""
    try:
        a, b = list(a), list(b)
    except TypeError:
        return False
    if len(a) != 3 or len(b) != 3:
        return False
    try:
        return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))
    except (TypeError, ValueError):
        return False


def evaluate(plan, done, facts, before_identity=None, save_passes=None):
    """Turn raw editor facts into a verdict. 'done' alone is never success."""
    checks, notes = {}, []
    checks["completed"] = bool(done and done.get("done"))
    if not checks["completed"]:
        return {"ok": False, "checks": checks, "notes": ["not complete: started != done"]}
    # Review 48565 fix 2: a missing mesh must fail on its own. Without this, a Nanite-off plan
    # passed nanite_as_planned with mesh None (None == False), and only inventory_count caught it.
    mesh_found = facts.get("mesh_found", facts.get("mesh", True) is not None)
    checks["mesh_found"] = bool(mesh_found)
    if not checks["mesh_found"]:
        notes.append("mesh %r not found under %s" % (plan.get("asset"), plan.get("destination")))
    exp = plan.get("expect", {})
    inv = facts.get("inventory", [])
    if "inventory_count" in exp:
        checks["inventory_exact"] = len(inv) == exp["inventory_count"]
    if "slots" in exp:
        got = [m.get("slot") for m in facts.get("materials", [])]
        checks["slots_exact_order"] = got == exp["slots"]
    if "triangles" in exp:
        checks["triangles"] = facts.get("tris_lod0") == exp["triangles"]
    if "min_cm" in exp and "max_cm" in exp:
        tol = exp.get("bounds_tolerance_cm", 0.2)
        checks["bounds"] = _close(facts.get("bounds_min_cm", []), exp["min_cm"], tol) and _close(facts.get("bounds_max_cm", []), exp["max_cm"], tol)
    checks["nanite_as_planned"] = (checks["mesh_found"] and facts.get("nanite") is not None
                                   and bool(facts.get("nanite")) == bool(plan["options"]["build_nanite"]))
    if plan["glb"]["ucx"] and plan["options"]["collision_from_ucx"]:
        checks["ucx_convex"] = (facts.get("collision", {}).get("convex", 0) >= len(plan["glb"]["ucx"]))
    want = {s["name"] for s in plan["sockets"]["sockets"]}
    if want:
        have = {s.get("name") for s in facts.get("sockets", [])}
        checks["sockets_added"] = want <= have
    if before_identity is not None:
        checks["same_uobject"] = bool(before_identity.get("same_uobject"))
    if save_passes is not None:
        checks["saved_clean"] = save_passes.get("dirty_after") == [] and save_passes.get("passes", 0) <= MAX_SAVE_PASSES
        if save_passes.get("passes", 0) > 1:
            notes.append("needed %d save passes (MIC re-dirty)" % save_passes["passes"])
    notes.extend(plan["sockets"]["warnings"])
    notes.extend(plan["material_review"])
    return {"ok": all(checks.values()), "checks": checks, "notes": notes}


def terrain_profile(source_packet_path, expected_sha256=None):
    """Five-slot receiver profile from a frozen BIP1 source packet (e.g. 519f28bb for terrain_33)."""
    with open(source_packet_path, "rb") as fh:
        raw = fh.read()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and digest != expected_sha256.lower():
        raise PlanError("source packet sha mismatch")
    sp = json.loads(raw.decode("utf-8-sig"))
    rc, tc = sp["receiving_contract"], sp["transform_contract"]
    slots = [s["material"]["name"] for s in sorted(sp["slots"], key=lambda s: s["slot"])]
    opts = dict(rc["interchange_requested_options"])
    opts["nanite_reason"] = "source packet %s freezes build_nanite=false" % digest[:8]
    return {
        "source_packet_sha256": digest,
        "destination": rc["proposed_root"],
        "interchange_requested_options": opts,
        "expect": {
            "inventory_count": 1 + len(slots),
            "slots": slots,
            "triangles": sp["triangles"],
            "min_cm": tc["expected_native_min_cm"],
            "max_cm": tc["expected_native_max_cm"],
            "bounds_tolerance_cm": tc.get("bounds_tolerance_cm", 0.2),
        },
        "packet": sp["source_pins"]["packet"],
        "material_factors": {s["material"]["name"]: s["material"].get("pbrMetallicRoughness", {}) for s in sp["slots"]},
    }