# SPDX-License-Identifier: MIT
"""Tests for G206 Census Budget Beacons (world census -> RAM/disk resident-set budget flags)."""
import copy
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
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402
import dsb_manifest  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
CONFIG = os.path.join(ROOT, "data", "islands", "disk-saver", "census-budget-v1.json")
GOLDEN = os.path.join(HERE, "census_budget_golden.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")
SEEDS = (205, 1, 2, 3, 4, 5, 6, 7)


def _read(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _cfg():
    return _read(CONFIG)


def cfg(ram=40000, disk=32768, warn=900):
    return {"budget": {"ram_budget_kib": ram, "disk_budget_kib": disk, "warn_permille": warn}}


def random_census(seed, worlds=3, max_islands=10, max_assets=900):
    rng = random.Random(seed)
    ws = []
    for w in range(worlds):
        slots = rng.sample(range(64), rng.randint(0, max_islands))
        ws.append({"id": f"w{seed}_{w}", "islands": [{"slot": s, "asset_definitions": rng.randint(0, max_assets)}
                                                      for s in slots]})
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": "2026-10-26", "sources": [], "worlds": ws}


def real_census(tmp):
    """Run the real tools/world_census CLI on its own fixtures (read-only) and load census.json."""
    out = os.path.join(tmp, "census")
    subprocess.run([sys.executable, "-B", "-m", "tools.world_census",
                    os.path.join(FIX, "alpha.json"), os.path.join(FIX, "beta.json"),
                    "--snapshot-date", "2026-10-26", "--bindings", os.path.join(FIX, "bindings.json"),
                    "--output-dir", out], cwd=ROOT, check=True, capture_output=True)
    return os.path.join(out, "census.json")


class CostModel(unittest.TestCase):
    def test_constants_match_dsb_manifest(self):
        self.assertEqual(cb.BASE_RAM_KIB, dsb_manifest.BASE_RAM_KIB)
        self.assertEqual(cb.PER_ASSET_RAM_KIB, dsb_manifest.PER_PLACEMENT_RAM_KIB)
        self.assertEqual(cb.BASE_DISK_KIB, dsb_manifest.BASE_DISK_KIB)
        self.assertEqual(cb.PER_ASSET_DISK_KIB, dsb_manifest.PER_PLACEMENT_DISK_KIB)

    def test_island_cost_pinned(self):
        self.assertEqual(cb.island_cost(0), (16384, 4096))
        self.assertEqual(cb.island_cost(1), (16408, 4192))
        self.assertEqual(cb.island_cost(1000), (40384, 100096))

    def test_cost_refuses_bad_counts(self):
        for bad in (-1, True, 1.5, "3", None):
            with self.assertRaises(cb.CensusBudgetError):
                cb.island_cost(bad)


class Beacons(unittest.TestCase):
    def test_boundaries_exact(self):
        # equal to budget fits; one KiB over is red
        self.assertEqual(cb.beacon(100, 10, 100, 10, 1000), ([], "green"))
        self.assertEqual(cb.beacon(101, 10, 100, 10, 1000), (["ram_over"], "red"))
        self.assertEqual(cb.beacon(100, 11, 100, 10, 1000), (["disk_over"], "red"))
        self.assertEqual(cb.beacon(101, 11, 100, 10, 1000), (["ram_over", "disk_over"], "red"))
        # warn line: 90 of 100 at 900 permille is not near, 91 is
        self.assertEqual(cb.beacon(90, 1, 100, 10, 900), ([], "green"))
        self.assertEqual(cb.beacon(91, 1, 100, 10, 900), (["ram_near"], "amber"))
        self.assertEqual(cb.beacon(1, 10, 100, 10, 900), (["disk_near"], "amber"))

    def test_flags_agree_with_definition(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(200):
                ram, disk = rng.randint(1, 2000), rng.randint(1, 2000)
                rb, db, w = rng.randint(1, 2000), rng.randint(1, 2000), rng.randint(1, 1000)
                flags, color = cb.beacon(ram, disk, rb, db, w)
                over = ram > rb or disk > db
                self.assertEqual(color == "red", over)
                self.assertEqual(color == "green", not over and ram * 1000 <= rb * w and disk * 1000 <= db * w)


class ResidentSet(unittest.TestCase):
    def test_greedy_equals_brute_force_oracle(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(60):
                rams = [rng.randint(1, 500) for _ in range(rng.randint(0, 12))]
                budget = rng.randint(0, 2500)
                self.assertEqual(cb.max_resident(rams, budget), cb.max_resident_oracle(rams, budget))

    def test_plan_world_matches_oracle(self):
        for seed in SEEDS:
            rep = cb.plan(random_census(seed), cfg(ram=60000))
            for w in rep["worlds"]:
                rams = [i["ram_kib"] for i in w["islands"]]
                self.assertEqual(w["max_resident"], cb.max_resident_oracle(rams, 60000))
                self.assertEqual(w["fits_all_resident"],
                                 sum(rams) <= 60000 and sum(i["disk_kib"] for i in w["islands"]) <= 32768)

    def test_oracle_limit(self):
        with self.assertRaises(cb.CensusBudgetError):
            cb.max_resident_oracle([1] * (cb.ORACLE_LIMIT + 1), 5)


class PlanReport(unittest.TestCase):
    def test_seeded_replay_determinism(self):
        for seed in SEEDS:
            a = cb.dumps(cb.plan(random_census(seed), cfg()))
            b = cb.dumps(cb.plan(random_census(seed), cfg()))
            self.assertEqual(a, b)

    def test_order_independent(self):
        doc = random_census(205)
        shuffled = copy.deepcopy(doc)
        random.Random(9).shuffle(shuffled["worlds"])
        for w in shuffled["worlds"]:
            w["islands"].reverse()
        self.assertEqual(cb.dumps(cb.plan(doc, cfg())), cb.dumps(cb.plan(shuffled, cfg())))

    def test_summary_counts(self):
        rep = cb.plan(random_census(3), cfg())
        isl = [i for w in rep["worlds"] for i in w["islands"]]
        s = rep["summary"]
        self.assertEqual(s["islands"], len(isl))
        self.assertEqual(s["green"] + s["amber"] + s["red"], len(isl))
        self.assertEqual(s["red"], sum(1 for i in isl if i["beacon"] == "red"))

    def test_refusals(self):
        good = random_census(1)
        bad_cases = []
        for mutate in (
            lambda d: d.update(format="x"),
            lambda d: d.update(version=2),
            lambda d: d.update(version=True),
            lambda d: d.update(count_semantics="instances"),
            lambda d: d.update(worlds=[]),
            lambda d: d["worlds"].append(dict(d["worlds"][0])),
            lambda d: d["worlds"][0].update(islands=[{"slot": 1, "asset_definitions": 0}] * 2),
            lambda d: d["worlds"][0].update(islands=[{"slot": -1, "asset_definitions": 0}]),
            lambda d: d["worlds"][0].update(islands=[{"slot": 1, "asset_definitions": False}]),
        ):
            d = copy.deepcopy(good)
            mutate(d)
            bad_cases.append(d)
        for d in bad_cases:
            with self.assertRaises(cb.CensusBudgetError):
                cb.plan(d, cfg())
        for c in ({}, cfg(ram=0), cfg(warn=0), cfg(warn=1001), cfg(disk=True)):
            with self.assertRaises(cb.CensusBudgetError):
                cb.plan(good, c)


class RealCensusAndHook(unittest.TestCase):
    def test_golden_fixture_from_real_census(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(real_census(tmp), encoding="utf-8") as f:
                rep = cb.plan(json.load(f), _cfg())
        rep.pop("census_sources")  # raw-byte hashes depend on checkout line endings
        with open(GOLDEN, encoding="utf-8") as f:
            self.assertEqual(rep, json.load(f))

    def test_tight_budget_flags_real_census(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(real_census(tmp), encoding="utf-8") as f:
                rep = cb.plan(json.load(f), cfg(ram=16400, disk=8192))
        alpha = {i["slot"]: i for i in rep["worlds"][0]["islands"]}
        self.assertEqual(alpha[2]["beacon"], "red")       # 16408 KiB > 16400
        self.assertEqual(alpha[2]["flags"], ["ram_over"])
        self.assertEqual(alpha[9]["beacon"], "amber")     # 16384 KiB is within 0.9 of 16400
        self.assertEqual(rep["worlds"][0]["max_resident"], 1)
        self.assertFalse(rep["worlds"][0]["fits_all_resident"])

    def test_config_hook_shape(self):
        c = _cfg()
        self.assertEqual(c["quest"], "q_census_beacons")
        self.assertEqual(c["hook"]["report_format"], cb.FORMAT)
        self.assertEqual(set(c["npc"]["lines"]), {"green", "amber", "red", "spill"})
        cb.load_budget(c)

    def test_cli_writes_new_file_and_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            census = real_census(tmp)
            out = os.path.join(tmp, "report.json")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cb.main([census, "-o", out]), 0)
            self.assertEqual(_read(out)["format"], cb.FORMAT)
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                self.assertEqual(cb.main([census, "-o", out]), 2)  # never overwrites
            tight = os.path.join(tmp, "tight.json")
            with open(tight, "w", encoding="utf-8") as f:
                json.dump(cfg(ram=16400), f)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cb.main([census, "--config", tight, "--strict"]), 1)
                self.assertEqual(cb.main([census, "--config", tight]), 0)


if __name__ == "__main__":
    unittest.main()
