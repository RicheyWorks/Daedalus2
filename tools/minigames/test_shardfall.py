"""Tests for tools/minigames/shardfall.py (Shardfall Gamble)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import shardfall as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def test_draw_bank_and_collapse(self):
        g = gm.start(2)
        g.bag = [0, 4, 0, 3]
        self.assertEqual(g.step("draw"), "+3")
        self.assertEqual(g.step("draw"), "cracked")
        self.assertEqual(g.step("draw"), "+4")
        self.assertEqual(g.step("bank"), "banked 7")
        self.assertEqual((g.score, g.round, g.pot), (7, 2, 0))
        g.bag = [0, 0]
        g.step("draw")
        self.assertEqual(g.step("draw"), "collapse")
        self.assertEqual((g.score, g.round, g.history), (7, 3, [7, 0]))

    def test_bag_contents(self):
        for d, cfg in gm.DIFFICULTY.items():
            g = gm.start(9, d)
            self.assertEqual(sorted(g.bag), sorted(cfg["values"] + [0] * cfg["cracked"]))

    def test_win_and_loss(self):
        g = gm.start(1)
        g.score = g.cfg["target"] - 1
        g.pot = 1
        g.step("bank")
        self.assertTrue(g.won)
        g = gm.start(1)
        g.round = g.cfg["rounds"]
        g.step("bank")
        self.assertTrue(g.over and not g.won)


if __name__ == "__main__":
    unittest.main()
