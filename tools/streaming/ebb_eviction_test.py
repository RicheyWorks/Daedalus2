# SPDX-License-Identifier: MIT
"""Tests for Ebb Tide Eviction (G253): exact DP = brute-force oracle, greedy gaps, seeded replay, golden."""
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402
import ebb_eviction as ee  # noqa: E402

GOLDEN = os.path.join(HERE, "ebb_eviction_golden.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")


def real_report(budget_kib=None):
    """Real pipeline: world_census CLI on its own fixtures -> census_budget plan (read-only)."""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, "-B", "-m", "tools.world_census",
                        os.path.join(FIX, "alpha.json"), os.path.join(FIX, "beta.json"),
                        "--snapshot-date", "2026-10-26", "--bindings", os.path.join(FIX, "bindings.json"),
                        "--output-dir", os.path.join(d, "census")], cwd=ROOT, check=True, capture_output=True)
        with open(os.path.join(d, "census", "census.json"), encoding="utf-8") as f:
            census = json.load(f)
    with open(cb.DEFAULT_CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    if budget_kib is not None:
        cfg["budget"]["ram_budget_kib"] = budget_kib
    return cb.plan(census, cfg)


def report(budget, worlds):
    return {"format": "daedalus-census-budget", "version": 1, "budget": {"ram_budget_kib": budget},
            "worlds": [{"id": w, "islands": [{"slot": s, "ram_kib": r} for s, r in isl]} for w, isl in worlds]}


CFG = {"v": 1, "pinned_slots": [0], "default_weight": 1}


def rand_items(rng, n):
    return [(s, rng.randint(1, 60), rng.randint(1, 5)) for s in range(1, n + 1)]


class EbbEvictionTest(unittest.TestCase):
    def test_dp_equals_brute_force_oracle(self):
        rng = random.Random(251)
        for _ in range(400):
            items = rand_items(rng, rng.randint(0, 9))
            need = rng.randint(-5, sum(r for _, r, _ in items) + 5)
            got = ee.solve(items, need)
            want = ee.solve_oracle(items, need)
            self.assertEqual(None if got is None else got[:2], want if need > 0 else (0, 0))

    def test_plan_slots_are_valid(self):
        rng = random.Random(7)
        for _ in range(200):
            items = rand_items(rng, rng.randint(1, 8))
            need = rng.randint(1, sum(r for _, r, _ in items))
            w, c, slots = ee.solve(items, need)
            by = {s: (r, wt) for s, r, wt in items}
            self.assertGreaterEqual(sum(by[s][0] for s in slots), need)
            self.assertEqual(sum(by[s][1] for s in slots), w)
            self.assertEqual(len(slots), c)

    def test_greedy_never_beats_optimal(self):
        rng = random.Random(9)
        for _ in range(300):
            items = rand_items(rng, rng.randint(1, 8))
            need = rng.randint(1, sum(r for _, r, _ in items))
            opt = ee.solve(items, need)
            for key in (ee.HEAVIEST_FIRST, ee.LIGHTEST_WEIGHT_FIRST):
                self.assertGreaterEqual(ee.greedy(items, need, key)[:2], opt[:2])

    def test_greedy_counterexamples_pinned(self):
        # heaviest-first unloads the precious capital; lowest-weight-first unloads three rocks
        items = [(1, 50, 9), (2, 20, 1), (3, 20, 1), (4, 15, 2)]
        self.assertEqual(ee.solve(items, 40), (2, 2, [2, 3]))
        self.assertEqual(ee.greedy(items, 40, ee.HEAVIEST_FIRST), (9, 1, [1]))
        items2 = [(1, 10, 1), (2, 10, 1), (3, 10, 1), (4, 30, 2)]
        self.assertEqual(ee.solve(items2, 30), (2, 1, [4]))
        self.assertEqual(ee.greedy(items2, 30, ee.LIGHTEST_WEIGHT_FIRST), (3, 3, [1, 2, 3]))

    def test_budget_edges_exact(self):
        items = [(1, 10, 1)]
        self.assertEqual(ee.solve(items, 0), (0, 0, []))
        self.assertEqual(ee.solve(items, 10), (1, 1, [1]))
        self.assertIsNone(ee.solve(items, 11))
        p = ee.plan(report(30, [("w", [(0, 10), (1, 20)])]), CFG)
        self.assertEqual(p["worlds"][0]["tide"], "slack")
        p = ee.plan(report(29, [("w", [(0, 10), (1, 20)])]), CFG)
        self.assertEqual(p["worlds"][0]["optimal"], {"weight": 1, "count": 1, "unload_slots": [1]})

    def test_pinned_never_unloaded_and_stranded(self):
        p = ee.plan(report(5, [("w", [(0, 10), (1, 20)])]), CFG)
        w = p["worlds"][0]
        self.assertEqual(w["tide"], "stranded")
        self.assertIsNone(w["optimal"])
        self.assertEqual(p["summary"]["cannot_fit"], 1)
        rng = random.Random(3)
        for _ in range(100):
            isl = [(s, rng.randint(1, 50)) for s in range(rng.randint(1, 7))]
            p = ee.plan(report(rng.randint(1, 150), [("w", isl)]), CFG)
            o = p["worlds"][0]["optimal"]
            if o:
                self.assertNotIn(0, o["unload_slots"])

    def test_weights_from_config(self):
        cfg = dict(CFG, weights={"w": {"1": 5}})
        p = ee.plan(report(25, [("w", [(0, 5), (1, 20), (2, 10), (3, 10)])]), cfg)
        self.assertEqual(p["worlds"][0]["optimal"]["unload_slots"], [2, 3])

    def test_seeded_replay_determinism(self):
        def run(seed):
            rng = random.Random(seed)
            worlds = [(f"w{k}", [(s, rng.randint(100, 9000)) for s in range(rng.randint(1, 9))]) for k in range(5)]
            return ee.dumps(ee.plan(report(rng.randint(5000, 30000), worlds), CFG))
        self.assertEqual(run(42), run(42))
        self.assertNotEqual(run(42), run(43))

    def test_order_independent(self):
        isl = [(0, 9), (3, 40), (1, 25), (2, 30)]
        a = ee.plan(report(60, [("b", isl), ("a", isl[::-1])]), CFG)
        b = ee.plan(report(60, [("a", isl), ("b", isl[::-1])]), CFG)
        self.assertEqual(ee.dumps(a), ee.dumps(b))

    def test_oracle_limit(self):
        with self.assertRaises(ee.EvictionError):
            ee.solve_oracle([(s, 1, 1) for s in range(ee.ORACLE_LIMIT + 1)], 1)

    def test_refusals(self):
        bad = [{"format": "x"}, {"format": "daedalus-census-budget", "version": 2},
               report(1, [("w", [(0, 1), (0, 2)])]), report(1, [("w", [(0, -1)])]),
               report(1, [("w", []), ("w", [])])]
        for doc in bad:
            with self.assertRaises(ee.EvictionError):
                ee.plan(doc, CFG)
        for cfg in [{"v": 2}, dict(CFG, default_weight=0), dict(CFG, weights={"w": {"x": 1}}),
                    dict(CFG, pinned_slots=[True])]:
            with self.assertRaises(ee.EvictionError):
                ee.plan(report(1, [("w", [(0, 1)])]), cfg)

    def test_golden_fixture_from_real_census(self):
        with open(ee.DEFAULT_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        got = ee.dumps(ee.plan(real_report(budget_kib=20000), cfg))
        with open(GOLDEN, encoding="utf-8") as f:
            self.assertEqual(got, f.read())

    def test_config_hook_shape(self):
        with open(ee.DEFAULT_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        ee.load_config(cfg)
        self.assertEqual(cfg["quest"], "q_ebb_eviction")
        self.assertEqual(cfg["hook"]["report_format"], ee.FORMAT)
        self.assertEqual(set(cfg["npc"]["lines"]), {"slack", "ebb", "stranded"})
        with open(ee.DEFAULT_CONFIG, "rb") as f:
            self.assertFalse(f.read(3) == b"\xef\xbb\xbf")

    def test_cli_writes_new_file_and_strict(self):
        with tempfile.TemporaryDirectory() as d:
            rp, out = os.path.join(d, "r.json"), os.path.join(d, "p.json")
            with open(rp, "w", encoding="utf-8") as f:
                json.dump(report(5, [("w", [(0, 10), (1, 20)])]), f)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(ee.main([rp, "-o", out]), 0)
                self.assertEqual(ee.main([rp, "--strict"]), 1)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(ee.main([rp, "-o", out]), 2)  # never overwrites
            with open(out, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["format"], ee.FORMAT)


if __name__ == "__main__":
    unittest.main()
