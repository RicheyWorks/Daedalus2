"""Tests for tools/minigames/spiritkite.py (Spiritkite Weave)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import spiritkite as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm
    SEEDS = range(6)


class Rules(unittest.TestCase):
    def test_shortest_and_best_tour(self):
        d = gm.shortest(3, [[0, 1, 2], [1, 2, 2], [0, 2, 9]])
        self.assertEqual(d[0][2], 4)
        best, order = gm.best_tour(d, [0, 3, 5], 8)
        self.assertEqual((best, sorted(order)), (8, [1, 2]))
        self.assertEqual(gm.best_tour(d, [0, 3, 5], 3)[0], 0)

    def test_graph_connected_and_demo_wins(self):
        for d in gm.DIFFICULTY:
            for s in range(15):
                g = gm.start(s, d)
                self.assertTrue(all(x < gm.INF for x in g.dist[0]))
                g = gm.demo(s, d)
                self.assertTrue(g.won, (d, s))
                self.assertGreaterEqual(g.lanterns(), g.target)
                self.assertEqual(g.at, 0)

    def test_fly_land_and_lost(self):
        g = gm.start(3)
        j = min(g.adj[0])
        w = g.wind
        g.step(("fly", j))
        self.assertEqual((g.at, g.wind, g.score), (j, w - g.adj[0][j], g.values[j]))
        with self.assertRaises(ValueError):
            g.step(("land", 0))
        with self.assertRaises(ValueError):
            g.step(("fly", 99))
        g = gm.start(3)
        g.wind = g.adj[0][j]
        self.assertEqual(g.step(("fly", j)), "the kite is lost")
        self.assertTrue(g.over and not g.won)

    def test_land_short_of_target_loses(self):
        g = gm.start(4)
        g.step(("land", 0))
        self.assertTrue(g.over and not g.won)
        self.assertEqual(g.score, 0)


if __name__ == "__main__":
    unittest.main()
