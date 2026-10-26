# SPDX-License-Identifier: MIT
"""Tests for G158 Toll Bridge Tokens."""
import dataclasses
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import toll_bridge_tokens as t  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "toll-bridge-tokens-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = t.validate(raw())
        cls.waves = t.harbour_waves(cls.c)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = t.validate(raw())
        self.assertEqual(c.npc_name, "Tollkeeper Bram")
        self.assertEqual((c.gate, c.burst, c.buffer, c.limit, c.window), ("token_bucket", 66, 180, 120, 20))

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["bridge"].update(gate="moat"),
                    lambda d: d["bridge"].update(limit=181),
                    lambda d: d["bridge"].update(burst=0),
                    lambda d: d["bridge"].update(window=True),
                    lambda d: d["bridge"].update(harbour_data="../secret.json"),
                    lambda d: d["bridge"].pop("buffer"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("toll")):
            d = raw()
            mut(d)
            with self.assertRaises(t.TollError):
                t.validate(d)


class GateTest(unittest.TestCase):
    def test_bucket_refills_and_caps(self):
        tb = t.TokenBucket(500, 2)
        self.assertTrue(tb.take() and tb.take())
        self.assertFalse(tb.take())
        tb.tick()
        self.assertFalse(tb.take())
        tb.tick()
        self.assertTrue(tb.take())
        for _ in range(100):
            tb.tick()
        self.assertEqual(tb.level, 2000)

    def test_fixed_window_resets_on_block(self):
        fw = t.FixedWindow(2, 5)
        fw.tick(4)
        self.assertTrue(fw.take() and fw.take())
        self.assertFalse(fw.take())
        fw.tick(5)
        self.assertTrue(fw.take())


class ScienceTest(Base):
    def test_envelope_holds_on_harbour_waves(self):
        for burst in (10, 40, 66, 120):
            s = t.admitted_series(self.c, "token_bucket", burst, self.waves)
            self.assertTrue(t.envelope_ok(s, burst, t.rate_milli(self.c), range(1, 81)), burst)

    def test_envelope_tight_under_saturation(self):
        sat = [10 ** 4] * 200
        for burst in (6, 30, 66):  # a bucket smaller than one tick's drip (6) is capped per tick
            s = t.admitted_series(self.c, "token_bucket", burst, sat)
            for span in (1, 7, 20, 60):
                self.assertEqual(t.max_in_window(s, span), t.envelope(burst, t.rate_milli(self.c), span))
        long_run = sum(t.admitted_series(self.c, "token_bucket", 66, sat)[100:])
        self.assertEqual(long_run, 100 * self.c.limit // self.c.window)  # long-run rate = limit / window

    def test_fixed_window_boundary_double_burst(self):
        w = [0] * 40
        w[19], w[20] = 500, 500  # last tick of block 0 and first tick of block 1
        s = t.admitted_series(self.c, "fixed_window", None, w)
        self.assertEqual(t.max_in_window(s, self.c.window), 2 * self.c.limit)
        self.assertGreater(2 * self.c.limit, self.c.buffer)
        # on the seeded G126 harbour waves the worst fixed-window span also straddles a block edge
        fw = t.admitted_series(self.c, "fixed_window", None, self.waves)
        w = self.c.window
        worst = max(range(w - 1, len(fw)), key=lambda i: sum(fw[i - w + 1:i + 1]))
        start = worst - w + 1
        self.assertGreater(sum(fw[start:worst + 1]), self.c.buffer)
        self.assertNotEqual(start % w, 0)  # not an aligned block: it spans the boundary
        self.assertTrue(all(sum(fw[b:b + w]) <= self.c.limit for b in range(0, len(fw), w)))

    def test_solver_equals_brute_force(self):
        best = t.solve_burst(self.c)
        self.assertEqual(best, self.c.burst)
        self.assertLessEqual(t.envelope(best, t.rate_milli(self.c), self.c.window), self.c.buffer)
        self.assertGreater(t.envelope(best + 1, t.rate_milli(self.c), self.c.window), self.c.buffer)
        sat = [10 ** 4] * 200
        brute = max(b for b in range(6, 200)
                    if t.max_in_window(t.admitted_series(self.c, "token_bucket", b, sat), self.c.window) <= self.c.buffer)
        self.assertEqual(best, brute)
        safe_on_waves = max(b for b in range(40, 100)
                            if t.simulate(self.c, "token_bucket", b, self.waves).reason != t.FAIL_SWAY)
        self.assertEqual(best, safe_on_waves)


class GameTest(Base):
    def test_sized_bucket_wins(self):
        r = t.simulate(self.c, waves=self.waves)
        self.assertEqual(r.status, t.WON)
        self.assertLessEqual(r.worst_window, self.c.buffer)
        self.assertGreaterEqual(r.admitted_permille, self.c.min_admitted_permille)
        self.assertEqual(r.admitted + r.rejected, r.arrived)

    def test_open_and_fixed_window_sway(self):
        for g in ("open", "fixed_window"):
            r = t.simulate(self.c, g, waves=self.waves)
            self.assertEqual((r.status, r.reason), (t.FAILED, t.FAIL_SWAY), g)

    def test_bucket_size_traps(self):
        big = t.simulate(self.c, "token_bucket", 96, self.waves)
        self.assertEqual(big.reason, t.FAIL_SWAY)
        small = t.simulate(self.c, "token_bucket", 30, self.waves)
        self.assertEqual(small.reason, t.FAIL_REJECT)

    def test_g126_waves_read_only(self):
        import breakwater_queue as bq
        path = os.path.join(ROOT, "data", "islands", "disk-saver", "breakwater-queue-v1.json")
        with open(path, "rb") as fh:
            before = fh.read()
        with open(path, encoding="utf-8") as fh:
            hc = bq.validate(json.load(fh))
        self.assertEqual(self.waves, [len(w) for w in bq.arrivals(hc)])
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), before)


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = t.islands_from_shoals(json.load(fh))
        c = t.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_win_and_traps(self):
        self.assertEqual(t.main([DATA]), 0)
        self.assertEqual(t.main([DATA, "--gate", "fixed_window"]), 1)
        self.assertEqual(t.main([DATA, "--burst", "200"]), 1)


if __name__ == "__main__":
    unittest.main()
