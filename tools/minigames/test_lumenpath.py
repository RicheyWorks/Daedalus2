"""Tests for tools/minigames/lumenpath.py (Lumenpath Refraction)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lumenpath as lp  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Lumenpath(kit.GameContract, unittest.TestCase):
    MOD = lp

    def test_trace_reflects_and_stops(self):
        grid = [".\\.", "...", "#.."]
        self.assertEqual(lp.trace(grid, 0), [(0, 0), (0, 1), (1, 1), (2, 1)])
        self.assertEqual(lp.trace(["#.."], 0), [])

    def test_solution_always_wins(self):
        for d in lp.DIFFICULTY:
            for s in range(30):
                g = lp.demo(s, d)
                self.assertTrue(g.won, (s, d))
                self.assertGreaterEqual(g.score, 10)

    def test_scoring_and_loss(self):
        g = lp.start(4, "easy")
        before = g.lit
        r, c, m = g.solution[0]
        pts = g.step((r, c))
        self.assertEqual(pts, 10 * max(0, g.lit - before) + (20 * g.moves if g.won else 0))
        g = lp.start(4, "easy")
        free = [(i, j) for i in range(5) for j in range(5) if g.grid[i][j] == "." and [i, j] not in [s[:2] for s in g.solution]]
        g.moves = 1
        g.step(free[0])
        self.assertTrue(g.over or g.won)

    def test_bad_cell(self):
        g = lp.start(1)
        r, c = g.crystals[0]
        with self.assertRaises(ValueError):
            g.step((r, c))


class SaveChecks(unittest.TestCase):
    """Round 2 finding (prometheus 1): the saved score is recomputed on load."""

    def test_tampered_score_is_rejected(self):
        st = lp.start(1, "normal").to_state()
        st["score"] = 9999
        with self.assertRaises(ValueError):
            lp.Game.from_state(st)

    def test_mid_game_and_won_saves_reload(self):
        g = lp.start(4, "hard")
        while not g.over:
            g.step(g.demo_action())
            self.assertEqual(lp.Game.from_state(g.to_state()).score, g.score)


if __name__ == "__main__":
    unittest.main()
