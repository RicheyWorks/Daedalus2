# SPDX-License-Identifier: MIT
"""BIP 1 splitter (blender-team): turns one huge island glb into small, bounded import packets plus a placement manifest.
Deterministic (no clocks, no randomness; same input + same caps -> byte-identical packets and manifest). Pure numpy, no Blender,
never touches Unreal.  Usage:  python bip_split.py <island.glb> <packet out dir> <manifest.json>

Layout (glTF is Y-up, metres; the manifest keeps the file's own space):
  terrain   the island base (nodes whose name ends _Terrain / _Underside) baked to world space and cut into a quadtree of
            chunks on the XZ plane by triangle centroid (no triangle is cut, shared edges keep identical vertices, so no cracks)
  props     every distinct prop mesh once, packed into library packets (nodes at the origin, one node per prop mesh)
  placements  one row per source node: which prop mesh (and packet) at which translation/rotation/scale, with a world AABB
Hard caps per packet (the script refuses to write a packet over any of them): tris, bytes, materials."""
import hashlib, json, math, os, re, sys
import numpy as np
from bip_glb import Builder, accessor, read_glb

CAPS = {"tris": 12000, "bytes": 1572864, "materials": 64}
TERRAIN_TARGET = 6000          # quadtree leaf target (well under the hard cap)
BASE_SUFFIX = ("_Terrain", "_Underside")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def node_rs(nd):
    s = np.array(nd.get("scale", [1, 1, 1]), float)
    r = quat_mat(nd.get("rotation", [0, 0, 0, 1]))
    return r * s, np.array(nd.get("translation", [0, 0, 0]), float)   # p' = (R*S) p + T  (columns of R scaled)


def mesh_prims(g, b, mi):
    out = []
    for p in g["meshes"][mi]["primitives"]:
        if p.get("mode", 4) != 4:
            raise ValueError("non-triangle primitive in mesh %d" % mi)
        at = p["attributes"]
        pos = np.array(accessor(g, b, at["POSITION"]), np.float32)
        out.append({"pos": pos, "nrm": np.array(accessor(g, b, at["NORMAL"]), np.float32) if "NORMAL" in at else None,
                    "uv": np.array(accessor(g, b, at["TEXCOORD_0"]), np.float32) if "TEXCOORD_0" in at else None,
                    "idx": np.array(accessor(g, b, p["indices"]), np.int64) if "indices" in p else np.arange(len(pos), dtype=np.int64),
                    "mat": g["materials"][p["material"]] if "material" in p else {"name": "M_BIP_Default"}})
    return out


def sub(prim, tri_sel):
    """New primitive with only the given triangles, vertices re-indexed in first-use order."""
    tris = prim["idx"].reshape(-1, 3)[tri_sel].reshape(-1)
    uniq, inv = np.unique(tris, return_inverse=True)
    return {"pos": prim["pos"][uniq], "nrm": None if prim["nrm"] is None else prim["nrm"][uniq],
            "uv": None if prim["uv"] is None else prim["uv"][uniq], "idx": inv.astype(np.int64), "mat": prim["mat"]}


def est_bytes(prims):
    n = 0
    for p in prims:
        v = len(p["pos"]); n += v * 12 * (1 + (p["nrm"] is not None)) + (v * 8 if p["uv"] is not None else 0) + len(p["idx"]) * (2 if v < 65536 else 4) + 64
    return n + 700


def tris_of(prims):
    return sum(len(p["idx"]) // 3 for p in prims)


def bounds_of(prims):
    lo = np.min([p["pos"].min(axis=0) for p in prims], axis=0); hi = np.max([p["pos"].max(axis=0) for p in prims], axis=0)
    return [round(float(x), 4) for x in lo], [round(float(x), 4) for x in hi]


def safe(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def write_packet(outdir, pid, builder, extras, kind, tris, meta):
    data = builder.finish(extras)
    nm = len(builder.mats)
    if tris > CAPS["tris"] or len(data) > CAPS["bytes"] or nm > CAPS["materials"]:
        raise SystemExit("packet %s over a hard cap: tris %d bytes %d materials %d" % (pid, tris, len(data), nm))
    fn = pid + ".glb"
    open(os.path.join(outdir, fn), "wb").write(data)
    rec = {"id": pid, "file": fn, "kind": kind, "tris": tris, "bytes": len(data), "sha256": sha256(data), "materials": nm}
    rec.update(meta)
    return rec


def main(src, outdir, manifest):
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.endswith(".glb"):
            os.remove(os.path.join(outdir, f))      # only our own packet files, in our own output dir
    raw = open(src, "rb").read()
    g, b = read_glb(src)
    nodes = g["nodes"]
    # ---- terrain: bake base nodes to world space, quadtree on XZ
    items = []   # (prim dict, tri centroid x, z) flattened per primitive
    base_nodes = [n for n in nodes if n.get("name", "").endswith(BASE_SUFFIX)]
    prim_world = []
    for nd in base_nodes:
        M, T = node_rs(nd)
        for p in mesh_prims(g, b, nd["mesh"]):
            pos = (p["pos"].astype(np.float64) @ M.T + T).astype(np.float32)
            nrm = None
            if p["nrm"] is not None:
                Ni = np.linalg.inv(M).T; nn = p["nrm"].astype(np.float64) @ Ni.T; nrm = (nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-12)).astype(np.float32)
            prim_world.append({"pos": pos, "nrm": nrm, "uv": p["uv"], "idx": p["idx"], "mat": p["mat"], "src": nd["name"]})
    cent = []
    for p in prim_world:
        t = p["idx"].reshape(-1, 3); c = p["pos"][t].mean(axis=1); cent.append(c[:, [0, 2]])
    lo = np.min([c.min(axis=0) for c in cent], axis=0); hi = np.max([c.max(axis=0) for c in cent], axis=0)
    leaves = []

    def split(path, x0, z0, x1, z1, sels):
        n = sum(len(s) for s in sels)
        if n == 0:
            return
        if n <= TERRAIN_TARGET or len(path) >= 8:
            leaves.append((path, sels)); return
        xm, zm = (x0 + x1) / 2, (z0 + z1) / 2
        for q, (a, c, d, e) in enumerate(((x0, z0, xm, zm), (xm, z0, x1, zm), (x0, zm, xm, z1), (xm, zm, x1, z1))):
            ns = []
            for ci, s in zip(cent, sels):
                cc = ci[s]
                ins = ((cc[:, 0] >= a) & ((cc[:, 0] < d) if q % 2 == 0 else (cc[:, 0] <= d)) & (cc[:, 1] >= c) & ((cc[:, 1] < e) if q < 2 else (cc[:, 1] <= e)))
                ns.append(s[ins])
            split(path + str(q), a, c, d, e, ns)

    split("", float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1]), [np.arange(len(c)) for c in cent])
    packets, terrain_rec = [], []
    terrain_tris = 0
    for path, sels in sorted(leaves):
        prims = [sub(p, s) for p, s in zip(prim_world, sels) if len(s)]
        bld = Builder(); bld.add_mesh("Terrain_" + path, prims)
        t = tris_of(prims); terrain_tris += t
        lo_, hi_ = bounds_of(prims)
        packets.append(write_packet(outdir, "flagship_terrain_" + (path or "0"), bld, {"bip": 1, "kind": "terrain", "quad": path}, "terrain", t,
                                    {"quad": path, "bounds_min": lo_, "bounds_max": hi_, "import": "static mesh at the origin; vertices are already in island space"}))
    # ---- props: distinct meshes once, packed into library packets
    base_ids = {id(n) for n in base_nodes}
    prop_nodes = [n for n in nodes if id(n) not in base_ids]
    mesh_ids = sorted({n["mesh"] for n in prop_nodes}, key=lambda mi: (g["meshes"][mi].get("name", ""), mi))
    used = {}
    lib, cur, cur_t, cur_b, cur_m = [], [], 0, 700, set()
    prop_info = {}
    for mi in mesh_ids:
        pr = mesh_prims(g, b, mi)
        t, eb = tris_of(pr), est_bytes(pr)
        mats = {json.dumps(p["mat"], sort_keys=True) for p in pr}
        if t > CAPS["tris"] or eb > CAPS["bytes"] or len(mats) > CAPS["materials"]:
            raise SystemExit("single prop mesh %d (%s) is over a hard cap" % (mi, g["meshes"][mi].get("name")))
        if cur and (cur_t + t > CAPS["tris"] * 0.8 or cur_b + eb > CAPS["bytes"] * 0.8 or len(cur_m | mats) > CAPS["materials"] * 0.8):
            lib.append(cur); cur, cur_t, cur_b, cur_m = [], 0, 700, set()
        cur.append((mi, pr)); cur_t += t; cur_b += eb; cur_m |= mats
    if cur:
        lib.append(cur)
    for k, group in enumerate(lib):
        bld = Builder(); names = {}; t_all = 0
        for mi, pr in group:
            base = safe(g["meshes"][mi].get("name") or "mesh") ; nm = base if base not in names.values() else "%s__m%d" % (base, mi); names[mi] = nm
            bld.add_mesh(nm, pr); t_all += tris_of(pr)
            lo_, hi_ = bounds_of(pr)
            prop_info[mi] = {"name": nm, "src_mesh_name": g["meshes"][mi].get("name"), "packet": "flagship_props_%03d" % k, "tris": tris_of(pr), "bounds_min": lo_, "bounds_max": hi_}
        packets.append(write_packet(outdir, "flagship_props_%03d" % k, bld, {"bip": 1, "kind": "props", "meshes": list(names.values())}, "props", t_all,
                                    {"meshes": len(group), "import": "library: one static mesh per node, all at the origin (not a scene); place via the manifest placements"}))
    # ---- placements
    placements = []
    for n in prop_nodes:
        mi = n["mesh"]; M, T = node_rs(n); info = prop_info[mi]
        lo_, hi_ = np.array(info["bounds_min"]), np.array(info["bounds_max"])
        corners = np.array([[x, y, z] for x in (lo_[0], hi_[0]) for y in (lo_[1], hi_[1]) for z in (lo_[2], hi_[2])]) @ M.T + T
        placements.append({"node": n.get("name"), "prop": info["name"], "packet": info["packet"], "translation": [round(float(x), 5) for x in T],
                           "rotation": [round(float(x), 6) for x in n.get("rotation", [0, 0, 0, 1])],
                           "scale": [round(float(x), 5) for x in n.get("scale", [1, 1, 1])],
                           "world_min": [round(float(x), 3) for x in corners.min(axis=0)], "world_max": [round(float(x), 3) for x in corners.max(axis=0)]})
    placements.sort(key=lambda p: (p["packet"], p["prop"], p["translation"], p["node"]))
    prop_inst_tris = sum(prop_info[mi]["tris"] * sum(1 for n in prop_nodes if n["mesh"] == mi) for mi in mesh_ids)
    acc = g["accessors"]
    src_tris = sum(sum(acc[p["indices"]]["count"] // 3 for p in g["meshes"][n["mesh"]]["primitives"]) for n in nodes)
    all_w = [np.array(p["world_min"]) for p in placements] + [np.array(p["world_max"]) for p in placements]
    wlo = np.min([np.array(r["bounds_min"]) for r in packets if r["kind"] == "terrain"] + all_w, axis=0)
    whi = np.max([np.array(r["bounds_max"]) for r in packets if r["kind"] == "terrain"] + all_w, axis=0)
    man = {"bip": 1, "source": {"file": os.path.basename(src), "bytes": len(raw), "sha256": sha256(raw), "nodes": len(nodes), "meshes": len(g["meshes"]),
                                "materials": len(g["materials"]), "tris_by_instance": src_tris},
           "caps": CAPS, "terrain_target_tris": TERRAIN_TARGET, "units": "metres, glTF Y-up", "packet_dir": "art/packets/flagship",
           "ingestion": "offline output only; import one packet at a time in a claimed turn, never from the art watcher; terrain first, then props, then placements",
           "totals": {"packets": len(packets), "terrain_packets": sum(r["kind"] == "terrain" for r in packets), "prop_packets": sum(r["kind"] == "props" for r in packets),
                      "terrain_tris": terrain_tris, "prop_library_tris": sum(r["tris"] for r in packets if r["kind"] == "props"), "placements": len(placements),
                      "instanced_prop_tris": prop_inst_tris, "tris_by_instance": terrain_tris + prop_inst_tris, "bytes": sum(r["bytes"] for r in packets),
                      "max_packet_tris": max(r["tris"] for r in packets), "max_packet_bytes": max(r["bytes"] for r in packets),
                      "world_min": [round(float(x), 3) for x in wlo], "world_max": [round(float(x), 3) for x in whi]},
           "packets": packets, "props": [prop_info[mi] for mi in mesh_ids], "placements": placements}
    with open(manifest, "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=1, sort_keys=False); f.write("\n")
    print(json.dumps({"source_tris": src_tris, "packets_tris": man["totals"]["tris_by_instance"], **{k: v for k, v in man["totals"].items() if k.startswith(("packets", "terrain_p", "prop_p", "max_", "placements", "bytes"))}}))
    if src_tris != man["totals"]["tris_by_instance"]:
        raise SystemExit("triangle total mismatch")


if __name__ == "__main__":
    main(*sys.argv[1:4])
