"""Tests for tools/minigames/shadewatch.py (Shadewatch Vigil)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import shadewatch as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def test_flare_burns_front_and_shades_advance(self):
        g = gm.start(1)
        g.lanes = [[1, 4], [], [3]]
        g.rng.random = lambda: 1.0  # no spawns this turn
        self.assertEqual(g.step(("flare", 0)), "burned 1")
        self.assertEqual(g.lanes, [[3], [], [2]])
        self.assertEqual((g.score, g.burned, g.turn), (6, 1, 1))

    def test_heart_hit_and_loss(self):
        g = gm.start(1, "hard")
        g.rng.random = lambda: 1.0
        g.hearts = 1
        g.lanes = [[0], [], [], []]
        self.assertEqual(g.step(("kindle", 0)), "the heart dims")
        self.assertTrue(g.over and not g.won)

    def test_nova_and_light(self):
        g = gm.start(2)
        g.rng.random = lambda: 1.0
        with self.assertRaises(ValueError):
            g.step(("nova", 0))
        g.light = 5
        g.step(("kindle", 0))
        self.assertEqual(g.light, gm.LIGHT_MAX)
        g.lanes = [[0, 2, 5], [1], [3]]
        self.assertEqual(g.step(("nova", 0)), "burned 3")
        self.assertEqual((g.light, g.lanes), (2, [[4], [], [2]]))

    def test_survive_wins_with_heart_bonus(self):
        g = gm.start(3)
        g.rng.random = lambda: 1.0
        g.lanes = [[], [], []]
        g.turn = g.cfg["turns"] - 1
        before = g.score
        self.assertEqual(g.step(("kindle", 0)), "dawn: the vigil holds")
        self.assertTrue(g.won)
        self.assertEqual(g.score, before + 1 + 10 * g.hearts)

    def test_demo_wins_most_easy_games(self):
        self.assertGreaterEqual(sum(gm.demo(s, "easy").won for s in range(30)), 25)


class ParseErrors(unittest.TestCase):
    """Round 2 self-test: typos get the help line, never a Python error."""

    def test_bad_lines_give_the_help_line(self):
        for line in ("", "   ", "flare", "flare x", "flare -1", "flare \u0661", "kindle 2", "nova now", "zz"):
            with self.assertRaisesRegex(ValueError, "use flare <lane>, kindle or nova", msg=repr(line)):
                gm.Game.parse(line)
        self.assertEqual(gm.Game.parse("flare 2"), ("flare", 2))


if __name__ == "__main__":
    unittest.main()
