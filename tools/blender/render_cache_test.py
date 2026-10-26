# SPDX-License-Identifier: MIT
"""render_cache: when a finished render may be reused. Pure Python, synthetic files, no Blender.

    python tools/blender/render_cache_test.py

Cases (PootScoot review 32692/32727): the same inputs hit; a change to the camera frame, the focus, the view, the
samples, the resolution, a source GLB, the tide offset or the PNG misses; a shot made with adjust() but no identity
never hits; a malformed, truncated or pre-cache-key sidecar misses without raising; an interrupted sidecar write leaves
the previous sidecar intact, and the other shots' sidecars are untouched. Last line "RENDER-CACHE n/m PASS|FAIL".
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_cache as RC  # noqa: E402

res = []


def check(name, ok, info=""):
    res.append(bool(ok))
    print(("ok   " if ok else "FAIL ") + name + ("  " + str(info) if info != "" else ""), flush=True)


with tempfile.TemporaryDirectory() as d:
    glb = os.path.join(d, "Land_Pen.glb")
    open(glb, "wb").write(b"glTF-synthetic-1")
    FRAME, FOCUS = (1.0, -2.0, -0.6, 19.0), (1.0, -2.0, -0.6)
    LOW = {"water_state": "low", "offset_m": -0.5}

    def inp(**kw):
        a = dict(glbs=[glb], view="plunge", focus=FOCUS, frame=FRAME, res=(1920, 1200), samples=48, identity=LOW, adjusted=True)
        a.update(kw)
        return RC.inputs(**a)

    def finish(stem, i, png=b"PNG-low"):
        """What render() does after Cycles: the PNG, then the sidecar."""
        open(stem + ".png", "wb").write(png)
        return RC.write_sidecar(stem, {"sha256": RC.sha(stem + ".png"), "file": os.path.basename(stem) + ".png"}, i)

    stem = os.path.join(d, "Land.tide.low.plunge")
    finish(stem, inp())
    check("same inputs: the finished shot is reused", RC.reusable(stem, inp()) is not None)
    check("camera frame changed: miss", RC.reusable(stem, inp(frame=(1.0, -2.0, -0.6, 14.0))) is None)
    check("focus changed: miss", RC.reusable(stem, inp(focus=(0.0, 0.0, 0.0))) is None)
    check("view changed: miss", RC.reusable(stem, inp(view="detail")) is None)
    check("samples changed: miss", RC.reusable(stem, inp(samples=16)) is None)
    check("resolution changed: miss", RC.reusable(stem, inp(res=(640, 400))) is None)
    check("tide offset changed (same GLBs, same camera): miss", RC.reusable(stem, inp(identity={"water_state": "low", "offset_m": -0.7})) is None)
    check("adjusted with no identity: never reused", RC.reusable(stem, inp(identity=None)) is None)
    check("unadjusted inputs do not match an adjusted shot", RC.reusable(stem, inp(identity=None, adjusted=False)) is None)
    check("float noise in the frame still hits (rounded to 1e-6)", RC.reusable(stem, inp(frame=(1.0 + 1e-9, -2.0, -0.6, 19.0))) is not None)

    open(stem + ".png", "wb").write(b"PNG-edited")
    check("PNG changed after the sidecar: miss", RC.reusable(stem, inp()) is None)
    finish(stem, inp())
    open(glb, "wb").write(b"glTF-synthetic-2")
    check("source GLB changed: miss", RC.reusable(stem, inp()) is None)
    open(glb, "wb").write(b"glTF-synthetic-1")
    check("...and back to the original bytes: hit again", RC.reusable(stem, inp()) is not None)

    good = open(stem + ".json", encoding="utf-8").read()
    open(stem + ".json", "w", encoding="utf-8").write(good[: len(good) // 2])
    try:
        r = RC.reusable(stem, inp())
        check("truncated sidecar: miss, no exception", r is None)
    except Exception as e:  # noqa: BLE001
        check("truncated sidecar: miss, no exception", False, repr(e))
    open(stem + ".json", "w", encoding="utf-8").write("[1, 2, 3]")
    check("sidecar that is not an object: miss", RC.reusable(stem, inp()) is None)
    old = json.loads(good)
    old.pop("cache_key")
    old.pop("cache_inputs")
    open(stem + ".json", "w", encoding="utf-8").write(json.dumps(old))
    check("pre-cache-key sidecar (the r3 batch's format): miss", RC.reusable(stem, inp()) is None)
    os.remove(stem + ".json")
    check("no sidecar: miss", RC.reusable(stem, inp()) is None)

    finish(stem, inp())
    other = os.path.join(d, "Land.tide.high.plunge")
    finish(other, inp(identity={"water_state": "high", "offset_m": 0.6}), b"PNG-high")
    before = open(stem + ".json", "rb").read()
    real = RC.os.replace
    def boom(src, dst):
        raise OSError("disk full")
    RC.os.replace = boom
    try:
        finish(stem, inp(samples=64), b"PNG-low")
        check("an interrupted sidecar write raises", False)
    except OSError:
        check("an interrupted sidecar write raises", True)
    finally:
        RC.os.replace = real
    check("...and leaves the previous sidecar byte-identical", open(stem + ".json", "rb").read() == before)
    check("...which still matches its own inputs, not the new ones", RC.reusable(stem, inp()) is not None and RC.reusable(stem, inp(samples=64)) is None)
    check("...and the other shot's sidecar is untouched and still hits",
          RC.reusable(other, inp(identity={"water_state": "high", "offset_m": 0.6})) is not None)
    check("the cache key is stored with its readable inputs", json.load(open(other + ".json"))["cache_inputs"]["identity"]["offset_m"] == 0.6)

k = sum(res)
print("RENDER-CACHE %d/%d %s" % (k, len(res), "PASS" if k == len(res) else "FAIL"))
sys.exit(0 if k == len(res) else 1)
