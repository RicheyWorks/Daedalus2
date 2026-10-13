# SPDX-License-Identifier: MIT
"""Headless check for heph_turn give-up + SINCE parsing (no bridge, no link writes). python test_heph_give_up.py"""
import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import heph_turn as t
D = dt.datetime
s = D(2026, 10, 12, 23, 10)
assert t.give_up_at(s, {}) == D(2026, 10, 13, 2, 10), "default start+180"
assert t.give_up_at(s, {"HEPH_GIVE_UP_MIN": "60"}) == D(2026, 10, 13, 0, 10), "custom minutes"
assert t.give_up_at(s, {"HEPH_GIVE_UP": "23:00"}) == D(2026, 10, 13, 23, 0), "passed HH:MM rolls to tomorrow"
assert t.give_up_at(s, {"HEPH_GIVE_UP": "23:45"}) == D(2026, 10, 12, 23, 45), "future HH:MM stays today"
assert t.give_up_at(s, {"HEPH_GIVE_UP": "01:30"}) == D(2026, 10, 13, 1, 30), "after-midnight HH:MM"
os.environ["HEPH_T_ISO"] = "2026-10-12T23:30"
assert t._hhmm("HEPH_T_ISO", "00:00") == D(2026, 10, 12, 23, 30), "ISO SINCE for post-midnight re-arm"
assert t.GIVE_UP > D.now(), "module GIVE_UP is in the future at import"
print("test_heph_give_up ALL PASS")
