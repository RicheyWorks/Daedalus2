# SPDX-License-Identifier: MIT
"""Import a validated Blender handoff GLB without opening or contacting Blender.

The caller owns queue/job result writes. This module reads the handoff and
retains a byte-identical, content-addressed import cache for Unreal Reimport.
It preserves the existing import judge, including its current rotation limits.
"""
import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys
import tempfile
import time
from pathlib import Path

from . import glb, ship, sides, wire

BUDGET = {"Tool": 3000, "Item": 3000, "Wpn": 3000, "Prop": 3000,
          "Mob": 6000, "Veh": 12000, "Bld": 15000, "Sky": 15000}
MAX_SLOTS = 3
NAME = re.compile(r"^(Tool|Item|Wpn|Prop|Mob|Veh|Bld|Sky)_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*$")

# Keep the established import/material/source-triangle behavior, with two local
# guards. Never accept old destination contents as evidence of this attempt.
_IMPORT_TASK = "task = unreal.AssetImportTask()"
_EMPTY_FALLBACK = '''if not paths:
    paths = [str(p) for p in unreal.EditorAssetLibrary.list_assets(P["dest"], recursive=True)]'''
if sides.UNREAL_IMPORT.count(_EMPTY_FALLBACK) != 1 or sides.UNREAL_IMPORT.count(_IMPORT_TASK) != 1:
    raise RuntimeError("Unreal import template changed; review the strict import guards")
STRICT_UNREAL_IMPORT = sides.UNREAL_IMPORT.replace(
    _IMPORT_TASK,
    '''if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is not None:
    raise RuntimeError("Unreal is in Play mode; retry after Play ends")
task = unreal.AssetImportTask()''', 1).replace(
    _EMPTY_FALLBACK,
    '''if not paths:
    raise RuntimeError("Unreal returned no imported_object_paths for this attempt")''', 1)


def _fail(message):
    raise ValueError(message)


def _inside(path, directory, label):
    try:
        path.relative_to(directory)
    except ValueError:
        _fail("%s must stay within %s" % (label, directory))


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _dims(value, label):
    if not isinstance(value, list) or len(value) != 3 or not all(_number(x) and x >= 0 for x in value):
        _fail("%s must contain three finite, nonnegative dimensions" % label)
    if value != sorted(value, reverse=True):
        _fail("%s must be sorted largest first" % label)
    return value


def _materials(value, label):
    if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
        _fail("%s must be a list of material names" % label)
    if len(set(value)) != len(value):
        _fail("%s has duplicate material names" % label)
    return value


def _document(data):
    """Check the GLB container before using the existing JSON-side reader."""
    if len(data) < 20:
        _fail("GLB is truncated")
    magic, version, total = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or total != len(data):
        _fail("GLB must be a complete version-2 container with the stated length")
    pos, document, binary = 12, None, None
    while pos < len(data):
        if pos + 8 > len(data):
            _fail("GLB has a truncated chunk header")
        length, kind = struct.unpack_from("<I4s", data, pos)
        pos += 8
        if length % 4 or pos + length > len(data):
            _fail("GLB has an invalid or truncated chunk")
        if document is None:
            if kind != b"JSON":
                _fail("GLB first chunk must be JSON")
            try:
                document = json.loads(data[pos:pos + length].decode("utf-8"))
            except (UnicodeError, ValueError) as exc:
                raise ValueError("GLB JSON is invalid") from exc
        elif kind == b"JSON":
            _fail("GLB has more than one JSON chunk")
        elif kind == b"BIN\x00":
            if binary is not None:
                _fail("GLB has more than one BIN chunk")
            binary = data[pos:pos + length]
        pos += length
    if not isinstance(document, dict):
        _fail("GLB JSON must be an object")
    # A snapshot cannot safely witness files outside its own bytes.
    for key in ("buffers", "images"):
        entries = document.get(key, [])
        if not isinstance(entries, list):
            _fail("GLB %s must be a list" % key)
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("uri"):
                _fail("GLB handoff must embed all buffers and images")
    buffers = document.get("buffers", [])
    if len(buffers) > 1:
        _fail("GLB handoff must use at most one embedded buffer")
    if buffers:
        length = buffers[0].get("byteLength")
        if type(length) is not int or length < 0:
            _fail("GLB buffer byteLength must be a nonnegative integer")
        if length and binary is None:
            _fail("GLB is missing its declared BIN buffer")
        if binary is not None and not length <= len(binary) <= length + 3:
            _fail("GLB BIN chunk does not match its declared buffer byteLength")
    views, accessors = document.get("bufferViews", []), document.get("accessors", [])
    if not isinstance(views, list) or not isinstance(accessors, list):
        _fail("GLB bufferViews and accessors must be lists")
    for view in views:
        if not isinstance(view, dict) or type(view.get("buffer")) is not int or view["buffer"] != 0 or not buffers:
            _fail("GLB bufferViews must reference the embedded buffer")
        offset, size = view.get("byteOffset", 0), view.get("byteLength")
        if type(offset) is not int or type(size) is not int or offset < 0 or size < 0 or offset + size > buffers[0]["byteLength"]:
            _fail("GLB bufferView range exceeds the embedded buffer")
    for accessor in accessors:
        if not isinstance(accessor, dict):
            _fail("GLB accessors must be objects")
        if "bufferView" in accessor:
            index = accessor["bufferView"]
            if type(index) is not int or not 0 <= index < len(views):
                _fail("GLB accessor bufferView index is invalid")
        if type(accessor.get("count")) is not int or accessor["count"] < 0:
            _fail("GLB accessor counts must be nonnegative integers")
    meshes = document.get("meshes", [])
    if not isinstance(meshes, list):
        _fail("GLB meshes must be a list")
    for mesh in meshes:
        if not isinstance(mesh, dict) or not isinstance(mesh.get("primitives"), list):
            _fail("GLB meshes need primitives")
        for primitive in mesh["primitives"]:
            if not isinstance(primitive, dict) or not isinstance(primitive.get("attributes"), dict) or "POSITION" not in primitive["attributes"]:
                _fail("GLB primitives need POSITION attributes")
            indexes = list(primitive["attributes"].values()) + ([primitive["indices"]] if "indices" in primitive else [])
            if not all(type(i) is int and 0 <= i < len(accessors) for i in indexes):
                _fail("GLB primitive accessor index is invalid")
    return document


def _validated(job_path, asset, handoff_root):
    job_path = Path(job_path).resolve(strict=True)
    root = Path(handoff_root).resolve(strict=True) if handoff_root is not None else job_path.parent.parent
    jobs_dir, glb_dir = (root / "jobs").resolve(), (root / "glb").resolve()
    _inside(jobs_dir, root, "jobs directory")
    _inside(glb_dir, root, "GLB directory")
    _inside(job_path, jobs_dir, "job path")
    with job_path.open(encoding="utf-8-sig") as stream:
        job = json.load(stream)
    if not isinstance(job, dict) or type(job.get("spec")) is not int or job["spec"] != 1:
        _fail("handoff must use spec 1")
    name, kind = job.get("asset"), job.get("kind")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        _fail("asset must be a safe Kind_Name")
    if asset is not None and asset != name:
        _fail("handoff asset does not match the expected asset")
    if kind != name.split("_", 1)[0] or kind not in BUDGET:
        _fail("handoff kind does not match the asset")
    if job_path.name != name + ".json":
        _fail("job filename must match the asset")
    record = job.get("blender")
    if not isinstance(record, dict):
        _fail("handoff needs a blender record")
    selfcheck = record.get("selfcheck")
    if not isinstance(selfcheck, dict) or selfcheck.get("ok") is not True or selfcheck.get("fails") != []:
        _fail("Blender selfcheck must pass with an empty fails list")
    source = record.get("glb")
    if not isinstance(source, str) or not source:
        _fail("handoff needs a GLB path")
    source = Path(source)
    source = (root / source).resolve(strict=True) if not source.is_absolute() else source.resolve(strict=True)
    _inside(source, glb_dir, "GLB path")
    if source.name != name + ".glb":
        _fail("GLB filename must match the asset")
    expected_hash = record.get("glb_sha1")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", expected_hash):
        _fail("handoff needs a valid GLB SHA1")
    data = source.read_bytes()  # Capture once: all following checks/import use these bytes.
    digest = hashlib.sha1(data).hexdigest()
    if digest != expected_hash.lower():
        _fail("GLB SHA1 does not match the handoff")
    document = _document(data)
    meshes = record.get("meshes")
    if not isinstance(meshes, list) or not meshes:
        _fail("handoff needs at least one mesh")
    objects, names = [], set()
    for mesh in meshes:
        if not isinstance(mesh, dict):
            _fail("handoff meshes must be objects")
        mesh_name, triangles = mesh.get("name"), mesh.get("tris")
        if not isinstance(mesh_name, str) or not mesh_name or mesh_name in names:
            _fail("handoff mesh names must be nonempty and unique")
        names.add(mesh_name)
        if type(triangles) is not int or triangles <= 0:
            _fail("handoff mesh triangles must be positive integers")
        materials = _materials(mesh.get("materials"), "mesh materials")
        if not 1 <= len(materials) <= MAX_SLOTS:
            _fail("each handoff mesh must have 1-3 material slots")
        objects.append({"name": mesh_name, "triangles": triangles, "materials": materials,
                        "dims": _dims(mesh.get("dims_m"), "mesh dims_m")})
    total = sum(obj["triangles"] for obj in objects)
    if type(record.get("tris")) is not int or record["tris"] != total:
        _fail("handoff triangle total does not match its meshes")
    if total > BUDGET[kind]:
        _fail("triangle budget exceeded (%s %d)" % (kind, BUDGET[kind]))
    used = {material for obj in objects for material in obj["materials"]}
    if set(_materials(record.get("materials"), "handoff materials")) != used:
        _fail("handoff material total does not match its meshes")
    raw_nodes = document.get("nodes", [])
    if not isinstance(raw_nodes, list):
        _fail("GLB nodes must be a list")
    for node in raw_nodes:
        if not isinstance(node, dict):
            _fail("GLB nodes must be objects")
        scale = node.get("scale", [1, 1, 1])
        if not isinstance(scale, list) or len(scale) != 3 or not all(_number(x) and abs(x - 1) <= 1e-4 for x in scale):
            _fail("GLB node scales must be applied")
        if "matrix" in node:
            _fail("GLB node matrices are not supported by the handoff witness")
    return job_path, root, name, kind, source, data, digest, objects


def _witness(path, objects):
    try:
        witness = glb.summarize(str(path))
        nodes, meshes = witness["nodes"], witness["meshes"]
        expected = {obj["name"]: obj for obj in objects}
        if len(nodes) != len(expected) or len(meshes) != len(expected):
            _fail("GLB must contain one mesh and node per manifest mesh")
        actual, node_names, node_meshes = {}, set(), set()
        for node in nodes:
            node_name, index = node["name"], node["mesh"]
            if not isinstance(node_name, str) or not node_name or node_name in node_names:
                _fail("GLB node names must be nonempty and unique")
            if type(index) is not int or not 0 <= index < len(meshes) or index in node_meshes:
                _fail("GLB must have one distinct mesh per node")
            node_names.add(node_name)
            node_meshes.add(index)
            mesh = meshes[index]
            name = mesh["name"]  # Blender object names can differ from mesh-data names (e.g. .001).
            if name in actual or name not in expected:
                _fail("GLB mesh names do not match the manifest")
            actual[name] = mesh
            obj = expected[name]
            if mesh["triangles"] != obj["triangles"]:
                _fail("GLB triangles differ from manifest for " + name)
            if set(mesh["materials"]) != set(obj["materials"]):
                _fail("GLB materials differ from manifest for " + name)
            dims = _dims(mesh["dims"], "GLB mesh dimensions")
            if not ship._dims_match(obj["dims"], dims) or not ship._dims_match(obj["dims"], node["dims"]):
                _fail("GLB dimensions differ from manifest for " + name)
        if set(actual) != set(expected):
            _fail("GLB is missing manifest nodes")
        return witness
    except (KeyError, IndexError, TypeError, struct.error) as exc:
        raise ValueError("GLB geometry metadata is invalid") from exc


def _current_import(made):
    """Reject malformed or stale editor evidence before calling the current judge."""
    def blocked(message):
        raise wire.BridgeError("Unreal", {"message": message})
    if not isinstance(made, dict) or made.get("error"):
        blocked("Unreal import failed: %s" % (made.get("error") if isinstance(made, dict) else "missing result"))
    paths, meshes, materials = made.get("imported"), made.get("meshes"), made.get("materials")
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p for p in paths):
        blocked("Unreal returned no current imported_object_paths")
    if not isinstance(meshes, list) or not meshes:
        blocked("Unreal imported no static meshes for this attempt")
    if not isinstance(materials, list):
        blocked("Unreal import did not report materials")
    material_paths = set()
    for material in materials:
        if not isinstance(material, dict) or not all(isinstance(material.get(k), str) and material[k] for k in ("path", "name")):
            blocked("Unreal has invalid material evidence")
        if material["path"] in material_paths:
            blocked("Unreal material evidence contains duplicate paths")
        # ADR-055 judges the observed parent after repair. Missing evidence must
        # not silently become the explicit empty parent of a direct Material.
        if not isinstance(material.get("parent"), str):
            blocked("Unreal material must report string parent evidence (empty for a direct Material)")
        material_paths.add(material["path"])
    reported = set()
    for mesh in meshes:
        if not isinstance(mesh, dict) or mesh.get("path") not in paths or mesh.get("path") in reported:
            blocked("Unreal mesh evidence must belong to this current import")
        reported.add(mesh["path"])
        if type(mesh.get("triangles")) is not int or mesh["triangles"] < 0:
            blocked("Unreal mesh has invalid triangle evidence")
        if not isinstance(mesh.get("name"), str) or not mesh["name"]:
            blocked("Unreal mesh has invalid name evidence")
        if not isinstance(mesh.get("materials"), list) or not all(isinstance(m, str) and m for m in mesh["materials"]):
            blocked("Unreal mesh has invalid material-slot evidence")
        dims = mesh.get("dims_cm")
        if not isinstance(dims, list) or len(dims) != 3 or not all(_number(x) and x >= 0 for x in dims):
            blocked("Unreal mesh has invalid size evidence")
    return made


def _snapshot(root, name, digest, data):
    """Publish once, atomically; retain the source file Unreal records for Reimport."""
    directory = root / "import-cache" / digest
    if directory.resolve() != directory:
        _fail("import cache directories must not redirect through links")
    _inside(directory.resolve(), root, "import cache")
    directory.mkdir(parents=True, exist_ok=True)
    if directory.resolve(strict=True) != directory:
        _fail("import cache directory changed or redirects through a link")
    snapshot = directory / (name + ".glb")
    if snapshot.resolve() != snapshot:
        _fail("import snapshot must not redirect through a link")
    if not snapshot.exists():
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".snapshot-", dir=directory, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                if os.name == "nt":
                    os.rename(temporary, snapshot)  # Windows rename atomically refuses an existing destination.
                else:
                    os.link(temporary, snapshot)  # POSIX rename overwrites; use an exclusive link publication.
            except FileExistsError:
                pass
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    if snapshot.resolve(strict=True) != snapshot or snapshot.stat().st_nlink > 1:
        _fail("import snapshot aliases another file; refusing mutable shared cache data")
    if snapshot.read_bytes() != data:
        _fail("existing import snapshot differs from the validated GLB; refusing to overwrite it")
    return snapshot


def _report_path(path, root, job_path, source):
    target = Path(path).resolve()
    for directory in ("jobs", "glb", "import-cache"):
        try:
            target.relative_to((root / directory).resolve())
        except ValueError:
            continue
        _fail("report output must not overwrite handoff jobs, GLBs or import cache")
    if target.exists():
        if target.stat().st_nlink > 1 or any(target.samefile(p) for p in (job_path, source)):
            _fail("report output aliases protected handoff data")
    target.parent.resolve(strict=True)  # Refuse an unusable report path before any editor call.
    return target


def ship_saved(job_path, dest=None, save=True, unreal=wire.UNREAL, timeout=600, *, asset=None, handoff_root=None):
    """Validate spec-1 handoff, import its exact bytes, and return a shipment report.

    dest is the parent Unreal folder; /<asset> is appended, as in ship.ship.
    Invalid art raises ValueError/OSError before an editor call. Editor failures
    raise BridgeError; geometry preservation failures produce report['ok']=False.
    """
    started = time.time()
    job_path, root, name, kind, source, data, digest, objects = _validated(job_path, asset, handoff_root)
    dest = dest if dest is not None else "/Game/Daedalus/Art/" + kind
    if not isinstance(dest, str) or not re.fullmatch(r"/Game(?:/[A-Za-z0-9_]+)*", dest.rstrip("/")):
        _fail("dest must be an Unreal /Game parent folder")
    destination = dest.rstrip("/") + "/" + name
    sent = {"objects": objects, "path": str(source), "bytes": len(data), "source": "saved manifest"}
    # Refuse invalid manifest/file facts before publishing a retained cache blob.
    with tempfile.TemporaryDirectory(prefix="daedalus-glb-check-") as directory:
        temporary = Path(directory) / (name + ".glb")
        temporary.write_bytes(data)
        witness = _witness(temporary, objects)
    snapshot = _snapshot(root, name, digest, data)
    try:
        response = wire.call(unreal, "execute_python", timeout=timeout, side="Unreal",
                             code=sides.script(STRICT_UNREAL_IMPORT, path=str(snapshot), dest=destination, save=save))
    except (OSError, ValueError) as exc:
        raise wire.BridgeError("Unreal", {"message": "import connection failed: %s" % exc}) from exc
    made = _current_import(response.get("result") if isinstance(response, dict) else None)
    checks = ship.judge(sent, witness, made)
    checks += [{"check": "triangle budget (%s %d)" % (kind, BUDGET[kind]), "ok": True,
                "detail": "%d triangles" % sum(obj["triangles"] for obj in objects)},
               {"check": "material slots ≤ %d" % MAX_SLOTS, "ok": True,
                "detail": str(max(len(obj["materials"]) for obj in objects))}]
    return {"name": name, "path": str(source), "dest": destination, "started": started,
            "ok": all(check["ok"] for check in checks), "checks": checks, "blender": sent,
            "file": witness, "unreal": made, "seconds": round(time.time() - started, 2),
            "provenance": {"job_path": str(job_path), "handoff_root": str(root), "source_glb": str(source),
                           "source_sha1": digest, "import_snapshot": str(snapshot), "snapshot_sha1": digest,
                           "snapshot_retained": True, "imported_object_paths": list(made["imported"])}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--job", required=True)
    parser.add_argument("--name", help="assert the expected asset name")
    parser.add_argument("--dest", help="parent Unreal folder")
    parser.add_argument("--report")
    parser.add_argument("--unreal-port", type=int, default=wire.UNREAL[1])
    args = parser.parse_args(argv)
    try:
        report_path = None
        if args.report:
            job_path, root, _, _, source, _, _, _ = _validated(args.job, args.name, None)
            report_path = _report_path(args.report, root, job_path, source)
        report = ship_saved(args.job, args.dest, unreal=(wire.UNREAL[0], args.unreal_port), asset=args.name)
        if args.report:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=report_path.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    json.dump(report, stream, indent=2)
                os.replace(temporary, report_path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    except (ValueError, OSError, wire.BridgeError) as exc:
        print("FAIL  %s" % exc)
        return 2
    for check in report["checks"]:
        print("%-4s  %-46s %s" % ("ok" if check["ok"] else "FAIL", check["check"], check["detail"]))
    print("%s  %s -> %s in %.1fs" % ("SHIPPED" if report["ok"] else "REJECTED",
                                     report["path"], report["dest"], report["seconds"]))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
