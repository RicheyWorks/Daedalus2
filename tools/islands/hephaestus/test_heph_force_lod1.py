# SPDX-License-Identifier: MIT
"""Headless: heph_turn.should_force_lod1 (no Unreal, no bridge). HEPH_FORCE_LOD1=0 disables, =1 forces, otherwise auto-on
when preflight.json lists lod1_ready landmarks and needs_import is empty. Prints PASS/FAIL; exits 1 on failure."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import heph_turn as t  # noqa: E402  (import has no side effects; main() only runs under __main__)

fails = []
def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)

ready = {"lod1_ready": ["Prop_Grok_Monolith", "Prop_ArkWreck_Hull"], "needs_import": []}
check(not t.should_force_lod1(ready, {"HEPH_FORCE_LOD1": "0"}), "explicit HEPH_FORCE_LOD1=0 -> False")
check(t.should_force_lod1({}, {"HEPH_FORCE_LOD1": "1"}), "explicit HEPH_FORCE_LOD1=1 -> True")
check(t.should_force_lod1(ready, {}), "lod1_ready nonempty + needs_import [] -> True")
check(not t.should_force_lod1({"lod1_ready": ["Prop_Grok_Monolith"], "needs_import": ["Prop_Grok_SeedPod"]}, {}),
      "lod1_ready nonempty + needs_import nonempty -> False")
check(not t.should_force_lod1({"lod1_ready": [], "needs_import": []}, {}), "lod1_ready empty -> False")
check(not t.should_force_lod1({}, {}), "no preflight -> False")
check(isinstance(t.load_preflight(), dict), "load_preflight reads data/islands/hephaestus/preflight.json (or {})")
check(t.load_preflight(r"C:\nope\missing.json") == {}, "missing preflight -> {} (no crash)")
print("PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(1 if fails else 0)
