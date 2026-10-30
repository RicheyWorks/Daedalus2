"""Tests for tools/minigames/prismvault.py (Prismvault Weigh)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import prismvault as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def test_weigh_results(self):
        g = gm.start(4, "easy")
        h = g.hollow
        other = [i for i in range(8) if i != h]
        self.assertEqual(g.step(("weigh", [h], [other[0]])), "<")
        self.assertEqual(g.step(("weigh", [other[1]], [h])), ">")
        self.assertEqual(g.step(("weigh", [other[2]], [other[3]])), "=")
        self.assertEqual(g.weighings, 0)
        with self.assertRaises(ValueError):
            g.step(("weigh", [0], [1]))
        self.assertEqual(g.step(("name", h)), 100)
        self.assertTrue(g.won)

    def test_bad_weighings_and_wrong_name(self):
        g = gm.start(4)
        for bad in (([0, 1], [2]), ([0], [0]), ([], []), ([99], [0])):
            with self.assertRaises(ValueError):
                g.step(("weigh",) + bad)
        g.step(("name", (g.hollow + 1) % 12))
        self.assertTrue(g.over and not g.won)

    def test_demo_is_optimal(self):
        for d in gm.DIFFICULTY:
            for s in range(40):
                g = gm.demo(s, d)
                self.assertTrue(g.won, (d, s))


if __name__ == "__main__":
    unittest.main()
