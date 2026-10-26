# SPDX-License-Identifier: MIT
"""Headless: Hephaestus hero framing + basalt ground (no Unreal needed).

Round-5 lit capture (luma 174) was a pale 1024 m blockout disc with the caldera props as specks: the fixed
hero_cam_m sat ~230 m out and the ground used the white engine material. Checks hero_pose_from_layout on the real
layout.json: fits closer than the fixed pose, keeps the view direction, every trimmed core point sits inside the
FOV cone, HEPH_HERO_FIT=0 and thin layouts fall back to the fixed pose, and run() puts MI_BasaltGround on the
ground disc and passes the fitted fov to hero_capture. Prints PASS/FAIL; exits 1 on failure.
"""
import json, math, sys, types
from pathlib import Path

_ue = types.ModuleType("unreal")
_ue.__getattr__ = lambda name: type(name, (), {})
sys.modules.setdefault("unreal", _ue)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import heph_island_ue as h  # noqa: E402

LAYOUT = HERE.parents[2] / "data" / "islands" / "hephaestus" / "layout.json"
fails = []
def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)

lay = json.loads(LAYOUT.read_text(encoding="utf-8"))
cam, tgt, fov, info = h.hero_pose_from_layout(lay, env={})
print(" . fitted", cam, tgt, fov, info)
check(info.get("fit") is True, "real layout: fitted pose")
check(info["dist_m"] < 0.85 * info["fixed_dist_m"], f"fit is closer than fixed ({info['dist_m']} < 0.85*{info['fixed_dist_m']} m)")
check(info["dist_m"] >= h.HERO_FRAME_MIN_M, "fit respects minimum distance")
v0 = [lay["hero_cam_m"][i] - lay["hero_target_m"][i] for i in range(3)]
v1 = [cam[i] - tgt[i] for i in range(3)]
cosang = sum(a * b for a, b in zip(v0, v1)) / (math.sqrt(sum(a * a for a in v0)) * math.sqrt(sum(b * b for b in v1)))
check(cosang > 0.9999, "view direction kept (same three-quarter overlook)")
pts = [(p["x"], p["y"], p.get("z", 0)) for p in lay["placements"] if p.get("zone") in h.HERO_FRAME_ZONES and not p.get("skip")]
cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
check(abs(tgt[0] - cx) < 0.01 and abs(tgt[1] - cy) < 0.01, "target is the hero-zone centroid")
ds = sorted(math.hypot(p[0] - cx, p[1] - cy) for p in pts)
core_r = ds[int(h.HERO_FRAME_TRIM * (len(ds) - 1) + 0.5)]
axis = [-x for x in v1]; an = math.sqrt(sum(a * a for a in axis))
inside = 0; core = [p for p in pts if math.hypot(p[0] - cx, p[1] - cy) <= core_r]
for p in core:
    w = [p[i] - cam[i] for i in range(3)]; wn = math.sqrt(sum(a * a for a in w))
    ang = math.degrees(math.acos(max(-1, min(1, sum(a * b for a, b in zip(w, axis)) / (wn * an)))))
    inside += ang <= fov / 2
check(inside == len(core), f"all {len(core)} core props inside the {fov} deg cone ({inside})")
c2, t2, _, i2 = h.hero_pose_from_layout(lay, env={"HEPH_HERO_FIT": "0"})
check(not i2["fit"] and c2 == lay["hero_cam_m"] and t2 == lay["hero_target_m"], "HEPH_HERO_FIT=0 keeps fixed pose")
thin = {"hero_cam_m": [140, -160, 90], "hero_target_m": [0, 0, 5], "placements": [{"x": 0, "y": 0, "zone": "caldera_forge"}]}
check(not h.hero_pose_from_layout(thin, env={})[3]["fit"], "fewer than 3 hero points -> fixed pose")
src = (HERE / "heph_island_ue.py").read_text(encoding="utf-8")
run_src = src[src.index("def run():"):]
check("basalt_material()" in run_src and "g.static_mesh_component.set_material(0, basalt)" in run_src, "run() puts MI_BasaltGround on the ground disc")
check("hero_pose_from_layout(lay)" in run_src and "fov=hero_fov" in run_src, "run() uses the fitted pose and fov")
check(max(h.BASALT_COLOR) < 0.1, "basalt colour is dark")
if fails:
    print("test_heph_hero_frame: FAIL"); sys.exit(1)
print(f"test_heph_hero_frame: ALL PASS (dist {info['dist_m']} m vs fixed {info['fixed_dist_m']} m)")
