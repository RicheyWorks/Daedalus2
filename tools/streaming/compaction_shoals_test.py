# SPDX-License-Identifier: MIT
"""Tests for G86 Compaction Shoals."""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import compaction_shoals as m  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")
JOURNAL = os.path.join(ROOT, "data", "islands", "disk-saver", "journal-tide-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = m.validate(raw())
        self.assertEqual(c.npc_name, "Sorter Merge")

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d["shoals"].update(memtable=0),
                    lambda d: d["shoals"].update(get_permille=990),
                    lambda d: d["islands"].append(dict(d["islands"][0])),
                    lambda d: d["npc"]["lines"].pop("win")):
            d = raw()
            mut(d)
            with self.assertRaises(m.ShoalsError):
                m.validate(d)


class TreeTest(unittest.TestCase):
    def test_lookup_newest_and_tombstone(self):
        sh = m.Shoals(2)
        sh.put("a", 1); sh.put("b", 2)      # flush run 1
        sh.put("a", 3); sh.delete("b")      # flush run 2
        self.assertEqual(sh.get("a"), 3)
        self.assertIsNone(sh.get("b"))
        self.assertEqual(sh.runs(), 2)

    def test_compact_merges_and_drops_bottom_tombstones(self):
        sh = m.Shoals(2)
        sh.put("a", 1); sh.put("b", 2)
        sh.put("a", 3); sh.delete("b")
        io = sh.io
        sh.compact(0)
        self.assertEqual(sh.runs(), 1)
        self.assertEqual(sh.levels[1], [[("a", 3)]])
        self.assertEqual(sh.io - io, 1)

    def test_tombstone_kept_above_deeper_data(self):
        sh = m.Shoals(1)
        sh.put("k", 1); sh.compact(0); sh.compact(1)   # k lives on L2
        sh.delete("k"); sh.compact(0)                  # tombstone to L1, L2 non-empty
        self.assertEqual(sh.levels[1], [[("k", None)]])
        self.assertIsNone(sh.get("k"))

    def test_probe_counting(self):
        sh = m.Shoals(1)
        for i in range(5):
            sh.put(f"k{i}", i)
        sh.get("k0")
        self.assertEqual(sh.probes, 5)


class SimTest(unittest.TestCase):
    def setUp(self):
        self.c = m.validate(raw())

    def test_deterministic_ops(self):
        self.assertEqual(m.ops(self.c), m.ops(self.c))
        kinds = {k for k, _, _ in m.ops(self.c)}
        self.assertEqual(kinds, {"put", "del", "get"})

    def test_leveled_wins(self):
        r = m.simulate(self.c, m.leveled())
        self.assertEqual(r.status, m.WON)
        self.assertLessEqual(r.io, self.c.io_budget)
        self.assertLessEqual(r.probes_x100, self.c.max_probes_x100)

    def test_never_compact_drowns_reads(self):
        r = m.simulate(self.c, m.never_policy)
        self.assertEqual((r.status, r.reason), (m.FAILED, m.FAIL_READS))
        self.assertEqual(r.runs, r.flushes)

    def test_every_flush_runs_out_of_ink(self):
        r = m.simulate(self.c, m.every_flush_policy)
        self.assertEqual((r.status, r.reason), (m.FAILED, m.FAIL_IO))
        self.assertEqual(r.runs, 1)

    def test_tradeoff_ordering(self):
        rs = [m.simulate(self.c, p) for p in (m.never_policy, m.leveled(), m.every_flush_policy)]
        self.assertTrue(rs[0].io < rs[1].io < rs[2].io)
        self.assertTrue(rs[0].probes_x100 > rs[1].probes_x100 > rs[2].probes_x100)

    def test_lookups_match_dict_across_seeds_and_policies(self):
        for seed in range(1, 6):
            d = raw(); d["seed"] = seed; d["shoals"]["ops"] = 1500
            c = m.validate(d)
            for p in (m.leveled(2, 3), m.never_policy, m.every_flush_policy):
                m.simulate(c, p)  # raises on any mismatch

    def test_g79_tie_in(self):
        with open(JOURNAL, encoding="utf-8") as fh:
            j = json.load(fh)
        self.assertEqual(m.islands_from_journal(j), raw()["islands"])

    def test_receipt_and_cli(self):
        r = m.simulate(self.c)
        rec = m.receipt(self.c, r)
        self.assertEqual(rec["quest"], m.QUEST_ID)
        self.assertEqual(m.main([DATA]), 0)
        self.assertEqual(m.main([DATA, "--policy", "never"]), 1)


if __name__ == "__main__":
    unittest.main()
