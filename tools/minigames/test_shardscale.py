"""Tests for tools/minigames/shardscale.py (Shardscale)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import shardscale as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402

L, R, H = ("left", "next"), ("right", "next"), ("hold", "next")


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def line(self, weights, cap=5, tolerance=1, bench=2):
        g = gm.start(1, "easy")
        g.cfg = dict(g.cfg, shards=len(weights), cap=cap, tolerance=tolerance, bench=bench)
        g.line = list(weights)
        g.index, g.left, g.right, g.held, g.bench_used, g.tipped = 0, 0, 0, [], 0, False
        return g

    def test_setup_is_solvable(self):
        for d, cfg in gm.DIFFICULTY.items():
            for s in range(20):
                g = gm.start(s, d)
                self.assertEqual(len(g.line), cfg["shards"])
                self.assertTrue(all(gm.MIN_WEIGHT <= w <= gm.MAX_WEIGHT for w in g.line))
                self.assertIsNotNone(gm.solve(tuple(g.line), 0, 0, (), cfg["cap"], cfg["tolerance"], cfg["bench"], {}))

    def test_placing_and_holding(self):
        g = self.line([3, 4, 2])
        self.assertIn("left 3", g.step(L))
        self.assertEqual((g.left, g.right, g.index), (3, 0, 1))
        g.step(H)
        self.assertEqual((g.held, g.bench_used, g.index), ([4], 1, 2))
        g.step(R)
        self.assertEqual((g.left, g.right), (3, 2))
        self.assertFalse(g.over, "a held shard still has to be placed")
        res = g.step(("right", 0))
        self.assertEqual((g.left, g.right, g.held), (3, 6, []))
        self.assertTrue(g.over and not g.won)
        self.assertIn("askew", res)

    def test_tip_loses_at_once(self):
        g = self.line([9, 1], cap=5)
        res = g.step(L)
        self.assertTrue(g.over and not g.won and g.tipped)
        self.assertIn("tips", res)
        self.assertEqual(g.score, 0)

    def test_level_wins_with_slack_and_bench_bonus(self):
        g = self.line([4, 4], cap=5, tolerance=1, bench=2)
        g.step(L)
        res = g.step(R)
        self.assertTrue(g.won)
        self.assertIn("level", res)
        self.assertEqual(g.score, gm.WIN_SCORE + gm.SLACK_SCORE * 1 + gm.BENCH_SCORE * 2)
        g = self.line([4, 3], cap=5, tolerance=1, bench=1)
        g.step(H)
        g.step(L)
        g.step(("right", 0))
        self.assertTrue(g.won)
        self.assertEqual(g.score, gm.WIN_SCORE + 0 + 0)

    def test_illegal_actions(self):
        g = self.line([3, 4, 2], bench=1)
        g.step(H)
        for bad in (H, ("left", 1), ("right", 5), ("up", "next")):
            with self.assertRaises(ValueError):
                g.step(bad)
        g = self.line([3])
        g.step(L)
        self.assertTrue(g.over)

    def test_parse(self):
        self.assertEqual(gm.Game.parse("l"), L)
        self.assertEqual(gm.Game.parse("R"), R)
        self.assertEqual(gm.Game.parse("hold"), H)
        self.assertEqual(gm.Game.parse("r1"), ("right", 1))
        with self.assertRaises(ValueError):
            gm.Game.parse("lx")

    def test_preview_matches_the_move(self):
        for s in range(20):
            g = gm.start(s, "hard")
            while not g.over:
                a = g.demo_action()
                legal, after, tips, ends = g.preview(a)
                self.assertTrue(legal)
                state = g.to_state()
                self.assertEqual(g.to_state(), state)
                res = g.step(a)
                self.assertEqual(g.diff(), after)
                self.assertEqual(tips, "tips" in res)
                self.assertEqual(ends, g.over)

    def test_weigher_always_levels_and_greedy_rarely_does(self):
        greedy = 0
        for s in range(60):
            g = gm.start(s)
            while not g.over:
                g.step(g.demo_action())
            self.assertTrue(g.won, "the exact weigher levels every seeded line")
            g = gm.start(s)
            while not g.over:
                g.step(L if g.diff() <= 0 else R)
            greedy += g.won
        self.assertLess(greedy, 20, "lighter-pan greedy without the bench loses most lines")

    def test_properties_hold_under_random_actions(self):
        """Iteration 1: random legal actions on 150 lines never break the bookkeeping."""
        import random
        for s in range(150):
            d = ("easy", "normal", "hard")[s % 3]
            g = gm.start(s, d)
            rng = random.Random(s)
            while not g.over:
                acts = g.actions()
                a = acts[rng.randrange(len(acts))]
                legal, after, tips, ends = g.preview(a)
                self.assertTrue(legal)
                before = (g.index, g.bench_used, len(g.held))
                res = g.step(a)
                self.assertEqual(g.diff(), after)
                self.assertEqual(tips, g.tipped)
                self.assertEqual(g.index - before[0], 1 if a[1] == "next" else 0)
                self.assertEqual(g.bench_used - before[1], 1 if a[0] == "hold" else 0)
                self.assertEqual(g.left + g.right + sum(g.held), sum(g.line[:g.index]))
                self.assertEqual(g.held, sorted(g.held))
                self.assertLessEqual(len(g.held), g.cfg["bench"])
                self.assertTrue(g.tipped or abs(g.diff()) <= g.cfg["cap"])
                if tips:
                    self.assertIn("tips", res)
            self.assertEqual(g.won, not g.tipped and g.remaining() == 0 and abs(g.diff()) <= g.cfg["tolerance"])

    def test_render_marks(self):
        g = self.line([3, 4, 2])
        self.assertIn("SET    l / r", g.render())
        g.step(L)
        screen = g.render()
        self.assertNotIn("SET    l / r", screen)
        self.assertIn("beam: L", screen)
        self.assertIn("left 3 right 0 diff +3", screen)



class Balance(unittest.TestCase):
    """Iteration 3: pinned bands. The weigher always levels; lighter-pan greedy without the bench stays rare, so a rules
    change that makes lines trivially greedy-solvable (or impossible) is caught."""
    GREEDY_BANDS = {"easy": (3, 30), "normal": (0, 20), "hard": (0, 12)}

    def test_weigher_levels_every_line(self):
        for d in gm.DIFFICULTY:
            for s in range(100):
                g = gm.start(s, d)
                while not g.over:
                    g.step(g.demo_action())
                self.assertTrue(g.won, "%s seed %d" % (d, s))

    def test_greedy_win_rates(self):
        for d, (low, high) in self.GREEDY_BANDS.items():
            wins = 0
            for s in range(200):
                g = gm.start(s, d)
                while not g.over:
                    g.step(L if g.diff() <= 0 else R)
                wins += g.won
            self.assertTrue(low <= wins / 2 <= high, "%s greedy win rate %.1f%% outside %d-%d" % (d, wins / 2, low, high))


if __name__ == "__main__":
    unittest.main()
