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


class Properties(unittest.TestCase):
    """Iteration 1: invariants on every voyage, every move, every seed (no rule change)."""
    SEEDS = range(60)

    def check(self, g, before):
        s = g.size()
        self.assertEqual(g.turn, before["turn"] + 1, "every action is one turn")
        self.assertEqual(g.tide, g.turn // gm.TIDE_EVERY)
        self.assertEqual(g.heights, before["heights"], "heights never change")
        self.assertEqual(g.aboard + len(g.passengers), g.cfg["passengers"], "lanterns are aboard or waiting, never lost")
        self.assertTrue(all(0 <= r < s and 0 <= c < s for r, c in [g.ferry]))
        self.assertLessEqual(abs(g.ferry[0] - before["ferry"][0]) + abs(g.ferry[1] - before["ferry"][1]), 1, "the ferry moves at most one cell")
        if g.over:
            at_harbour = g.ferry == g.harbour
            self.assertTrue(at_harbour or g.flooded(*g.ferry), "a voyage ends only at the harbour or under water")
            self.assertEqual(g.won, at_harbour and g.aboard >= g.cfg["need"])
            if at_harbour:
                self.assertEqual(g.score, gm.PASSENGER_SCORE * g.aboard + gm.TIDE_SCORE * max(0, gm.TIDE_EVERY * s - g.turn))
        else:
            self.assertFalse(g.flooded(*g.ferry), "a live ferry is never under water")
            self.assertEqual(g.score, 0, "score is settled only at the harbour")

    def legal_moves(self, g):
        s = g.size()
        out = []
        for name, (dr, dc) in gm.MOVES.items():
            r, c = g.ferry[0] + dr, g.ferry[1] + dc
            if 0 <= r < s and 0 <= c < s and not g.flooded(r, c):
                out.append(name)
        return out

    def test_random_legal_moves_keep_invariants(self):
        import random
        for d in gm.DIFFICULTY:
            for seed in self.SEEDS:
                g = gm.start(seed, d)
                rng = random.Random(seed * 13 + 5)
                while not g.over:
                    before = {"turn": g.turn, "heights": [row[:] for row in g.heights], "ferry": list(g.ferry)}
                    moves = self.legal_moves(g)
                    self.assertTrue(moves, "wait is always legal while the ferry is dry")
                    g.step(rng.choice(moves))
                    self.check(g, before)

    def test_demo_moves_keep_invariants_and_are_legal(self):
        for d in gm.DIFFICULTY:
            for seed in self.SEEDS:
                g = gm.start(seed, d)
                while not g.over:
                    before = {"turn": g.turn, "heights": [row[:] for row in g.heights], "ferry": list(g.ferry)}
                    a = g.demo_action()
                    self.assertIn(a, self.legal_moves(g))
                    g.step(a)
                    self.check(g, before)

    def test_every_voyage_ends(self):
        for d in gm.DIFFICULTY:
            for seed in self.SEEDS:
                g = gm.start(seed, d)
                while not g.over:
                    g.step("wait")
                self.assertLessEqual(g.turn, gm.TIDE_EVERY * g.size())


class Balance(unittest.TestCase):
    """Iteration 3: the greedy watcher's win rate per difficulty is pinned to a band."""
    BANDS = {"easy": (0.70, 0.95), "normal": (0.35, 0.65), "hard": (0.20, 0.50)}

    def test_greedy_win_rate_bands(self):
        import io
        for d, (lo, hi) in self.BANDS.items():
            wins = sum(gm.demo(s, d, io.StringIO()).won for s in range(100))
            self.assertTrue(lo <= wins / 100 <= hi, f"{d}: greedy wins {wins}/100, band {lo}-{hi}")

    def test_voyages_are_not_trivial(self):
        import io
        for d in gm.DIFFICULTY:
            turns = [gm.demo(s, d, io.StringIO()).turn for s in range(100)]
            self.assertGreaterEqual(sum(turns) / 100, 10, f"{d}: average voyage too short")
