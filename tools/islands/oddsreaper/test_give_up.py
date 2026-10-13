# SPDX-License-Identifier: MIT
"""Headless (no Unreal): give-up never lands in the past (round 3 runs after 23:00) and HANDOFF target is overridable."""
import datetime as dt, importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oddsreaper_turn as t

late = dt.datetime(2026, 10, 12, 23, 40)
t.GIVE_UP_HHMM = ""; t.GIVE_UP_MIN = 60
assert t._give_up_dt(late) == dt.datetime(2026, 10, 13, 0, 40)
t.GIVE_UP_HHMM = "23:00"
assert t._give_up_dt(late) == dt.datetime(2026, 10, 13, 23, 0), "passed HH:MM must roll to tomorrow"
assert t._give_up_dt(dt.datetime(2026, 10, 12, 22, 20)) == dt.datetime(2026, 10, 12, 23, 0)
os.environ["OR_NEXT"] = "disk-saver"; importlib.reload(t)
assert t.NEXT == "disk-saver"
print("test_give_up: ALL PASS")
