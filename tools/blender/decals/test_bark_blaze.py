# SPDX-License-Identifier: MIT
"""Checks for tools/blender/decals/bark_blaze.py (Decal_Forest_Blaze, G82). python test_bark_blaze.py [--dir <built Asset dir>]"""
import argparse, hashlib, json, os, sys, tempfile
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bark_blaze as B

ap = argparse.ArgumentParser(); ap.add_argument("--dir"); o = ap.parse_args()
checks = []
def add(n, r, d=""): checks.append((n, bool(r), d))
t = tempfile.mkdtemp(); m, mask, hgt, col, n = B.build(t, seed=8283)
d = os.path.join(t, "Decal_Forest_Blaze"); T = m["textures"]
m2 = B.build(tempfile.mkdtemp(), seed=8283)[0]
add("deterministic (same seed -> same texture hashes)", all(T[k]["sha12"] == m2["textures"][k]["sha12"] for k in T))
add("different seed -> different blaze", B.build(tempfile.mkdtemp(), seed=8284)[0]["textures"]["Opacity"]["sha12"] != T["Opacity"]["sha12"])
add("three textures + manifest written", all(os.path.isfile(os.path.join(d, T[k]["file"])) for k in T) and os.path.isfile(os.path.join(d, "Decal_Forest_Blaze.decal.json")))
ims = {k: Image.open(os.path.join(d, T[k]["file"])) for k in T}
add("sizes 512x1024, power of two", all(im.size == (512, 1024) for im in ims.values()))
add("modes: BC RGB, N RGB, M greyscale", ims["BaseColor"].mode == "RGB" and ims["Normal"].mode == "RGB" and ims["Opacity"].mode == "L")
add("import flags: BC sRGB, N/M linear, N normalmap compression", T["BaseColor"]["srgb"] and not T["Normal"]["srgb"] and not T["Opacity"]["srgb"] and T["Normal"]["compression"] == "TC_Normalmap")
mk = np.asarray(ims["Opacity"], float) / 255
cov = (mk > 0.5).mean()
add("blaze covers 40-75% of the decal", 0.4 <= cov <= 0.75, cov)
add("mask clear at the border (decal box edges invisible)", max(mk[0].max(), mk[-1].max(), mk[:, 0].max(), mk[:, -1].max()) == 0)
add("soft rim (partial-alpha pixels present)", ((mk > 0.05) & (mk < 0.95)).mean() > 0.005)
nv = np.asarray(ims["Normal"], float) / 255 * 2 - 1; ln = np.linalg.norm(nv, axis=-1)
add("normals unit length (+-4%)", np.abs(ln - 1).max() < 0.04, np.abs(ln - 1).max())
add("normals face out (B >= 0.5 everywhere)", nv[..., 2].min() > 0)
add("normal has real relief inside the cut", nv[..., :2][mk > 0.9].std() > 0.03, nv[..., :2][mk > 0.9].std())
# DirectX green: a bump that rises toward the top of the image must have G < 0.5 (normal tilts down the texture = +G in DX means down)
ramp = np.tile(np.linspace(1, 0, 64)[:, None], (1, 64)); nd = B.normals(ramp, 1, 10, 10)
add("DirectX green convention (height rising up the texture tilts the normal down -> G > 0.5)", nd[32, 32, 1] > 0 and abs(nd[32, 32, 0]) < 1e-9)
bc = np.asarray(ims["BaseColor"], float); inside = bc[mk > 0.95].mean(0)
add("sapwood inside is pale (luma > 150)", inside @ [0.299, 0.587, 0.114] > 150, inside)
add("material: DeferredDecal, translucent, params wired to the files", m["material"]["domain"] == "DeferredDecal" and m["material"]["blend_mode"] == "Translucent" and
    {m["material"]["params"][k] for k in ("BaseColorTex", "NormalTex", "OpacityTex")} == {T[k]["file"] for k in T})
add("projection: DecalSize = half of size_cm, no mesh", m["projection"]["ue_DecalSize_half_extent"] == [v / 2 for v in m["projection"]["size_cm"]] and m["projection"]["mesh"] is None)
add("aspect of texture matches projection face", abs(512 / 1024 - m["projection"]["size_cm"][1] / m["projection"]["size_cm"][2]) < 1e-9)
add("manifest status NOT READY", m["status"] == "NOT READY")
if o.dir:
    mb = json.load(open(os.path.join(o.dir, "Decal_Forest_Blaze.decal.json"), encoding="utf-8"))
    add("built dir hashes match manifest", all(hashlib.sha256(open(os.path.join(o.dir, v["file"]), "rb").read()).hexdigest()[:12] == v["sha12"] for v in mb["textures"].values()))
    add("built dir == fresh build (seeded)", all(mb["textures"][k]["sha12"] == T[k]["sha12"] for k in T))
ok = 0
for nme, r, dd in checks:
    ok += r
    if not r: print("FAIL", nme, dd)
print("%d/%d" % (ok, len(checks))); sys.exit(0 if ok == len(checks) else 1)
