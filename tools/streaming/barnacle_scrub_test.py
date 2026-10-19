# SPDX-License-Identifier: MIT
"""Tests for G151 Barnacle Scrub."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import barnacle_scrub as b  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "barnacle-scrub-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = b.validate(raw())
        self.assertEqual(c.npc_name, "Diver Pell")
        self.assertEqual((c.rate, c.checksum, c.max_lost), (12, True, 105))
        self.assertEqual(len(b.keys_for(c)), 1200)

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["reef"].update(checksum=1),
                    lambda d: d["reef"].update(rate=-1),
                    lambda d: d["reef"].update(ticks=0),
                    lambda d: d["reef"].update(max_lost=True),
                    lambda d: d["reef"].pop("max_reads"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("dive")):
            d = raw()
            mut(d)
            with self.assertRaises(b.ScrubError):
                b.validate(d)


class ReefTest(unittest.TestCase):
    def test_checksum_repairs_from_good_copy(self):
        r = b.Reef(3)
        r.a[0] = False
        self.assertEqual(r.visit(0, True), b.REPAIRED)
        self.assertEqual((r.a[0], r.b[0]), (True, True))
        r.b[1] = False
        self.assertEqual(r.visit(1, True), b.REPAIRED)
        self.assertEqual(r.visit(2, True), b.OK)

    def test_both_copies_rotted_is_lost(self):
        r = b.Reef(1)
        r.a[0] = r.b[0] = False
        self.assertEqual((r.visit(0, True), r.lost()), (b.LOST, 1))

    def test_blind_repair_spreads_rot(self):
        r = b.Reef(2)
        r.a[0] = False  # A rotted, B good: copying A over B destroys the save
        self.assertEqual(r.visit(0, False), b.SPREAD)
        self.assertEqual(r.lost(), 1)
        r.b[1] = False  # B rotted: copying A over B happens to be right
        self.assertEqual(r.visit(1, False), b.REPAIRED)
        self.assertEqual(r.lost(), 1)

    def test_rot_only_hits_good_copies(self):
        r = b.Reef(4)
        rng = b.Lcg(5)
        total = r.rot(rng, 50)
        self.assertEqual(total, sum(not x for x in r.a) + sum(not x for x in r.b))
        self.assertLessEqual(total, 8)


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = b.validate(raw())

    def test_tuned_scrub_wins(self):
        r = b.simulate(self.c)
        self.assertEqual(r.status, b.WON)
        self.assertLessEqual(r.lost, self.c.max_lost)
        self.assertLessEqual(r.reads, self.c.max_reads)
        self.assertGreater(r.repaired, r.lost)

    def test_slow_diver_loses_saves(self):
        for rate in (0, 3, 6):
            r = b.simulate(self.c, rate)
            self.assertEqual((r.status, r.reason), (b.FAILED, b.FAIL_LOST), rate)

    def test_fast_diver_runs_out_of_air(self):
        for rate in (16, 40):
            r = b.simulate(self.c, rate)
            self.assertEqual((r.status, r.reason), (b.FAILED, b.FAIL_READS), rate)
            self.assertLess(r.lost, b.simulate(self.c).lost)

    def test_no_checksum_spreads_rot(self):
        r = b.simulate(self.c, checksum=False)
        self.assertEqual((r.status, r.reason), (b.FAILED, b.FAIL_LOST))
        self.assertGreater(r.spread, 0)
        self.assertGreater(r.lost, 5 * b.simulate(self.c).lost)

    def test_tuned_wins_across_seeds(self):
        for seed in range(1, 6):
            d = raw()
            d["seed"] = seed
            self.assertEqual(b.simulate(b.validate(d)).status, b.WON, seed)

    def test_deterministic(self):
        self.assertEqual(b.simulate(self.c), b.simulate(self.c))


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = b.islands_from_shoals(json.load(fh))
        c = b.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_win_and_traps(self):
        self.assertEqual(b.main([DATA]), 0)
        self.assertEqual(b.main([DATA, "--rate", "4"]), 1)
        self.assertEqual(b.main([DATA, "--rate", "20"]), 1)
        self.assertEqual(b.main([DATA, "--no-checksum"]), 1)


if __name__ == "__main__":
    unittest.main()
