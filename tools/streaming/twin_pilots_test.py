# SPDX-License-Identifier: MIT
"""Tests for twin_pilots (G557)."""
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
import twin_pilots as tp  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "twin-pilots-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2)])])
FULL = census([("w", [(i, 0) for i in range(8)])])


def tour(d, calls):
    if not calls:
        return 0
    return min(sum(d[a][b] for a, b in zip((0,) + p, p + (0,))) for p in itertools.permutations(calls))


def oracle(n, edges):
    """Independent: best split of the calls between two boats, each half toured by brute force."""
    d = tp.distances(n, edges)
    calls = list(range(1, n))
    best = None
    for m in range(1 << len(calls)):
        s1 = tuple(c for i, c in enumerate(calls) if (m >> i) & 1)
        s2 = tuple(c for i, c in enumerate(calls) if not (m >> i) & 1)
        v = max(tour(d, s1), tour(d, s2))
        best = v if best is None else min(best, v)
    return best


def plan_of(r):
    return ";".join(">".join(rt) for rt in r["routes"])


class TwinPilotsTest(unittest.TestCase):
    def test_par_matches_split_oracle(self):
        for doc in (DOC, census([("a", [(1, 0)]), ("b", [(2, 0), (3, 0)])])):
            for seed in range(12):
                nodes, edges = tp.chart(doc, seed)
                self.assertEqual(tp.solve(len(nodes), edges)[0], oracle(len(nodes), edges), seed)

    def test_par_oracle_on_full_chart(self):
        for seed in range(3):
            nodes, edges = tp.chart(FULL, seed)
            self.assertEqual(len(nodes), 9)
            self.assertEqual(tp.solve(len(nodes), edges)[0], oracle(len(nodes), edges))

    def test_solo_matches_brute_tour(self):
        for seed in range(8):
            nodes, edges = tp.chart(DOC, seed)
            d = tp.distances(len(nodes), edges)
            self.assertEqual(tp.solo_bells(len(nodes), edges), tour(d, tuple(range(1, len(nodes)))))

    def test_two_boats_never_worse_than_one(self):
        for seed in range(10):
            r = tp.play(DOC, seed)
            self.assertLessEqual(r["par"], r["solo_bells"])

    def test_auto_is_in_step(self):
        for seed in range(6):
            r = tp.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "in_step")
            self.assertEqual(r["bells"], r["par"])
            self.assertEqual(tp.play(DOC, seed, plan=plan_of(r))["verdict"], "in_step")

    def test_solo_plan_is_late_when_slower(self):
        found = False
        for seed in range(20):
            r = tp.play(DOC, seed, auto=True)
            if r["solo_bells"] > r["par"]:
                # one boat does A's route then B's route back to back
                solo = ">".join(r["routes"][0] + r["routes"][1])
                g = tp.play(DOC, seed, plan=solo)
                self.assertEqual(g["verdict"], "late")
                found = True
        self.assertTrue(found)

    def test_missed_call_is_adrift(self):
        r = tp.play(DOC, 1, auto=True)
        a, b = r["routes"]
        g = tp.play(DOC, 1, plan=">".join(a))
        self.assertEqual(g["verdict"], "adrift")
        self.assertTrue(g["missed"])

    def test_not_home_is_adrift(self):
        r = tp.play(DOC, 2, auto=True)
        nodes, edges = tp.chart(DOC, 2)
        out = nodes[tp.adjacency(len(nodes), edges)[0][1]]
        g = tp.play(DOC, 2, plan=">".join(r["routes"][0] + r["routes"][1]) + ";" + out)
        self.assertEqual(g["verdict"], "adrift")
        self.assertFalse(g["missed"])
        self.assertFalse(g["home"])

    def test_refusals(self):
        nodes, edges = tp.chart(DOC, 0)
        adj = tp.adjacency(len(nodes), edges)
        far = next(i for i in range(1, len(nodes)) if i not in adj[0])
        for bad in (f"{nodes[far]}", "nowhere", "harbour;harbour;harbour"):
            with self.assertRaises(tp.PilotError):
                tp.play(DOC, 0, plan=bad)
        with self.assertRaises(tp.PilotError):
            tp.chart(census([("w", [(i, 0) for i in range(9)])]))
        with self.assertRaises(tp.PilotError):
            tp.chart(census([]))

    def test_deterministic_and_seeded(self):
        self.assertEqual(tp.chart(DOC, 4), tp.chart(DOC, 4))
        self.assertTrue(any(tp.chart(DOC, 0)[1] != tp.chart(DOC, s)[1] for s in range(1, 6)))

    def test_real_fixtures_cli(self):
        with tempfile.TemporaryDirectory() as t:
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(FIX, "alpha.json"),
                            os.path.join(FIX, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(FIX, "bindings.json"), "--output-dir", os.path.join(t, "c")], cwd=cb.ROOT, check=True,
                           capture_output=True)
            path = os.path.join(t, "c", "census.json")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(tp.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "in_step")
            self.assertEqual(r["nodes"][:4], ["harbour", "alpha:2", "alpha:9", "beta:4"])
            self.assertEqual(len(r["nodes"]), 7)
            self.assertEqual(r["par"], oracle(len(r["nodes"]), tp.chart(tp._load(path), 7)[1]))
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(tp.main([path, "--plan", "atlantis"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_twin_pilots")
        self.assertEqual(h["hook"]["report_format"], tp.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), tp.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(tp.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Cuthbert"))


if __name__ == "__main__":
    unittest.main()
