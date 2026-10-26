# SPDX-License-Identifier: MIT
"""G48 Bee Bloom (pythagoras 49144, pyth-g48-assets-20261019; code main c5a738b1 battlefield.BeeBloom), blender-kit/v1.
Prop_Bee_Skep        straw ark skep (coiled-straw dome, wax-sealed base band, dark entrance notch) on a wooden stand, 0.6 m.
                     SOCKET_Entrance at the hive mouth (front, -Y). UCX stand + dome.
Prop_Bee_FlowerBed   modular 2 x 1 m raised timber bed with soil, 8 planting sockets SOCKET_Plant_00..07 (4 x 2 grid on the soil).
                     One bed = one Flora (BeeBloom.sow(Flora, n)): the host drops that flora's clump glbs on the sockets.
Flora clumps (one per planting socket; keys = BeeBloom.Flora enum names):
  WILLOW_CATKIN -> Prop_Bee_Flora_WillowCatkin (new)   CROCUS -> Prop_Bee_Flora_Crocus (new)   BRAMBLE -> Prop_Bee_Flora_Bramble (new)
  CLOVER  -> REUSE Prop_Ground_PYT_Clover_V01..V10     HEATHER -> REUSE Prop_Ground_PYT_Wildflower_V01..V10 (pcg-ecology, pythagoras)
Frost-killed state: an MI swap on each clump's bloom/leaf slots (variants/flora_states.py), not a mesh, so reused meshes stay untouched.
REUSE check: catalog Prop_BBIsle_Beehive_00-12 are 0.6 m box hives with no sockets; no bee-guest or wax-den assets in catalog.bba -> skep new.
Usage: python bee_g48.py --out data/contest/bee_g48.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 4848
SKEP, BED, FL = "Prop_Bee_Skep", "Prop_Bee_FlowerBed", "Prop_Bee_Flora_"
NEW_FLORA = {"WILLOW_CATKIN": "WillowCatkin", "CROCUS": "Crocus", "BRAMBLE": "Bramble"}
REUSE_FLORA = {"CLOVER": "Prop_Ground_PYT_Clover_V%02d", "HEATHER": "Prop_Ground_PYT_Wildflower_V%02d"}
FLORA = ["WILLOW_CATKIN", "CROCUS", "CLOVER", "BRAMBLE", "HEATHER"]            # = BeeBloom.Flora (c5a738b1), checked by the test
CAPS = {SKEP: 3000, BED: 2000}; CAPS.update({FL + v: 1200 for v in NEW_FLORA.values()})
SOCKETS = {SKEP: ["SOCKET_Entrance"], BED: ["SOCKET_Plant_%02d" % i for i in range(8)]}; SOCKETS.update({FL + v: [] for v in NEW_FLORA.values()})
SPEC = {"gap": "G48", "ask": "pythagoras 49144", "lod": "LOD0/1"}
STAND_TOP = 0.24
DOME = [(0.2, 0.0), (0.206, 0.05), (0.203, 0.12), (0.186, 0.19), (0.152, 0.25), (0.105, 0.3), (0.05, 0.33), (0.012, 0.342)]
PLANT_Z = 0.2
PLANTS = [(round(-0.75 + 0.5 * i, 4), round(-0.25 + 0.5 * j, 4)) for j in range(2) for i in range(4)]


def dome_r(z):
    for (r0, z0), (r1, z1) in zip(DOME, DOME[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return DOME[-1][0]


def skep(seed=SEED):
    a = SKEP
    mats = [K.material(a, 0, "coiled straw", "C9A45C", 0.9), K.material(a, 1, "stand wood", "6B4A2E", 0.8), K.material(a, 2, "entrance dark / wax band", "2A1E14", 0.6)]
    P = K.plain_lod1(K.box("Board", (0.5, 0.5, 0.04), (0, 0, STAND_TOP - 0.02), 1))
    for i, (x, y) in enumerate(((-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2), (0.2, 0.2))):
        P += K.plain_lod1(K.box("Leg%d" % i, (0.05, 0.05, STAND_TOP - 0.04), (x, y, (STAND_TOP - 0.04) / 2), 1))
    P.append(K.lathe("Dome", DOME, (0, 0, STAND_TOP), 0, 20, cap_bottom=True, cap_top=True, lod1={"segments": 10}))
    for i, z in enumerate((0.035, 0.085, 0.135, 0.185, 0.235, 0.28)):       # straw coils: raised rings that follow the dome
        r = dome_r(z)
        P.append(K.lathe("Coil%d" % i, [(r - 0.002, z - 0.012), (r + 0.007, z), (r - 0.002, z + 0.012)], (0, 0, STAND_TOP), 0, 20,
                         cap_bottom=False, cap_top=False, lod1={"segments": 10}))
    P.append(K.lathe("WaxBand", [(0.207, 0.0), (0.209, 0.008), (0.207, 0.016)], (0, 0, STAND_TOP), 2, 20, cap_bottom=False, cap_top=False, lod1={"segments": 10}))
    P.append(K.box("Entrance", (0.07, 0.03, 0.035), (0, -0.196, STAND_TOP + 0.0175), 2, bevel=False))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="skep on stand ~0.6 m", tri_cap=3000, collision="UCX stand + dome", sockets=["Entrance"]),
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [K.socket("Entrance", (0, -0.212, STAND_TOP + 0.0175))],
         "collision": [K.ucx_box(a, 0, (0.5, 0.5, STAND_TOP), (0, 0, STAND_TOP / 2)), K.ucx_prism(a, 1, "z", 0.21, 0.342, (0, 0, STAND_TOP + 0.171), 10)], "nanite": True}
    return K.finish(m)


def bed(seed=SEED):
    a = BED
    mats = [K.material(a, 0, "bed timber", "7A5A3A", 0.85), K.material(a, 1, "soil", "3B2A1E", 0.95), K.material(a, 2, "corner posts", "5A4028", 0.85)]
    P = []
    for s, nm in ((-1, "F"), (1, "B")):
        P += K.plain_lod1(K.box("Side" + nm, (2.0, 0.06, 0.22), (0, s * 0.47, 0.11), 0))
    for s, nm in ((-1, "L"), (1, "R")):
        P += K.plain_lod1(K.box("End" + nm, (0.06, 0.88, 0.22), (s * 0.97, 0, 0.11), 0))
    P += K.plain_lod1(K.box("Soil", (1.88, 0.88, 0.17), (0, 0, 0.115), 1))
    for i, (x, y) in enumerate(((-0.96, -0.46), (0.96, -0.46), (-0.96, 0.46), (0.96, 0.46))):
        P.append(K.box("Post%d" % i, (0.08, 0.08, 0.26), (x, y, 0.13), 2))
    for i in range(6):                                          # furrow ridges in the soil
        P.append(K.box("Furrow%d" % i, (1.8, 0.03, 0.012), (0, round(-0.375 + 0.15 * i, 4), 0.2), 1, bevel=False, lod1={"drop": True}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="bed 2 x 1 m", tri_cap=2000, collision="UCX bed", sockets=["Plant_00..07"],
         planting="one Flora per bed (BeeBloom.sow); host spawns that flora's clump at each SOCKET_Plant_*, seeded pick + yaw"),
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [K.socket("Plant_%02d" % i, (x, y, PLANT_Z)) for i, (x, y) in enumerate(PLANTS)],
         "collision": [K.ucx_box(a, 0, (2.0, 1.0, 0.26), (0, 0, 0.13))], "nanite": True}
    return K.finish(m)


def _clump(key, P, mats, seed):
    a = FL + NEW_FLORA[key]
    lo, hi = K.bounds(P)                                        # seat the clump: base on z=0, centred x/y on the socket
    off = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])
    P = [dict(q, centre=[q["centre"][i] - off[i] for i in range(3)]) for q in P]
    m = {"asset": a, "kind": "Prop", "seed": seed, "flora": key, "spec": dict(SPEC, size_m="clump for one planting socket (<= 0.4 m footprint)", tri_cap=1200, collision="none (decoration)",
         states="BLOOM / FROST via MI swap (flora_states manifest)"), "materials": mats, "objects": [K.obj(a, P)], "sockets": [], "collision": [], "nanite": True}
    return K.finish(m)


def willow(seed=SEED):
    a = FL + "WillowCatkin"; r = K.rng(seed, a)
    mats = [K.material(a, 0, "willow twig", "5A3E2B", 0.8), K.material(a, 1, "catkin bloom", "D8C24A", 0.9), K.material(a, 2, "catkin fuzz", "C9C7B8", 0.95)]
    P = []
    for t in range(3):
        ang = 120 * t + r.uniform(-20, 20); tilt = r.uniform(10, 22); L = r.uniform(0.36, 0.44)
        dx, dy = math.sin(math.radians(tilt)) * math.cos(math.radians(ang)), math.sin(math.radians(tilt)) * math.sin(math.radians(ang)); dz = math.cos(math.radians(tilt))
        P.append(K.cyl("Twig%d" % t, "z", 0.007, 0.004, round(L, 4), (round(dx * L / 2, 5), round(dy * L / 2, 5), round(dz * L / 2 + 0.004, 5)), 0, 6,
                       rot=(round(-math.degrees(math.atan2(dy, dz)), 3), round(math.degrees(math.asin(dx)), 3), 0), lod1={"segments": 4}))
        for k in range(3):
            f = 0.45 + 0.22 * k; s = 1 if k % 2 else -1
            P.append(K.cyl("Catkin%d_%d" % (t, k), "z", 0.009, 0.007, 0.03, (round(dx * L * f + s * 0.012, 5), round(dy * L * f, 5), round(dz * L * f, 5)), 1 if k else 2, 6,
                           lod1={"segments": 4} if k != 1 else {"drop": True}))
    return _clump("WILLOW_CATKIN", P, mats, seed)


def crocus(seed=SEED):
    a = FL + "Crocus"; r = K.rng(seed, a)
    mats = [K.material(a, 0, "crocus leaf", "4E8A3A", 0.8), K.material(a, 1, "crocus bloom", "8E5BC2", 0.6), K.material(a, 2, "stamen", "F2B630", 0.6)]
    P = []
    for i in range(6):
        ang = 60 * i + r.uniform(-15, 15); d = r.uniform(0.04, 0.1); x, y = d * math.cos(math.radians(ang)), d * math.sin(math.radians(ang)); h = r.uniform(0.05, 0.08)
        P.append(K.cyl("Stem%d" % i, "z", 0.004, 0.004, round(h, 4), (round(x, 5), round(y, 5), round(h / 2, 5)), 0, 6, lod1={"segments": 4}))
        P.append(K.cyl("Cup%d" % i, "z", 0.006, 0.017, 0.035, (round(x, 5), round(y, 5), round(h + 0.0175, 5)), 1, 8, lod1={"segments": 5}))
        P.append(K.cyl("Stamen%d" % i, "z", 0.003, 0.003, 0.02, (round(x, 5), round(y, 5), round(h + 0.02, 5)), 2, 4, lod1={"drop": True}))
        P.append(K.box("Leaf%d" % i, (0.006, 0.004, round(h + 0.03, 4)), (round(x + 0.012, 5), round(y, 5), round((h + 0.03) / 2, 5)), 0, rot=(0, round(r.uniform(-12, 12), 2), round(ang, 2)), bevel=False, lod1={"drop": i % 2 == 1}))
    return _clump("CROCUS", P, mats, seed)


def bramble(seed=SEED):
    a = FL + "Bramble"; r = K.rng(seed, a)
    mats = [K.material(a, 0, "bramble cane", "6E2E2A", 0.8), K.material(a, 1, "bramble bloom", "F2D9E6", 0.7), K.material(a, 2, "bramble leaf", "3E6B30", 0.85)]
    P = []
    for c in range(3):                                          # arching canes: 5 box segments on an arc
        ang = 120 * c + r.uniform(-25, 25); R = r.uniform(0.15, 0.2); ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for s in range(5):
            t0, t1 = math.pi * s / 5, math.pi * (s + 1) / 5; u0, u1 = R * (1 - math.cos(t0)), R * (1 - math.cos(t1)); z0, z1 = 1.6 * R * math.sin(t0), 1.6 * R * math.sin(t1)
            L = math.hypot(u1 - u0, z1 - z0); um, zm = (u0 + u1) / 2 - R * 0.9, (z0 + z1) / 2
            pitch = math.degrees(math.atan2(z1 - z0, u1 - u0))
            P.append(K.cyl("Cane%d_%d" % (c, s), "x", 0.005, 0.005, round(L + 0.004, 4), (round(um * ca, 5), round(um * sa, 5), round(max(zm, 0.012), 5)), 0, 6,
                           rot=(0, round(-pitch, 3), round(ang, 3)), lod1={"segments": 3}))
            if s in (1, 3):
                P.append(K.box("Leaf%d_%d" % (c, s), (0.04, 0.03, 0.004), (round(um * ca, 5), round(um * sa + 0.015, 5), round(zm + 0.01, 5)), 2, rot=(15, 0, round(ang + 40, 3)), bevel=False, lod1={"drop": s == 3}))
            if s == 2:
                P.append(K.cyl("Bloom%d" % c, "z", 0.016, 0.016, 0.006, (round(um * ca, 5), round(um * sa, 5), round(zm + 0.014, 5)), 1, 8, lod1={"segments": 4}))
    m = _clump("BRAMBLE", P, mats, seed)
    return m


def assets(seed=SEED):
    return [skep(seed), bed(seed), willow(seed), crocus(seed), bramble(seed)]


def extra_checks(A):
    S, B = A[SKEP], A[BED]; cl = [A[FL + v] for v in NEW_FLORA.values()]
    ent = S["sockets"][0]["location"]
    return [("skep on stand ~0.6 m tall", 0.55 <= S["predicted"]["dimensions"][2] <= 0.65, S["predicted"]["dimensions"]),
            ("SOCKET_Entrance at the hive mouth (front of the dome base)", ent[1] < -0.19 and STAND_TOP <= ent[2] <= STAND_TOP + 0.05),
            ("bed ~2 x 1 m", S and abs(B["predicted"]["dimensions"][0] - 2.0) < 0.01 and abs(B["predicted"]["dimensions"][1] - 1.0) < 0.01, B["predicted"]["dimensions"]),
            ("8 planting sockets on the soil, inside the frame", len(B["sockets"]) == 8 and all(abs(s["location"][0]) < 0.94 and abs(s["location"][1]) < 0.44 and s["location"][2] == PLANT_Z for s in B["sockets"])),
            ("every Flora key has clumps (3 new, 2 reused pcg-ecology)", sorted(list(NEW_FLORA) + list(REUSE_FLORA)) == sorted(FLORA)),
            ("clumps fit one planting socket (<= 0.45 m footprint)", all(max(m["predicted"]["dimensions"][:2]) <= 0.45 for m in cl), [m["predicted"]["dimensions"] for m in cl])]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
