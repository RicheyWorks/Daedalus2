# SPDX-License-Identifier: MIT
"""G82 Wood Wide Web hand prop (pythagoras 49500, pyth-g82-assets-20261019; code main 702d8fc9 docs/mechanics/WEB01-wood-wide-web.md), blender-kit/v1.
Prop_Forest_SporePouch  ~0.15 m drawstring leather pouch Forester Hesper Ngaio carries (6 spore doses): bulb body, cinched neck with a
                        cord wrap, flared ruffle open at the top showing ochre spore dust, two knotted cord ends, a pressed mushroom
                        emblem on the front (-Y). SOCKET_Grip at the cinch (held-prop attach, +X up the pouch); UCX prism.
Companion: Decal_Forest_Blaze (tools/blender/decals/bark_blaze.py). Trees reuse pcg-ecology; root threads are UE decal/VFX (not built).
REUSE check: only seed/groat sacks exist (ash_g20 boxes, ytm_g66 0.3 m sacks): none is a 0.15 m hand pouch, so new.
Usage: python forest_g82.py --out data/contest/forest_g82.kit.json"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 8282
POUCH = "Prop_Forest_SporePouch"
CAPS = {POUCH: 1200}
SOCKETS = {POUCH: ["SOCKET_Grip"]}
SPEC = {"gap": "G82", "ask": "pythagoras 49500", "lod": "LOD0/1"}
CINCH_Z, TOP_Z, R = 0.114, 0.148, 0.056


def pouch(seed=SEED):
    a = POUCH; r = K.rng(seed, a)
    mats = [K.material(a, 0, "oiled leather", "7A5A3A", 0.75), K.material(a, 1, "hemp cord", "B79F74", 0.95), K.material(a, 2, "spore dust / emblem", "C99A3C", 0.9)]
    w = [1 + 0.03 * r.uniform(-1, 1) for _ in range(3)]          # slight hand-sewn wobble, seeded
    P = [K.lathe("Body", [(0.006, 0.0), (0.036 * w[0], 0.006), (0.052, 0.03), (R * w[1], 0.056), (0.05 * w[2], 0.082), (0.032, 0.1), (0.018, CINCH_Z)],
                 (0, 0, 0), 0, 14, True, False, lod1={"segments": 7}),
         K.lathe("Ruffle", [(0.018, CINCH_Z), (0.021, 0.122), (0.031, 0.137), (0.036, TOP_Z)], (0, 0, 0), 0, 14, False, False, lod1={"segments": 7}),
         K.cyl("SporeDust", "z", 0.02, 0.014, 0.012, (0, 0, 0.126), 2, 10, lod1={"segments": 5}),
         K.cyl("CordWrap", "z", 0.0215, 0.0215, 0.009, (0, 0, CINCH_Z), 1, 12, lod1={"segments": 6})]
    for i, s in enumerate((1, -1)):
        P.append(K.cyl("CordEnd%d" % i, "z", 0.0022, 0.0022, 0.045, (s * 0.034, -0.03, CINCH_Z - 0.021), 1, 5, rot=(-30, -s * 32, 0), lod1={"segments": 4}))   # hangs from the wrap, top tilted in
        P.append(K.box("Knot%d" % i, (0.008, 0.008, 0.009), (s * 0.045, -0.04, CINCH_Z - 0.04), 1, lod1={"drop": True}))
    P.append(K.lathe("EmblemCap", [(0.017, 0.0), (0.014, 0.003), (0.006, 0.005), (0.001, 0.0055)], (0, -0.0545, 0.06), 2, 10, True, True, rot=(90, 0, 0), lod1={"segments": 5}))
    P.append(K.cyl("EmblemStem", "z", 0.004, 0.005, 0.016, (0, -0.0555, 0.047), 2, 6, lod1={"drop": True}))
    m = {"asset": a, "kind": "Prop", "seed": seed,
         "spec": dict(SPEC, size_m="~0.15 m pouch (0.148 tall)", tri_cap=CAPS[a], collision="UCX prism", sockets=["Grip"], held="attach socket +X up the pouch, at the cinched neck"),
         "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Grip", (0, 0, CINCH_Z), forward=(0, 0, 1), attach=((0, 0, 1), (0, 1, 0)))],
         "collision": [K.ucx_prism(a, 0, "z", R, TOP_Z, (0, 0, TOP_Z / 2))], "nanite": False}
    return K.finish(m)


def assets(seed=SEED):
    return [pouch(seed)]


def extra_checks(A):
    p = A[POUCH]; d = p["predicted"]["dimensions"]; s = {x["name"]: x for x in p["sockets"]}
    return [("pouch ~0.15 m (0.13-0.17 tall)", 0.13 <= d[2] <= 0.17, d),
            ("hand-sized footprint (< 0.13 m)", max(d[0], d[1]) < 0.13, d),
            ("SOCKET_Grip at the cinch, held-prop attach", s["SOCKET_Grip"]["location"] == [0, 0, CINCH_Z] and "attach" in s["SOCKET_Grip"]),
            ("emblem on the front (-Y) surface", all(q["centre"][1] < -0.05 for q in p["objects"][0]["parts"] if q["name"].startswith("Emblem")))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
