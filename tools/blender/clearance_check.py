# SPDX-License-Identifier: MIT
"""Minimum mesh-to-mesh clearance between two sets of exported GLBs, measured on the delivered files.

    python clearance_check.py --a WALK.glb [...] --b WHEEL_ROTOR.glb WHEEL_FRAME.glb [...] --min 3.0

It imports the files into an empty scene, applies their transforms, and finds the minimum 3-D distance from any
vertex of set A to any vertex of set B (a KD-tree over B). UCX_ collision objects are skipped. The last line is
"CLEARANCE <m> PASS|FAIL (min <required>)"; the exit code is 0 on PASS.

This is a vertex-to-vertex distance. Faces between vertices could come slightly closer, so treat it as an upper
bound on the true surface gap. Run it on the delivered GLBs, not on the build scene, so it checks what was
actually shipped.
"""
import sys

import bpy
from mathutils import kdtree


def load(paths):
    before = set(bpy.data.objects)
    for p in paths:
        bpy.ops.import_scene.gltf(filepath=p)
    bpy.context.view_layer.update()
    return [o for o in bpy.data.objects if o not in before and o.type == "MESH" and not o.name.startswith("UCX_")]


def main(argv):
    def group(flag):
        out, on = [], False
        for a in argv:
            if a.startswith("--"):
                on = a == flag
                continue
            if on:
                out.append(a)
        return out
    need = float(argv[argv.index("--min") + 1]) if "--min" in argv else 0.0
    bpy.ops.wm.read_factory_settings(use_empty=True)
    A, B = load(group("--a")), load(group("--b"))
    verts = [o.matrix_world @ v.co for o in B for v in o.data.vertices]
    kd = kdtree.KDTree(len(verts))
    for i, v in enumerate(verts):
        kd.insert(v, i)
    kd.balance()
    best = (1e18, None, None)
    for o in A:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            co, _, d = kd.find(w)
            if d < best[0]:
                best = (d, tuple(round(x, 4) for x in w), tuple(round(x, 4) for x in co))
    ok = best[0] >= need
    print("WITNESS a=%s b=%s" % (best[1], best[2]))
    print("CLEARANCE %.4f %s (min %.2f)" % (best[0], "PASS" if ok else "FAIL", need), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]))
