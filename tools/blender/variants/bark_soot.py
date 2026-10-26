# SPDX-License-Identifier: MIT
"""G103 bark soot material set (pythagoras 49770, pyth-g103-assets-20261019; code 9fcb07bd battlefield.SootMoths), G28 style:
an MI-ready parameter manifest for ONE master M_Bark_Soot with a Soot scalar, two instances, and a tileable soot mask.
  MI_Bark_Clean   Soot 0.0  (OAK band: Report.bark() < 0.2)
  MI_Bark_Sooted  Soot 0.8  (Settings.DEFAULT startSoot; BARE band >= 0.5)
Soot is the code's bark darkness 0..1 as-is (SootMoths years().bark / the last year's bark), so UE can drive one MID per
trunk band or animate Soot per year. Soot fills the bark furrows first: cover = smoothstep(e - 0.08, e + 0.08, SootMask), e = 1.08 - 1.32 Soot
(0 at Soot 0, ~1 at Soot 1; reference cover() below, tested). The bark base colour/normal stay the trees' own (pcg-ecology).
Also writes WHAT_THE_BIRD_SEES preview: pale + dark Mob_Moth_Peppered (top-down, real morph colours + pepper mask) on bark at
Soot 0 / 0.2 / 0.5 / 0.8 / 1.0 with the code's bands.
Usage: python bark_soot.py --out <dir> [--preview <png>]"""
import argparse, hashlib, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("decals", "kit", "creatures", "contest"):
    sys.path.insert(0, os.path.join(HERE, "..", d))
import decalkit as DK

SEED = 1032
SCHEMA = "bb-material-variants/1"
SOOT = {"MI_Bark_Clean": 0.0, "MI_Bark_Sooted": 0.8}
SOOT_COLOUR = "1B1A18"
BANDS = [(0.5, "BARE"), (0.2, "SCRUB"), (-1, "OAK")]                  # SootMoths.Report.bark(): b >= 0.5 BARE, >= 0.2 SCRUB, else OAK


def band(soot):
    return next(n for t, n in BANDS if soot >= t)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def cover(soot, mask):
    """Reference of the master's soot coverage (0..1) for a Soot scalar and SootMask value(s)."""
    c = 1.08 - 1.32 * soot
    return smoothstep(c - 0.08, c + 0.08, np.asarray(mask, float))


def soot_mask(seed=SEED, n=512):
    """Tileable greyscale: high in the vertical bark furrows (soot settles there first), noisy along the ridges."""
    rng = np.random.default_rng(seed)
    fur = DK.tnoise(rng, n, n, 3, 14, 3)                               # stretched along V (up the trunk)
    fine = DK.tnoise(rng, n, n, 24, 24, 2)
    m = 0.75 * fur + 0.25 * fine
    return (m - m.min()) / (np.ptp(m) + 1e-9)


def lin(hexv):
    c = [int(hexv[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [round(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4, 6) for v in c] + [1.0]


def build(out, seed=SEED):
    os.makedirs(out, exist_ok=True); m = soot_mask(seed); fn = "T_Bark_SootMask.png"
    Image.fromarray(np.round(m * 255).astype(np.uint8), "L").save(os.path.join(out, fn), optimize=True)
    sha = hashlib.sha256(open(os.path.join(out, fn), "rb").read()).hexdigest()
    man = {"schema": SCHEMA, "asset": "Bark (pcg-ecology tree trunks; meshes untouched)", "slot": "Bark", "status": "NOT READY",
           "gap": "G103 (pythagoras 49770, code 9fcb07bd com.daedalus.world.battlefield.SootMoths)",
           "parent_material": {"name": "M_Bark_Soot (UE side; wraps the trees' bark textures)",
                               "graph": "e = 1.08 - 1.32*Soot; cover = smoothstep(e - 0.08, e + 0.08, SootMask(uv * SootTiling)); "
                                        "BaseColor = lerp(BarkBaseColor, SootColour, cover); Roughness = lerp(BarkRoughness, SootRoughness, cover); "
                                        "Normal = lerp(BarkNormal, FlattenNormal(BarkNormal, 0.5), cover)",
                               "soot_colour": {"srgb_hex": SOOT_COLOUR, "linear_rgba": lin(SOOT_COLOUR), "roughness": 0.95}},
           "params": {"Soot": "scalar 0..1 = SootMoths bark darkness (years().bark / Report bark)", "SootColour": "vector, linear", "SootRoughness": "scalar",
                      "SootMask": "texture, greyscale, sRGB off, tileable", "SootTiling": "scalar (repeats per metre of trunk UV)"},
           "mask": {"file": fn, "sha256": sha, "format": "PNG 8-bit greyscale 512x512, tileable, white = soot settles first", "uv": "the trunk's bark UVs (tiling)"},
           "instances": {k: {"parent": "M_Bark_Soot", "params": {"Soot": v, "SootColour": {"srgb_hex": SOOT_COLOUR, "linear_rgba": lin(SOOT_COLOUR)}, "SootRoughness": 0.95,
                                                                  "SootMask": fn, "SootTiling": 1.0}, "band": band(v),
                             "coverage_at_this_soot": round(float(cover(v, m).mean()), 3)} for k, v in SOOT.items()},
           "bands": {"BARE": "Soot >= 0.5", "SCRUB": "0.2 <= Soot < 0.5", "OAK": "Soot < 0.2", "source": "SootMoths.Report.bark()"},
           "drive": "one MID per trunk band, or set Soot each simulated year from SootMoths.years() (it settles at level * (1 - filters * 0.25))"}
    with open(os.path.join(out, "Bark_Soot.material_variants.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=1); f.write("\n")
    return man, m


def _moth_topdown(px_per_cm, morph, morph_dir):
    """Top-down RGBA of the moth (wings + body) with its morph colours and pepper mask, from the recipe outlines."""
    import moth_g103 as MG
    import kitlib as K
    m = MG.moth(); man = json.load(open(os.path.join(morph_dir, MG.MOTH + ".morph_variants.json"), encoding="utf-8"))
    pm = np.asarray(Image.open(os.path.join(morph_dir, man["mask"]["file"])).convert("L"), float) / 255
    mi = man["instances"]["MI_%s_%s" % (MG.MOTH, morph)]["params"]; base = np.array([int(mi["MorphBase"]["srgb_hex"][i:i + 2], 16) for i in (0, 2, 4)], float)
    pep = np.array([int(mi["Pepper"]["srgb_hex"][i:i + 2], 16) for i in (0, 2, 4)], float)
    u, v = man["mask"]["u"], man["mask"]["v"]; W, H = int(u["size_cm"] * px_per_cm), int(v["size_cm"] * px_per_cm)
    sil = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(sil)
    def to_px(x, y):             # Blender metres -> image px (UE X right, UE Y = -y down the image)
        return ((x * 100 - u["min_cm"]) / u["size_cm"] * W, (-y * 100 - v["min_cm"]) / v["size_cm"] * H)
    for p in sorted(m["parts"], key=lambda q: q["centre"][2]):
        if p["shape"] == "slab":
            dr.polygon([to_px(p["centre"][0] + x, p["centre"][1] + y) for x, y in p["outline"]], fill=255)
        elif p["name"] in ("Thorax", "Abdomen", "Head"):
            pts = K.part_points(p); xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
            a, b = to_px(min(xs), max(ys)), to_px(max(xs), min(ys)); dr.ellipse([a, b], fill=255)
    sil = np.asarray(sil, float) / 255
    pmr = np.asarray(Image.fromarray((pm * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), float) / 255
    col = base * (1 - (pmr * mi["PepperAmount"])[..., None]) + pep * (pmr * mi["PepperAmount"])[..., None]
    return col[::-1], sil[::-1]                                        # display head-up


def preview(out_png, morph_dir, seed=SEED, levels=(0.0, 0.2, 0.5, 0.8, 1.0)):
    m = soot_mask(seed, 256); rng = np.random.default_rng(seed + 1); TW, TH = 300, 300; pxcm = 28
    bark = 0.55 + 0.45 * DK.tnoise(rng, TH, TW, 4, 18, 3)
    base = np.array([118, 112, 100])[None, None, :] * bark[..., None] + np.array([10, 14, 3]) * np.clip((DK.tnoise(rng, TH, TW, 10, 10, 2) - 0.6) / 0.1, 0, 1)[..., None]   # lichen-grey bark
    mt = np.tile(m, (2, 2))[:TH, :TW]; soot = np.array([int(SOOT_COLOUR[i:i + 2], 16) for i in (0, 2, 4)], float)
    moths = {k: _moth_topdown(pxcm, k, morph_dir) for k in ("Pale", "Dark")}
    tiles = []
    for s in levels:
        c = cover(s, mt)[..., None]; img = base * (1 - c) + soot * c
        for k, (x0, y0) in (("Pale", (24, 70)), ("Dark", (160, 170))):
            col, sil = moths[k]; h, w = sil.shape; a = sil[..., None]
            img[y0:y0 + h, x0:x0 + w] = col * a + img[y0:y0 + h, x0:x0 + w] * (1 - a)
        tiles.append((s, Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))))
    S = Image.new("RGB", (len(tiles) * (TW + 10) + 10, TH + 120), "white"); dr = ImageDraw.Draw(S)
    try:
        f = ImageFont.truetype(r"C:\\Windows\\Fonts\\arial.ttf", 15); fb = ImageFont.truetype(r"C:\\Windows\\Fonts\\arialbd.ttf", 18)
    except OSError:
        f = fb = ImageFont.load_default()
    dr.text((10, 10), "G103 WHAT THE BIRD SEES: Mob_Moth_Peppered Pale (left) + Dark (right) on M_Bark_Soot | pythagoras 49770 | NOT READY", fill="black", font=fb)
    for i, (s, im) in enumerate(tiles):
        x = 10 + i * (TW + 10); S.paste(im, (x, 40))
        tag = " = MI_Bark_Clean" if s == 0.0 else (" = MI_Bark_Sooted" if s == 0.8 else "")
        dr.text((x, 46 + TH), "Soot %.1f  band %s%s" % (s, band(s), tag), fill="black", font=f)
        dr.text((x, 66 + TH), "soot cover %.0f%%" % (100 * float(cover(s, mt).mean())), fill="black", font=f)
    dr.text((10, 92 + TH), "moths at true scale (4.5 cm span; tile = %.1f cm). Birds take dark moths with 0.2*(1-bark), pale with 0.2*bark." % (TW / pxcm), fill="black", font=f)
    S.save(out_png); print(out_png, S.size)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--preview"); ap.add_argument("--moth-dir"); o = ap.parse_args()
    man = build(o.out)[0]; print({k: (v["params"]["Soot"], v["band"], v["coverage_at_this_soot"]) for k, v in man["instances"].items()})
    if o.preview:
        preview(o.preview, o.moth_dir)
