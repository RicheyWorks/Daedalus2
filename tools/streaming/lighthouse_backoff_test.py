# SPDX-License-Identifier: MIT
"""Tests for G134 Lighthouse Backoff."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import lighthouse_backoff as b  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "lighthouse-backoff-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = b.validate(raw())
        self.assertEqual(c.npc_name, "Keeper Wren")
        self.assertEqual((c.policy, c.capacity, c.outage), ("full_jitter", 20, 30))
        self.assertEqual(len(b.boats(c)), 300)

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["lighthouse"].update(capacity=0),
                    lambda d: d["lighthouse"].update(policy="random"),
                    lambda d: d["lighthouse"].update(cap=0),
                    lambda d: d["lighthouse"].update(writes_per_island=201),
                    lambda d: d["lighthouse"].update(base=True),
                    lambda d: d["lighthouse"].pop("deadline"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("lit")):
            d = raw()
            mut(d)
            with self.assertRaises(b.LighthouseError):
                b.validate(d)


class DelayTest(unittest.TestCase):
    def test_fixed_and_expo(self):
        rng = b.Lcg(1)
        self.assertEqual([b.delay("fixed", a, 2, 64, rng) for a in range(4)], [2, 2, 2, 2])
        self.assertEqual([b.delay("expo", a, 1, 16, rng) for a in range(7)], [1, 2, 4, 8, 16, 16, 16])

    def test_full_jitter_in_range(self):
        rng = b.Lcg(7)
        for a in range(12):
            span = min(64, 1 << a)
            for _ in range(50):
                d = b.delay("full_jitter", a, 1, 64, rng)
                self.assertTrue(1 <= d <= span, (a, d))
        with self.assertRaises(b.LighthouseError):
            b.delay("nope", 0, 1, 2, rng)


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = b.validate(raw())

    def test_full_jitter_wins(self):
        r = b.simulate(self.c, "full_jitter")
        self.assertEqual(r.status, b.WON)
        self.assertEqual(r.berthed, r.writes)
        self.assertLessEqual(r.retries, self.c.max_retries)
        self.assertLessEqual(r.last_berth, self.c.deadline)

    def test_fixed_retry_storm(self):
        r = b.simulate(self.c, "fixed")
        self.assertEqual((r.status, r.reason), (b.FAILED, b.FAIL_RETRIES))
        self.assertEqual(r.berthed, r.writes)  # lands fast but floods the sea

    def test_expo_without_jitter_herds(self):
        r = b.simulate(self.c, "expo")
        self.assertEqual((r.status, r.reason), (b.FAILED, b.FAIL_LATE))
        self.assertEqual(r.peak_wave, r.writes)  # the whole fleet in lockstep

    def test_jitter_wins_across_seeds(self):
        for seed in range(1, 6):
            d = raw()
            d["seed"] = seed
            self.assertEqual(b.simulate(b.validate(d), "full_jitter").status, b.WON, seed)

    def test_dark_lighthouse_berths_nothing(self):
        d = raw()
        d["lighthouse"]["outage"] = 10_000
        r = b.simulate(b.validate(d), "full_jitter")
        self.assertEqual((r.berthed, r.reason), (0, b.FAIL_LATE))

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
        self.assertEqual(b.main([DATA, "--policy", "fixed"]), 1)
        self.assertEqual(b.main([DATA, "--policy", "expo"]), 1)

    def test_receipt_and_npc(self):
        c = b.validate(raw())
        rc = b.receipt(c, b.simulate(c), c.policy)
        self.assertEqual((rc["quest"], rc["policy"], rc["writes"]), (b.QUEST_ID, "full_jitter", 300))
        self.assertTrue(b.npc_say(c, "dark").startswith("Keeper Wren: "))


if __name__ == "__main__":
    unittest.main()
