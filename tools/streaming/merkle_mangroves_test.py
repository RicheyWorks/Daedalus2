# SPDX-License-Identifier: MIT
"""Tests for G90 Merkle Mangroves."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import merkle_mangroves as m  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "merkle-mangroves-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        self.assertEqual(m.validate(raw()).npc_name, "Warden Hashroot")

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d["mangroves"].update(depth=17),
                    lambda d: d["mangroves"].pop("bandwidth"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("fail")):
            d = raw()
            mut(d)
            with self.assertRaises(m.MangroveError):
                m.validate(d)


class TreeTest(unittest.TestCase):
    def setUp(self):
        self.c = m.validate(raw())
        self.keys = m.keys_for(self.c)
        self.shore = {k: 0 for k in self.keys}

    def test_tree_shape_and_equal_roots(self):
        t = m.build_tree(self.shore, self.keys, 8)
        self.assertEqual([len(x) for x in t], [1 << i for i in range(9)])
        self.assertEqual(t[0], m.build_tree(dict(self.shore), self.keys, 8)[0])

    def test_one_flip_changes_one_path(self):
        mg = dict(self.shore); mg[self.keys[5]] = 7
        a, b = m.build_tree(self.shore, self.keys, 8), m.build_tree(mg, self.keys, 8)
        for la, lb in zip(a, b):
            self.assertEqual(sum(x != y for x, y in zip(la, lb)), 1)

    def test_identical_replicas_cost_one_hash(self):
        mg = dict(self.shore)
        self.assertEqual(m.merkle_sync(self.shore, mg, self.keys, 8), 1)

    def test_merkle_cost_single_flip(self):
        mg = dict(self.shore); k = self.keys[42]; mg[k] = 3
        bucket_size = len([x for x in self.keys if m.bucket(x, 8) == m.bucket(k, 8)])
        cost = m.merkle_sync(self.shore, mg, self.keys, 8)
        self.assertEqual(cost, 1 + 2 * 8 + bucket_size)
        self.assertEqual(mg, self.shore)

    def test_every_sync_repairs(self):
        for s in (m.merkle_sync, m.leaf_scan_sync, m.full_copy_sync):
            mg = dict(self.shore)
            for k in self.keys[::97]:
                mg[k] = 9
            s(self.shore, mg, self.keys, 8)
            self.assertEqual(mg, self.shore)


class SimTest(unittest.TestCase):
    def setUp(self):
        self.c = m.validate(raw())

    def test_merkle_wins(self):
        r = m.simulate(self.c)
        self.assertEqual(r.status, m.WON)
        self.assertLessEqual(r.worst_cost, self.c.bandwidth)
        self.assertGreater(r.drifted, 0)

    def test_traps_fail(self):
        for s in (m.leaf_scan_sync, m.full_copy_sync):
            r = m.simulate(self.c, s)
            self.assertEqual((r.status, r.reason), (m.FAILED, m.FAIL_BW))

    def test_deterministic_and_cost_order(self):
        a, b = m.simulate(self.c), m.simulate(self.c)
        self.assertEqual(a, b)
        costs = [m.simulate(self.c, s).total_cost
                 for s in (m.merkle_sync, m.leaf_scan_sync, m.full_copy_sync)]
        self.assertEqual(costs, sorted(costs))

    def test_seeds_and_depths(self):
        for seed in range(1, 5):
            for depth in (0, 3, 8):
                d = raw(); d["seed"] = seed; d["mangroves"]["depth"] = depth; d["mangroves"]["windows"] = 4
                m.simulate(m.validate(d))  # raises if replicas unequal

    def test_g86_tie_in(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = m.islands_from_shoals(json.load(fh))
        self.assertEqual(isl, raw()["islands"])
        self.assertEqual(kpi, self.c.keys_per_island)

    def test_cli(self):
        self.assertEqual(m.main([DATA]), 0)
        self.assertEqual(m.main([DATA, "--sync", "full_copy"]), 1)


if __name__ == "__main__":
    unittest.main()
