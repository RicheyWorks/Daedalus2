# SPDX-License-Identifier: MIT
"""Headless contest export (Richey 09:36 "be smart when sharing ... keep building"): runs voxel_island.build_many in a
background Blender, so Team Claude's batches never need the shared Blender GUI lock.

    "C:\\Program Files\\Blender Foundation\\Blender 4.3\\blender.exe" -b --factory-startup --python-exit-code 1 --python tools/blender/export_islands.py -- 250 300 [out_dir]
"""
import importlib.util
import os
import sys
import time

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
start, stop = int(argv[0]), int(argv[1])
force = "force" in argv
argv = [a for a in argv if a != "force"]
out = argv[2] if len(argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "engines", "unreal", "art", "claude-islands")
spec = importlib.util.spec_from_file_location("voxel_island", os.path.join(os.path.dirname(os.path.abspath(__file__)), "voxel_island.py"))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
t = time.time()
done = V.build_many(range(start, stop), out, force=force)
built = sum(1 for v in done.values() if v != "exists")
print("EXPORTED %d (skipped %d) in %.1fs -> %s" % (built, len(done) - built, time.time() - t, out), flush=True)
