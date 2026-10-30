# SPDX-License-Identifier: MIT
"""Tests for census_riddles (G546)."""
import contextlib
import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import census_riddles as cr  # noqa: E402

ROOT = cb.ROOT
HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "census-riddles-v1.json")
CFG = {"budget": {"ram_budget_kib": 40000, "disk_budget_kib": 32768, "warn_permille": 900}}


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(2, 1), (9, 0)]), ("beta", [(4, 0)]), ("gamma", [(1, 200), (3, 5), (5, 0)])])


def key(quiz):
    return {r["kind"]: r["answer"] for r in quiz["riddles"]}


class RiddlesTest(unittest.TestCase):
    def full(self, doc=DOC, seed=0):
        return cr.draw(doc, CFG, seed, len(cr.KINDS))

    def test_all_kinds_drawn_once(self):
        q = self.full()
        self.assertEqual(sorted(r["kind"] for r in q["riddles"]), sorted(cr.KINDS))
        self.assertEqual([r["id"] for r in q["riddles"]], [f"r{i}" for i in range(1, 10)])

    def test_global_answers(self):
        k = key(self.full())
        self.assertEqual(k["islands_total"], "6")
        self.assertEqual(k["cargo_total"], "206")
        self.assertEqual(k["empty_islands"], "3")
        self.assertEqual(k["widest_world"], "gamma")
        self.assertEqual(k["heaviest_island"], "gamma:1")
        self.assertEqual(k["islands_fit"], "6")

    def test_world_answers_match_cost_model(self):
        for seed in range(12):
            q = self.full(seed=seed)
            for r in q["riddles"]:
                if r["kind"] in ("world_ram", "world_disk", "max_resident"):
                    w = r["question"].split("'")[1]
                    isl = dict(cb.read_census(DOC))[w]
                    ram = [cb.island_cost(n)[0] for _, n in isl]
                    want = {"world_ram": sum(ram), "world_disk": sum(cb.island_cost(n)[1] for _, n in isl),
                            "max_resident": max(len(c) for k in range(len(ram) + 1)
                                                for c in itertools.combinations(ram, k) if sum(c) <= 40000)}[r["kind"]]
                    self.assertEqual(r["answer"], str(want), (seed, r))

    def test_ties_break_by_id(self):
        k = key(self.full(census([("zeta", [(1, 3), (2, 3)]), ("eta", [(7, 3), (8, 3)])])))
        self.assertEqual(k["widest_world"], "eta")
        self.assertEqual(k["heaviest_island"], "eta:7")

    def test_seeded_and_portable(self):
        self.assertEqual(cr.draw(DOC, CFG, 5), cr.draw(DOC, CFG, 5))
        draws = {json.dumps([r["kind"] for r in cr.draw(DOC, CFG, s)["riddles"]]) for s in range(10)}
        self.assertGreater(len(draws), 3)
        moved = census([("gamma", [(1, 200), (3, 5), (5, 0)]), ("beta", [(4, 0)]), ("alpha", [(2, 1), (9, 0)])])
        self.assertEqual(cr.draw(moved, CFG, 5)["riddles"], cr.draw(DOC, CFG, 5)["riddles"])

    def test_count_bounds(self):
        self.assertEqual(len(cr.draw(DOC, CFG, 0, 3)["riddles"]), 3)
        for bad in (0, 21, True, "5"):
            with self.assertRaises(cr.RiddleError):
                cr.draw(DOC, CFG, 0, bad)

    def test_refuses_bad_census_and_config(self):
        with self.assertRaises(cr.RiddleError):
            cr.draw({"format": "nope"}, CFG)
        with self.assertRaises(cr.RiddleError):
            cr.draw(DOC, {"budget": {}})

    def test_refuses_islandless_census(self):
        with self.assertRaises(cr.RiddleError):
            cr.draw(census([("alpha", []), ("beta", [])]), CFG)

    def test_grade_verdicts(self):
        q = cr.draw(DOC, CFG, 1, 4)
        right = {r["id"]: r["answer"] for r in q["riddles"]}
        self.assertEqual(cr.grade(q, right)["verdict"], "shipshape")
        half = dict(right, r1="wrong", r2="wrong")
        self.assertEqual((cr.grade(q, half)["score"], cr.grade(q, half)["verdict"]), (2, "adrift"))
        self.assertEqual(cr.grade(q, {"r1": right["r1"]})["verdict"], "aground")
        with self.assertRaises(cr.RiddleError):
            cr.grade(q, ["nope"])

    def test_answer_normalising(self):
        q = {"seed": 0, "riddles": [{"id": "r1", "kind": "world_ram", "answer": "32792"},
                                    {"id": "r2", "kind": "widest_world", "answer": "alpha"},
                                    {"id": "r3", "kind": "islands_total", "answer": "3"}]}
        g = cr.grade(q, {"r1": " 32,792 ", "r2": "ALPHA", "r3": 3})
        self.assertEqual(g["verdict"], "shipshape")

    def test_cli_hides_answers_unless_key(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "census.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(cr.main([c, "--json"]), 0)
            self.assertTrue(all("answer" not in r for r in json.loads(out.getvalue())["riddles"]))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cr.main([c, "--json", "--key"])
            quiz = json.loads(out.getvalue())
            a = os.path.join(d, "answers.json")
            with open(a, "w", encoding="utf-8") as f:
                json.dump({r["id"]: r["answer"] for r in quiz["riddles"]}, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(cr.main([c, "--answers", a]), 0)
            self.assertIn("shipshape (5/5", out.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cr.main([os.path.join(d, "missing.json")]), 2)

    def test_real_census_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            fx = os.path.join("tools", "world_census", "fixtures")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(fx, "alpha.json"),
                            os.path.join(fx, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(fx, "bindings.json"), "--output-dir", os.path.join(d, "out")],
                           cwd=ROOT, check=True, capture_output=True)
            with open(os.path.join(d, "out", "census.json"), encoding="utf-8-sig") as f:
                doc = json.load(f)
        with open(cb.DEFAULT_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        k = key(cr.draw(doc, cfg, 0, len(cr.KINDS)))
        self.assertEqual(k["islands_total"], "3")
        self.assertEqual(k["heaviest_island"], "alpha:2")
        self.assertEqual(k["empty_islands"], "2")

    def test_hook_covers_grades(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_census_riddles")
        self.assertEqual(h["npc"]["name"], "Tide-clerk Leocadia")
        self.assertEqual(h["hook"]["values"], list(cr.GRADES))
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
