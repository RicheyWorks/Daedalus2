# SPDX-License-Identifier: MIT
"""Pinned, offline subsets for 1-3 static root mesh nodes. Never contacts an editor.

Plan and admit completed GLBs, or extract a source-derived GLB subset by copying
referenced binary spans. Export publishes only to a fresh explicit file path.
CLI receipts are JSON on stdout; no command dispatches native intake.
"""
import argparse
import copy
import hashlib
import json
import math
import os
import struct
import sys
import tempfile

SCHEMA = "daedalus.static-subset.v1"
MAX_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_ACCESSOR_ROWS = 100_000
MAX_DECODED_SCALARS = 1_000_000
MAX_TRIANGLES = 100_000
MAX_CANONICAL_BYTES = 16 * 1024 * 1024
MAX_ATTRIBUTES = 16
MAX_ATTRIBUTE_NAME = 64
COMPONENTS = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _names(names):
    if not isinstance(names, (list, tuple)) or not 1 <= len(names) <= 3:
        raise ValueError("selection requires 1-3 explicit node names")
    if any(not isinstance(n, str) or not n.strip() or n != n.strip() for n in names):
        raise ValueError("node names must be nonempty exact strings")
    if len(set(names)) != len(names):
        raise ValueError("duplicate node names in selection")
    return list(names)


def _pin(expected):
    if not isinstance(expected, dict):
        raise ValueError("an expected sha256 and byte count are required")
    digest, size = expected.get("sha256"), expected.get("bytes")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
            or type(size) is not int or not 0 < size <= MAX_BYTES):
        raise ValueError("invalid expected sha256 or byte count (limit 64 MiB)")
    return {"sha256": digest, "bytes": size}


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("invalid " + label)
    return value


def _item(items, index, label):
    _integer(index, label)
    if index >= len(items):
        raise ValueError("out of range " + label)
    return items[index]


def _objects(value, label):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("invalid " + label + " records")
    return value


def _file_bytes(path, expected):
    """Read at most the pinned size plus one byte, including during final checks."""
    expected = _pin(expected)
    if os.path.getsize(path) != expected["bytes"]:
        raise ValueError("artifact identity mismatch: " + os.fspath(path))
    with open(path, "rb") as source:
        data = source.read(expected["bytes"] + 1)
    if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
        raise ValueError("artifact changed while collecting binary witness")
    return data


def _read(path, expected):
    data = _file_bytes(path, expected)
    if len(data) < 28 or struct.unpack_from("<4sII", data) != (b"glTF", 2, len(data)):
        raise ValueError("invalid GLB header or declared length")
    chunks, offset = [], 12
    for expected_kind in (b"JSON", b"BIN\x00"):
        if offset + 8 > len(data):
            raise ValueError("truncated GLB chunk header")
        size, kind = struct.unpack_from("<I4s", data, offset)
        offset += 8
        if kind != expected_kind or size % 4 or offset + size > len(data):
            raise ValueError("invalid GLB chunk length")
        if kind == b"JSON" and size > MAX_JSON_BYTES:
            raise ValueError("JSON metadata work limit exceeded")
        chunks.append((kind, data[offset:offset + size]))
        offset += size
    if offset != len(data):
        raise ValueError("require one embedded JSON and BIN chunk")
    # Parse the already bounded, pinned bytes, rather than reopening an unchecked
    # metadata chunk. The public pin shape matches the existing pipeline.
    doc = json.loads(chunks[0][1])
    if (not isinstance(doc, dict) or not isinstance(doc.get("asset"), dict)
            or doc["asset"].get("version") != "2.0"):
        raise ValueError("require glTF 2.0")
    for key in ("skins", "animations", "images", "textures", "cameras", "extensions", "extensionsUsed", "extensionsRequired"):
        if doc.get(key):
            raise ValueError("unsupported static subset feature: " + key)
    buffers = _objects(doc.get("buffers", []), "buffer")
    if len(buffers) != 1 or "uri" in buffers[0] or buffers[0].get("extensions"):
        raise ValueError("require one embedded buffer")
    length = _integer(buffers[0].get("byteLength"), "buffer byteLength", 1)
    binary = chunks[1][1]
    if not 0 <= len(binary) - length <= 3:
        raise ValueError("BIN length differs from declared buffer")
    return doc, binary[:length]


def _accessor(doc, binary, index, budget, vertex=False):
    acc = _item(doc.get("accessors", []), index, "accessor")
    if "sparse" in acc or acc.get("extensions"):
        raise ValueError("sparse/extended accessors are outside this static slice")
    view_index = acc.get("bufferView")
    view = _item(doc.get("bufferViews", []), view_index, "bufferView")
    if _integer(view.get("buffer", 0), "buffer index") != 0 or view.get("extensions"):
        raise ValueError("require an unextended embedded bufferView")
    component, width = acc.get("componentType"), WIDTHS.get(acc.get("type"))
    if component not in COMPONENTS or width is None:
        raise ValueError("unsupported accessor type")
    count = _integer(acc.get("count"), "accessor count", 1)
    if count > MAX_ACCESSOR_ROWS or count * width > budget["scalars"]:
        raise ValueError("decoded accessor work limit exceeded")
    budget["scalars"] -= count * width
    fmt = "<" + COMPONENTS[component] * width
    packed = struct.calcsize(fmt)
    component_size = struct.calcsize("<" + COMPONENTS[component])
    stride = _integer(view.get("byteStride", packed), "byteStride", packed)
    view_start = _integer(view.get("byteOffset", 0), "bufferView byteOffset")
    view_length = _integer(view.get("byteLength"), "bufferView byteLength", 1)
    start = _integer(acc.get("byteOffset", 0), "accessor byteOffset")
    if start % component_size or (view_start + start) % component_size:
        raise ValueError("misaligned accessor component")
    if "byteStride" in view and (not vertex or stride % 4 or not 4 <= stride <= 252):
        raise ValueError("invalid vertex byteStride")
    if vertex and (start % 4 or (view_start + start) % 4 or stride % 4):
        raise ValueError("misaligned vertex attribute")
    normalized = acc.get("normalized", False)
    if type(normalized) is not bool or (normalized and component in (5125, 5126)):
        raise ValueError("invalid accessor normalization")
    if view_start + view_length > len(binary) or start + (count - 1) * stride + packed > view_length:
        raise ValueError("accessor exceeds its bufferView")
    rows = [struct.unpack_from(fmt, binary, view_start + start + i * stride) for i in range(count)]
    if any(not math.isfinite(v) for row in rows for v in row):
        raise ValueError("non-finite accessor value")
    description = (component, acc["type"], normalized)
    return rows, description, view_index


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _charge(budget, value):
    encoded = _canonical(value)
    budget["canonical"] -= len(encoded.encode("utf-8"))
    if budget["canonical"] < 0:
        raise ValueError("canonical witness work limit exceeded")
    return encoded


def _transform(node):
    if "matrix" in node:
        if any(k in node for k in ("translation", "rotation", "scale")):
            raise ValueError("matrix and TRS cannot coexist")
        result = {"matrix": node["matrix"]}
        lengths = {"matrix": 16}
    else:
        result = {"translation": node.get("translation", [0, 0, 0]),
                  "rotation": node.get("rotation", [0, 0, 0, 1]),
                  "scale": node.get("scale", [1, 1, 1])}
        lengths = {"translation": 3, "rotation": 4, "scale": 3}
    for key, values in result.items():
        if not isinstance(values, list) or len(values) != lengths[key]:
            raise ValueError("invalid node transform")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError("non-finite node transform")
    return result


def _inspect(path, expected, names, exact=False):
    doc, binary = _read(path, expected)
    for label in ("nodes", "meshes", "materials", "scenes", "accessors", "bufferViews"):
        _objects(doc.get(label, []), label)
    nodes, meshes, materials = doc.get("nodes", []), doc.get("meshes", []), doc.get("materials", [])
    by_name = {}
    for i, node in enumerate(nodes):
        if node.get("name") is not None and not isinstance(node["name"], str):
            raise ValueError("invalid node name")
        by_name.setdefault(node.get("name"), []).append(i)
    children = set()
    for node in nodes:
        child_list = node.get("children", [])
        if not isinstance(child_list, list):
            raise ValueError("invalid node children")
        for child in child_list:
            _item(nodes, child, "child node")
            children.add(child)
    scene = _item(doc.get("scenes", []), doc.get("scene", 0), "scene")
    roots = scene.get("nodes", [])
    if not isinstance(roots, list):
        raise ValueError("invalid scene nodes")
    for root in roots:
        _item(nodes, root, "scene root")
    if len(set(roots)) != len(roots):
        raise ValueError("duplicate scene roots")
    used_meshes, used_materials, used_accessors, used_views = set(), set(), set(), set()
    budget = {"scalars": MAX_DECODED_SCALARS, "triangles": MAX_TRIANGLES,
              "canonical": MAX_CANONICAL_BYTES}
    witnesses = []
    for name in names:
        hits = by_name.get(name, [])
        if len(hits) != 1:
            raise ValueError("missing or duplicate selected node: " + name)
        node_index = hits[0]
        node = nodes[node_index]
        if node_index not in roots or node_index in children or node.get("children"):
            raise ValueError("selection requires root mesh nodes without children: " + name)
        if "skin" in node or "weights" in node or node.get("extensions"):
            raise ValueError("unsupported selected node: " + name)
        mesh_index = node.get("mesh")
        mesh = _item(meshes, mesh_index, "mesh")
        if "weights" in mesh or mesh.get("extensions"):
            raise ValueError("morph/extended meshes are outside this static slice")
        used_meshes.add(mesh_index)
        primitives, triangles = [], 0
        for prim in _objects(mesh.get("primitives", []), "primitive"):
            if prim.get("mode", 4) != 4 or "targets" in prim or prim.get("extensions"):
                raise ValueError("require static triangle primitives")
            attrs = prim.get("attributes", {})
            if not isinstance(attrs, dict) or "POSITION" not in attrs or any(k.startswith(("JOINTS_", "WEIGHTS_")) for k in attrs):
                raise ValueError("require static POSITION attributes")
            if len(attrs) > MAX_ATTRIBUTES or any(len(key) > MAX_ATTRIBUTE_NAME for key in attrs):
                raise ValueError("attribute metadata work limit exceeded")
            values, formats = {}, {}
            for attr, index in sorted(attrs.items()):
                rows, desc, view = _accessor(doc, binary, index, budget, vertex=True)
                values[attr], formats[attr] = rows, desc
                used_accessors.add(index)
                used_views.add(view)
            count = len(values["POSITION"])
            if formats["POSITION"] != (5126, "VEC3", False) or any(len(rows) != count for rows in values.values()):
                raise ValueError("invalid POSITION or attribute count")
            if "indices" in prim:
                rows, desc, view = _accessor(doc, binary, prim["indices"], budget)
                if desc[0] not in (5121, 5123, 5125) or desc[1] != "SCALAR" or desc[2]:
                    raise ValueError("invalid triangle indices")
                indices = [r[0] for r in rows]
                used_accessors.add(prim["indices"])
                used_views.add(view)
            else:
                indices = list(range(count))
            if len(indices) % 3 or any(i >= count for i in indices):
                raise ValueError("invalid triangle index count/range")
            if len(indices) // 3 > budget["triangles"]:
                raise ValueError("selected triangle work limit exceeded")
            budget["triangles"] -= len(indices) // 3
            material = None
            if "material" in prim:
                index = prim["material"]
                material = _item(materials, index, "material")
                if not isinstance(material.get("name"), str) or not material["name"] or material.get("extensions"):
                    raise ValueError("require named unextended materials")
                pbr = material.get("pbrMetallicRoughness", {})
                if not isinstance(pbr, dict) or pbr.get("extensions"):
                    raise ValueError("require unextended PBR material values")
                if (any(key in material for key in ("normalTexture", "occlusionTexture", "emissiveTexture"))
                        or any(key in pbr for key in ("baseColorTexture", "metallicRoughnessTexture"))):
                    raise ValueError("textured materials are outside this static slice")
                used_materials.add(index)
            metadata = {k: v for k, v in prim.items() if k not in ("attributes", "indices", "material", "mode")}
            _charge(budget, {"metadata": metadata, "material": material})
            corners = [_charge(budget, {a: values[a][i] for a in values}) for i in range(count)]
            faces = []
            for i in range(0, len(indices), 3):
                a, b, c = (corners[j] for j in indices[i:i + 3])
                # A cyclic corner rotation preserves a face; reversing it does not.
                face = min((a, b, c), (b, c, a), (c, a, b))
                _charge(budget, face)
                faces.append(face)
            triangles += len(faces)
            primitives.append({"formats": formats, "material": material,
                               "metadata": metadata,
                               "triangles": len(faces),
                               "geometry_sha256": hashlib.sha256(_canonical(sorted(faces)).encode()).hexdigest()})
        if not primitives or not triangles:
            raise ValueError("selected mesh has no triangles: " + name)
        witnesses.append({"name": name, "transform": _transform(node),
                          "node_metadata": {k: v for k, v in node.items() if k not in ("mesh", "matrix", "translation", "rotation", "scale")},
                          "mesh_metadata": {k: v for k, v in mesh.items() if k != "primitives"},
                          "triangles": triangles, "primitives": sorted(primitives, key=_canonical)})
        _charge(budget, witnesses[-1])
    material_names = [materials[i]["name"] for i in used_materials]
    if len(set(material_names)) != len(material_names):
        raise ValueError("duplicate selected material names")
    if exact:
        if len(nodes) != len(names) or len(roots) != len(names) or len(doc.get("scenes", [])) != 1:
            raise ValueError("candidate contains extra nodes or scenes")
        for label, used in (("meshes", used_meshes), ("materials", used_materials),
                            ("accessors", used_accessors), ("bufferViews", used_views)):
            if len(doc.get(label, [])) != len(used):
                raise ValueError("candidate contains extra " + label)
    return witnesses


def make_plan(source_path, names, expected_source):
    """Describe an explicit selection in a completed, externally pinned source GLB."""
    names, expected = _names(names), _pin(expected_source)
    source_path = os.path.abspath(source_path)
    witnesses = _inspect(source_path, expected, names)
    _file_bytes(source_path, expected)
    return {"schema": SCHEMA, "source": {"path": source_path, **expected}, "nodes": names,
            "expected": json.loads(_canonical(witnesses)), "native_ready": False,
            "scope": "Static root meshes only; no subset export, editor call, import or pivot conversion."}


def _plan_witnesses(plan):
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("unsupported subset plan schema")
    names = _names(plan.get("nodes"))
    source = plan.get("source", {})
    if not isinstance(source, dict) or not isinstance(source.get("path"), str) or not source["path"]:
        raise ValueError("subset plan requires a pinned source path")
    expected = _inspect(source["path"], source, names)
    # JSON round-tripping converts tuples to lists. Compare the persisted form.
    if json.loads(_canonical(expected)) != plan.get("expected"):
        raise ValueError("source witnesses differ from pinned plan")
    return names, source, expected


def _root_matrix(node):
    transform = _transform(node)
    if "matrix" in transform:
        matrix = transform["matrix"]
        if any(abs(matrix[i]) > 1e-9 for i in (3, 7, 11)) or abs(matrix[15] - 1) > 1e-9:
            raise ValueError("geometry manifest requires an affine root matrix")
        return matrix
    x, y, z, w = transform["rotation"]
    if abs(x*x + y*y + z*z + w*w - 1) > 1e-5:
        raise ValueError("geometry manifest requires a unit root quaternion")
    sx, sy, sz = transform["scale"]
    tx, ty, tz = transform["translation"]
    return [(1-2*y*y-2*z*z)*sx, (2*x*y+2*z*w)*sx, (2*x*z-2*y*w)*sx, 0,
            (2*x*y-2*z*w)*sy, (1-2*x*x-2*z*z)*sy, (2*y*z+2*x*w)*sy, 0,
            (2*x*z+2*y*w)*sz, (2*y*z-2*x*w)*sz, (1-2*x*x-2*y*y)*sz, 0,
            tx, ty, tz, 1]


def _bounds(lo, hi):
    size = [b-a for a, b in zip(lo, hi)]
    if any(not math.isfinite(v) for v in lo + hi + size):
        raise ValueError("non-finite geometry manifest bounds")
    return {"min": lo, "max": hi, "size": size}


def _geometry_manifest(path, expected, names):
    """Describe actual referenced corners in the GLB source coordinate system."""
    doc, binary = _read(path, expected)
    by_name = {node.get("name"): (i, node) for i, node in enumerate(doc["nodes"])}
    budget = {"scalars": MAX_DECODED_SCALARS}
    nodes, all_lo, all_hi = [], [math.inf]*3, [-math.inf]*3
    for name in names:
        node_index, node = by_name[name]
        mesh = doc["meshes"][node["mesh"]]
        matrix = _root_matrix(node)
        lo, hi = [math.inf]*3, [-math.inf]*3
        world_lo, world_hi = [math.inf]*3, [-math.inf]*3
        materials, material_order, triangles, attributes = [], [], 0, set()
        for prim in mesh["primitives"]:
            positions, _, _ = _accessor(doc, binary, prim["attributes"]["POSITION"], budget, vertex=True)
            if "indices" in prim:
                indices, _, _ = _accessor(doc, binary, prim["indices"], budget)
                indices = [row[0] for row in indices]
            else:
                indices = range(len(positions))
            triangles += len(indices) // 3
            attributes.update(prim["attributes"])
            material = prim.get("material")
            materials.append(material)
            if material is not None and material not in material_order:
                material_order.append(material)
            for index in set(indices):
                point = positions[index]
                world = [sum(matrix[c*4+r] * point[c] for c in range(3)) + matrix[12+r] for r in range(3)]
                if any(not math.isfinite(v) for v in world):
                    raise ValueError("non-finite transformed geometry")
                for axis in range(3):
                    lo[axis], hi[axis] = min(lo[axis], point[axis]), max(hi[axis], point[axis])
                    world_lo[axis], world_hi[axis] = min(world_lo[axis], world[axis]), max(world_hi[axis], world[axis])
        nodes.append({"name": name, "node_index": node_index, "mesh_index": node["mesh"],
                      "mesh_name": mesh.get("name"), "transform": _transform(node),
                      "node_extras": copy.deepcopy(node.get("extras", {})), "triangles": triangles,
                      "attributes": sorted(attributes), "primitive_material_indices": materials,
                      "source_material_slots": len(material_order),
                      "materials": [{"index": i, "name": doc["materials"][i]["name"],
                                     "definition": copy.deepcopy(doc["materials"][i])} for i in material_order],
                      "local_bounds": _bounds(lo, hi), "world_bounds": _bounds(world_lo, world_hi)})
        all_lo = [min(a, b) for a, b in zip(all_lo, world_lo)]
        all_hi = [max(a, b) for a, b in zip(all_hi, world_hi)]
    return {"coordinate_system": {"distance_unit": "metre", "up_axis": "+Y", "handedness": "right",
                                   "native_conversion_verified": False},
            "nodes": nodes, "world_bounds": _bounds(all_lo, all_hi),
            "scope": "Actual referenced POSITION corners; root transforms applied. Source material slots are not native slot acceptance; no pivot/collision/actor-scale inference."}


def admit(plan, candidate_path, expected_candidate, include_geometry=False):
    """Check an existing candidate; success proves file preservation, never native readiness."""
    names, source, expected = _plan_witnesses(plan)
    candidate_path = os.path.abspath(candidate_path)
    if os.path.normcase(candidate_path) == os.path.normcase(os.path.abspath(source["path"])):
        raise ValueError("candidate must be a separately produced subset file")
    actual = _inspect(candidate_path, expected_candidate, names, exact=True)
    for wanted, got in zip(expected, actual):
        if wanted != got:
            fields = [key for key in wanted if wanted[key] != got.get(key)]
            raise ValueError("subset changed %s: %s" % (wanted["name"], ", ".join(fields)))
    geometry = _geometry_manifest(candidate_path, expected_candidate, names) if include_geometry else None
    _file_bytes(source["path"], source)
    _file_bytes(candidate_path, expected_candidate)
    report = {"schema": "daedalus.static-subset-admission.v1", "admitted": True, "native_ready": False,
            "source": source, "candidate": {"path": candidate_path, **_pin(expected_candidate)},
            "nodes": names, "mesh_nodes": len(names), "triangles": sum(n["triangles"] for n in actual),
            "scope": "Offline file evidence only; native units, material translation, collision and placement remain unverified."}
    if geometry is not None:
        report["geometry"] = geometry
    return report


def export_subset(plan, output_path):
    """Extract pinned GLB bytes into a fresh, admitted file; never invoke Blender.

    Whole used bufferViews are retained, including any unused bytes inside them.
    A staged file is admitted before atomic no-overwrite hard-link publication.
    A failure after publication leaves an unadmitted output for reconciliation.
    """
    names, source, _ = _plan_witnesses(plan)
    output_path = os.path.abspath(output_path)
    if os.path.lexists(output_path):
        raise FileExistsError("subset output must be fresh: " + output_path)
    doc, binary = _read(source["path"], source)
    node_ids = [next(i for i, node in enumerate(doc["nodes"]) if node.get("name") == name) for name in names]
    mesh_ids = sorted({doc["nodes"][i]["mesh"] for i in node_ids})
    primitives = [prim for i in mesh_ids for prim in doc["meshes"][i]["primitives"]]
    material_ids = sorted({prim["material"] for prim in primitives if "material" in prim})
    accessor_ids = {index for prim in primitives for index in prim["attributes"].values()}
    accessor_ids.update(prim["indices"] for prim in primitives if "indices" in prim)
    accessor_ids = sorted(accessor_ids)
    view_ids = sorted({doc["accessors"][i]["bufferView"] for i in accessor_ids})
    source_indices = {"nodes": node_ids, "meshes": mesh_ids, "materials": material_ids,
                      "accessors": accessor_ids, "bufferViews": view_ids}
    maps = {key: {old: new for new, old in enumerate(indices)} for key, indices in source_indices.items()}
    result = {key: [copy.deepcopy(doc[key][i]) for i in indices] for key, indices in source_indices.items()}
    for node in result["nodes"]:
        node["mesh"] = maps["meshes"][node["mesh"]]
    for mesh in result["meshes"]:
        for prim in mesh["primitives"]:
            prim["attributes"] = {key: maps["accessors"][i] for key, i in prim["attributes"].items()}
            if "indices" in prim:
                prim["indices"] = maps["accessors"][prim["indices"]]
            if "material" in prim:
                prim["material"] = maps["materials"][prim["material"]]
    for accessor in result["accessors"]:
        accessor["bufferView"] = maps["bufferViews"][accessor["bufferView"]]
    spans, binary_length = [], 0
    for old, view in zip(view_ids, result["bufferViews"]):
        original = doc["bufferViews"][old]
        padding = -binary_length % 4
        start, length = original.get("byteOffset", 0), original["byteLength"]
        binary_length += padding + length
        # Overlapping source views can grow the output when copied separately.
        # Reject the complete span budget before allocating or writing its bytes.
        if binary_length > MAX_BYTES:
            raise ValueError("subset output exceeds file work limit")
        view.update(buffer=0, byteOffset=binary_length - length)
        spans.append((padding, start, length))
    result["asset"] = copy.deepcopy(doc["asset"])
    result["asset"]["generator"] = "Daedalus pinned GLB subset v1 (source-derived)"
    result["scene"] = 0
    result["scenes"] = [{"name": "Daedalus static subset", "nodes": list(range(len(names)))}]
    result["buffers"] = [copy.deepcopy(doc["buffers"][0])]
    result["buffers"][0]["byteLength"] = binary_length
    result["extras"] = {"daedalus_subset": {"schema": SCHEMA, "source_sha256": source["sha256"], "nodes": names}}
    metadata = _canonical(result).encode("utf-8")
    metadata += b" " * (-len(metadata) % 4)
    if len(metadata) > MAX_JSON_BYTES:
        raise ValueError("subset JSON metadata work limit exceeded")
    bin_padding = -binary_length % 4
    total = 12 + 8 + len(metadata) + 8 + binary_length + bin_padding
    if total > MAX_BYTES:
        raise ValueError("subset output exceeds file work limit")
    digest, written, staged_path = hashlib.sha256(), 0, None
    try:
        with tempfile.NamedTemporaryFile(prefix=".static-subset-", suffix=".glb", dir=os.path.dirname(output_path), delete=False) as staged:
            staged_path = staged.name

            def emit(data):
                nonlocal written
                if staged.write(data) != len(data):
                    raise OSError("short subset write")
                digest.update(data)
                written += len(data)

            emit(struct.pack("<4sII", b"glTF", 2, total))
            emit(struct.pack("<I4s", len(metadata), b"JSON"))
            emit(metadata)
            emit(struct.pack("<I4s", binary_length + bin_padding, b"BIN\x00"))
            for padding, start, length in spans:
                emit(b"\0" * padding)
                emit(memoryview(binary)[start:start + length])
            emit(b"\0" * bin_padding)
            staged.flush()
            os.fsync(staged.fileno())
        if written != total:
            raise ValueError("subset declared length differs from written bytes")
        candidate_pin = {"sha256": digest.hexdigest(), "bytes": written}
        admit(plan, staged_path, candidate_pin)
        # os.link fails if any destination already exists. There is no overwrite
        # fallback on filesystems that cannot provide this publication primitive.
        os.link(staged_path, output_path)
        admission = admit(plan, output_path, candidate_pin)
    finally:
        if staged_path is not None:
            os.unlink(staged_path)
    return {"schema": "daedalus.static-subset-export.v1", "exported": True,
            "producer": "pinned-glb-byte-extraction", "native_ready": False,
            "source": source, "source_asset": doc["asset"], "source_indices": source_indices,
            "plan_sha256": hashlib.sha256(_canonical(plan).encode("utf-8")).hexdigest(),
            "candidate": {"path": output_path, **candidate_pin}, "nodes": names, "admission": admission,
            "scope": "Source-derived GLB subset; no Blender execution, native import or compact-BIN guarantee."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("plan", help="read the pinned source and print a plan")
    make.add_argument("--source", required=True)
    make.add_argument("--sha256", required=True)
    make.add_argument("--bytes", type=int, required=True)
    make.add_argument("--nodes", nargs="+", required=True)
    check = commands.add_parser("admit", help="read a plan and an existing candidate; never import")
    check.add_argument("--plan", required=True)
    check.add_argument("--candidate", required=True)
    check.add_argument("--sha256", required=True)
    check.add_argument("--bytes", type=int, required=True)
    check.add_argument("--geometry", action="store_true", help="include actual source geometry/material metadata for handoff")
    produce = commands.add_parser("export", help="extract a pinned source-derived subset to a fresh GLB")
    produce.add_argument("--plan", required=True)
    produce.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            expected = {"sha256": args.sha256, "bytes": args.bytes}
            result = make_plan(args.source, args.nodes, expected)
        else:
            with open(args.plan, encoding="utf-8-sig") as source:
                raw = source.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("subset plan work limit exceeded")
            plan = json.loads(raw)
            if args.command == "export":
                result = export_subset(plan, args.output)
            else:
                result = admit(plan, args.candidate, {"sha256": args.sha256, "bytes": args.bytes}, include_geometry=args.geometry)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, struct.error) as error:
        print(json.dumps({"admitted": False, "native_ready": False,
                          "error": {"type": type(error).__name__, "message": str(error)}}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
