# SPDX-License-Identifier: MIT
"""Tests for rope_run (G564)."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import rope_run as rr  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "rope-run-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2)])])
ONE = census([("solo", [(1, 4)])])


def oracle(grip, start, dock):
    """Independent: recursive best over frozensets of used squares, no route tracking."""
    def best(cell, used):
        if cell == dock:
            return grip[cell]
        out = None
        r, c = cell
        for n in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if n in grip and n not in used:
                v = best(n, used | {n})
                if v is not None and (out is None or v > out):
                    out = v
        return None if out is None else out + grip[cell]
    return best(start, frozenset([start]))


class RopeRunTest(unittest.TestCase):
    def test_par_matches_oracle(self):
        for doc in (DOC, ONE):
            for seed in range(5):
                q = rr.quay(doc, seed)
                self.assertEqual(q["par"], oracle(q["grip"], q["start"], q["dock"]), seed)

    def test_route_scores_par(self):
        for seed in range(5):
            q = rr.quay(DOC, seed)
            r = rr.play(DOC, seed, route=q["route"])
            self.assertEqual(r["grip"], q["par"])

    def test_hand_grid(self):
        grip = {(0, 0): 1, (0, 1): 1, (0, 2): 1, (1, 0): 1, (1, 1): 5, (1, 2): 1}
        self.assertEqual(rr.solve(grip, (0, 0), (0, 2))[0], 9)  # every square, through the 5
        self.assertEqual(oracle(grip, (0, 0), (0, 2)), 9)
        self.assertEqual(rr.solve({(0, 0): 1, (0, 2): 1}, (0, 0), (0, 2)), (None, None))

    def test_greedy_never_beats_par_and_sometimes_loses(self):
        lost = False
        for seed in range(20):
            q = rr.quay(DOC, seed)
            g = rr.greedy(q["grip"], q["start"], q["dock"])
            self.assertLessEqual(g, q["par"])
            lost |= g < q["par"]
        self.assertTrue(lost)

    def test_auto_is_taut(self):
        for seed in range(5):
            r = rr.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "taut")
            self.assertTrue(r["on_dock"])

    def test_short_rope_is_loose(self):
        q = rr.quay(DOC, 1)
        r = rr.play(DOC, 1, route=q["route"][:-1])
        self.assertEqual(r["verdict"], "loose")
        self.assertEqual(rr.play(DOC, 1, route="")["verdict"], "loose")

    def test_slack_found(self):
        for seed in range(20):
            q = rr.quay(DOC, seed)
            if rr.greedy(q["grip"], q["start"], q["dock"]) not in (0, q["par"]):
                cell, seen, route = q["start"], {q["start"]}, ""
                while cell != q["dock"]:
                    opts = [(q["grip"][n], -"NSEW".index(d), d, n)
                            for d, n in rr.neighbours(cell, set(q["grip"])) if n not in seen]
                    _, _, d, cell = max(opts)
                    seen.add(cell)
                    route += d
                self.assertEqual(rr.play(DOC, seed, route=route)["verdict"], "slack")
                return
        self.fail("no slack case")

    def test_refusals(self):
        q = rr.quay(DOC, 0)
        with self.assertRaises(rr.RopeError):
            rr.play(DOC, 0, route="X")
        with self.assertRaises(rr.RopeError):
            rr.play(DOC, 0, route=q["route"] + "N")
        first = q["route"][0]
        back = {"N": "S", "S": "N", "E": "W", "W": "E"}[first]
        with self.assertRaises(rr.RopeError):
            rr.play(DOC, 0, route=first + back)
        with self.assertRaises(rr.RopeError):
            rr.play(DOC, 0, route="N" * 6)
        with self.assertRaises(rr.RopeError):
            rr.quay(census([]))

    def test_cleat_values(self):
        q = rr.quay(DOC, 2)
        self.assertEqual([q["grip"][p] for p in q["cleats"]], [3, 4, 3, 3, 5])
        self.assertTrue(all(v == 1 for p, v in q["grip"].items() if p not in q["cleats"]))

    def test_deterministic_and_seeded(self):
        self.assertEqual(rr.play(DOC, 3)["chart"], rr.play(DOC, 3)["chart"])
        self.assertTrue(any(rr.play(DOC, 0)["chart"] != rr.play(DOC, s)["chart"] for s in range(1, 6)))
        self.assertEqual(len(rr.play(DOC, 0)["chart"]), rr.ROWS)

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
                self.assertEqual(rr.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "taut")
            self.assertEqual(r["cleats"], ["alpha:2", "alpha:9", "beta:4"])
            self.assertGreater(r["par"], r["greedy_grip"])
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(rr.main([path, "--route", "Q"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_rope_run")
        self.assertEqual(h["hook"]["report_format"], rr.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), rr.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(rr.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Theodora"))


if __name__ == "__main__":
    unittest.main()
