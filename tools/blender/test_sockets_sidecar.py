# SPDX-License-Identifier: MIT
"""Pure-Python checks for sockets_sidecar.py (no Blender, no Unreal). python test_sockets_sidecar.py"""
import json, os, struct, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sockets_sidecar as S


def glb_bytes(doc):
    j = json.dumps(doc).encode(); j += b" " * (-len(j) % 4)
    return b"glTF" + struct.pack("<II", 2, 12 + 8 + len(j)) + struct.pack("<I4s", len(j), b"JSON") + j


def gq(rb):
    """glTF node quaternion [x, y, z, w] the exporter writes for Blender rotation rb."""
    w, x, y, z = S.matrix_to_quat_wxyz(S._mm(S._mm(S.P, rb), S._T(S.P))); return [x, y, z, w]


I = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
plain_rb = S.blender_empty_matrix(I)
rod = {"name": "SOCKET_Tip", "attach": {"barrel": [0, 0, 1], "up": [0, 1, 0]}}
rifle = {"name": "SOCKET_Muzzle", "attach": {"barrel": [0, -1, 0], "up": [0, 0, 1]}}
doc = {"asset": {"version": "2.0"}, "nodes": [
    {"name": "Prop_PracticeCrate", "mesh": 0, "children": [1, 2, 4, 5]},
    {"name": "SOCKET_Top", "translation": [0, 0.5, 0], "rotation": gq(plain_rb)},      # Blender (0, 0, 0.5), pre-rotated plain
    {"name": "Child", "mesh": 1, "translation": [0, 0.5, 0], "children": [3]},
    {"name": "SOCKET_Front", "translation": [0.035, 0.0, 0.045], "rotation": gq(plain_rb)},
    {"name": "SOCKET_Tip", "translation": [0, 1.8, 0], "rotation": gq(S.blender_empty_matrix(S.desired_frame(rod)))},
    {"name": "SOCKET_Old", "translation": [0, 0.1, 0]}]}                               # an un-rotated (pre-convention) empty
man = {"sockets": [{"name": "SOCKET_Top", "forward": [0, 0, 1]}, {"name": "SOCKET_Front", "forward": [0, -1, 0]}, rod, {"name": "SOCKET_Old"}]}
sc = S.from_gltf(doc, None, man); by = {s["name"]: s for s in sc["sockets"]}
d = tempfile.mkdtemp(); g = os.path.join(d, "Prop_X.glb"); open(g, "wb").write(glb_bytes(doc)); p, sc2 = S.write_for_glb(g, man)
R = S.matrix_to_rotator
checks = [
    ("Blender front (-Y) lands on UE +Y (UEB 48725 native evidence)", S.blender_to_ue((0, -1, 0)) == [0.0, 100.0, 0.0]),
    ("Blender up (Z) is UE +Z", S.blender_to_ue((0, 0, 1)) == [0.0, 0.0, 100.0]),
    ("Blender +X is UE +X", S.blender_to_ue((1, 0, 0)) == [100.0, 0.0, 0.0]),
    ("glTF path agrees with Blender path", all(S.gltf_to_ue((x, z, -y)) == S.blender_to_ue((x, y, z)) for x, y, z in [(0.1, -0.2, 0.3), (-0.5, 0.25, 1.8)])),
    ("crate SOCKET_Top -> (0, 0, 50) cm", by["SOCKET_Top"]["location"] == [0.0, 0.0, 50.0]),
    ("parent recorded", by["SOCKET_Top"]["parent"] == "Prop_PracticeCrate" and by["SOCKET_Front"]["parent"] == "Child"),
    ("child socket relative to its parent node", by["SOCKET_Front"]["location"] == [3.5, 4.5, 0.0]),
    ("rotator <-> matrix round trip", all(R(S.rotator_to_matrix(r)) == r for r in ([0.0, 0.0, 0.0], [10.0, 20.0, 30.0], [0.0, 180.0, -90.0], [-45.0, -120.0, 15.0]))),
    ("UEB 48794: identity Blender empty reads [0, 180, -90] natively (both offset models)", R(S.predict_native(I)) == [0.0, 180.0, -90.0] == R(S.predict_native_alt(I))),
    ("pre-rotated plain empty reads [0, 0, 0] natively (both models)", R(S.predict_native(plain_rb)) == [0.0, 0.0, 0.0] == R(S.predict_native_alt(plain_rb))),
    ("plain Blender empty = 180 deg about (0, -1, 1)/sqrt2", S.matrix_to_quat_wxyz(plain_rb) == [0.0, 0.0, -0.7071068, 0.7071068]),
    ("plain sockets -> sidecar [0, 0, 0], native matches", all(by[n]["rotation"] == [0.0, 0.0, 0.0] and by[n]["native_matches"] and by[n]["kind"] == "plain" for n in ("SOCKET_Top", "SOCKET_Front"))),
    ("un-rotated empty flagged: native [0, 180, -90] != sidecar", by["SOCKET_Old"]["native_rotation_predicted"] == [0.0, 180.0, -90.0] and not by["SOCKET_Old"]["native_matches"]),
    ("attach frame: +X along the barrel, +Z up, proper rotation", (lambda f: S._T(f)[0] == (0.0, 1.0, 0.0) and S._T(f)[2] == (0.0, 0.0, 1.0) and S._T(f)[1] == (-1.0, 0.0, 0.0))(S.attach_frame((0, -1, 0)))),
    ("rifle Muzzle/Grip (barrel Blender -Y) -> [0, 90, 0]", R(S.desired_frame(rifle)) == [0.0, 90.0, 0.0]),
    ("rod Tip/Grip (shaft Blender +Z, up Blender +Y) -> [90, 0, -90]", by["SOCKET_Tip"]["rotation"] == [90.0, 0.0, -90.0] and by["SOCKET_Tip"]["kind"] == "attach"),
    ("pre-rotated attach empty: native == sidecar", by["SOCKET_Tip"]["native_matches"]),
    ("attach X axis really is the shaft in UE", all(abs(a - b) < 1e-9 for a, b in zip(S._T(S.rotator_to_matrix(by["SOCKET_Tip"]["rotation"]))[0], (0, 0, 1)))),
    ("up hint orthogonalised", (lambda f: abs(sum(S._T(f)[0][i] * S._T(f)[2][i] for i in range(3))) < 1e-12)(S.attach_frame((0, -1, 0.3), (0, 0, 1)))),
    ("format keys", set(sc) >= {"asset", "units", "space", "sockets"} and sc["units"] == "cm" and sc["space"] == "unreal"),
    ("asset = root mesh node", sc["asset"] == "Prop_PracticeCrate"),
    ("file written next to the glb, asset from the file name", os.path.basename(p) == "Prop_X.sockets.json" and json.load(open(p))["asset"] == "Prop_X"),
]
try:
    S.from_gltf({"nodes": [{"name": "SOCKET_Bad", "scale": [2, 2, 2]}]}); checks.append(("scaled socket refused", False))
except ValueError:
    checks.append(("scaled socket raises", True))
M = [S.blender_to_ue(e) for e in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]]
det = (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0]) + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
checks.append(("glTF (gX, gY, gZ) -> UE (gX, gZ, gY) as UEB measured on terrain_33", S.gltf_to_ue((0.1, 0.2, 0.3)) == [10.0, 30.0, 20.0]))
checks.append(("axis map det < 0 (right-handed Blender -> left-handed UE, not mirrored)", det < 0))
ok = 0
for n, r in checks:
    ok += bool(r); print(("ok   " if r else "FAIL ") + n)
print("%d/%d" % (ok, len(checks))); sys.exit(ok != len(checks))
