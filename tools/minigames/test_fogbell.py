"""Tests for tools/minigames/fogbell.py (Fogbell Ferry)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fogbell as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def flat(self, rows, passengers, need=1):
        g = gm.start(1, "easy")
        s = len(rows)
        g.cfg = dict(g.cfg, size=s, passengers=len(passengers), need=need)
        g.heights = [[int(ch) for ch in row] for row in rows]
        g.ferry, g.harbour = [0, 0], [s - 1, s - 1]
        g.passengers = [list(p) for p in passengers]
        g.aboard, g.turn = 0, 0
        return g

    def test_setup_shape(self):
        for d, cfg in gm.DIFFICULTY.items():
            g = gm.start(5, d)
            s = cfg["size"]
            self.assertEqual(len(g.heights), s)
            self.assertTrue(all(len(r) == s and all(1 <= h <= s for h in r) for r in g.heights))
            self.assertEqual((g.heights[0][0], g.heights[s - 1][s - 1]), (s, s))
            self.assertEqual(len(g.passengers), cfg["passengers"])
            self.assertEqual(len({tuple(p) for p in g.passengers}), cfg["passengers"])
            self.assertTrue(all(g.heights[r][c] >= 2 for r, c in g.passengers))
            self.assertNotIn([0, 0], g.passengers)
            self.assertNotIn([s - 1, s - 1], g.passengers)

    def test_moves_and_pickup(self):
        g = self.flat(["333", "333", "333"], [(0, 1)])
        self.assertEqual(g.step("e"), "e: lantern aboard, tide 0")
        self.assertEqual((g.ferry, g.aboard, g.passengers), ([0, 1], 1, []))
        self.assertEqual(g.step("s"), "s: open water, tide 0")
        with self.assertRaises(ValueError):
            g.step("x")
        g.ferry = [0, 0]
        with self.assertRaises(ValueError):
            g.step("n")

    def test_tide_floods_and_blocks(self):
        g = self.flat(["313", "333", "333"], [])
        g.turn = 3                      # tide 1: the middle of the top row is under water
        self.assertTrue(g.flooded(0, 1))
        with self.assertRaises(ValueError):
            g.step("e")
        g.turn = 2
        g.ferry = [0, 1]
        self.assertEqual(g.step("wait"), "wait: the tide takes the ferry")
        self.assertTrue(g.over and not g.won)

    def test_harbour_win_and_short(self):
        g = self.flat(["33", "33"], [(0, 1)], need=1)
        g.step("e")
        res = g.step("s")
        self.assertTrue(res.startswith("s: harbour with 1 aboard") and g.won)
        self.assertEqual(g.score, gm.PASSENGER_SCORE + gm.TIDE_SCORE * (gm.TIDE_EVERY * 2 - 2))
        g = self.flat(["33", "33"], [(0, 1)], need=1)
        g.step("s")
        g.step("e")
        self.assertTrue(g.over and not g.won and g.score == gm.TIDE_SCORE * (gm.TIDE_EVERY * 2 - 2))

    def test_demo_prefers_passengers_then_harbour(self):
        g = self.flat(["3333", "3333", "3333", "3333"], [(0, 2)], need=1)
        self.assertEqual(g.demo_action(), "e")
        g.step("e")
        g.step("e")
        self.assertEqual(g.aboard, 1)
        self.assertIn(g.demo_action(), ("e", "s"))

    def test_bfs_avoids_cells_that_flood_on_arrival(self):
        # the straight path east crosses a height-1 cell that floods at tide 1 (turn 3): BFS must route around it
        g = self.flat(["3133", "3333", "3333", "3333"], [(0, 3)], need=1)
        g.turn = 2
        self.assertEqual(g._bfs([[0, 3]])[0], "s")

    def test_wait_when_stranded(self):
        g = self.flat(["31", "13"], [], need=1)
        g.turn = 3
        self.assertEqual(g.demo_action(), "wait")


if __name__ == "__main__":
    unittest.main()
