# SPDX-License-Identifier: MIT
"""Headless: Hephaestus hero SceneCapture exposure ladder + brightness gate (no Unreal needed).

Stubs the `unreal` module, imports heph_island_ue, and checks: the ladder starts with auto+1 and ends with the
unlit base_color rung; manual rungs carry an EV100; mean_lum matches Rec.601 on tuples and .r/.g/.b objects;
sample_grid is 9x9 and inside the frame; the gate matches the NFT card gate (20); the
world-light verdict and lit-hero-owed flag behave on the round-3 dark world and the restored Clear world. Prints PASS/FAIL; exits 1 on failure.
"""
import sys, types
from pathlib import Path

_ue = types.ModuleType("unreal")
_ue.__getattr__ = lambda name: type(name, (), {})  # any unreal.X is a dummy class
sys.modules.setdefault("unreal", _ue)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import heph_island_ue as h  # noqa: E402

fails = []
def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)

lad = h.EXPOSURE_LADDER
check(lad[0][0] == "auto+1" and lad[0][2] is None and lad[0][3] == 1.0, "first rung is auto exposure +1")
check(lad[-1][1] == "SCS_BASE_COLOR", "last rung is unlit base color")
check(all(r[2] is not None for r in lad if r[0].startswith("manual")), "manual rungs carry an EV100")
check(len({r[0] for r in lad}) == len(lad), "rung labels unique")
check(abs(h.mean_lum([(255, 255, 255), (0, 0, 0)]) - 127.5) < 0.01, "mean_lum white+black = 127.5")
C = types.SimpleNamespace
check(abs(h.mean_lum([C(r=100, g=50, b=10)]) - (29.9 + 29.35 + 1.14)) < 0.01, "mean_lum reads .r/.g/.b")
check(h.mean_lum([]) == 0.0, "mean_lum empty = 0")
g = h.sample_grid(1920, 1080)
check(len(g) == 81 and all(0 <= x < 1920 and 0 <= y < 1080 for x, y in g), "sample_grid 9x9 inside 1920x1080")
check(h.MIN_CAPTURE_LUM == 20.0, "capture gate = NFT card gate (20)")
wv = h.world_light_verdict([0.0], [0.017])
check(wv["dark"] and wv["sun_lux"] == 0.0, "round-3 storm save (sun 0 lux, sky 0.017) reads as world-dark")
check(not h.world_light_verdict([10.0], [1.1])["dark"], "restored Clear world (sun 10 lux, sky 1.1) reads as lit")
check(h.world_light_verdict([], [])["dark"], "no sun and no sky light = dark")
check(not h.world_light_verdict([0.0], [1.1])["dark"], "sky light alone still counts as lit")
check(h.lit_owed("base_color", 201.4), "base_color fallback (round-4 23:45 hero) leaves a lit hero owed")
check(not h.lit_owed("manual_ev8", 42.0), "lit rung over the gate clears the debt")
check(h.lit_owed("auto+1", 0.1) and h.lit_owed(None, None), "dark lit rung or no capture = owed")
print("ALL PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(1 if fails else 0)