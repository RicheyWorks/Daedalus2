# SPDX-License-Identifier: MIT
"""Tests for smugglers_island (G553)."""
import contextlib
import io
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import smugglers_island as si  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "smugglers-island-v1.json")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "realm_id": r, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]}
                       for w, r, isl in worlds]}


DOC = census([("alpha", "north", [(1, 0), (2, 5), (3, 40)]), ("beta", None, [(1, 2), (4, 0)]),
              ("gamma", "north", [(2, 0), (5, 9), (6, 1)])])


def brute_depth(qs, group):
    """Smallest d such that some strategy of depth d separates the group (plain recursion)."""
    group = frozenset(group)
    if len(group) <= 1:
        return 0
    best = math.inf
    for yes in qs.values():
        a, b = group & yes, group - yes
        if a and b:
            best = min(best, 1 + max(brute_depth(qs, a), brute_depth(qs, b)))
    return best


class SmugglerTest(unittest.TestCase):
    def test_suspects(self):
        s = si.suspects(DOC)
        self.assertEqual([x["label"] for x in s][:3], ["alpha:1", "alpha:2", "alpha:3"])
        self.assertEqual({x["realm"] for x in s}, {"north", "none"})

    def test_questions_unique_and_useful(self):
        sus = si.suspects(DOC)
        qs = si.questions(sus)
        every = frozenset(range(len(sus)))
        keys = set()
        for yes in qs.values():
            self.assertTrue(yes and yes != every)
            k = min(yes, every - yes, key=sorted)
            self.assertNotIn(k, keys)
            keys.add(k)
        self.assertIn("world:alpha", qs)
        self.assertNotIn("realm:none", qs)  # same split as world:beta, so dropped
        self.assertNotIn("realm:north", qs)
        self.assertNotIn("empty", qs)  # same split as cargo>=1

    def test_depth_matches_brute_and_bound(self):
        sus = si.suspects(DOC)
        qs = si.questions(sus)
        depth, _ = si.solver(qs)
        every = frozenset(range(len(sus)))
        self.assertEqual(depth(every), brute_depth(qs, every))
        self.assertGreaterEqual(depth(every), math.ceil(math.log2(len(sus))))
        for group in itertools.combinations(range(len(sus)), 3):
            self.assertEqual(depth(frozenset(group)), brute_depth(qs, group))

    def test_auto_is_sharp_for_every_seed(self):
        for s in range(20):
            r = si.play(DOC, s, auto=True)
            self.assertEqual(r["verdict"], "sharp")
            self.assertLessEqual(len(r["asked"]), r["optimal_questions"])
            self.assertEqual(r["still_possible"], [r["hidden"]])

    def test_answers_truthful(self):
        sus, qs, hidden = si.setup(DOC, 3)
        r = si.play(DOC, 3, list(qs), sus[hidden]["label"])
        for q in r["asked"]:
            self.assertEqual(q["answer"] == "yes", hidden in qs[q["question"]])
        self.assertEqual(r["verdict"], "caught" if len(qs) > r["optimal_questions"] else "sharp")

    def test_guess_without_questions(self):
        sus, _, hidden = si.setup(DOC, 1)
        wrong = [s["label"] for i, s in enumerate(sus) if i != hidden][0]
        self.assertEqual(si.play(DOC, 1, [], wrong)["verdict"], "escaped")
        self.assertEqual(si.play(DOC, 1, [], sus[hidden]["label"])["verdict"], "sharp")

    def test_seeded_hidden(self):
        self.assertEqual(si.setup(DOC, 5)[2], si.setup(DOC, 5)[2])
        self.assertGreater(len({si.setup(DOC, s)[2] for s in range(20)}), 3)

    def test_refusals(self):
        with self.assertRaises(si.SmugglerError):
            si.play(DOC, 0, ["nope"], "alpha:1")
        with self.assertRaises(si.SmugglerError):
            si.play(DOC, 0, [], "omega:1")
        with self.assertRaises(si.SmugglerError):
            si.play(DOC, 0)
        with self.assertRaises(si.SmugglerError):
            si.play(DOC, 0, ["empty"], None)
        with self.assertRaises(si.SmugglerError):
            si.suspects(census([("a", None, [])]))
        with self.assertRaises(si.SmugglerError):
            si.suspects(census([("a", None, [(i, 0) for i in range(41)])]))

    def test_single_suspect(self):
        one = census([("a", None, [(1, 0)])])
        r = si.play(one, 0, auto=True)
        self.assertEqual((r["optimal_questions"], r["asked"], r["verdict"]), (0, [], "sharp"))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "census.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(si.main([c, "--list", "--json"]), 0)
            listing = json.loads(out.getvalue())
            self.assertNotIn("hidden", listing)
            self.assertEqual(len(listing["suspects"]), 8)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(si.main([c, "--auto"]), 0)
            self.assertTrue(out.getvalue().startswith("smuggler's island: sharp"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(si.main([c, "--ask", "world:alpha", "--accuse", "alpha:1"]), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(si.main([c, "--ask", "bogus", "--accuse", "alpha:1"]), 2)

    def test_real_census_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            fx = os.path.join("tools", "world_census", "fixtures")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(fx, "alpha.json"),
                            os.path.join(fx, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(fx, "bindings.json"), "--output-dir", os.path.join(d, "out")],
                           cwd=cb.ROOT, check=True, capture_output=True)
            with open(os.path.join(d, "out", "census.json"), encoding="utf-8-sig") as f:
                doc = json.load(f)
        r = si.play(doc, 0, auto=True)
        self.assertEqual((r["suspects"], r["optimal_questions"], r["verdict"]), (3, 2, "sharp"))

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_smugglers_island")
        self.assertEqual(h["npc"]["name"], "Exciseman Bartholomew")
        self.assertEqual(h["hook"]["values"], list(si.VERDICTS))
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
