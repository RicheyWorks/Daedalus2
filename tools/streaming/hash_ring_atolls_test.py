# SPDX-License-Identifier: MIT
"""Tests for G105 Hash Ring Atolls."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import hash_ring_atolls as h  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "hash-ring-atolls-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = h.validate(raw())
        self.assertEqual(c.npc_name, "Ringwarden Tamsin")
        self.assertEqual((c.start_atolls, len(c.atolls)), (6, 10))

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["ring"].update(vnodes=0),
                    lambda d: d["ring"].update(start_atolls=3),
                    lambda d: d["ring"].update(start_atolls=10),
                    lambda d: d["ring"].update(load_cap_permille=999),
                    lambda d: d["ring"].update(events=True),
                    lambda d: d["ring"].pop("max_moved_permille"),
                    lambda d: d["atolls"].append({"id": "tern_cay"}),
                    lambda d: d["islands"].append({"id": "bad id"}),
                    lambda d: d["npc"]["lines"].pop("sink")):
            d = raw()
            mut(d)
            with self.assertRaises(h.RingError):
                h.validate(d)


class RingTest(unittest.TestCase):
    def setUp(self):
        self.c = h.validate(raw())
        self.keys = h.keys_for(self.c)

    def test_owner_deterministic_and_live(self):
        r = h.HashRing(["a", "b", "c"], 16)
        for k in self.keys[:200]:
            self.assertIn(r.owner(k), {"a", "b", "c"})
            self.assertEqual(r.owner(k), h.HashRing(["c", "b", "a"], 16).owner(k))

    def test_join_moves_only_to_new_atoll(self):
        r = h.HashRing(list(self.c.atolls[:6]), 64)
        before = {k: r.owner(k) for k in self.keys}
        r.add("drift_isle")
        for k in self.keys:
            o = r.owner(k)
            self.assertIn(o, (before[k], "drift_isle"))

    def test_leave_moves_only_its_saves(self):
        r = h.HashRing(list(self.c.atolls[:6]), 64)
        before = {k: r.owner(k) for k in self.keys}
        r.remove("gull_rock")
        for k in self.keys:
            if before[k] != "gull_rock":
                self.assertEqual(r.owner(k), before[k])
            else:
                self.assertNotEqual(r.owner(k), "gull_rock")

    def test_empty_ring(self):
        with self.assertRaises(h.RingError):
            h.HashRing([], 4).owner("x")
        with self.assertRaises(h.RingError):
            h.HashRing(["a"], 0)

    def test_mod_n_moves_most_saves(self):
        m = h.ModN(list(self.c.atolls[:6]))
        before = {k: m.owner(k) for k in self.keys}
        m.add("drift_isle")
        moved = sum(m.owner(k) != before[k] for k in self.keys)
        self.assertGreater(moved, len(self.keys) * 7 // 10)

    def test_events_keep_atoll_counts_in_range(self):
        live = set(self.c.atolls[:self.c.start_atolls])
        for kind, a in h.plan_events(self.c):
            if kind == "join":
                self.assertNotIn(a, live)
                live.add(a)
            else:
                self.assertIn(a, live)
                live.discard(a)
            self.assertTrue(h.MIN_ATOLLS <= len(live) <= len(self.c.atolls))
        kinds = {k for k, _ in h.plan_events(self.c)}
        self.assertEqual(kinds, {"join", "leave"})


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = h.validate(raw())

    def test_virtual_markers_win(self):
        for vn in (32, 64, 128):
            r = h.simulate(self.c, vn)
            self.assertEqual((r.status, r.events_ok), (h.WON, self.c.events), vn)
            self.assertLessEqual(r.worst_load_permille, self.c.load_cap_permille)

    def test_few_markers_overload(self):
        for vn in (1, 4, 8):
            r = h.simulate(self.c, vn)
            self.assertEqual(r.status, h.FAILED, vn)
            self.assertGreater(r.worst_load_permille, self.c.load_cap_permille)

    def test_mod_n_swamps_ferries(self):
        r = h.simulate(self.c, mod_n=True)
        self.assertEqual((r.status, r.reason), (h.FAILED, h.FAIL_MOVED))
        self.assertGreater(r.total_moved, 4 * h.simulate(self.c).total_moved)

    def test_deterministic(self):
        self.assertEqual(h.simulate(self.c), h.simulate(self.c))


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = h.islands_from_shoals(json.load(fh))
        c = h.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_win_and_traps(self):
        self.assertEqual(h.main([DATA]), 0)
        self.assertEqual(h.main([DATA, "--vnodes", "1"]), 1)
        self.assertEqual(h.main([DATA, "--mod-n"]), 1)

    def test_receipt_and_npc(self):
        c = h.validate(raw())
        rc = h.receipt(c, h.simulate(c), c.vnodes, False)
        self.assertEqual((rc["quest"], rc["scheme"]), (h.QUEST_ID, "ring_v64"))
        self.assertTrue(h.npc_say(c, "rise").startswith("Ringwarden Tamsin: "))


if __name__ == "__main__":
    unittest.main()
