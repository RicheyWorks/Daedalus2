# SPDX-License-Identifier: MIT
"""BBA 1 manifest generator (blender-team): reads the Blender catalog glbs and their _LOD1 siblings and writes
data/assets/catalog.bba for AssetLodManifest.java / DaedalusAssetLodCore.h. No Blender needed: faces come from the glTF
index accessors (triangles), bounds from the POSITION accessor min/max (mesh-local, in metres -> cm, half diagonal, rounded up).
Usage: python bba_manifest.py <glb dir> <out.bba>"""
import json, math, os, re, struct, sys

TOKEN = re.compile(r"^[A-Za-z0-9_.-]{1,96}$")
SKIP = ("Prop_Island_",)


def glb_stats(path):
    with open(path, "rb") as f:
        head = f.read(20)
        if len(head) < 20 or head[:4] != b"glTF":
            raise ValueError("not a glb")
        n, kind = struct.unpack("<II", head[12:20])
        if kind != 0x4E4F534A:
            raise ValueError("first chunk is not JSON")
        g = json.loads(f.read(n))
    acc = g.get("accessors", [])
    uses = {}
    for node in g.get("nodes", []):
        if "mesh" in node:
            uses[node["mesh"]] = uses.get(node["mesh"], 0) + 1
    faces, lo, hi = 0, [math.inf] * 3, [-math.inf] * 3
    for mi, mesh in enumerate(g.get("meshes", [])):
        k = uses.get(mi, 1)
        for p in mesh.get("primitives", []):
            if p.get("mode", 4) != 4:
                continue
            pos = acc[p["attributes"]["POSITION"]]
            count = acc[p["indices"]]["count"] if "indices" in p else pos["count"]
            faces += k * (count // 3)
            for i in range(3):
                lo[i] = min(lo[i], pos.get("min", [0, 0, 0])[i]); hi[i] = max(hi[i], pos.get("max", [0, 0, 0])[i])
    if faces == 0:
        raise ValueError("no triangles")
    radius = max(1, math.ceil(50.0 * math.sqrt(sum((hi[i] - lo[i]) ** 2 for i in range(3)))))
    return faces, radius


def main(src, out):
    names = sorted(f[:-4] for f in os.listdir(src) if f.endswith(".glb") and not f.endswith("_LOD1.glb") and not f.startswith(SKIP))
    rows, skipped = [], []
    for n in names:
        if not TOKEN.match(n):
            skipped.append((n, "bad id")); continue
        try:
            f0, r = glb_stats(os.path.join(src, n + ".glb"))
            f1 = None
            if os.path.exists(os.path.join(src, n + "_LOD1.glb")):
                f1 = min(glb_stats(os.path.join(src, n + "_LOD1.glb"))[0], f0)
        except Exception as e:  # unreadable glb: leave it out, say so
            skipped.append((n, str(e)[:60])); continue
        if f0 > 10_000_000:
            skipped.append((n, "too many faces")); continue
        rows.append("asset %s lod0 %d lod1 %s radius %d switch %d\n" % (n, f0, "-" if f1 is None else f1, min(r, 100_000_000), max(500, r * 20)))
    rows.sort(key=lambda s: s.split(" ")[1].encode())
    with open(out, "w", encoding="ascii", newline="\n") as f:
        f.write("BBA 1\n"); f.writelines(rows)
    with_lod1 = sum(" lod1 - " not in r for r in rows)
    print(json.dumps({"assets": len(rows), "with_lod1": with_lod1, "skipped": len(skipped), "skipped_first": skipped[:5]}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
