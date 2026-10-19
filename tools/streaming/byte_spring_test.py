# SPDX-License-Identifier: MIT
"""G39 Byte Spring tests. Run: python -m unittest tools.streaming.byte_spring_test"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import byte_spring as bs  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "byte-spring-v1.json")


def tiny_cfg(**over):
    base = {
        "v": 1,
        "cistern": {
            "capacity": 1000,
            "level": 500,
            "spring_fill": 350,
            "leak": 50,
            "budget_cap": 400,
        },
        "islands": [
            {"id": "cache_a", "cost_kib": 100, "priority": 1},
            {"id": "cache_b", "cost_kib": 200, "priority": 0},
            {"id": "vault", "cost_kib": 250, "priority": 2},
        ],
        "start_residents": ["cache_a", "cache_b"],
        "drought_limit": 3,
        "win_ticks": 5,
    }
    base.update(over)
    return base


class ValidateTest(unittest.TestCase):
    def test_ok(self):
        c, islands, d, w = bs.validate(tiny_cfg())
        self.assertEqual(c.capacity, 1000)
        self.assertEqual(len(islands), 3)
        self.assertEqual((d, w), (3, 5))

    def test_bad_version(self):
        with self.assertRaises(bs.ByteSpringError):
            bs.validate({"v": 2, "cistern": tiny_cfg()["cistern"], "islands": []})

    def test_duplicate_id(self):
        cfg = tiny_cfg()
        cfg["islands"].append({"id": "cache_a", "cost_kib": 10})
        with self.assertRaises(bs.ByteSpringError):
            bs.validate(cfg)


class BudgetTest(unittest.TestCase):
    def test_overflow_dumps_lowest_priority(self):
        # cache_a(100,p1)+cache_b(200,p0)+vault(250,p2)=550 > budget 400
        # dump order: priority 0 first => cache_b, then still 350 ok
        cfg = tiny_cfg()
        state = bs.State(cistern=bs.validate(cfg)[0])
        bs.load_residents(state, bs.validate(cfg)[1], ["cache_a", "cache_b", "vault"])
        bs._enforce_budget(state)
        self.assertEqual(state.dumped, ["cache_b"])
        self.assertEqual(sorted(r.id for r in state.residents), ["cache_a", "vault"])
        self.assertLessEqual(bs.resident_cost(state.residents), 400)


class SimTest(unittest.TestCase):
    def test_wet_run_wins(self):
        # all wet ticks, should win at win_ticks with level > 0
        state = bs.simulate(tiny_cfg(), weather=[False] * 5)
        self.assertTrue(state.won)
        self.assertFalse(state.failed)
        self.assertEqual(state.ticks, 5)
        self.assertGreater(state.cistern.level, 0)

    def test_drought_fails(self):
        # heavy residents + dry weather empties cistern for 3 dry ticks
        cfg = tiny_cfg(
            cistern={
                "capacity": 300,
                "level": 120,
                "spring_fill": 10,
                "leak": 40,
                "budget_cap": 500,
            },
            start_residents=["cache_a", "cache_b"],  # drink 300/tick
            drought_limit=3,
            win_ticks=20,
        )
        state = bs.simulate(cfg, weather=[True] * 10)
        self.assertTrue(state.failed)
        self.assertFalse(state.won)
        self.assertGreaterEqual(state.dry_streak, 3)
        self.assertEqual(state.cistern.level, 0)

    def test_fixture_file_loads(self):
        with open(DATA, encoding="utf-8") as f:
            cfg = json.load(f)
        c, islands, d, w = bs.validate(cfg)
        self.assertEqual(cfg["v"], 1)
        self.assertGreaterEqual(len(islands), 2)
        state = bs.simulate(cfg, weather=[False, False, True, False, False, False, False, False, False, False])
        self.assertFalse(state.failed)


if __name__ == "__main__":
    unittest.main()
