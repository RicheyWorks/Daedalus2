# SPDX-License-Identifier: MIT
"""Tests for G126 Breakwater Queue."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import breakwater_queue as b  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "breakwater-queue-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = b.validate(raw())
        self.assertEqual(c.npc_name, "Cranemaster Odo")
        self.assertEqual((c.capacity, c.drain_per_tick), (140, 6))

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["harbour"].update(drain_per_tick=0),
                    lambda d: d["harbour"].update(storm_start=4001),
                    lambda d: d["harbour"].update(storm_len=2001),
                    lambda d: d["harbour"].update(swell_permille=1001),
                    lambda d: d["harbour"].update(capacity=True),
                    lambda d: d["harbour"].pop("max_wait"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("crane")):
            d = raw()
            mut(d)
            with self.assertRaises(b.HarbourError):
                b.validate(d)


class BreakwaterTest(unittest.TestCase):
    def test_fifo_and_waits(self):
        bw = b.Breakwater(5)
        bw.offer("a", 0)
        bw.offer("b", 1)
        bw.offer("c", 1)
        self.assertEqual(bw.drain(2, 3), [3, 2])
        self.assertEqual(bw.drain(5, 4), [3])
        self.assertEqual(bw.drain(1, 5), [])

    def test_full_queue_drops(self):
        bw = b.Breakwater(2)
        self.assertTrue(bw.offer("a", 0))
        self.assertTrue(bw.offer("b", 0))
        self.assertFalse(bw.offer("c", 0))
        self.assertEqual(bw.dropped, 1)

    def test_zero_capacity_drops_all(self):
        bw = b.Breakwater(0)
        self.assertFalse(bw.offer("a", 0))
        with self.assertRaises(b.HarbourError):
            b.Breakwater(-1)

    def test_storm_brings_more_swells(self):
        c = b.validate(raw())
        waves = b.arrivals(c)
        storm = sum(len(w) for w in waves[c.storm_start:c.storm_start + c.storm_len])
        calm = sum(len(w) for w in waves[:c.storm_len])
        self.assertGreater(storm, calm)
        self.assertGreater(storm, c.drain_per_tick * c.storm_len)  # crane is overrun


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = b.validate(raw())

    def test_tuned_breakwater_wins(self):
        for cap in (130, 140, 150):
            r = b.simulate(self.c, cap)
            self.assertEqual(r.status, b.WON, cap)
            self.assertLessEqual(r.dropped, self.c.max_dropped)
            self.assertLessEqual(r.worst_wait, self.c.max_wait)

    def test_short_breakwater_drops(self):
        for cap in (0, 40, 120):
            r = b.simulate(self.c, cap)
            self.assertEqual((r.status, r.reason), (b.FAILED, b.FAIL_DROP), cap)

    def test_long_breakwater_bloats(self):
        for cap in (160, 300, 10_000):
            r = b.simulate(self.c, cap)
            self.assertEqual((r.status, r.reason), (b.FAILED, b.FAIL_WAIT), cap)
        self.assertEqual(b.simulate(self.c, 10_000).dropped, 0)

    def test_every_write_accounted(self):
        r = b.simulate(self.c)
        self.assertGreaterEqual(r.arrived, r.landed + r.dropped)
        self.assertLessEqual(r.peak_queue, self.c.capacity)

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
        self.assertEqual(b.main([DATA, "--capacity", "40"]), 1)
        self.assertEqual(b.main([DATA, "--capacity", "1000"]), 1)

    def test_receipt_and_npc(self):
        c = b.validate(raw())
        rc = b.receipt(c, b.simulate(c), c.capacity)
        self.assertEqual((rc["quest"], rc["capacity"]), (b.QUEST_ID, 140))
        self.assertTrue(b.npc_say(c, "swell").startswith("Cranemaster Odo: "))


if __name__ == "__main__":
    unittest.main()
