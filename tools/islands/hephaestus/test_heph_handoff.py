# -*- coding: utf-8 -*-
"""Headless checks for heph_turn HANDOFF matcher (round-3 youtube-master style)."""
import importlib.util, sys
from pathlib import Path
import datetime as dt

TOOL = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("heph_turn", TOOL / "heph_turn.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
pat = m.HANDOFF_US

should_match = [
    "HANDOFF hephaestus — youtube-master round-3 done",
    "HANDOFF youtube-master -> hephaestus",
    "HANDOFF youtube-master to hephaestus",
]
should_miss = [
    "HANDOFF disk-saver -> youtube-master",
    "going after disk-saver HANDOFF",
    "waiting on disk-saver HANDOFF for round-3",
]

ok = True
for s in should_match:
    if not pat.search(s):
        print("FAIL expected match:", s); ok = False
    else:
        print("PASS match:", s[:60])
for s in should_miss:
    if pat.search(s):
        print("FAIL expected miss:", s); ok = False
    else:
        print("PASS miss:", s)
assert m.give_up_at(dt.datetime(2026,10,12,22,50), {}) > dt.datetime(2026,10,12,22,50)
print("PASS give_up_at")
print("ALL PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
