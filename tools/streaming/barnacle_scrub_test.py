# SPDX-License-Identifier: MIT
"""Tests for G151 Barnacle Scrub."""
import dataclasses
import json
import os
import zlib
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
        self.assertEqual((c.rate, c.checksum, c.max_lost), (10, True, 105))
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
    def reef(self, n):
        return b.Reef([f"k:{i:04d}" for i in range(n)])

    def flip(self, side, i, bit):
        side[i][bit >> 3] ^= 1 << (bit & 7)

    def test_checksum_repairs_from_good_copy(self):
        r = self.reef(3)
        self.flip(r.a, 0, 5)
        self.assertEqual(r.visit(0, True), b.REPAIRED)
        self.assertTrue(r.good(r.a, 0) and r.good(r.b, 0))
        self.flip(r.b, 1, 77)
        self.assertEqual(r.visit(1, True), b.REPAIRED)
        self.assertEqual(r.visit(2, True), b.OK)

    def test_both_copies_rotted_is_lost(self):
        r = self.reef(1)
        self.flip(r.a, 0, 1)
        self.flip(r.b, 0, 300)
        self.assertEqual((r.visit(0, True), r.lost()), (b.LOST, 1))

    def test_blind_repair_picks_wrong_copy(self):
        r = self.reef(2)
        self.flip(r.a, 0, 9)  # A rotted, B good: copying A over B destroys the save
        self.assertEqual(r.visit(0, False), b.SPREAD)
        self.assertEqual(r.lost(), 1)
        self.flip(r.b, 1, 9)  # B rotted: copying A over B happens to be right
        self.assertEqual(r.visit(1, False), b.REPAIRED)
        self.assertEqual(r.lost(), 1)

    def test_crc32_catches_every_single_bit_flip(self):
        d = bytearray(b.Reef(["k:0000"]).a[0])
        crc = zlib.crc32(d)
        self.assertEqual(len(d), b.PAYLOAD)
        for bit in range(b.PAYLOAD * 8):
            d[bit >> 3] ^= 1 << (bit & 7)
            self.assertNotEqual(zlib.crc32(d), crc, bit)
            d[bit >> 3] ^= 1 << (bit & 7)

    def test_crc32_random_multibit_damage_detected(self):
        # undetected chance is about 2**-32 per corruption; 3000 seeded corruptions should all be caught
        d0 = bytes(b.Reef(["k:0001"]).a[0])
        crc, rng = zlib.crc32(d0), b.Lcg(151)
        for _ in range(3000):
            d = bytearray(d0)
            for _ in range(2 + rng.next(30)):
                bit = rng.next(b.PAYLOAD * 8)
                d[bit >> 3] ^= 1 << (bit & 7)
            if d != d0:
                self.assertNotEqual(zlib.crc32(d), crc)

    def test_rot_spoils_only_good_copies(self):
        r = self.reef(50)
        spoiled = r.rot(b.Lcg(5), 30)
        bad = sum(not r.good(r.a, i) for i in range(50)) + sum(not r.good(r.b, i) for i in range(50))
        self.assertEqual(spoiled, bad)
        self.assertLessEqual(spoiled, 30)


class ScienceTest(unittest.TestCase):
    SEEDS = range(1, 6)

    def setUp(self):
        self.c = b.validate(raw())

    def test_loss_matches_rT_model(self):
        r = b.rot_rate(self.c)
        for rate in (6, 10, 16):
            T = b.window(self.c, rate)
            p = b.predicted_loss_per_window(self.c, rate)
            self.assertAlmostEqual(p, (1 - __import__("math").exp(-r * T)) ** 2)
            self.assertLess(abs(p - (r * T) ** 2) / p, 0.15)  # (rT)^2 is close for small rT
            mc = sum(b.simulate(dataclasses.replace(self.c, seed=s), rate).lost for s in self.SEEDS) / 5
            pred = b.predicted_lost(self.c, rate)
            self.assertLess(abs(mc - pred) / pred, 0.12, (rate, mc, pred))

    def test_reads_per_tick_is_2N_over_T(self):
        for rate in (1, 7, 10, 16):
            res = b.simulate(self.c, rate)
            self.assertAlmostEqual(res.reads / self.c.ticks, b.reads_per_tick(self.c, rate))
            self.assertAlmostEqual(b.reads_per_tick(self.c, rate), 2 * 1200 / b.window(self.c, rate))

    def test_no_checksum_picks_wrong_copy_half_the_time(self):
        res = b.simulate(self.c, checksum=False)
        frac = res.spread / (res.spread + res.repaired)
        self.assertLess(abs(frac - 0.5), 0.05, frac)
        self.assertEqual((res.status, res.reason), (b.FAILED, b.FAIL_LOST))
        self.assertGreater(res.lost, 5 * b.simulate(self.c).lost)

    def test_solver_largest_window_equals_brute_force(self):
        best = b.solve(self.c)
        self.assertEqual(best, b.brute_force(self.c, self.SEEDS))
        self.assertEqual(best, self.c.rate)  # the shipped dive plan is the solver's answer
        self.assertGreater(b.predicted_lost(self.c, best - 1), self.c.max_lost)
        tight = dataclasses.replace(self.c, max_reads=2 * (best - 1) * self.c.ticks)
        self.assertIsNone(b.solve(tight))


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
