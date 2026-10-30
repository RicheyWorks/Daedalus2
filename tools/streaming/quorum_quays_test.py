# SPDX-License-Identifier: MIT
"""Tests for G110 Quorum Quays."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import quorum_quays as q  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "quorum-quays-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = q.validate(raw())
        self.assertEqual(c.npc_name, "Harbourmaster Quill")
        self.assertEqual((c.replicas, c.read_quorum, c.write_quorum), (5, 3, 3))

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["quays"].update(read_quorum=6),
                    lambda d: d["quays"].update(write_quorum=0),
                    lambda d: d["quays"].update(max_down=6),
                    lambda d: d["quays"].update(write_permille=1001),
                    lambda d: d["quays"].update(ticks=True),
                    lambda d: d["quays"].pop("min_available_permille"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("read")):
            d = raw()
            mut(d)
            with self.assertRaises(q.QuayError):
                q.validate(d)


class ClusterTest(unittest.TestCase):
    def test_write_needs_w_open_quays(self):
        cl = q.QuayCluster(3)
        self.assertFalse(cl.write("k", 1, [0], 2))
        self.assertTrue(cl.write("k", 1, [0, 2], 2))
        self.assertEqual([x.get("k") for x in cl.quays], [1, None, 1])

    def test_read_takes_highest_version(self):
        cl = q.QuayCluster(3)
        cl.write("k", 1, [0, 1, 2], 3)
        cl.write("k", 2, [2], 1)
        self.assertEqual(cl.read("k", [0, 2], 2), 2)
        self.assertEqual(cl.read("k", [0, 1], 2), 1)
        self.assertIsNone(cl.read("k", [0], 2))
        self.assertEqual(cl.read("missing", [0], 1), 0)

    def test_overlapping(self):
        self.assertTrue(q.overlapping(3, 3, 5))
        self.assertFalse(q.overlapping(2, 3, 5))


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = q.validate(raw())

    def test_majority_quorums_win(self):
        r = q.simulate(self.c)
        self.assertEqual((r.status, r.stale_reads), (q.WON, 0))
        self.assertGreaterEqual(r.available_permille, self.c.min_available_permille)

    def test_overlap_is_never_stale(self):
        n = self.c.replicas
        for r in range(1, n + 1):
            for w in range(1, n + 1):
                res = q.simulate(self.c, r, w)
                if q.overlapping(r, w, n):
                    self.assertEqual(res.stale_reads, 0, (r, w))

    def test_one_one_is_stale(self):
        r = q.simulate(self.c, 1, 1)
        self.assertEqual((r.status, r.reason), (q.FAILED, q.FAIL_STALE))
        self.assertEqual(r.available_permille, 1000)

    def test_all_quays_stalls(self):
        r = q.simulate(self.c, 5, 5)
        self.assertEqual((r.status, r.reason), (q.FAILED, q.FAIL_AVAIL))
        self.assertEqual(r.stale_reads, 0)

    def test_only_majority_wins_shipped_storms(self):
        self.assertEqual(q.best_quorums(self.c), [(3, 3)])

    def test_calm_sea_lets_read_one_write_all_win(self):
        d = raw()
        d["quays"]["max_down"] = 0
        c = q.validate(d)
        self.assertEqual(q.simulate(c, 1, 5).status, q.WON)

    def test_bad_quorum_override(self):
        with self.assertRaises(q.QuayError):
            q.simulate(self.c, 0, 3)

    def test_deterministic(self):
        self.assertEqual(q.simulate(self.c), q.simulate(self.c))


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = q.islands_from_shoals(json.load(fh))
        c = q.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_win_and_traps(self):
        self.assertEqual(q.main([DATA]), 0)
        self.assertEqual(q.main([DATA, "--r", "1", "--w", "1"]), 1)
        self.assertEqual(q.main([DATA, "--r", "5", "--w", "5"]), 1)

    def test_receipt_and_npc(self):
        c = q.validate(raw())
        rc = q.receipt(c, q.simulate(c), 3, 3)
        self.assertEqual((rc["quest"], rc["stale_reads"]), (q.QUEST_ID, 0))
        self.assertTrue(q.npc_say(c, "storm").startswith("Harbourmaster Quill: "))


if __name__ == "__main__":
    unittest.main()
