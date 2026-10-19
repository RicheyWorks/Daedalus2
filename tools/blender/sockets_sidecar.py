# SPDX-License-Identifier: MIT
"""Socket sidecar for Unreal (blender-team). Stock glTF Interchange drops SOCKET_ empties (unreal-epic-boss 48518/48519,
PR197), so every socketed asset ships <Asset>.sockets.json next to its glb; the empties stay in the glb as well.

  {"asset": ..., "units": "cm", "space": "unreal",
   "sockets": [{"name", "parent", "location": [x, y, z], "rotation": [pitch, yaw, roll]}]}

Unreal space: +X forward, +Y right, +Z up, centimetres, left-handed. Our Blender convention (BLENDER-TEAM-BRIEF; buffffff
48487): front = Blender -Y = Unreal +X, up = Blender Z. Keeping the shape un-mirrored fixes the third axis:
    UE = 100 * (-y_b, -x_b, z_b)          and from glTF (+Y up, Blender (x,y,z) -> glTF (x,z,-y)):  UE = 100 * (gz, -gx, gy)
location is relative to the socket's parent node (the static mesh Interchange makes from that node). rotation comes
from the socket's forward vector (yaw about Z, pitch toward Z; roll 0); sockets without one get [0, 0, 0].

  python sockets_sidecar.py <asset.glb> [--manifest <recipe or kit json>] [--out <dir>]   -> <dir>/<Asset>.sockets.json
"""
import argparse, json, math, os, struct

SCHEMA_NOTE = "UE +X forward, +Y right, +Z up, cm; location relative to parent node; rotation [pitch, yaw, roll] deg"


def blender_to_ue(v):
    x, y, z = v
    return [round(-y * 100.0, 4) + 0.0, round(-x * 100.0, 4) + 0.0, round(z * 100.0, 4) + 0.0]


def gltf_to_ue(v):
    gx, gy, gz = v
    return [round(gz * 100.0, 4) + 0.0, round(-gx * 100.0, 4) + 0.0, round(gy * 100.0, 4) + 0.0]


def forward_to_rotation(fwd_blender):
    """Blender forward vector -> UE [pitch, yaw, roll] degrees (roll 0)."""
    fx, fy, fz = (c / 100.0 for c in blender_to_ue(fwd_blender))
    yaw = math.degrees(math.atan2(fy, fx)) if (fx or fy) else 0.0
    pitch = math.degrees(math.atan2(fz, math.hypot(fx, fy)))
    return [round(pitch, 4) + 0.0, round(yaw, 4) + 0.0, 0.0]


def read_glb_json(path):
    with open(path, "rb") as f:
        b = f.read()
    if b[:4] != b"glTF":
        raise ValueError("not a glb: %s" % path)
    n = struct.unpack_from("<I", b, 12)[0]
    return json.loads(b[20:20 + n].decode("utf-8"))


def _forwards(manifest):
    """{socket name: Blender forward} from a recipe (crate/rifle) or blender-kit/v1 manifest, if given."""
    out = {}
    if not manifest:
        return out
    socks = manifest.get("sockets", [])
    for s in socks:
        if s.get("forward") is not None:
            out[s["name"]] = s["forward"]
    return out


def from_gltf(doc, asset=None, manifest=None):
    nodes = doc.get("nodes", []); parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    fw = _forwards(manifest); socks = []
    for i, n in enumerate(nodes):
        name = n.get("name", "")
        if not name.upper().startswith("SOCKET_"):
            continue
        if n.get("rotation") not in (None, [0, 0, 0, 1], [0.0, 0.0, 0.0, 1.0]) or n.get("scale") not in (None, [1, 1, 1], [1.0, 1.0, 1.0]) or "matrix" in n:
            raise ValueError("socket %s has a rotation/scale/matrix; only translations are supported" % name)
        p = parent.get(i)
        socks.append({"name": name, "parent": nodes[p].get("name") if p is not None else None,
                      "location": gltf_to_ue(n.get("translation", [0, 0, 0])),
                      "rotation": forward_to_rotation(fw[name]) if name in fw else [0.0, 0.0, 0.0]})
    roots = [nodes[i].get("name") for i in range(len(nodes)) if i not in parent and "mesh" in nodes[i]]
    return {"asset": asset or (roots[0] if roots else None), "units": "cm", "space": "unreal", "note": SCHEMA_NOTE,
            "sockets": sorted(socks, key=lambda s: s["name"])}


def write_for_glb(glb, manifest=None, out_dir=None, asset=None):
    doc = read_glb_json(glb); asset = asset or os.path.splitext(os.path.basename(glb))[0]
    sc = from_gltf(doc, asset, manifest)
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
