"""Tests for tools/minigames/glowmoss.py (Glowmoss Delve)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import glowmoss as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm
    SEEDS = range(6)


def tiny_cfg(light=6, refill=3):
    return {"cols": 2, "rows": 3, "light": light, "refill": refill, "moss_pct": 0, "target_pct": 100}


class Rules(unittest.TestCase):
    def test_climb_cost_and_reach(self):
        self.assertEqual([gm.climb_cost(r) for r in (-1, 0, 1, 2, 3, 4)], [0, 1, 1, 2, 2, 3])
        self.assertEqual(list(gm.dig_cols(0, 4)), [0, 1])
        self.assertEqual(list(gm.dig_cols(3, 4)), [2, 3])

    def test_after_dig_refill_is_capped(self):
        cfg = tiny_cfg()
        self.assertEqual(gm.after_dig(6, cfg, 2, False), 3)
        self.assertEqual(gm.after_dig(6, cfg, 0, True), 6)
        self.assertEqual(gm.after_dig(1, cfg, 1, True), 2)

    def test_best_delve_exact(self):
        gems = [[1, 9], [5, 1], [1, 1]]
        dark = [[0, 2], [0, 0], [0, 0]]
        no_moss = [[False, False], [False, False], [False, False]]
        # Start above column 1 with 6 light: 9 costs 3 (light 3), then 5 costs 1 (light 2 >= climb 1), the bottom needs 2 more.
        self.assertEqual(gm.best_delve(tiny_cfg(), gems, dark, no_moss), (14, [1, 0]))
        moss = [[False, True], [False, False], [False, False]]
        self.assertEqual(gm.best_delve(tiny_cfg(), gems, dark, moss), (15, [1, 0, 0]))
        self.assertEqual(gm.best_delve(tiny_cfg(light=1), gems, dark, no_moss), (0, []))

    def test_demo_follows_the_best_plan_and_wins(self):
        for d in gm.DIFFICULTY:
            for s in range(15):
                g = gm.demo(s, d)
                self.assertTrue(g.won, (d, s))
                self.assertEqual(g.path, g.plan)
                self.assertGreaterEqual(g.crystals, g.target)

    def test_dig_rules_and_guttering(self):
        g = gm.start(3)
        with self.assertRaises(ValueError):
            g.step(("dig", g.col + 2))
        c = g.col
        light = g.light
        res = g.step(("dig", c))
        self.assertEqual((g.row, g.col, g.crystals), (0, c, g.gems[0][c]))
        self.assertTrue(res.startswith("+%d" % g.gems[0][c]))
        self.assertLessEqual(g.light, light)
        g = gm.start(3)
        g.light = 1 + g.dark[0][g.col]
        g.moss[0][g.col] = False
        self.assertEqual(g.step(("dig", g.col)), "the lamp gutters out")
        self.assertTrue(g.over and not g.won)

    def test_climb_short_of_target_loses(self):
        g = gm.start(4)
        self.assertEqual(g.step(("climb", 0)), "climbed out with 0")
        self.assertTrue(g.over and not g.won)
        self.assertEqual(g.score, 0)


if __name__ == "__main__":
    unittest.main()
