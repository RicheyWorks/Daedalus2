# SPDX-License-Identifier: MIT
"""One command from recipe to showcase: build a land, then render BEFORE and AFTER with identical cameras.

    python land_showcase.py RECIPE OUT_DIR --before PREV_REV_GLBS... [--reference OTHER.glb ...] [--res 1920x1200] [--samples 64] [--quick]

BEFORE is the previous revision of the SAME land (same seed, same cameras): an honest matched pair. --reference renders
an inspiration land (hero + top only), labelled as a different land.

RECIPE is a land recipe module in tools/blender that exposes:
  * build(out_dir) -> (layout, focus_xy)
  * NAME
reedwheel_haven is one.

Steps:
1. Build the land into OUT_DIR. The build runs in the same process, so no second Blender is started.
2. Render AFTER (every exported role GLB) and BEFORE (the given GLBs). Both use the same three cameras:
   * hero: three-quarter view of the island centre at a fixed distance
   * detail: close view on the land's focus
   * top: orthographic plan at a fixed scale
   Cameras are fixed numbers and do not depend on scene bounds, so the pair is comparable shot for shot.
3. Write NAME.showcase.json. It holds every image's sha256, bytes, settings, sources and hashes, and the camera
   numbers. Each image is labelled a Blender render, not an Unreal capture.

--quick renders 640x400 at 16 samples, for checking framing. --resume reuses a finished shot only when every input
that decides its pixels matches (render_cache.py: sources, samples, resolution, view, focus, frame, adjustment
identity, PNG hash); the build is byte-reproducible (repro_check.py), so a restarted batch picks up where it stopped.
Runs wherever `bpy` imports: the cloud venv, or Blender's own Python.
"""
import importlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import showcase_render as SR  # noqa: E402

HERO = (0.0, 0.0, 0.0, 330.0)        # target x, y, z, distance: the whole 220 m plateau with its islet in frame
TOP = (0.0, 0.0, 0.0, 300.0)         # centre x, y, (unused), ortho scale in metres


def main(argv):
    recipe, out = argv[0], os.path.abspath(argv[1])
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    def files(flag):
        got = []
        if flag in argv:
            i = argv.index(flag) + 1
            while i < len(argv) and not argv[i].startswith("--"):
                got.append(os.path.abspath(argv[i]))
                i += 1
        return got
    before, reference = files("--before"), files("--reference")
    quick = "--quick" in argv
    res = (640, 400) if quick else tuple(int(v) for v in opt("--res", "1920x1200").split("x"))
    samples = 16 if quick else int(opt("--samples", "64"))
    R = importlib.import_module(recipe)
    t0 = time.time()
    layout, focus = R.build(out)
    after = [os.path.join(out, v["file"]) for v in layout["roles"].values()] + [os.path.join(out, layout["island_file"])]
    sc = layout.get("showcase", {})
    spread = max(((v["anchor"][0] - focus[0]) ** 2 + (v["anchor"][1] - focus[1]) ** 2) ** .5 for v in layout["roles"].values())
    hero = tuple(sc["hero"]) if "hero" in sc else HERO                       # the recipe can frame its own story
    detail = tuple(sc["detail"]) if "detail" in sc else (round(focus[0], 2), round(focus[1], 2), 0.0, round(max(48.0, spread * 2.4), 1))
    shots = []
    for tag, glbs in (("after", after), ("before", before), ("reference", reference)):
        if not glbs:
            continue
        top = tuple(sc["top"]) if "top" in sc else TOP
        for view, frame in (("hero", hero), ("detail", detail), ("top", top)):
            if tag == "reference" and view == "detail":
                continue                                  # inspiration only: a different land, so no matched close-up
            m = SR.render(out, glbs, tag, view, focus=detail[:3] if view == "detail" else None, frame=frame, res=res, samples=samples, name=R.NAME,
                          resume="--resume" in argv)
            shots.append(m)
    card = {"land": layout.get("land_id"), "name": R.NAME, "label": "Blender renders (Cycles CPU) - NOT Unreal captures",
            "comparable": "before and after share camera numbers, light, sky, samples and resolution per view",
            "cameras": {"hero": hero, "detail": detail, "top": tuple(sc.get("top", TOP))}, "res": list(res), "samples": samples, "quick": quick,
            "before_sources": [os.path.basename(b) for b in before], "reference_sources": [os.path.basename(b) for b in reference],
            "reference_note": "inspiration/source reference only - a different seed and geometry, NOT the same land", "shots": shots, "seconds": round(time.time() - t0, 1)}
    SR.RCACHE.write_json_atomic(os.path.join(out, R.NAME + ".showcase.json"), card)
    print("LAND_SHOWCASE %s shots=%d %.0fs" % (R.NAME, len(shots), card["seconds"]), flush=True)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
