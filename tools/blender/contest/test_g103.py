# SPDX-License-Identifier: MIT
"""Checks for G103: moth_g103.py (Mob_Moth_Peppered recipe + morph manifest) and variants/bark_soot.py. python test_g103.py [--staged <dir>]"""
import argparse, json, os, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", "..")
for d in ("", "../kit", "../creatures", "../decals", "../variants"):
    sys.path.insert(0, os.path.join(HERE, d))
import moth_g103 as MG, bark_soot as BS

ap = argparse.ArgumentParser(); ap.add_argument("--staged"); o = ap.parse_args()
checks = []
def add(n, r, d=""): checks.append((n, bool(r), d))
m = MG.moth(); pin = json.load(open(os.path.join(ROOT, "data", "contest", "g103_moth.quad.json"), encoding="utf-8"))
add("moth == its pin", json.loads(json.dumps(m)) == pin)
add("moth 4.5 cm wingspan", abs(m["predicted"]["dimensions"][0] - 0.045) < 1e-4, m["predicted"]["dimensions"])
add("moth clips Idle (rest on bark) + Flutter", sorted(m["clips"]) == ["Flutter", "Idle"])
add("slot 0 Morph carries wings + body, slot 1 the rest", {p["slot"] for p in m["parts"] if p["shape"] == "slab" or p["name"] in ("Thorax", "Abdomen", "Head")} == {0} and
    all(p["slot"] == 1 for p in m["parts"] if p["name"].startswith(("Eye", "Leg", "Antenna"))))
t = tempfile.mkdtemp(); man, mask = MG.morph_manifest(m, t)
add("two MIs, Pale + Dark, one master", sorted(man["instances"]) == ["MI_Mob_Moth_Peppered_Dark", "MI_Mob_Moth_Peppered_Pale"] and {v["parent"] for v in man["instances"].values()} == {"M_MothPeppered"})
pale, dark = (man["instances"]["MI_Mob_Moth_Peppered_%s" % k]["params"] for k in ("Pale", "Dark"))
lum = lambda h: sum(int(h[i:i + 2], 16) * w for i, w in ((0, 0.299), (2, 0.587), (4, 0.114)))
add("Pale is light, Dark is dark (luma > 180 vs < 60)", lum(pale["MorphBase"]["srgb_hex"]) > 180 and lum(dark["MorphBase"]["srgb_hex"]) < 60)
add("Pale shows the pepper fully, Dark faintly", pale["PepperAmount"] == 1.0 and dark["PepperAmount"] < 0.5)
add("pepper mask covers 10-45% (speckles + cross-lines)", 0.1 <= mask.mean() <= 0.45, mask.mean())
add("mask projection spans the moth bounds", abs(man["mask"]["u"]["size_cm"] - 4.5) < 0.01 and man["mask"]["u"]["min_cm"] == -2.25)
add("mask file hash recorded", len(man["mask"]["sha256"]) == 64)
# bark soot
add("bands match SootMoths.Report.bark()", [BS.band(x) for x in (0.0, 0.19, 0.2, 0.49, 0.5, 1.0)] == ["OAK", "OAK", "SCRUB", "SCRUB", "BARE", "BARE"])
sm = BS.soot_mask()
covs = [float(BS.cover(s, sm).mean()) for s in np.linspace(0, 1, 11)]
add("cover 0 at Soot 0, ~1 at Soot 1, monotonic", covs[0] == 0.0 and covs[-1] > 0.99 and all(b >= a for a, b in zip(covs, covs[1:])), [round(c, 3) for c in covs])
add("soot fills the furrows first (high mask covered before low)", BS.cover(0.3, 0.9) > BS.cover(0.3, 0.3))
edge = np.abs(sm[0] - sm[-1]).mean(); inner = np.abs(np.diff(sm, axis=0)).mean()
add("soot mask tiles (wrap seam no worse than a normal row step)", edge < 3 * inner, (edge, inner))
bm = BS.build(tempfile.mkdtemp())[0]
add("MI_Bark_Clean Soot 0 (OAK), MI_Bark_Sooted Soot 0.8 = DEFAULT startSoot (BARE)", (bm["instances"]["MI_Bark_Clean"]["params"]["Soot"], bm["instances"]["MI_Bark_Clean"]["band"],
    bm["instances"]["MI_Bark_Sooted"]["params"]["Soot"], bm["instances"]["MI_Bark_Sooted"]["band"]) == (0.0, "OAK", 0.8, "BARE"))
add("one master for both", {v["parent"] for v in bm["instances"].values()} == {"M_Bark_Soot"})
if o.staged:
    import hashlib
    s1 = json.load(open(os.path.join(o.staged, "Mob_Moth_Peppered", "Mob_Moth_Peppered.morph_variants.json"))); s2 = json.load(open(os.path.join(o.staged, "Bark_Soot", "Bark_Soot.material_variants.json")))
    ok = hashlib.sha256(open(os.path.join(o.staged, "Mob_Moth_Peppered", s1["mask"]["file"]), "rb").read()).hexdigest() == s1["mask"]["sha256"] and \
         hashlib.sha256(open(os.path.join(o.staged, "Bark_Soot", s2["mask"]["file"]), "rb").read()).hexdigest() == s2["mask"]["sha256"]
    add("staged masks match their manifests", ok)
ok = 0
for n, r, dd in checks:
    ok += r
    if not r: print("FAIL", n, dd)
print("%d/%d" % (ok, len(checks))); sys.exit(0 if ok == len(checks) else 1)
