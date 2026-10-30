# SPDX-License-Identifier: MIT
"""Tests for seal_roll (G560)."""
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
import seal_roll as sr  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "seal-roll-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2)])])
TWO = census([("w", [(1, 0), (2, 0)])])

# x = east, y = north, z = up; tipping rotates the seal's outward normal
VEC = {"up": (0, 0, 1), "down": (0, 0, -1), "north": (0, 1, 0), "south": (0, -1, 0),
       "east": (1, 0, 0), "west": (-1, 0, 0)}


def rot(v, d):
    x, y, z = v
    if d == "N":
        return (x, z, -y)
    if d == "S":
        return (x, -z, y)
    if d == "E":
        return (z, y, -x)
    return (-z, y, x)


def oracle(walls, marks, dock, start):
    """Independent: layered search with the seal as a 3-D vector and marks as a frozenset."""
    step = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
    st = frozenset([start]) & frozenset(marks)
    frontier, seen, depth = {(start, (0, 0, 1), st)}, set(), 0
    while frontier:
        if any(p == dock and len(m) == len(marks) for p, _, m in frontier):
            return depth
        seen |= frontier
        nxt = set()
        for p, v, m in frontier:
            for d, (dr, dc) in step.items():
                q = (p[0] + dr, p[1] + dc)
                if q in walls:
                    continue
                w = rot(v, d)
                m2 = m | {q} if (q in marks and w == (0, 0, 1)) else m
                t = (q, w, frozenset(m2))
                if t not in seen:
                    nxt.add(t)
        frontier, depth = nxt, depth + 1
    return None


class SealRollTest(unittest.TestCase):
    def test_tip_table_matches_vectors(self):
        for side, v in VEC.items():
            for d in "NSEW":
                self.assertEqual(VEC[sr.tip((3, 3), side, d)[1]], rot(v, d), (side, d))

    def test_four_tips_return_seal(self):
        for d in "NSEW":
            pos, seal = (3, 3), "up"
            for _ in range(4):
                pos, seal = sr.tip(pos, seal, d)
            self.assertEqual(seal, "up")
            pos, seal = sr.tip((3, 3), "up", d)
            self.assertNotEqual(seal, "up")

    def test_par_matches_oracle(self):
        for doc in (DOC, TWO):
            for seed in range(6):
                q = sr.quay(doc, seed)
                self.assertEqual(q["par"], oracle(q["walls"], q["marks"], q["dock"], q["start"]), seed)

    def test_open_yard_hand_par(self):
        border = {(r, c) for r in range(7) for c in range(7) if r in (0, 6) or c in (0, 6)}
        walls = frozenset(border)
        # one mark four squares east: four tips east bring the seal back up
        par, plan = sr.solve(walls, ((1, 5),), (1, 5), (1, 1))
        self.assertEqual((par, plan), (4, "EEEE"))
        # mark next door: one tip leaves the seal east, so more tips are needed
        par, _ = sr.solve(walls, ((1, 2),), (1, 2), (1, 1))
        self.assertEqual(par, oracle(walls, ((1, 2),), (1, 2), (1, 1)))
        self.assertGreater(par, 1)

    def test_auto_is_true(self):
        for seed in range(6):
            r = sr.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "true")
            self.assertEqual(r["count"], r["par"])
            self.assertEqual(len(r["stamped"]), 4)

    def test_detour_is_wobbly(self):
        for seed in range(10):
            q = sr.quay(DOC, seed)
            for a, b in (("N", "S"), ("E", "W"), ("S", "N"), ("W", "E")):
                p, _ = sr.tip(q["start"], "up", a)
                if p not in q["walls"] and p not in q["marks"]:
                    r = sr.play(DOC, seed, tips=a + b + q["plan"])
                    self.assertEqual(r["verdict"], "wobbly")
                    return
        self.fail("no detour found")

    def test_partial_is_off_mark(self):
        q = sr.quay(DOC, 2)
        r = sr.play(DOC, 2, tips=q["plan"][:-1])
        self.assertEqual(r["verdict"], "off_mark")
        self.assertEqual(sr.play(DOC, 2, tips="")["verdict"], "off_mark")

    def test_refusals(self):
        q = sr.quay(DOC, 0)
        wall_dir = None
        for d in "NSEW":
            if sr.tip(q["start"], "up", d)[0] in q["walls"]:
                wall_dir = d
        if wall_dir:
            with self.assertRaises(sr.RollError):
                sr.play(DOC, 0, tips=wall_dir)
        with self.assertRaises(sr.RollError):
            sr.play(DOC, 0, tips="X")
        with self.assertRaises(sr.RollError):
            sr.play(DOC, 0, tips="N" * 7)
        with self.assertRaises(sr.RollError):
            sr.quay(census([]))

    def test_marks_capped_and_sorted(self):
        self.assertEqual(sr.labels_for(DOC), ["alpha:1", "alpha:2", "alpha:3", "beta:4"])
        self.assertEqual(sr.labels_for(TWO), ["w:1", "w:2"])

    def test_deterministic_and_seeded(self):
        self.assertEqual(sr.play(DOC, 3)["start"], sr.play(DOC, 3)["start"])
        self.assertTrue(any(sr.play(DOC, 0)["start"] != sr.play(DOC, s)["start"] for s in range(1, 6)))
        rows = sr.play(DOC, 1)["start"]
        self.assertEqual(len(rows), sr.SIZE)
        self.assertEqual(sum(row.count("@") for row in rows), 1)

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
                self.assertEqual(sr.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "true")
            self.assertEqual(r["marks"], {"a": "alpha:2", "b": "alpha:9", "c": "beta:4"})
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(sr.main([path, "--tips", "Z"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_seal_roll")
        self.assertEqual(h["hook"]["report_format"], sr.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), sr.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(sr.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Cornelius"))


if __name__ == "__main__":
    unittest.main()
