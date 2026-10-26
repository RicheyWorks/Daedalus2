# SPDX-License-Identifier: MIT
"""Shared decal toolkit (reusable): seeded noise, height -> DirectX normal, texture writing and the daedalus.decal/v1 manifest
for UE deferred decals. Pure python (numpy + Pillow); generators (bark_blaze.py, lichen_rosette.py, ...) supply the fields
(colour, height, mask) and the material/projection specifics.
Texture set per decal in <out>/<Asset>/: T_<Asset>_BC.png (sRGB RGB), T_<Asset>_N.png (linear, DirectX/UE green), T_<Asset>_M.png
(linear greyscale opacity) + <Asset>.decal.json. UE decals project along local -X; texture U = +Y, V = -Z."""
import hashlib, json, os
import numpy as np
from PIL import Image

SCHEMA = "daedalus.decal/v1"
AXES = "project along local -X into the surface; texture U = +Y, V = -Z (top of texture = up)"


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


def tnoise(rng, h, w, cells_y, cells_x, octaves=3):
    """Tileable value noise in [0,1]: the random grids wrap, so the texture repeats seamlessly in both axes."""
    out = np.zeros((h, w)); amp, tot = 1.0, 0.0
    for o in range(octaves):
        cy, cx = cells_y * 2 ** o, cells_x * 2 ** o; g = rng.random((cy, cx))
        ys, xs = np.arange(h) * cy / h, np.arange(w) * cx / w
        y0, x0 = ys.astype(int), xs.astype(int); fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx); y1, x1 = (y0 + 1) % cy, (x0 + 1) % cx
        a, b, c, d = g[y0][:, x0], g[y0][:, x1], g[y1][:, x0], g[y1][:, x1]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy); tot += amp; amp *= 0.5
    return out / tot


def voronoi(rng, h, w, cell_px):
    """Jittered-grid Voronoi: (F1, F2, cell id) per pixel, distances in pixels. Checks the 3x3 neighbour cells."""
    gy, gx = int(np.ceil(h / cell_px)) + 2, int(np.ceil(w / cell_px)) + 2
    jit = rng.random((gy, gx, 2))
    v, u = np.mgrid[0:h, 0:w].astype(float); cy, cx = (v / cell_px).astype(int) + 1, (u / cell_px).astype(int) + 1
    f1 = np.full((h, w), 1e9); f2 = np.full((h, w), 1e9); cid = np.zeros((h, w), int)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ny, nx = np.clip(cy + dy, 0, gy - 1), np.clip(cx + dx, 0, gx - 1)
            py, px = (ny - 1 + jit[ny, nx, 0]) * cell_px, (nx - 1 + jit[ny, nx, 1]) * cell_px
            dd = np.hypot(v - py, u - px); closer = dd < f1
            f2 = np.where(closer, f1, np.minimum(f2, dd)); cid = np.where(closer, ny * gx + nx, cid); f1 = np.where(closer, dd, f1)
    return f1, f2, cid


def border_window(x, y, w, h, px=6):
    """1 inside, 0 within px pixels of the decal border (x, y in [-1, 1]): box edges never show."""
    return np.clip((1 - np.abs(x)) * w / (2 * px), 0, 1) * np.clip((1 - np.abs(y)) * h / (2 * px), 0, 1)


def normals(hgt, strength, w_cm, h_cm):
    """Height (cm of relief) -> tangent-space normal, DirectX/UE convention (G channel points down the texture)."""
    h, w = hgt.shape
    dy_img, dx = np.gradient(hgt * 1.0)                               # per pixel; rows go down the image
    sx, sy = w / w_cm, h / h_cm                                         # pixels per cm
    nx = -dx * sx * strength; ny_up = dy_img * sy * strength            # d/dy_up = -d/drow
    n = np.stack([nx, ny_up, np.ones_like(nx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.stack([n[..., 0], -n[..., 1], n[..., 2]], -1)            # DirectX: flip green


def write_textures(d, asset, col, n, mask):
    """Write T_<asset>_BC/N/M.png into d; return (files, sha12)."""
    os.makedirs(d, exist_ok=True)
    files = {"BC": "T_%s_BC.png" % asset, "N": "T_%s_N.png" % asset, "M": "T_%s_M.png" % asset}
    Image.fromarray(np.round(col).astype(np.uint8), "RGB").save(os.path.join(d, files["BC"]), optimize=True)
    Image.fromarray(np.round((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB").save(os.path.join(d, files["N"]), optimize=True)
    Image.fromarray(np.round(mask * 255).astype(np.uint8), "L").save(os.path.join(d, files["M"]), optimize=True)
    sha = {k: hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest()[:12] for k, f in files.items()}
    return files, sha


def manifest(asset, seed, generator, files, sha, w, h, size_cm, depth_cm, parent, roughness, placement, axes=AXES, extra_params=None,
             wiring=None, relief_cm=1.0, meta=None):
    params = {"BaseColorTex": files["BC"], "NormalTex": files["N"], "OpacityTex": files["M"], "BaseColorTint": [1.0, 1.0, 1.0],
              "NormalStrength": 1.0, "Roughness": roughness, "OpacityPower": 1.0, "OpacityContrast": 1.0}
    params.update(extra_params or {})
    man = {"schema": SCHEMA, "asset": asset, "seed": seed, "generator": generator, "status": "NOT READY",
           "textures": {
               "BaseColor": {"file": files["BC"], "size": [w, h], "srgb": True, "compression": "TC_Default", "sha12": sha["BC"]},
               "Normal": {"file": files["N"], "size": [w, h], "srgb": False, "compression": "TC_Normalmap", "green": "DirectX (UE native, no flip)", "sha12": sha["N"]},
               "Opacity": {"file": files["M"], "size": [w, h], "srgb": False, "compression": "TC_Grayscale", "sha12": sha["M"]}},
           "material": {"name": "MI_%s" % asset, "parent": parent, "domain": "DeferredDecal", "blend_mode": "Translucent",
                        "decal_response": "ColorNormalRoughness", "params": params,
                        "wiring": wiring or "BaseColor = BaseColorTex.rgb * BaseColorTint; Normal = FlattenNormal(NormalTex, 1-NormalStrength); "
                                            "Roughness = Roughness; Opacity = saturate(pow(OpacityTex.r, OpacityPower) * OpacityContrast)"},
           "projection": {"size_cm": [depth_cm, size_cm[0], size_cm[1]], "ue_DecalSize_half_extent": [depth_cm / 2, size_cm[0] / 2, size_cm[1] / 2],
                          "axes": axes, "placement": placement, "mesh": None},
           "relief_cm": relief_cm}
    if meta:
        man.update(meta)
    return man


def write_manifest(d, man):
    with open(os.path.join(d, man["asset"] + ".decal.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=1); f.write("\n")
