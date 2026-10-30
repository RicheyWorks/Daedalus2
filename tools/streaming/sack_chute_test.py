# SPDX-License-Identifier: MIT
"""Tests for sack_chute (G559)."""
import contextlib
import functools
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
import sack_chute as sc  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "sack-chute-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2)])])


def my_sow(bins, i):
    """Independent sowing: walk a ring of bins + hold written as a list."""
    ring = list(bins) + [None]
    k, ring[i] = ring[i], 0
    p = i
    while k:
        p = (p + 1) % len(ring)
        if ring[p] is not None:
            ring[p] += 1
        k -= 1
    return tuple(ring[:-1])


@functools.lru_cache(maxsize=None)
def best(bins):
    """Independent oracle: memoised recursion (the move graph has no cycles)."""
    if not any(bins):
        return 0
    return 1 + min(best(my_sow(bins, i)) for i, k in enumerate(bins) if k)


class SackChuteTest(unittest.TestCase):
    def test_sow_matches_independent(self):
        for bins in itertools.product(range(4), repeat=4):
            for i, k in enumerate(bins):
                if k:
                    self.assertEqual(sc.sow(bins, i)[0], my_sow(bins, i))

    def test_sow_banks_on_pass(self):
        self.assertEqual(sc.sow((0, 0, 3), 2), ((1, 1, 0), 1))
        self.assertEqual(sc.sow((9, 0), 0), ((3, 3), 3))
        with self.assertRaises(sc.ChuteError):
            sc.sow((0, 1), 0)

    def test_par_matches_memo_oracle_exhaustive(self):
        for bins in itertools.product(range(4), repeat=4):
            self.assertEqual(sc.solve(bins)[0], best(bins), bins)

    def test_par_oracle_on_seeded_chutes(self):
        for seed in range(15):
            labels, sacks = sc.chute(DOC, seed)
            self.assertEqual(sc.solve(sacks)[0], best(sacks))
            self.assertLessEqual(sum(sacks), sc.MAX_SACKS)

    def test_greedy_never_beats_par_and_sometimes_loses(self):
        lost = False
        for bins in itertools.product(range(4), repeat=4):
            p = sc.solve(bins)[0]
            g = sc.greedy(bins)
            self.assertGreaterEqual(g, p)
            lost |= g > p
        self.assertTrue(lost)

    def test_auto_is_stowed(self):
        for seed in range(6):
            r = sc.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "stowed")
            self.assertEqual(r["in_hold"], r["total"])
            self.assertEqual(len(r["moves"]), r["par"])

    def test_greedy_play_is_slow_when_worse(self):
        found = False
        for seed in range(40):
            labels, sacks = sc.chute(DOC, seed)
            if sc.greedy(sacks) > sc.solve(sacks)[0]:
                s, mv = sacks, []
                while any(s):
                    i = max(j for j, k in enumerate(s) if k)
                    mv.append(i + 1)
                    s = sc.sow(s, i)[0]
                r = sc.play(DOC, seed, moves=",".join(map(str, mv)))
                self.assertEqual(r["verdict"], "slow")
                found = True
                break
        self.assertTrue(found)

    def test_partial_is_loose(self):
        r = sc.play(DOC, 1, auto=True)
        g = sc.play(DOC, 1, moves=",".join(map(str, r["moves"][:-1])))
        self.assertEqual(g["verdict"], "loose")
        self.assertEqual(sc.play(DOC, 1, moves="")["verdict"], "loose")

    def test_refusals(self):
        labels, sacks = sc.chute(DOC, 0)
        r = sc.play(DOC, 0, auto=True)
        for bad in ("0", "9", "x", ",".join(map(str, r["moves"] + [1]))):
            with self.assertRaises(sc.ChuteError):
                sc.play(DOC, 0, moves=bad)
        with self.assertRaises(sc.ChuteError):
            sc.chute(census([("w", [(i, 0) for i in range(7)])]))
        with self.assertRaises(sc.ChuteError):
            sc.chute(census([]))

    def test_padding_and_determinism(self):
        labels, sacks = sc.chute(census([("solo", [(1, 4)])]), 3)
        self.assertEqual(labels, ["solo:1", "spare:1", "spare:2", "spare:3"])
        self.assertTrue(all(1 <= k <= 3 for k in sacks))
        self.assertEqual(sc.chute(DOC, 5), sc.chute(DOC, 5))
        self.assertTrue(any(sc.chute(DOC, 0) != sc.chute(DOC, s) for s in range(1, 8)))

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
                self.assertEqual(sc.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "stowed")
            self.assertEqual(r["bins"], ["alpha:2", "alpha:9", "beta:4", "spare:1"])
            self.assertEqual(r["par"], best(tuple(r["sacks"])))
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(sc.main([path, "--moves", "7"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_sack_chute")
        self.assertEqual(h["hook"]["report_format"], sc.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), sc.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(sc.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Peregrine"))


if __name__ == "__main__":
    unittest.main()
