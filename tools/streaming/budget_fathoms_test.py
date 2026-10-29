# SPDX-License-Identifier: MIT
"""Tests for Budget Fathoms (G529): breakpoints = brute-force oracle, fleet needs, sweep, verdicts, CLI."""
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
import budget_fathoms as bf  # noqa: E402

HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "budget-fathoms-v1.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")


def cfg(ram=40000, disk=32768, warn=900):
    return {"budget": {"ram_budget_kib": ram, "disk_budget_kib": disk, "warn_permille": warn}}


def census(worlds):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in sorted(isl.items())]}
                       for w, isl in sorted(worlds.items())]}


def fathoms(worlds, c=None, **kw):
    return bf.build(bf.to_report(census(worlds), c or cfg()), **kw)


def scan(pred, start=1):
    b = start
    while not pred(b):
        b += 1
    return b


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = bf.main(list(args))
    return code, out.getvalue(), err.getvalue()


class FathomTest(unittest.TestCase):
    def test_green_kib_equals_oracle(self):
        rng = random.Random(529)
        for _ in range(400):
            cost, warn = rng.randrange(1, 5000), rng.randrange(300, 1001)
            want = scan(lambda b: cb.beacon(cost, 0, b, 10 ** 9, warn)[1] == "green")
            self.assertEqual(bf.green_kib(cost, warn), want, (cost, warn))

    def test_island_breakpoints_match_g206(self):
        rng = random.Random(5291)
        for _ in range(60):
            n = rng.randrange(0, 400)
            i = fathoms({"a": {1: n}})["worlds"][0]["islands"][0]
            ram, disk = 16384 + 24 * n, 4096 + 96 * n
            for b, want in ((i["ram_green_kib"], "green"), (i["ram_green_kib"] - 1, "amber")):
                self.assertEqual(cb.beacon(ram, 0, b, 10 ** 9, 900)[1], want)
            self.assertEqual(cb.beacon(ram, 0, i["ram_clear_kib"], 10 ** 9, 900)[1], "amber" if i["ram_clear_kib"] < i["ram_green_kib"] else "green")
            self.assertEqual(cb.beacon(ram, 0, i["ram_clear_kib"] - 1, 10 ** 9, 900)[1], "red")
            self.assertEqual(cb.beacon(0, disk, 10 ** 9, i["disk_green_kib"], 900)[1], "green")
            self.assertEqual(cb.beacon(0, disk, 10 ** 9, i["disk_green_kib"] - 1, 900)[1], "amber")

    def test_fleet_needs_are_tight(self):
        rng = random.Random(5292)
        for _ in range(80):
            ws = {"w%d" % k: {s: rng.randrange(0, 200) for s in rng.sample(range(6), rng.randrange(1, 3))}
                  for k in range(rng.randrange(1, 3))}
            r = fathoms(ws)
            n = r["need_kib"]["ram"]
            at = lambda b: bf._state(cb.plan(census(ws), cfg(ram=b, disk=10 ** 8)))
            self.assertEqual(at(n["all_fit"])["worlds_spilling"], 0)
            self.assertGreater(at(n["all_fit"] - 1)["worlds_spilling"], 0)
            self.assertEqual(at(n["no_red"])["red"], 0)
            self.assertGreater(at(n["no_red"] - 1)["red"], 0)
            self.assertEqual(at(n["all_green"])["green"], sum(len(x) for x in ws.values()))
            self.assertEqual(bf.verdict_of(at(n["deep"])), "deep")
            self.assertNotEqual(bf.verdict_of(at(n["deep"] - 1)), "deep")

    def test_slack_signs(self):
        r = fathoms({"a": {1: 0, 2: 0, 3: 0}})
        self.assertEqual(r["slack_kib"]["ram"]["all_fit"], 40000 - 3 * 16384)
        self.assertLess(r["slack_kib"]["ram"]["all_fit"], 0)
        self.assertGreater(r["slack_kib"]["ram"]["no_red"], 0)

    def test_verdicts(self):
        self.assertEqual(fathoms({"a": {1: 0}})["verdict"], "deep")
        self.assertEqual(fathoms({"a": {1: 265}})["verdict"], "shoal")
        self.assertEqual(fathoms({"a": {1: 299}})["verdict"], "aground")
        self.assertEqual(fathoms({"a": {1: 0, 2: 0, 3: 0}})["verdict"], "aground")

    def test_sweep_matches_g206(self):
        ws = {"a": {1: 0, 2: 100}, "b": {3: 270}}
        r = fathoms(ws, sweep_ram=[30000, 40000, 60000], sweep_disk=[20000])
        self.assertEqual([(s["dim"], s["budget_kib"]) for s in r["sweep"]], [("ram", 30000), ("ram", 40000), ("ram", 60000), ("disk", 20000)])
        for s in r["sweep"]:
            c = cfg(**{s["dim"]: s["budget_kib"]})
            self.assertEqual({k: s[k] for k in ("green", "amber", "red", "worlds_spilling")}, bf._state(cb.plan(census(ws), c)))

    def test_parse_list(self):
        self.assertEqual(bf.parse_list("40000, 30000,40000", "x"), [30000, 40000])
        self.assertEqual(bf.parse_list(None, "x"), [])
        for bad in ("0", "-1", "abc", "1,,2", ",".join(str(i) for i in range(1, 70))):
            with self.assertRaises(bf.FathomError, msg=bad):
                bf.parse_list(bad, "x")

    def test_report_input_equals_census(self):
        rep = bf.to_report(census({"a": {1: 7}, "b": {2: 40}}), cfg())
        self.assertEqual(bf.build(rep), fathoms({"a": {1: 7}, "b": {2: 40}}))

    def test_deterministic_order_invariant(self):
        a = json.dumps(fathoms({"b": {3: 9, 1: 2}, "a": {4: 1}}), sort_keys=True)
        self.assertEqual(a, json.dumps(fathoms({"a": {4: 1}, "b": {1: 2, 3: 9}}), sort_keys=True))

    def test_real_census_pipeline(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census",
                            os.path.join(FIX, "alpha.json"), os.path.join(FIX, "beta.json"),
                            "--snapshot-date", "2026-10-26", "--bindings", os.path.join(FIX, "bindings.json"),
                            "--output-dir", os.path.join(d, "census")], cwd=ROOT, check=True, capture_output=True)
            path = os.path.join(d, "census", "census.json")
            code, out, _ = run_cli(path, "--json", "--fail-on-aground", "--sweep-ram", "30000")
            r = json.loads(out)
            self.assertEqual((code, r["verdict"]), (0, "deep"))
            self.assertEqual(r["need_kib"]["ram"], {"all_green": 18232, "no_red": 16408, "all_fit": 32792, "deep": 32792})
            self.assertEqual(r["sweep"][0]["verdict"], "aground")

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(hook["hook"]["values"], ["deep", "shoal", "aground"])
        self.assertEqual(set(hook["npc"]["lines"]), set(hook["hook"]["values"]))
        self.assertEqual(hook["npc"]["name"], "Gauge-keeper Corwin")

    def test_cli_exit_codes_and_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            c, bad, conf = (os.path.join(d, n) for n in ("c.json", "bad.json", "cfg.json"))
            with open(c, "w", encoding="utf-8") as f:
                json.dump(census({"a": {1: 0, 2: 0, 3: 0}}), f)
            with open(bad, "w", encoding="utf-8") as f:
                f.write("{nope")
            with open(conf, "w", encoding="utf-8") as f:
                json.dump(cfg(warn=1200), f)
            self.assertEqual(run_cli(c)[0], 0)
            self.assertEqual(run_cli(c, "--fail-on-aground")[0], 1)
            for args in ([bad], [os.path.join(d, "none.json")], [c, "--sweep-ram", "x"]):
                code, _, err = run_cli(*args)
                self.assertEqual(code, 2, args)
                self.assertIn("refused", err)
            self.assertEqual(run_cli(c, "--config", conf)[0], 2)


if __name__ == "__main__":
    unittest.main()