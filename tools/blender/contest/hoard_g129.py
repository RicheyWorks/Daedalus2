# SPDX-License-Identifier: MIT
"""G129 Squirrel's Winter hoard (pythagoras 50065, pyth-g129-assets-20261019; code 6df61143 PatchForager, FORAGE01 "Prop_Hoard_Cache
(a log hollow whose fill level follows the share)"). blender-kit/v1. 6df61143 has no morph/material param reader for the hoard, so the fill
is three mesh variants (no Fill morph): the same hollow log with an empty floor, a half heap and a full heap (hazelnuts + bramble berries).
  Prop_Hoard_Cache_Empty / _Half / _Full   0.6 m hollow log lying along Y, open mouth at the front (-Y), closed heart end at the back.
                             The shell is 12 bark staves around the hollow (LOD1: 10 wider staves), a cut-heartwood rim at the mouth,
                             a branch stub on top. The heap is a child object (<asset>_Fill, nut + berry slots) on Half / Full only.
                             SOCKET_Mouth (opening: where Pip drops a load), SOCKET_Perch (log top: Pip sits here between patches),
                             SOCKET_Fill (top of the heap, on the hollow floor when empty). Same socket names on all three, so a swap
                             keeps attachments. UCX: one 8-sided prism along the log. Sidecar <asset>.sockets.json from build_kit, plus
                             Prop_Hoard_Cache.fill_variants.json (--fill): which variant to show for a share / outcome.
Bramble patches reuse the BEE01 bramble clumps (no new asset).
Usage: python hoard_g129.py --out data/contest/hoard_g129.kit.json [--fill <dir>]"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K

SEED = 12929
BASE = "Prop_Hoard_Cache"
LEVELS = (("Empty", 0.0), ("Half", 0.5), ("Full", 1.0))
NAMES = [BASE + "_" + n for n, _ in LEVELS]
CAPS = {n: 2500 for n in NAMES}
LEN, R, WALL = 0.6, 0.17, 0.035          # log length, outer radius, wall
RIN = R - WALL
ZC = R - 0.008                           # log axis height: the bottom stave sinks 8 mm into the leaf litter (ground() re-zeroes)
STAVES, STAVES_L1 = 12, 10
SPEC = {"gap": "G129", "ask": "pythagoras 50065", "lod": "LOD0/1", "code": "6df61143 PatchForager (FORAGE01): hoard fill follows the share"}
BARK, HEART, NUT, BERRY = "5B4330", "B08A5E", "8C5A2B", "4A1830"


def staves(n, lod1):
    out = []; rm = R - WALL / 2; w = 2 * math.pi * rm / n * 1.08
    for i in range(n):
        th = 360.0 * (i + 0.5) / n; t = math.radians(th)
        out.append(K.box("Stave%s%02d" % ("L1_" if lod1 else "", i), (w, LEN, WALL), (rm * math.sin(t), 0, ZC + rm * math.cos(t)), 0, rot=(0, th, 0), bevel=False,
                         lod1={"only": True} if lod1 else {"drop": True}))
    return out


def log_parts():
    P = staves(STAVES, False) + staves(STAVES_L1, True)
    for i in range(STAVES):                  # cut heartwood rim at the mouth: a ring of end-grain blocks just proud of the staves
        th = 360.0 * (i + 0.5) / STAVES; t = math.radians(th); rm = R - WALL / 2
        P.append(K.box("Rim%02d" % i, (2 * math.pi * rm / STAVES * 1.08, 0.012, WALL + 0.004), (rm * math.sin(t), -LEN / 2 - 0.004, ZC + rm * math.cos(t)), 1,
                       rot=(0, th, 0), bevel=False, lod1={"drop": True}))
    P.append(K.cyl("HeartEnd", "y", RIN + 0.004, RIN + 0.004, 0.03, (0, LEN / 2 - 0.03, ZC), 1, 10, lod1={"segments": 8}))
    P.append(K.cyl("Stub", "z", 0.035, 0.025, 0.12, (0.05, 0.12, ZC + R + 0.04), 0, 6, rot=(0, 25, 0), lod1={"segments": 4}))
    return P


def nut(name, c, r, slot, drop):
    prof = [(0.0, -r), (r * 0.8, -r * 0.55), (r, 0.0), (r * 0.7, r * 0.6), (0.0, r * 1.15)]
    return K.lathe(name, prof, c, slot, 6, False, False, lod1={"drop": True} if drop else {"segments": 4})


def heap(level, seed):
    """Half: one mound just inside the mouth, about half the hollow's height. Full: two mounds filling the hollow to near the roof, a few nuts spilling at the mouth."""
    if level == 0.0:
        return []
    r = K.rng(seed, BASE + ":heap:%s" % level); floor = ZC - RIN; P = []
    mounds = [(-0.06, 0.125, 0.115)] if level == 0.5 else [(0.1, 0.13, 0.2), (-0.13, 0.13, 0.17)]
    for k, (y, rad, h) in enumerate(mounds):
        P.append(K.lathe("Mound%d" % k, [(rad, 0.0), (rad * 0.85, h * 0.45), (rad * 0.45, h * 0.85), (0.0, h)], (0, y, floor + 0.004), 2, 8, False, False, lod1={"segments": 5}))
    n = 8 if level == 0.5 else 16
    for i in range(n):                       # nuts and berries scattered over the mound surfaces
        y0, rad, h = mounds[i % len(mounds)]; a = r.uniform(0, 2 * math.pi); f = r.uniform(0.15, 0.75)
        x = f * rad * math.cos(a) * 0.8; yy = y0 + f * rad * math.sin(a) * 0.8; z = floor + 0.004 + h * (1 - f ** 1.6) + 0.006
        berry = i % 3 == 2
        P.append(nut("%s%02d" % ("Berry" if berry else "Nut", i), (round(x, 5), round(yy, 5), round(z, 5)), 0.009 if berry else 0.012, 3 if berry else 2, i % 2 == 1))
    if level == 1.0:                         # the spill: three nuts on the litter at the mouth
        for i, (x, y) in enumerate(((-0.06, -LEN / 2 - 0.03), (0.02, -LEN / 2 - 0.05), (0.07, -LEN / 2 - 0.02))):
            P.append(nut("Spill%d" % i, (x, y, 0.012), 0.012, 2, i == 1))
    return P


def fill_top(level, seed):
    H = heap(level, seed)
    if not H:
        return ZC - RIN
    return max(p["centre"][2] + p["profile"][-1][1] for p in H if p["name"].startswith("Mound"))


def ground(m):
    dz = -m["predicted"]["bounds_min"][2]
    if abs(dz) < 1e-9:
        return m
    for o in m["objects"]:
        for q in o["parts"]:
            q["centre"] = [q["centre"][0], q["centre"][1], round(q["centre"][2] + dz, 6)]
    for s_ in m["sockets"]:
        s_["location"] = [s_["location"][0], s_["location"][1], round(s_["location"][2] + dz, 6)]
        s_["location_gltf"] = [s_["location"][0], s_["location"][2], round(-s_["location"][1], 5) + 0.0]
    for c in m["collision"]:
        c["centre"] = [c["centre"][0], c["centre"][1], round(c["centre"][2] + dz, 6)]
    m.pop("predicted", None)
    return K.finish(m)


def cache(name, level, seed=SEED):
    H = heap(level, seed); ft = fill_top(level, seed)
    objs = [K.obj(name, log_parts())]
    if H:
        objs.append(K.obj(name + "_Fill", H, parent=name, role="hoard fill"))
    socks = [K.socket("Mouth", (0, -LEN / 2, ZC), forward=(0, -1, 0)), K.socket("Perch", (0, -0.08, ZC + R), forward=(0, -1, 0)),
             K.socket("Fill", (0, -0.06 if level == 0.5 else (0.1 if level == 0.0 else 0.0), round(ft, 5)), forward=(0, -1, 0))]
    m = {"asset": name, "kind": "Prop", "seed": seed,
         "spec": dict(SPEC, size_m="0.6 m hollow log, 0.34 m across", tri_cap=CAPS[name], collision="UCX 8-sided prism along the log",
                      fill={"level": level, "variant": name.split("_")[-1], "variants": NAMES, "sidecar": "Prop_Hoard_Cache.fill_variants.json"},
                      sockets=["Mouth", "Perch", "Fill"]),
         "materials": [K.material(name, 0, "log bark", BARK, 0.95), K.material(name, 1, "cut heartwood", HEART, 0.85)]
                      + ([K.material(name, 2, "hazelnut shell", NUT, 0.6), K.material(name, 3, "bramble berry", BERRY, 0.35)] if H else []),
         "objects": objs, "sockets": socks,
         "collision": [K.ucx_prism(name, 0, "y", R, LEN, (0, 0, ZC))], "nanite": True}
    return ground(K.finish(m))


def assets(seed=SEED):
    return [cache(n, lv, seed) for n, lv in zip(NAMES, (l for _, l in LEVELS))]


SOCKETS = {n: ["SOCKET_Mouth", "SOCKET_Perch", "SOCKET_Fill"] for n in NAMES}


def fill_manifest():
    return {"schema": "bb-fill-variants/1", "gap": "G129 (pythagoras 50065, 6df61143 PatchForager / FORAGE01)", "status": "NOT READY", "base": BASE,
            "why_meshes": "6df61143 reads no morph target or material param for the hoard, so the fill is three mesh variants with identical sockets",
            "variants": {n: lv for n, lv in zip(NAMES, (l for _, l in LEVELS))},
            "live": "during the day show the variant nearest share_so_far = hoard / Report.best: Empty < 0.25 <= Half < 0.75 <= Full",
            "outcome": {"HOARDED (share >= 0.97)": NAMES[2], "SHORT (0.70 <= share < 0.97)": NAMES[1], "STARVED (share < 0.70)": NAMES[0]},
            "sockets": "SOCKET_Mouth (drop-off), SOCKET_Perch (Pip sits up here), SOCKET_Fill (heap top; spawn a nut here per load)",
            "swap": "same pivot, collision and socket names on all three: swap the static mesh, keep attachments"}


def extra_checks(A):
    a = [A[n] for n in NAMES]; S = [{s["name"]: s["location"] for s in m["sockets"]} for m in a]
    logs = [[q for q in m["objects"][0]["parts"]] for m in a]
    d = a[0]["predicted"]["dimensions"]
    return [("hoard: three fill variants share one log", logs[0] == logs[1] == logs[2]),
            ("hoard: ~0.6 m log (0.55-0.7 m along Y)", 0.55 <= d[1] <= 0.7, d),
            ("hoard: Empty has no heap, Half/Full have a fill child", len(a[0]["objects"]) == 1 and all(len(m["objects"]) == 2 and m["objects"][1]["parent"] == m["asset"] for m in a[1:])),
            ("hoard: heap rises Empty < Half < Full, under the roof", S[0]["SOCKET_Fill"][2] < S[1]["SOCKET_Fill"][2] < S[2]["SOCKET_Fill"][2] < S[2]["SOCKET_Perch"][2] - WALL),
            ("hoard: tris rise with the fill", a[0]["predicted"]["triangles"] < a[1]["predicted"]["triangles"] < a[2]["predicted"]["triangles"]),
            ("hoard: identical mouth/perch sockets and UCX on all three", all(S[i]["SOCKET_Mouth"] == S[0]["SOCKET_Mouth"] and S[i]["SOCKET_Perch"] == S[0]["SOCKET_Perch"] and [dict(c, name=None) for c in a[i]["collision"]] == [dict(c, name=None) for c in a[0]["collision"]] for i in range(3))),
            ("hoard: mouth at the open front end", abs(S[0]["SOCKET_Mouth"][1] + LEN / 2) < 1e-9),
            ("hoard: fill sidecar maps the FORAGE01 outcomes", set(fill_manifest()["outcome"].values()) == set(NAMES))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); ap.add_argument("--fill"); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
    if o.fill:
        os.makedirs(o.fill, exist_ok=True)
        with open(os.path.join(o.fill, BASE + ".fill_variants.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(fill_manifest(), f, indent=1); f.write("\n")
