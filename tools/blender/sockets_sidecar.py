# SPDX-License-Identifier: MIT
"""Socket sidecar for Unreal (blender-team): <Asset>.sockets.json next to each socketed glb, a cross-check / rotation carrier.
Stock UE 5.8 glTF Interchange DOES import SOCKET_ empties natively (unreal-epic-boss 48725; the earlier "dropped" result,
48518/48519, was a reader false negative). Our empties carry translation only, so the native sockets have rotation 0;
the sidecar adds the forward-derived rotation and lets intake (PR203 add_sockets) cross-check positions.

  {"asset": ..., "units": "cm", "space": "unreal",
   "sockets": [{"name", "parent", "location": [x, y, z], "rotation": [pitch, yaw, roll]}]}

Unreal space: +X forward, +Y right, +Z up, centimetres, left-handed. Mapping, from native evidence (UEB 48725: terrain_33,
no node rotation, imported at UE = 100 * (gX, gZ, gY)) and PR203 (no yaw applied; sidecar location -> relative_location):
    from glTF (+Y up):  UE = 100 * (gx, gz, gy)        from Blender (glTF = (x, z, -y)):  UE = 100 * (x_b, -y_b, z_b)
So the Blender front (-Y) lands on UE +Y, not +X (corrected 2026-10-19; earlier sidecars used 100 * (-y_b, -x_b, z_b), a 90 deg
yaw off). Decided (buffffff 48769): glbs are not rotated at export; placement faces them with actor/component yaw -90
(as with the UE mannequin). Exception: an asset whose UE attach code needs mesh +X forward (weapon/character attach) is revisited. location is relative to the socket's parent node. rotation comes from the socket's forward vector (yaw about Z,
pitch toward Z; roll 0): Blender front (0, -1, 0) -> yaw 90. Sockets without a forward get [0, 0, 0].

  python sockets_sidecar.py <asset.glb> [--manifest <recipe or kit json>] [--out <dir>]   -> <dir>/<Asset>.sockets.json
"""
import argparse, json, math, os, struct

SCHEMA_NOTE = ("UE +X forward, +Y right, +Z up, cm; UE = 100 * (x_b, -y_b, z_b) = 100 * (gx, gz, gy) (UEB 48725); location relative to parent node; "
               "rotation [pitch, yaw, roll] deg: plain sockets [0, 0, 0] = mesh-aligned, attach sockets +X along barrel/shaft, +Z up; native empties pre-rotated to match")


def blender_to_ue(v):
    x, y, z = v
    return [round(x * 100.0, 4) + 0.0, round(-y * 100.0, 4) + 0.0, round(z * 100.0, 4) + 0.0]


def gltf_to_ue(v):
    gx, gy, gz = v
    return [round(gx * 100.0, 4) + 0.0, round(gz * 100.0, 4) + 0.0, round(gy * 100.0, 4) + 0.0]


# ---- socket orientation (team convention, UEB 48793/48794) -------------------------------------------------------
# Rotation matrices act on column vectors; a UE frame is the 3x3 whose columns are the socket's X, Y, Z axes in UE mesh space.
#   plain socket  : identity, [0, 0, 0] = aligned with the mesh.
#   attach socket : +X along the barrel/shaft (toward the muzzle/tip), +Z up (the given up hint, orthogonalised).
# Interchange path for an empty with Blender rotation Rb (glTF exporter +Y up: Rg = P Rb P^T; Interchange: M Rg M, then a fixed
# offset A, measured by UEB 48794: identity empties read [0, 180, -90]):  native = M P Rb P^T M A = N Rb N A,  N = M P = diag(1, -1, 1).
# So the empty is pre-rotated Rb = N R_d A^T N (A^T = A) and native == sidecar == R_d (build_kit does this). The PR227 harness
# takes rotation from the sidecar anyway (UEB 48812), so the sidecar is authoritative and native_matches is a cross-check. For plain sockets (R_d = I) this is the same
# whether A applies on the right (local) or the left; for attach sockets it assumes the right (local) side, see predict_native_alt.
N = ((1, 0, 0), (0, -1, 0), (0, 0, 1))


def _mm(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _T(a):
    return tuple(tuple(a[j][i] for j in range(3)) for i in range(3))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(v):
    n = math.sqrt(sum(c * c for c in v)); return tuple(c / n for c in v)


def rotator_to_matrix(r):
    """UE FRotator [pitch, yaw, roll] deg -> frame (columns X, Y, Z), as FRotationMatrix."""
    p, y, ro = (math.radians(v) for v in r)
    SP, CP, SY, CY, SR, CR = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(ro), math.cos(ro)
    X = (CP * CY, CP * SY, SP)
    Y = (SR * SP * CY - CR * SY, SR * SP * SY + CR * CY, -SR * CP)
    Z = (-(CR * SP * CY + SR * SY), CY * SR - CR * SP * SY, CR * CP)
    return _T((X, Y, Z))


def matrix_to_rotator(m):
    """frame -> UE [pitch, yaw, roll] deg (FMatrix::Rotator)."""
    X, Y, Z = _T(m)
    pitch = math.degrees(math.atan2(X[2], math.hypot(X[0], X[1])))
    yaw = math.degrees(math.atan2(X[1], X[0]))
    sy = rotator_to_matrix([pitch, yaw, 0.0]); syY = _T(sy)[1]
    roll = math.degrees(math.atan2(sum(Z[i] * syY[i] for i in range(3)), sum(Y[i] * syY[i] for i in range(3))))
    return [_clean(pitch), _clean(yaw), _clean(roll)]


def _clean(a):
    a = round(a, 4) + 0.0
    if abs(abs(a) - 180.0) < 1e-3:
        a = 180.0
    return a


A = rotator_to_matrix([0, 180, -90])         # Interchange offset on an identity empty (UEB 48794)


def blender_dir_to_ue(v):
    return (v[0], -v[1], v[2])


def attach_frame(barrel_blender, up_blender=(0, 0, 1)):
    """UE frame for a held-prop socket: +X along the Blender barrel/shaft direction, +Z toward the up hint."""
    X = _unit(blender_dir_to_ue(barrel_blender)); U = blender_dir_to_ue(up_blender)
    d = sum(U[i] * X[i] for i in range(3)); Z = _unit(tuple(U[i] - d * X[i] for i in range(3)))
    return _T((X, _cross(Z, X), Z))


def desired_frame(sock):
    """Team convention: attach sockets get attach_frame, everything else identity."""
    at = sock.get("attach") if sock else None
    return attach_frame(at["barrel"], at.get("up", (0, 0, 1))) if at else ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def blender_empty_matrix(frame_ue):
    """Blender rotation for the SOCKET_ empty so the native Interchange socket equals frame_ue."""
    return _mm(_mm(_mm(N, frame_ue), _T(A)), N)


def predict_native(rb):
    """Native UE frame Interchange gives an empty with Blender rotation rb (A on the right, local)."""
    return _mm(_mm(_mm(N, rb), N), A)


def predict_native_alt(rb):
    """Same with A on the left; differs from predict_native only for non-identity attach frames."""
    return _mm(A, _mm(_mm(N, rb), N))


def quat_to_matrix(q):
    x, y, z, w = q
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
            (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
            (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)))


def matrix_to_quat_wxyz(m):
    """3x3 rotation -> (w, x, y, z) for Blender's rotation_quaternion."""
    t = m[0][0] + m[1][1] + m[2][2]
    if t > 0:
        s = math.sqrt(t + 1.0) * 2; w, x, y, z = 0.25 * s, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2; w, x, y, z = (m[2][1] - m[1][2]) / s, 0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2; w, x, y, z = (m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2; w, x, y, z = (m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s
    return [round(c, 7) + 0.0 for c in (w, x, y, z)]


def socket_blender_quat(sock):
    """(w, x, y, z) to set on the SOCKET_ empty in Blender for this recipe socket."""
    return matrix_to_quat_wxyz(blender_empty_matrix(desired_frame(sock)))


P = ((1, 0, 0), (0, 0, 1), (0, -1, 0))       # Blender -> glTF (+Y up)


def read_glb_json(path):
    with open(path, "rb") as f:
        b = f.read()
    if b[:4] != b"glTF":
        raise ValueError("not a glb: %s" % path)
    n = struct.unpack_from("<I", b, 12)[0]
    return json.loads(b[20:20 + n].decode("utf-8"))


def _recipe_sockets(manifest):
    return {s["name"]: s for s in (manifest or {}).get("sockets", [])}


def from_gltf(doc, asset=None, manifest=None):
    nodes = doc.get("nodes", []); parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    rs = _recipe_sockets(manifest); socks = []
    for i, n in enumerate(nodes):
        name = n.get("name", "")
        if not name.upper().startswith("SOCKET_"):
            continue
        if n.get("scale") not in (None, [1, 1, 1], [1.0, 1.0, 1.0]) or "matrix" in n:
            raise ValueError("socket %s has a scale/matrix; only translation + rotation are supported" % name)
        p = parent.get(i)
        rg = quat_to_matrix(n.get("rotation", [0, 0, 0, 1]))
        rb = _mm(_mm(_T(P), rg), P)                       # back to the Blender empty rotation
        native = matrix_to_rotator(predict_native(rb))
        rot = matrix_to_rotator(desired_frame(rs.get(name))) if name in rs else native
        e = {"name": name, "parent": nodes[p].get("name") if p is not None else None,
             "location": gltf_to_ue(n.get("translation", [0, 0, 0])), "rotation": rot,
             "kind": "attach" if (rs.get(name) or {}).get("attach") else "plain", "native_rotation_predicted": native}
        e["native_matches"] = all(abs(((e["rotation"][k] - native[k]) + 180) % 360 - 180) < 0.01 for k in range(3)) or \
            _same_frame(rotator_to_matrix(e["rotation"]), rotator_to_matrix(native))
        socks.append(e)
    roots = [nodes[i].get("name") for i in range(len(nodes)) if i not in parent and "mesh" in nodes[i]]
    return {"asset": asset or (roots[0] if roots else None), "units": "cm", "space": "unreal", "note": SCHEMA_NOTE,
            "sockets": sorted(socks, key=lambda s: s["name"])}


def _same_frame(a, b):
    return all(abs(a[i][j] - b[i][j]) < 1e-4 for i in range(3) for j in range(3))


def write_for_glb(glb, manifest=None, out_dir=None, asset=None):
    doc = read_glb_json(glb); asset = asset or os.path.splitext(os.path.basename(glb))[0]
    sc = from_gltf(doc, asset, manifest)
    for k in ("hinges", "hinge"):              # frame/mover split (UEB 48812): hinge sockets + open pose as a UE rotator
        if manifest and manifest.get(k):
            sc[k] = manifest[k]
    path = os.path.join(out_dir or os.path.dirname(os.path.abspath(glb)), asset + ".sockets.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(sc, f, indent=1); f.write("\n")
    return path, sc


def find_manifest(manifest_path, asset):
    if not manifest_path:
        return None
    m = json.load(open(manifest_path, encoding="utf-8"))
    if "assets" in m:
        return next((a for a in m["assets"] if a["asset"] == asset), None)
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("glb"); ap.add_argument("--manifest"); ap.add_argument("--out"); ap.add_argument("--asset")
    o = ap.parse_args(); asset = o.asset or os.path.splitext(os.path.basename(o.glb))[0]
    p, sc = write_for_glb(o.glb, find_manifest(o.manifest, asset), o.out, asset)
    print(p, json.dumps(sc["sockets"]))
