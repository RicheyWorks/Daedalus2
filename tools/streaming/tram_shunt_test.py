# SPDX-License-Identifier: MIT
"""Tests for tram_shunt (G566)."""
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
import tram_shunt as ts  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "tram-shunt-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2)])])
ONE = census([("solo", [(1, 4)])])


def oracle(order):
    """Independent layered search; yard as a dict of lists, frozen to strings."""
    n = len(order)

    def key(y):
        return (tuple(y["in"]), tuple(y["A"]), tuple(y["B"]), y["out"])

    frontier = {key({"in": list(order), "A": [], "B": [], "out": 0})}
    seen, depth = set(), 0
    while frontier:
        if any(k[3] == n for k in frontier):
            return depth
        seen |= frontier
        nxt = set()
        for inb, a, b, out in frontier:
            srcs = {"in": list(inb), "A": list(a), "B": list(b)}
            for src in ("in", "A", "B"):
                if not srcs[src]:
                    continue
                w = srcs[src][0] if src == "in" else srcs[src][-1]
                for dst in ("A", "B", "out"):
                    if dst == src:
                        continue
                    y = {k: list(v) for k, v in srcs.items()}
                    y["out"] = out
                    if src == "in":
                        y["in"].pop(0)
                    else:
                        y[src].pop()
                    if dst == "out":
                        if w != out + 1:
                            continue
                        y["out"] += 1
                    else:
                        y[dst].append(w)
                    k = key(y)
                    if k not in seen:
                        nxt.add(k)
        frontier, depth = nxt, depth + 1
    return None


class TramShuntTest(unittest.TestCase):
    def test_par_matches_oracle_all_small_trains(self):
        for n in (3, 4, 5):
            for order in itertools.permutations(range(1, n + 1)):
                self.assertEqual(ts.solve(order)[0], oracle(order), order)

    def test_par_matches_oracle_seeded(self):
        for doc in (DOC, ONE):
            for seed in range(6):
                names, order = ts.train(doc, seed)
                self.assertEqual(ts.solve(order)[0], oracle(order))
                g = ts.greedy(order)
                self.assertTrue(g is None or g > ts.solve(order)[0])

    def test_par_bounds(self):
        self.assertEqual(ts.solve((1, 2, 3, 4, 5, 6))[0], 6)
        self.assertEqual(ts.solve((6, 5, 4, 3, 2, 1))[0], 11)  # five into one siding, then out
        for seed in range(10):
            names, order = ts.train(DOC, seed)
            par = ts.solve(order)[0]
            self.assertGreaterEqual(par, 6)

    def test_greedy_never_beats_par_and_sometimes_loses(self):
        worse = False
        for order in itertools.permutations(range(1, 6)):
            g, p = ts.greedy(order), ts.solve(order)[0]
            if g is not None:
                self.assertGreaterEqual(g, p)
            worse |= g is None or g > p
        self.assertTrue(worse)

    def test_auto_is_smart(self):
        for seed in range(6):
            r = ts.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "smart")
            self.assertEqual(r["out"], ts.TRAIN)

    def test_detour_is_slow(self):
        names, order = ts.train(DOC, 2)
        plan = ts.solve(order)[1]
        i = next(k for k, m in enumerate(plan) if m.endswith("A") or m.endswith("B"))
        src = plan[i][-1]
        other = "B" if src == "A" else "A"
        moves = plan[:i + 1] + [src + other, other + src] + plan[i + 1:]
        r = ts.play(DOC, 2, moves=",".join(moves))
        self.assertEqual(r["verdict"], "slow")
        self.assertEqual(r["count"], len(plan) + 2)

    def test_partial_is_jammed(self):
        r = ts.play(DOC, 1, auto=True)
        g = ts.play(DOC, 1, moves=",".join(r["moves"][:-1]))
        self.assertEqual(g["verdict"], "jammed")
        self.assertEqual(ts.play(DOC, 1, moves="")["verdict"], "jammed")

    def test_refusals(self):
        names, order = ts.train(DOC, 0)
        for bad in ("xy", "AA", "Aout", "outA"):
            with self.assertRaises(ts.ShuntError):
                ts.play(DOC, 0, moves=bad)
        if order[0] != 1:
            with self.assertRaises(ts.ShuntError):
                ts.play(DOC, 0, moves="inout")
        r = ts.play(DOC, 0, auto=True)
        with self.assertRaises(ts.ShuntError):
            ts.play(DOC, 0, moves=",".join(r["moves"] + ["inA"]))
        with self.assertRaises(ts.ShuntError):
            ts.train(census([]))

    def test_train_shape(self):
        names, order = ts.train(ONE, 0)
        self.assertEqual(names, ["solo:1"] + [f"spare:{k}" for k in range(1, 6)])
        self.assertEqual(sorted(order), list(range(1, 7)))
        self.assertNotEqual(list(order), list(range(1, 7)))
        self.assertEqual(ts.train(DOC, 3), ts.train(DOC, 3))
        self.assertTrue(any(ts.train(DOC, 0) != ts.train(DOC, s) for s in range(1, 6)))

    def test_step_rules(self):
        s = ((2, 1), (), (), 1)
        self.assertIsNone(ts.step(s, "inout"))
        s = ts.step(s, "inA")
        self.assertEqual(s, ((1,), (2,), (), 1))
        s = ts.step(s, "inout")
        self.assertEqual(ts.step(s, "Aout"), ((), (), (), 3))
        self.assertIsNone(ts.step(s, "Bout"))

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
                self.assertEqual(ts.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "smart")
            self.assertEqual(list(r["wagons"].values())[:3], ["alpha:2", "alpha:9", "beta:4"])
            self.assertGreater(r["par"], ts.TRAIN)
            self.assertTrue(r["greedy_moves"] is None or r["greedy_moves"] > r["par"])
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(ts.main([path, "--moves", "zz"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_tram_shunt")
        self.assertEqual(h["hook"]["report_format"], ts.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), ts.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(ts.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Rosalind"))


if __name__ == "__main__":
    unittest.main()
