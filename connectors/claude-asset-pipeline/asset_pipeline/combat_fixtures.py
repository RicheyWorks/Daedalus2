# SPDX-License-Identifier: MIT
"""Sample combat-slice .glb files built from a combat-slice/v1 spec, so blender-team can see what a PASSING file contains
(and what each defect looks like) without waiting for real art. They are minimal hand-made glTF: right node, joint and
mesh names, right triangle counts, no real geometry. Never import them into Unreal: they are test shapes, not art.

    python -m asset_pipeline.combat_fixtures --spec specs/combat-slice-1.json --out <dir>
    python -m asset_pipeline.combat_fixtures --spec specs/combat-slice-1.json --out <dir> --defect Wpn_Slice1_Rifle=socket

Defects: socket (drops the last socket), skin (no armature), joints (3 joints only), lods (LOD1 missing),
lod-order (LOD1 heavier than LOD0), tris (over the triangle budget), collision (one hull only), nocollision, broken (not a glb).
"""
import argparse
import json
import os
import struct
import sys

from . import combat_handoff as ch

DEFECTS = ("socket", "skin", "joints", "lods", "lod-order", "tris", "collision", "nocollision", "broken")


def write_glb(path, meshes=(), empties=(), joints=None):
    """meshes: [(name, triangles)]; empties: mesh-less node names; joints: bone names (made into one skin)."""
    acc, ms, nodes = [], [], []
    for name, tris in meshes:
        acc.append({"count": tris * 3, "type": "VEC3", "componentType": 5126, "min": [0, 0, 0], "max": [1, 1, 1]})
        ms.append({"name": name, "primitives": [{"attributes": {"POSITION": len(acc) - 1}}]})
        nodes.append({"name": name, "mesh": len(ms) - 1})
    for e in empties:
        nodes.append({"name": e})
    doc = {"asset": {"version": "2.0", "generator": "combat_fixtures (test shape, not art)"}, "accessors": acc, "meshes": ms, "nodes": nodes}
    if joints:
        first = len(nodes)
        nodes.extend({"name": j} for j in joints)
        doc["skins"] = [{"joints": list(range(first, first + len(joints)))}]
    body = json.dumps(doc).encode()
    body += b" " * (-len(body) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, 20 + len(body)) + struct.pack("<I4s", len(body), b"JSON") + body)


def build_asset(asset, path, defect=None):
    """Write one passing sample for `asset` (a spec asset dict), or the same with one `defect`."""
    if defect == "broken":
        with open(path, "wb") as f:
            f.write(b"not a glb")
        return
    cap = int(asset.get("max_triangles", 10000))
    over = cap + 1000 if defect == "tris" else 0
    role = asset["role"]
    if role == "weapon":
        sockets = list(asset.get("sockets", ["Muzzle", "Grip"]))
        if defect == "socket" and sockets:
            sockets = sockets[:-1]
        write_glb(path, [(asset["name"].split("_")[-1], max(12, cap // 4) + over)], ["SOCKET_" + s for s in sockets])
    elif role == "enemy":
        sk = asset.get("skeleton", {})
        joints = list(sk.get("required_joints", ["root"]))
        joints += ["bone_%02d" % i for i in range(max(0, sk.get("min_joints", 1) - len(joints)))]
        if defect == "joints":
            joints = joints[:3]
        n = max(2, asset.get("lods", 2))
        base = max(300, cap // 3)
        tris = [max(12, base // (3 ** i)) for i in range(n)]
        if defect == "lod-order" and n > 1:
            tris[1] = tris[0] + 50
        if defect == "tris":
            tris[0] = cap + 1000
        lods = list(range(n))
        if defect == "lods" and n > 1:
            lods = [0] + lods[2:]
        write_glb(path, [("Body_LOD%d" % i, tris[i]) for i in lods], joints=None if defect == "skin" else joints)
    elif role == "environment":
        hulls = asset.get("collision", {}).get("min_hulls", 1)
        if defect == "collision":
            hulls = 1
        meshes = [("Arena", max(12, cap // 3) + over)]
        meshes += [("UCX_%s_%02d" % ("Arena", i), 12) for i in range(hulls)]
        if defect == "nocollision":
            meshes = [("Arena", 1000)]
        write_glb(path, meshes)
    else:
        write_glb(path, [(asset["name"], 12)])


def build_slice(spec, out, defects=None):
    """Write every asset of the spec into <out>/glb/<name>.glb. defects: {asset name: defect}. Returns the paths."""
    spec = ch.load_spec(spec)
    defects = defects or {}
    os.makedirs(os.path.join(out, "glb"), exist_ok=True)
    paths = []
    for a in spec["assets"]:
        d = defects.get(a["name"])
        if d and d not in DEFECTS:
            raise ValueError("unknown defect %r (choose from %s)" % (d, ", ".join(DEFECTS)))
        p = os.path.join(out, "glb", a["name"] + ".glb")
        build_asset(a, p, d)
        paths.append(p)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--defect", action="append", default=[], metavar="ASSET=KIND")
    a = ap.parse_args(argv)
    defects = dict(x.split("=", 1) for x in a.defect)
    try:
        paths = build_slice(a.spec, a.out, defects)
    except (ch.SpecError, ValueError) as e:
        print("ERROR %s" % e)
        return 2
    for p in paths:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())