"""Tests for tools/minigames/prismcairn.py (Prismcairn Duel)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import prismcairn as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def test_grundy_and_best_move(self):
        self.assertEqual(gm.grundy([4, 4], 3), 0)
        self.assertEqual(gm.best_move([5, 4], 3), (0, 1))
        self.assertEqual(gm.grundy([4, 4], 3), gm.grundy([0, 0], 3))

    def test_openings_are_winnable_and_perfect_play_wins(self):
        for d in gm.DIFFICULTY:
            for s in range(40):
                g = gm.start(s, d)
                self.assertNotEqual(gm.grundy(g.cairns, g.cfg["take_max"]), 0)
                g = gm.demo(s, d)
                self.assertTrue(g.won, (d, s))
                self.assertEqual(g.losses, 0)
                self.assertEqual(g.score, 100 + 5 * (g.cfg["rounds"] - g.round))

    def test_last_shard_and_bad_moves(self):
        g = gm.start(1)
        with self.assertRaises(ValueError):
            g.step((0, g.cfg["take_max"] + 1))
        g.cairns = [0, 0, 2, 0]
        self.assertEqual(g.step((2, 2)), "you lift the last shard")
        self.assertEqual((g.wins, g.round, g.score), (1, 2, 50))

    def test_warden_wins_rounds_and_match(self):
        g = gm.start(2, "hard")
        for _ in range(2):
            g.cairns = [0, 0, 0, 0, 2]
            g.step((4, 1))
        self.assertTrue(g.over and not g.won)
        self.assertEqual(g.losses, 2)


if __name__ == "__main__":
    unittest.main()
