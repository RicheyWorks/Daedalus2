# SPDX-License-Identifier: MIT
"""Render the Tide-Pen's water states: the same pen close-up at LOW, NORMAL and HIGH water.

    python tidepen_tides.py BUILD_DIR [--rev r3] [--view detail|plunge] [--res 1600x1000] [--samples 32] [--resume]

--view plunge looks steeply down into the pen from closer (14 m), so the bed and residents read through the water.

BUILD_DIR holds a built Tide-Pen revision (tidepen_shelf.py). Every role GLB is loaded; the PenWater role, which the
recipe exports at the NORMAL level, is moved by each state's offset_m read from the layout's habitat record (itself
read from data/ocean/habitat-tidepool-r1.json). The camera is fixed, so the three images differ only by the water.
Writes NAME.tide.<state>.detail.png + .json and NAME.tides.json. Labelled Blender renders, not Unreal captures.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import showcase_render as SR  # noqa: E402


def main(argv):
    out = os.path.abspath(argv[0])
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    name = "TidePen_" + opt("--rev", "r3")
    view = opt("--view", "detail")
    lay = json.load(open(os.path.join(out, name + ".layout.json"), encoding="utf-8"))
    hab = lay["habitat"]
    glbs = [os.path.join(out, v["file"]) for v in lay["roles"].values()] + [os.path.join(out, lay["island_file"])]
    res = tuple(int(v) for v in opt("--res", "1600x1000").split("x"))
    samples = int(opt("--samples", "32"))
    pen = lay["roles"]["Pen"]["anchor"]
    frame = (pen[0] - .5, pen[1] - 1.0, -.6, 19.0) if view == "detail" else (pen[0] - 1.2, pen[1], -1.2, 14.0)   # fixed per view
    shots, t0 = [], time.time()
    for st in hab["water_states"]:
        def adjust(dz=st["offset_m"]):
            hit = [o for o in bpy.data.objects if o.type == "MESH" and "_PenWater" in o.name]
            if not hit:
                raise RuntimeError("PenWater role not found in the loaded GLBs")
            for o in hit:
                o.location.z += dz
        m = SR.render(out, glbs, "tide." + st["id"], view, focus=frame[:3], frame=frame, res=res, samples=samples, name=name, adjust=adjust, resume="--resume" in argv,
                     identity={"water_state": st["id"], "offset_m": st["offset_m"], "moves": "PenWater role z", "habitat_sha256": hab["sha256"]})
        m["water_state"] = {k: st[k] for k in ("id", "offset_m", "surface_z", "wet")}
        shots.append(m)
    card = {"name": name, "label": "Blender renders (Cycles CPU) - NOT Unreal captures",
            "comparable": "one camera, light, sky, samples and resolution; only the PenWater role moves (offset_m)",
            "camera": frame, "habitat_source": hab["source"], "habitat_sha256": hab["sha256"], "shots": shots, "seconds": round(time.time() - t0, 1)}
    SR.RCACHE.write_json_atomic(os.path.join(out, name + ".tides.json"), card)
    print("TIDES %s shots=%d %.0fs" % (name, len(shots), card["seconds"]), flush=True)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
