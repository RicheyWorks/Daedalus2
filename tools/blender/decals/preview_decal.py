# SPDX-License-Identifier: MIT
"""Preview sheet for a daedalus.decal/v1 decal: the three maps plus the decal composited on a procedural bark backdrop and lit
through its normal map (light from upper left), so the chop relief reads. Pure python (Pillow + numpy).
Usage: python preview_decal.py --dir <out>/<Asset> --title "..." --out sheet.png"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def bark(w, h, seed=1):
    rng = np.random.default_rng(seed); x = np.arange(w)[None, :] / w; y = np.arange(h)[:, None] / h
    fur = np.abs(np.sin((x * 9 + 0.25 * np.sin(y * 7 + rng.uniform(0, 6))) * np.pi)) ** 0.6
    base = np.array([92, 72, 54])[None, None, :] * (0.55 + 0.45 * fur[..., None]) + rng.normal(0, 6, (h, w, 1))
    hgt = fur; gy, gx = np.gradient(hgt); n = np.stack([-gx * 30, gy * 30, np.ones_like(gx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.clip(base, 0, 255), n


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
    h, w = mk.shape; BW, BH = int(w * 2.0), int(h * 1.25); bgc, bgn = bark(BW, BH)
    y0, x0 = (BH - h) // 2, (BW - w) // 2; comp = lit(bgc, bgn, np.zeros((BH, BW)), bgc, bgn)
    comp[y0:y0 + h, x0:x0 + w] = lit(bc, nm, mk, bgc[y0:y0 + h, x0:x0 + w], bgn[y0:y0 + h, x0:x0 + w])
    tiles = [("on bark, lit through the normal", Image.fromarray(comp.astype(np.uint8))), ("T_BC (sRGB)", Image.fromarray(bc.astype(np.uint8))),
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


def m_name(d):
    return next(f for f in os.listdir(d) if f.endswith(".decal.json"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--title", default=""); ap.add_argument("--out", required=True); main(ap.parse_args())
