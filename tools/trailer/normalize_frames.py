# SPDX-License-Identifier: MIT
"""Re-save Unreal's exported PNG frames as plain JPEGs ffmpeg reads cleanly.

UE's export_render_target writes PNGs whose chunks ffmpeg 7.1 sometimes rejects ("chunk too big", "Invalid PNG
signature"); Pillow reads them fine. Usage: python normalize_frames.py <frames dir> <out dir>. Skips frames done.
"""
import os
import sys

from PIL import Image


def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    names = sorted(n for n in os.listdir(src) if n.startswith("f_") and n.endswith(".png"))
    done = 0
    for n in names:
        out = os.path.join(dst, n[:-4] + ".jpg")
        if not os.path.exists(out):
            Image.open(os.path.join(src, n)).convert("RGB").save(out, quality=94)
        done += 1
    print(done)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
