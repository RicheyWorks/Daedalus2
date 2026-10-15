# SPDX-License-Identifier: MIT
"""Shared numpy pixel-art helpers for Blender renders (no PIL on the PC's Blender): load a render raw, pixelate a
transparent sprite (colour limit + outline), pixelate an opaque backdrop, save, and tile a contact sheet."""
import os

import bpy
import numpy as np


def load(path):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"          # the PNG's sRGB bytes as they are
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return px


def save(arr, path):
    im = bpy.data.images.new(os.path.basename(path), arr.shape[1], arr.shape[0], alpha=True)
    im.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def _limit(rgb, mask, n, lattice=7):
    lat = np.round(rgb * lattice) / lattice
    if mask.any():
        cols, counts = np.unique(lat[mask].reshape(-1, 3), axis=0, return_counts=True)
    else:
        cols, counts = np.zeros((1, 3)), np.ones(1)
    top = cols[np.argsort(-counts)[:n]]
    d = ((rgb[:, :, None, :] - top[None, None, :, :]) ** 2).sum(-1)
    return top[np.argmin(d, axis=-1)]


GAMMA = 3.5   # voxel colours are stored c**(1/2.2) for Unreal and the Standard view encodes again (net c**(1/4.84)); 3.5 undoes most of it and keeps some lift in the shading


def sprite(px, grid, colors, outline=(0.02, 0.02, 0.03), punch=1.12, gamma=GAMMA):
    """Transparent render -> grid×grid sprite: alpha-weighted block average, punch, colour limit, 1 px outline."""
    h, w = px.shape[:2]
    b = w // grid
    blk = px[:grid * b, :grid * b].reshape(grid, b, grid, b, 4)
    a = blk[..., 3]
    asum = a.sum(axis=(1, 3))
    rgb = (blk[..., :3] * a[..., None]).sum(axis=(1, 3)) / np.maximum(asum, 1e-6)[..., None]
    m = (asum / (b * b)) > .45
    rgb = np.clip(rgb, 0, 1) ** gamma if gamma else rgb
    lum = rgb.mean(-1, keepdims=True)
    rgb = np.clip(lum + (rgb - lum) * punch, 0, 1)
    q = _limit(rgb, m, colors)
    dil = m.copy()
    dil[1:] |= m[:-1]
    dil[:-1] |= m[1:]
    dil[:, 1:] |= m[:, :-1]
    dil[:, :-1] |= m[:, 1:]
    edge = dil & ~m
    out = np.zeros((grid, grid, 4), dtype=np.float32)
    out[m, :3] = q[m]
    out[m, 3] = 1
    if outline is None:
        nb = np.zeros_like(q)
        for s in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = np.where(np.roll(m, s, axis=(0, 1))[..., None] & (nb.sum(-1, keepdims=True) == 0), np.roll(q, s, axis=(0, 1)), nb)
        out[edge, :3] = nb[edge] * .35
    else:
        out[edge, :3] = outline
    out[edge, 3] = 1
    return out


def backdrop(px, gw, gh, colors, punch=1.1, gamma=GAMMA):
    """Opaque render -> gw×gh pixel backdrop with a limited palette (dithering left out: flat bands read as console art)."""
    h, w = px.shape[:2]
    bx, by = w // gw, h // gh
    blk = px[:gh * by, :gw * bx, :3].reshape(gh, by, gw, bx, 3).mean(axis=(1, 3))
    blk = np.clip(blk, 0, 1) ** gamma if gamma else blk
    lum = blk.mean(-1, keepdims=True)
    blk = np.clip(lum + (blk - lum) * punch, 0, 1)
    q = _limit(blk, np.ones(blk.shape[:2], bool), colors, lattice=9)
    out = np.ones((gh, gw, 4), dtype=np.float32)
    out[..., :3] = q
    return out


def upscale(arr, k):
    return np.repeat(np.repeat(arr, k, axis=0), k, axis=1)


def sheet(tiles, path, cell_w, cell_h=None, bg=(.10, .10, .16)):
    cell_h = cell_h or cell_w
    n = len(tiles)
    cols = max(1, int(np.ceil(np.sqrt(n * 1.6 * cell_h / cell_w))))
    rows = int(np.ceil(n / cols))
    canvas = np.zeros((rows * cell_h, cols * cell_w, 4), dtype=np.float32)
    canvas[..., :3] = bg
    canvas[..., 3] = 1
    for i, s in enumerate(tiles):
        r, c = rows - 1 - i // cols, i % cols
        hh, ww = min(s.shape[0], cell_h), min(s.shape[1], cell_w)
        y0, x0 = r * cell_h + (cell_h - hh) // 2, c * cell_w + (cell_w - ww) // 2
        a = s[:hh, :ww, 3:4]
        canvas[y0:y0 + hh, x0:x0 + ww, :3] = canvas[y0:y0 + hh, x0:x0 + ww, :3] * (1 - a) + s[:hh, :ww, :3] * a
    save(canvas, path)
