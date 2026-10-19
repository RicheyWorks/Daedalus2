# SPDX-License-Identifier: MIT
"""Pure-Python checks for sockets_sidecar.py (no Blender, no Unreal). python test_sockets_sidecar.py"""
import json, os, struct, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sockets_sidecar as S


def glb_bytes(doc):
    j = json.dumps(doc).encode(); j += b" " * (-len(j) % 4)
    return b"glTF" + struct.pack("<II", 2, 12 + 8 + len(j)) + struct.pack("<I4s", len(j), b"JSON") + j


doc = {"asset": {"version": "2.0"}, "nodes": [
    {"name": "Prop_PracticeCrate", "mesh": 0, "children": [1, 2]},
    {"name": "SOCKET_Top", "translation": [0, 0.5, 0]},                 # Blender (0, 0, 0.5)
    {"name": "Child", "mesh": 1, "translation": [0, 0.5, 0], "children": [3]},
    {"name": "SOCKET_Front", "translation": [0.035, 0.0, 0.045]}]}      # Blender (0.035, -0.045, 0)
man = {"sockets": [{"name": "SOCKET_Top", "forward": [0, 0, 1]}, {"name": "SOCKET_Front", "forward": [0, -1, 0]}]}
sc = S.from_gltf(doc, None, man); by = {s["name"]: s for s in sc["sockets"]}
d = tempfile.mkdtemp(); g = os.path.join(d, "Prop_X.glb"); open(g, "wb").write(glb_bytes(doc)); p, sc2 = S.write_for_glb(g, man)
checks = [
    ("Blender front (-Y) lands on UE +Y (UEB 48725 native evidence)", S.blender_to_ue((0, -1, 0)) == [0.0, 100.0, 0.0]),
    ("Blender up (Z) is UE +Z", S.blender_to_ue((0, 0, 1)) == [0.0, 0.0, 100.0]),
    ("Blender +X is UE +X", S.blender_to_ue((1, 0, 0)) == [100.0, 0.0, 0.0]),
    ("glTF path agrees with Blender path", all(S.gltf_to_ue((x, z, -y)) == S.blender_to_ue((x, y, z)) for x, y, z in [(0.1, -0.2, 0.3), (-0.5, 0.25, 1.8)])),
    ("crate SOCKET_Top -> (0, 0, 50) cm", by["SOCKET_Top"]["location"] == [0.0, 0.0, 50.0]),
    ("parent recorded", by["SOCKET_Top"]["parent"] == "Prop_PracticeCrate" and by["SOCKET_Front"]["parent"] == "Child"),
    ("child socket relative to its parent node", by["SOCKET_Front"]["location"] == [3.5, 4.5, 0.0]),
    ("forward Blender -Y -> yaw 90, pitch 0", by["SOCKET_Front"]["rotation"] == [0.0, 90.0, 0.0]),
    ("forward +Z -> pitch 90", by["SOCKET_Top"]["rotation"] == [90.0, 0.0, 0.0]),
    ("forward Blender +X -> yaw 0", S.forward_to_rotation((1, 0, 0)) == [0.0, 0.0, 0.0]),
    ("format keys", set(sc) >= {"asset", "units", "space", "sockets"} and sc["units"] == "cm" and sc["space"] == "unreal"),
    ("asset = root mesh node", sc["asset"] == "Prop_PracticeCrate"),
    ("file written next to the glb, asset from the file name", os.path.basename(p) == "Prop_X.sockets.json" and json.load(open(p))["asset"] == "Prop_X"),
]
try:
    S.from_gltf({"nodes": [{"name": "SOCKET_Bad", "rotation": [0, 0.7071, 0, 0.7071]}]}); checks.append(("rotated socket refused", False))
except ValueError:
    checks.append(("rotated socket raises", True))
M = [S.blender_to_ue(e) for e in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]]
det = (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0]) + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
checks.append(("glTF (gX, gY, gZ) -> UE (gX, gZ, gY) as UEB measured on terrain_33", S.gltf_to_ue((0.1, 0.2, 0.3)) == [10.0, 30.0, 20.0]))
checks.append(("axis map det < 0 (right-handed Blender -> left-handed UE, not mirrored)", det < 0))
ok = 0
for n, r in checks:
    ok += bool(r); print(("ok   " if r else "FAIL ") + n)
print("%d/%d" % (ok, len(checks))); sys.exit(ok != len(checks))
