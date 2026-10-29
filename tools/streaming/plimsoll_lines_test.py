# SPDX-License-Identifier: MIT
"""Tests for Plimsoll Lines (G522): headroom = brute-force oracle, cargo verdicts, real census, CLI."""
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
import plimsoll_lines as pl  # noqa: E402

HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "plimsoll-lines-v1.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")


def cfg():
    with open(cb.DEFAULT_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def census(worlds):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in sorted(isl.items())]}
                       for w, isl in sorted(worlds.items())]}


def lines(worlds, adds=()):
    return pl.build(pl.to_report(census(worlds), cfg()), list(adds))


def oracle_island(n, rb=40000, db=32768, warn=900):
    """Scan k = 0, 1, ... with the real G206 beacon until the colour changes."""
    def colour(k):
        m = n + k
        return cb.beacon(16384 + 24 * m, 4096 + 96 * m, rb, db, warn)[1]
    k = 0
    while colour(k) == "green":
        k += 1
    to_amber = k
    while colour(k) != "red":
        k += 1
    return to_amber, k


def oracle_spill(isl, rb=40000, db=32768):
    k = 0
    while True:
        tr = sum(16384 + 24 * n for n in isl.values()) + 24 * k
        td = sum(4096 + 96 * n for n in isl.values()) + 96 * k
        if not (tr <= rb and td <= db):
            return k
        k += 1


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = pl.main(list(args))
    return code, out.getvalue(), err.getvalue()


class PlimsollTest(unittest.TestCase):
    def test_island_lines_equal_oracle_every_n(self):
        for n in range(0, 330):
            self.assertEqual(pl.island_lines(16384 + 24 * n, 4096 + 96 * n, 40000, 32768, 900), oracle_island(n), n)

    def test_island_lines_random_budgets(self):
        rng = random.Random(522)
        for _ in range(300):
            rb, db, warn = rng.randrange(17000, 60000), rng.randrange(5000, 50000), rng.randrange(500, 1000)
            n = rng.randrange(0, 200)
            self.assertEqual(pl.island_lines(16384 + 24 * n, 4096 + 96 * n, rb, db, warn), oracle_island(n, rb, db, warn))

    def test_world_spill_equals_oracle(self):
        rng = random.Random(5220)
        for _ in range(200):
            isl = {s: rng.randrange(0, 150) for s in rng.sample(range(6), rng.randrange(1, 3))}
            w = lines({"w": isl})["worlds"][0]
            self.assertEqual(w["to_spill"], oracle_spill(isl))
            self.assertTrue(all(i["to_spill"] == w["to_spill"] for i in w["islands"]))

    def test_already_amber_red_spilling_are_zero(self):
        w = lines({"a": {1: 270, 2: 300}})["worlds"][0]
        got = {i["slot"]: (i["beacon"], i["to_amber"], i["to_red"]) for i in w["islands"]}
        self.assertEqual(got[1], ("amber", 0, 29))
        self.assertEqual(got[2], ("red", 0, 0))
        self.assertEqual(w["to_spill"], 0)

    def test_tightest_slot(self):
        self.assertEqual(lines({"a": {1: 5, 2: 100, 3: 50}})["worlds"][0]["tightest_slot"], 2)

    def test_cargo_verdicts(self):
        base = {"a": {1: 0}}
        self.assertEqual(lines(base)["verdict"], "afloat")
        self.assertEqual(lines(base, [("a", 1, 264)])["verdict"], "afloat")
        self.assertEqual(lines(base, [("a", 1, 265)])["verdict"], "awash")
        self.assertEqual(lines(base, [("a", 1, 299)])["verdict"], "sunk")
        r = lines({"a": {1: 0, 2: 0}}, [("a", 1, 257)])
        self.assertEqual((r["verdict_now"], r["verdict"]), ("afloat", "sunk"))

    def test_lines_predict_cargo(self):
        rng = random.Random(52201)
        for _ in range(120):
            isl = {s: rng.randrange(0, 120) for s in rng.sample(range(5), rng.randrange(1, 3))}
            r = lines({"w": isl})
            w = r["worlds"][0]
            i = rng.choice(w["islands"])
            if r["verdict_now"] != "afloat" or w["to_spill"] == 0:
                continue
            k = min(i["to_amber"], w["to_spill"]) - 1
            if k >= 0:
                self.assertEqual(lines({"w": isl}, [("w", i["slot"], k)])["verdict"], "afloat")
            self.assertNotEqual(lines({"w": isl}, [("w", i["slot"], k + 1)])["verdict"], "afloat")

    def test_cargo_does_not_mutate_input(self):
        rep = pl.to_report(census({"a": {1: 3}}), cfg())
        before = json.dumps(rep, sort_keys=True)
        pl.build(rep, [("a", 1, 500)])
        self.assertEqual(json.dumps(rep, sort_keys=True), before)

    def test_parse_add_and_refusals(self):
        self.assertEqual(pl.parse_add(["alpha:2:40", "x:y:1:3"]), [("alpha", 2, 40), ("x:y", 1, 3)])
        for bad in ("alpha:2", "alpha:-1:3", ":1:2", "a:1:x", "a:1:9999999"):
            with self.assertRaises(pl.PlimsollError, msg=bad):
                pl.parse_add([bad])
        with self.assertRaises(pl.PlimsollError):
            lines({"a": {1: 0}}, [("a", 7, 1)])
        with self.assertRaises(pl.PlimsollError):
            pl.to_report({"format": "nope"}, cfg())

    def test_deterministic_order_invariant(self):
        a = json.dumps(lines({"b": {3: 9, 1: 2}, "a": {4: 1}}), sort_keys=True)
        self.assertEqual(a, json.dumps(lines({"a": {4: 1}, "b": {1: 2, 3: 9}}), sort_keys=True))

    def test_report_input_equals_census_input(self):
        rep = pl.to_report(census({"a": {1: 7}, "b": {2: 40}}), cfg())
        self.assertEqual(pl.build(rep), lines({"a": {1: 7}, "b": {2: 40}}))

    def test_real_census_pipeline(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census",
                            os.path.join(FIX, "alpha.json"), os.path.join(FIX, "beta.json"),
                            "--snapshot-date", "2026-10-26", "--bindings", os.path.join(FIX, "bindings.json"),
                            "--output-dir", os.path.join(d, "census")], cwd=ROOT, check=True, capture_output=True)
            path = os.path.join(d, "census", "census.json")
            code, out, _ = run_cli(path, "--json", "--fail-on-sunk")
            r = json.loads(out)
            self.assertEqual((code, r["verdict"]), (0, "afloat"))
            self.assertEqual({w["world"]: w["to_spill"] for w in r["worlds"]}, {"alpha": 256, "beta": 299})
            self.assertEqual(run_cli(path, "--add", "alpha:2:300", "--fail-on-sunk")[0], 1)

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(hook["hook"]["values"], ["afloat", "awash", "sunk"])
        self.assertEqual(set(hook["npc"]["lines"]), set(hook["hook"]["values"]))
        self.assertEqual(hook["npc"]["name"], "Surveyor Odile")

    def test_cli_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.json")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("{nope")
            for args in ([bad], [os.path.join(d, "missing.json")]):
                code, _, err = run_cli(*args)
                self.assertEqual(code, 2)
                self.assertIn("refused", err)
            c = os.path.join(d, "c.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(census({"a": {1: 0}}), f)
            self.assertEqual(run_cli(c, "--add", "a:9:1")[0], 2)
            code, out, _ = run_cli(c, "--add", "a:1:270")
            self.assertEqual(code, 0)
            self.assertIn("with cargo awash", out)


if __name__ == "__main__":
    unittest.main()