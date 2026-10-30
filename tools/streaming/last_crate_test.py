# SPDX-License-Identifier: MIT
"""Tests for last_crate (G549)."""
import contextlib
import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import last_crate as lc  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "last-crate-v1.json")
CFG = {"budget": {"ram_budget_kib": 40000, "disk_budget_kib": 32768, "warn_permille": 900}}


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 100), (3, 400)]), ("beta", [(4, 10), (5, 1000)]), ("gamma", [(6, 50)])])
HOLD = 70000


class CrateTest(unittest.TestCase):
    def test_crates_use_cost_model(self):
        c = dict(lc.crates(DOC))
        self.assertEqual(len(c), 6)
        self.assertEqual(c["beta:5"], cb.island_cost(1000)[0])
        self.assertEqual(c["alpha:1"], cb.BASE_RAM_KIB)

    def test_stack_is_seeded_permutation(self):
        a, b = lc.stack(DOC, 3), lc.stack(DOC, 3)
        self.assertEqual(a, b)
        self.assertEqual(sorted(a), lc.crates(DOC))
        self.assertGreater(len({json.dumps(lc.stack(DOC, s)) for s in range(12)}), 3)
        moved = census([("gamma", [(6, 50)]), ("beta", [(4, 10), (5, 1000)]), ("alpha", [(1, 0), (2, 100), (3, 400)])])
        self.assertEqual(lc.stack(moved, 3), a)

    def test_advice_matches_enumeration(self):
        for loaded in (0, 20000, 40000, 55000, 69000):
            rem = [w for _, w in lc.crates(DOC)][:4]
            a = lc.advise(loaded, rem, HOLD)
            outcomes = [loaded + w if loaded + w <= HOLD else 0 for w in rem]
            self.assertEqual(Fraction(a["load_value"]), Fraction(sum(outcomes), len(rem)))
            self.assertEqual(Fraction(a["bust_chance"]), Fraction(outcomes.count(0), len(rem)))
            self.assertEqual(a["advice"], "load" if Fraction(sum(outcomes), len(rem)) > loaded else "sail")

    def test_advice_empty_stack(self):
        self.assertEqual(lc.advise(5, [], 10)["advice"], "sail")

    def test_best_stop_brute(self):
        for s in range(10):
            deck = lc.stack(DOC, s)
            want = max(sum(w for _, w in deck[:k]) for k in range(len(deck) + 1)
                       if sum(w for _, w in deck[:k]) <= HOLD)
            self.assertEqual(lc.best_stop(deck, HOLD), want)

    def test_outcomes(self):
        deck = lc.stack(DOC, 0)
        best_k = max(k for k in range(len(deck) + 1) if sum(w for _, w in deck[:k]) <= HOLD)
        full = lc.play(DOC, 0, HOLD, ["load"] * best_k + ["sail"])
        self.assertEqual((full["outcome"], full["carried_kib"]), ("full", full["best_kib"]))
        if best_k:
            light = lc.play(DOC, 0, HOLD, ["load"] * (best_k - 1) + ["sail"])
            self.assertEqual(light["outcome"], "light")
        over = lc.play(DOC, 0, HOLD, ["load"] * (best_k + 1))
        self.assertEqual((over["outcome"], over["carried_kib"]), ("overboard", 0))

    def test_auto_never_busts_when_certain(self):
        for s in range(20):
            r = lc.play(DOC, s, HOLD, auto=True)
            for t in r["turns"]:
                if Fraction(t["advice"]["bust_chance"]) == 1:
                    self.assertEqual(t["move"], "sail")
            self.assertIn(r["outcome"], lc.OUTCOMES)

    def test_auto_beats_never_loading_on_average(self):
        auto = sum(lc.play(DOC, s, HOLD, auto=True)["carried_kib"] for s in range(30))
        one = sum(lc.play(DOC, s, HOLD, ["load", "sail"])["carried_kib"] for s in range(30))
        self.assertGreaterEqual(auto, one)

    def test_bad_moves_refused(self):
        for moves in (["load"], ["jump"], ["sail", "load"], ["load"] * 7 + ["sail"]):
            with self.assertRaises(lc.CrateError, msg=moves):
                lc.play(DOC, 0, 10 ** 7, moves)
        with self.assertRaises(lc.CrateError):
            lc.play(DOC, 0, 0, ["sail"])
        with self.assertRaises(lc.CrateError):
            lc.play(DOC, 0, HOLD)
        with self.assertRaises(lc.CrateError):
            lc.crates(census([("a", [])]))

    def test_hold_defaults_to_budget(self):
        r = lc.play(DOC, 0, None, ["sail"], cfg=CFG)
        self.assertEqual((r["hold_kib"], r["outcome"]), (40000, "light"))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "census.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(lc.main([c, "--auto", "--json", "--hold-kib", str(HOLD)]), 0)
            self.assertEqual(json.loads(out.getvalue())["format"], lc.FORMAT)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(lc.main([c, "--moves", "load, sail"]), 0)
            self.assertTrue(out.getvalue().startswith("last crate: "))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(lc.main([c, "--moves", "fly"]), 2)

    def test_real_census_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            fx = os.path.join("tools", "world_census", "fixtures")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(fx, "alpha.json"),
                            os.path.join(fx, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(fx, "bindings.json"), "--output-dir", os.path.join(d, "out")],
                           cwd=cb.ROOT, check=True, capture_output=True)
            with open(os.path.join(d, "out", "census.json"), encoding="utf-8-sig") as f:
                doc = json.load(f)
        with open(cb.DEFAULT_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        r = lc.play(doc, 0, None, auto=True, cfg=cfg)
        self.assertEqual((r["stack_size"], r["carried_kib"], r["outcome"]), (3, 32768, "full"))

    def test_hook_covers_outcomes(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_last_crate")
        self.assertEqual(h["npc"]["name"], "Dockhand Ambrose")
        self.assertEqual(h["hook"]["values"], list(lc.OUTCOMES))
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
