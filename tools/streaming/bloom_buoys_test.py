# SPDX-License-Identifier: MIT
"""Tests for G99 Bloom Buoys."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import bloom_buoys as b  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "bloom-buoys-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = b.validate(raw())
        self.assertEqual(c.npc_name, "Buoykeeper Fennick")
        self.assertEqual(c.hashes, 7)

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["buoys"].update(hashes=0),
                    lambda d: d["buoys"].update(hashes=33),
                    lambda d: d["buoys"].update(absent_permille=1001),
                    lambda d: d["buoys"].update(bits_per_key=True),
                    lambda d: d["buoys"].pop("max_wasted"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["islands"].append({"id": "bad id"}),
                    lambda d: d["npc"]["lines"].pop("fail")):
            d = raw()
            mut(d)
            with self.assertRaises(b.BuoyError):
                b.validate(d)


class FilterTest(unittest.TestCase):
    def test_no_false_negatives(self):
        for h in (1, 3, 7, 20, 32):
            f = b.BloomFilter(500, h)
            keys = [f"k{i}" for i in range(50)]
            for k in keys:
                f.add(k)
            self.assertTrue(all(f.might_contain(k) for k in keys), h)

    def test_empty_filter_says_no(self):
        f = b.BloomFilter(64, 4)
        self.assertFalse(any(f.might_contain(f"k{i}") for i in range(100)))
        self.assertEqual(f.fill_permille(), 0)

    def test_probes_deterministic_and_in_range(self):
        f = b.BloomFilter(1000, 7)
        p = f._probes("archive_a:0007")
        self.assertEqual(p, f._probes("archive_a:0007"))
        self.assertEqual(len(p), 7)
        self.assertTrue(all(0 <= x < 1000 for x in p))

    def test_fill_near_half_at_optimal_hashes(self):
        c = b.validate(raw())
        f = b.build_buoys(c, b.optimal_hashes(c.bits_per_key))["vault_east"]
        self.assertTrue(420 <= f.fill_permille() <= 580, f.fill_permille())
        self.assertGreater(b.build_buoys(c, 32)["vault_east"].fill_permille(), 900)

    def test_optimal_hashes(self):
        self.assertEqual(b.optimal_hashes(10), 7)
        self.assertEqual(b.optimal_hashes(1), 1)
        self.assertEqual(b.optimal_hashes(64), 32)

    def test_bad_filter(self):
        with self.assertRaises(b.BuoyError):
            b.BloomFilter(0, 1)
        with self.assertRaises(b.BuoyError):
            b.BloomFilter(10, 33)


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = b.validate(raw())

    def test_tuned_hashes_win(self):
        r = b.simulate(self.c)
        self.assertEqual((r.status, r.windows_ok), (b.WON, self.c.windows))
        self.assertLessEqual(r.worst_wasted, self.c.max_wasted)
        self.assertEqual(r.false_negatives, 0)

    def test_neighbourhood_of_optimum_wins(self):
        for h in (5, 6, 7, 8):
            self.assertEqual(b.simulate(self.c, h).status, b.WON, h)

    def test_traps_fail(self):
        for h in (1, 2, 20, 32):
            r = b.simulate(self.c, h)
            self.assertEqual((r.status, r.reason), (b.FAILED, b.FAIL_WASTE), h)
        nb = b.simulate(self.c, use_buoys=False)
        self.assertEqual(nb.status, b.FAILED)
        self.assertEqual(nb.skipped, 0)

    def test_useful_dives_same_every_strategy(self):
        base = b.simulate(self.c).useful_dives
        for h in (1, 7, 32):
            self.assertEqual(b.simulate(self.c, h).useful_dives, base)
        self.assertEqual(b.simulate(self.c, use_buoys=False).useful_dives, base)

    def test_deterministic(self):
        self.assertEqual(b.simulate(self.c), b.simulate(self.c))

    def test_no_lookups_absent_means_no_waste(self):
        d = raw()
        d["buoys"]["absent_permille"] = 0
        r = b.simulate(b.validate(d), 1)
        self.assertEqual((r.total_wasted, r.skipped), (0, 0))


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = b.islands_from_shoals(json.load(fh))
        c = b.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_win_and_trap(self):
        self.assertEqual(b.main([DATA]), 0)
        self.assertEqual(b.main([DATA, "--hashes", "1"]), 1)
        self.assertEqual(b.main([DATA, "--no-buoys"]), 1)

    def test_receipt_and_npc(self):
        c = b.validate(raw())
        rc = b.receipt(c, b.simulate(c), c.hashes)
        self.assertEqual(rc["quest"], b.QUEST_ID)
        self.assertTrue(b.npc_say(c, "ask").startswith("Buoykeeper Fennick: "))


if __name__ == "__main__":
    unittest.main()
