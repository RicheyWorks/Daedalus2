# SPDX-License-Identifier: MIT
"""Tests for channel_dash (G561)."""
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
import channel_dash as cd  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "channel-dash-v1.json")
FIX = os.path.join(cb.ROOT, "tools", "world_census", "fixtures")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2)])])
ONE = census([("solo", [(1, 4)])])


def barges_at(lanes, t):
    """Independent: drift each barge cell forward t ticks, one tick at a time."""
    out = []
    for cells, v in lanes:
        now = set(cells)
        for _ in range(t):
            now = {(c + v) % cd.WIDTH for c in now}
        out.append(now)
    return out


def oracle(lanes, dock, start, limit=200):
    """Independent: real-time layered search over positions, no modular state."""
    home = len(lanes) + 1
    frontier = {(home, start)}
    for t in range(limit + 1):
        if (0, dock) in frontier:
            return t
        bz = barges_at(lanes, t + 1)
        nxt = set()
        for r, c in frontier:
            for dr, dc in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr <= home and 0 <= nc < cd.WIDTH:
                    if 1 <= nr <= len(lanes) and nc in bz[nr - 1]:
                        continue
                    nxt.add((nr, nc))
        frontier = nxt
    return None


class ChannelDashTest(unittest.TestCase):
    def test_busy_matches_drift(self):
        labels, lanes, dock, start = cd.lanes_for(DOC, 1)
        for t in range(12):
            bz = barges_at(lanes, t)
            for i in range(len(lanes)):
                for c in range(cd.WIDTH):
                    self.assertEqual(cd.busy(lanes, i + 1, c, t), c in bz[i])

    def test_par_matches_oracle(self):
        for doc in (DOC, ONE):
            for seed in range(10):
                labels, lanes, dock, start = cd.lanes_for(doc, seed)
                self.assertEqual(cd.solve(lanes, dock, start)[0], oracle(lanes, dock, start), seed)

    def test_empty_channel_par(self):
        lanes = [(frozenset(), 1)] * 3
        self.assertEqual(cd.solve(lanes, 2, 2), (4, "UUUU"))
        self.assertEqual(cd.solve(lanes, 5, 2)[0], 7)

    def test_wall_lane_is_unsolvable(self):
        lanes = [(frozenset(range(cd.WIDTH)), 1)]
        self.assertEqual(cd.solve(lanes, 0, 0), (None, None))
        self.assertIsNone(oracle(lanes, 0, 0, limit=30))

    def test_auto_is_swift(self):
        for seed in range(6):
            r = cd.play(DOC, seed, auto=True)
            self.assertEqual(r["verdict"], "swift")
            self.assertEqual(r["ticks"], r["par"])
            self.assertIsNone(r["hit_tick"])

    def test_waiting_is_safe(self):
        for seed in range(20):
            labels, lanes, dock, start = cd.lanes_for(DOC, seed)
            plan = cd.solve(lanes, dock, start)[1]
            # a wait on the near quay shifts the whole plan by a tick; keep it only if still clear
            r = cd.play(DOC, seed, moves="." * cd.WIDTH + plan)
            self.assertEqual(r["verdict"], "safe")
            return

    def test_swamped_on_hit(self):
        found = False
        for seed in range(30):
            labels, lanes, dock, start = cd.lanes_for(DOC, seed)
            home = len(lanes) + 1
            if cd.busy(lanes, home - 1, start, 1):
                r = cd.play(DOC, seed, moves="U")
                self.assertEqual(r["verdict"], "swamped")
                self.assertEqual(r["hit_tick"], 1)
                found = True
                break
        self.assertTrue(found)

    def test_not_arrived_is_swamped(self):
        r = cd.play(DOC, 2, moves="")
        self.assertEqual(r["verdict"], "swamped")
        self.assertIsNone(r["hit_tick"])

    def test_refusals(self):
        r = cd.play(DOC, 0, auto=True)
        for bad in ("X", "D", r["moves"] + "."):
            with self.assertRaises(cd.DashError):
                cd.play(DOC, 0, moves=bad)
        with self.assertRaises(cd.DashError):
            cd.lanes_for(census([]))

    def test_lanes_padded_and_capped(self):
        self.assertEqual(cd.lanes_for(ONE, 0)[0], ["solo:1", "lane:1", "lane:2"])
        big = census([("w", [(i, i) for i in range(8)])])
        self.assertEqual(len(cd.lanes_for(big, 0)[0]), cd.MAX_LANES)
        self.assertEqual(cd.lanes_for(DOC, 4), cd.lanes_for(DOC, 4))
        self.assertTrue(any(cd.lanes_for(DOC, 0) != cd.lanes_for(DOC, s) for s in range(1, 6)))

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
                self.assertEqual(cd.main([path, "--seed", "7", "--auto", "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual(r["verdict"], "swift")
            self.assertEqual(r["lanes"], ["alpha:2", "alpha:9", "beta:4"])
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(cd.main([path, "--moves", "Q"]), 2)

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_channel_dash")
        self.assertEqual(h["hook"]["report_format"], cd.FORMAT)
        self.assertEqual(tuple(h["hook"]["values"]), cd.VERDICTS)
        self.assertEqual(set(h["npc"]["lines"]), set(cd.VERDICTS))
        self.assertTrue(h["npc"]["name"].endswith("Isadora"))


if __name__ == "__main__":
    unittest.main()
