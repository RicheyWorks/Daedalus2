"""Stdlib-only GLB intake check for the Interchange reimport fixture.

Usage: python glb_intake.py <expectations.json> <variant A|B> <file.glb>
Prints a JSON report and exits 0 only if every check passes. Pure Python:
no Blender, no Unreal, no network.
"""
import hashlib
import json
import struct
import sys

_FMT = {5126: "f", 5125: "I", 5123: "H", 5121: "B"}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(data):
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("not a glTF 2 binary or length mismatch")
    clen, ctype = struct.unpack_from("<I4s", data, 12)
    if ctype != b"JSON":
        raise ValueError("first chunk is not JSON")
    gltf = json.loads(data[20:20 + clen])
    off = 20 + clen
    blen, btype = struct.unpack_from("<I4s", data, off)
    return gltf, data[off + 8:off + 8 + blen]


def _accessor(gltf, binary, index):
    acc = gltf["accessors"][index]
    view = gltf["bufferViews"][acc["bufferView"]]
    fmt = _FMT[acc["componentType"]]
    n = _NCOMP[acc["type"]]
    size = struct.calcsize(fmt)
    stride = view.get("byteStride", size * n)
    base = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    return [struct.unpack_from("<" + fmt * n, binary, base + k * stride) for k in range(acc["count"])]


def mesh_facts(gltf, binary, mesh_index):
    tris = 0
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    mats = []
    for prim in gltf["meshes"][mesh_index]["primitives"]:
        pos = _accessor(gltf, binary, prim["attributes"]["POSITION"])
        count = gltf["accessors"][prim["indices"]]["count"] if "indices" in prim else len(pos)
        tris += count // 3
        for v in pos:
            for k in range(3):
                lo[k] = min(lo[k], v[k])
                hi[k] = max(hi[k], v[k])
        if "material" in prim:
            mats.append(gltf["materials"][prim["material"]]["name"])
    return {"tris": tris, "min": lo, "max": hi, "dims": [hi[k] - lo[k] for k in range(3)], "materials": mats}


def srgb_hex_to_linear(hexstr):
    return [(int(hexstr[i:i + 2], 16) / 255.0) ** 2.2 for i in (0, 2, 4)]


def check(exp, variant, path):
    with open(path, "rb") as fh:
        data = fh.read()
    v = exp["variants"][variant]
    tol = exp.get("tolerance_m", 0.001)
    ctol = exp.get("color_tolerance", 0.01)
    gltf, binary = read_glb(data)
    nodes = gltf["nodes"]
    by_name = {n.get("name"): i for i, n in enumerate(nodes)}
    res = {"variant": variant, "path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "checks": {}}
    c = res["checks"]
    c["bytes"] = len(data) == v["bytes"]
    c["sha256"] = res["sha256"] == v["sha256"]
    mesh_node = by_name.get(exp["asset"])
    c["mesh_node"] = mesh_node is not None and "mesh" in nodes[mesh_node]
    if not c["mesh_node"]:
        res["ok"] = False
        return res
    mf = mesh_facts(gltf, binary, nodes[mesh_node]["mesh"])
    res["mesh"] = mf
    c["tris"] = mf["tris"] == v["tris"]
    c["dims_m_gltf"] = all(abs(mf["dims"][k] - v["dims_m_gltf"][k]) <= tol for k in range(3))
    children = [nodes[i].get("name") for i in nodes[mesh_node].get("children", [])]
    res["children"] = children
    sock = exp["socket"]
    c["socket_child"] = sock["name"] in children
    if c["socket_child"]:
        t = nodes[by_name[sock["name"]]].get("translation", [0, 0, 0])
        res["socket_translation"] = t
        c["socket_translation"] = all(abs(t[k] - sock["gltf_translation"][k]) <= tol for k in range(3))
    ucx = exp["collision"]["name"]
    c["ucx_child"] = ucx in children
    if c["ucx_child"] and "mesh" in nodes[by_name[ucx]]:
        uf = mesh_facts(gltf, binary, nodes[by_name[ucx]]["mesh"])
        res["ucx"] = uf
        c["ucx_tris"] = uf["tris"] == v["ucx_tris"]
        c["ucx_no_material"] = not uf["materials"]
    names = [m["name"] for m in gltf.get("materials", [])]
    res["materials"] = names
    c["material_names"] = names == [m["name"] for m in exp["materials"]]
    for m in exp["materials"]:
        mat = next((x for x in gltf.get("materials", []) if x["name"] == m["name"]), None)
        bcf = (mat or {}).get("pbrMetallicRoughness", {}).get("baseColorFactor", [1, 1, 1, 1])
        lin = srgb_hex_to_linear(m["srgb_hex"])
        c["color_" + m["name"]] = mat is not None and all(abs(bcf[k] - lin[k]) <= ctol for k in range(3))
    res["ok"] = all(c.values())
    return res


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    exp = json.load(open(argv[1], encoding="utf-8-sig"))
    res = check(exp, argv[2], argv[3])
    print(json.dumps(res, indent=1))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))