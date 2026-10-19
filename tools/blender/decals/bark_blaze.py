# SPDX-License-Identifier: MIT
"""Procedural bark-blaze decal (reusable): a marking-axe blaze, bark chopped off to pale sapwood, delivered as UE deferred-decal
textures + an MI-ready parameter manifest. Pure python (numpy + Pillow), seeded and deterministic; no Blender needed.
First use: Decal_Forest_Blaze, G82 Wood Wide Web (pythagoras 49500, pyth-g82-assets-20261019, Daedalus2 702d8fc9).

Outputs in <out>/<Asset>/:
  T_<Asset>_BC.png  base colour, sRGB RGB (sapwood with grain, oxidised edge, torn cambium rim)
  T_<Asset>_N.png   tangent-space normal, linear, DirectX/UE green (G = down), from the chop height field
  T_<Asset>_M.png   opacity mask, linear greyscale (1 = blaze, soft 0..1 rim)
  <Asset>.decal.json  daedalus.decal/v1 manifest: texture import settings, material params, projection size
Projection: UE decals project along local -X; texture U runs along +Y and V down from +Z, so mount the decal with +X out of the
bark and +Z up the trunk. A placeholder projection mesh is not shipped: UDecalComponent needs none (702d8fc9 has no decal-mesh code).
Usage: python bark_blaze.py --out <dir> [--asset Decal_Forest_Blaze] [--seed 8283] [--w 512 --h 1024] [--size-cm 20 40 --depth-cm 8]"""
import argparse, hashlib, json, os
import numpy as np
from PIL import Image

SCHEMA = "daedalus.decal/v1"
SAP, SAP_OX, CAMBIUM, GRAIN = np.array([226, 205, 160]), np.array([176, 136, 88]), np.array([118, 70, 40]), np.array([196, 168, 120])


def vnoise(rng, h, w, cells_y, cells_x, octaves=3):
    """Smooth value noise in [0,1] (bilinear upsampled random grids, summed octaves)."""
    out = np.zeros((h, w)); amp, tot = 1.0, 0.0
    for o in range(octaves):
        cy, cx = cells_y * 2 ** o + 1, cells_x * 2 ** o + 1; g = rng.random((cy + 1, cx + 1))
        ys, xs = np.linspace(0, cy, h, endpoint=False), np.linspace(0, cx, w, endpoint=False)
        y0, x0 = ys.astype(int), xs.astype(int); fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        a, b, c, d = g[y0][:, x0], g[y0][:, x0 + 1], g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy); tot += amp; amp *= 0.5
    return out / tot


def fields(seed, w, h):
    """Return (mask 0..1, height 0..1, colour float RGB) for one blaze."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:h, 0:w]; x = (u + 0.5) / w * 2 - 1; y = 1 - (v + 0.5) / h * 2          # x,y in [-1,1], y up
    ang = np.arctan2(y, x * 0.5)
    edge_n = vnoise(rng, h, w, 6, 3)
    # blaze outline: tall superellipse (pointed a little at the top where the first stroke bit in), ragged by noise
    rad = (np.abs(x / 0.78) ** 2.4 + np.abs((y - 0.02) / (0.82 + 0.06 * np.clip(y, 0, 1))) ** 2.2) ** (1 / 2.3)
    rad = rad + 0.07 * (edge_n - 0.5) * 2 + 0.03 * np.sin(ang * 7 + rng.uniform(0, 6.28))
    inner = np.clip((1.0 - rad) / 0.035, 0, 1)                       # sapwood (soft 0..1 over ~2% of the decal)
    rim = np.clip((1.09 - rad) / 0.04, 0, 1)                          # torn cambium/bark lip beyond the cut
    win = np.clip((1 - np.abs(x)) * w / 12, 0, 1) * np.clip((1 - np.abs(y)) * h / 12, 0, 1)   # 6 px clear border: box edges never show
    mask = np.clip(rim, 0, 1) * win
    # height: cut face recessed; three diagonal axe strokes leave planar facets with ridges between; raised bark lip
    strokes = sorted(rng.uniform(-0.55, 0.55, 3)); slope = rng.uniform(0.35, 0.6)
    t = y + slope * x; facet = np.zeros_like(x)
    bounds = [-9] + [(a + b) / 2 for a, b in zip(strokes, strokes[1:])] + [9]
    for i, s in enumerate(strokes):
        band = (t >= bounds[i]) & (t < bounds[i + 1]); facet = np.where(band, 0.7 * (t - bounds[i]) / max(1e-3, bounds[i + 1] - bounds[i]), facet)
    grain = vnoise(rng, h, w, 40, 6, 2)
    hgt = 0.3 + 0.5 * facet + 0.05 * grain
    lip = np.exp(-((rad - 1.03) / 0.03) ** 2)
    hgt = hgt * inner + (1 - inner) * (0.85 + 0.12 * vnoise(rng, h, w, 10, 5, 2)) + 0.12 * lip * (1 - inner)
    # colour: sapwood with vertical grain + growth-ring streaks, oxidised toward the edge, cambium rim outside the cut
    streak = 0.5 + 0.5 * np.sin(x * 38 + 6 * vnoise(rng, h, w, 12, 3, 2))
    edge_ox = np.clip((rad - 0.55) / 0.45, 0, 1) ** 1.5
    col = SAP[None, None, :] * (1 - 0.18 * streak[..., None]) + GRAIN * 0.18 * streak[..., None]
    col = col * (1 - 0.6 * edge_ox[..., None]) + SAP_OX * 0.6 * edge_ox[..., None]
    col = col * (1 - 0.25 * np.abs(facet - 0.35)[..., None] * 0.6) - 18 * (np.abs(np.gradient(facet, axis=0)) > 0.002)[..., None]  # stroke ridges darker
    col = col * inner[..., None] + CAMBIUM * (1 - inner[..., None]) * (0.85 + 0.3 * vnoise(rng, h, w, 20, 8, 2))[..., None]
    return mask, hgt, np.clip(col, 0, 255)


def normals(hgt, strength, w_cm, h_cm):
    """Height (0..1 of 1 cm relief) -> tangent-space normal, DirectX/UE convention (G channel points down the texture)."""
    h, w = hgt.shape
    dy_img, dx = np.gradient(hgt * 1.0)                               # per pixel; rows go down the image
    sx, sy = w / w_cm, h / h_cm                                         # pixels per cm
    nx = -dx * sx * strength; ny_up = dy_img * sy * strength            # d/dy_up = -d/drow
    n = np.stack([nx, ny_up, np.ones_like(nx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.stack([n[..., 0], -n[..., 1], n[..., 2]], -1)            # DirectX: flip green


def build(out, asset="Decal_Forest_Blaze", seed=8283, w=512, h=1024, size_cm=(20.0, 40.0), depth_cm=8.0, strength=1.0, meta=None):
    d = os.path.join(out, asset); os.makedirs(d, exist_ok=True)
    mask, hgt, col = fields(seed, w, h); n = normals(hgt, strength, *size_cm)
    files = {"BC": "T_%s_BC.png" % asset, "N": "T_%s_N.png" % asset, "M": "T_%s_M.png" % asset}
    Image.fromarray(np.round(col).astype(np.uint8), "RGB").save(os.path.join(d, files["BC"]), optimize=True)
    Image.fromarray(np.round((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB").save(os.path.join(d, files["N"]), optimize=True)
    Image.fromarray(np.round(mask * 255).astype(np.uint8), "L").save(os.path.join(d, files["M"]), optimize=True)
    sha = {k: hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest()[:12] for k, f in files.items()}
    man = {"schema": SCHEMA, "asset": asset, "seed": seed, "generator": "tools/blender/decals/bark_blaze.py", "status": "NOT READY",
           "textures": {
               "BaseColor": {"file": files["BC"], "size": [w, h], "srgb": True, "compression": "TC_Default", "sha12": sha["BC"]},
               "Normal": {"file": files["N"], "size": [w, h], "srgb": False, "compression": "TC_Normalmap", "green": "DirectX (UE native, no flip)", "sha12": sha["N"]},
               "Opacity": {"file": files["M"], "size": [w, h], "srgb": False, "compression": "TC_Grayscale", "sha12": sha["M"]}},
           "material": {"name": "MI_%s" % asset, "parent": "M_Decal_BarkBlaze (Deferred Decal master)", "domain": "DeferredDecal", "blend_mode": "Translucent",
                        "decal_response": "ColorNormalRoughness",
                        "params": {"BaseColorTex": files["BC"], "NormalTex": files["N"], "OpacityTex": files["M"], "BaseColorTint": [1.0, 1.0, 1.0],
                                   "NormalStrength": 1.0, "Roughness": 0.78, "OpacityPower": 1.0, "OpacityContrast": 1.0, "AgeDarken": 0.0},
                        "wiring": "BaseColor = BaseColorTex.rgb * BaseColorTint * lerp(1, 0.6, AgeDarken); Normal = FlattenNormal(NormalTex, 1-NormalStrength); "
                                  "Roughness = Roughness; Opacity = saturate(pow(OpacityTex.r, OpacityPower) * OpacityContrast)"},
           "projection": {"size_cm": [depth_cm, size_cm[0], size_cm[1]], "ue_DecalSize_half_extent": [depth_cm / 2, size_cm[0] / 2, size_cm[1] / 2],
                          "axes": "project along local -X into the bark; texture U = +Y, V = -Z (top of texture = up the trunk)",
                          "placement": "breast height ~1.3 m on the trunk, X = trunk surface normal, roll jitter +-8 deg, FadeScreenSize 0.002, SortOrder 0",
                          "mesh": None},
           "relief_cm": 1.0}
    if meta: man.update(meta)
    with open(os.path.join(d, asset + ".decal.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=1); f.write("\n")
    return man, mask, hgt, col, n


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--asset", default="Decal_Forest_Blaze"); ap.add_argument("--seed", type=int, default=8283)
    ap.add_argument("--w", type=int, default=512); ap.add_argument("--h", type=int, default=1024); ap.add_argument("--size-cm", type=float, nargs=2, default=(20.0, 40.0))
    ap.add_argument("--depth-cm", type=float, default=8.0); o = ap.parse_args()
    m = build(o.out, o.asset, o.seed, o.w, o.h, tuple(o.size_cm), o.depth_cm)[0]
    print(o.asset, {k: v["sha12"] for k, v in m["textures"].items()})
