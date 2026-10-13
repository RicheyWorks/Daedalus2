# SPDX-License-Identifier: MIT
"""Headless (no Unreal): post-Play save contract. After Stop Play the turn must run restore_world_sky, then save the
OddsReaperIsland sublevel ONLY, then verify the world is Clear (young_meadow / Clear / ~9.4 / clock running).
No blind bridge 'save' (save_dirty_packages) after Play: that leaked oddsreaper_storm into DaedalusWorld in rounds 3/4.
Run: python test_sublevel_save_plan.py"""
import ast, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oddsreaper_turn as t

fails = []
def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

CLEAR = {"directors": 1, "mood": "young_meadow", "weather": "DaedalusWeather.CLEAR", "hour": 9.41, "clock_running": True}
STORM = {"directors": 1, "mood": "oddsreaper_storm", "weather": "DaedalusWeather.STORM", "hour": 18.75, "clock_running": False}

# 1) plan order
check(t.post_play_plan() == ["stop", "restore_world_sky", "save_sublevel", "verify_clear"], "plan: stop -> restore -> sublevel -> verify")
check("save" not in t.post_play_plan(), "plan has no blind bridge save")

# 2) pure Clear check
check(t.world_clear(CLEAR)[0], "Clear read-back passes")
ok, bad = t.world_clear(STORM)
check(not ok and len(bad) == 4, f"storm read-back fails on all 4 fields ({bad})")
check(not t.world_clear(dict(CLEAR, clock_running=False))[0], "paused clock fails")
check(not t.world_clear(dict(CLEAR, hour=18.75))[0], "storm hour fails")
check(t.world_clear(dict(CLEAR, hour=9.7))[0], "small clock drift (9.7) ok")
check(not t.world_clear({"directors": 0})[0] and not t.world_clear(None)[0], "missing director fails")

# 3) umap jump detection
check(t.world_umap_jumped(100.0, 100.5), "DaedalusWorld mtime advance = jump")
check(not t.world_umap_jumped(100.0, 100.0), "unchanged mtime = no jump")
check(not t.world_umap_jumped(None, 5), "unreadable mtime does not crash")

# 4) sequence with fakes: happy path
def fake(sub, verifies):
    calls, vs = [], list(verifies)
    def mk(n, r):
        def f():
            calls.append(n); return r() if callable(r) else r
        return f
    ops = {"stop": mk("stop", {"playing": False}),
           "restore_world_sky": mk("restore_world_sky", {"ok": True}),
           "save_sublevel": mk("save_sublevel", sub),
           "verify_clear": mk("verify_clear", lambda: vs.pop(0))}
    return ops, calls

ops, calls = fake({"saved": True, "current": "OddsReaperIsland", "world_umap_before": 10.0, "world_umap_after": 10.0}, [CLEAR])
r = t.post_play_save(ops)
check(calls == ["stop", "restore_world_sky", "save_sublevel", "verify_clear"], f"happy order {calls}")
check(r["ok"] and r["clear"] and r["sublevel_saved"] and not r["reclear"], "happy: ok, clear, saved, no reclear")

# 5) DaedalusWorld moved during sublevel save -> restore + verify again
ops, calls = fake({"saved": True, "world_umap_before": 10.0, "world_umap_after": 12.0}, [CLEAR, CLEAR])
r = t.post_play_save(ops)
check(calls == ["stop", "restore_world_sky", "save_sublevel", "verify_clear", "restore_world_sky", "verify_clear"], f"jump -> reclear {calls}")
check(r["reclear"] and r["ok"], "jump: reclear then ok")

# 6) storm still in world after restore -> reclear; still storm -> not ok
ops, calls = fake({"saved": True, "world_umap_before": 10.0, "world_umap_after": 10.0}, [STORM, STORM])
r = t.post_play_save(ops)
check(r["reclear"] and not r["ok"] and not r["clear"], "storm persists -> reported not ok")

# 7) a failing step is recorded, the rest still runs, never a bridge save
def boom(): raise RuntimeError("bridge timeout")
ops, calls = fake({"saved": True, "world_umap_before": 1.0, "world_umap_after": 1.0}, [CLEAR])
ops["stop"] = boom
r = t.post_play_save(ops)
check("error" in r["stop"] and r["order"][:4] == list(t.POST_PLAY_SEQUENCE) and r["ok"], "stop error recorded; restore/save/verify still run")

# 8) source contract: snippets parse, sublevel-only save, finally uses post_play_save, restore reused not duplicated
ast.parse(t.SAVE_SUBLEVEL_CODE); ast.parse(t.VERIFY_CLEAR_CODE)
s = t.SAVE_SUBLEVEL_CODE
check('set_current_level_by_name(NAME)' in s and "save_current_level()" in s and 'NAME = "OddsReaperIsland"' in s, "sublevel save sets OddsReaperIsland current + save_current_level")
check("save_dirty_packages" not in s and "save_map" not in s, "sublevel save never writes dirty packages / persistent map")
check(s.index("set_current_level_by_name(NAME)") < s.index("save_current_level()"), "set current before save")
check("DaedalusWorld.umap" in s and "world_umap_after" in s, "sublevel save records DaedalusWorld.umap mtime")
check(t.RESTORE_WORLD_SKY.endswith("restore_world_sky.py") and os.path.isfile(t.RESTORE_WORLD_SKY), "reuses restore_world_sky.py")
src = open(t.__file__, encoding="utf-8").read()
fin = src[src.index('if __name__ == "__main__":'):]
check("post_play_save()" in fin, "finally runs post_play_save")
check('call("save"' not in fin, "finally has no blind bridge save")
check("save_map" not in src, "turn does not duplicate restore_world_sky's save_map logic")
print("test_sublevel_save_plan: ALL PASS" if not fails else f"test_sublevel_save_plan: FAIL ({len(fails)})")
sys.exit(1 if fails else 0)
