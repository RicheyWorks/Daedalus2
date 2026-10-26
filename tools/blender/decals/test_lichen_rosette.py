# SPDX-License-Identifier: MIT
"""Checks for decalkit.py + lichen_rosette.py (Decal_Rock_Lichen S/M/L, G91). python test_lichen_rosette.py [--dir <built staging dir>]"""
import argparse, copy, hashlib, json, os, sys, tempfile
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import decalkit as DK, lichen_rosette as L, bark_blaze as BB

ap = argparse.ArgumentParser(); ap.add_argument("--dir"); o = ap.parse_args()
checks = []
def add(n, r, d=""): checks.append((n, bool(r), d))
# growth curve parity with LichenClock.java DEFAULT (0.6 mm/yr x 50 yr, then 0.3; lag 8)
add("curve parity: 25/50/150/212 yr -> 15/30/60/78.6 mm", [round(L.curve(y), 6) for y in (25, 50, 150, 212)] == [15.0, 30.0, 60.0, 78.6])
add("curve(0) = 0 and age(0) = lag", L.curve(0) == 0 and L.age(0) == 8.0)
add("age inverts curve (+lag)", all(abs(L.age(L.curve(y)) - (y + 8)) < 1e-9 for y in (5, 25, 50, 51, 150, 212)))
t = tempfile.mkdtemp(); idx, mans = L.build(t)
add("three sizes S < M < L", list(idx["sizes"]) == ["S", "M", "L"] and idx["sizes"]["S"]["diameter_mm"] < idx["sizes"]["M"]["diameter_mm"] < idx["sizes"]["L"]["diameter_mm"])
add("sizes keyed to the clock (S young, M end of great growth, L old)", [idx["sizes"][k]["growth_years"] for k in "SML"] == [25.0, 50.0, 150.0])
add("all sizes inside the code's range (<= max 78.6 mm)", all(s["diameter_mm"] <= idx["max_diameter_mm"] for s in idx["sizes"].values()) and idx["max_diameter_mm"] == 78.6)
add("textures power of two", all((s["texture_px"] & (s["texture_px"] - 1)) == 0 for s in idx["sizes"].values()), [s["texture_px"] for s in idx["sizes"].values()])
add("constant texel density (6.4 px/mm)", len({round(s["texture_px"] / (s["decal_cm"] * 10), 6) for s in idx["sizes"].values()}) == 1)
idx2 = L.build(tempfile.mkdtemp())[0]
add("deterministic", all(json.load(open(os.path.join(t, s["manifest"])))["textures"] == json.load(open(os.path.join(os.path.dirname(os.path.join(t, s["manifest"])), os.path.basename(s["manifest"]))))["textures"] for s in idx["sizes"].values()) and
    all(mans[k]["textures"][x]["sha12"] == L.build(tempfile.mkdtemp())[1][k]["textures"][x]["sha12"] for k in "S" for x in ("BaseColor", "Normal", "Opacity")))
for k, s in idx["sizes"].items():
    d = os.path.join(t, s["asset"]); m = mans[k]; T = m["textures"]
    ims = {x: Image.open(os.path.join(d, T[x]["file"])) for x in T}
    mk = np.asarray(ims["Opacity"], float) / 255; bc = np.asarray(ims["BaseColor"], float); nv = np.asarray(ims["Normal"], float) / 255 * 2 - 1
    add("%s modes RGB/RGB/L, square" % k, ims["BaseColor"].mode == "RGB" and ims["Normal"].mode == "RGB" and ims["Opacity"].mode == "L" and all(im.size == (s["texture_px"],) * 2 for im in ims.values()))
    add("%s mask clear at the border" % k, max(mk[0].max(), mk[-1].max(), mk[:, 0].max(), mk[:, -1].max()) == 0)
    cov = (mk > 0.5).mean(); want = np.pi / 4 * L.FILL ** 2
    add("%s rosette fills ~FILL^2 pi/4 of the decal (+-30%%)" % k, abs(cov - want) / want < 0.3, (cov, want))
    inside = bc[mk > 0.95]; lum = inside @ [0.299, 0.587, 0.114]
    chart = inside[(inside[:, 1] > inside[:, 2] + 60) & (inside[:, 1] > 120)]
    add("%s chartreuse areoles (yellow-green) cover 35-85%% of the thallus (centres darker)" % k, 0.35 <= len(chart) / len(inside) <= 0.85, len(chart) / len(inside))
    add("%s black prothallus cracks/rim present (>8%% dark)" % k, (lum < 50).mean() > 0.08, (lum < 50).mean())
    add("%s normals unit, facing out, with relief" % k, np.abs(np.linalg.norm(nv, axis=-1) - 1).max() < 0.04 and nv[..., 2].min() > 0 and nv[..., :2][mk > 0.9].std() > 0.03, nv[..., :2][mk > 0.9].std())
    add("%s manifest: DeferredDecal, square projection = decal_cm, lichen keys" % k, m["material"]["domain"] == "DeferredDecal" and m["projection"]["size_cm"][1:] == [s["decal_cm"]] * 2 and
        m["lichen"]["diameter_mm"] == s["diameter_mm"] and m["lichen"]["fall_age_years_zero_delay"] == round(L.age(s["diameter_mm"]), 2))
# areoles are a constant physical size, so bigger thalli carry more of them (the "map" grows, not the cells)
add("areole size constant across sizes", L.AREOLE_MM == 0.9)
# refactor guard: the blaze manifest is unchanged by the decalkit split (compare with the pinned copy, textures' sha12 aside)
pin = json.load(open(os.path.join(HERE, "..", "..", "..", "data", "decals", "Decal_Forest_Blaze.decal.json"), encoding="utf-8"))
nb = BB.build(tempfile.mkdtemp())[0]
def strip(mm):
    mm = copy.deepcopy(mm)
    for v in mm["textures"].values(): v.pop("sha12")
    return mm
add("decalkit refactor: Decal_Forest_Blaze manifest == pin (sha aside)", strip(nb) == strip(pin))
add("decalkit voronoi F1 <= F2", (lambda r: (r[0] <= r[1] + 1e-9).all())(DK.voronoi(np.random.default_rng(1), 32, 32, 6)))
if o.dir:
    bi = json.load(open(os.path.join(o.dir, "Decal_Rock_Lichen.decals.json"), encoding="utf-8"))
    ok = True
    for s in bi["sizes"].values():
        mb = json.load(open(os.path.join(o.dir, s["manifest"]), encoding="utf-8")); dd = os.path.dirname(os.path.join(o.dir, s["manifest"]))
        ok &= all(hashlib.sha256(open(os.path.join(dd, v["file"]), "rb").read()).hexdigest()[:12] == v["sha12"] for v in mb["textures"].values())
        ok &= all(mb["textures"][x]["sha12"] == mans[[k for k in mans if mans[k]["asset"] == s["asset"]][0]]["textures"][x]["sha12"] for x in mb["textures"])
    add("built dir hashes match manifests and a fresh build", ok)
ok = 0
for nme, r, dd in checks:
    ok += r
    if not r: print("FAIL", nme, dd)
print("%d/%d" % (ok, len(checks))); sys.exit(0 if ok == len(checks) else 1)
