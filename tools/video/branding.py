"""Channel art: 800x800 profile logo and a 2560x1440 banner (reaction-diffusion texture, safe-area text), plus a
safe-area check image. Deterministic (seeded).  usage: python branding.py [--out DIR] [--name richeyworks] [--steps 2500]"""
import argparse
import os
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand  # noqa: E402


def reaction_diffusion(h, w, steps, F=.037, k=.06, seed=7):
    r = np.random.default_rng(seed)
    U, V = np.ones((h, w)), np.zeros((h, w))
    for _ in range(60):
        y, x = r.integers(0, h - 6), r.integers(0, w - 6)
        V[y:y + 6, x:x + 6] = .5; U[y:y + 6, x:x + 6] = .25
    L = lambda Z: np.roll(Z, 1, 0) + np.roll(Z, -1, 0) + np.roll(Z, 1, 1) + np.roll(Z, -1, 1) - 4 * Z  # noqa: E731
    for _ in range(steps):
        uvv = U * V * V
        U += .16 * L(U) - uvv + F * (1 - U)
        V += .08 * L(V) + uvv - (F + k) * V
    return V / max(V.max(), 1e-9)


def profile(out, size=800):
    lg = Image.new("RGBA", (size, size), brand.BG + (255,))
    s = brand.stamp(int(size * .875))
    if s is not None:
        lg.alpha_composite(s, ((size - s.width) // 2, (size - s.height) // 2))
    p = os.path.join(out, "profile_logo_%d.png" % size); lg.convert("RGB").save(p); return p


def banner(out, name="richeyworks", tagline=None, subline="reaction / diffusion / song · daedalus · biomorph", steps=2500):
    tagline = tagline or brand.TAGLINES[0]
    v = reaction_diffusion(180, 320, steps)
    a = np.array(Image.fromarray((np.clip(v * 1.8, 0, 1) * 255).astype(np.uint8)).resize((2560, 1440), Image.BICUBIC), float) / 255
    yy, xx = np.mgrid[0:1440, 0:2560]
    fade = np.clip(np.hypot((xx - 1280) / 1100, (yy - 720) / 420) - .6, 0, 1)
    c = np.array(brand.BG) + (np.array([46, 46, 46]) * (a * np.clip(fade * 1.5, 0, 1))[..., None])
    bn = Image.fromarray(c.astype(np.uint8)).convert("RGBA")
    x0, y0 = 507, 508  # YouTube safe area 1546x423
    s = brand.stamp(400)
    if s is not None:
        bn.alpha_composite(s, (x0 + 40, y0 + 12))
    g = ImageDraw.Draw(bn)
    g.line((x0 + 490, y0 + 70, x0 + 490, y0 + 353), fill=brand.LINE, width=3)
    g.text((x0 + 540, y0 + 120), name, font=brand.font(120, True), fill=brand.FG, anchor="lm")
    g.text((x0 + 546, y0 + 235), tagline, font=brand.font(50), fill=brand.FG, anchor="lm")
    g.text((x0 + 546, y0 + 310), subline, font=brand.font(32), fill=brand.DIM, anchor="lm")
    p = os.path.join(out, "banner_2560x1440.png"); bn.convert("RGB").save(p)
    ck = bn.copy(); ImageDraw.Draw(ck).rectangle((x0, y0, x0 + 1546, y0 + 423), outline=(255, 0, 0), width=4)
    q = os.path.join(out, "banner_safearea_check.png"); ck.convert("RGB").resize((1280, 720)).save(q)
    return p, q


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--out", default="branding_out"); a.add_argument("--name", default="richeyworks")
    a.add_argument("--steps", type=int, default=2500)
    o = a.parse_args(argv)
    os.makedirs(o.out, exist_ok=True)
    print("branding ok:", profile(o.out), *banner(o.out, o.name, steps=o.steps))


if __name__ == "__main__":
    main()
