# SPDX-License-Identifier: MIT
"""Tests for Stray Cargo (G531): every finding kind, hidden cost = brute force, verdicts, real census, CLI."""
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
import stray_cargo as sc  # noqa: E402

HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "stray-cargo-v1.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")


def world(wid, islands, assets, realm="r", claimed=None):
    w = {"id": wid, "realm_id": realm, "islands": [{"slot": s, "asset_definitions": n} for s, n in islands.items()],
         "assets": [{"name": n, "file": f, "island_slot": s} for n, f, s in assets]}
    if claimed is not None:
        w["assets_without_island"] = claimed
    return w


def census(*worlds):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions", "worlds": list(worlds)}


TIDY = census(world("a", {1: 1}, [("ark", "a/ark.glb", 1)]))


def kinds(r):
    return sorted(x["kind"] for x in r["findings"])


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = sc.main(list(args))
    return code, out.getvalue(), err.getvalue()


class StrayTest(unittest.TestCase):
    def test_tidy(self):
        r = sc.survey(TIDY)
        self.assertEqual((r["verdict"], r["findings"]), ("tidy", []))

    def test_stray_and_hidden_cost(self):
        r = sc.survey(census(world("a", {1: 1}, [("ark", "x", 1), ("buoy", "y", None), ("bell", "z", None)])))
        self.assertEqual(kinds(r), ["stray", "stray"])
        self.assertEqual(r["hidden_cost_kib"], {"ram_kib": 48, "disk_kib": 192})
        self.assertEqual(r["verdict"], "littered")

    def test_dangling_is_adrift(self):
        r = sc.survey(census(world("a", {1: 1}, [("ark", "x", 1), ("buoy", "y", 7)])))
        self.assertEqual((kinds(r), r["verdict"]), (["dangling"], "adrift"))

    def test_bool_slot_is_dangling(self):
        r = sc.survey(census(world("a", {1: 1}, [("ark", "x", True)])))
        self.assertIn("dangling", kinds(r))

    def test_duplicate_name(self):
        r = sc.survey(census(world("a", {1: 2}, [("ark", "x", 1), ("ark", "y", 1)])))
        self.assertEqual(r["findings"], [{"world": "a", "kind": "duplicate_name", "asset": "ark", "count": 2}])

    def test_count_mismatch(self):
        r = sc.survey(census(world("a", {1: 1}, [("ark", "x", 1), ("buoy", "y", None)], claimed=0)))
        self.assertIn({"world": "a", "kind": "count_mismatch", "claimed": 0, "found": 1}, r["findings"])
        self.assertEqual(r["verdict"], "adrift")
        self.assertEqual(sc.survey(census(world("a", {1: 1}, [("ark", "x", 1)], claimed=0)))["verdict"], "tidy")

    def test_empty_hull_and_no_realm(self):
        r = sc.survey(census(world("a", {1: 0, 2: 1}, [("ark", "x", 2)], realm=None)))
        self.assertEqual(kinds(r), ["empty_hull", "no_realm"])
        self.assertEqual(r["empty_hull_ram_kib"], 16384)

    def test_shared_file(self):
        r = sc.survey(census(world("a", {1: 1}, [("ark", "s.glb", 1)]), world("b", {1: 1}, [("ark", "s.glb", 1)]),
                             world("c", {1: 1}, [("ark", "s.glb", 1)])))
        self.assertEqual(r["findings"], [{"world": None, "kind": "shared_file", "file": "s.glb",
                                          "worlds": ["a", "b", "c"], "disk_kib": 192}])

    def test_counts_equal_brute_force(self):
        rng = random.Random(531)
        for _ in range(200):
            ws, stray = [], 0
            for k in range(rng.randrange(1, 4)):
                isl = {s: rng.randrange(0, 3) for s in rng.sample(range(6), rng.randrange(1, 4))}
                assets = []
                for j in range(rng.randrange(0, 6)):
                    slot = rng.choice([None, None] + list(isl) + [99])
                    assets.append(("a%d" % rng.randrange(4), "f%d" % rng.randrange(5), slot))
                    stray += slot is None
                ws.append(world("w%d" % k, isl, assets, realm=rng.choice([None, "r"])))
            r = sc.survey(census(*ws))
            self.assertEqual(r["counts"]["stray"], stray)
            self.assertEqual(r["hidden_cost_kib"], {"ram_kib": 24 * stray, "disk_kib": 96 * stray})
            dangling = sum(1 for w in ws for a in w["assets"] if a["island_slot"] not in (None,) and
                           a["island_slot"] not in {i["slot"] for i in w["islands"]})
            self.assertEqual(r["counts"]["dangling"], dangling)
            self.assertEqual(r["counts"]["empty_hull"], sum(1 for w in ws for i in w["islands"] if i["asset_definitions"] == 0))
            self.assertEqual(r["verdict"] == "adrift", bool(r["counts"]["dangling"] or r["counts"]["duplicate_name"]))

    def test_deterministic_order_invariant(self):
        a = census(world("b", {1: 0}, [("x", "s", None)]), world("a", {2: 1}, [("y", "s", 2)]))
        b = census(world("a", {2: 1}, [("y", "s", 2)]), world("b", {1: 0}, [("x", "s", None)]))
        self.assertEqual(json.dumps(sc.survey(a), sort_keys=True), json.dumps(sc.survey(b), sort_keys=True))

    def test_real_census_fixtures(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census",
                            os.path.join(FIX, "alpha.json"), os.path.join(FIX, "beta.json"),
                            "--snapshot-date", "2026-10-26", "--bindings", os.path.join(FIX, "bindings.json"),
                            "--output-dir", os.path.join(d, "census")], cwd=ROOT, check=True, capture_output=True)
            code, out, _ = run_cli(os.path.join(d, "census", "census.json"), "--json", "--fail-on", "adrift")
        r = json.loads(out)
        self.assertEqual((code, r["verdict"]), (0, "littered"))
        self.assertEqual(r["counts"], {"dangling": 0, "duplicate_name": 0, "count_mismatch": 0, "stray": 2,
                                       "empty_hull": 2, "shared_file": 1, "no_realm": 1})

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(hook["hook"]["values"], ["tidy", "littered", "adrift"])
        self.assertEqual(set(hook["npc"]["lines"]), set(hook["hook"]["values"]))
        self.assertEqual(hook["npc"]["name"], "Beachcomber Linnet")

    def test_cli_exit_codes_and_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            c, bad = os.path.join(d, "c.json"), os.path.join(d, "bad.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(census(world("a", {1: 1}, [("ark", "x", None)])), f)
            with open(bad, "w", encoding="utf-8") as f:
                f.write("{nope")
            self.assertEqual(run_cli(c)[0], 0)
            self.assertEqual(run_cli(c, "--fail-on", "adrift")[0], 0)
            self.assertEqual(run_cli(c, "--fail-on", "littered")[0], 1)
            for args in ([bad], [os.path.join(d, "none.json")]):
                code, _, err = run_cli(*args)
                self.assertEqual(code, 2)
                self.assertIn("refused", err)
        for doc in ({"format": "nope"}, census(), census(world("a", {1: 1}, []), world("a", {1: 1}, []))):
            with self.assertRaises(sc.StrayError):
                sc.survey(doc)


if __name__ == "__main__":
    unittest.main()