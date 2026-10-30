"""Tests for tools/minigames/roostcall.py (Roostcall)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import roostcall as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def yard(self, size, whistler, birds, turns=10):
        g = gm.start(1, "easy")
        g.cfg = dict(g.cfg, size=size, birds=len(birds), turns=turns)
        g.whistler, g.birds, g.turns, g.settled = list(whistler), [list(b) for b in birds], turns, 0
        return g

    def test_setup(self):
        for d, cfg in gm.DIFFICULTY.items():
            g = gm.start(9, d)
            self.assertEqual(g.whistler, [0, 0])
            self.assertEqual(len(g.birds), cfg["birds"])
            self.assertEqual(len({tuple(b) for b in g.birds}), cfg["birds"])
            for r, c in g.birds:
                self.assertFalse(g.in_roost(r, c))
                self.assertGreater(max(r, c), gm.SCARE_RANGE, "birds start out of reach")

    def test_bird_flees_directly_away(self):
        g = self.yard(6, (1, 1), [(2, 1)])
        self.assertEqual(g.flee_step(0), [3, 1])          # whistler north: bird goes south
        g = self.yard(6, (2, 3), [(2, 1)])
        self.assertEqual(g.flee_step(0), [2, 0])          # whistler east: bird goes west
        g = self.yard(6, (4, 4), [(1, 1)])
        self.assertIsNone(g.flee_step(0), "out of scare range")

    def test_cornered_bird_slides_along_the_edge(self):
        g = self.yard(6, (0, 4), [(0, 5)])
        self.assertEqual(g.flee_step(0), [1, 5])          # beside a corner bird: it goes down the edge
        g = self.yard(6, (1, 4), [(0, 5)])
        self.assertIsNone(g.flee_step(0), "nothing is strictly farther from a diagonal whistler")

    def test_blocked_bird_sidesteps_or_stays_and_ties_go_in_order(self):
        g = self.yard(6, (1, 1), [(2, 1), (3, 1)])
        self.assertEqual(g.flee_step(0), [2, 2], "the cell behind is taken, so it sidesteps (e before w)")
        self.assertEqual(g.flee_step(1), [4, 1])
        g = self.yard(6, (1, 1), [(2, 1), (3, 1), (2, 2), (2, 0)])
        self.assertIsNone(g.flee_step(0), "boxed in on every farther side")
        g = self.yard(6, (2, 2), [(1, 1)])                # equal escapes north and west: n wins the tie
        self.assertEqual(g.flee_step(0), [0, 1])

    def test_perch_settles_and_wins(self):
        g = self.yard(6, (2, 4), [(3, 4)], turns=5)
        res = g.step("wait")
        self.assertEqual((g.birds, g.settled), ([], 1))
        self.assertTrue(g.won and res.endswith("every bird is home"))
        self.assertEqual(g.score, gm.BIRD_SCORE + 4)

    def test_dusk_loses(self):
        g = self.yard(6, (0, 0), [(5, 0)], turns=1)
        self.assertTrue(g.step("wait").startswith("wait: 0 flew, dusk falls"))
        self.assertTrue(g.over and not g.won and g.score == 0)

    def test_moves_are_checked(self):
        g = self.yard(6, (0, 0), [(0, 1)])
        with self.assertRaises(ValueError):
            g.step("n")
        with self.assertRaises(ValueError):
            g.step("e")
        with self.assertRaises(ValueError):
            g.step("x")

    def test_demo_herds_every_seed_home_given_time(self):
        import io
        for d in gm.DIFFICULTY:
            gm.DIFFICULTY[d] = dict(gm.DIFFICULTY[d], turns=300)
            try:
                for s in range(40):
                    self.assertTrue(gm.demo(s, d, io.StringIO()).won, f"{d} seed {s}")
            finally:
                gm.DIFFICULTY[d] = dict(gm.DIFFICULTY[d], turns={"easy": 16, "normal": 30, "hard": 48}[d])


if __name__ == "__main__":
    unittest.main()
