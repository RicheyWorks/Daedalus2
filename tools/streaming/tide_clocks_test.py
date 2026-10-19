# SPDX-License-Identifier: MIT
"""Tests for G166 Tide Clocks (wall vs Lamport vs vector clocks, happens-before oracle, G86 tie-in)."""
import copy
import hashlib
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tide_clocks as tc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "tide-clocks-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")
SEEDS = (166, 1, 2, 3, 4)


def load():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def cfg(seed=None, **over):
    raw = load()
    if seed is not None:
        raw["seed"] = seed
    raw["clocks"].update(over)
    return tc.validate(raw)


class ShippedOutcome(unittest.TestCase):
    def test_vector_wins_others_lose_edits(self):
        c = cfg()
        rv, _ = tc.run(c, "vector")
        self.assertEqual((rv.status, rv.lost), (tc.WON, 0))
        for clock in ("wall", "lamport"):
            r, _ = tc.run(c, clock)
            self.assertEqual((r.status, r.reason), (tc.FAILED, tc.FAIL_LOST))
            self.assertGreater(r.lost, 0)
            self.assertEqual(r.detected_conflicts, 0)

    def test_deterministic(self):
        c = cfg()
        a, _ = tc.run(c)
        b, _ = tc.run(c)
        self.assertEqual(tc.receipt(c, a), tc.receipt(c, b))


class Science(unittest.TestCase):
    def test_vc_order_equals_happens_before_oracle(self):
        for s in SEEDS:
            _, vs = tc.run(cfg(s, steps=250), "vector")
            for a in vs:
                for b in vs:
                    self.assertEqual(tc.vc_lt(a.vc, b.vc), tc.happened_before(a, b), (s, a.vid, b.vid))

    def test_lamport_consistent_not_complete(self):
        found_reverse_gap = False
        for s in SEEDS:
            _, vs = tc.run(cfg(s, steps=250), "lamport")
            for a in vs:
                for b in vs:
                    if tc.happened_before(a, b):
                        self.assertLess(a.lamport, b.lamport)
                    elif a.lamport < b.lamport and not tc.happened_before(b, a):
                        found_reverse_gap = True  # L(a) < L(b) yet concurrent
        self.assertTrue(found_reverse_gap)

    def test_vector_detects_exactly_oracle_conflicts_and_loses_nothing(self):
        for s in SEEDS:
            r, _ = tc.run(cfg(s), "vector")
            self.assertEqual(r.detected_pairs, r.oracle_pairs, s)
            self.assertGreater(r.detected_conflicts, 0)
            self.assertEqual(r.lost, 0, s)

    def test_lww_clocks_miss_conflicts_and_lose_edits_on_every_seed(self):
        for s in SEEDS:
            for clock in ("wall", "lamport"):
                r, _ = tc.run(cfg(s), clock)
                self.assertGreater(r.oracle_conflicts, 0)
                self.assertEqual(r.detected_conflicts, 0)
                self.assertGreater(r.lost, 0, (s, clock))

    def test_skew_inverts_causality_on_wall_clock(self):
        total = sum(tc.run(cfg(s, max_skew=10), "wall")[0].causal_inversions for s in SEEDS)
        self.assertGreater(total, 0)
        self.assertEqual(sum(tc.run(cfg(s, max_skew=0), "wall")[0].causal_inversions for s in SEEDS), 0)


class TieIn(unittest.TestCase):
    def test_islands_and_keys_from_g86_read_only(self):
        before = hashlib.sha256(open(SHOALS, "rb").read()).hexdigest()
        with open(SHOALS, encoding="utf-8") as fh:
            ids, kpi = tc.islands_from_shoals(json.load(fh))
        c = cfg()
        self.assertEqual(list(c.islands), ids[:len(c.islands)])
        self.assertLessEqual(len(c.saves), kpi)
        tc.run(c)
        self.assertEqual(hashlib.sha256(open(SHOALS, "rb").read()).hexdigest(), before)


class Validation(unittest.TestCase):
    def test_rejects_bad_configs(self):
        for mut in (lambda r: r.update(v=2), lambda r: r["clocks"].update(clock="sundial"),
                    lambda r: r["clocks"].update(islands=1), lambda r: r["clocks"].update(saves=10 ** 6),
                    lambda r: r["clocks"].update(edit_permille=0), lambda r: r.pop("npc"),
                    lambda r: r["clocks"].update(steps=-1)):
            raw = copy.deepcopy(load())
            mut(raw)
            with self.assertRaises(tc.ClockError):
                tc.validate(raw)


class Cli(unittest.TestCase):
    def test_cli_vector_wins_lamport_fails(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(tc.main([DATA]), 0)
            self.assertEqual(tc.main([DATA, "--clock", "lamport"]), 1)
        self.assertIn("Clockwright Odile", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
