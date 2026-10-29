# SPDX-License-Identifier: MIT
"""Tests for Beacon Watch (G505): gate = brute-force oracle, each regression kind, seeded replay, golden."""
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
import beacon_watch as bw  # noqa: E402

GOLDEN = os.path.join(HERE, "beacon_watch_golden.json")
BASELINE = os.path.join(ROOT, "data", "islands", "disk-saver", "beacon-watch-baseline-v1.json")
CONFIG = os.path.join(ROOT, "data", "islands", "disk-saver", "beacon-watch-v1.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")


def real_report(ram_budget_kib=None):
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
    if ram_budget_kib is not None:
        cfg["budget"]["ram_budget_kib"] = ram_budget_kib
    return cb.plan(census, cfg)


def rep(worlds):
    """worlds: [(id, fits, max_resident, [(slot, beacon)])]."""
    return {"format": "daedalus-census-budget", "version": 1,
            "worlds": [{"id": w, "fits_all_resident": f, "max_resident": m,
                        "islands": [{"slot": s, "beacon": b} for s, b in isl]} for w, f, m, isl in worlds]}


def rand_report(rng):
    worlds = []
    for wid in rng.sample(["alpha", "beta", "gamma", "delta"], rng.randint(0, 4)):
        isl = [(s, rng.choice(["green", "amber", "red"])) for s in rng.sample(range(8), rng.randint(0, 6))]
        worlds.append((wid, rng.random() < 0.5, rng.randint(0, 6), isl))
    return rep(worlds)


def kinds(v):
    return [f["kind"] for f in v["findings"]]


class BeaconWatchTest(unittest.TestCase):
    def test_gate_equals_brute_force_oracle(self):
        rng = random.Random(505)
        for _ in range(500):
            a, b = rand_report(rng), rand_report(rng)
            got = bw.findings(bw.read_report(a, "a"), bw.read_report(b, "b"))
            self.assertEqual(got, bw.findings_oracle(a, b))

    def test_identical_reports_are_calm(self):
        r = real_report()
        v = bw.watch(r, r)
        self.assertEqual((v["verdict"], v["regressions"], v["findings"]), ("calm", 0, []))

    def test_each_worsening_step_fails(self):
        for before, after in (("green", "amber"), ("amber", "red"), ("green", "red")):
            v = bw.watch(rep([("w", True, 2, [(1, before)])]), rep([("w", True, 2, [(1, after)])]))
            self.assertEqual((v["verdict"], kinds(v)), ("storm", ["worse"]))

    def test_improvements_and_removals_never_fail(self):
        base = rep([("w", False, 1, [(1, "red"), (2, "amber"), (3, "green")])])
        cur = rep([("w", True, 3, [(1, "green"), (2, "green"), (4, "green")])])
        v = bw.watch(base, cur)
        self.assertEqual(v["verdict"], "calm")
        self.assertEqual(sorted(kinds(v)), ["better", "better", "gone", "new", "unspill"])

    def test_new_hot_island_spill_and_max_resident_drop_fail(self):
        base = rep([("w", True, 3, [(1, "green")])])
        cur = rep([("w", False, 2, [(1, "green"), (5, "amber")])])
        v = bw.watch(base, cur)
        self.assertEqual(sorted(kinds(v)), ["max_resident_drop", "new_hot", "spill"])
        self.assertEqual(v["regressions"], 3)

    def test_input_order_does_not_matter(self):
        rng = random.Random(7)
        for _ in range(100):
            a, b = rand_report(rng), rand_report(rng)
            b2 = json.loads(json.dumps(b))
            rng.shuffle(b2["worlds"])
            for w in b2["worlds"]:
                rng.shuffle(w["islands"])
            self.assertEqual(bw.dumps(bw.watch(a, b)), bw.dumps(bw.watch(a, b2)))

    def test_seeded_replay_is_byte_identical(self):
        def run():
            rng = random.Random(20261029)
            return "".join(bw.dumps(bw.watch(rand_report(rng), rand_report(rng))) for _ in range(50))
        self.assertEqual(run(), run())

    def test_baseline_matches_real_pipeline(self):
        with open(BASELINE, encoding="utf-8") as f:
            base = json.load(f)
        self.assertEqual(base, real_report())

    def test_golden_tight_budget_storm(self):
        with open(BASELINE, encoding="utf-8") as f:
            base = json.load(f)
        v = bw.watch(base, real_report(ram_budget_kib=17000))
        with open(GOLDEN, encoding="utf-8") as f:
            self.assertEqual(bw.dumps(v), f.read())
        self.assertEqual(v["verdict"], "storm")
        self.assertTrue(v["budget_changed"])

    def test_refuses_bad_reports(self):
        good = rep([("w", True, 1, [(1, "green")])])
        for bad in ({"format": "x"}, dict(good, version=2), rep([("w", "yes", 1, [])]),
                    rep([("w", True, 1, [(1, "blue")])]), rep([("w", True, 1, [(1, "green"), (1, "red")])]),
                    rep([("w", True, -1, [])]), dict(good, worlds=[{"id": "w"}, {"id": "w"}])):
            with self.assertRaises(bw.BeaconWatchError):
                bw.watch(good, bad)

    def test_cli_exit_codes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p_base, p_ok, p_bad = (os.path.join(d, n) for n in ("b.json", "ok.json", "bad.json"))
            for p, r in ((p_base, rep([("w", True, 1, [(1, "green")])])),
                         (p_ok, rep([("w", True, 1, [(1, "green")])])),
                         (p_bad, rep([("w", True, 1, [(1, "red")])]))):
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(r, f)
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                self.assertEqual(bw.main([p_base, p_ok, "--strict"]), 0)
                self.assertEqual(bw.main([p_base, p_bad, "--strict"]), 1)
                self.assertEqual(bw.main([p_base, p_bad]), 0)
                o = os.path.join(d, "v.json")
                self.assertEqual(bw.main([p_base, p_bad, "-o", o]), 0)
                self.assertEqual(bw.main([p_base, p_bad, "-o", o]), 2)
                self.assertEqual(bw.main([p_base, os.path.join(d, "missing.json")]), 2)
            self.assertIn("FAIL worse: w slot 1 green -> red", out.getvalue())

    def test_hook_config_names_every_kind(self):
        with open(CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["hook"]["report_format"], bw.FORMAT)
        self.assertEqual(set(cfg["npc"]["lines"]), {"calm", "storm"})
        self.assertEqual(sorted(cfg["hook"]["failing_kinds"]), sorted(bw.WORSE))


if __name__ == "__main__":
    unittest.main()
