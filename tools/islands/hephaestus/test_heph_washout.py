# SPDX-License-Identifier: MIT
"""Headless: Hephaestus washout gate (no Unreal needed).

Round-5 SceneCapture cleared luma 174 but the forge was a speck on a pale 1024 m blockout disc. The luma>=20 gate
only catches dark frames. washout_owed flags a bright probe whose 3x3 center is nearly all-pale (disc fills the view).
Checks pure helpers on synthetic grids + the archived round-5 / Blender / Play PNGs when present. Prints PASS/FAIL.
"""
import sys, types
from pathlib import Path

_ue = types.ModuleType("unreal")
_ue.__getattr__ = lambda name: type(name, (), {})
sys.modules.setdefault("unreal", _ue)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import heph_island_ue as h  # noqa: E402

fails = []
def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)

# Synthetic 9x9: washed pale disc (center all 240)
washed = [240.0] * 81
ws = h.washout_stats(washed, n=9)
check(ws["mean"] == 240.0 and ws["center_pale_frac"] == 1.0, f"washed grid stats {ws}")
check(h.washout_owed(ws) is True, "washed grid -> washout_owed")

# Dark frame: not washout (lit_owed's job)
dark = [5.0] * 81
ds = h.washout_stats(dark, n=9)
check(h.washout_owed(ds) is False, "dark grid is not washout")
check(h.lit_owed("auto+1", ds["mean"]) is True, "dark grid is lit_owed")

# Good forge overlook: mid tones in center, few pale samples
good = []
for j in range(9):
    for i in range(9):
        # sky rim a bit brighter, forge core mid-dark
        if 3 <= i <= 5 and 3 <= j <= 5:
            good.append(90.0 + (i + j) % 3 * 5)
        else:
            good.append(70.0 + (i * 3 + j) % 20)
gs = h.washout_stats(good, n=9)
check(gs["center_pale_frac"] < 0.5, f"good grid center_pale {gs['center_pale_frac']}")
check(h.washout_owed(gs) is False, "good mid-tone grid not washout")

# Edge case: bright mean but detailed center (pale_frac high on rim only)
rim_bright = []
for j in range(9):
    for i in range(9):
        if 3 <= i <= 5 and 3 <= j <= 5:
            rim_bright.append(100.0)
        else:
            rim_bright.append(200.0)
rs = h.washout_stats(rim_bright, n=9)
check(rs["pale_frac"] > 0.5 and rs["center_pale_frac"] == 0.0, f"rim-bright center clear {rs}")
check(h.washout_owed(rs) is False, "rim pale + mid center is not washout")

# Real PNGs when present (same 9x9 inset probe as the editor)
SHOTS = Path(r"C:\Users\730ri\projects\bot-team\shots\hephaestus")
try:
    from PIL import Image
except ImportError:
    Image = None

def probe_png(path, n=9):
    im = Image.open(path).convert("RGB")
    w, hh = im.size
    xs = [int(w * (0.05 + 0.9 * i / (n - 1))) for i in range(n)]
    ys = [int(hh * (0.05 + 0.9 * j / (n - 1))) for j in range(n)]
    return [h.luma601(*im.getpixel((x, y))) for y in ys for x in xs]

if Image is not None:
    r5 = SHOTS / "hero_unreal_lit_r5.png"
    bl = SHOTS / "hero_blender.png"
    if r5.is_file():
        s = h.washout_stats(probe_png(r5), n=9)
        print(" . r5 probe", s)
        check(h.washout_owed(s) is True, f"archived round-5 lit capture is washout ({s})")
        check(h.lit_owed("auto+1", s["mean"]) is False, "round-5 is lit (not lit_owed)")
    if bl.is_file():
        s = h.washout_stats(probe_png(bl), n=9)
        print(" . blender probe", s)
        check(h.washout_owed(s) is False, f"Blender overlook is not washout ({s})")

# Wiring: hero_capture writes washout_owed; run() copies it into island_result
src = (HERE / "heph_island_ue.py").read_text(encoding="utf-8")
check('"washout_owed"' in src and "washout_owed(best[1])" in src, "hero_capture records + NEED on washout")
check('cap.get("washout_owed"' in src, "run() writes washout_owed into island_result")
check("WASHOUT_CENTER_PALE_FRAC" in src and "center_pale_frac" in src, "constants + probe fields present")

if fails:
    print("test_heph_washout: FAIL"); sys.exit(1)
print("test_heph_washout: ALL PASS")
