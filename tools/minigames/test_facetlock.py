"""Tests for tools/minigames/facetlock.py (Facetlock Lattice)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import facetlock as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def test_shift_wraps_and_inverts(self):
        b = ["EEE", "TTT", "VVV"]
        self.assertEqual(gm.shift(b, "c", 0, 1), ["VEE", "ETT", "TVV"])
        self.assertEqual(gm.shift(gm.shift(b, "r", 1, 1), "r", 1, -1), b)

    def test_scrambled_and_solvable_in_budget(self):
        for d in gm.DIFFICULTY:
            for s in range(30):
                g = gm.start(s, d)
                self.assertNotEqual(g.board, g.target())
                self.assertLessEqual(len(g.solution), g.moves)
                g = gm.demo(s, d)
                self.assertTrue(g.won)
                self.assertEqual(g.score, 100 + 10 * g.moves)

    def test_wrong_moves_then_loss(self):
        g = gm.start(1, "easy")
        g.moves = 1
        a = g.solution[0]
        g.step((a[0], a[1], a[2]) if len(g.solution) > 1 else (a[0], a[1], -a[2]))
        self.assertTrue(g.over)
        with self.assertRaises(ValueError):
            gm.start(1).step(("x", 0, 1))


if __name__ == "__main__":
    unittest.main()
