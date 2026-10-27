# SPDX-License-Identifier: MIT
"""Pure preservation plans; these functions never import or alter native assets."""

import hashlib
import json
import re

from .reader_adapter import PlanError, member_path, read_snapshot

ROOT = "/Game/Daedalus/PackageImports"
RECEIPT_KEYS = {"format", "version", "status", "world_id", "revision", "package_sha256",
                "destination_root", "acceptance_reference"}


def _text(value, field, maximum=512):
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum or
            any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise PlanError(field + " must be a nonempty bounded text value without controls")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise PlanError(field + " must be valid Unicode") from error
    return value


def _integer(value, field):
    if type(value) is not int or value < 0 or value > 2 ** 63 - 1:
        raise PlanError(field + " must be a nonnegative signed 64-bit integer")
    return value


def _segment(value):
    stem = re.sub(r"[^A-Za-z0-9_]", "_", value)[:16].strip("_") or "item"
    return stem + "_" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def destination(world_id, revision, package_sha256):
    identity = json.dumps([world_id, revision, package_sha256], ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    stem = re.sub(r"[^A-Za-z0-9_]", "_", world_id)[:16].strip("_") or "world"
    return ROOT + "/" + stem + "_r" + str(revision) + "_" + digest


def validate_receipt(receipt):
    """Validate explicitly supplied owner evidence; does not verify native effects."""
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
        raise PlanError("prior receipt has missing or unknown fields")
    if (receipt["format"] != "daedalus-world-import-receipt" or
            type(receipt["version"]) is not int or receipt["version"] != 1 or receipt["status"] != "accepted"):
        raise PlanError("prior receipt is not a supported accepted receipt")
    world_id = _text(receipt["world_id"], "prior world_id")
    revision = _integer(receipt["revision"], "prior revision")
    digest = receipt["package_sha256"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise PlanError("prior package_sha256 must be a lowercase SHA-256")
    _text(receipt["acceptance_reference"], "prior acceptance_reference", maximum=2048)
    if receipt["destination_root"] != destination(world_id, revision, digest):
        raise PlanError("prior destination does not bind its raw world identity, revision and package")
    return receipt


def build_plan(zip_path, prior_receipt=None):
    """Plan new immutable destinations, or an exact no-op from supplied evidence.

    No receipt is inferred from a directory, a sanitized world name or an earlier
    plan. Receipt authenticity/current custody remains the native owner's check.
    """
    manifest, names, digest, size = read_snapshot(zip_path)
    world = manifest.get("world")
    geometry = manifest.get("geometry")
    if not isinstance(world, dict) or not isinstance(geometry, dict):
        raise PlanError("manifest world and geometry must be objects")
    world_id = _text(world.get("id"), "world.id")
    revision = _integer(world.get("revision"), "world.revision")
    # bool compares equal to 1 in Python, so refuse it explicitly at the boundary.
    if type(manifest.get("version")) is not int:
        raise PlanError("package version must be an integer")
    chunks = _integer(geometry.get("chunks"), "geometry.chunks")
    triangles = _integer(geometry.get("triangles"), "geometry.triangles")
    if geometry.get("file") != "world.glb":
        raise PlanError("geometry.file must name the validated world.glb")
    root = destination(world_id, revision, digest)
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        raise PlanError("manifest assets must be an array")
    planned_assets = []
    asset_names = set()
    asset_files = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise PlanError("each asset must be an object")
        name = _text(asset.get("name"), "asset.name")
        file = member_path(asset.get("file"))
        use = _text(asset.get("use"), "asset.use")
        if file not in names or not file.startswith("assets/") or not file.endswith(".glb"):
            raise PlanError("asset.file must name an existing assets/*.glb member")
        if name.casefold() in asset_names or file.casefold() in asset_files:
            raise PlanError("duplicate or case-colliding asset identity")
        asset_names.add(name.casefold())
        asset_files.add(file.casefold())
        planned_assets.append({"name": name, "file": file, "use": use,
                               "destination": root + "/Assets/" + _segment(name)})
    plan = {"format": "daedalus-world-import-plan", "version": 1, "action": "plan_new",
            "world": {"id": world_id, "revision": revision},
            "source": {"format": manifest["format"], "version": manifest["version"],
                       "package_sha256": digest, "package_bytes": size},
            "destination": {"root": root, "level": root + "/L_World",
                            "materials": root + "/Materials", "geometry": root + "/Geometry/world"},
            "geometry": {"file": "world.glb", "chunks": chunks, "triangles": triangles},
            "assets": planned_assets, "previous_destination_root": None,
            "policy": {"replace_existing": False, "delete_existing": False,
                       "use_shared_materials": False, "connect_live": False,
                       "requires_native_owner_review": True},
            "native_acceptance": False}
    return _apply_receipt(plan, prior_receipt)


def _apply_receipt(plan, prior_receipt):
    """Apply evidence to a freshly validated in-process plan without rereading ZIPs.

    Internal composition boundary, not a loader for saved/untrusted plans.
    """
    if prior_receipt is None:
        return plan
    prior = validate_receipt(prior_receipt)
    if prior["world_id"] != plan["world"]["id"]:
        raise PlanError("prior receipt belongs to a different raw world ID")
    revision = plan["world"]["revision"]
    if revision < prior["revision"]:
        raise PlanError("requested revision predates the accepted revision")
    action = "plan_new"
    if revision == prior["revision"]:
        if (plan["source"]["package_sha256"] != prior["package_sha256"] or
                plan["destination"]["root"] != prior["destination_root"]):
            raise PlanError("accepted world revision has conflicting package bytes")
        action = "no_op"
    return dict(plan, action=action, previous_destination_root=prior["destination_root"])
