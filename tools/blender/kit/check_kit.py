# SPDX-License-Identifier: MIT
"""Self-check built blender-kit/v1 assets from the files alone (no Blender, no Unreal), against their kit manifest.
  python tools/blender/kit/check_kit.py --set <x.kit.json> --out <staging dir>   -> prints n/m per asset, writes selfcheck.json
Checks: glb readable; every recipe object is a mesh node with the predicted triangles and its parent; collision children
(UCX_/USP_) under the right parent with the predicted tris and no material; SOCKET_ empties present under the right
parent; the sockets sidecar matches; LOD1 glb triangles; render bounds (glTF, metres) = predicted within 1 mm;
build_report ok and its sha256s match the files."""
import argparse, hashlib, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sockets_sidecar as SS


def tris(doc, mi):
    t = 0
    for p in doc["meshes"][mi]["primitives"]:
        if p.get("mode", 4) == 4:
            t += (doc["accessors"][p["indices"]]["count"] if "indices" in p else doc["accessors"][p["attributes"]["POSITION"]]["count"]) // 3
    return t


def world_bounds(doc, skip=("UCX_", "USP_", "UBX_", "UCP_")):
    """Render-mesh bounds in glTF space, applying node translations (our nodes have no rotation/scale)."""
    par = {c: i for i, n in enumerate(doc["nodes"]) for c in n.get("children", [])}
    def off(i):
        t = [0.0, 0.0, 0.0]
        while i is not None:
            tr = doc["nodes"][i].get("translation", [0, 0, 0]); t = [t[k] + tr[k] for k in range(3)]; i = par.get(i)
        return t
    lo, hi = [1e9] * 3, [-1e9] * 3
    for i, n in enumerate(doc["nodes"]):
        if "mesh" not in n or n.get("name", "").startswith(skip):
            continue
        o = off(i)
        for p in doc["meshes"][n["mesh"]]["primitives"]:
            a = doc["accessors"][p["attributes"]["POSITION"]]
            lo = [min(lo[k], a["min"][k] + o[k]) for k in range(3)]; hi = [max(hi[k], a["max"][k] + o[k]) for k in range(3)]
    return lo, hi


def check(m, d):
    name = m["asset"]; c = []; add = lambda n, ok, det="": c.append([n, bool(ok), det])
    glb = os.path.join(d, name + ".glb")
    doc = SS.read_glb_json(glb); nodes = doc["nodes"]; by = {n.get("name"): i for i, n in enumerate(nodes)}
    par = {ch: i for i, n in enumerate(nodes) for ch in n.get("children", [])}
    pname = lambda i: nodes[par[i]].get("name") if i in par else None
    for o in m["objects"]:
        i = by.get(o["name"]); ok = i is not None and "mesh" in nodes[i]
        add("mesh node %s" % o["name"], ok)
        if ok:
            add("%s tris %d" % (o["name"], m["predicted"]["objects"][o["name"]]), tris(doc, nodes[i]["mesh"]) == m["predicted"]["objects"][o["name"]], tris(doc, nodes[i]["mesh"]))
            add("%s parent %s" % (o["name"], o["parent"]), pname(i) == o["parent"], pname(i))
    for col in m.get("collision", []):
        i = by.get(col["name"]); ok = i is not None and "mesh" in nodes[i]
        add("collision %s present" % col["name"], ok)
        if ok:
            prim = doc["meshes"][nodes[i]["mesh"]]["primitives"]
            add("collision %s tris %d, no material, parent %s" % (col["name"], col["tris"], col["parent"] or name),
                tris(doc, nodes[i]["mesh"]) == col["tris"] and all("material" not in p for p in prim) and pname(i) == (col["parent"] or name))
    for s in m["sockets"]:
        i = by.get(s["name"])
        add("socket %s under %s" % (s["name"], s["parent"] or name), i is not None and "mesh" not in nodes[i] and pname(i) == (s["parent"] or name))
    if m["sockets"]:
        sp = os.path.join(d, name + ".sockets.json"); ok = os.path.exists(sp)
        add("sockets sidecar present", ok)
        if ok:
            sc = json.load(open(sp, encoding="utf-8")); want = SS.from_gltf(doc, name, m)
            add("sidecar = glb sockets in UE space", sc["sockets"] == want["sockets"] and sc["units"] == "cm" and sc["space"] == "unreal")
    lo, hi = world_bounds(doc); pr = m["predicted"]
    want_lo = [pr["bounds_min"][0], pr["bounds_min"][2], -pr["bounds_max"][1]]; want_hi = [pr["bounds_max"][0], pr["bounds_max"][2], -pr["bounds_min"][1]]
    add("render bounds = predicted (1 mm)", all(abs(lo[k] - want_lo[k]) <= 0.001 and abs(hi[k] - want_hi[k]) <= 0.001 for k in range(3)),
        [[round(v, 4) for v in lo], [round(v, 4) for v in hi]])
    if pr["lod1_triangles"] is not None:
        l1 = os.path.join(d, name + "_LOD1.glb"); ok = os.path.exists(l1)
        add("LOD1 glb present", ok)
        if ok:
            d1 = SS.read_glb_json(l1); t1 = sum(tris(d1, n["mesh"]) for n in d1["nodes"] if "mesh" in n)
            add("LOD1 tris %d" % pr["lod1_triangles"], t1 == pr["lod1_triangles"], t1)
            add("LOD1 has no sockets/collision", not any(n.get("name", "").startswith(("SOCKET_", "UCX_", "USP_")) for n in d1["nodes"]))
    rep = json.load(open(os.path.join(d, "build_report.json"), encoding="utf-8"))
    add("build_report ok", rep.get("ok"), rep.get("match"))
    add("report sha256 = files", all(hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest() == v["sha256"] for f, v in rep["files"].items()))
    return c


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--set", required=True); ap.add_argument("--out", required=True); ap.add_argument("--only", default="")
    o = ap.parse_args(); S = json.load(open(o.set, encoding="utf-8")); only = set(filter(None, o.only.split(","))); res = {}; bad = 0
    for m in S["assets"]:
        if only and m["asset"] not in only:
            continue
        d = os.path.join(o.out, m["asset"]); cs = check(m, d); res[m["asset"]] = cs
        n = sum(x[1] for x in cs); bad += n != len(cs)
        print("%s selfcheck %d/%d" % (m["asset"], n, len(cs)) + "".join("\n   FAIL %s %s" % (x[0], x[2]) for x in cs if not x[1]))
        json.dump(cs, open(os.path.join(d, "selfcheck.json"), "w"), indent=1)
    sys.exit(1 if bad else 0)
