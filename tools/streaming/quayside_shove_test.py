# SPDX-License-Identifier: MIT
"""Tests for quayside_shove (G558)."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import quayside_shove as qs  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "quayside-shove-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2)])])
ONE = census([("solo", [(1, 4)])])


def layered(walls, marks, player, crates):
    """Independent oracle: frontier-by-frontier search with plain sets, own move rules."""
    def go(p, cs, dr, dc):
        n = (p[0] + dr, p[1] + dc)
        if n in walls:
            return None
        if n in cs:
            b = (n[0] + dr, n[1] + dc)
            if b in walls or b in cs:
                return None
            cs = frozenset(set(cs) - {n} | {b})
        return n, cs
    frontier, seen, depth = {(player, frozenset(crates))}, set(), 0
    while frontier:
        if any(cs == marks for _, cs in frontier):
            return depth
        seen |= frontier
        nxt = set()
        for p, cs in frontier:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                t = go(p, cs, dr, dc)
                if t and t not in seen:
                    nxt.add(t)
        frontier, depth = nxt, depth + 1
    return None


def parse(rows):
    walls, marks, crates, player = set(), set(), set(), None
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                walls.add((r, c))
            if ch in ".*+":
                marks.add((r, c))
            if ch in "$*":
                crates.add((r, c))
            if ch in "@+":
                player = (r, c)
    return frozenset(walls), frozenset(marks), player, frozenset(crates)


class QuaysideShoveTest(unittest.TestCase):
    def test_par_matches_layered_oracle(self):
        for doc in (DOC, ONE):
            for seed in range(6):
                y = qs.yard(doc, seed)
                self.assertEqual(y["par"], layered(y["walls"], y["marks"], y["player"], y["crates"]), seed)

    def test_hand_yard_par(self):
        w, m, p, c = parse(["#####", "#@$.#", "#####"])
        self.assertEqual(qs.solve(w, m, p, c), (1, "R"))
        w, m, p, c = parse(["######", "#    #", "# $  #", "#@  .#", "######"])
        par, plan = qs.solve(w, m, p, c)
        self.assertEqual(par, layered(w, m, p, c))

    def test_unsolvable_corner(self):
        w, m, p, c = parse(["#####", "#$ .#", "# @ #", "#####"])
        self.assertEqual(qs.solve(w, m, p, c), (None, None))
        self.assertIsNone(layered(w, m, p, c))

    def test_auto_is_tidy(self):
        for seed in range(6):
            r = qs.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "tidy")
            self.assertEqual(r["steps"], r["par"])
            self.assertEqual(r["on_marks"], 3)

    def test_wasted_steps_are_shuffled(self):
        y = qs.yard(DOC, 3)
        floor_dirs = [d for d in "UDLR" if qs.move(y["walls"], y["player"], frozenset(), d) and
                      qs.step(y["player"], d) not in y["crates"]]
        d = floor_dirs[0]
        back = {"U": "D", "D": "U", "L": "R", "R": "L"}[d]
        r = qs.play(DOC, 3, moves=d + back + y["plan"])
        self.assertEqual(r["verdict"], "shuffled")
        self.assertEqual(r["steps"], y["par"] + 2)

    def test_partial_is_stuck_not_deadlocked(self):
        y = qs.yard(DOC, 2)
        r = qs.play(DOC, 2, moves=y["plan"][:-1])
        self.assertEqual(r["verdict"], "stuck")
        self.assertFalse(r["deadlocked"])
        self.assertEqual(qs.play(DOC, 2, moves="")["verdict"], "stuck")

    def test_deadlock_detected(self):
        found = False
        for seed in range(10):
            y = qs.yard(DOC, seed)
            for i in range(1, len(y["plan"]) + 1):
                for d in "UDLR":
                    try:
                        r = qs.play(DOC, seed, moves=y["plan"][:i - 1] + d)
                    except qs.ShoveError:
                        continue
                    if r["verdict"] == "stuck" and r["deadlocked"]:
                        found = True
                        break
                if found:
                    break
            if found:
                break
        self.assertTrue(found)

    def test_refusals(self):
        y = qs.yard(DOC, 0)
        blocked = next(d for d in "UDLR" if qs.move(y["walls"], y["player"], y["crates"], d) is None) \
            if any(qs.move(y["walls"], y["player"], y["crates"], d) is None for d in "UDLR") else None
        if blocked:
            with self.assertRaises(qs.ShoveError):
                qs.play(DOC, 0, moves=blocked)
        for bad in ("X", y["plan"] + "U"):
            with self.assertRaises(qs.ShoveError):
                qs.play(DOC, 0, moves=bad)
        with self.assertRaises(qs.ShoveError):
            qs.play(census([]), 0)

    def test_crates_are_costliest_islands(self):
        self.assertEqual(qs.crates_for(DOC), ["alpha:2", "alpha:3", "beta:5"])
        self.assertEqual(qs.crates_for(ONE), ["solo:1"])

    def test_deterministic_and_seeded(self):
        self.assertEqual(qs.play(DOC, 4)["start"], qs.play(DOC, 4)["start"])
        self.assertTrue(any(qs.play(DOC, 0)["start"] != qs.play(DOC, s)["start"] for s in range(1, 6)))
        r = qs.play(DOC, 1)
        self.assertEqual(sum(row.count("$") + row.count("*") for row in r["start"]), 3)
        self.assertEqual(len(r["start"]), qs.SIZE)

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
                self.assertEqual(qs.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "tidy")
            self.assertEqual(r["crates"], ["alpha:2", "alpha:9", "beta:4"])
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(qs.main([path, "--moves", "Q"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_quayside_shove")
        self.assertEqual(h["hook"]["report_format"], qs.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), qs.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(qs.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Hamish"))


if __name__ == "__main__":
    unittest.main()
