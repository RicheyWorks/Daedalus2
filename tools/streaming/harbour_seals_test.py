# SPDX-License-Identifier: MIT
"""Tests for Harbour Seals (G525): each verdict, field diffs, order invariance, real census + G505 baseline, CLI."""
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
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402
import harbour_seals as hs  # noqa: E402

HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "harbour-seals-v1.json")
BASELINE = os.path.join(ROOT, "data", "islands", "disk-saver", "beacon-watch-baseline-v1.json")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")


def cfg():
    with open(cb.DEFAULT_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def census(worlds, date="2026-10-29", shas=("aa", "bb")):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date, "sources": [{"sha256": s} for s in shas],
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in sorted(isl.items())]}
                       for w, isl in sorted(worlds.items())]}


C = census({"a": {1: 0, 2: 270}, "b": {4: 10}})


def report(c=C, conf=None):
    return cb.plan(c, conf or cfg())


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = hs.main(list(args))
    return code, out.getvalue(), err.getvalue()


def real_census():
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, "-B", "-m", "tools.world_census",
                        os.path.join(FIX, "alpha.json"), os.path.join(FIX, "beta.json"),
                        "--snapshot-date", "2026-10-26", "--bindings", os.path.join(FIX, "bindings.json"),
                        "--output-dir", os.path.join(d, "census")], cwd=ROOT, check=True, capture_output=True)
        with open(os.path.join(d, "census", "census.json"), encoding="utf-8-sig") as f:
            return json.load(f)


class SealTest(unittest.TestCase):
    def test_fresh_report_is_sealed(self):
        r = hs.seal(C, report(), cfg())
        self.assertEqual((r["verdict"], r["diff_count"], r["reasons"]), ("sealed", 0, []))

    def test_unsealed_without_sources(self):
        rep = report()
        rep["census_sources"] = []
        self.assertEqual(hs.seal(C, rep, cfg())["verdict"], "unsealed")
        del rep["census_sources"]
        self.assertEqual(hs.seal(C, rep, cfg())["verdict"], "unsealed")

    def test_stale_sources_date_budget(self):
        old = census({"a": {1: 0, 2: 270}, "b": {4: 10}}, shas=("aa", "cc"))
        r = hs.seal(C, report(old), cfg())
        self.assertEqual(r["verdict"], "stale")
        self.assertIn("census_sources differ from the census", r["reasons"])
        r = hs.seal(C, report(census({"a": {1: 0, 2: 270}, "b": {4: 10}}, date="2026-10-01")), cfg())
        self.assertEqual(r["verdict"], "stale")
        conf = cfg()
        conf["budget"]["ram_budget_kib"] = 36000
        r = hs.seal(C, report(conf=conf), cfg())
        self.assertEqual((r["verdict"], r["reasons"]), ("stale", ["budget differs from the current config"]))

    def test_tampered_beacon(self):
        rep = report()
        rep["worlds"][0]["islands"][1]["beacon"] = "green"
        r = hs.seal(C, rep, cfg())
        self.assertEqual(r["verdict"], "tampered")
        self.assertEqual(r["diffs"], [{"path": "worlds[a].islands[slot 2].beacon", "kind": "changed",
                                       "expected": "amber", "found": "green"}])

    def test_tampered_missing_and_extra(self):
        rep = report()
        del rep["worlds"][1]
        rep["worlds"][0]["note"] = "hand edit"
        kinds = {(d["path"].split(".")[0], d["kind"]) for d in hs.seal(C, rep, cfg())["diffs"]}
        self.assertIn(("worlds[b]", "missing"), kinds)
        self.assertIn(("worlds[a]", "extra"), kinds)

    def test_type_change_is_a_diff(self):
        rep = report()
        rep["worlds"][0]["max_resident"] = float(rep["worlds"][0]["max_resident"])
        self.assertEqual(hs.seal(C, rep, cfg())["verdict"], "tampered")

    def test_reordering_is_not_a_diff(self):
        rep = report()
        rep["worlds"].reverse()
        for w in rep["worlds"]:
            w["islands"].reverse()
        self.assertEqual(hs.seal(C, rep, cfg())["verdict"], "sealed")

    def test_random_single_edits_always_caught(self):
        rng = random.Random(525)
        base = report()
        leaves = [p for p in hs.flatten(base) if isinstance(hs.flatten(base)[p], int) and not p.startswith("budget")
                  and not p.startswith("cost_model") and p != "version" and not p.endswith(".slot")]
        for _ in range(150):
            rep = copy.deepcopy(base)
            path = rng.choice(leaves)
            # walk to the leaf through the keyed path and bump it
            node, parts = rep, path.replace("]", "").replace("[", ".").split(".")
            for p in parts[:-1]:
                if isinstance(node, list):
                    node = next(x for x in node if hs._key(x) == p)
                else:
                    node = node[p]
            node[parts[-1]] += rng.randrange(1, 50)
            r = hs.seal(C, rep, cfg())
            self.assertEqual((r["verdict"], r["diffs"][0]["path"] if r["diffs"] else None), ("tampered", path), path)

    def test_flatten_keys(self):
        f = hs.flatten({"worlds": [{"id": "x", "islands": [{"slot": 3, "v": 1}]}], "e": [], "d": {}})
        self.assertEqual(f, {"worlds[x].id": "x", "worlds[x].islands[slot 3].slot": 3,
                             "worlds[x].islands[slot 3].v": 1, "e": [], "d": {}})

    def test_real_census_seals_g505_baseline(self):
        with open(BASELINE, encoding="utf-8") as f:
            base = json.load(f)
        r = hs.seal(real_census(), base, cfg())
        self.assertEqual(r["verdict"], "sealed", r["reasons"])

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(hook["hook"]["values"], ["sealed", "stale", "tampered", "unsealed"])
        self.assertEqual(set(hook["npc"]["lines"]), set(hook["hook"]["values"]))
        self.assertEqual(hook["npc"]["name"], "Customs Officer Perpetua")

    def test_refusals(self):
        with self.assertRaises(hs.SealError):
            hs.seal(C, {"format": "nope"}, cfg())
        with self.assertRaises(hs.SealError):
            hs.seal({"format": "nope"}, report(), cfg())

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            c, r, bad = (os.path.join(d, n) for n in ("c.json", "r.json", "bad.json"))
            for path, doc in ((c, C), (r, report())):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(doc, f)
            with open(bad, "w", encoding="utf-8") as f:
                f.write("{nope")
            self.assertEqual(run_cli(c, r, "--fail-on-broken")[0], 0)
            rep = report()
            rep["summary"]["red"] = 9
            with open(r, "w", encoding="utf-8") as f:
                json.dump(rep, f)
            code, out, _ = run_cli(c, r, "--json")
            self.assertEqual((code, json.loads(out)["verdict"]), (0, "tampered"))
            code, out, _ = run_cli(c, r, "--fail-on-broken")
            self.assertEqual(code, 1)
            self.assertIn("summary.red: expected 0, found 9", out)
            code, _, err = run_cli(c, bad)
            self.assertEqual(code, 2)
            self.assertIn("refused", err)
            self.assertEqual(run_cli(os.path.join(d, "none.json"), r)[0], 2)


if __name__ == "__main__":
    unittest.main()
