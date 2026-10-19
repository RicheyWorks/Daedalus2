# SPDX-License-Identifier: MIT
"""G20 Ashfall Regrowth art for pythagoras (48721 pyth-g20-assets-20261019; code main c203b07e AshfallRegrowth), blender-kit/v1.
  Prop_Ash_SeedCache_Closed/_Open  ~0.8 m ark seed cache crate; the lid is the named child node <asset>_Lid hinged on the back top
      edge (Open = swung up and back 105 deg); two seed sacks inside; SOCKET_Seeds inside; UCX for body and lid (lid UCX on the lid).
  Prop_WaterBucket  ~0.4 m wooden bucket with iron bands and a bail handle; the water surface is the child node Prop_WaterBucket_Water
      with SOCKET_Water on it (same idea as the G03 trough); UCX prism.
Herd and flora are REUSE only (not built): see REUSE below and the DONE post.
Front = Blender -Y (lands on UE +Y; face with yaw -90 at placement, buffffff 48769).
Usage: python ash_g20.py --out data/contest/ash_g20.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 2020
SC, WB = "Prop_Ash_SeedCache", "Prop_WaterBucket"
CAPS = {SC + "_Closed": 3000, SC + "_Open": 3000, WB: 3000}
SOCKETS = {SC + "_Closed": ["SOCKET_Seeds"], SC + "_Open": ["SOCKET_Seeds"], WB: ["SOCKET_Water"]}
WOOD, IRON, BURLAP, SEED_G, WATER = "7A5232", "3A3A3E", "B89B6A", "8DB255", "3E7CA8"
HINGE = (0.0, 0.275, 0.5)
REUSE = {"herd": "Mob_BUF_Gruffsheep_* / Mob_BUF_Puffgoat_* (buffffff livestock), Mob_DS_MossGoat_* / Mob_DS_CacheCow_* (disksaver)",
         "flora": "pcg-ecology bands (Daedalus2-pcg-ecology, d8f4f11b)"}


def _rotx(c, deg):
    t = math.radians(deg); y, z = c[1] - HINGE[1], c[2] - HINGE[2]
    return [c[0], round(HINGE[1] + y * math.cos(t) - z * math.sin(t), 5), round(HINGE[2] + y * math.sin(t) + z * math.cos(t), 5)]


def seedcache(state, seed=SEED):
    a = "%s_%s" % (SC, state); op = state == "Open"; lid = a + "_Lid"; r = K.rng(seed, SC)
    mats = [K.material(a, 0, "ark wood", WOOD, 0.9), K.material(a, 1, "iron", IRON, 0.8, 0.3), K.material(a, 2, "burlap", BURLAP, 0.95)]
    P = [K.box("Bottom", (0.8, 0.55, 0.05), (0, 0, 0.025), 0),
         K.box("WallFront", (0.8, 0.05, 0.45), (0, -0.25, 0.275), 0), K.box("WallBack", (0.8, 0.05, 0.45), (0, 0.25, 0.275), 0),
         K.box("WallL", (0.05, 0.45, 0.45), (0.375, 0, 0.275), 0), K.box("WallR", (0.05, 0.45, 0.45), (-0.375, 0, 0.275), 0)]
    for i, (x, y) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
        P.append(K.box("Strap%d" % i, (0.06, 0.06, 0.5), (0.375 * x, 0.25 * y, 0.25), 1, lod1={"drop": True}))
    for i, x in enumerate((-0.17, 0.17)):
        h = 0.3 + r.uniform(-0.03, 0.03)
        P.append(K.box("Sack%d" % i, (0.3, 0.38, h), (x, 0, 0.05 + h / 2), 2))
    L = [K.box("LidSlab", (0.82, 0.57, 0.08), (0, 0, 0.54), 0),
         K.box("LidBand0", (0.06, 0.59, 0.09), (-0.25, 0, 0.54), 1, lod1={"drop": True}), K.box("LidBand1", (0.06, 0.59, 0.09), (0.25, 0, 0.54), 1, lod1={"drop": True}),
         K.box("Handle", (0.16, 0.04, 0.03), (0, -0.2, 0.595), 1, lod1={"drop": True})]
    lsize, lcent = [0.82, 0.57, 0.09], [0, 0, 0.54]
    if op:
        for p in L:
            p["centre"] = _rotx(p["centre"], -105); p["rot"] = [-105, 0, 0]
        lsize, lcent = [0.82, 0.09, 0.57], _rotx(lcent, -105)
    m = {"asset": a, "kind": "Prop", "seed": seed, "state": state, "state_of": SC,
         "spec": {"gap": "G20", "size_m": "~0.8 m", "tri_cap": 3000, "states": ["Closed", "Open"], "lid": "named child node", "asker": "pythagoras 48721"},
         "materials": mats, "objects": [K.obj(a, P), K.obj(lid, L, parent=a, pivot=HINGE, role="lid (hinge pivot on the back top edge; Unreal may swing it)")],
         "sockets": [K.socket("Seeds", (0, 0, 0.38), forward=(0, 0, 1))],
         "collision": [K.ucx_box(a, 0, (0.8, 0.55, 0.5), (0, 0, 0.25)), K.ucx_box(a, 1, lsize, lcent, parent=lid)], "reuse": REUSE, "nanite": True}
    if op:
        m["off_centre_ok"] = "Open lid swings up and back (+Y); root pivot stays the Closed crate's bottom centre so both states line up"
    return K.finish(m)


def bucket(seed=SEED):
    a = WB; w = a + "_Water"
    mats = [K.material(a, 0, "wood", WOOD, 0.9), K.material(a, 1, "iron", IRON, 0.8, 0.3), K.material(a, 2, "water (opaque)", WATER, 0.1)]
    P = [K.lathe("Body", [(0.005, 0.03), (0.13, 0.03), (0.15, 0.38), (0.165, 0.38), (0.145, 0.0), (0.005, 0.0)], (0, 0, 0), 0, 16, True, True, lod1={"segments": 8})]
    for i, z in enumerate((0.07, 0.3)):
        rr = 0.145 + 0.02 * z / 0.38 + 0.003
        P.append(K.lathe("Band%d" % i, [(rr, z), (rr + 0.006, z), (rr + 0.006, z + 0.025), (rr, z + 0.025), (rr, z)], (0, 0, 0), 1, 16, False, False, lod1={"drop": True}))
    n, ax, az, z0 = 7, 0.175, 0.16, 0.37             # bail handle: an upright arch in the X-Z plane, ears on the rim
    for i in range(n):
        t = math.pi * (i + 0.5) / n
        P.append(K.box("Bail%d" % i, (0.088, 0.012, 0.012), (round(ax * math.cos(t), 5), 0, round(z0 + az * math.sin(t), 5)), 1,
                       rot=(0, round(-math.degrees(math.atan2(az * math.cos(t), -ax * math.sin(t))), 4), 0), lod1={"drop": i % 2 == 1}))
    W = [K.cyl("Surface", "z", 0.138, 0.138, 0.01, (0, 0, 0.3), 2, 16, lod1={"segments": 8})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": {"gap": "G20", "size_m": "~0.4 m", "tri_cap": 3000, "asker": "pythagoras 48721"},
         "materials": mats, "objects": [K.obj(a, P), K.obj(w, W, parent=a, pivot=(0, 0, 0.305), role="water surface (separate node)")],
         "sockets": [K.socket("Water", (0, 0, 0.305), parent=w, forward=(0, 0, 1))],
         "collision": [K.ucx_prism(a, 0, "z", 0.17, 0.42, (0, 0, 0.21))], "reuse": REUSE, "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    sc_, so_ = seedcache("Closed", seed), seedcache("Open", seed)
    return [sc_, so_] + K.split_into(CAPS, SOCKETS, 3000, sc_, so_) + [bucket(seed)]


def extra_checks(A):
    C, O, B = A[SC + "_Closed"], A[SC + "_Open"], A[WB]
    return [("seed cache ~0.8 m", abs(C["predicted"]["dimensions"][0] - 0.82) < 0.01, C["predicted"]["dimensions"]),
            ("seed cache states: same nodes, pivots, sockets, tris", [o["name"].replace("_Open", "_Closed") for o in O["objects"]] == [o["name"] for o in C["objects"]]
             and [o["pivot"] for o in O["objects"]] == [o["pivot"] for o in C["objects"]] and O["sockets"] == C["sockets"] and O["predicted"]["triangles"] == C["predicted"]["triangles"], ""),
            ("lid is a named child node with its own UCX", all(g["objects"][1]["name"] == g["asset"] + "_Lid" and sum(c["parent"] == g["asset"] + "_Lid" for c in g["collision"]) == 1 for g in (C, O)), ""),
            ("open lid clears the opening (lid above and behind)", O["predicted"]["bounds_max"][2] > 1.0 and O["predicted"]["bounds_max"][1] > C["predicted"]["bounds_max"][1], O["predicted"]["bounds_max"]),
            ("bucket ~0.4 m body, handle up", 0.5 <= B["predicted"]["dimensions"][2] <= 0.56, B["predicted"]["dimensions"]),
            ("bucket water is a child node under the rim", B["objects"][1]["name"] == WB + "_Water" and B["objects"][1]["parts"][0]["centre"][2] < 0.38, ""),
            ("herd + flora reuse named, not built", set(REUSE) == {"herd", "flora"} and not any(k.startswith("Mob_") for k in A), "")]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
