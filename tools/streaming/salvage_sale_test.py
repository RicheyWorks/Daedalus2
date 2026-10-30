# SPDX-License-Identifier: MIT
"""Tests for salvage_sale (G563)."""
import contextlib
import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import salvage_sale as ss  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "salvage-sale-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2), (6, 5)])])
ONE = census([("solo", [(1, 4)])])


def brute(values, coin):
    """Independent: every win/pass plan, simulated with its own rival rule."""
    best = 0
    for plan in itertools.product((0, 1), repeat=len(values)):
        mine, theirs, lost, score, ok = coin, coin, 0, 0, True
        for v, want in zip(values, plan):
            rb = min(theirs, v // 2 + 3 * lost)
            if want:
                if rb + 1 > mine:
                    ok = False
                    break
                mine -= rb + 1
                score += v
                lost += 1
            else:
                theirs -= rb
        if ok:
            best = max(best, score)
    return best


class SalvageSaleTest(unittest.TestCase):
    def test_par_matches_brute(self):
        for doc in (DOC, ONE):
            for seed in range(15):
                lots, values, coin = ss.sale(doc, seed)
                self.assertEqual(ss.solve(values, coin)[0], brute(values, coin), seed)

    def test_par_matches_brute_on_hand_values(self):
        for values in ([4, 4, 4, 4, 4], [9, 3, 8, 3, 7], [3, 11, 3, 11, 3, 11], [7, 7, 7, 7, 7, 7]):
            for coin in (5, 10, sum(values) // 3):
                self.assertEqual(ss.solve(values, coin)[0], brute(values, coin))

    def test_overbidding_never_helps(self):
        for seed in range(5):
            lots, values, coin = ss.sale(DOC, seed)
            par = ss.solve(values, coin)[0]
            for bids in itertools.product(range(0, 9, 2), repeat=len(values)):
                try:
                    s, _ = ss.run(values, coin, list(bids))
                except ss.SaleError:
                    continue
                self.assertLessEqual(s, par)

    def test_broker_rule(self):
        self.assertEqual(ss.broker_bid(9, 20, 0), 4)
        self.assertEqual(ss.broker_bid(9, 20, 3), 13)
        self.assertEqual(ss.broker_bid(9, 3, 3), 3)
        s, log = ss.run([8, 8], 10, [4, 5])
        self.assertEqual([e["winner"] for e in log], ["broker", "you"])

    def test_greedy_never_beats_par_and_sometimes_loses(self):
        lost = False
        for seed in range(40):
            lots, values, coin = ss.sale(DOC, seed)
            p, g = ss.solve(values, coin)[0], ss.greedy(values, coin)
            self.assertLessEqual(g, p)
            lost |= g < p
        self.assertTrue(lost)

    def test_auto_is_shrewd(self):
        for seed in range(6):
            r = ss.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "shrewd")
            self.assertEqual(r["score"], r["par"])

    def test_pass_everything_is_fleeced(self):
        r = ss.play(DOC, 1, bids=",".join(["0"] * 6))
        self.assertEqual(r["score"], 0)
        self.assertEqual(r["verdict"], "fleeced")

    def test_fair_band(self):
        for seed in range(30):
            lots, values, coin = ss.sale(DOC, seed)
            par = ss.solve(values, coin)[0]
            if ss.greedy(values, coin) < par and 2 * ss.greedy(values, coin) >= par:
                mine, theirs, lost, bids = coin, coin, 0, []
                for v in values:
                    rb = ss.broker_bid(v, theirs, lost)
                    if rb + 1 <= mine:
                        bids.append(rb + 1)
                        mine -= rb + 1
                        lost += 1
                    else:
                        bids.append(0)
                        theirs -= rb
                r = ss.play(DOC, seed, bids=",".join(map(str, bids)))
                self.assertEqual(r["verdict"], "fair")
                return
        self.fail("no fair case")

    def test_refusals(self):
        lots, values, coin = ss.sale(DOC, 0)
        for bad in ("1,2", "a,b,c,d,e,f", ",".join([str(coin + 1)] + ["0"] * 5)):
            with self.assertRaises(ss.SaleError):
                ss.play(DOC, 0, bids=bad)
        with self.assertRaises(ss.SaleError):
            ss.sale(census([]))

    def test_padding_and_determinism(self):
        lots, values, coin = ss.sale(ONE, 2)
        self.assertEqual(lots, ["solo:1", "spare:1", "spare:2", "spare:3", "spare:4"])
        self.assertTrue(all(3 <= v <= 11 for v in values))
        self.assertEqual(coin, sum(values) // 3)
        self.assertEqual(ss.sale(DOC, 3), ss.sale(DOC, 3))
        self.assertTrue(any(ss.sale(DOC, 0) != ss.sale(DOC, s) for s in range(1, 6)))

    def test_real_fixtures_cli(self):
        with tempfile.TemporaryDirectory() as t:
            out_dir = os.path.join(t, "c")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(FIX, "alpha.json"),
                            os.path.join(FIX, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(FIX, "bindings.json"), "--output-dir", out_dir], cwd=cb.ROOT, check=True,
                           capture_output=True)
            path = os.path.join(out_dir, "census.json")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(ss.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "shrewd")
            self.assertEqual(r["lots"][:3], ["alpha:2", "alpha:9", "beta:4"])
            self.assertGreater(r["par"], r["greedy_value"])
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(ss.main([path, "--bids", "1"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_salvage_sale")
        self.assertEqual(h["hook"]["report_format"], ss.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), ss.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(ss.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Barnaby"))


if __name__ == "__main__":
    unittest.main()
