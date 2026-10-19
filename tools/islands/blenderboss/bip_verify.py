# SPDX-License-Identifier: MIT
"""BIP 1 verifier (blender-team): recomputes everything from the packet files themselves (sizes, sha256, triangle counts from
index accessors, bounds from the vertex data, caps, finiteness, index ranges), cross-checks the placement manifest, and, when the
source glb is present, checks the totals against it. Exit 0 only if every check passes.
Usage: python bip_verify.py <manifest.json> <packet dir> [source.glb] [--rebuild]"""
import hashlib, json, os, subprocess, sys, tempfile
import numpy as np
from bip_glb import accessor, read_glb


def main(manifest, pdir, src=None, rebuild=False):
    m = json.load(open(manifest, encoding="utf-8"))
    caps = m["caps"]; fails = []; ok = 0

    def chk(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(msg)

    nodes_in = {}; tris_by_kind = {"terrain": 0, "props": 0}; tri_of_node = {}; tb = {}
    files = {f for f in os.listdir(pdir) if f.endswith(".glb")}
    chk(files == {p["file"] for p in m["packets"]}, "packet dir has files not in the manifest or vice versa")
    for p in m["packets"]:
        path = os.path.join(pdir, p["file"])
        if not os.path.exists(path):
            chk(False, p["id"] + ": packet file missing"); continue
        raw = open(path, "rb").read()
        chk(len(raw) == p["bytes"], p["id"] + ": byte size differs"); chk(hashlib.sha256(raw).hexdigest() == p["sha256"], p["id"] + ": sha256 differs")
        chk(len(raw) <= caps["bytes"], p["id"] + ": over byte cap")
        try:
            g, b = read_glb(path)
        except Exception as e:
            chk(False, p["id"] + ": unreadable glb (%s)" % e); continue
        chk(len(g.get("materials", [])) <= caps["materials"] and len(g.get("materials", [])) == p["materials"], p["id"] + ": materials over cap/differ")
        tris = 0; lo = np.full(3, np.inf); hi = np.full(3, -np.inf); good = True
        for nd in g["nodes"]:
            mt = 0
            for pr in g["meshes"][nd["mesh"]]["primitives"]:
                pos = accessor(g, b, pr["attributes"]["POSITION"]); idx = accessor(g, b, pr["indices"]); a = g["accessors"][pr["attributes"]["POSITION"]]
                good &= bool(np.isfinite(pos).all()) and len(idx) % 3 == 0 and int(idx.max()) < len(pos) and pr.get("mode", 4) == 4
                if "NORMAL" in pr["attributes"]:
                    good &= bool(np.isfinite(accessor(g, b, pr["attributes"]["NORMAL"])).all())
                good &= bool(np.allclose(pos.min(axis=0), a["min"], atol=1e-6) and np.allclose(pos.max(axis=0), a["max"], atol=1e-6))
                mt += len(idx) // 3; lo = np.minimum(lo, pos.min(axis=0)); hi = np.maximum(hi, pos.max(axis=0))
            tris += mt; tri_of_node[(p["id"], nd["name"])] = (mt, nd["mesh"], g, b)
        chk(good, p["id"] + ": bad geometry (NaN, index out of range, non-triangles, accessor min/max wrong)")
        chk(tris == p["tris"], p["id"] + ": tris differ (file %d, manifest %d)" % (tris, p["tris"])); chk(tris <= caps["tris"], p["id"] + ": over tri cap")
        tris_by_kind[p["kind"]] += tris
        if p["kind"] == "terrain":
            chk(np.allclose(lo, p["bounds_min"], atol=1e-3) and np.allclose(hi, p["bounds_max"], atol=1e-3), p["id"] + ": bounds differ from the vertex data")
    props = {pr["name"]: pr for pr in m["props"]}
    for name, pr in props.items():
        k = (pr["packet"], name); chk(k in tri_of_node, "prop %s missing from %s" % (name, pr["packet"]))
        if k in tri_of_node:
            mt, mi, g, b = tri_of_node[k]; chk(mt == pr["tris"], "prop %s tris differ" % name)
            pos = np.concatenate([accessor(g, b, q["attributes"]["POSITION"]) for q in g["meshes"][mi]["primitives"]])
            chk(np.allclose(pos.min(axis=0), pr["bounds_min"], atol=1e-3) and np.allclose(pos.max(axis=0), pr["bounds_max"], atol=1e-3), "prop %s bounds differ" % name)
    inst = 0; wlo = np.full(3, np.inf); whi = np.full(3, -np.inf)
    for pl in m["placements"]:
        pr = props.get(pl["prop"]); chk(pr is not None and pr["packet"] == pl["packet"], "placement %s points at an unknown prop/packet" % pl["node"])
        if pr:
            inst += pr["tris"]
        chk(all(s > 0 for s in pl["scale"]) and abs(sum(q * q for q in pl["rotation"]) - 1) < 1e-3, "placement %s has a bad scale/rotation" % pl["node"])
        wlo = np.minimum(wlo, pl["world_min"]); whi = np.maximum(whi, pl["world_max"])
    t = m["totals"]
    chk(inst == t["instanced_prop_tris"], "instanced prop tris differ"); chk(len(m["placements"]) == t["placements"], "placement count differs")
    chk(tris_by_kind["terrain"] == t["terrain_tris"], "terrain tris differ"); chk(tris_by_kind["props"] == t["prop_library_tris"], "prop library tris differ")
    chk(tris_by_kind["terrain"] + inst == t["tris_by_instance"], "total tris differ")
    chk(max(p["tris"] for p in m["packets"]) == t["max_packet_tris"] and max(p["bytes"] for p in m["packets"]) == t["max_packet_bytes"], "max packet stats differ")
    chk(bool(np.all(wlo >= np.array(t["world_min"]) - 1e-2) and np.all(whi <= np.array(t["world_max"]) + 1e-2)), "placements outside the declared world bounds")
    if src and os.path.exists(src):
        raw = open(src, "rb").read(); g, b = read_glb(src)
        chk(hashlib.sha256(raw).hexdigest() == m["source"]["sha256"], "source glb sha256 differs from the manifest (source changed)")
        st = sum(sum(g["accessors"][q["indices"]]["count"] // 3 for q in g["meshes"][n["mesh"]]["primitives"]) for n in g["nodes"])
        chk(st == t["tris_by_instance"] == m["source"]["tris_by_instance"], "source tris (%d) != packets total (%d)" % (st, t["tris_by_instance"]))
        chk(len(g["nodes"]) == len(m["placements"]) + sum(1 for n in g["nodes"] if n["name"].endswith(("_Terrain", "_Underside"))), "node count != placements + base nodes")
    if rebuild:
        with tempfile.TemporaryDirectory() as td:
            here = os.path.dirname(os.path.abspath(__file__)); mj = os.path.join(td, "m.json")
            subprocess.run([sys.executable, os.path.join(here, "bip_split.py"), src, os.path.join(td, "p"), mj], check=True, capture_output=True)
            m2 = json.load(open(mj, encoding="utf-8"))
            chk([p["sha256"] for p in m2["packets"]] == [p["sha256"] for p in m["packets"]] and m2["placements"] == m["placements"], "rebuild is not byte-identical")
    print(json.dumps({"checks_passed": ok, "checks_failed": len(fails), "packets": len(m["packets"]), "max_packet_tris": t["max_packet_tris"], "max_packet_bytes": t["max_packet_bytes"],
                      "tris_by_instance": t["tris_by_instance"], "failures": fails[:10]}))
    return 0 if not fails else 1


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    sys.exit(main(a[0], a[1], a[2] if len(a) > 2 else None, "--rebuild" in sys.argv))
