# SPDX-License-Identifier: MIT
"""Tests for Budget Trend Ledger (G517): record/diff/trend, drift kinds, determinism, real census, CLI."""
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
import budget_ledger as bl  # noqa: E402

EXAMPLE = os.path.join(ROOT, "data", "islands", "disk-saver", "budget-ledger-example.jsonl")
HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "budget-ledger-v1.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")


def cfg():
    with open(cb.DEFAULT_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def census(worlds):
    """worlds = {id: {slot: asset_definitions}} -> minimal daedalus-world-census v1."""
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in sorted(isl.items())]}
                       for w, isl in sorted(worlds.items())]}


def rec(worlds, run, at=None):
    return bl.make_record(bl.to_report(census(worlds), cfg()), run, at)


def real_census():
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, "-B", "-m", "tools.world_census",
                        os.path.join(FIX, "alpha.json"), os.path.join(FIX, "beta.json"),
                        "--snapshot-date", "2026-10-26", "--bindings", os.path.join(FIX, "bindings.json"),
                        "--output-dir", os.path.join(d, "census")], cwd=ROOT, check=True, capture_output=True)
        with open(os.path.join(d, "census", "census.json"), encoding="utf-8-sig") as f:
            return json.load(f)


# Example ledger: run 1 = real World Census fixtures; runs 2-3 drift (disk amber at 265 defs, red at 299).
RUN2 = {"alpha": {2: 120, 9: 0}, "beta": {4: 270}, "gamma": {1: 10}}
RUN3 = {"alpha": {2: 310, 9: 0}, "gamma": {1: 10}}


def example_lines():
    r1 = bl.make_record(bl.to_report(real_census(), cfg()), "census-001", "2026-10-26")
    return [bl.dumps_line(r1), bl.dumps_line(rec(RUN2, "census-002", "2026-10-27")),
            bl.dumps_line(rec(RUN3, "census-003", "2026-10-28"))]


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = bl.main(list(args))
    return code, out.getvalue(), err.getvalue()


class LedgerTest(unittest.TestCase):
    def test_record_matches_g206_report(self):
        r = rec({"a": {1: 0, 2: 300}}, "r1")
        self.assertEqual(r["worlds"]["a"]["ram_kib"], 2 * 16384 + 24 * 300)
        self.assertEqual(r["worlds"]["a"]["disk_kib"], 2 * 4096 + 96 * 300)
        self.assertEqual(r["worlds"]["a"]["beacons"], {"1": "green", "2": "red"})
        self.assertTrue(r["worlds"]["a"]["over"])
        self.assertEqual(r["budget"], {"ram_budget_kib": 40000, "disk_budget_kib": 32768, "warn_permille": 900})

    def test_report_input_passes_through(self):
        rep = bl.to_report(census({"a": {1: 5}}), cfg())
        self.assertEqual(bl.make_record(rep, "x"), rec({"a": {1: 5}}, "x"))

    def test_beacon_thresholds(self):
        for n, want in ((264, "green"), (265, "amber"), (298, "amber"), (299, "red")):
            self.assertEqual(rec({"a": {1: n}}, "r")["worlds"]["a"]["beacons"]["1"], want, n)

    def test_diff_every_kind(self):
        a = rec({"keep": {1: 270}, "dim": {1: 0}, "gone": {1: 0}, "hot": {1: 0}}, "a")
        b = rec({"keep": {1: 0, 2: 300}, "dim": {1: 270}, "new": {1: 0}, "newhot": {1: 280}, "hot": {1: 0}}, "b")
        kinds = sorted((f["world"], f["kind"]) for f in bl.diff(a, b)["findings"])
        self.assertEqual(kinds, [("dim", "beacon_worse"), ("gone", "dropped"), ("keep", "beacon_better"),
                                 ("keep", "newly_over"), ("new", "appeared"), ("newhot", "appeared_hot")])
        self.assertEqual(bl.diff(a, b)["verdict"], "worse")
        self.assertEqual(sorted(f["kind"] for f in bl.diff(b, a)["findings"] if f["world"] == "keep"),
                         ["back_under", "beacon_worse"])

    def test_deltas_equal_brute_force(self):
        rng = random.Random(515)
        for _ in range(200):
            def world():
                return {s: rng.randrange(0, 400) for s in rng.sample(range(10), rng.randrange(1, 4))}
            ids = ["w%d" % i for i in range(4)]
            x = {w: world() for w in ids if rng.random() < 0.8} or {"w0": {1: 0}}
            y = {w: world() for w in ids if rng.random() < 0.8} or {"w0": {1: 0}}
            d = bl.diff(rec(x, "x"), rec(y, "y"))
            for w in d["worlds"]:
                ram = lambda isl: sum(16384 + 24 * n for n in isl.values())
                disk = lambda isl: sum(4096 + 96 * n for n in isl.values())
                self.assertEqual(w["ram_delta_kib"], ram(y[w["world"]]) - ram(x[w["world"]]))
                self.assertEqual(w["disk_delta_kib"], disk(y[w["world"]]) - disk(x[w["world"]]))
            self.assertEqual(sorted(w["world"] for w in d["worlds"]), sorted(set(x) & set(y)))

    def test_identical_runs_are_steady(self):
        a = rec({"a": {1: 270}}, "a")
        d = bl.diff(a, dict(a, run="b"))
        self.assertEqual((d["verdict"], d["findings"]), ("steady", []))

    def test_trend_growing_shrinking_flat(self):
        recs = [rec({"g": {1: n}, "s": {1: 100 - n}, "f": {1: 7}}, "r%d" % n) for n in range(0, 60, 10)]
        t = bl.trend(recs, 3)
        self.assertEqual(t["runs"], ["r30", "r40", "r50"])
        self.assertEqual({w["world"]: w["trend"] for w in t["worlds"]}, {"f": "flat", "g": "growing", "s": "shrinking"})
        self.assertEqual(t["tally"], "rising")
        self.assertEqual(bl.trend(recs[:1] + recs[:1], 5)["tally"], "steady")
        with self.assertRaises(bl.LedgerError):
            bl.trend(recs, 1)

    def test_ledger_append_and_duplicate_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            self.assertEqual(bl.append(p, rec({"a": {1: 0}}, "r1")), 1)
            self.assertEqual(bl.append(p, rec({"a": {1: 1}}, "r2")), 2)
            with self.assertRaises(bl.LedgerError):
                bl.append(p, rec({"a": {1: 2}}, "r1"))
            self.assertEqual([r["run"] for r in bl.read_ledger(p)], ["r1", "r2"])

    def test_deterministic_bytes_no_clock(self):
        a = bl.dumps_line(rec({"b": {3: 9}, "a": {1: 2}}, "r", "2026-10-29"))
        self.assertEqual(a, bl.dumps_line(rec({"a": {1: 2}, "b": {3: 9}}, "r", "2026-10-29")))
        self.assertIsNone(rec({"a": {1: 0}}, "r")["at"])

    def test_example_ledger_is_real_pipeline(self):
        with open(EXAMPLE, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), "".join(example_lines()))
        recs = bl.read_ledger(EXAMPLE)
        d = bl.diff(recs[1], recs[2])
        self.assertEqual(sorted(f["kind"] for f in d["findings"]), ["beacon_worse", "dropped", "newly_over"])

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(set(hook["npc"]["lines"]), {"steady", "rising", "ebbing", "worse"})
        self.assertEqual(hook["hook"]["values"], ["steady", "rising", "ebbing"])
        self.assertEqual(os.path.normpath(os.path.join(ROOT, hook["ledger"])), os.path.normpath(EXAMPLE))

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.jsonl")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("{not json\n")
            for args in (["diff", "--ledger", bad], ["trend", "--ledger", os.path.join(d, "none.jsonl")]):
                code, _, err = run_cli(*args)
                self.assertEqual(code, 2, args)
                self.assertIn("refused", err)
        with self.assertRaises(bl.LedgerError):
            bl.to_report({"format": "nope"}, cfg())
        with self.assertRaises(bl.LedgerError):
            rec({"a": {1: 0}}, " ")

    def test_cli_record_diff_trend_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            p, c = os.path.join(d, "l.jsonl"), os.path.join(d, "c.json")
            for run, w in (("r1", {"a": {1: 0}}), ("r2", {"a": {1: 299}})):
                with open(c, "w", encoding="utf-8") as f:
                    json.dump(census(w), f)
                self.assertEqual(run_cli("record", c, "--ledger", p, "--run", run, "--at", "t")[0], 0)
            self.assertEqual(run_cli("record", c, "--ledger", p, "--run", "r2")[0], 2)
            code, out, _ = run_cli("diff", "--ledger", p)
            self.assertEqual(code, 0)
            self.assertIn("newly_over", out)
            self.assertEqual(run_cli("diff", "--ledger", p, "--fail-on-worse")[0], 1)
            code, out, _ = run_cli("trend", "--ledger", p, "--json", "--fail-on-worse")
            self.assertEqual((code, json.loads(out)["tally"]), (1, "rising"))
            self.assertEqual(run_cli("diff", "--ledger", p, "--from", "r2", "--to", "r1", "--fail-on-worse")[0], 0)


if __name__ == "__main__":
    unittest.main()
