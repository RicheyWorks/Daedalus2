# SPDX-License-Identifier: MIT
"""Read what a .glb holds without any 3D library: meshes, triangles, materials, sizes.

The file between Blender and Unreal is the pipeline's witness. Blender's numbers are checked against it
(the export lost nothing), and Unreal's numbers are checked against it (the import lost nothing).
Only the JSON chunk is read: triangle counts and sizes come from accessor counts and min/max, which the
glTF spec requires on POSITION.
"""
import json
import struct

TRIANGLES = 4


def read_json(path):
    with open(path, "rb") as f:
        head = f.read(12)
        if len(head) < 12:
            raise ValueError("%s is not a GLB: too short" % path)
        magic, version, _length = struct.unpack("<4sII", head)
        if magic != b"glTF":
            raise ValueError("%s is not a GLB: bad magic" % path)
        if version != 2:
            raise ValueError("%s is glTF version %d, want 2" % (path, version))
        clen, ctype = struct.unpack("<I4s", f.read(8))
        if ctype != b"JSON":
            raise ValueError("%s: first chunk is not JSON" % path)
        return json.loads(f.read(clen).decode("utf-8"))


def _prim_tris(doc, prim):
    acc = doc["accessors"]
    mode = prim.get("mode", TRIANGLES)
    if mode != TRIANGLES:
        return 0   # lines and points are not surfaces
    if "indices" in prim:
        return acc[prim["indices"]]["count"] // 3
    return acc[prim["attributes"]["POSITION"]]["count"] // 3


def summarize(path):
    """{meshes: [{name, triangles, materials, dims}], nodes: [{name, mesh, dims}], materials: [names]}.

    dims is the mesh's own (local) size, sorted largest first, so a Y-up/Z-up swap does not change it.
    """
    doc = read_json(path)
    mats = [m.get("name", "material_%d" % i) for i, m in enumerate(doc.get("materials", []))]
    meshes = []
    for i, mesh in enumerate(doc.get("meshes", [])):
        tris, used, lo, hi = 0, [], None, None
        for prim in mesh.get("primitives", []):
            tris += _prim_tris(doc, prim)
            if "material" in prim and mats[prim["material"]] not in used:
                used.append(mats[prim["material"]])
            pos = doc["accessors"][prim["attributes"]["POSITION"]]
            if "min" in pos and "max" in pos:
                lo = pos["min"] if lo is None else [min(a, b) for a, b in zip(lo, pos["min"])]
                hi = pos["max"] if hi is None else [max(a, b) for a, b in zip(hi, pos["max"])]
        extent = [h - l for l, h in zip(lo, hi)] if lo else [0.0, 0.0, 0.0]
        meshes.append({"name": mesh.get("name", "mesh_%d" % i), "triangles": tris, "materials": used,
                       "extent": extent, "dims": [round(d, 5) for d in sorted(extent, reverse=True)]})
    # Unreal's Interchange makes one static mesh per node and bakes the node's scale into it (seen live,
    # UE 5.8.3), so each node also carries its scaled size. Rotation is not applied: sorting the sizes
    # covers quarter turns, and a free rotation would need the vertices, which this reader doesn't load.
    nodes = []
    for i, n in enumerate(doc.get("nodes", [])):
        if "mesh" not in n:
            continue
        scale = n.get("scale", [1.0, 1.0, 1.0])
        sized = sorted((abs(k) * e for k, e in zip(scale, meshes[n["mesh"]]["extent"])), reverse=True)
        nodes.append({"name": n.get("name", "node_%d" % i), "mesh": n["mesh"],
                      "dims": [round(d, 5) for d in sized]})
    return {"meshes": meshes, "nodes": nodes, "materials": mats}
