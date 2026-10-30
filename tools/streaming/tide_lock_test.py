# SPDX-License-Identifier: MIT
"""Tests for tide_lock (G554)."""
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
import tide_lock as tl  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "tide-lock-v1.json")
CFG = {"budget": {"ram_budget_kib": 40000, "disk_budget_kib": 32768, "warn_permille": 900}}
CHAMBER = 60000


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 100), (3, 300)]), ("beta", [(4, 0), (5, 50)]), ("gamma", [(6, 0), (7, 700), (8, 2)])])


def compositions(n):
    for cuts in itertools.product((0, 1), repeat=n - 1):
        sizes, run = [], 1
        for c in cuts:
            if c:
                sizes.append(run)
                run = 1
            else:
                run += 1
        sizes.append(run)
        yield sizes


def brute(queue, chamber, cycle):
    best = None
    for sizes in compositions(len(queue)):
        try:
            w = tl.run_plan(queue, sizes, chamber, cycle)[0]
        except tl.LockError:
            continue
        best = w if best is None else min(best, w)
    return best


class TideLockTest(unittest.TestCase):
    def test_queue_seeded(self):
        q = tl.boats(DOC, 2)
        self.assertEqual(q, tl.boats(DOC, 2))
        self.assertEqual(len(q), 8)
        self.assertEqual([t for *_, t in q], sorted(t for *_, t in q))
        self.assertEqual(dict((l, k) for l, k, _ in q)["gamma:7"], cb.island_cost(700)[0])
        self.assertGreater(len({json.dumps(tl.boats(DOC, s)) for s in range(8)}), 3)

    def test_run_plan_by_hand(self):
        q = [("a", 10, 0), ("b", 10, 5), ("c", 10, 50)]
        w, groups = tl.run_plan(q, [2, 1], 20, 30)
        self.assertEqual((w, [g["leaves"] for g in groups]), (5, [5, 50]))
        w, groups = tl.run_plan(q, [1, 1, 1], 20, 30)
        self.assertEqual((w, [g["leaves"] for g in groups]), (35, [0, 30, 60]))

    def test_optimum_matches_brute(self):
        for s in range(12):
            for chamber, cycle in ((CHAMBER, 30), (40000, 10), (10 ** 6, 45)):
                q = tl.boats(DOC, s)
                cost, plan = tl.optimum(q, chamber, cycle)
                self.assertEqual(cost, brute(q, chamber, cycle), (s, chamber, cycle))
                self.assertEqual(tl.run_plan(q, plan, chamber, cycle)[0], cost)

    def test_optimum_never_worse_than_greedy(self):
        for s in range(15):
            r = tl.puzzle(DOC, s, CHAMBER, 30)
            self.assertLessEqual(r["optimal_wait"], r["greedy_wait"])

    def test_greedy_can_lose(self):
        q = [("a", 10, 0), ("b", 10, 40)]
        self.assertEqual(tl.greedy(q, 20), [2])
        self.assertEqual(tl.run_plan(q, [2], 20, 30)[0], 40)
        self.assertEqual(tl.optimum(q, 20, 30)[0], 0)

    def test_verdicts(self):
        r = tl.puzzle(DOC, 1, CHAMBER, 30, auto=True)
        self.assertEqual(r["verdict"], "smooth")
        self.assertEqual(tl.puzzle(DOC, 1, CHAMBER, 30, plan=[1] * 8)["verdict"] in ("smooth", "slow"), True)
        slow = [s for s in range(15) if tl.puzzle(DOC, s, CHAMBER, 30, plan=[1] * 8)["verdict"] == "slow"]
        self.assertTrue(slow)
        self.assertEqual(tl.puzzle(DOC, 1, CHAMBER, 30, plan=[8])["verdict"], "jammed")
        self.assertEqual(tl.puzzle(DOC, 1, CHAMBER, 30, plan=[1, 1])["verdict"], "jammed")
        self.assertEqual(tl.puzzle(DOC, 1, CHAMBER, 30, plan=[0, 8])["verdict"], "jammed")

    def test_chamber_defaults_to_budget(self):
        r = tl.puzzle(DOC, 0, None, 30, CFG)
        self.assertEqual(r["chamber_kib"], 40000)

    def test_refusals(self):
        with self.assertRaises(tl.LockError):
            tl.puzzle(DOC, 0, 100, 30)
        with self.assertRaises(tl.LockError):
            tl.puzzle(DOC, 0, CHAMBER, 0)
        with self.assertRaises(tl.LockError):
            tl.boats(census([("a", [])]), 0)
        with self.assertRaises(tl.LockError):
            tl.boats({"format": "nope"}, 0)

    def test_deterministic(self):
        self.assertEqual(json.dumps(tl.puzzle(DOC, 3, CHAMBER, 30, auto=True)),
                         json.dumps(tl.puzzle(DOC, 3, CHAMBER, 30, auto=True)))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "census.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(tl.main([c, "--json", "--chamber-kib", str(CHAMBER)]), 0)
            r = json.loads(out.getvalue())
            self.assertNotIn("verdict", r)
            self.assertNotIn("optimal_plan", r)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(tl.main([c, "--auto", "--chamber-kib", str(CHAMBER)]), 0)
            self.assertTrue(out.getvalue().startswith("tide lock: smooth"))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(tl.main([c, "--plan", "a,b", "--chamber-kib", str(CHAMBER)]), 2)

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
        r = tl.puzzle(doc, 0, None, 30, cfg, auto=True)
        self.assertEqual((len(r["queue"]), r["optimal_wait"], r["greedy_wait"], r["verdict"]), (3, 12, 40, "smooth"))

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_tide_lock")
        self.assertEqual(h["npc"]["name"], "Lockkeeper Wilhelmina")
        self.assertEqual(h["hook"]["values"], list(tl.VERDICTS))
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
