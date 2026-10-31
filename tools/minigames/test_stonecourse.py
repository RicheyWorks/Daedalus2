"""Tests for tools/minigames/stonecourse.py (Stonecourse)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import stonecourse as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def wall(self, stones, width=5, courses=2, skips=1, rows=None):
        g = gm.start(1, "easy")
        g.cfg = dict(g.cfg, width=width, courses=courses, supply=len(stones), skips=skips)
        g.stones = list(stones)
        g.wall = [[int(ch) for ch in row] for row in rows] if rows else [[0] * width for _ in range(courses)]
        g.index, g.locked, g.skips_left = 0, sum(1 for row in g.wall if all(row)), skips
        return g

    def test_setup_is_solvable(self):
        for d, cfg in gm.DIFFICULTY.items():
            for s in range(15):
                g = gm.start(s, d)
                self.assertEqual(len(g.stones), cfg["supply"])
                self.assertTrue(all(gm.MIN_WIDTH <= x <= gm.MAX_WIDTH for x in g.stones))
                self.assertIsNotNone(g.search(), "%s seed %d" % (d, s))

    def test_stone_rests_on_the_lowest_full_support(self):
        g = self.wall([2, 2, 1, 3], width=5, courses=3)
        self.assertEqual(g.landing(0), 0)
        g.step("0")                                   # course 0: ##...
        self.assertEqual(g.landing(0), 1, "on top of the first stone")
        self.assertIsNone(g.landing(1), "half over empty footing")
        g.step("2")                                   # course 0: ####.
        self.assertEqual(g.placements(), [0, 1, 2, 3, 4], "a 1-stone rests on any filled cell below or the open footing")
        g.step("4")                                   # course 0 locks
        self.assertEqual(g.locked, 1)
        self.assertEqual(g.score, gm.COURSE_SCORE)
        self.assertEqual(g.landing(0), 1)

    def test_gaps_and_overhang_refused(self):
        g = self.wall([3, 3], width=5, courses=2, rows=["11011", "00000"])
        self.assertEqual(g.placements(), [])
        for bad in ("0", "1", "2", "7", "x"):
            with self.assertRaises(ValueError):
                g.step(bad)
        self.assertEqual(g.index, 0, "refused stones stay on the supply")

    def test_skip_and_lose_when_stuck(self):
        g = self.wall([3, 3, 1], width=5, courses=2, skips=1, rows=["11011", "00000"])
        res = g.step("skip")
        self.assertIn("rubble", res)
        self.assertEqual((g.index, g.skips_left), (1, 0))
        self.assertTrue(g.over and not g.won, "no placement and no skips left ends the build")
        self.assertIn("fits nowhere", res)

    def test_supply_runs_out(self):
        g = self.wall([1, 1], width=3, courses=1)
        g.step("0")
        res = g.step("1")
        self.assertTrue(g.over and not g.won)
        self.assertIn("supply runs out", res)

    def test_finish_scores(self):
        g = self.wall([3, 2, 1], width=3, courses=1, skips=2)
        res = g.step("0")
        self.assertTrue(g.won)
        self.assertIn("the wall stands", res)
        self.assertEqual(g.score, gm.COURSE_SCORE + 2 * gm.STONE_BONUS + 2 * gm.SKIP_BONUS)

    def test_preview_matches_the_move(self):
        for s in range(15):
            g = gm.start(s, "hard")
            while not g.over:
                a = g.demo_action()
                legal, course, locks = g.preview(a)
                self.assertTrue(legal)
                before = (g.locked, g.to_state())
                self.assertEqual(g.to_state(), before[1])
                g.step(a)
                if a != "skip":
                    self.assertEqual(g.locked - before[0], 1 if locks else 0)

    def test_mason_finishes_every_wall_and_greedy_often_does_not(self):
        greedy = 0
        for s in range(40):
            g = gm.start(s)
            while not g.over:
                g.step(g.demo_action())
            self.assertTrue(g.won, "seed %d" % s)
            h = gm.start(s)
            while not h.over:
                h.step(h.greedy_pick())
            greedy += h.won
        self.assertLess(greedy, 40)

    def test_properties_hold_under_random_actions(self):
        """Iteration 1: random legal actions on 90 walls never break support, locking or the counters."""
        import random
        for s in range(90):
            d = ("easy", "normal", "hard")[s % 3]
            g = gm.start(s, d)
            rng = random.Random(s)
            while not g.over:
                legal = [str(c) for c in g.placements()] + (["skip"] if g.skips_left > 0 else [])
                a = legal[rng.randrange(len(legal))]
                legal_ok, course, locks = g.preview(a)
                self.assertTrue(legal_ok)
                before = (g.index, g.locked, g.skips_left)
                g.step(a)
                self.assertEqual(g.index - before[0], 1)
                self.assertEqual(g.skips_left, before[2] - (1 if a == "skip" else 0))
                self.assertEqual(g.locked - before[1], 1 if (a != "skip" and locks) else 0)
                for k in range(1, g.cfg["courses"]):
                    for c in range(g.width()):
                        if g.wall[k][c]:
                            self.assertEqual(g.wall[k - 1][c], 1, "no overhang")
                self.assertEqual(g.locked, sum(1 for row in g.wall if all(row)))
            self.assertEqual(g.won, g.locked == g.cfg["courses"])

    def test_render_marks(self):
        g = gm.start(2)
        screen = g.render()
        self.assertIn("SET    a column", screen)
        self.assertIn("course 0  |", screen)
        g.step(g.demo_action())
        self.assertNotIn("SET    a column", g.render())
        self.assertIn("#", g.render())



class Saves(unittest.TestCase):
    """Iteration 5: from_state refuses saves that break the rules."""
    def bad(self, **fields):
        st = gm.start(3).to_state()
        st.update(fields)
        with self.assertRaises(ValueError):
            gm.Game.from_state(st)

    def test_round_trip_still_works(self):
        g = gm.start(3)
        for _ in range(5):
            g.step(g.demo_action())
        self.assertEqual(gm.Game.from_state(g.to_state()).status(), g.status())

    def test_bad_saves_are_refused(self):
        g = gm.start(3)
        w = g.width()
        self.bad(wall=[[1] + [0] * (w - 1)] + [[0] * w for _ in range(g.cfg["courses"] - 1)])          # stone the supply never gave
        self.bad(index=3, wall=[[0] * w, [1] + [0] * (w - 1)] + [[0] * w for _ in range(g.cfg["courses"] - 2)])   # overhang
        self.bad(locked=1)
        self.bad(skips_left=9)
        self.bad(won=True)
        self.bad(over=True)


class Balance(unittest.TestCase):
    """Iteration 3: pinned bands. The mason finishes every wall; the gap-aware greedy stays well below it."""
    GREEDY_BANDS = {"easy": (55, 92), "normal": (50, 90), "hard": (55, 92)}

    def test_mason_finishes_every_wall(self):
        for d in gm.DIFFICULTY:
            for s in range(60):
                g = gm.start(s, d)
                while not g.over:
                    g.step(g.demo_action())
                self.assertTrue(g.won, "%s seed %d" % (d, s))

    def test_greedy_win_rates(self):
        for d, (low, high) in self.GREEDY_BANDS.items():
            wins = 0
            for s in range(120):
                g = gm.start(s, d)
                while not g.over:
                    g.step(g.greedy_pick())
                wins += g.won
            rate = wins / 1.2
            self.assertTrue(low <= rate <= high, "%s greedy win rate %.1f%% outside %d-%d" % (d, rate, low, high))


if __name__ == "__main__":
    unittest.main()
