# SPDX-License-Identifier: MIT
"""Tests for G123 Prefetch Pelicans."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import prefetch_pelicans as p  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "prefetch-pelicans-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = p.validate(raw())
        self.assertEqual(c.npc_name, "Flockwarden Pim")
        self.assertEqual((c.depth, c.latency), (5, 4))

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["pelicans"].update(depth=0),
                    lambda d: d["pelicans"].update(flights_per_tick=0),
                    lambda d: d["pelicans"].update(jump_permille=1001),
                    lambda d: d["pelicans"].update(latency=True),
                    lambda d: d["pelicans"].pop("max_wasted"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("ferry")):
            d = raw()
            mut(d)
            with self.assertRaises(p.PelicanError):
                p.validate(d)


class PrefetcherTest(unittest.TestCase):
    def test_respects_flight_limit_and_depth(self):
        pf = p.Prefetcher(5, 3, 2)
        self.assertEqual(pf.tick(0, 0, 100), 2)
        self.assertEqual(pf.tick(1, 0, 100), 2)
        self.assertEqual(pf.tick(2, 0, 100), 1)
        self.assertEqual(pf.tick(3, 0, 100), 0)
        self.assertEqual(sorted(pf.lands), [0, 1, 2, 3, 4])

    def test_lands_after_latency(self):
        pf = p.Prefetcher(1, 3, 1)
        pf.tick(10, 7, 100)
        self.assertFalse(pf.ready(7, 12))
        self.assertTrue(pf.ready(7, 13))

    def test_wraps_around_path(self):
        pf = p.Prefetcher(3, 0, 3)
        pf.tick(0, 9, 10)
        self.assertEqual(sorted(pf.lands), [0, 1, 9])

    def test_drop_except_counts_waste(self):
        pf = p.Prefetcher(4, 1, 4)
        pf.tick(0, 0, 100)
        self.assertEqual(pf.drop_except({2, 3, 50}), 2)
        self.assertEqual(sorted(pf.lands), [2, 3])

    def test_path_and_starts(self):
        c = p.validate(raw())
        self.assertEqual(len(p.path_for(c)), 1200)
        self.assertEqual(p.island_starts(c)[:3], [0, 200, 400])


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = p.validate(raw())

    def test_latency_plus_one_wins(self):
        for d in (5, 6):
            r = p.simulate(self.c, d)
            self.assertEqual(r.status, p.WON, d)
            self.assertGreater(r.ferries, 0)

    def test_shallow_readahead_stalls(self):
        for d in (1, 2, 4):
            r = p.simulate(self.c, d)
            self.assertEqual((r.status, r.reason), (p.FAILED, p.FAIL_STALL), d)

    def test_deep_readahead_wastes(self):
        for d in (7, 10, 32):
            r = p.simulate(self.c, d)
            self.assertEqual((r.status, r.reason), (p.FAILED, p.FAIL_WASTE), d)

    def test_stalls_flatten_once_depth_covers_latency(self):
        s5 = p.simulate(self.c, 5).stalls
        self.assertEqual(p.simulate(self.c, 8).stalls, s5)
        self.assertGreater(p.simulate(self.c, 4).stalls, s5)

    def test_no_ferries_no_waste(self):
        d = raw()
        d["pelicans"]["jump_permille"] = 0
        r = p.simulate(p.validate(d), 32)
        self.assertEqual((r.wasted, r.ferries), (0, 0))

    def test_deterministic(self):
        self.assertEqual(p.simulate(self.c), p.simulate(self.c))


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = p.islands_from_shoals(json.load(fh))
        c = p.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_win_and_traps(self):
        self.assertEqual(p.main([DATA]), 0)
        self.assertEqual(p.main([DATA, "--depth", "1"]), 1)
        self.assertEqual(p.main([DATA, "--depth", "32"]), 1)

    def test_receipt_and_npc(self):
        c = p.validate(raw())
        rc = p.receipt(c, p.simulate(c), c.depth)
        self.assertEqual((rc["quest"], rc["depth"]), (p.QUEST_ID, 5))
        self.assertTrue(p.npc_say(c, "ferry").startswith("Flockwarden Pim: "))


if __name__ == "__main__":
    unittest.main()
