import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shoal_lure as sl  # noqa: E402


def demo(seed, diff):
    g = sl.Game(seed, diff)
    while not g.over:
        g.step(g.demo_action())
    return g


class Rules(unittest.TestCase):
    def test_chain_value(self):
        self.assertEqual(sl.chain_value([]), 0)
        self.assertEqual(sl.chain_value([1, 1, 1]), 6)
        self.assertEqual(sl.chain_value([1, 2, 1]), 3)
        self.assertEqual(sl.chain_value([2, 2, 1, 1]), 6)

    def test_step_cost_against_current(self):
        cur = [[0, 1], [2, 3]]
        self.assertEqual(sl.step_cost(cur, 0, 0, 2), 2)  # heading S into a cell flowing N
        self.assertEqual(sl.step_cost(cur, 0, 0, 0), 1)

    def test_distances_avoid_eels(self):
        cur = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
        d = sl.distances(3, cur, {1})
        self.assertEqual(d[0][2], 4)  # around the eel at cell 1, last step into 2 is with the current
        self.assertGreaterEqual(d[0][1], sl.INF)

    def test_best_trip_and_best_score(self):
        cur = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
        d = sl.distances(3, cur, set())
        fish = [[0, 1], [3, 1], [8, 2]]
        best, order = sl.best_trip(d, fish, 1, 1, 12, [])
        self.assertEqual(best, sl.chain_value([fish[i][1] for i in order]))
        self.assertEqual(best, 4)  # 1 + 2 for the two hue-1 fish in a row, + 1 for the hue-2 fish
        top_v, top = sl.best_trip(d, fish, 1, 1, 12, [], 3)
        self.assertEqual(top_v, 4)  # the value returned is still the biggest shoal
        self.assertEqual(sorted(top), [0, 1])  # the far fish costs more stamina (4 extra) than it adds (1)

    def test_demo_wins_everywhere(self):
        for diff in sl.DIFFICULTY:
            for seed in range(25):
                g = demo(seed, diff)
                self.assertTrue(g.won, (seed, diff))
                self.assertGreaterEqual(g.score, g.target)

    def test_refusals(self):
        g = sl.Game(1, "normal")
        for a, msg in ((("dock", 0), "swim first"), (("net", 0), "no prism-fish"), (("move", 0), "leave the water"),
                       (("fly", 0), "use n")):
            with self.assertRaisesRegex(ValueError, msg):
                g.step(a)

    def test_eel_scatters_the_shoal(self):
        g = sl.Game(1, "normal")
        g.fish[0] = [g.home() + 1, 1]
        g.eels[0] = g.home() + 2
        g.restore()
        g.step(("move", 1))
        g.step(("net", 0))
        self.assertEqual(g.score, 1)
        g.step(("move", 1))
        self.assertEqual(g.shoal, [])
        self.assertEqual(g.score, 0)

    def test_hint_matches_demo_at_start(self):
        for seed in range(10):
            g = sl.Game(seed, "hard")
            self.assertEqual(g.hint(), g.demo_action())

    def test_parse(self):
        self.assertEqual(sl.Game.parse(" N "), ("move", 0))
        self.assertEqual(sl.Game.parse("net"), ("net", 0))
        with self.assertRaises(ValueError):
            sl.Game.parse("")


class Saves(unittest.TestCase):
    def test_round_trip_mid_game_and_won(self):
        g = sl.Game(3, "normal")
        for _ in range(3):
            g.step(g.demo_action())
        h = sl.Game.from_state(g.to_state())
        self.assertEqual(h.status(), g.status())
        g = demo(3, "normal")
        self.assertEqual(sl.Game.from_state(g.to_state()).score, g.score)

    def test_tampering_is_refused(self):
        g = sl.Game(2, "easy")
        g.step(g.demo_action())
        for key, val in (("score", 999), ("stamina", 99), ("target", 1), ("netted", [0, 0]), ("eels", [0, 0]),
                         ("won", True)):
            st = g.to_state()
            st[key] = val
            with self.assertRaises(ValueError, msg=key):
                sl.Game.from_state(st)


if __name__ == "__main__":
    unittest.main()
