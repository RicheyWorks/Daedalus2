# SPDX-License-Identifier: MIT
"""G103 Soot Moths smoke filter (pythagoras 49770, pyth-g103-assets-20261019; code 9fcb07bd SootMoths: up to 3 filters, each
removes 25% of the soot; filter() is the keeper's action), blender-kit/v1.
Prop_Forge_SmokeFilter  chimney baffle hood: a 0.7 m square collar that sleeves over a 0.6 m flue, a charcoal filter cartridge,
                        four corner posts holding a square pyramid cowl (smoke leaves sideways under the cowl), three angled
                        baffle plates inside the opening, copper rivet bands, and a small capped vent on top.
                        SOCKET_Chimney at the collar's bottom centre (snap onto the chimney top; Prop_ForgeChimney_* has no top
                        socket, so UE places it at the chimney's top centre), SOCKET_Smoke at the vent outlet (soot VFX; scale the
                        plume by 1 - filters * 0.25). Root UCX: collar + cowl.
REUSE check: no hood/cowl/filter in the catalog (Prop_ForgeChimney_* are hephaestus' plain placeholder blocks, not modified).
Usage: python forge_g103.py --out data/contest/forge_g103.kit.json"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 1033
FILT = "Prop_Forge_SmokeFilter"
CAPS = {FILT: 1500}
SOCKETS = {FILT: ["SOCKET_Chimney", "SOCKET_Smoke"]}
SPEC = {"gap": "G103", "ask": "pythagoras 49770", "lod": "LOD0/1"}
FLUE, COLLAR, WALL, COLLAR_H = 0.6, 0.7, 0.05, 0.3
POST_H, COWL_Z, COWL_HALF, COWL_H = 0.3, 0.6, 0.55, 0.28


def mats(a):
    return [K.material(a, 0, "blackened iron", "2E2C2A", 0.6, metallic=0.7), K.material(a, 1, "copper rivet bands", "B87333", 0.45, metallic=0.85),
            K.material(a, 2, "charcoal filter mesh", "141414", 0.95)]


def filt(seed=SEED):
    a = FILT; h = COLLAR / 2; P = []
    for i, (sx, sy, cx, cy) in enumerate(((COLLAR, WALL, 0, h - WALL / 2), (COLLAR, WALL, 0, -h + WALL / 2), (WALL, COLLAR - 2 * WALL, h - WALL / 2, 0), (WALL, COLLAR - 2 * WALL, -h + WALL / 2, 0))):
        P += K.plain_lod1(K.box("Collar%d" % i, (sx, sy, COLLAR_H), (cx, cy, COLLAR_H / 2), 0))
    P.append(K.box("Cartridge", (COLLAR - 2 * WALL, COLLAR - 2 * WALL, 0.08), (0, 0, COLLAR_H - 0.06), 2, bevel=False))
    for i, z in enumerate((0.06, COLLAR_H - 0.03)):             # rivet bands: rings of 4 thin straps outside the collar walls
        for j, (sx, sy, cx, cy) in enumerate(((COLLAR + 0.012, 0.006, 0, h + 0.003), (COLLAR + 0.012, 0.006, 0, -h - 0.003),
                                               (0.006, COLLAR, h + 0.003, 0), (0.006, COLLAR, -h - 0.003, 0))):
            P.append(K.box("RivetBand%d_%d" % (i, j), (sx, sy, 0.025), (cx, cy, z), 1, bevel=False, lod1={"drop": True} if i else None))
    for i, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        P.append(K.box("Post%d" % i, (0.05, 0.05, POST_H), (sx * (h - 0.025), sy * (h - 0.025), COLLAR_H + POST_H / 2), 0, lod1={"drop": True} if i % 2 else None))
        if i % 2:
            P.append(dict(K.box("Post%d_L1" % i, (0.05, 0.05, POST_H), (sx * (h - 0.025), sy * (h - 0.025), COLLAR_H + POST_H / 2), 0, bevel=False), lod1={"only": True}))
    for i in range(3):                                   # angled baffles across the opening (smoke must zig-zag through)
        P.append(K.box("Baffle%d" % i, (COLLAR - 0.12, 0.012, 0.16), (0, -0.18 + 0.18 * i, COLLAR_H + 0.13), 0, rot=(35 if i % 2 == 0 else -35, 0, 0), bevel=False))
    r = COWL_HALF / 0.70710678
    P.append(K.lathe("Cowl", [(r, COWL_Z), (r * 0.96, COWL_Z + 0.03), (0.17, COWL_Z + COWL_H)], (0, 0, 0), 0, 4, True, False, rot=(0, 0, 45)))
    P.append(K.cyl("Vent", "z", 0.12, 0.12, 0.12, (0, 0, COWL_Z + COWL_H + 0.03), 0, 12, lod1={"segments": 6}))
    P.append(K.cyl("VentCap", "z", 0.19, 0.05, 0.07, (0, 0, COWL_Z + COWL_H + 0.155), 0, 12, lod1={"segments": 6}))
    P.append(K.cyl("VentRim", "z", 0.125, 0.125, 0.02, (0, 0, COWL_Z + COWL_H + 0.09), 1, 12, lod1={"drop": True}))
    top = COWL_Z + COWL_H + 0.19
    m = {"asset": a, "kind": "Prop", "seed": seed,
         "spec": dict(SPEC, size_m="1.1 m cowl over a 0.7 m collar (fits a 0.6 m flue), %.2f m tall" % top, tri_cap=CAPS[a], collision="UCX collar + cowl",
                      sockets=["Chimney", "Smoke"], fits="collar inner opening %.2f m; scale uniformly for other flues" % (COLLAR - 2 * WALL)),
         "materials": mats(a), "objects": [K.obj(a, P)],
         "sockets": [K.socket("Chimney", (0, 0, 0), forward=(0, 0, -1)), K.socket("Smoke", (0, 0, COWL_Z + COWL_H + 0.09), forward=(0, 0, 1))],
         "collision": [K.ucx_box(a, 0, (COLLAR, COLLAR, COLLAR_H + POST_H), (0, 0, (COLLAR_H + POST_H) / 2)),
                       K.ucx_box(a, 1, (2 * COWL_HALF, 2 * COWL_HALF, top - COWL_Z), (0, 0, (COWL_Z + top) / 2))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [filt(seed)]


def extra_checks(A):
    F = A[FILT]; d = F["predicted"]["dimensions"]; s = {x["name"]: x["location"] for x in F["sockets"]}
    inner = COLLAR - 2 * WALL
    return [("cowl 1.1 m wide, collar sleeves a 0.6 m flue", abs(d[0] - 2 * COWL_HALF) < 0.02 and inner >= FLUE, (d, inner)),
            ("SOCKET_Chimney at the collar's bottom centre", s["SOCKET_Chimney"] == [0, 0, 0]),
            ("SOCKET_Smoke above the cowl, under the vent cap", COWL_Z + COWL_H < s["SOCKET_Smoke"][2] < COWL_Z + COWL_H + 0.19),
            ("three baffles", sum(1 for q in F["objects"][0]["parts"] if q["name"].startswith("Baffle")) == 3)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
