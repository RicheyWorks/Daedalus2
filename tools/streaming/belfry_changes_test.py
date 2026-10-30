# SPDX-License-Identifier: MIT
"""Tests for belfry_changes (G565)."""
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
import belfry_changes as bc  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "belfry-changes-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2)])])
ONE = census([("solo", [(1, 4)])])


def my_changes(n):
    """Independent: every bitmask of pair starts with no two adjacent starts."""
    out = []
    for m in range(1, 1 << (n - 1)):
        starts = [i for i in range(n - 1) if m >> i & 1]
        if all(b - a >= 2 for a, b in zip(starts, starts[1:])):
            out.append(starts)
    return out


def oracle(start, islands, tenor):
    """Independent layered search with sets; rows as strings, led as frozensets."""
    n = len(start)
    goal = "".join(map(str, range(1, n + 1)))
    ch = my_changes(n)
    first = "".join(map(str, start))
    frontier = {(first, frozenset({start[0]}) & islands, False)}
    seen, depth = set(), 0
    while frontier:
        if any(r == goal and l == islands for r, l, _ in frontier):
            return depth
        seen |= frontier
        nxt = set()
        for r, l, rest in frontier:
            t = r.index(str(tenor))
            for starts in ch:
                moved = any(t in (p, p + 1) for p in starts)
                if rest and moved:
                    continue
                s = list(r)
                for p in starts:
                    s[p], s[p + 1] = s[p + 1], s[p]
                s = "".join(s)
                k = (s, l | (frozenset({int(s[0])}) & islands), moved)
                if k not in seen:
                    nxt.add(k)
        frontier, depth = nxt, depth + 1
    return None


class BelfryChangesTest(unittest.TestCase):
    def test_change_lists_match(self):
        for n in range(2, 7):
            self.assertEqual(sorted(map(tuple, my_changes(n))), bc.all_changes(n))
        self.assertEqual(len(bc.all_changes(5)), 7)  # Fibonacci minus one
        self.assertEqual(bc.all_changes(5, single=True), [(0,), (1,), (2,), (3,)])

    def test_par_matches_oracle(self):
        for doc in (DOC, ONE):
            for seed in range(8):
                names, isl, tenor, start = bc.ring(doc, seed)
                self.assertEqual(bc.solve(start, isl, tenor)[0], oracle(start, isl, tenor), seed)

    def test_par_oracle_hand_rows(self):
        for row in itertools.islice(itertools.permutations(range(1, 6)), 0, 120, 13):
            isl = frozenset({1, 2, 3})
            self.assertEqual(bc.solve(row, isl, 3)[0], oracle(row, isl, 3), row)

    def test_parallel_never_worse_than_single(self):
        for seed in range(8):
            r = bc.play(DOC, seed)
            self.assertLessEqual(r["par"], r["single_swap_par"])

    def test_auto_is_rung(self):
        for seed in range(6):
            r = bc.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "rung")
            self.assertEqual(r["final"], [1, 2, 3, 4, 5])
            self.assertEqual(r["led"], [1, 2, 3, 4, 5])

    def test_tenor_must_rest(self):
        names, isl, tenor, start = bc.ring(DOC, 0)
        ti = start.index(tenor)
        p = ti if ti < len(start) - 1 else ti - 1
        c = str(p + 1)
        with self.assertRaises(bc.BellError):
            bc.play(DOC, 0, changes=c + "," + c)

    def test_partial_is_unfinished(self):
        r = bc.play(DOC, 1, auto=True)
        g = bc.play(DOC, 1, changes=",".join(r["changes"][:-1]))
        self.assertEqual(g["verdict"], "unfinished")
        self.assertEqual(bc.play(DOC, 1, changes="")["verdict"], "unfinished")

    def test_extra_changes_clatter(self):
        for seed in range(10):
            r = bc.play(DOC, seed, auto=True)
            names, isl, tenor, start = bc.ring(DOC, seed)
            # two identical changes that leave the tenor alone undo each other
            ti = start.index(tenor)
            for p in range(len(start) - 1):
                if ti not in (p, p + 1):
                    try:
                        g = bc.play(DOC, seed, changes=f"{p + 1},{p + 1}," + ",".join(r["changes"]))
                    except bc.BellError:
                        continue
                    self.assertEqual(g["verdict"], "clattered")
                    return
        self.fail("no clatter case")

    def test_refusals(self):
        for bad in ("x", "0", "5", "1+2", "6"):
            with self.assertRaises(bc.BellError):
                bc.play(DOC, 0, changes=bad)
        with self.assertRaises(bc.BellError):
            bc.ring(census([]))

    def test_ring_shape(self):
        names, isl, tenor, start = bc.ring(ONE, 0)
        self.assertEqual(names, ["solo:1", "spare:1", "spare:2", "spare:3", "spare:4"])
        self.assertEqual((isl, tenor), (frozenset({1}), 1))
        names, isl, tenor, start = bc.ring(DOC, 0)
        self.assertEqual(tenor, 3)  # alpha:3 has the most assets
        self.assertNotEqual(start, (1, 2, 3, 4, 5))
        self.assertEqual(bc.ring(DOC, 4), bc.ring(DOC, 4))
        self.assertTrue(any(bc.ring(DOC, 0) != bc.ring(DOC, s) for s in range(1, 6)))

    def test_real_fixtures_cli(self):
        with tempfile.TemporaryDirectory() as t:
            out_dir = os.path.join(t, "c")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(FIX, "alpha.json"),
                            os.path.join(FIX, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(FIX, "bindings.json"), "--output-dir", out_dir], cwd=cb.ROOT, check=True,
                           capture_output=True)
            path = os.path.join(out_dir, "census.json")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(bc.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "rung")
            self.assertEqual(list(r["bells"].values())[:3], ["alpha:2", "alpha:9", "beta:4"])
            self.assertGreaterEqual(r["par"], 4)
            self.assertGreater(r["single_swap_par"], r["par"])
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(bc.main([path, "--changes", "9"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_belfry_changes")
        self.assertEqual(h["hook"]["report_format"], bc.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), bc.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(bc.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Agatha"))


if __name__ == "__main__":
    unittest.main()
