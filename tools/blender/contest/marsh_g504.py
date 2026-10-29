# SPDX-License-Identifier: MIT
"""G504 Reed Ceiling / G507 Reed Release marsh pieces (pythagoras, via buffffff 57306 buf-blender-next-20261029-1310).
  Mob_Marsh_Hawk            ~0.55 m harrier-style marsh hawk on creatures/bird_rig.py (blender-bird/v1). Clips Idle / Squawk / Walk / Fly. Raptor parts (2026-10-29 fix): hooked beak, talons, fingered primaries, 3 tail bands.
                            Sockets: SOCKET_Talon (Leg_L, foot), SOCKET_Head (Head; look-at / camera).
  Mob_Sky_Crane             adult: REUSE G142 (crane_g142.py, data/contest/g142_crane.quad.json), not rebuilt; staged copy only.
  Mob_Sky_Crane_Juvenile    ~0.85 m colt on the same long-bird params scaled down (cinnamon/brown juvenile plumage, shorter beak and legs).
                            Clips Idle / Walk / Fly; SOCKET_LegBand on Leg_L at the same 30 % height as the adult (G163 Prop_Leg_Band fits both).
  Prop_Marsh_ReedbedPatch_Sparse / _Medium / _Dense   2 x 2 m reedbed patches (blender-kit/v1), 24 / 56 / 110 stems, G66 green/straw,
                            SOCKET_Hide_0..3 (bird hide spots), SOCKET_Nest, SOCKET_Edge_N/E/S/W (tile chain). No collision (walk-through; UE overlap volume).
Usage: python marsh_g504.py --out-dir data/contest   (writes g504_marsh_hawk.quad.json, g504_crane_juvenile.quad.json, marsh_g504.kit.json)"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, os.path.join(HERE, "..", "creatures")); sys.path.insert(0, HERE)
import kitlib as K
import bird_rig as R
import crane_g142 as CR

SEED = 50429
ASK = "buffffff 57306 (pythagoras G504/G507)"
LEAF, STRAW, HEAD, MUD = "5E9A48", "C8B070", "6A4A2A", "4A4030"


def hawk(seed=SEED):
    a = "Mob_Marsh_Hawk"
    body = {"length": 0.55, "height_frac": 0.72, "leg_frac": 0.24, "neck_r": 0.9, "head_scale": 0.95, "wing_lift_deg": 34.0, "tail_off": 0.16, "squawk_deg": 30.0,
            "beak_style": "hook", "feet": "talons", "wing_tips": "fingered", "tail_bands": 3}
    mats = [K.material(a, 0, "russet-brown plumage", "8A5A38", 0.85), K.material(a, 1, "hooked beak / talons (dark horn)", "2A2420", 0.5),
            K.material(a, 2, "barred grey-buff wings", "A89A86", 0.85), K.material(a, 3, "dark wingtips / eyes", "1E1A18", 0.7)]
    P = R.params(seed, a, body); g = R._g(P)
    socks = [("Talon", "Leg_L", (g["hip"][0], g["hip"][1] - 0.02 * P["L"], 0.02 * P["L"])), ("Head", "Head", (0, g["head"][0], g["head"][1]))]
    spec = {"gap": "G504/G507", "asker": ASK, "size_m": "~0.55 m long, ~0.4 m tall", "tri_cap": 6000, "lod": "LOD0/1", "collision": "capsule in UE",
            "rig": "blender-bird/v1 (bird_rig.py), rigid; clips Idle, Squawk, Walk, Fly", "sockets": "SOCKET_Talon (Leg_L), SOCKET_Head (Head)", "status": "NOT READY"}
    return R.recipe(a, seed, materials=mats, spec=spec, body=body, clip_names=("Idle", "Squawk", "Walk", "Fly"), sockets=socks)


def juvenile(seed=SEED + 1):
    a = "Mob_Sky_Crane_Juvenile"
    body = dict(CR.BODY, length=0.72, leg_frac=0.46, head_scale=0.78)
    mats = [K.material(a, 0, "cinnamon-brown juvenile plumage", "B08A62", 0.9), K.material(a, 1, "beak / legs (dull slate)", "4A4A4A", 0.6),
            K.material(a, 2, "mottled grey-brown coverts", "9A8C7A", 0.9), K.material(a, 3, "dark wingtips / eyes", "2A2420", 0.7)]
    P = R.params(seed, a, body)
    spec = {"gap": "G504/G507", "asker": ASK, "size_m": "~0.85 m tall (adult Mob_Sky_Crane ~1.2 m)", "tri_cap": 6000, "lod": "LOD0/1", "collision": "capsule in UE",
            "rig": "blender-bird/v1 (bird_rig.py), rigid; clips Idle, Walk, Fly", "sockets": "SOCKET_LegBand on Leg_L (G163 Prop_Leg_Band)", "adult": "Mob_Sky_Crane (G142, reused)", "status": "NOT READY"}
    return R.recipe(a, seed, materials=mats, spec=spec, body=body, clip_names=("Idle", "Walk", "Fly"), sockets=[("LegBand", "Leg_L", CR.band_location(P))])


def reedbed(kind, n, seed=SEED):
    a = "Prop_Marsh_ReedbedPatch_" + kind; r = K.rng(seed, a); P = [K.box("Mud", (2.0, 2.0, 0.02), (0, 0, 0.01), 3, bevel=False)]
    for i in range(n):
        x, y = r.uniform(-0.95, 0.95), r.uniform(-0.95, 0.95); h = r.uniform(1.2, 2.1); lean = (r.uniform(-8, 8), r.uniform(-8, 8), 0)
        P.append(K.cyl("Stem%d" % i, "z", 0.009, 0.004, h, (x, y, h / 2), 0 if i % 3 else 1, 4, rot=lean))
        if i % 4 == 0: P.append(K.cyl("Head%d" % i, "z", 0.018, 0.016, 0.16, (x + math.sin(math.radians(lean[1])) * h, y - math.sin(math.radians(lean[0])) * h, h - 0.1), 2, 6))
        if i % 3 == 0: P.append(K.slab("Leaf%d" % i, [(-0.012, 0), (0.012, 0), (0.0, 0.6)], 0.003, (x, y, 0.02), 0, rot=(90 - r.uniform(10, 35), 0, r.uniform(0, 360))))
    S = [K.socket("Hide_%d" % k, (0.5 * (1 if k % 2 else -1), 0.5 * (1 if k > 1 else -1), 0)) for k in range(4)] + [K.socket("Nest", (0, 0, 0.02))]
    S += [K.socket("Edge_%s" % d, p) for d, p in (("N", (0, 1, 0)), ("E", (1, 0, 0)), ("S", (0, -1, 0)), ("W", (-1, 0, 0)))]
    spec = {"gap": "G504/G507", "ask": ASK, "size_m": "2 x 2 m, reeds 1.2-2.1 m", "tri_cap": 8000, "lod": "LOD0/1", "density": kind, "stems": n,
            "sockets": [s["name"] for s in S], "collision": "none (walk-through; use a UE overlap volume for hiding)", "style": "G66 island palette", "status": "NOT READY"}
    mats = [K.material(a, 0, "reed stems (G66 green)", LEAF), K.material(a, 1, "dry reed (straw)", STRAW), K.material(a, 2, "bulrush heads", HEAD), K.material(a, 3, "wet mud", MUD, 0.4)]
    return K.finish({"asset": a, "kind": "Prop", "seed": seed, "spec": spec, "materials": mats, "objects": [K.obj(a, P)], "sockets": S, "collision": [], "nanite": True})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out-dir", required=True); o = ap.parse_args()
    for fn, m in (("g504_marsh_hawk.quad.json", hawk()), ("g504_crane_juvenile.quad.json", juvenile())):
        with open(os.path.join(o.out_dir, fn), "w", encoding="utf-8", newline="\n") as f: json.dump(m, f, indent=1); f.write("\n")
        print(fn, m["predicted"]["triangles"], m["predicted"]["dimensions"], [s["name"] for s in m["sockets"]])
    A = [reedbed(k, n) for k, n in (("Sparse", 24), ("Medium", 56), ("Dense", 110))]; K.write(A, os.path.join(o.out_dir, "marsh_g504.kit.json"))
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
