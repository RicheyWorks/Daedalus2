# SPDX-License-Identifier: MIT
"""Tests for G179 Bottle Census (local-clock vs sync census vs Chandy-Lamport markers, G86 tie-in)."""
import copy
import dataclasses
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bottle_census as bc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "bottle-census-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")
SEEDS = (179, 1, 2, 3, 4, 5, 6, 7)


def load():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def cfg(seed=None, **over):
    raw = load()
    if seed is not None:
        raw["seed"] = seed
    raw["census"].update(over)
    return bc.validate(raw)


class TestBottleCensus(unittest.TestCase):
    def test_shipped_marker_wins_others_fail(self):
        for s in SEEDS:
            c = cfg(s)
            self.assertEqual(bc.run(c, "marker").status, bc.WON, s)
            for m in ("local", "sync"):
                self.assertEqual(bc.run(c, m).status, bc.FAILED, (s, m))

    def test_credits_conserved(self):
        for s in SEEDS:
            for m in bc.MODES:
                r = bc.run(cfg(s), m)
                self.assertEqual(r.true_total, sum(i.weight for i in cfg().islands) * cfg().credits_per_weight)

    def test_marker_total_exact_and_cut_consistent(self):
        for s in SEEDS:
            for initiator in range(len(cfg().islands)):
                r = bc.run(cfg(s, initiator=initiator), "marker")
                self.assertEqual(r.census_total, r.true_total, (s, initiator))
                self.assertTrue(r.consistent, (s, initiator))
                self.assertTrue(bc.cut_consistent(r.log, r.cut), (s, initiator))

    def test_lane_state_equals_in_transit_oracle(self):
        for s in SEEDS:
            r = bc.run(cfg(s), "marker")
            self.assertEqual(list(r.lane_bottles), bc.in_transit_oracle(r.log, r.cut), s)
            amt = {b.seq: b.amount for b in r.log}
            self.assertEqual(r.counted_at_sea, sum(amt[q] for q in r.lane_bottles), s)

    def test_sync_shortfall_equals_credits_at_sea(self):
        for s in SEEDS:
            c = cfg(s)
            r = bc.run(c, "sync")
            at_sea = sum(b.amount for b in r.log if b.sent < c.start <= b.arrive)
            self.assertEqual(r.true_total - r.census_total, at_sea, s)
            self.assertEqual(at_sea, sum(b.amount for b in r.log if b.seq in bc.in_transit_oracle(r.log, r.cut)))
            self.assertTrue(r.consistent, s)

    def test_local_skew_can_break_the_cut(self):
        bad = [s for s in SEEDS if not bc.run(cfg(s), "local").consistent]
        self.assertGreater(len(bad), 0)
        # no skew: local counting is the sync census
        for s in SEEDS:
            a, b = bc.run(cfg(s, max_skew=0), "local"), bc.run(cfg(s, max_skew=0), "sync")
            self.assertEqual((a.census_total, a.cut), (b.census_total, b.cut), s)

    def test_non_fifo_lanes_can_break_markers(self):
        wrong = [s for s in SEEDS if bc.run(cfg(s), "marker", fifo=False).census_total != bc.run(cfg(s)).true_total]
        self.assertGreater(len(wrong), 0)
        # with every delay equal, lanes are FIFO anyway and markers are exact again
        for s in SEEDS:
            r = bc.run(cfg(s, max_delay=1), "marker", fifo=False)
            self.assertEqual((r.census_total, r.consistent), (r.true_total, True), s)

    def test_fifo_lanes_never_overtake(self):
        for s in SEEDS:
            r = bc.run(cfg(s), "marker")
            lanes = {}
            for b in sorted(r.log, key=lambda b: b.seq):
                lanes.setdefault((b.src, b.dst), []).append(b.arrive)
            for arr in lanes.values():
                self.assertEqual(arr, sorted(arr), s)

    def test_no_traffic_every_census_exact(self):
        for m in bc.MODES:
            r = bc.run(cfg(send_permille=0), m)
            self.assertEqual((r.status, r.bottles), (bc.WON, 0), m)

    def test_seeded_replay_determinism(self):
        for s in SEEDS:
            for fifo in (True, False):
                a = [bc.receipt(cfg(s), bc.run(cfg(s), m, fifo)) for m in bc.MODES]
                b = [bc.receipt(cfg(s), bc.run(cfg(s), m, fifo)) for m in bc.MODES]
                self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
            self.assertEqual(bc.run(cfg(s)).log, bc.run(cfg(s)).log)

    def test_g86_tie_in_islands(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl = json.load(fh)["islands"]
        c = cfg()
        self.assertEqual([(i.id, i.weight) for i in c.islands], [(i["id"], i["weight"]) for i in isl])
        self.assertTrue({b.src for b in bc.run(c).log} <= set(range(len(isl))))

    def test_validate_rejects_bad_config(self):
        for mut in (lambda r: r.update(v=2), lambda r: r["census"].update(mode="hope"),
                    lambda r: r["census"].update(start=120), lambda r: r["census"].pop("ticks"),
                    lambda r: r["npc"]["lines"].pop("win"), lambda r: r.update(extra=1),
                    lambda r: r["census"].update(initiator=6), lambda r: r["census"].update(ticks=True)):
            raw = copy.deepcopy(load())
            mut(raw)
            with self.assertRaises(bc.CensusError):
                bc.validate(raw)

    def test_receipt_and_npc(self):
        c = cfg()
        rc = bc.receipt(c, bc.run(c))
        self.assertEqual((rc["quest"], rc["status"]), (bc.QUEST_ID, bc.WON))
        self.assertEqual(rc["census_total"], rc["true_total"])
        self.assertTrue(bc.npc_say(c, "win").startswith("Harbourmaster Tilde: "))

    def test_cli(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(bc.main([DATA]), 0)
            self.assertEqual(bc.main([DATA, "--mode", "sync"]), 1)
        self.assertIn('"consistent": true', buf.getvalue())


if __name__ == "__main__":
    unittest.main()
