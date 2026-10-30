# SPDX-License-Identifier: MIT
"""Preview sheet for a daedalus.decal/v1 decal: the three maps plus the decal composited on a procedural bark backdrop and lit
through its normal map (light from upper left), so the chop relief reads. Pure python (Pillow + numpy).
Usage: python preview_decal.py --dir <out>/<Asset> --title "..." --out sheet.png [--backdrop bark|rock] [--scale 2]
       python preview_decal.py --set <out>/<Asset>.decals.json --title "..." --out sheet.png   (sizes side by side at true scale, on rock)"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def bark(w, h, seed=1):
    rng = np.random.default_rng(seed); x = np.arange(w)[None, :] / w; y = np.arange(h)[:, None] / h
    fur = np.abs(np.sin((x * 9 + 0.25 * np.sin(y * 7 + rng.uniform(0, 6))) * np.pi)) ** 0.6
    base = np.array([92, 72, 54])[None, None, :] * (0.55 + 0.45 * fur[..., None]) + rng.normal(0, 6, (h, w, 1))
    hgt = fur; gy, gx = np.gradient(hgt); n = np.stack([-gx * 30, gy * 30, np.ones_like(gx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.clip(base, 0, 255), n


def rock(w, h, seed=2):
    rng = np.random.default_rng(seed); g = np.zeros((h, w))
    for k in (4, 8, 16, 32, 64):
        n = rng.random((k + 1, k + 1)); g += np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), float) / 255 / k ** 0.6
    g = (g - g.min()) / (np.ptp(g) + 1e-9)
    base = np.array([128, 124, 116])[None, None, :] * (0.7 + 0.45 * g[..., None]) + rng.normal(0, 5, (h, w, 1))
    gy, gx = np.gradient(g); n = np.stack([-gx * 12, gy * 12, np.ones_like(gx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.clip(base, 0, 255), n


BACKDROPS = {"bark": bark, "rock": rock}


def lit(col, n_dx, mask, bg_col, bg_n):
    L = np.array([-0.5, 0.5, 0.7]); L /= np.linalg.norm(L)                 # upper left, y up
    n = np.stack([n_dx[..., 0], -n_dx[..., 1], n_dx[..., 2]], -1)          # DirectX -> y up
    a = mask[..., None]; c = col * a + bg_col * (1 - a); nn = n * a + bg_n * (1 - a); nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
    return np.clip(c * (0.35 + 0.75 * np.clip((nn * L).sum(-1), 0, 1))[..., None], 0, 255)


def main(o):
    m = json.load(open(os.path.join(o.dir, m_name(o.dir)), encoding="utf-8")); T = m["textures"]
    bc = np.asarray(Image.open(os.path.join(o.dir, T["BaseColor"]["file"])).convert("RGB"), float)
    nm = np.asarray(Image.open(os.path.join(o.dir, T["Normal"]["file"])).convert("RGB"), float) / 255 * 2 - 1
    mk = np.asarray(Image.open(os.path.join(o.dir, T["Opacity"]["file"])).convert("L"), float) / 255
    h, w = mk.shape; BW, BH = int(w * o.scale), int(h * (1.25 if o.scale >= 2 else o.scale)); bgc, bgn = BACKDROPS[o.backdrop](BW, BH)
    y0, x0 = (BH - h) // 2, (BW - w) // 2; comp = lit(bgc, bgn, np.zeros((BH, BW)), bgc, bgn)
    comp[y0:y0 + h, x0:x0 + w] = lit(bc, nm, mk, bgc[y0:y0 + h, x0:x0 + w], bgn[y0:y0 + h, x0:x0 + w])
    tiles = [("on %s, lit through the normal" % o.backdrop, Image.fromarray(comp.astype(np.uint8))), ("T_BC (sRGB)", Image.fromarray(bc.astype(np.uint8))),
             ("T_N (DirectX green)", Image.open(os.path.join(o.dir, T["Normal"]["file"])).convert("RGB")), ("T_M opacity", Image.fromarray((mk * 255).astype(np.uint8)).convert("RGB"))]
    TH = 520; ims = [(lab, im.resize((int(im.width * TH / im.height), TH), Image.LANCZOS)) for lab, im in tiles]
    W = sum(im.width for _, im in ims) + 10 * (len(ims) + 1); S = Image.new("RGB", (W, TH + 110), "white"); dr = ImageDraw.Draw(S)
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 15); fb = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 19)
    except OSError:
        f = fb = ImageFont.load_default()
    dr.text((10, 10), o.title, fill="black", font=fb); x = 10
    for lab, im in ims:
        S.paste(im, (x, 44)); dr.text((x, 50 + TH), lab, fill="black", font=f); x += im.width + 10
    p = m["projection"]; dr.text((10, 76 + TH), "%s | %dx%d px | projection %s cm (DecalSize %s) | %s, %s" % (m["asset"], w, h, p["size_cm"], p["ue_DecalSize_half_extent"], m["material"]["domain"], m["material"]["blend_mode"]), fill="black", font=f)
    S.save(o.out); print(o.out, S.size)


def set_sheet(o):
    """All sizes of a decal set on one rock backdrop at true relative scale, plus each size's maps."""
    idx = json.load(open(o.set, encoding="utf-8")); root = os.path.dirname(os.path.abspath(o.set)); S = idx["sizes"]
    pxmm = max(s["texture_px"] / (s["decal_cm"] * 10) for s in S.values())
    W, H = int(sum(s["decal_cm"] * 10 for s in S.values()) * pxmm * 1.35), int(max(s["decal_cm"] for s in S.values()) * 10 * pxmm * 1.4)
    bgc, bgn = rock(W, H); comp = lit(bgc, bgn, np.zeros((H, W)), bgc, bgn); x = int(W * 0.06)
    labels = []
    for k, s in S.items():
        d = os.path.join(root, s["asset"]); T = json.load(open(os.path.join(d, s["asset"] + ".decal.json"), encoding="utf-8"))["textures"]
        bc = np.asarray(Image.open(os.path.join(d, T["BaseColor"]["file"])).convert("RGB"), float)
        nm = np.asarray(Image.open(os.path.join(d, T["Normal"]["file"])).convert("RGB"), float) / 255 * 2 - 1
        mk = np.asarray(Image.open(os.path.join(d, T["Opacity"]["file"])).convert("L"), float) / 255
        h, w = mk.shape; y = (H - h) // 2
        comp[y:y + h, x:x + w] = lit(bc, nm, mk, bgc[y:y + h, x:x + w], bgn[y:y + h, x:x + w]); labels.append((x, y + h + 6, "%s  %g mm  ~%g yr growth" % (k, s["diameter_mm"], s["growth_years"])))
        x += w + int(W * 0.06)
    im = Image.fromarray(comp.astype(np.uint8)); TW = 1500; sc = TW / W; im = im.resize((TW, int(H * sc)), Image.LANCZOS)
    S2 = Image.new("RGB", (TW + 20, im.height + 120), "white"); dr = ImageDraw.Draw(S2)
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 16); fb = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 19)
    except OSError:
        f = fb = ImageFont.load_default()
    dr.text((10, 10), o.title, fill="black", font=fb); S2.paste(im, (10, 44))
    for lx, ly, t in labels:
        dr.text((10 + lx * sc, 44 + min(ly * sc, im.height - 22)), t, fill="white", font=f)
    c = idx["clock"]; dr.text((10, 54 + im.height), "true relative scale on rock | keyed to %s: lag %g yr, %g mm/yr for %g yr, then %g mm/yr; max %g mm" % (
        c["source"], c["lag"], c["fastRate"], c["fastYears"], c["slowRate"], idx["max_diameter_mm"]), fill="black", font=f)
    dr.text((10, 78 + im.height), idx["scale_rule"], fill="black", font=f)
    S2.save(o.out); print(o.out, S2.size)


def m_name(d):
    return next(f for f in os.listdir(d) if f.endswith(".decal.json"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dir"); ap.add_argument("--set"); ap.add_argument("--title", default=""); ap.add_argument("--out", required=True); ap.add_argument("--backdrop", default="bark", choices=sorted(BACKDROPS))
    ap.add_argument("--scale", type=float, default=2.0, help="backdrop width / decal width"); o = ap.parse_args(); set_sheet(o) if o.set else main(o)
