# SPDX-License-Identifier: MIT
"""Tests for Memory Footprint Report (G519): G206 parity, shares, ranking = brute force, wins, tools, CLI."""
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
import memory_footprint as mf  # noqa: E402

HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "memory-footprint-v1.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")


def cfg():
    with open(cb.DEFAULT_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def census(worlds):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in sorted(isl.items())]}
                       for w, isl in sorted(worlds.items())]}


def fp(worlds, **kw):
    return mf.build(mf.to_report(census(worlds), cfg()), **kw)


def ram(n):
    return 16384 + 24 * n


def disk(n):
    return 4096 + 96 * n


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = mf.main(list(args))
    return code, out.getvalue(), err.getvalue()


class FootprintTest(unittest.TestCase):
    def test_world_totals_and_permille(self):
        r = fp({"a": {1: 0, 2: 100}})
        w = r["worlds"][0]
        self.assertEqual((w["ram_kib"], w["disk_kib"]), (ram(0) + ram(100), disk(0) + disk(100)))
        self.assertEqual(w["ram_permille"], (ram(0) + ram(100)) * 1000 // 40000)
        self.assertEqual(w["disk_permille"], (disk(0) + disk(100)) * 1000 // 32768)

    def test_matches_g206_report_totals(self):
        rep = mf.to_report(census({"a": {1: 7, 3: 50}, "b": {2: 0}}), cfg())
        r = mf.build(rep)
        got = {w["world"]: (w["ram_kib"], w["disk_kib"]) for w in r["worlds"]}
        self.assertEqual(got, {w["id"]: (w["total_ram_kib"], w["total_disk_kib"]) for w in rep["worlds"]})
        self.assertEqual(mf.build(rep), fp({"a": {1: 7, 3: 50}, "b": {2: 0}}))

    def test_verdict_light_laden_overladen(self):
        self.assertEqual(fp({"a": {1: 0}})["verdict"], "light")
        self.assertEqual(fp({"a": {1: 265}})["verdict"], "laden")
        self.assertEqual(fp({"a": {1: 0, 2: 0, 3: 0}})["verdict"], "overladen")

    def test_top_consumers_equal_brute_force(self):
        rng = random.Random(519)
        for _ in range(200):
            ws = {"w%d" % k: {s: rng.randrange(0, 400) for s in rng.sample(range(12), rng.randrange(1, 5))}
                  for k in range(rng.randrange(1, 4))}
            top = rng.randrange(1, 5)
            r = fp(ws, top=top)
            flat = sorted(((-ram(n), -disk(n), w, s) for w, isl in ws.items() for s, n in isl.items()))[:top]
            self.assertEqual([(c["world"], c["slot"]) for c in r["top_consumers"]], [(w, s) for _, _, w, s in flat])
            self.assertEqual(r["totals"]["ram_kib"], sum(ram(n) for isl in ws.values() for n in isl.values()))

    def test_world_top_and_shares(self):
        w = fp({"a": {1: 0, 2: 300, 3: 10}}, top=2)["worlds"][0]
        self.assertEqual([c["slot"] for c in w["top"]], [2, 3])
        self.assertEqual(w["top"][0]["ram_share_permille"], ram(300) * 1000 // w["ram_kib"])

    def test_wins_over_world_first_and_clears(self):
        r = fp({"big": {1: 0, 2: 0, 3: 0}, "small": {1: 0}}, wins=20)
        first = r["wins"][0]
        self.assertEqual((first["world"], first["action"], first["clears"], first["rank"]), ("big", "unload", True, 1))
        self.assertTrue(all(c["world_over"] for c in r["wins"][:3]))
        self.assertEqual([c["rank"] for c in r["wins"]], list(range(1, len(r["wins"]) + 1)))

    def test_wins_clears_equals_brute_force(self):
        rng = random.Random(5190)
        for _ in range(150):
            isl = {s: rng.randrange(0, 600) for s in rng.sample(range(8), rng.randrange(1, 4))}
            for c in fp({"w": isl}, wins=50)["wins"]:
                n = isl[c["slot"]]
                fr, fd = (ram(n), disk(n)) if c["action"] == "unload" else (24 * n, 96 * n)
                R, D = sum(map(ram, isl.values())), sum(map(disk, isl.values()))
                over = R > 40000 or D > 32768
                self.assertEqual((c["ram_free_kib"], c["disk_free_kib"]), (fr, fd))
                self.assertEqual(c["clears"], over and R - fr <= 40000 and D - fd <= 32768)

    def test_trim_only_when_assets(self):
        acts = {(c["slot"], c["action"]) for c in fp({"a": {1: 0, 2: 5}}, wins=10)["wins"]}
        self.assertEqual(acts, {(1, "unload"), (2, "unload"), (2, "trim")})

    def test_tool_footprint(self):
        with tempfile.TemporaryDirectory() as d:
            for name, size in (("a.py", 10), ("b.py", 3000), ("b_test.py", 9), ("test_x.py", 9), ("c.txt", 9)):
                with open(os.path.join(d, name), "wb") as f:
                    f.write(b"x" * size)
            self.assertEqual(mf.tool_footprint(d), [{"tool": "b", "bytes": 3000, "kib": 3}, {"tool": "a", "bytes": 10, "kib": 1}])
        self.assertEqual(fp({"a": {1: 0}})["tools"], [])

    def test_deterministic_and_order_invariant(self):
        a = json.dumps(fp({"b": {3: 9, 1: 2}, "a": {4: 1}}), sort_keys=True)
        self.assertEqual(a, json.dumps(fp({"a": {4: 1}, "b": {1: 2, 3: 9}}), sort_keys=True))

    def test_real_census_pipeline(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census",
                            os.path.join(FIX, "alpha.json"), os.path.join(FIX, "beta.json"),
                            "--snapshot-date", "2026-10-26", "--bindings", os.path.join(FIX, "bindings.json"),
                            "--output-dir", os.path.join(d, "census")], cwd=ROOT, check=True, capture_output=True)
            code, out, _ = run_cli(os.path.join(d, "census", "census.json"), "--json", "--tools-dir", "", "--fail-on-over")
        r = json.loads(out)
        self.assertEqual((code, r["verdict"], r["totals"]["islands"]), (0, "light", 3))
        self.assertEqual(r["top_consumers"][0], {"world": "alpha", "slot": 2, "ram_kib": 16408, "disk_kib": 4192})

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(hook["hook"]["values"], ["light", "laden", "overladen"])
        self.assertEqual(set(hook["npc"]["lines"]), set(hook["hook"]["values"]))

    def test_cli_exit_codes_and_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "c.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(census({"a": {1: 0, 2: 0, 3: 0}}), f)
            code, out, _ = run_cli(c, "--tools-dir", "")
            self.assertEqual(code, 0)
            self.assertIn("(clears world)", out)
            self.assertEqual(run_cli(c, "--tools-dir", "", "--fail-on-over")[0], 1)
            self.assertEqual(run_cli(c, "--top", "0")[0], 2)
            bad = os.path.join(d, "bad.json")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("{nope")
            code, _, err = run_cli(bad)
            self.assertEqual(code, 2)
            self.assertIn("refused", err)
            self.assertEqual(run_cli(os.path.join(d, "missing.json"))[0], 2)
            self.assertEqual(run_cli(c, "--tools-dir", os.path.join(d, "nodir"))[0], 2)


if __name__ == "__main__":
    unittest.main()
