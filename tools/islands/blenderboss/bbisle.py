# SPDX-License-Identifier: MIT
"""Blender Boss Island only (contest): unique models Prop_BBIsle_<Family>_<nn>, structure seeded per item. 500 target, batches of 120.
Not shared with the team queue pool (autowave uses bbkit with other names/palettes). python: GROUPS for headless.py; --batch via env BBISLE_BATCH (0-based)."""
import os
from assets.bbkit import FAM, build
PAL = [("E8772E", "2A3B4C", "4FE3D0"), ("F2C230", "3A2A1A", "FF6A3D"), ("2F9E8F", "E4DDCF", "FFB84D"), ("8C5A2A", "C8A070", "4FE3D0"), ("5C389E", "F4F6FB", "FF8A3D")]
def items(lo, hi):
    out = []; fams = sorted(FAM)
    for i in range(lo, hi):
        f = fams[i % len(fams)]; n = i // len(fams); p = PAL[(i * 7 + n) % len(PAL)]
        out.append({"asset": "Prop_BBIsle_%s_%02d" % (f, n), "materials": list(p), "glow": [2], "parts": [{"name": "", "boxes": build(f, "bbisle-%s-%d" % (f, n))}]})
    return out
B = int(os.environ.get("BBISLE_BATCH", "0"))
GROUPS = {"bbisle": items(B * 120, min(500, B * 120 + 120))}
SPECS = GROUPS["bbisle"]; ORDER = ["bbisle"]; SIZE = {"bbisle": "0.5-5 m"}
