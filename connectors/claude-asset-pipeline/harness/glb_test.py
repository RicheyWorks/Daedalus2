# SPDX-License-Identifier: MIT
"""The .glb reader on hand-made files: indexed, non-indexed, lines, no material, and broken files.

    python3 harness/glb_test.py        # n/m last; exit 1 on any failure
"""
import json
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from asset_pipeline import glb  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("%-4s  %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  " + str(detail)))


def write(doc, magic=b"glTF", version=2):
    body = json.dumps(doc).encode()
    body += b" " * (-len(body) % 4)
    path = tempfile.mktemp(suffix=".glb")
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", magic, version, 12 + 8 + len(body)))
        f.write(struct.pack("<I4s", len(body), b"JSON") + body)
    return path


def pos(count, lo, hi):
    return {"count": count, "type": "VEC3", "componentType": 5126, "min": lo, "max": hi}


DOC = {
    "asset": {"version": "2.0"},
    "materials": [{"name": "Brass"}, {"name": "Glow"}],
    "accessors": [pos(24, [-1, 0, -0.5], [1, 3, 0.5]), {"count": 36, "type": "SCALAR", "componentType": 5123},
                  pos(9, [0, 0, 0], [0.2, 0.4, 0.1]), pos(4, [0, 0, 0], [1, 1, 0])],
    "meshes": [
        {"name": "Indexed", "primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0},
                                           {"attributes": {"POSITION": 2}, "material": 1}]},
        {"name": "Bare", "primitives": [{"attributes": {"POSITION": 2}}]},
        {"name": "Wire", "primitives": [{"attributes": {"POSITION": 3}, "mode": 1}]},
    ],
    "nodes": [{"name": "A", "mesh": 0}, {"name": "B", "mesh": 0, "scale": [1, 2, -3]}, {"name": "C", "mesh": 1}, {"name": "Empty"}],
}
s = glb.summarize(write(DOC))
m = {x["name"]: x for x in s["meshes"]}
check("indexed primitive: indices / 3, plus a non-indexed one: positions / 3", m["Indexed"]["triangles"] == 12 + 3,
      m["Indexed"])
check("a non-indexed mesh counts positions / 3", m["Bare"]["triangles"] == 3, m["Bare"])
check("lines are not triangles", m["Wire"]["triangles"] == 0, m["Wire"])
check("materials in use, per mesh, in order", m["Indexed"]["materials"] == ["Brass", "Glow"] and m["Bare"]["materials"] == [])
check("dims: union of primitive bounds, sorted largest first", m["Indexed"]["dims"] == [3.0, 2.0, 1.0], m["Indexed"]["dims"])
check("nodes: only the ones holding a mesh, instancing kept", [n["mesh"] for n in s["nodes"]] == [0, 0, 1], s["nodes"])

check("a node's scale sizes it (sign ignored), the mesh keeps its own size",
      s["nodes"][1]["dims"] == [6.0, 3.0, 2.0] and s["nodes"][0]["dims"] == [3.0, 2.0, 1.0], s["nodes"])

for name, path in [("bad magic", write(DOC, magic=b"nope")), ("glTF 1", write(DOC, version=1))]:
    try:
        glb.summarize(path)
        check("%s is refused" % name, False, "read it")
    except ValueError:
        check("%s is refused" % name, True)
short = tempfile.mktemp(suffix=".glb")
open(short, "wb").write(b"glTF")
try:
    glb.summarize(short)
    check("a truncated file is refused", False, "read it")
except ValueError:
    check("a truncated file is refused", True)

print("%d/%d" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
