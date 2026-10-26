# SPDX-License-Identifier: MIT
"""Headless (no Unreal): RAM gate skips build/PIE when host free RAM is low (round 5: ~0.9-1.1 GB free), fails open if unreadable."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oddsreaper_turn as t

assert t.ram_ok("play", 1.5, free=0.93) is False
assert t.ram_ok("build", 2.0, free=1.92) is False
assert t.ram_ok("play", 1.5, free=3.66) is True
t.free_ram_gb = lambda: None
assert t.ram_ok("play", 1.5) is True, "unreadable RAM must fail open"
src = open(t.__file__, encoding="utf-8").read()
assert 'ram_ok("build", MIN_BUILD_GB)' in src and 'ram_ok("play", MIN_PLAY_GB)' in src
print("test_ram_gate: ALL PASS")
