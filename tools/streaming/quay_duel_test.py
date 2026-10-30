# SPDX-License-Identifier: MIT
"""Tests for quay_duel (G550)."""
import contextlib
import functools
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import quay_duel as qd  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "quay-duel-v1.json")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 700), (3, 40)]), ("beta", [(4, 900), (5, 3)]), ("gamma", [(6, 250), (7, 5)])])


def minimax(values):
    @functools.lru_cache(maxsize=None)
    def go(i, j):
        if i > j:
            return 0
        return max(values[i] - go(i + 1, j), values[j] - go(i, j - 1))
    return go(0, len(values) - 1)


class DuelTest(unittest.TestCase):
    def test_dp_matches_minimax(self):
        rng = random.Random(5)
        for _ in range(200):
            v = [rng.randint(0, 50) for _ in range(rng.randint(1, 9))]
            self.assertEqual(qd.margins(v)[0][len(v) - 1], minimax(tuple(v)), v)

    def test_quay_seeded_and_order_free(self):
        a = qd.quay(DOC, 4)
        self.assertEqual(a, qd.quay(DOC, 4))
        self.assertEqual(len(a), 7)
        self.assertEqual(dict(a)["beta:4"], cb.island_cost(900)[0])
        moved = census([("gamma", [(6, 250), (7, 5)]), ("alpha", [(1, 0), (2, 700), (3, 40)]), ("beta", [(4, 900), (5, 3)])])
        self.assertEqual(qd.quay(moved, 4), a)
        self.assertGreater(len({json.dumps(qd.quay(DOC, s)) for s in range(10)}), 3)

    def test_auto_reaches_best_margin(self):
        for s in range(15):
            for second in (False, True):
                r = qd.duel(DOC, s, auto=True, second=second)
                self.assertEqual(r["margin_kib"], r["best_margin_kib"])
                self.assertTrue(r["perfect"])
                self.assertEqual(r["you_kib"] + r["casimir_kib"], sum(v for _, v in qd.quay(DOC, s)))

    def test_casimir_never_does_worse_than_dp(self):
        rng = random.Random(9)
        for s in range(15):
            n = len(qd.quay(DOC, s))
            moves = [rng.choice("LR") for _ in range((n + 1) // 2)]
            r = qd.duel(DOC, s, moves)
            self.assertLessEqual(r["margin_kib"], r["best_margin_kib"])
            self.assertEqual(r["best_margin_kib"] - r["margin_kib"], r["gave_away_kib"])
            self.assertEqual(r["perfect"], r["gave_away_kib"] == 0)

    def test_even_opener_never_loses(self):
        even = census([("a", [(i, (i * 37) % 11) for i in range(8)])])
        for s in range(10):
            r = qd.duel(even, s, auto=True)
            self.assertTrue(r["opener_cannot_lose"])
            self.assertGreaterEqual(r["best_margin_kib"], 0)

    def test_outcomes(self):
        one = census([("a", [(1, 0)])])
        self.assertEqual(qd.duel(one, 0, ["L"])["outcome"], "won")
        self.assertEqual(qd.duel(one, 0, [], second=True)["outcome"], "lost")
        two = census([("a", [(1, 0), (2, 0)])])
        self.assertEqual(qd.duel(two, 0, ["R"])["outcome"], "tied")

    def test_turn_log(self):
        r = qd.duel(DOC, 1, auto=True)
        self.assertEqual([t["turn"] for t in r["turns"]], list(range(1, 8)))
        self.assertEqual([t["captain"] for t in r["turns"][:3]], ["you", "casimir", "you"])
        self.assertEqual(sorted(t["crate"] for t in r["turns"]), sorted(r["quay"]))

    def test_bad_moves_refused(self):
        for moves in ([], ["L"] * 5, ["X", "L", "L", "L"]):
            with self.assertRaises(qd.DuelError, msg=moves):
                qd.duel(DOC, 0, moves)
        with self.assertRaises(qd.DuelError):
            qd.duel(DOC, 0)
        with self.assertRaises(qd.DuelError):
            qd.quay(census([("a", [])]), 0)
        with self.assertRaises(qd.DuelError):
            qd.quay({"format": "nope"}, 0)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "census.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(qd.main([c, "--auto", "--json", "--second"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual((r["format"], r["you_open"]), (qd.FORMAT, False))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(qd.main([c, "--moves", "l, r, l, r"]), 0)
            self.assertTrue(out.getvalue().startswith("quay duel: "))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(qd.main([c, "--moves", "L"]), 2)

    def test_deterministic(self):
        self.assertEqual(json.dumps(qd.duel(DOC, 3, auto=True)), json.dumps(qd.duel(DOC, 3, auto=True)))

    def test_real_census_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            fx = os.path.join("tools", "world_census", "fixtures")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(fx, "alpha.json"),
                            os.path.join(fx, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(fx, "bindings.json"), "--output-dir", os.path.join(d, "out")],
                           cwd=cb.ROOT, check=True, capture_output=True)
            with open(os.path.join(d, "out", "census.json"), encoding="utf-8-sig") as f:
                doc = json.load(f)
        r = qd.duel(doc, 0, auto=True)
        self.assertEqual((r["crates"], r["you_kib"], r["casimir_kib"], r["outcome"]), (3, 32792, 16384, "won"))

    def test_hook_covers_outcomes(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_quay_duel")
        self.assertEqual(h["npc"]["name"], "Wharfinger Casimir")
        self.assertEqual(h["hook"]["values"], list(qd.OUTCOMES))
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
