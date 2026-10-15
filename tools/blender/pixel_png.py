# SPDX-License-Identifier: MIT
"""Tiny dependency-free PNG/GIF-free image helpers for pixel-art tools that run outside Blender (numpy only).
Arrays are float RGBA in [0, 1], row 0 = TOP (screen order, unlike Blender's bottom-up pixels)."""
import struct
import zlib

import numpy as np


def save_png(arr, path):
    a = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    h, w = a.shape[:2]
    if a.shape[2] == 3:
        a = np.concatenate([a, np.full((h, w, 1), 255, np.uint8)], axis=2)
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def upscale(arr, k):
    return np.repeat(np.repeat(arr, k, axis=0), k, axis=1)


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


def over(dst, src):
    """Alpha-composite src over dst (same shape RGBA)."""
    a = src[..., 3:4]
    out = dst.copy()
    out[..., :3] = dst[..., :3] * (1 - a) + src[..., :3] * a
    out[..., 3:4] = np.maximum(dst[..., 3:4], a)
    return out


def grid_sheet(tiles, cols, bg=(0.10, 0.10, 0.16), pad=4):
    th = max(t.shape[0] for t in tiles)
    tw = max(t.shape[1] for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    c = np.zeros((rows * (th + pad) + pad, cols * (tw + pad) + pad, 4), np.float32)
    c[..., :3] = bg
    c[..., 3] = 1
    for i, t in enumerate(tiles):
        r, q = divmod(i, cols)
        y, x = pad + r * (th + pad), pad + q * (tw + pad)
        c[y:y + t.shape[0], x:x + t.shape[1]] = over(c[y:y + t.shape[0], x:x + t.shape[1]], t)
    return c
