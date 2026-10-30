# SPDX-License-Identifier: MIT
"""Tests for Fleet Flags (G533): realm rollup = brute force over G206, flags, tally checks, real census, CLI."""
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
import fleet_flags as ff  # noqa: E402

HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "fleet-flags-v1.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")


def cfg():
    with open(cb.DEFAULT_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def census(worlds, realms=None):
    """worlds = {id: (realm, {slot: n})}."""
    doc = {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
           "worlds": [{"id": w, "realm_id": r, "asset_definitions": sum(isl.values()),
                       "islands": [{"slot": s, "asset_definitions": n} for s, n in sorted(isl.items())]}
                      for w, (r, isl) in sorted(worlds.items())]}
    if realms is not None:
        doc["realms"] = realms
    return doc


def flags(worlds, realms=None):
    return ff.muster(census(worlds, realms), cfg())


def by_realm(r):
    return {g["realm"]: g for g in r["realms"]}


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = ff.main(list(args))
    return code, out.getvalue(), err.getvalue()


class FleetFlagsTest(unittest.TestCase):
    def test_rollup_totals(self):
        g = by_realm(flags({"a": ("r", {1: 0, 2: 10}), "b": ("r", {1: 5}), "c": (None, {1: 0})}))
        self.assertEqual((g["r"]["worlds"], g["r"]["islands"], g["r"]["asset_definitions"]), (2, 3, 15))
        self.assertEqual(g["r"]["ram_kib"], 3 * 16384 + 24 * 15)
        self.assertEqual(g["r"]["disk_kib"], 3 * 4096 + 96 * 15)
        self.assertEqual(g[None]["worlds"], 1)

    def test_rollup_equals_brute_force(self):
        rng = random.Random(533)
        for _ in range(150):
            ws = {"w%d" % k: (rng.choice([None, "r1", "r2"]), {s: rng.randrange(0, 320) for s in rng.sample(range(6), rng.randrange(1, 4))})
                  for k in range(rng.randrange(1, 6))}
            got = by_realm(flags(ws))
            rep = cb.plan(census(ws), cfg())
            for rid in {r for r, _ in ws.values()}:
                mine = [w for w in rep["worlds"] if ws[w["id"]][0] == rid]
                g = got[rid]
                self.assertEqual(g["ram_kib"], sum(w["total_ram_kib"] for w in mine))
                self.assertEqual(g["red"], sum(1 for w in mine for i in w["islands"] if i["beacon"] == "red"))
                self.assertEqual(g["worlds_spilling"], sum(1 for w in mine if not w["fits_all_resident"]))
                heavy = min(mine, key=lambda w: (-w["total_ram_kib"], -w["total_disk_kib"], w["id"]))["id"]
                self.assertEqual(g["heaviest_world"], heavy)
            self.assertEqual(sorted(got, key=ff._rkey), [g["realm"] for g in flags(ws)["realms"]])

    def test_flags_and_verdicts(self):
        self.assertEqual(flags({"a": ("r", {1: 0})})["verdict"], "fair")
        r = flags({"a": ("r", {1: 270}), "b": ("s", {1: 0})})
        self.assertEqual((by_realm(r)["r"]["flag"], by_realm(r)["s"]["flag"], r["verdict"]), ("amber", "green", "signal"))
        self.assertEqual(flags({"a": ("r", {1: 299})})["verdict"], "distress")

    def test_spill_alone_flies_red(self):
        r = flags({"a": ("r", {1: 0, 2: 0, 3: 0})})
        g = by_realm(r)["r"]
        self.assertEqual((g["red"], g["worlds_spilling"], g["flag"]), (0, 1, "red"))

    def test_unrealmed_sorted_first(self):
        r = flags({"a": ("zeta", {1: 0}), "b": (None, {1: 0}), "c": ("alpha", {1: 0})})
        self.assertEqual([g["realm"] for g in r["realms"]], [None, "alpha", "zeta"])

    def test_tally_ok(self):
        ws = {"a": ("r", {1: 2}), "b": (None, {1: 0})}
        realms = [{"id": None, "worlds": 1, "islands": 1, "asset_definitions": 0},
                  {"id": "r", "worlds": 1, "islands": 1, "asset_definitions": 2}]
        self.assertEqual(flags(ws, realms)["tally_mismatches"], [])

    def test_tally_mismatch_and_missing_row(self):
        ws = {"a": ("r", {1: 2}), "b": ("s", {1: 0})}
        m = flags(ws, [{"id": "r", "worlds": 2, "islands": 1, "asset_definitions": 2}])["tally_mismatches"]
        self.assertEqual(m, [{"realm": "r", "field": "worlds", "claimed": 2, "found": 1},
                             {"realm": "s", "field": "missing_row", "claimed": None, "found": 1}])

    def test_ghost_realm_row(self):
        m = flags({"a": ("r", {1: 0})}, [{"id": "r", "worlds": 1}, {"id": "ghost", "worlds": 3}])["tally_mismatches"]
        self.assertEqual(m, [{"realm": "ghost", "field": "worlds", "claimed": 3, "found": 0}])

    def test_bad_realm_id_refused(self):
        for bad in ("", "  ", 7):
            with self.assertRaises(ff.FlagError):
                flags({"a": (bad, {1: 0})})
        with self.assertRaises(ff.FlagError):
            ff.muster({"format": "nope"}, cfg())

    def test_deterministic_order_invariant(self):
        a = census({"a": ("r", {1: 3, 2: 9}), "b": (None, {4: 1})})
        b = dict(a, worlds=list(reversed(a["worlds"])))
        self.assertEqual(json.dumps(ff.muster(a, cfg()), sort_keys=True), json.dumps(ff.muster(b, cfg()), sort_keys=True))

    def test_real_census_fixtures(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census",
                            os.path.join(FIX, "alpha.json"), os.path.join(FIX, "beta.json"),
                            "--snapshot-date", "2026-10-26", "--bindings", os.path.join(FIX, "bindings.json"),
                            "--output-dir", os.path.join(d, "census")], cwd=ROOT, check=True, capture_output=True)
            code, out, _ = run_cli(os.path.join(d, "census", "census.json"), "--json", "--fail-on-distress")
        r = json.loads(out)
        self.assertEqual((code, r["verdict"], r["tally_mismatches"]), (0, "fair", []))
        self.assertEqual([(g["realm"], g["heaviest_world"]) for g in r["realms"]], [(None, "beta"), ("synthetic-realm", "alpha")])

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(hook["hook"]["values"], ["fair", "signal", "distress"])
        self.assertEqual(set(hook["npc"]["lines"]), set(hook["hook"]["values"]))
        self.assertEqual(hook["npc"]["name"], "Signal Yeoman Marisol")

    def test_cli_exit_codes_and_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            c, m, bad = (os.path.join(d, n) for n in ("c.json", "m.json", "bad.json"))
            with open(c, "w", encoding="utf-8") as f:
                json.dump(census({"a": ("r", {1: 0, 2: 0, 3: 0})}), f)
            with open(m, "w", encoding="utf-8") as f:
                json.dump(census({"a": ("r", {1: 0})}, [{"id": "r", "worlds": 9}]), f)
            with open(bad, "w", encoding="utf-8") as f:
                f.write("{nope")
            self.assertEqual(run_cli(c)[0], 0)
            self.assertEqual(run_cli(c, "--fail-on-distress")[0], 1)
            code, out, _ = run_cli(m, "--fail-on-distress")
            self.assertEqual(code, 1)
            self.assertIn("census says 9, worlds say 1", out)
            for args in ([bad], [os.path.join(d, "none.json")]):
                code, _, err = run_cli(*args)
                self.assertEqual(code, 2)
                self.assertIn("refused", err)


if __name__ == "__main__":
    unittest.main()
