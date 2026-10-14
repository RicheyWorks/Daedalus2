# SPDX-License-Identifier: MIT
"""Headless batch of four-island themed clusters: seeds x themes.
    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_clusters.py -- 100 110 OUT_DIR [theme,theme]
"""
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
start, stop, out_dir = int(argv[0]), int(argv[1]), argv[2]
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import island_cluster as X  # noqa: E402

themes = argv[3].split(",") if len(argv) > 3 else list(X.THEME_NAMES)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
t0 = time.time()
n = 0
for seed in range(start, stop):
    theme = themes[seed % len(themes)]
    out = os.path.join(out_dir, "Cluster_%s_%d.fbx" % (theme, seed))
    if os.path.exists(out):
        continue
    t = time.time()
    X.build(seed, out, theme=theme, keep=False)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    n += 1
    print("CLUSTER %d %s %.0fs" % (seed, theme, time.time() - t), flush=True)
print("EXPORTED %d clusters in %.0fs -> %s" % (n, time.time() - t0, out_dir), flush=True)
