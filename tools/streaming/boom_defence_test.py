# SPDX-License-Identifier: MIT
"""Tests for boom_defence (G562)."""
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
import boom_defence as bd  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "boom-defence-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2), (6, 5)])])
ONE = census([("solo", [(1, 4)])])


def my_sim(path, hulls, posts):
    """Independent simulator: event list per tick with dicts, own reach test."""
    skiffs = {i: {"pos": -1, "hp": h, "out": False} for i, h in enumerate(hulls)}
    through = 0
    t = 0
    while any(not s["out"] for s in skiffs.values()):
        for i, s in skiffs.items():
            if not s["out"] and s["pos"] >= 0:
                s["pos"] += 1
                if s["pos"] == len(path):
                    s["out"] = True
                    through += 1
        if t % 2 == 0 and t // 2 in skiffs:
            skiffs[t // 2]["pos"] = 0
        for pr, pc in posts:
            cand = [(s["pos"], -i, i) for i, s in skiffs.items() if not s["out"] and s["pos"] >= 0
                    and (pr, pc) != path[s["pos"]] and abs(pr - path[s["pos"]][0]) <= 1
                    and abs(pc - path[s["pos"]][1]) <= 1]
            if cand:
                j = max(cand)[2]
                skiffs[j]["hp"] -= 1
                if skiffs[j]["hp"] == 0:
                    skiffs[j]["out"] = True
        t += 1
    return through


class BoomDefenceTest(unittest.TestCase):
    def test_simulator_matches_independent(self):
        for doc in (DOC, ONE):
            for seed in range(6):
                c = bd.chart(doc, seed)
                for combo in itertools.combinations(c["sites"], 2):
                    self.assertEqual(bd.simulate(c["path"], c["hulls"], list(combo))[0],
                                     my_sim(c["path"], c["hulls"], list(combo)))

    def test_par_is_exhaustive_minimum(self):
        for seed in range(6):
            c = bd.chart(DOC, seed)
            want = min(my_sim(c["path"], c["hulls"], list(p)) for p in itertools.combinations(c["sites"], 2))
            self.assertEqual(bd.best(c)[0], want)

    def test_greedy_never_beats_par_and_sometimes_loses(self):
        lost = False
        for seed in range(40):
            c = bd.chart(DOC, seed)
            p, g = bd.best(c)[0], bd.greedy(c)[0]
            self.assertGreaterEqual(g, p)
            lost |= g > p
        self.assertTrue(lost)

    def test_hand_channel(self):
        path = [(1, c) for c in range(5)]
        self.assertEqual(bd.simulate(path, [1], [])[0], 1)
        # a post beside the middle cell reaches three channel cells: a 3-hull skiff sinks
        self.assertEqual(bd.simulate(path, [3], [(0, 2)]), (0, ["sunk"]))
        self.assertEqual(bd.simulate(path, [4], [(0, 2)]), (1, ["through"]))

    def test_chart_shape(self):
        c = bd.chart(DOC, 3)
        self.assertEqual(c["path"][0][1], 0)
        self.assertEqual(c["path"][-1][1], bd.COLS - 1)
        self.assertEqual(len(set(c["path"])), len(c["path"]))
        for a, b in zip(c["path"], c["path"][1:]):
            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)
        self.assertTrue(all(any(bd.reach(s, p) for p in c["path"]) for s in c["sites"]))
        self.assertLessEqual(len(c["sites"]), bd.MAX_SITES)

    def test_auto_is_watertight(self):
        for seed in range(6):
            r = bd.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "watertight")
            self.assertEqual(r["through"], r["par"])

    def test_no_posts_is_overrun(self):
        r = bd.play(DOC, 1, posts="")
        self.assertEqual(r["verdict"], "overrun")
        self.assertEqual(r["through"], 6)

    def test_leaky_found(self):
        for seed in range(20):
            c = bd.chart(DOC, seed)
            par = bd.best(c)[0]
            for i in range(len(c["sites"])):
                r = bd.play(DOC, seed, posts="ABCDEFGHIJKL"[i])
                if r["verdict"] == "leaky":
                    self.assertGreater(r["through"], par)
                    return
        self.fail("no leaky single post found")

    def test_refusals(self):
        for bad in ("Z", "A,A", "A,B,C", "AB"):
            with self.assertRaises(bd.BoomError):
                bd.play(DOC, 0, posts=bad)
        with self.assertRaises(bd.BoomError):
            bd.chart(census([]))

    def test_deterministic_and_capped(self):
        self.assertEqual(bd.chart(DOC, 4), bd.chart(DOC, 4))
        self.assertTrue(any(bd.chart(DOC, 0) != bd.chart(DOC, s) for s in range(1, 6)))
        big = census([("w", [(i, i) for i in range(9)])])
        self.assertEqual(len(bd.chart(big, 0)["skiffs"]), bd.MAX_SKIFFS)
        self.assertEqual(bd.chart(ONE, 0)["skiffs"], ["solo:1"])

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
                self.assertEqual(bd.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "watertight")
            self.assertEqual(r["skiffs"], ["alpha:2", "alpha:9", "beta:4"])
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(bd.main([path, "--posts", "Q"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_boom_defence")
        self.assertEqual(h["hook"]["report_format"], bd.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), bd.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(bd.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Leopold"))


if __name__ == "__main__":
    unittest.main()
